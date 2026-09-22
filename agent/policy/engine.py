"""Rule evaluation for Fraud Policy v1.0.

This module computes permitted recommendations from structured evidence. It
does not accept free-form model actions, so an LLM cannot bypass routing or
the R10 guardrail.
"""

from __future__ import annotations

from typing import NamedTuple

from .actions import Action, ActionRec, Route
from .router import route_for_action


class CaseContext(NamedTuple):
    verdict: str
    fraud_probability: float
    evidence_count: int
    exposure_usd: float
    is_single_signal: bool
    customer_response: str | None
    pattern: str | None
    shared_entity: dict | None
    recurring_match: bool
    coordinated_undocumented: bool
    confirmed_fraud_card_count: int
    credentials_confirmed_compromised: bool
    large_purchase_cleared: bool = False
    evidence_conflicts: bool = False


class PolicyResult(NamedTuple):
    actions: list[ActionRec]
    stop: bool
    stop_reason: str | None


def _rec(action: Action, context: CaseContext, reason: str) -> ActionRec:
    return ActionRec(action, route_for_action(action, context.exposure_usd), reason)


def _has_action(actions: list[ActionRec], action: Action) -> bool:
    return any(item.action == action for item in actions)


def evaluate(context: CaseContext) -> PolicyResult:
    actions: list[ActionRec] = []

    # R7 is deliberately evaluated first: a recurring disputed charge must
    # suppress the otherwise applicable denial/block path in R2.
    if context.recurring_match:
        actions.extend([
            _rec(Action.CREATE_CASE, context, "R7: disputed charge matches the customer's recurring pattern"),
            _rec(Action.VERIFY_WITH_CUSTOMER, context, "R7: verify the recurring charge with the customer"),
            _rec(Action.WARN_CUSTOMER, context, "R7: warn the customer about the recurring-charge dispute"),
        ])
    elif context.customer_response == "confirmed":
        actions.extend([
            _rec(Action.CREATE_CASE, context, "R3: evidence request opened an investigation record"),
            _rec(Action.CLOSE_NO_FRAUD, context, "R3: customer confirmed the transaction"),
        ])
    elif context.customer_response == "denied":
        actions.extend([
            _rec(Action.BLOCK_CARD, context, "R2: customer denied the transaction"),
            _rec(Action.CREATE_CASE, context, "R2: customer denial requires a fraud case"),
        ])
        if context.exposure_usd > 1000 or context.shared_entity is not None:
            actions.append(_rec(Action.FILE_REPORT, context, "R2: denial exceeds the report threshold or connects to shared activity"))
    elif context.customer_response == "no_reply":
        actions.extend([
            _rec(Action.MONITOR_CARD, context, "R4: no reply within 24 hours"),
            _rec(Action.DECLINE_TRANSACTION, context, "R4: decline pending authorizations after no reply"),
        ])
        if context.exposure_usd > 500:
            actions.append(_rec(Action.ESCALATE_TO_ANALYST, context, "R4: no reply with exposure above $500"))
    elif context.pattern == "card_testing":
        actions.extend([
            _rec(Action.DECLINE_TRANSACTION, context, "R5: card-testing sequence requires declining the authorization"),
            _rec(Action.STEP_UP_AUTH, context, "R5: card-testing sequence requires step-up authentication"),
        ])
        if context.large_purchase_cleared or context.exposure_usd > 100:
            actions.append(_rec(Action.BLOCK_CARD, context, "R5: a purchase over $100 has already cleared"))
    elif context.is_single_signal and context.fraud_probability < 0.70:
        actions.append(_rec(Action.VERIFY_WITH_CUSTOMER, context, "R1: single signal below 0.70 requires verification before blocking"))

    if context.shared_entity is not None and context.verdict == "fraud":
        entity_type = context.shared_entity.get("type", "shared entity")
        if not _has_action(actions, Action.CREATE_CASE):
            actions.append(_rec(Action.CREATE_CASE, context, f"R6: coordinated fraud shares a {entity_type}"))
        if not _has_action(actions, Action.FILE_REPORT):
            actions.append(_rec(Action.FILE_REPORT, context, f"R6: shared {entity_type} connects multiple cards"))
        actions.append(_rec(Action.MONITOR_CONNECTED_CARDS, context, f"R6: monitor cards sharing the {entity_type}"))

    if context.coordinated_undocumented:
        if not _has_action(actions, Action.CREATE_CASE):
            actions.append(_rec(Action.CREATE_CASE, context, "R9: coordinated activity does not fit a documented pattern"))
        if not _has_action(actions, Action.FILE_REPORT):
            actions.append(_rec(Action.FILE_REPORT, context, "R9: coordinated undocumented activity requires a report"))
        actions.append(_rec(Action.ESCALATE_TO_ANALYST, context, "R9: undocumented coordinated activity requires analyst review"))

    if context.verdict == "uncertain" and (context.exposure_usd > 500 or context.evidence_conflicts):
        if not _has_action(actions, Action.ESCALATE_TO_ANALYST):
            actions.append(_rec(Action.ESCALATE_TO_ANALYST, context, "R8: uncertainty remains with material exposure or conflicting evidence"))

    case_required = (
        context.fraud_probability >= 0.30
        or context.customer_response is not None
        or context.recurring_match
        or bool(actions)
    )
    if case_required and not _has_action(actions, Action.CREATE_CASE):
        actions.append(_rec(Action.CREATE_CASE, context, "R3a: case required by probability or requested evidence"))

    if context.confirmed_fraud_card_count >= 2 or context.credentials_confirmed_compromised:
        if context.verdict == "fraud":
            actions.append(_rec(Action.BLOCK_ALL_CARDS, context, "R10: two other cards are confirmed fraud or credentials are compromised"))

    settled = context.customer_response in {"confirmed", "denied", "no_reply"}
    extreme = context.evidence_count >= 2 and (
        context.fraud_probability >= 0.85 or context.fraud_probability <= 0.15
    )
    stop = settled or extreme
    if settled:
        stop_reason = f"Customer response '{context.customer_response}' settled the question."
    elif extreme:
        stop_reason = "Probability crossed a policy threshold with at least two independent evidence items."
    else:
        stop_reason = None
    return PolicyResult(actions=actions, stop=stop, stop_reason=stop_reason)