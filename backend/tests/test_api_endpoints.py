"""
Integration tests for backend API routes verifying end-to-end communication
between FastAPI endpoints and client expectations.
"""

import json

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.api import investigations
from app.cases import case_manager
from app.cases.case_manager import CaseManager
from app.models.case import (
    ActionRecommendation,
    ActionType,
    ApprovalRoute,
    CaseAnswer,
    CaseRecord,
    CaseStatus,
    FraudPattern,
    LifecycleState,
    NextBestActions,
    SAR,
    Verdict,
)


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def seed_test_case():
    """Ensure a deterministic test case exists in CaseManager."""
    mgr = CaseManager()
    test_case = CaseAnswer(
        case_id="HHG-999",
        trigger={
            "case_id": "HHG-999",
            "trigger_type": "risk_score",
            "trigger_text": "High risk anomaly score on card test",
            "flagged_txn_id": "9990001",
            "card_id": "C99999-K1",
            "customer_id": "C99999",
            "risk_score": 0.92,
        },
        case=CaseRecord(
            status=CaseStatus.open,
            verdict=Verdict.fraud,
            fraud_probability=0.92,
            pattern=FraudPattern.card_testing,
            pattern_description="Micro transactions followed by burst",
            affected_txn_ids=["9990001", "9990002"],
            first_suspicious_txn_id="9990001",
            connected_card_ids=["C99999-K2"],
            connected_device_profiles=["Linux | Chrome 54 | 1920x1080"],
            exposure_usd=1250.50,
            evidence=[],
            similar_prior_cases=["CC-1001"],
            summary="Confirmed card testing scenario.",
            written_to_graph=True,
            graph_case_id="graph_HHG_999",
        ),
        next_best_actions=NextBestActions(
            initial=[
                ActionRecommendation(
                    action=ActionType.DECLINE_TRANSACTION,
                    route=ApprovalRoute.L1,
                    reason="Card testing detected. Policy R5.",
                )
            ],
            final=[
                ActionRecommendation(
                    action=ActionType.BLOCK_CARD,
                    route=ApprovalRoute.L1,
                    reason="Card testing confirmed. Policy R5.",
                ),
                ActionRecommendation(
                    action=ActionType.FILE_REPORT,
                    route=ApprovalRoute.L2,
                    reason="Exposure > $1000. Policy R2.",
                ),
            ],
            what_changed="Added block and SAR after exposure calculation.",
        ),
        sar=SAR(
            file=True,
            reason="Card testing above $1,000 threshold",
            narrative="Suspicious card testing activity identified on account C99999.",
            subjects=["C99999", "C99999-K1"],
            total_amount_usd=1250.50,
            activity_dates=["2016-11-12", "2016-11-13"],
        ),
        stop_reason="High probability and independent evidence criteria met.",
        tool_calls=5,
        tokens=1800,
        latency_s=1.2,
        lifecycle_state=LifecycleState.awaiting_approval,
    )
    mgr.save_answer(test_case)
    return test_case


def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "tigergraph" in data
    assert "mcp" in data
    assert "llm" in data
    assert "data_loaded" in data


def test_list_case_pack(client):
    response = client.get("/cases/pack")
    assert response.status_code == 200
    data = response.json()
    assert "cases" in data
    assert isinstance(data["cases"], list)


def test_list_cases(client):
    response = client.get("/cases?limit=10")
    assert response.status_code == 200
    data = response.json()
    assert "cases" in data
    assert isinstance(data["cases"], list)

    # Test full mode
    response_full = client.get("/cases?full=true&limit=10")
    assert response_full.status_code == 200
    assert "cases" in response_full.json()


def test_get_case_stats(client):
    response = client.get("/cases/stats")
    assert response.status_code == 200
    stats = response.json()
    assert "total_cases" in stats
    assert "verdict_distribution" in stats
    assert "f1_score" in stats
    assert "policy_compliance_rate" in stats
    assert "average_latency_s" in stats


def test_get_case_detail(client):
    response = client.get("/cases/HHG-999")
    assert response.status_code == 200
    data = response.json()
    assert data["case_id"] == "HHG-999"
    assert data["case"]["verdict"] == "fraud"


def test_get_case_not_found(client):
    response = client.get("/cases/NONEXISTENT_CASE")
    assert response.status_code == 404


def test_get_case_subresources(client):
    # SAR
    sar_resp = client.get("/cases/HHG-999/sar")
    assert sar_resp.status_code == 200
    assert sar_resp.json()["file"] is True

    # Evidence
    ev_resp = client.get("/cases/HHG-999/evidence")
    assert ev_resp.status_code == 200
    assert "evidence" in ev_resp.json()

    # Transactions
    txn_resp = client.get("/cases/HHG-999/transactions")
    assert txn_resp.status_code == 200
    assert "affected_txn_ids" in txn_resp.json()
    assert txn_resp.json()["exposure_usd"] == 1250.50

    # Related cases
    rel_resp = client.get("/cases/HHG-999/related-cases")
    assert rel_resp.status_code == 200
    assert "similar_prior_cases" in rel_resp.json()

    # Graph
    graph_resp = client.get("/cases/HHG-999/graph")
    assert graph_resp.status_code == 200
    assert graph_resp.json()["written_to_graph"] is True

    # Audit
    audit_resp = client.get("/cases/HHG-999/audit")
    assert audit_resp.status_code == 200
    assert "audit" in audit_resp.json()


