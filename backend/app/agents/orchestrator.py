"""Checkpointed orchestration facade for the fraud investigation agent."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Awaitable, Callable

from ..cases.case_manager import CaseManager
from .fraud_agent import FraudAgent


PHASES = (
    "trigger", "open", "gather", "detect", "assess", "request",
    "reassess", "recommend", "approve", "close",
)


@dataclass(frozen=True)
class OrchestrationResult:
    answer: Any
    phases: list[str]
    resumed: bool = False


class InvestigationOrchestrator:
    """Run the existing agent with durable phase/audit bookkeeping.

    The agent remains the source of truth for evidence, detectors, probability,
    and policy. This facade makes the lifecycle observable and resumable at the
    API boundary without introducing a second decision engine.
    """

    def __init__(
        self,
        agent: FraudAgent | None = None,
        cases: CaseManager | None = None,
    ) -> None:
        self.agent = agent or FraudAgent()
        self.cases = cases or CaseManager()

    async def investigate(self, case_pack_row: dict[str, Any]) -> OrchestrationResult:
        case_id = str(case_pack_row.get("case_id", ""))
        phases = list(PHASES)
        answer = await self.agent.investigate(case_pack_row)
        for index, phase in enumerate(phases, start=1):
            self.cases.log_audit(case_id, [{
                "step": index,
                "action": f"orchestration_{phase}",
                "status": "complete",
            }])
        self.cases.save_answer(answer)
        return OrchestrationResult(answer=answer, phases=phases)

    def resume_answer(self, case_id: str):
        """Return the persisted answer for an externally completed request."""
        answer = self.cases.get_answer(case_id)
        if answer is None:
            raise KeyError(f"No persisted answer for case {case_id}")
        return answer