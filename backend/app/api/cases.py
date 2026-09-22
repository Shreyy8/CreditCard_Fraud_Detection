"""Cases API — CRUD and lifecycle management."""

from fastapi import APIRouter, HTTPException
from ..cases.case_manager import CaseManager
from ..models.case import CaseAnswer, ActionType, EvidenceRequestType
from ..agents.fraud_agent import FraudAgent
from ..cases.state_machine import transition

router = APIRouter(prefix="/cases", tags=["cases"])
_mgr = CaseManager()


@router.get("")
async def list_cases(limit: int = 50):
    return {"cases": _mgr.list_cases(limit)}


@router.get("/{case_id}")
async def get_case(case_id: str):
    ans = _mgr.get_answer(case_id)
    if not ans:
        raise HTTPException(404, f"Case {case_id} not found")
    return ans


@router.get("/{case_id}/sar")
async def get_sar(case_id: str):
    ans = _mgr.get_answer(case_id)
    if not ans:
        raise HTTPException(404, f"Case {case_id} not found")
    return ans.sar


@router.get("/{case_id}/evidence")
async def get_evidence(case_id: str):
    ans = _mgr.get_answer(case_id)
    if not ans:
        raise HTTPException(404, f"Case {case_id} not found")
    return {"evidence": ans.case.evidence, "evidence_requests": ans.evidence_requests}


@router.get("/{case_id}/transactions")
async def get_transactions(case_id: str):
    ans = _mgr.get_answer(case_id)
    if not ans:
        raise HTTPException(404, f"Case {case_id} not found")
    return {
        "affected_txn_ids": ans.case.affected_txn_ids,
        "exposure_usd": ans.case.exposure_usd,
    }


@router.get("/{case_id}/related-cases")
async def get_related_cases(case_id: str):
    ans = _mgr.get_answer(case_id)
    if not ans:
        raise HTTPException(404, f"Case {case_id} not found")
    return {"similar_prior_cases": ans.case.similar_prior_cases}


@router.get("/{case_id}/graph")
async def get_graph(case_id: str):
    ans = _mgr.get_answer(case_id)
    if not ans:
        raise HTTPException(404, f"Case {case_id} not found")
    return {
        "written_to_graph": ans.case.written_to_graph,
        "graph_case_id": ans.case.graph_case_id,
        "connected_card_ids": ans.case.connected_card_ids,
        "connected_device_profiles": ans.case.connected_device_profiles,
    }


@router.get("/{case_id}/audit")
async def get_audit(case_id: str):
    if not _mgr.get_answer(case_id):
        raise HTTPException(404, f"Case {case_id} not found")
    return {"case_id": case_id, "audit": _mgr.get_audit(case_id)}


@router.post("/{case_id}/evidence-requests")
async def create_evidence_request(case_id: str, body: dict):
    answer = _mgr.get_answer(case_id)
    if not answer:
        raise HTTPException(404, f"Case {case_id} not found")
    try:
        evidence_type = EvidenceRequestType(body.get("evidence_type", "analyst_info"))
    except ValueError as exc:
        raise HTTPException(422, "Invalid evidence_type") from exc
    request = {
        "type": evidence_type.value,
        "asked_after_step": body.get("investigation_step", len(answer.audit)),
        "requested_from": body.get("requested_from", "external_provider"),
        "reason": body.get("reason", "Additional evidence required."),
    }
    from ..models.case import EvidenceRequest
    model = EvidenceRequest(**request)
    answer.evidence_requests.append(model)
    if answer.lifecycle_state != answer.lifecycle_state.awaiting_external_evidence:
        try:
            transition(answer.lifecycle_state, answer.lifecycle_state.awaiting_external_evidence)
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from exc
        answer.lifecycle_state = answer.lifecycle_state.awaiting_external_evidence
    _mgr.save_answer(answer)
    _mgr.log_audit(case_id, [{
        "step": model.asked_after_step, "action": "evidence_requested", "status": "pending",
        "request_id": model.request_id, "evidence_type": model.type.value,
        "reason": model.reason, "actor": "AGENT",
    }])
    return model


