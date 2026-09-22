"""Deterministic approval routing from Fraud Policy v1.0."""

from .actions import Action, Route

AUTO_ACTIONS = {
    Action.ALLOW_TRANSACTION,
    Action.MONITOR_CARD,
    Action.MONITOR_CONNECTED_CARDS,
    Action.WARN_CUSTOMER,
    Action.VERIFY_WITH_CUSTOMER,
    Action.STEP_UP_AUTH,
    Action.GENERATE_REPORT,
    Action.CREATE_CASE,
    Action.ESCALATE_TO_ANALYST,
    Action.CLOSE_NO_FRAUD,
}


def route_for_action(action: Action, exposure_usd: float) -> Route:
    if action in AUTO_ACTIONS:
        return Route.AUTO
    if action == Action.DECLINE_TRANSACTION:
        return Route.L1
    if action == Action.BLOCK_CARD:
        return Route.L1 if exposure_usd <= 2500 else Route.L2
    if action in {Action.BLOCK_ALL_CARDS, Action.FILE_REPORT}:
        return Route.L2
    raise ValueError(f"unsupported policy action: {action}")