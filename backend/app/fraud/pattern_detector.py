"""
Deterministic fraud pattern detector.

Evaluates evidence from graph queries and CSV data to classify the fraud
pattern. Uses the five known patterns plus 'undocumented' and 'none'.

Does NOT call the LLM. The LLM may reason further on top of these results.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from ..models.case import FraudPattern

logger = logging.getLogger(__name__)


class PatternResult:
    def __init__(self) -> None:
        self.pattern: FraudPattern = FraudPattern.none
        self.pattern_description: str = ""
        self.confidence: float = 0.0
        self.supporting_evidence: list[str] = []
        self.contradicting_evidence: list[str] = []
        self.uncertainty: list[str] = []


class PatternDetector:
    """
    Evaluates transactions and graph evidence to classify fraud pattern.

    Rules are derived from:
    - README pattern definitions
    - Policy rules R1–R9
    - Closed case patterns for calibration
    """

    # Card testing: ≥ 3 tiny online charges within 1 hour, then larger purchase
    CARD_TESTING_SMALL_THRESHOLD = 5.0      # dollars
    CARD_TESTING_MIN_SMALL_COUNT = 3
    CARD_TESTING_WINDOW_HOURS = 1
    CARD_TESTING_LARGE_THRESHOLD = 20.0

    # CNP burst: 2-4 online purchases within 48 hours
    CNP_BURST_WINDOW_HOURS = 48
    CNP_BURST_MIN_COUNT = 2
    CNP_BURST_MAX_COUNT = 4

    def detect(
        self,
        flagged_txn: dict[str, Any],
        card_transactions: list[dict[str, Any]],
        identity: dict[str, Any] | None,
        customer_history: list[dict[str, Any]],
        shared_devices: list[dict[str, Any]],
        prior_fraud_cases: list[dict[str, Any]],
        trigger_type: str,
    ) -> PatternResult:
        result = PatternResult()

        txn_ts = _parse_ts(flagged_txn.get("ts", ""))
        channel = flagged_txn.get("channel", "")
        addr2 = str(flagged_txn.get("addr2", "")).strip()

        # ── Pattern 1: Card testing ───────────────────────────────────────────
        ct = self._check_card_testing(flagged_txn, card_transactions, txn_ts)
        if ct.confidence > 0.6:
            result = ct
            return result

        # ── Pattern 4: Out-of-region use ─────────────────────────────────────
        oor = self._check_out_of_region(
            flagged_txn, addr2, channel, customer_history, card_transactions
        )
        if oor.confidence > 0.6:
            result = oor
            return result

        # ── Pattern 5: Account takeover ───────────────────────────────────────
        ato = self._check_account_takeover(
            flagged_txn, identity, customer_history, card_transactions, trigger_type
        )
        if ato.confidence > 0.6:
            result = ato
            return result

        # ── Pattern 3: CNP from new device ───────────────────────────────────
        cnp_new = self._check_cnp_new_device(
            flagged_txn, identity, card_transactions, customer_history, txn_ts
        )
        if cnp_new.confidence > 0.5:
            result = cnp_new
            return result

        # ── Pattern 2: CNP fraud ──────────────────────────────────────────────
        cnp = self._check_cnp(
            flagged_txn, card_transactions, customer_history, txn_ts, trigger_type
        )
        if cnp.confidence > 0.4:
            result = cnp
            return result

        # ── Undocumented: shared device ring ─────────────────────────────────
        if shared_devices and len(shared_devices) > 0:
            multi_card_devs = [d for d in shared_devices if len(d.get("cards", [])) > 2]
            if multi_card_devs:
                r = PatternResult()
                r.pattern = FraudPattern.undocumented
                r.confidence = 0.55
                dev_info = multi_card_devs[0]
                r.pattern_description = (
                    f"Multiple cards ({len(dev_info.get('cards', []))}) share the same "
                    "device profile. Possible coordinated fraud network or device "
                    "compromised across accounts. No exact match to documented patterns."
                )
                r.supporting_evidence = [
                    f"Device shared by {len(dev_info.get('cards', []))} cards"
                ]
                return r

        # Default: insufficient evidence to classify
        result.pattern = FraudPattern.none
        result.confidence = 0.1
        result.uncertainty = ["Pattern unclear from available data"]
        return result

    # ── Pattern sub-checks ────────────────────────────────────────────────────

    def _check_card_testing(
        self,
        flagged_txn: dict,
        card_txns: list[dict],
        flagged_ts: datetime | None,
    ) -> PatternResult:
        r = PatternResult()
        if not flagged_ts:
            return r
        channel = flagged_txn.get("channel", "")
        if channel != "online":
            r.uncertainty.append("Card testing typically online; this is in-person")
            return r

        window_start = flagged_ts - timedelta(hours=self.CARD_TESTING_WINDOW_HOURS)
        nearby = [
            t for t in card_txns
            if _parse_ts(t.get("ts", "")) and
            window_start <= _parse_ts(t.get("ts")) <= flagged_ts and  # type: ignore[arg-type]
            t.get("channel") == "online"
        ]

        small = [
            t for t in nearby
            if _safe_float(t.get("TransactionAmt")) < self.CARD_TESTING_SMALL_THRESHOLD
        ]
        larger = [
            t for t in card_txns
            if _parse_ts(t.get("ts", "")) and
            _parse_ts(t.get("ts")) > flagged_ts and  # type: ignore[arg-type]
            _safe_float(t.get("TransactionAmt")) > self.CARD_TESTING_LARGE_THRESHOLD
        ]

        if len(small) >= self.CARD_TESTING_MIN_SMALL_COUNT:
            r.pattern = FraudPattern.card_testing
            r.confidence = min(0.65 + 0.05 * len(small), 0.95)
            r.supporting_evidence = [
                f"{len(small)} micro-transactions (< ${self.CARD_TESTING_SMALL_THRESHOLD}) "
                f"within {self.CARD_TESTING_WINDOW_HOURS} hour(s) of flagged transaction",
            ]
            if larger:
                r.confidence = min(r.confidence + 0.1, 0.97)
                r.supporting_evidence.append(
                    f"Followed by {len(larger)} larger purchase(s)"
                )
        return r

    def _check_out_of_region(
        self,
        flagged_txn: dict,
        addr2: str,
        channel: str,
        customer_history: list[dict],
        card_txns: list[dict],
    ) -> PatternResult:
        r = PatternResult()
        if channel == "online":
            return r  # Out-of-region is card-present fraud pattern

        if not addr2:
            r.uncertainty.append("No addr2 (country) on this transaction")
            return r

        # Build customer's known regions
        known_regions = {
            str(t.get("addr2", "")).strip()
            for t in customer_history
            if str(t.get("addr2", "")).strip()
        }
        known_regions.discard("")

        if addr2 not in known_regions and len(known_regions) > 0:
            # Check if home activity continued (clone indicator)
            ts = _parse_ts(flagged_txn.get("ts", ""))
            if ts:
                window_start = ts - timedelta(days=1)
                home_txns = [
                    t for t in customer_history
                    if _parse_ts(t.get("ts", "")) and
                    window_start <= _parse_ts(t.get("ts")) <= ts and  # type: ignore[arg-type]
                    str(t.get("addr2", "")) in known_regions
                ]
                if home_txns:
                    r.pattern = FraudPattern.out_of_region_use
                    r.confidence = 0.80
                    r.supporting_evidence = [
                        f"Transaction in region {addr2}, not in known regions {list(known_regions)[:5]}",
                        f"Concurrent home-region activity: {len(home_txns)} transaction(s)",
                    ]
                    return r
            r.pattern = FraudPattern.out_of_region_use
            r.confidence = 0.60
            r.supporting_evidence = [
                f"Transaction in region {addr2}, not in known regions {list(known_regions)[:5]}"
            ]
            r.uncertainty.append("No simultaneous home activity detected to confirm clone")
        elif not known_regions:
            r.uncertainty.append("No history to establish home region")
        else:
            r.contradicting_evidence.append(
                f"Region {addr2} is in customer's known history"
            )
        return r

    def _check_account_takeover(
        self,
        flagged_txn: dict,
        identity: dict | None,
        customer_history: list[dict],
        card_txns: list[dict],
        trigger_type: str,
    ) -> PatternResult:
        r = PatternResult()
        signals = 0

        # M-column match flag anomalies
        m_flags = {
            f"M{i}": flagged_txn.get(f"M{i}", "") for i in range(1, 10)
        }
        mismatch_count = sum(1 for v in m_flags.values() if v == "F")
        if mismatch_count >= 2:
            signals += 1
            r.supporting_evidence.append(
                f"{mismatch_count} match-flag mismatches (M columns) on flagged transaction"
            )

        # id_34 match status
        if identity:
            match_status = identity.get("id_34", "").strip()
            if "0" in match_status or "mismatch" in match_status.lower():
                signals += 1
                r.supporting_evidence.append(f"Identity match_status: {match_status}")

            device_status = identity.get("id_15", "").strip()
            if device_status == "New":
                signals += 1
                r.supporting_evidence.append("New device on account")

        # Mixed channel (recent in-person while this is online or vice versa)
        if customer_history:
            recent = customer_history[-10:]
            channels = {t.get("channel", "") for t in recent}
            if len(channels) > 1 and flagged_txn.get("channel") == "online":
                signals += 1
                r.supporting_evidence.append("Mixed channel activity (in-person + online) recently")

        # Customer dispute trigger
        if trigger_type == "customer_report":
            signals += 1
            r.supporting_evidence.append("Customer explicitly disputed transaction")

        if signals >= 3:
            r.pattern = FraudPattern.account_takeover
            r.confidence = min(0.55 + 0.1 * signals, 0.92)
        elif signals == 2:
            r.confidence = 0.45
            r.pattern = FraudPattern.account_takeover
            r.uncertainty.append("Only two ATO signals — verify with customer")
        return r

    def _check_cnp_new_device(
        self,
        flagged_txn: dict,
        identity: dict | None,
        card_txns: list[dict],
        customer_history: list[dict],
        flagged_ts: datetime | None,
    ) -> PatternResult:
        r = PatternResult()
        if not identity:
            return r
        if flagged_txn.get("channel") != "online":
            return r

        device_status = identity.get("id_15", "").strip()
        if device_status != "New":
            r.contradicting_evidence.append("Device is not new for this account")
            return r

        # Check CNP burst on top of new device
        cnp = self._check_cnp(flagged_txn, card_txns, customer_history, flagged_ts, "risk_score")
        if cnp.confidence > 0.35:
            r.pattern = FraudPattern.card_not_present_new_device
            r.confidence = min(cnp.confidence + 0.15, 0.92)
            r.supporting_evidence = cnp.supporting_evidence + ["New device"]
            proxy = identity.get("id_23", "").strip().lower()
            if proxy in ("anonymous", "hidden"):
                r.confidence = min(r.confidence + 0.08, 0.95)
                r.supporting_evidence.append(f"Proxy: {proxy}")
        else:
            r.pattern = FraudPattern.card_not_present_new_device
            r.confidence = 0.50
            r.supporting_evidence = ["Online transaction from new device"]
            r.uncertainty = ["No burst of transactions to confirm CNP fraud pattern"]
        return r

    def _check_cnp(
        self,
        flagged_txn: dict,
        card_txns: list[dict],
        customer_history: list[dict],
        flagged_ts: datetime | None,
        trigger_type: str,
    ) -> PatternResult:
        r = PatternResult()
        if flagged_txn.get("channel") != "online":
            return r
        if not flagged_ts:
            return r

        window_start = flagged_ts - timedelta(hours=self.CNP_BURST_WINDOW_HOURS)
        burst = [
            t for t in card_txns
            if _parse_ts(t.get("ts", "")) and
            window_start <= _parse_ts(t.get("ts")) <= flagged_ts and  # type: ignore[arg-type]
            t.get("channel") == "online" and
            t.get("TransactionID") != flagged_txn.get("TransactionID")
        ]

        if len(burst) >= self.CNP_BURST_MIN_COUNT - 1:  # Including flagged txn itself
            # Check if amounts/merchants are out of character
            historical_amts = [
                _safe_float(t.get("TransactionAmt"))
                for t in customer_history[-50:]
            ]
            flagged_amt = _safe_float(flagged_txn.get("TransactionAmt"))
            out_of_character = False
            if historical_amts:
                import statistics as st
                mean = st.mean(historical_amts)
                if flagged_amt > mean * 3:
                    out_of_character = True
                    r.supporting_evidence.append(
                        f"Amount ${flagged_amt:.2f} is significantly above mean ${mean:.2f}"
                    )

            r.pattern = FraudPattern.card_not_present_fraud
            r.confidence = 0.55 + (0.05 * len(burst)) + (0.1 if out_of_character else 0)
            r.confidence = min(r.confidence, 0.90)
            r.supporting_evidence.append(
                f"{len(burst)+1} online transaction(s) within {self.CNP_BURST_WINDOW_HOURS}h window"
            )
            if trigger_type == "customer_report":
                r.confidence = min(r.confidence + 0.15, 0.95)
                r.supporting_evidence.append("Customer disputed transaction")
        elif trigger_type == "customer_report":
            r.pattern = FraudPattern.card_not_present_fraud
            r.confidence = 0.45
            r.supporting_evidence = ["Customer dispute on online transaction"]
            r.uncertainty = ["No clear burst of transactions to confirm CNP pattern"]
        return r


# ── Utilities ─────────────────────────────────────────────────────────────────

def _parse_ts(ts_str: str) -> datetime | None:
    if not ts_str:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(ts_str, fmt)
        except ValueError:
            continue
    return None


def _safe_float(val: Any) -> float:
    try:
        return float(val)
    except (TypeError, ValueError):
        return 0.0
