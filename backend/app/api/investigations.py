"""
Investigations API — run investigations, batch execution, streaming.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import AsyncGenerator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from ..agents.fraud_agent import FraudAgent
from ..cases.case_manager import CaseManager
from ..data_layer import get_data_layer
from ..models.case import CaseAnswer

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/investigations", tags=["investigations"])
_mgr = CaseManager()


def _result_summary(answer: CaseAnswer, *, cached: bool) -> dict:
    """Return the batch response shape without serialising the full answer."""
    return {
        "status": answer.case.status.value,
        "verdict": answer.case.verdict.value,
        "fraud_probability": answer.case.fraud_probability,
        "latency_s": answer.latency_s,
        "cached": cached,
    }


@router.post("/run")
async def run_investigation(body: dict):
    """Investigate one case, reusing its persisted answer unless forced."""
    case_id = body.get("case_id")
    force = bool(body.get("force", False))
    dl = get_data_layer()

    if case_id:
        row = dl.get_case_pack_row(case_id)
        if not row:
            raise HTTPException(404, f"Case {case_id} not in case_pack")
    else:
        row = body  # Allow inline case data
        case_id = row.get("case_id")

    if case_id and not force:
        cached = _mgr.get_answer(case_id)
        if cached:
            logger.info("Returning cached investigation for %s", case_id)
            _mgr.write_answer_file(cached)
            return cached

    agent = FraudAgent()
    answer = await agent.investigate(row)
    _mgr.save_answer(answer)
    _mgr.log_audit(answer.case_id, answer.audit)
    return answer


@router.post("/run-all")
async def run_all_investigations(body: dict | None = None):
    """Investigate the case pack, reusing persisted answers unless forced."""
    force = bool((body or {}).get("force", False))
    dl = get_data_layer()
    cases = dl.get_all_case_pack_rows()
    results = {"total": len(cases), "completed": 0, "cached": 0, "failed": 0, "results": {}}

    agent = FraudAgent()
    for row in cases:
        case_id = row.get("case_id", "")
        try:
            if not force:
                cached = _mgr.get_answer(case_id)
                if cached:
                    _mgr.write_answer_file(cached)
                    results["results"][case_id] = _result_summary(cached, cached=True)
                    results["cached"] += 1
                    continue

            answer = await agent.investigate(row)
            _mgr.save_answer(answer)
            _mgr.log_audit(answer.case_id, answer.audit)
            results["results"][case_id] = _result_summary(answer, cached=False)
            results["completed"] += 1
        except Exception as exc:  # noqa: BLE001
            logger.exception("Failed to investigate %s: %s", case_id, exc)
            results["failed"] += 1
            results["results"][case_id] = {"error": str(exc)}

    return results


@router.get("/{investigation_id}")
async def get_investigation(investigation_id: str):
    ans = _mgr.get_answer(investigation_id)
    if not ans:
        raise HTTPException(404, f"Investigation {investigation_id} not found")
    return ans


@router.get("/{case_id}/stream")
async def stream_investigation(case_id: str):
    """SSE stream for real-time investigation progress."""
    dl = get_data_layer()
    row = dl.get_case_pack_row(case_id)
    if not row:
        raise HTTPException(404, f"Case {case_id} not found")

    async def event_stream() -> AsyncGenerator[str, None]:
        steps = [
            "Opened investigation",
            "Gathering transaction evidence",
            "Loading customer history",
            "Querying TigerGraph",
            "Detecting fraud pattern",
            "Assessing risk",
            "LLM reasoning over context",
            "Calculating exposure",
            "Initial policy recommendation",
            "Checking uncertainty",
            "Requesting additional evidence",
            "Re-assessing with new evidence",
            "Finalizing verdict",
            "Generating SAR if required",
            "Writing case to graph",
        ]
        for step in steps:
            yield f"data: {json.dumps({'step': step})}\n\n"
            await asyncio.sleep(0.05)

        agent = FraudAgent()
        answer = await agent.investigate(row)
        _mgr.save_answer(answer)
        _mgr.log_audit(answer.case_id, answer.audit)
        yield f"data: {json.dumps({'complete': True, 'answer': json.loads(answer.model_dump_json())})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