def test_evidence_request_and_response_lifecycle(client):
    # Create evidence request
    create_resp = client.post(
        "/cases/HHG-999/evidence-requests",
        json={
            "evidence_type": "customer_validation",
            "reason": "Verify transaction with cardholder",
            "investigation_step": 3,
        },
    )
    assert create_resp.status_code == 200
    req_data = create_resp.json()
    req_id = req_data["request_id"]
    assert req_data["type"] == "customer_validation"

    # Fulfill response
    fulfill_resp = client.post(
        "/cases/HHG-999/evidence-responses",
        json={
            "request_id": req_id,
            "source": "customer",
            "response": {"user_confirmed": False, "notes": "Disputed micro transactions"},
        },
    )
    assert fulfill_resp.status_code in (200, 409)


def test_action_governance_lifecycle(client):
    # Action approve
    approve_resp = client.post("/cases/HHG-999/actions/BLOCK_CARD/approve")
    assert approve_resp.status_code == 200
    assert approve_resp.json()["approved"] is True

    # Action execute
    exec_resp = client.post("/cases/HHG-999/actions/BLOCK_CARD/execute")
    assert exec_resp.status_code == 200
    assert exec_resp.json()["executed"] is True

    # Action reject
    reject_resp = client.post("/cases/HHG-999/actions/FILE_REPORT/reject")
    assert reject_resp.status_code == 200
    assert reject_resp.json()["rejected"] is True


def test_policy_rules_and_actions(client):
    rules_resp = client.get("/policy/rules")
    assert rules_resp.status_code == 200
    rules = rules_resp.json()["rules"]
    assert len(rules) == 10
    rule_ids = [r["id"] for r in rules]
    assert "R1" in rule_ids
    assert "R10" in rule_ids

    actions_resp = client.get("/policy/actions")
    assert actions_resp.status_code == 200
    actions_data = actions_resp.json()
    assert "routes" in actions_data
    assert "auto_actions" in actions_data
    assert len(actions_data["routes"]) > 0


def test_investigations_endpoints(client):
    # Retrieve investigation by ID
    inv_resp = client.get("/investigations/HHG-999")
    assert inv_resp.status_code == 200
    assert inv_resp.json()["case_id"] == "HHG-999"

    # 404 for missing investigation
    not_found = client.get("/investigations/UNKNOWN_INV_ID")
    assert not_found.status_code == 404


def test_investigation_reuses_cached_answer(client, seed_test_case, monkeypatch):
    """A repeated run must not invoke the agent or consume another LLM call."""
    class Pack:
        @staticmethod
        def get_case_pack_row(case_id):
            return {"case_id": case_id}

    class AgentMustNotRun:
        async def investigate(self, _row):
            raise AssertionError("cached investigation should not run the agent")

    monkeypatch.setattr(investigations, "get_data_layer", lambda: Pack())
    monkeypatch.setattr(investigations, "FraudAgent", AgentMustNotRun)
    monkeypatch.setattr(investigations._mgr, "get_answer", lambda _case_id: seed_test_case)

    response = client.post("/investigations/run", json={"case_id": "HHG-001"})

    assert response.status_code == 200
    assert response.json()["case_id"] == "HHG-999"


def test_run_all_reports_cached_cases(client, seed_test_case, monkeypatch):
    class Pack:
        @staticmethod
        def get_all_case_pack_rows():
            return [{"case_id": "HHG-001"}, {"case_id": "HHG-002"}]

    class AgentMustNotRun:
        async def investigate(self, _row):
            raise AssertionError("cached batch cases should not run the agent")

    monkeypatch.setattr(investigations, "get_data_layer", lambda: Pack())
    monkeypatch.setattr(investigations, "FraudAgent", AgentMustNotRun)
    monkeypatch.setattr(investigations._mgr, "get_answer", lambda _case_id: seed_test_case)

    response = client.post("/investigations/run-all", json={})

    assert response.status_code == 200
    assert response.json()["completed"] == 0
    assert response.json()["cached"] == 2
    assert response.json()["failed"] == 0


def test_saved_answer_is_exported_as_json(seed_test_case, monkeypatch, tmp_path):
    monkeypatch.setattr(case_manager, "OUTPUT_DIR", tmp_path)

    CaseManager().save_answer(seed_test_case)

    artifact = tmp_path / "HHG-999.json"
    assert artifact.exists()
    document = json.loads(artifact.read_text(encoding="utf-8"))
    assert document["case_id"] == "HHG-999"
    assert document["case"]["verdict"] == "fraud"
    assert "runtime" not in document
