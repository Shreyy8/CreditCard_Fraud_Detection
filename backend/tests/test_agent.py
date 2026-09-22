"""
Integration tests for the fraud agent workflow.
These tests run without TigerGraph connectivity.
"""

import asyncio
import pytest
from app.agents.fraud_agent import FraudAgent
from app.models.case import CaseStatus, Verdict, FraudPattern


@pytest.fixture
def sample_case_row():
    return {
        "case_id": "HHG-001",
        "opened_at": "2016-12-05 01:55:28",
        "trigger_type": "risk_score",
        "trigger_text": "Real-time model scored transaction 3514030 ($77.07) at 0.61. Review.",
        "flagged_txn_id": "3514030",
        "card_id": "C12382-K1",
        "customer_id": "C12382",
        "risk_score": "0.61",
    }


@pytest.fixture
def customer_report_row():
    return {
        "case_id": "HHG-003",
        "opened_at": "2016-12-10 15:01:21",
        "trigger_type": "customer_report",
        "trigger_text": "Customer C08623 message: 'I never made this $49.00 purchase.'",
        "flagged_txn_id": "3530164",
        "card_id": "C08623-K2",
        "customer_id": "C08623",
        "risk_score": "",
    }


class TestFraudAgentWorkflow:
    def test_investigation_returns_case_answer(self, sample_case_row):
        agent = FraudAgent()
        answer = asyncio.run(agent.investigate(sample_case_row))
        assert answer.case_id == "HHG-001"
        assert answer.case.status is not None
        assert answer.case.verdict is not None
        assert 0.0 <= answer.case.fraud_probability <= 1.0
        assert answer.case.pattern is not None

    def test_answer_has_all_required_fields(self, sample_case_row):
        agent = FraudAgent()
        answer = asyncio.run(agent.investigate(sample_case_row))
        # Required top-level fields from Answer Format
        assert answer.case_id
        assert answer.case is not None
        assert answer.next_best_actions is not None
        assert answer.sar is not None
        assert answer.stop_reason
        assert isinstance(answer.tool_calls, int)
        assert isinstance(answer.latency_s, float)

    def test_customer_report_triggers_evidence_request(self, customer_report_row):
        agent = FraudAgent()
        answer = asyncio.run(agent.investigate(customer_report_row))
        # Customer report should result in evidence request
        assert len(answer.evidence_requests) > 0

    def test_before_after_actions_when_evidence_requested(self, customer_report_row):
        agent = FraudAgent()
        answer = asyncio.run(agent.investigate(customer_report_row))
        # Both initial and final should be populated
        assert len(answer.next_best_actions.initial) > 0
        assert len(answer.next_best_actions.final) > 0

    def test_sar_required_for_customer_denial(self, customer_report_row):
        """Customer denial + evidence should trigger SAR assessment."""
        agent = FraudAgent()
        answer = asyncio.run(agent.investigate(customer_report_row))
        # If SAR filed, it should have all required fields
        if answer.sar.file:
            assert answer.sar.narrative
            assert len(answer.sar.subjects) > 0
            assert answer.sar.total_amount_usd >= 0
            assert len(answer.sar.activity_dates) == 2

    def test_sar_not_filed_has_empty_narrative(self, sample_case_row):
        agent = FraudAgent()
        answer = asyncio.run(agent.investigate(sample_case_row))
        if not answer.sar.file:
            assert answer.sar.narrative == ""
            assert answer.sar.subjects == []
            assert answer.sar.total_amount_usd == 0

    def test_affected_txn_ids_always_includes_flagged(self, sample_case_row):
        agent = FraudAgent()
        answer = asyncio.run(agent.investigate(sample_case_row))
        assert sample_case_row["flagged_txn_id"] in answer.case.affected_txn_ids

    def test_evidence_not_empty(self, sample_case_row):
        agent = FraudAgent()
        answer = asyncio.run(agent.investigate(sample_case_row))
        # Should always have at least one evidence item (trigger itself)
        assert len(answer.case.evidence) >= 1

    def test_all_actions_have_routes(self, sample_case_row):
        agent = FraudAgent()
        answer = asyncio.run(agent.investigate(sample_case_row))
        for action in answer.next_best_actions.final:
            assert action.route is not None
            assert action.reason

    def test_analyst_request_trigger(self):
        row = {
            "case_id": "HHG-014",
            "opened_at": "2016-11-22 20:11:00",
            "trigger_type": "analyst_request",
            "trigger_text": "Analyst request: several cards this month show purchases from same device.",
            "flagged_txn_id": "3478561",
            "card_id": "C13487-K1",
            "customer_id": "C13487",
            "risk_score": "",
        }
        agent = FraudAgent()
        answer = asyncio.run(agent.investigate(row))
        assert answer.case_id == "HHG-014"
        assert answer.case.status is not None


class TestDataLayer:
    def test_data_loads(self):
        from app.data_layer import get_data_layer
        dl = get_data_layer()
        assert len(dl.case_pack) == 20
        assert len(dl.closed_cases) > 0

    def test_transaction_lookup(self):
        from app.data_layer import get_data_layer
        dl = get_data_layer()
        # Transaction IDs from case pack
        txn = dl.get_transaction("3514030")
        if txn:  # May or may not be in the limited CSV
            assert txn.get("TransactionID") == "3514030"

    def test_closed_case_lookup(self):
        from app.data_layer import get_data_layer
        dl = get_data_layer()
        case = dl.closed_cases.get("CC-0001")
        assert case is not None
        assert case.get("outcome") in ("confirmed_fraud", "cleared")

    def test_case_pack_has_20_cases(self):
        from app.data_layer import get_data_layer
        dl = get_data_layer()
        rows = dl.get_all_case_pack_rows()
        assert len(rows) == 20
        case_ids = {r["case_id"] for r in rows}
        for i in range(1, 21):
            assert f"HHG-{i:03d}" in case_ids


class TestSARGenerator:
    def test_sar_narrative_has_required_sections(self, customer_report_row):
        agent = FraudAgent()
        answer = asyncio.run(agent.investigate(customer_report_row))
        if answer.sar.file:
            narrative = answer.sar.narrative
            # FinCEN requires: who, what, when, where, how, why
            assert "WHO" in narrative or "customer" in narrative.lower()
            assert "WHAT" in narrative or "transaction" in narrative.lower()
            assert "WHEN" in narrative or "20" in narrative  # Year 2016
