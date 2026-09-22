"""
GraphRAG retriever.

Builds a structured context package for the LLM from:
1. Graph evidence (TigerGraph queries)
2. Similar closed cases (case memory)
3. Policy sections (relevant rules)
4. Fraud typology (pattern descriptions)

Does NOT send raw CSVs or full transaction sets to the LLM.
Applies top-k filtering and evidence ranking.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Fraud policy text — embedded for retrieval (extracted from README)
POLICY_SECTIONS = {
    "R1": "R1. Verify before you block on a weak signal. If fraud probability < 0.70 and single signal, recommend VERIFY_WITH_CUSTOMER or STEP_UP_AUTH before any block.",
    "R2": "R2. Customer denies: BLOCK_CARD + CREATE_CASE. Add FILE_REPORT if exposure > $1000 or shared device.",
    "R3": "R3. Customer confirms: CLOSE_NO_FRAUD.",
    "R4": "R4. No reply 24h: MONITOR_CARD + DECLINE_TRANSACTION. Escalate if exposure > $500.",
    "R5": "R5. Card testing (3+ small online auths < $5 within 1h then larger purchase): DECLINE_TRANSACTION + STEP_UP_AUTH. BLOCK_CARD if purchase > $100 already cleared.",
    "R6": "R6. Shared origin (same device/region/email across cards): CREATE_CASE + FILE_REPORT + MONITOR_CONNECTED_CARDS for all sharing cards.",
    "R7": "R7. Disputed but matches recurring pattern (same merchant, same amount, monthly): CREATE_CASE + VERIFY_WITH_CUSTOMER + WARN_CUSTOMER. Do not block.",
    "R8": "R8. Uncertain + exposure > $500 or conflicting evidence: ESCALATE_TO_ANALYST.",
    "R9": "R9. Undocumented pattern (coordinated/repeated abuse across customers): CREATE_CASE + FILE_REPORT + ESCALATE_TO_ANALYST. Describe in own words.",
    "R10": "R10. Never BLOCK_ALL_CARDS unless at least two cards confirmed fraud or credentials confirmed compromised.",
}

PATTERN_DESCRIPTIONS = {
    "card_testing": "Card testing: stolen card number checked before use — 3+ tiny online auths (< $5) within 1 hour, then larger purchase. Confirmed by sequence. Policy R5.",
    "card_not_present_fraud": "Card-not-present fraud: card number used online without the card. Amounts/products inconsistent with history, burst of 2-4 transactions within 48h. Verify before blocking. Policy R1-R4.",
    "card_not_present_new_device": "CNP from new device: same as CNP fraud but identity record marks device as New, sometimes behind proxy. Stronger signal, still not proof. Policy R1-R4.",
    "out_of_region_use": "Out-of-region use: card-present purchases in billing region cardholder has no history in while normal activity continues at home. Multiple days = trip not clone. Policy R2, R3.",
    "account_takeover": "Account takeover: mixed-channel activity inconsistent with cardholder, device and match-flag anomalies, points to stolen credentials. Policy R2.",
}


class GraphRAGRetriever:
    """Assembles a ranked context package for LLM reasoning."""

    MAX_EVIDENCE_ITEMS = 12
    MAX_HISTORY_TRANSACTIONS = 10
    MAX_PRIOR_CASES = 5

    def build_context(
        self,
        flagged_txn: dict[str, Any],
        customer_history: list[dict[str, Any]],
        identity: dict[str, Any] | None,
        closed_cases: list[dict[str, Any]],
        graph_evidence: list[dict[str, Any]],
        pattern_result: Any,
        risk_assessment: Any,
        trigger_type: str,
        trigger_text: str,
    ) -> dict[str, Any]:
        """
        Build a focused, top-k evidence context package.
        Returns a dict ready to pass to the LLM system prompt.
        """
        ctx: dict[str, Any] = {}

        # 1. Alert / trigger
        ctx["trigger"] = {
            "type": trigger_type,
            "text": trigger_text,
            "flagged_txn_id": flagged_txn.get("TransactionID", ""),
            "amount": flagged_txn.get("TransactionAmt", ""),
            "channel": flagged_txn.get("channel", ""),
            "timestamp": flagged_txn.get("ts", ""),
            "bank_risk_score": flagged_txn.get("risk_score", ""),
        }

        # 2. Transaction snapshot (key fields only)
        ctx["flagged_transaction"] = self._summarize_transaction(flagged_txn, identity)

        # 3. Customer history summary (top-k recent)
        ctx["customer_history_summary"] = self._summarize_history(customer_history)

        # 4. Graph evidence (ranked, top-k)
        ctx["graph_evidence"] = self._rank_evidence(graph_evidence)[: self.MAX_EVIDENCE_ITEMS]

        # 5. Similar prior cases
        ctx["prior_cases"] = [
            self._summarize_case(c) for c in closed_cases[: self.MAX_PRIOR_CASES]
        ]

        # 6. Pattern assessment
        if pattern_result:
            ctx["pattern_assessment"] = {
                "pattern": pattern_result.pattern.value,
                "confidence": pattern_result.confidence,
                "supporting_evidence": pattern_result.supporting_evidence[:5],
                "contradicting_evidence": pattern_result.contradicting_evidence[:3],
                "uncertainty": pattern_result.uncertainty[:3],
                "description": PATTERN_DESCRIPTIONS.get(pattern_result.pattern.value, ""),
            }

        # 7. Risk assessment
        if risk_assessment:
            ctx["risk_assessment"] = {
                "risk_level": risk_assessment.risk_level,
                "risk_score": risk_assessment.risk_score,
                "confidence": risk_assessment.confidence,
                "evidence_count": risk_assessment.evidence_count,
                "uncertainty_flags": risk_assessment.uncertainty_flags[:5],
            }

        # 8. Relevant policy sections
        ctx["relevant_policy"] = self._select_policy_sections(
            pattern_result, risk_assessment, trigger_type
        )

        return ctx

    def _summarize_transaction(
        self, txn: dict, identity: dict | None
    ) -> dict[str, Any]:
        """Key fields only — not all 58+ columns."""
        summary = {
            "id": txn.get("TransactionID"),
            "timestamp": txn.get("ts"),
            "amount_usd": txn.get("TransactionAmt"),
            "channel": txn.get("channel"),
            "product_code": txn.get("ProductCD"),
            "card_network": txn.get("card4"),
            "card_type": txn.get("card6"),
            "billing_region": txn.get("addr1"),
            "billing_country": txn.get("addr2"),
            "purchaser_email_domain": txn.get("P_emaildomain"),
            "bank_risk_score": txn.get("risk_score"),
            "match_flags": {
                f"M{i}": txn.get(f"M{i}") for i in range(1, 10)
                if txn.get(f"M{i}")
            },
        }
        if identity:
            summary["identity"] = {
                "device_type": identity.get("DeviceType"),
                "device_info": identity.get("DeviceInfo"),
                "os": identity.get("id_30"),
                "browser": identity.get("id_31"),
                "screen": identity.get("id_33"),
                "device_status": identity.get("id_15"),  # New/Found
                "proxy_type": identity.get("id_23"),
                "match_status": identity.get("id_34"),
            }
        return summary

    def _summarize_history(self, history: list[dict]) -> dict[str, Any]:
        if not history:
            return {"count": 0, "note": "No transaction history available"}
        recent = history[-self.MAX_HISTORY_TRANSACTIONS:]
        amounts = [float(t.get("TransactionAmt") or 0) for t in history if t.get("TransactionAmt")]
        channels = {t.get("channel", "") for t in history}
        regions = {str(t.get("addr2", "")) for t in history if t.get("addr2")}
        return {
            "total_transactions": len(history),
            "recent_transactions": [
                {
                    "id": t.get("TransactionID"),
                    "ts": t.get("ts"),
                    "amount": t.get("TransactionAmt"),
                    "channel": t.get("channel"),
                    "region": t.get("addr2"),
                }
                for t in recent
            ],
            "avg_amount_usd": round(sum(amounts) / len(amounts), 2) if amounts else 0,
            "max_amount_usd": round(max(amounts), 2) if amounts else 0,
            "channels_seen": list(channels),
            "regions_seen": list(regions),
        }

    def _summarize_case(self, case: dict) -> dict[str, Any]:
        return {
            "case_id": case.get("case_id"),
            "outcome": case.get("outcome"),
            "pattern": case.get("pattern"),
            "exposure_usd": case.get("exposure_usd"),
            "n_txns": case.get("n_txns"),
            "analyst_notes": (case.get("analyst_notes") or "")[:300],
        }

    def _rank_evidence(self, evidence: list[dict]) -> list[dict]:
        """Rank evidence by severity / relevance. High severity first."""
        severity_order = {"high": 0, "medium": 1, "low": 2}
        return sorted(
            evidence,
            key=lambda e: severity_order.get(e.get("severity", "low"), 2),
        )

    def _select_policy_sections(
        self, pattern_result: Any, risk_assessment: Any, trigger_type: str
    ) -> list[str]:
        sections = []
        if trigger_type == "customer_report":
            sections += [POLICY_SECTIONS["R2"], POLICY_SECTIONS["R3"], POLICY_SECTIONS["R7"]]
        if pattern_result:
            pattern = pattern_result.pattern.value
            if pattern == "card_testing":
                sections.append(POLICY_SECTIONS["R5"])
            elif pattern in ("card_not_present_fraud", "card_not_present_new_device"):
                sections += [POLICY_SECTIONS["R1"], POLICY_SECTIONS["R2"]]
            elif pattern == "out_of_region_use":
                sections += [POLICY_SECTIONS["R2"], POLICY_SECTIONS["R3"]]
            elif pattern == "account_takeover":
                sections += [POLICY_SECTIONS["R2"], POLICY_SECTIONS["R8"]]
            elif pattern == "undocumented":
                sections.append(POLICY_SECTIONS["R9"])
        if risk_assessment and risk_assessment.uncertainty_flags:
            sections.append(POLICY_SECTIONS["R8"])
        # Always include shared origin rule
        sections.append(POLICY_SECTIONS["R6"])
        # Deduplicate while preserving order
        seen = set()
        unique = []
        for s in sections:
            if s not in seen:
                seen.add(s)
                unique.append(s)
        return unique
