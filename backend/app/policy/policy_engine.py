"""
Policy engine — machine-readable implementation of Fraud Policy v1.0.
Rules R1-R10, approval routes, and stopping criteria.
"""

from __future__ import annotations

import logging
from typing import Any

from ..models.case import ActionRecommendation, ActionType, ApprovalRoute, FraudPattern

logger = logging.getLogger(__name__)

AUTO_ACTIONS = {
    ActionType.ALLOW_TRANSACTION, ActionType.MONITOR_CARD,
    ActionType.MONITOR_CONNECTED_CARDS, ActionType.WARN_CUSTOMER,
    ActionType.VERIFY_WITH_CUSTOMER, ActionType.STEP_UP_AUTH,
    ActionType.GENERATE_REPORT, ActionType.CREATE_CASE,
    ActionType.ESCALATE_TO_ANALYST, ActionType.CLOSE_NO_FRAUD,
}


def get_route(action: ActionType, exposure_usd: float = 0.0) -> ApprovalRoute:
    if action in AUTO_ACTIONS:
        return ApprovalRoute.auto
    if action == ActionType.BLOCK_CARD:
        return ApprovalRoute.L1 if exposure_usd <= 2500 else ApprovalRoute.L2
    if action == ActionType.DECLINE_TRANSACTION:
        return ApprovalRoute.L1
    if action in {ActionType.BLOCK_ALL_CARDS, ActionType.FILE_REPORT}:
        return ApprovalRoute.L2
    return ApprovalRoute.auto


