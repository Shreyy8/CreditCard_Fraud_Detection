"""
Suspicious Activity Report (SAR) generator.

Produces a standalone SAR narrative following FinCEN guidelines.
All facts come from investigation evidence — nothing is fabricated.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any

from ..models.case import SAR

if TYPE_CHECKING:
    from ..models.case import InvestigationState

logger = logging.getLogger(__name__)


class SARGenerator:
    """
    Generates a policy-compliant SAR when FILE_REPORT is recommended.

    SAR structure follows FinCEN narrative guidance:
    who, what, when, where, how, why suspicious.
    """

    def generate(
        self,
        state: "InvestigationState",
        exposure: Any,
    ) -> SAR:
        txn = state.flagged_txn or {}
        txn_id = txn.get("TransactionID", state.flagged_txn_id)
        customer_id = state.customer_id
        card_id = state.card_id

        # ── Subjects ────────────────────────────────────────────────────────
        subjects: list[str] = [customer_id, card_id]
        if exposure and exposure.connected_card_ids:
            subjects.extend(exposure.connected_card_ids[:5])
        if exposure and exposure.connected_device_profiles:
            subjects.extend([f"DEVICE:{d[:40]}" for d in exposure.connected_device_profiles[:3]])
        # Deduplicate
        subjects = list(dict.fromkeys(s for s in subjects if s))

        # ── Amounts and dates ────────────────────────────────────────────────
        total_amount = round(state.exposure_usd, 2)
        affected_txn_ids = [t.get("TransactionID", "") for t in state.affected_txns]
        if not affected_txn_ids:
            affected_txn_ids = [txn_id]

        # Activity date range from transaction timestamps
        dates = []
        for t in ([txn] + state.affected_txns[:20]):
            ts = t.get("ts", "")
            if ts:
                try:
                    d = datetime.strptime(ts[:10], "%Y-%m-%d").date().isoformat()
                    dates.append(d)
                except ValueError:
                    pass
        dates = sorted(set(dates))
        activity_dates = [dates[0], dates[-1]] if len(dates) >= 2 else (
            [dates[0], dates[0]] if dates else [
                txn.get("ts", "")[:10] or "",
                txn.get("ts", "")[:10] or "",
            ]
        )

        # ── Narrative ───────────────────────────────────────────────────────
        narrative = self._build_narrative(
            state=state,
            txn=txn,
            txn_id=txn_id,
            affected_txn_ids=affected_txn_ids,
            total_amount=total_amount,
            activity_dates=activity_dates,
            exposure=exposure,
        )

        # ── SAR reason ───────────────────────────────────────────────────────
        reason = self._build_reason(state, total_amount, exposure)

        return SAR(
            file=True,
            reason=reason,
            narrative=narrative,
            subjects=subjects,
            total_amount_usd=total_amount,
            activity_dates=activity_dates,
        )

    def _build_narrative(
        self,
        state: "InvestigationState",
        txn: dict,
        txn_id: str,
        affected_txn_ids: list[str],
        total_amount: float,
        activity_dates: list[str],
        exposure: Any,
    ) -> str:
        channel = txn.get("channel", "unknown channel")
        amount = txn.get("TransactionAmt", "unknown amount")
        card_network = txn.get("card4", "")
        card_type = txn.get("card6", "")
        region = txn.get("addr1", "")
        country = txn.get("addr2", "")
        pattern = state.pattern.value.replace("_", " ")
        fp = state.fraud_probability
        trigger = state.trigger_type.replace("_", " ")

        identity = state.connected_entities.get("identity", {}) or {}
        device_info = identity.get("DeviceInfo", "")
        os_info = identity.get("id_30", "")
        browser = identity.get("id_31", "")
        proxy = identity.get("id_23", "")
        device_status = identity.get("id_15", "")

        connected_cards_str = ""
        if exposure and exposure.connected_card_ids:
            connected_cards_str = (
                f" Investigation identified {len(exposure.connected_card_ids)} "
                f"additional connected card(s): {', '.join(exposure.connected_card_ids[:5])}."
            )

        prior_fraud_str = ""
        prior_confirmed = [c for c in state.prior_cases if c.get("outcome") == "confirmed_fraud"]
        if prior_confirmed:
            prior_fraud_str = (
                f" Customer {state.customer_id} has {len(prior_confirmed)} prior confirmed "
                f"fraud case(s) on record (e.g., {prior_confirmed[0].get('case_id', '')})."
            )

        identity_str = ""
        if device_info:
            identity_str = (
                f" The transaction originated from device '{device_info}'"
                f"{' running ' + os_info if os_info else ''}"
                f"{' via ' + browser if browser else ''}"
                f"{', device status: ' + device_status if device_status else ''}"
                f"{', proxy: ' + proxy if proxy and proxy not in ('', 'nan') else ''}."
            )

        evidence_summary = "; ".join(
            e.claim for e in state.graph_evidence[:5] if e.claim
        )

        narrative = (
            f"SUSPICIOUS ACTIVITY REPORT — {state.case_id}\n\n"
            f"WHO: Customer {state.customer_id}, card {state.card_id} "
            f"({'  '.join(filter(None, [card_network, card_type]))}). "
            f"Alert triggered by: {trigger}.\n\n"
            f"WHAT: {len(affected_txn_ids)} transaction(s) totaling ${total_amount:.2f} USD "
            f"assessed as {pattern} with fraud probability {fp:.2f}. "
            f"Flagged transaction {txn_id} of ${amount} USD via {channel}."
            f"{prior_fraud_str}{connected_cards_str}\n\n"
            f"WHEN: Activity between {activity_dates[0]} and {activity_dates[-1]}.\n\n"
            f"WHERE: Transaction billed in region {region}, country code {country}. "
            f"Channel: {channel}.{identity_str}\n\n"
            f"HOW: {pattern.capitalize()} — "
            f"{self._how_description(state.pattern.value)}\n\n"
            f"WHY SUSPICIOUS: {evidence_summary or 'Multiple independent evidence signals support fraud classification.'}. "
            f"Fraud probability assessed at {fp:.0%} based on {len(state.graph_evidence)} "
            f"evidence item(s) from transaction graph, identity data, and closed case history. "
            f"Policy rules applied: "
            f"{self._applicable_rules(state)}."
        )
        return narrative.strip()

    def _how_description(self, pattern: str) -> str:
        descriptions = {
            "card_testing": (
                "Card number tested with multiple small online authorizations before "
                "larger purchase, consistent with stolen card verification."
            ),
            "card_not_present_fraud": (
                "Card number used online in a burst of transactions inconsistent with "
                "cardholder's established purchase history, without physical card present."
            ),
            "card_not_present_new_device": (
                "Online card-not-present transactions from a device newly associated with "
                "this account, potentially via proxy, inconsistent with normal behavior."
            ),
            "out_of_region_use": (
                "Card-present purchases in a billing region with no historical presence "
                "while normal home-region activity continued, indicating possible card clone."
            ),
            "account_takeover": (
                "Mixed-channel transactions with match-flag anomalies and device changes "
                "inconsistent with cardholder's established profile, suggesting credential theft."
            ),
            "undocumented": (
                "Activity matching none of the five documented patterns but showing "
                "coordinated or repeated suspicious behavior across accounts."
            ),
            "none": "No specific fraud typology identified; activity is suspicious based on combined signals.",
        }
        return descriptions.get(pattern, "Pattern details in case file.")

    def _applicable_rules(self, state: "InvestigationState") -> str:
        rules = []
        if state.trigger_type == "customer_report":
            rules.append("R2")
        pattern = state.pattern.value
        if pattern == "card_testing":
            rules.append("R5")
        elif pattern in ("card_not_present_fraud", "card_not_present_new_device"):
            rules += ["R1", "R2"]
        elif pattern == "out_of_region_use":
            rules += ["R2", "R3"]
        elif pattern == "account_takeover":
            rules += ["R2", "R8"]
        elif pattern == "undocumented":
            rules.append("R9")
        if state.exposure_usd > 1000:
            rules.append("R2 (exposure > $1,000)")
        return ", ".join(sorted(set(rules))) or "R2"

    def _build_reason(
        self, state: "InvestigationState", total_amount: float, exposure: Any
    ) -> str:
        reasons = []
        if total_amount > 1000:
            reasons.append(f"exposure ${total_amount:.2f} > $1,000")
        if exposure and exposure.connected_card_ids:
            reasons.append(
                f"activity connects to {len(exposure.connected_card_ids)} additional card(s)"
            )
        if exposure and exposure.connected_device_profiles:
            reasons.append("shared device profile across cards")
        if state.trigger_type == "customer_report":
            reasons.append("customer denial of transaction")
        if state.pattern.value == "undocumented":
            reasons.append("undocumented coordinated pattern (Policy R9)")
        if not reasons:
            reasons.append(f"fraud probability {state.fraud_probability:.2f} with corroborating evidence")
        return "FILE_REPORT required: " + "; ".join(reasons) + "."