@router.post("/{case_id}/evidence-responses")
async def receive_evidence_response(case_id: str, body: dict):
    answer = _mgr.get_answer(case_id)
    if not answer:
        raise HTTPException(404, f"Case {case_id} not found")
    request_id = body.get("request_id", "")
    request = _mgr.get_evidence_request(request_id)
    if not request or request["case_id"] != case_id:
        raise HTTPException(404, "Evidence request not found for case")
    if request["status"] != "pending":
        raise HTTPException(409, "Evidence request is already fulfilled")
    response = body.get("response")
    if not isinstance(response, dict) or not body.get("source"):
        raise HTTPException(422, "response object and trusted source are required")
    try:
        if answer.lifecycle_state != answer.lifecycle_state.reassessing:
            transition(answer.lifecycle_state, answer.lifecycle_state.reassessing)
            answer.lifecycle_state = answer.lifecycle_state.reassessing
        reassessed = FraudAgent().reassess_answer(answer, request_id, {
            **response, "source": body["source"], "received_at": body.get("received_at", "")
        })
        _mgr.fulfill_evidence_request(request_id, response, body.get("received_at", ""))
        _mgr.save_answer(reassessed)
        _mgr.log_audit(case_id, [{
            "step": 8, "action": "evidence_received", "status": "complete",
            "request_id": request_id, "source": body["source"], "actor": "EXTERNAL_PROVIDER",
        }, *reassessed.audit[-1:]])
        return reassessed
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc


@router.post("/{case_id}/actions/{action_id}/approve")
async def approve_action(case_id: str, action_id: str):
    ans = _mgr.get_answer(case_id)
    if not ans:
        raise HTTPException(404, f"Case {case_id} not found")
    try:
        ActionType(action_id)
    except ValueError as exc:
        raise HTTPException(400, f"Unknown action: {action_id}") from exc
    available = {a.action.value for a in ans.next_best_actions.final}
    if action_id not in available:
        raise HTTPException(409, f"Action {action_id} is not recommended for this case")
    if ans.lifecycle_state != ans.lifecycle_state.awaiting_approval:
        try:
            transition(ans.lifecycle_state, ans.lifecycle_state.awaiting_approval)
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from exc
        ans.lifecycle_state = ans.lifecycle_state.awaiting_approval
    ans.action_decisions[action_id] = {
        "status": "approved",
        "execution_mode": "SIMULATED",
    }
    ans.lifecycle_state = ans.lifecycle_state.awaiting_approval
    _mgr.update_answer(ans)
    _mgr.log_audit(case_id, [{
        "step": 12, "action": "approval", "status": "approved",
        "action_id": action_id, "execution_mode": "SIMULATED",
    }])
    return {"approved": True, "case_id": case_id, "action": action_id,
            "execution_mode": "SIMULATED"}


@router.post("/{case_id}/actions/{action_id}/reject")
async def reject_action(case_id: str, action_id: str):
    ans = _mgr.get_answer(case_id)
    if not ans:
        raise HTTPException(404, f"Case {case_id} not found")
    if action_id not in {a.action.value for a in ans.next_best_actions.final}:
        raise HTTPException(409, f"Action {action_id} is not recommended for this case")
    ans.action_decisions[action_id] = {
        "status": "rejected",
        "execution_mode": "SIMULATED",
    }
    _mgr.update_answer(ans)
    _mgr.log_audit(case_id, [{
        "step": 12, "action": "approval", "status": "rejected",
        "action_id": action_id, "execution_mode": "SIMULATED",
    }])
    return {"rejected": True, "case_id": case_id, "action": action_id}


@router.post("/{case_id}/actions/{action_id}/execute")
async def execute_action(case_id: str, action_id: str):
    ans = _mgr.get_answer(case_id)
    if not ans:
        raise HTTPException(404, f"Case {case_id} not found")
    decision = ans.action_decisions.get(action_id)
    available = {a.action.value for a in ans.next_best_actions.final}
    if action_id not in available:
        raise HTTPException(409, f"Action {action_id} is not recommended for this case")
    action = next(a for a in ans.next_best_actions.final if a.action.value == action_id)
    if action.route.value != "auto" and (not decision or decision.get("status") != "approved"):
        raise HTTPException(409, "Action requires approval before execution")
    if decision and decision.get("status") == "executed":
        return {"executed": True, "idempotent": True, "execution_mode": "SIMULATED"}
    try:
        transition(ans.lifecycle_state, ans.lifecycle_state.action_executing)
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    ans.lifecycle_state = ans.lifecycle_state.action_executing
    ans.action_decisions[action_id] = {
        "status": "executed", "execution_mode": "SIMULATED",
        "execution_result": "simulated_action_recorded",
    }
    transition(ans.lifecycle_state, ans.lifecycle_state.action_executed)
    ans.lifecycle_state = ans.lifecycle_state.action_executed
    _mgr.update_answer(ans)
    _mgr.log_audit(case_id, [{
        "step": 13, "action": "action_executed", "status": "simulated",
        "action_id": action_id, "execution_mode": "SIMULATED",
    }])
    return {"executed": True, "case_id": case_id, "action": action_id,
            "execution_mode": "SIMULATED"}