class PolicyEngine:
    def recommend(
        self,
        trigger_type: str,
        fraud_probability: float,
        risk_level: str,
        confidence: float,
        pattern: FraudPattern,
        exposure_usd: float,
        num_signals: int,
        num_connected_cards: int,
        num_shared_devices: int,
        has_prior_confirmed_fraud: bool,
        customer_response: str | None = None,
    ) -> list[ActionRecommendation]:
        actions: list[ActionRecommendation] = []

        # R3: customer confirmed
        if customer_response == "confirmed":
            return [ActionRecommendation(
                action=ActionType.CLOSE_NO_FRAUD,
                route=ApprovalRoute.auto,
                reason="Customer confirmed transaction. Policy R3.",
            )]

        # R2: customer denied
        if customer_response == "denied" or trigger_type == "customer_report":
            actions.append(ActionRecommendation(
                action=ActionType.CREATE_CASE, route=ApprovalRoute.auto,
                reason="Customer dispute. Policy R2.",
            ))
            actions.append(ActionRecommendation(
                action=ActionType.BLOCK_CARD,
                route=get_route(ActionType.BLOCK_CARD, exposure_usd),
                reason="Customer denied transaction. Policy R2.",
            ))
            if exposure_usd > 1000 or num_shared_devices > 0 or num_connected_cards > 0:
                actions.append(ActionRecommendation(
                    action=ActionType.FILE_REPORT, route=ApprovalRoute.L2,
                    reason=f"Denial + exposure ${exposure_usd:.2f} > $1000 or shared device/cards. R2.",
                ))
            if num_connected_cards > 0:
                actions.append(ActionRecommendation(
                    action=ActionType.MONITOR_CONNECTED_CARDS, route=ApprovalRoute.auto,
                    reason="Connected cards detected. Policy R2.",
                ))
            return actions

        # R4: no reply
        if customer_response == "no_reply":
            actions = [
                ActionRecommendation(
                    action=ActionType.MONITOR_CARD, route=ApprovalRoute.auto,
                    reason="No reply within 24h. Policy R4.",
                ),
                ActionRecommendation(
                    action=ActionType.DECLINE_TRANSACTION, route=ApprovalRoute.L1,
                    reason="Pending authorization declined — no reply. Policy R4.",
                ),
            ]
            if exposure_usd > 500:
                actions.append(ActionRecommendation(
                    action=ActionType.ESCALATE_TO_ANALYST, route=ApprovalRoute.auto,
                    reason=f"Exposure ${exposure_usd:.2f} > $500 with no reply. R4.",
                ))
            return actions

        # R5: card testing
        if pattern == FraudPattern.card_testing:
            actions = [
                ActionRecommendation(
                    action=ActionType.DECLINE_TRANSACTION, route=ApprovalRoute.L1,
                    reason="Card testing confirmed. Policy R5.",
                ),
                ActionRecommendation(
                    action=ActionType.STEP_UP_AUTH, route=ApprovalRoute.auto,
                    reason="Card testing: require step-up auth. Policy R5.",
                ),
            ]
            if exposure_usd > 100:
                actions.append(ActionRecommendation(
                    action=ActionType.BLOCK_CARD,
                    route=get_route(ActionType.BLOCK_CARD, exposure_usd),
                    reason="Purchase >$100 cleared during card test. Policy R5.",
                ))
            return actions

        # R6: shared origin
        if num_shared_devices > 0 or num_connected_cards > 2:
            actions += [
                ActionRecommendation(
                    action=ActionType.CREATE_CASE, route=ApprovalRoute.auto,
                    reason="Shared device/region across cards. Policy R6.",
                ),
                ActionRecommendation(
                    action=ActionType.FILE_REPORT, route=ApprovalRoute.L2,
                    reason="Shared origin pattern. Policy R6.",
                ),
                ActionRecommendation(
                    action=ActionType.MONITOR_CONNECTED_CARDS, route=ApprovalRoute.auto,
                    reason="Monitor all cards sharing device. Policy R6.",
                ),
            ]

        # R1: weak signal — verify before blocking
        if fraud_probability < 0.70 and num_signals <= 1:
            if not actions:
                actions.append(ActionRecommendation(
                    action=ActionType.VERIFY_WITH_CUSTOMER, route=ApprovalRoute.auto,
                    reason=f"p={fraud_probability:.2f} < 0.70 with {num_signals} signal. Policy R1.",
                ))
            return actions

        # R8: uncertain + exposed
        if 0.30 < fraud_probability < 0.85 and exposure_usd > 500:
            actions.append(ActionRecommendation(
                action=ActionType.ESCALATE_TO_ANALYST, route=ApprovalRoute.auto,
                reason=f"Uncertain (p={fraud_probability:.2f}) + exposure ${exposure_usd:.2f} > $500. R8.",
            ))

        # High confidence fraud
        if fraud_probability >= 0.85 and confidence >= 0.60:
            if not any(a.action == ActionType.CREATE_CASE for a in actions):
                actions.append(ActionRecommendation(
                    action=ActionType.CREATE_CASE, route=ApprovalRoute.auto,
                    reason=f"High fraud probability {fraud_probability:.2f}.",
                ))
            actions.append(ActionRecommendation(
                action=ActionType.BLOCK_CARD,
                route=get_route(ActionType.BLOCK_CARD, exposure_usd),
                reason=f"Confirmed fraud p={fraud_probability:.2f}. Block card.",
            ))
            if exposure_usd > 1000 or num_shared_devices > 0:
                actions.append(ActionRecommendation(
                    action=ActionType.FILE_REPORT, route=ApprovalRoute.L2,
                    reason=f"Exposure ${exposure_usd:.2f} > $1000 or shared device. File SAR.",
                ))
        elif fraud_probability >= 0.40:
            if not any(a.action == ActionType.MONITOR_CARD for a in actions):
                actions.append(ActionRecommendation(
                    action=ActionType.MONITOR_CARD, route=ApprovalRoute.auto,
                    reason=f"Medium risk p={fraud_probability:.2f}. Monitor card.",
                ))
            if not any(a.action == ActionType.STEP_UP_AUTH for a in actions):
                actions.append(ActionRecommendation(
                    action=ActionType.STEP_UP_AUTH, route=ApprovalRoute.auto,
                    reason="Medium risk — require step-up before further transactions.",
                ))
        else:
            if not actions:
                actions.append(ActionRecommendation(
                    action=ActionType.ALLOW_TRANSACTION, route=ApprovalRoute.auto,
                    reason=f"Low fraud probability p={fraud_probability:.2f} < 0.40. Allow.",
                ))

        # R9: undocumented pattern
        if pattern == FraudPattern.undocumented:
            action_set = {a.action for a in actions}
            for act, reason in [
                (ActionType.CREATE_CASE, "Undocumented pattern. Policy R9."),
                (ActionType.FILE_REPORT, "Undocumented coordinated pattern. Policy R9."),
                (ActionType.ESCALATE_TO_ANALYST, "Undocumented pattern needs analyst. R9."),
            ]:
                if act not in action_set:
                    actions.append(ActionRecommendation(
                        action=act,
                        route=get_route(act, exposure_usd),
                        reason=reason,
                    ))

        return actions

    def requires_sar(self, actions: list[ActionRecommendation]) -> bool:
        return any(a.action == ActionType.FILE_REPORT for a in actions)

    def get_stopping_reason(
        self,
        fraud_probability: float,
        confidence: float,
        customer_response: str | None,
        num_evidence: int,
    ) -> str | None:
        if customer_response in ("confirmed", "denied"):
            return f"Customer response '{customer_response}' settled the question."
        if fraud_probability >= 0.85 and num_evidence >= 2:
            return (
                f"Fraud probability {fraud_probability:.2f} >= 0.85 with "
                f"{num_evidence} independent evidence pieces (Policy section 6)."
            )
        if fraud_probability <= 0.15 and num_evidence >= 2:
            return (
                f"Fraud probability {fraud_probability:.2f} <= 0.15 with "
                f"{num_evidence} independent evidence pieces (Policy section 6)."
            )
        return None
