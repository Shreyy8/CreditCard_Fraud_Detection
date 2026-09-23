"""Business case lifecycle transition guard."""

from __future__ import annotations

from ..models.case import LifecycleState

ALLOWED_TRANSITIONS: dict[LifecycleState, set[LifecycleState]] = {
    LifecycleState.new: {LifecycleState.investigating},
    LifecycleState.investigating: {
        LifecycleState.awaiting_external_evidence,
        LifecycleState.ready_for_action,
        LifecycleState.escalated,
        LifecycleState.failed,
    },
    LifecycleState.awaiting_external_evidence: {
        LifecycleState.reassessing,
        LifecycleState.failed,
    },
    LifecycleState.reassessing: {
        LifecycleState.awaiting_external_evidence,
        LifecycleState.ready_for_action,
        LifecycleState.escalated,
        LifecycleState.failed,
    },
    LifecycleState.ready_for_action: {
        LifecycleState.awaiting_approval,
        LifecycleState.action_executing,
        LifecycleState.escalated,
    },
    LifecycleState.awaiting_approval: {
        LifecycleState.action_executing,
        LifecycleState.escalated,
        LifecycleState.closed,
        LifecycleState.awaiting_external_evidence,
    },
    LifecycleState.action_executing: {
        LifecycleState.action_executed,
        LifecycleState.action_failed,
    },
    LifecycleState.action_executed: {
        LifecycleState.closed,
        LifecycleState.awaiting_approval,
        LifecycleState.action_executing,
    },
    LifecycleState.action_failed: {LifecycleState.escalated},
    LifecycleState.escalated: {
        LifecycleState.investigating,
        LifecycleState.closed,
        LifecycleState.awaiting_approval,
    },
    LifecycleState.closed: {LifecycleState.awaiting_approval},
    LifecycleState.failed: set(),
}


def transition(current: LifecycleState, target: LifecycleState) -> None:
    if current == target:
        return
    if target not in ALLOWED_TRANSITIONS.get(current, set()):
        raise ValueError(f"Invalid case transition: {current.value} -> {target.value}")