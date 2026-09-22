"""Lifecycle, reassessment, and action-governance regression tests."""

import pytest

from app.agents.fraud_agent import FraudAgent
from app.cases.state_machine import transition
from app.models.case import (
    ActionRecommendation,
    ActionType,
    ApprovalRoute,
    CaseAnswer,
    EvidenceRequest,
    EvidenceRequestType,
    LifecycleState,
)


def test_closed_case_cannot_reopen():
    with pytest.raises(ValueError):
        transition(LifecycleState.closed, LifecycleState.investigating)


def test_awaiting_evidence_can_reassess():
    transition(LifecycleState.awaiting_external_evidence, LifecycleState.reassessing)


def test_external_evidence_changes_reassessment():
    answer = CaseAnswer(
        case_id="TEST-LIFECYCLE",
        trigger={"type": "customer_report", "transaction_id": "txn-1"},
        evidence_requests=[EvidenceRequest(
            request_id="req-1",
            type=EvidenceRequestType.customer_validation,
            asked_after_step=7,
            reason="Authorization is unresolved",
        )],
        next_best_actions={
            "initial": [],
            "final": [ActionRecommendation(
                action=ActionType.MONITOR_CARD,
                route=ApprovalRoute.auto,
                reason="Initial monitoring",
            )],
        },
    )
    answer.case.fraud_probability = 0.55

    result = FraudAgent().reassess_answer(
        answer, "req-1", {"outcome": "denied", "detail": "Customer denied transaction"}
    )

    assert result.case.fraud_probability == 0.8
    assert result.evidence_requests[0].status == "fulfilled"
    assert result.reassessment_history[0]["risk_before"] == 0.55
    assert result.reassessment_history[0]["risk_after"] == 0.8
    assert result.validation["external_evidence_grounded"] is True
