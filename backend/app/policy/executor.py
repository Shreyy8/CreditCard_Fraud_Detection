"""Permission boundary for executing policy recommendations."""

from __future__ import annotations

from ..models.case import ActionRecommendation, ActionType, ApprovalRoute


class ActionExecutionError(ValueError):
    pass


class PolicyActionExecutor:
    """Execute only auto-routed actions; queue L1/L2 for human approval."""

    def execute(self, recommendation: ActionRecommendation) -> dict[str, str]:
        if recommendation.route != ApprovalRoute.auto:
            raise ActionExecutionError(
                f"{recommendation.action.value} requires {recommendation.route.value} approval"
            )
        return {
            "action": recommendation.action.value,
            "status": "executed",
            "route": recommendation.route.value,
        }

    def approval_request(self, recommendation: ActionRecommendation) -> dict[str, str]:
        if recommendation.route == ApprovalRoute.auto:
            raise ActionExecutionError("Auto actions do not require approval")
        return {
            "action": recommendation.action.value,
            "status": "awaiting_approval",
            "route": recommendation.route.value,
            "reason": recommendation.reason,
        }