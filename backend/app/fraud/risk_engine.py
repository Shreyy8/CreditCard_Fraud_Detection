"""
Deterministic risk engine.

The LLM does NOT assign risk scores.
This module aggregates evidence signals into a structured risk assessment.
"""

from __future__ import annotations

import logging
import statistics
from typing import Any

logger = logging.getLogger(__name__)


class RiskSignal:
    def __init__(self, name: str, weight: float, triggered: bool, detail: str = "") -> None:
        self.name = name
        self.weight = weight          # 0.0 – 1.0
        self.triggered = triggered
        self.detail = detail


class RiskAssessment:
    def __init__(self) -> None:
        self.signals: list[RiskSignal] = []
        self.risk_score: float = 0.0
        self.risk_level: str = "LOW"
        self.confidence: float = 0.0
        self.evidence_count: int = 0
        self.uncertainty_count: int = 0
        self.uncertainty_flags: list[str] = []


class RiskEngine:
    """
    Aggregates deterministic risk signals.

    Signal weights are policy-calibrated.
    The final score is NOT fed directly to the policy without confidence checking.
    """

    # Risk thresholds
    HIGH_THRESHOLD = 0.70
    MEDIUM_THRESHOLD = 0.40
    # Confidence: how many independent corroborating signals we have
    HIGH_CONFIDENCE_MIN_SIGNALS = 3

    def assess(
        self,
        trigger_type: str,
        bank_risk_score: float | None,
        txn: dict[str, Any],
        customer_history: list[dict[str, Any]],
        identity: dict[str, Any] | None,
        closed_cases: list[dict[str, Any]],
        connected_cards: list[str],
        shared_devices: list[dict[str, Any]],
        behavioral_anomalies: list[dict[str, Any]],
        llm_fraud_probability: float | None = None,
    ) -> RiskAssessment:
        """
        Produce a RiskAssessment from all available evidence signals.
        LLM probability is an optional additional signal, NOT the authority.
        """
        signals: list[RiskSignal] = []

        # 1. Bank model risk score
        if bank_risk_score is not None:
            signals.append(RiskSignal(
                name="bank_model_risk_score",
                weight=bank_risk_score * 0.4,  # Capped influence
                triggered=bank_risk_score > 0.5,
                detail=f"Bank model scored {bank_risk_score:.2f}",
            ))

        # 2. Customer report (strongest single signal)
        if trigger_type == "customer_report":
            signals.append(RiskSignal(
                name="customer_dispute",
                weight=0.6,
                triggered=True,
                detail="Cardholder explicitly disputed this transaction",
            ))

        # 3. Prior confirmed fraud on same customer/card
        confirmed_prior = [c for c in closed_cases if c.get("outcome") == "confirmed_fraud"]
        if confirmed_prior:
            signals.append(RiskSignal(
                name="prior_confirmed_fraud",
                weight=0.5,
                triggered=True,
                detail=f"{len(confirmed_prior)} prior confirmed fraud case(s) on this customer/card",
            ))

        # 4. New device flag
        if identity:
            device_status = identity.get("id_15", "").strip()
            proxy = identity.get("id_23", "").strip().lower()
            if device_status == "New":
                signals.append(RiskSignal(
                    name="new_device",
                    weight=0.35,
                    triggered=True,
                    detail="Transaction from a device newly seen on this account",
                ))
            if proxy in ("anonymous", "hidden"):
                signals.append(RiskSignal(
                    name="proxy_connection",
                    weight=0.3,
                    triggered=True,
                    detail=f"Proxy type: {proxy}",
                ))

        # 5. Out-of-region use
        txn_region = str(txn.get("addr2", "")).strip()
        if txn_region and txn_region != "87":  # 87 = home country
            historical_regions = {
                str(t.get("addr2", "")) for t in customer_history[-30:]
            }
            if txn_region not in historical_regions:
                signals.append(RiskSignal(
                    name="out_of_home_country",
                    weight=0.25,
                    triggered=True,
                    detail=f"Transaction in country {txn_region}, not in recent history",
                ))

        # 6. High-value transaction vs history
        try:
            amt = float(txn.get("TransactionAmt", 0))
            historical_amts = [
                float(t.get("TransactionAmt", 0))
                for t in customer_history
                if t.get("TransactionAmt")
            ]
            if historical_amts:
                mean_amt = statistics.mean(historical_amts)
                stdev_amt = statistics.stdev(historical_amts) if len(historical_amts) > 1 else mean_amt
                z_score = (amt - mean_amt) / (stdev_amt + 1e-9)
                if z_score > 3:
                    signals.append(RiskSignal(
                        name="unusually_high_amount",
                        weight=0.3,
                        triggered=True,
                        detail=f"Amount ${amt:.2f} is {z_score:.1f} std devs above mean ${mean_amt:.2f}",
                    ))
        except (ValueError, TypeError):
            pass

        # 7. Shared device with fraud
        fraud_device_cards = []
        for dev in shared_devices:
            for card in dev.get("cards", []):
                if card in [c.get("card_id") for c in confirmed_prior]:
                    fraud_device_cards.append(card)
        if fraud_device_cards:
            signals.append(RiskSignal(
                name="device_linked_to_fraud",
                weight=0.55,
                triggered=True,
                detail=f"Shared device with known fraud cards: {fraud_device_cards[:3]}",
            ))

        # 8. Multiple connected cards
        if len(connected_cards) > 2:
            signals.append(RiskSignal(
                name="multi_card_ring",
                weight=0.3,
                triggered=True,
                detail=f"{len(connected_cards)} cards connected to same device/region",
            ))

        # 9. Behavioral anomalies from graph
        for anomaly in behavioral_anomalies[:3]:
            severity = anomaly.get("severity", "low")
            w = {"high": 0.4, "medium": 0.25, "low": 0.1}.get(severity, 0.1)
            signals.append(RiskSignal(
                name=f"behavioral_anomaly_{anomaly.get('type', 'unknown')}",
                weight=w,
                triggered=True,
                detail=anomaly.get("description", ""),
            ))

        # 10. LLM fraud probability as additional signal (capped)
        if llm_fraud_probability is not None:
            signals.append(RiskSignal(
                name="llm_reasoning_signal",
                weight=min(llm_fraud_probability * 0.3, 0.3),
                triggered=llm_fraud_probability > 0.5,
                detail=f"LLM assessed fraud probability: {llm_fraud_probability:.2f}",
            ))

        # ── Aggregate ─────────────────────────────────────────────────────────
        triggered = [s for s in signals if s.triggered]
        if not triggered:
            raw_score = 0.05
        else:
            # Weighted average of triggered signals, capped at 1.0
            total_w = sum(s.weight for s in triggered)
            raw_score = min(total_w, 1.0)

        # Confidence: grows with number of independent triggered signals
        confidence = min(len(triggered) / max(self.HIGH_CONFIDENCE_MIN_SIGNALS, 1), 1.0)

        # Risk level
        if raw_score >= self.HIGH_THRESHOLD:
            level = "HIGH"
        elif raw_score >= self.MEDIUM_THRESHOLD:
            level = "MEDIUM"
        else:
            level = "LOW"

        # Uncertainty flags
        uncertainty_flags = []
        if not identity and txn.get("channel") == "online":
            uncertainty_flags.append("No identity record for online transaction")
        if not confirmed_prior and trigger_type == "risk_score":
            uncertainty_flags.append("No prior confirmed fraud to corroborate model score")
        if len(triggered) < 2 and raw_score > 0.5:
            uncertainty_flags.append("Only one signal supports this risk level")
        if not customer_history:
            uncertainty_flags.append("No transaction history to establish baseline")

        result = RiskAssessment()
        result.signals = signals
        result.risk_score = round(raw_score, 3)
        result.risk_level = level
        result.confidence = round(confidence, 3)
        result.evidence_count = len(triggered)
        result.uncertainty_count = len(uncertainty_flags)
        result.uncertainty_flags = uncertainty_flags
        return result
