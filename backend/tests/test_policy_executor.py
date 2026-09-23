import pytest

from app.models.case import ActionRecommendation, ActionType, ApprovalRoute
from app.policy.executor import ActionExecutionError, PolicyActionExecutor


def test_auto_action_executes():
    result = PolicyActionExecutor().execute(ActionRecommendation(
        action=ActionType.MONITOR_CARD,
        route=ApprovalRoute.auto,
        reason="monitor",
    ))
    assert result["status"] == "executed"


def test_l2_action_cannot_execute():
    with pytest.raises(ActionExecutionError):
        PolicyActionExecutor().execute(ActionRecommendation(
            action=ActionType.FILE_REPORT,
            route=ApprovalRoute.L2,
            reason="report",
        ))