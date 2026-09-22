"""
Fraud Investigation Agent — orchestrates the full investigation lifecycle.

Flow:
  trigger → evidence gathering → pattern detection → risk assessment
  → uncertainty check → optional evidence request → re-assess
  → policy recommendation → SAR if needed → case memory write

The LLM reasons over context; all deterministic decisions are in the
fraud/, policy/, and graphrag/ modules.
"""

from __future__ import annotations

import json
import hashlib
import logging
import os
import time
from datetime import datetime, timezone
from typing import Any, AsyncGenerator

from ..config import get_settings
from ..data_layer import get_data_layer
from ..fraud.exposure_engine import ExposureEngine
from ..fraud.pattern_detector import PatternDetector, _parse_ts, _safe_float
from ..fraud.risk_engine import RiskEngine
from ..graphrag.retriever import GraphRAGRetriever
from ..models.case import (
    ActionRecommendation,
    CaseAnswer,
    CaseRecord,
    CaseStatus,
    EvidenceItem,
    EvidenceRequest,
    EvidenceRequestType,
    EvidenceSource,
    FraudPattern,
    InvestigationState,
    LifecycleState,
    NextBestActions,
    SAR,
    Verdict,
)
from ..policy.policy_engine import PolicyEngine
from ..rag.context_builder import InvestigationContextBuilder
from ..rag.evidence import EvidencePack, ProvenanceItem
from ..reports.sar_generator import SARGenerator
from ..tigergraph.queries import TGQueries
from ..tigergraph.mcp_client import get_mcp_investigation_client
from ..llm.factory import get_llm_provider
from ..cases.state_machine import transition

logger = logging.getLogger(__name__)
settings = get_settings()


def validate_grounded_llm_output(
    context: dict[str, Any], output: dict[str, Any]
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Accept only LLM evidence whose entity IDs occur in the supplied pack."""
    allowed_ids: set[str] = set()
    for item in context.get("graph_evidence", []) + context.get("mcp_evidence", []):
        allowed_ids.update(str(v) for v in item.get("entity_ids", []) if v)
    trigger = context.get("trigger", {})
    allowed_ids.update(str(trigger[key]) for key in ("txn_id", "card_id", "customer_id") if trigger.get(key))
    allowed_ids.update(
        str(item.get("case_id")) for item in context.get("historical_cases", [])
        if item.get("case_id")
    )
    allowed_ids.update(
        str(item.get("rule_id")) for item in context.get("policy_evidence", [])
        if item.get("rule_id")
    )

    accepted: list[dict[str, Any]] = []
    fabricated_entities = 0
    unsupported_claims = 0
    for item in output.get("evidence", [])[:5]:
        if not isinstance(item, dict):
            unsupported_claims += 1
            continue
        entity_ids = [str(v) for v in item.get("entity_ids", []) if v]
        unknown_ids = [value for value in entity_ids if value not in allowed_ids]
        if unknown_ids:
            fabricated_entities += len(unknown_ids)
            unsupported_claims += 1
            continue
        accepted.append({
            "claim": str(item.get("claim", ""))[:500],
            "entity_ids": entity_ids,
        })
    return accepted, {
        "fabricated_entities": fabricated_entities,
        "unsupported_claims": unsupported_claims,
    }


class FraudAgent:
    """
    Stateful fraud investigation agent.

    Each call to investigate() runs the full lifecycle for one case
    and returns a CaseAnswer matching the Answer Format.
    """

    def __init__(self, mcp_client_factory=None) -> None:
        self.data = get_data_layer()
        self.tg = TGQueries()
        self.pattern_detector = PatternDetector()
        self.risk_engine = RiskEngine()
        self.exposure_engine = ExposureEngine()
        self.policy_engine = PolicyEngine()
        self.graphrag = GraphRAGRetriever()          # kept for backward compat
        self.rag = InvestigationContextBuilder()     # new real GraphRAG layer
        self.sar_generator = SARGenerator()
        self._llm_available = bool(
            settings.llm_api_key and os.getenv("TIGERATTACK_DISABLE_LLM", "0") != "1"
        )
        self._evidence_pack: EvidencePack | None = None  # persisted per investigation
        self._mcp_client_factory = mcp_client_factory or get_mcp_investigation_client

    def reassess_answer(
        self, answer: CaseAnswer, request_id: str, response: dict[str, Any]
    ) -> CaseAnswer:
        """Resume a persisted case from an external evidence response."""
        request = next(
            (item for item in answer.evidence_requests if item.request_id == request_id),
            None,
        )
        if request is None:
            raise ValueError("Evidence request does not belong to this case")
        if request.status == "fulfilled":
            raise ValueError("Evidence request has already been fulfilled")

        previous_probability = answer.case.fraud_probability
        outcome = str(response.get("outcome", "")).lower()
        delta = {
            "denied": 0.25,
            "failed": 0.15,
            "confirmed": -0.30,
            "passed": -0.15,
        }.get(outcome, 0.0)
        probability = max(0.0, min(1.0, round(previous_probability + delta, 3)))
        request.status = "fulfilled"
        request.response = response
        request.received_at = datetime.now(timezone.utc)
        request.assumed_response = str(response.get("detail", response.get("response", "")))

        answer.case.evidence.append(EvidenceItem(
            claim=f"External {request.type.value} response received: {request.assumed_response[:300]}",
            source=EvidenceSource.external,
            ref=f"evidence-request:{request_id}",
            entity_ids=[answer.trigger.get("transaction_id", "")],
        ))
        before_actions = [a.action.value for a in answer.next_best_actions.final]
        answer.case.fraud_probability = probability
        answer.next_best_actions.final = self.policy_engine.recommend(
            trigger_type=answer.trigger.get("type", ""),
            fraud_probability=probability,
            risk_level="UNKNOWN",
            confidence=min(1.0, 0.6 + (0.2 if outcome else 0.0)),
            pattern=answer.case.pattern,
            exposure_usd=answer.case.exposure_usd,
            num_signals=len(answer.case.evidence),
            num_connected_cards=len(answer.case.connected_card_ids),
            num_shared_devices=len(answer.case.connected_device_profiles),
            has_prior_confirmed_fraud=False,
            customer_response=outcome or None,
        )
        after_actions = [a.action.value for a in answer.next_best_actions.final]
        answer.next_best_actions.what_changed = (
            "changed after external evidence"
            if before_actions != after_actions or previous_probability != probability
            else "nothing"
        )
        answer.reassessment_history.append({
            "stage": "POST_EVIDENCE",
            "request_id": request_id,
            "risk_before": previous_probability,
            "risk_after": probability,
            "action_before": before_actions,
            "action_after": after_actions,
            "evidence_causing_change": [f"evidence-request:{request_id}"],
            "change_summary": answer.next_best_actions.what_changed,
        })
        if outcome == "denied" or probability >= 0.80:
            answer.case.verdict = Verdict.fraud
            answer.case.status = CaseStatus.closed_fraud
            transition(answer.lifecycle_state, LifecycleState.ready_for_action)
            answer.lifecycle_state = LifecycleState.ready_for_action
        elif outcome == "confirmed" or probability <= 0.20:
            answer.case.verdict = Verdict.legitimate
            answer.case.status = CaseStatus.closed_legitimate
            transition(answer.lifecycle_state, LifecycleState.ready_for_action)
            answer.lifecycle_state = LifecycleState.ready_for_action
        else:
            answer.case.verdict = Verdict.uncertain
            answer.case.status = CaseStatus.escalated
            transition(answer.lifecycle_state, LifecycleState.escalated)
            answer.lifecycle_state = LifecycleState.escalated
        answer.stop_reason = "POST_EVIDENCE_REASSESSMENT_COMPLETE"
        answer.validation["external_evidence_grounded"] = True
        answer.audit.append({
            "step": 8,
            "action": "reassessment_completed",
            "status": "complete",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "request_id": request_id,
            "outcome": outcome,
        })
        return answer

    # ── Main entry point ──────────────────────────────────────────────────────

    async def investigate(
        self, case_pack_row: dict[str, Any]
    ) -> CaseAnswer:
        """Run a complete investigation and return a graded answer file."""
        t0 = time.monotonic()
        state = self._init_state(case_pack_row)
        audit = state.audit_trail

        try:
            # Step 1: Gather raw evidence
            self._audit(audit, 1, "gather_evidence", "start")
            await self._gather_evidence(state)
            state.tool_calls += 5
            self._audit(audit, 1, "gather_evidence", "complete", {
                "history_txns": len(state.customer_history),
                "identity_available": state.connected_entities.get("identity") is not None,
                "prior_cases": len(state.prior_cases),
                "mcp_status": state.runtime.get("mcp", "UNKNOWN"),
            })

            # Step 2: Pattern detection (deterministic)
            self._audit(audit, 2, "pattern_detection", "start")
            pattern_result = self._detect_pattern(state)
            state.pattern = pattern_result.pattern
            state.pattern_description = pattern_result.pattern_description
            self._audit(audit, 2, "pattern_detection", "complete", {
                "pattern": pattern_result.pattern.value,
                "confidence": pattern_result.confidence,
            })

            # Step 3: Risk assessment (deterministic)
            self._audit(audit, 3, "risk_assessment", "start")
            risk = self._assess_risk(state, pattern_result)
            state.risk_score = risk.risk_score
            state.risk_level = risk.risk_level
            state.confidence = risk.confidence
            state.uncertainty_flags = risk.uncertainty_flags
            self._audit(audit, 3, "risk_assessment", "complete", {
                "risk_score": risk.risk_score,
                "level": risk.risk_level,
                "confidence": risk.confidence,
            })

            # Step 4: LLM reasoning over GraphRAG context
            self._audit(audit, 4, "llm_reasoning", "start")
            llm_result = await self._llm_reason(state, pattern_result, risk)
            state.fraud_probability = llm_result.get("fraud_probability", risk.risk_score)
            state.tokens += llm_result.get("tokens", 0)
            self._audit(audit, 4, "llm_reasoning", "complete", {
                "fraud_probability": state.fraud_probability,
            })

            # Step 5: Exposure calculation
            self._audit(audit, 5, "exposure_calculation", "start")
            exposure = self._calculate_exposure(state)
            state.exposure_usd = exposure.exposure_usd
            state.affected_txns = [
                {"TransactionID": tid} for tid in exposure.affected_txn_ids
            ]
            self._audit(audit, 5, "exposure_calculation", "complete", {
                "exposure_usd": exposure.exposure_usd,
                "affected_txns": len(exposure.affected_txn_ids),
            })

            # Step 6: Initial policy recommendation
            self._audit(audit, 6, "initial_recommendation", "start")
            state.initial_actions = self.policy_engine.recommend(
                trigger_type=state.trigger_type,
                fraud_probability=state.fraud_probability,
                risk_level=state.risk_level,
                confidence=state.confidence,
                pattern=state.pattern,
                exposure_usd=state.exposure_usd,
                num_signals=risk.evidence_count,
                num_connected_cards=len(exposure.connected_card_ids),
                num_shared_devices=len(exposure.connected_device_profiles),
                has_prior_confirmed_fraud=any(
                    c.get("outcome") == "confirmed_fraud" for c in state.prior_cases
                ),
                customer_response=None,
            )
            self._audit(audit, 6, "initial_recommendation", "complete", {
                "actions": [a.action.value for a in state.initial_actions],
            })
            state.initial_assessment = self._assessment_snapshot(state, risk)

            # Step 7: Uncertainty check — request evidence if needed
            self._audit(audit, 7, "uncertainty_check", "start")
            need_more, evidence_request = self._check_uncertainty(state, risk)
            if need_more and evidence_request:
                evidence_request.reason = self._evidence_request_reason(evidence_request, risk)
                state.evidence_requests.append(evidence_request)
                self._audit(audit, 7, "evidence_request", "requested", {
                    "type": evidence_request.type.value,
                    "status": "awaiting_external_response",
                })

                if settings.allow_simulated_evidence:
                    simulated_response = self._simulate_evidence_response(
                        state, evidence_request
                    )
                    state.evidence_received.append(simulated_response)
                    state.tool_calls += 1
                    evidence_request.assumed_response = simulated_response.get("detail", "")
                    self._audit(audit, 7, "evidence_request", "simulated", {
                        "type": evidence_request.type.value,
                        "assumed_response": evidence_request.assumed_response,
                    })

                    # Step 8: Re-assess only after an actual or explicitly
                    # simulated response has been received.
                    self._audit(audit, 8, "re_assessment", "start")
                    customer_resp = simulated_response.get("outcome")
                    state.fraud_probability = self._re_assess_probability(
                        state, simulated_response
                    )
                    state.final_actions = self.policy_engine.recommend(
                        trigger_type=state.trigger_type,
                        fraud_probability=state.fraud_probability,
                        risk_level=state.risk_level,
                        confidence=min(state.confidence + 0.2, 1.0),
                        pattern=state.pattern,
                        exposure_usd=state.exposure_usd,
                        num_signals=risk.evidence_count + 1,
                        num_connected_cards=len(exposure.connected_card_ids),
                        num_shared_devices=len(exposure.connected_device_profiles),
                        has_prior_confirmed_fraud=any(
                            c.get("outcome") == "confirmed_fraud" for c in state.prior_cases
                        ),
                        customer_response=customer_resp,
                    )
                    state.what_changed = self._diff_actions(
                        state.initial_actions, state.final_actions, simulated_response
                    )
                    self._audit(audit, 8, "re_assessment", "complete", {
                        "new_fraud_probability": state.fraud_probability,
                        "final_actions": [a.action.value for a in state.final_actions],
                    })
                else:
                    state.final_actions = state.initial_actions
                    state.verdict = Verdict.uncertain
                    state.status = CaseStatus.escalated
                    state.what_changed = "pending external evidence"
                    state.stop_reason = "AWAITING_EXTERNAL_EVIDENCE"
                    self._audit(audit, 8, "re_assessment", "pending", {
                        "reason": "External evidence response is required before reassessment.",
                    })
            else:
                state.final_actions = state.initial_actions
                state.what_changed = "nothing"
                self._audit(audit, 7, "uncertainty_check", "complete", {
                    "need_more_evidence": False,
                })

            # Step 9: Determine verdict + status
            self._finalize_verdict(state)

            # Step 10: SAR generation
            self._audit(audit, 9, "sar_check", "start")
            if self.policy_engine.requires_sar(state.final_actions):
                state.sar = self.sar_generator.generate(state, exposure)
            else:
                state.sar = SAR(
                    file=False,
                    reason="No FILE_REPORT action in final recommendations — SAR not required.",
                )
            self._audit(audit, 9, "sar_check", "complete", {"file_sar": state.sar.file})

            # Step 11: Write case to graph (best effort)
            self._audit(audit, 10, "case_memory_write", "start")
            await self._write_case_to_graph(state, exposure)
            self._audit(audit, 10, "case_memory_write", "complete", {
                "written": state.written_to_graph,
            })

            # Stopping reason
            if not state.stop_reason:
                state.stop_reason = self.policy_engine.get_stopping_reason(
                    state.fraud_probability,
                    state.confidence,
                    state.evidence_received[0].get("outcome") if state.evidence_received else None,
                    len(state.graph_evidence),
                ) or "Investigation completed — all applicable policy rules evaluated."

        except Exception as exc:  # noqa: BLE001
            logger.exception("Investigation failed for %s: %s", state.case_id, exc)
            state.stop_reason = f"Investigation error: {exc}"
            state.status = CaseStatus.escalated

        state.tokens += 0  # counted during LLM calls
        return self._build_answer(state, exposure if 'exposure' in dir() else None, t0)

    # ── Evidence gathering ────────────────────────────────────────────────────

    async def _gather_evidence(self, state: InvestigationState) -> None:
        dl = self.data
        txn_id = state.flagged_txn_id
        customer_id = state.customer_id
        card_id = state.card_id

        # Load flagged transaction
        state.flagged_txn = dl.get_transaction(txn_id)
        if state.flagged_txn is None:
            logger.warning("Transaction %s not found in local data", txn_id)
            state.flagged_txn = {
                "TransactionID": txn_id,
                "customer_id": customer_id,
                "channel": "unknown",
            }

        # Identity record
        identity = dl.get_identity(txn_id)
        if identity:
            state.connected_entities["identity"] = identity

        # Customer history
        state.customer_history = dl.get_customer_transactions(customer_id, limit=200)

        # Card transactions (using customer prefix)
        card_txns = dl.get_card_transactions(card_id, limit=200)
        state.connected_entities["card_transactions"] = card_txns

        # Prior closed cases
        prior_on_customer = dl.get_closed_cases_for_customer(customer_id)
        prior_on_card = dl.get_closed_cases_for_card(card_id)
        seen = set()
        for case in prior_on_customer + prior_on_card:
            cid = case.get("case_id", "")
            if cid not in seen:
                seen.add(cid)
                state.prior_cases.append(case)

        # Build graph evidence items from what we gathered
        self._build_local_evidence(state, identity, card_txns)

        # Try TigerGraph queries (non-fatal if unavailable)
        try:
            # VERTEX<T> params require tuple format in pyTigerGraph v2
            tg_txn = await self.tg.get_transaction_context(txn_id)
            if tg_txn and tg_txn.get("T"):
                state.connected_entities["tg_txn_context"] = tg_txn
                state.tool_calls += 1
                state.runtime["tigergraph"] = "CONNECTED"

            connected_cards = await self.tg.find_connected_cards(card_id)
            if connected_cards:
                state.connected_entities["connected_cards"] = connected_cards
                state.tool_calls += 1
                state.graph_evidence.append(EvidenceItem(
                    claim=f"{len(connected_cards)} card(s) connected to {card_id}",
                    source=EvidenceSource.graph,
                    ref="find_connected_cards",
                    entity_ids=connected_cards[:5],
                ))

            shared_devs = await self.tg.find_shared_devices(txn_id)
            if shared_devs:
                state.connected_entities["shared_devices"] = shared_devs
                state.tool_calls += 1
                state.runtime.setdefault("tigergraph", "CONNECTED")
        except Exception as exc:  # noqa: BLE001
            logger.info("TigerGraph legacy queries skipped: %s", exc)
            state.runtime["tigergraph"] = "DEGRADED"

        await self._gather_mcp_evidence(state)

    async def _gather_mcp_evidence(self, state: InvestigationState) -> None:
        """Use the official stdio MCP path and preserve every call outcome."""
        if not settings.mcp_enabled:
            state.runtime["mcp"] = "DISABLED"
            return

        try:
            async with self._mcp_client_factory() as mcp:
                if not mcp.available:
                    state.runtime["mcp"] = "DEGRADED"
                    state.mcp_calls.append({
                        "tool_name": "",
                        "query_name": "",
                        "success": False,
                        "error": "MCP session unavailable",
                    })
                    return
                results, _ = await mcp.retrieve_investigation_evidence(
                    state.flagged_txn_id, state.card_id, state.customer_id
                )
                # Include successful and failed results when the client exposes
                # them; failed calls are operational evidence, not substitutes.
                state.mcp_evidence = [r.to_dict() for r in results]
                state.mcp_calls = [r.to_dict() for r in results]
                state.tool_calls += len(results)
                state.runtime["mcp"] = "AVAILABLE" if results else "DEGRADED"
                self._audit(state.audit_trail, 1, "mcp_graph_access",
                            "complete" if any(r.success for r in results) else "failed",
                            {
                                "calls": len(results),
                                "successful_calls": sum(1 for r in results if r.success),
                                "queries": [r.query_name for r in results if r.success],
                            })
                for result in results:
                    if result.success:
                        state.graph_evidence.append(EvidenceItem(
                            claim=(
                                f"MCP verified {result.query_name} result for "
                                f"{', '.join(result.entity_ids[:3])}"
                            ),
                            source=EvidenceSource.graph,
                            ref=f"mcp:{result.query_name}",
                            entity_ids=result.entity_ids,
                        ))
        except Exception as exc:  # noqa: BLE001
            logger.warning("MCP evidence gathering failed: %s", exc)
            state.runtime["mcp"] = "FAILED"
            state.mcp_calls.append({
                "tool_name": "",
                "query_name": "",
                "success": False,
                "error": str(exc),
            })

    def _build_local_evidence(
        self,
        state: InvestigationState,
        identity: dict | None,
        card_txns: list[dict],
    ) -> None:
        """Build evidence items from local CSV data."""
        # Always add the trigger as evidence
        state.graph_evidence.append(EvidenceItem(
            claim=f"Alert triggered by {state.trigger_type}: {state.trigger_text[:120]}",
            source=EvidenceSource.document,
            ref="case_pack.csv",
            entity_ids=[state.flagged_txn_id, state.card_id],
        ))
        # Prior fraud evidence
        confirmed = [c for c in state.prior_cases if c.get("outcome") == "confirmed_fraud"]
        if confirmed:
            state.graph_evidence.append(EvidenceItem(
                claim=f"{len(confirmed)} prior confirmed fraud case(s) on this customer/card",
                source=EvidenceSource.graph,
                ref="closed_cases_history.csv",
                entity_ids=[c["case_id"] for c in confirmed[:3]],
            ))

        # Identity evidence
        if identity:
            device_status = identity.get("id_15", "").strip()
            proxy = identity.get("id_23", "").strip()
            if device_status == "New":
                state.graph_evidence.append(EvidenceItem(
                    claim="Transaction device is newly associated with this account (id_15=New)",
                    source=EvidenceSource.graph,
                    ref="identity.csv:id_15",
                    entity_ids=[state.flagged_txn_id],
                ))
            if proxy in ("anonymous", "hidden"):
                state.graph_evidence.append(EvidenceItem(
                    claim=f"Proxy type '{proxy}' detected on transaction (id_23)",
                    source=EvidenceSource.graph,
                    ref="identity.csv:id_23",
                    entity_ids=[state.flagged_txn_id],
                ))

        # Transaction trigger evidence
        if state.trigger_type == "customer_report":
            state.graph_evidence.append(EvidenceItem(
                claim="Cardholder explicitly disputed this transaction",
                source=EvidenceSource.customer,
                ref="case_pack.csv",
                entity_ids=[state.flagged_txn_id, state.card_id],
            ))

        # Region evidence
        txn = state.flagged_txn or {}
        addr2 = str(txn.get("addr2", "")).strip()
        if addr2 and addr2 != "87" and state.customer_history:
            known_regions = {str(t.get("addr2", "")) for t in state.customer_history[-30:]}
            if addr2 not in known_regions:
                state.graph_evidence.append(EvidenceItem(
                    claim=f"Transaction in country {addr2}, not in customer's recent history: {list(known_regions)[:5]}",
                    source=EvidenceSource.graph,
                    ref="transactions_clean.csv:addr2",
                    entity_ids=[state.flagged_txn_id],
                ))

    # ── Analysis helpers ──────────────────────────────────────────────────────

    def _detect_pattern(self, state: InvestigationState):
        txn = state.flagged_txn or {}
        identity = state.connected_entities.get("identity")
        card_txns = state.connected_entities.get("card_transactions", [])
        shared_devices = state.connected_entities.get("shared_devices", [])
        return self.pattern_detector.detect(
            flagged_txn=txn,
            card_transactions=card_txns,
            identity=identity,
            customer_history=state.customer_history,
            shared_devices=shared_devices,
            prior_fraud_cases=[c for c in state.prior_cases if c.get("outcome") == "confirmed_fraud"],
            trigger_type=state.trigger_type,
        )

    def _assess_risk(self, state: InvestigationState, pattern_result) -> Any:
        txn = state.flagged_txn or {}
        identity = state.connected_entities.get("identity")
        connected_cards = state.connected_entities.get("connected_cards", [])
        shared_devices = state.connected_entities.get("shared_devices", [])
        return self.risk_engine.assess(
            trigger_type=state.trigger_type,
            bank_risk_score=state.trigger_risk_score or _safe_float(txn.get("risk_score")),
            txn=txn,
            customer_history=state.customer_history,
            identity=identity,
            closed_cases=state.prior_cases,
            connected_cards=connected_cards,
            shared_devices=shared_devices,
            behavioral_anomalies=[],
        )

    def _calculate_exposure(self, state: InvestigationState):
        txn = state.flagged_txn or {}
        card_txns = state.connected_entities.get("card_transactions", [])
        connected_cards = state.connected_entities.get("connected_cards", [])
        shared_devices = state.connected_entities.get("shared_devices", [])
        # Only include transactions we have positive evidence for
        related = self._find_related_in_episode(state, card_txns)
        return self.exposure_engine.calculate(
            flagged_txn=txn,
            related_transactions=related,
            connected_cards=connected_cards,
            shared_devices=shared_devices,
        )

    def _find_related_in_episode(
        self, state: InvestigationState, card_txns: list[dict]
    ) -> list[dict]:
        """
        Return card transactions that are part of the same fraud episode.
        Conservative: only include transactions where we have supporting evidence.
        """
        if state.pattern == FraudPattern.none:
            return []

        txn = state.flagged_txn or {}
        flagged_ts = _parse_ts(txn.get("ts", ""))
        if not flagged_ts:
            return []

        from datetime import timedelta
        window = timedelta(hours=48)
        episode_txns = []

        if state.pattern == FraudPattern.card_testing:
            # Include small transactions within 1 hour before flagged
            window = timedelta(hours=1)
            for t in card_txns:
                ts = _parse_ts(t.get("ts", ""))
                if ts and flagged_ts - window <= ts <= flagged_ts:
                    if _safe_float(t.get("TransactionAmt")) < 5.0:
                        episode_txns.append(t)

        elif state.pattern in (
            FraudPattern.card_not_present_fraud,
            FraudPattern.card_not_present_new_device,
        ):
            # Include online burst within 48 hours
            for t in card_txns:
                ts = _parse_ts(t.get("ts", ""))
                if (
                    ts
                    and flagged_ts - window <= ts <= flagged_ts + timedelta(hours=6)
                    and t.get("channel") == "online"
                    and t.get("TransactionID") != txn.get("TransactionID")
                ):
                    episode_txns.append(t)

        return episode_txns

    async def _llm_reason(
        self, state: InvestigationState, pattern_result, risk
    ) -> dict[str, Any]:
        """
        Build a real GraphRAG EvidencePack then call the LLM.

        The LLM receives ONLY the EvidencePack context — not raw CSVs or
        full graph dumps. Falls back to deterministic if LLM unavailable.
        """
        # ── Build the real evidence pack via the new RAG layer ────────────────
        try:
            pack = await self.rag.build(
                case_id=state.case_id,
                txn_id=state.flagged_txn_id,
                card_id=state.card_id,
                customer_id=state.customer_id,
                trigger_type=state.trigger_type,
                trigger_text=state.trigger_text,
                pattern=state.pattern.value,
                fraud_probability=risk.risk_score,
                risk_score=risk.risk_score,
                exposure_usd=state.exposure_usd,
                num_signals=risk.evidence_count,
                mcp_results=state.mcp_evidence,
                runtime_status=state.runtime,
            )
            self._evidence_pack = pack
            state.tool_calls += len(pack.tg_queries_executed)

            # Merge RAG evidence into state.graph_evidence for the answer file
            for prov in pack.graph_evidence:
                state.graph_evidence.append(EvidenceItem(
                    claim=prov.claim,
                    source=EvidenceSource.graph if prov.source_type.value == "tigergraph"
                           else EvidenceSource.document,
                    ref=prov.query_name,
                    entity_ids=prov.entity_ids,
                ))

            state.runtime.update(pack.runtime_status)
            state.policy_evidence = pack.policy_evidence
            state.typology_evidence = pack.typology_evidence

            # Merge historical cases
            for hc in pack.historical_cases:
                cid = hc.get("case_id", "")
                if cid and not any(c.get("case_id") == cid for c in state.prior_cases):
                    state.prior_cases.append({
                        "case_id": cid,
                        "outcome": hc.get("outcome", ""),
                        "pattern": hc.get("pattern", ""),
                        "exposure_usd": hc.get("exposure_usd", 0),
                        "analyst_notes": hc.get("analyst_notes", ""),
                    })

            # Add any new uncertainty flags
            state.uncertainty_flags.extend(pack.uncertainties[:3])

            llm_ctx = pack.to_llm_context()
            serialized_context = json.dumps(llm_ctx, sort_keys=True, default=str)
            state.validation.update({
                "llm_context_source": "EvidencePack.to_llm_context",
                "llm_context_sha256": hashlib.sha256(
                    serialized_context.encode("utf-8")
                ).hexdigest(),
                "llm_context_keys": sorted(llm_ctx.keys()),
                "llm_context_chars": len(serialized_context),
                "llm_raw_dataset_in_context": False,
            })

        except Exception as exc:  # noqa: BLE001
            logger.warning("RAG build failed, falling back to legacy context: %s", exc)
            llm_ctx = self.graphrag.build_context(
                flagged_txn=state.flagged_txn or {},
                customer_history=state.customer_history,
                identity=state.connected_entities.get("identity"),
                closed_cases=state.prior_cases,
                graph_evidence=[e.model_dump() for e in state.graph_evidence],
                pattern_result=pattern_result,
                risk_assessment=risk,
                trigger_type=state.trigger_type,
                trigger_text=state.trigger_text,
            )

        # ── Call LLM with grounded context ────────────────────────────────────
        if not self._llm_available:
            return self._deterministic_probability(state, pattern_result, risk)

        try:
            state.llm_calls += 1
            return await self._call_llm(state, llm_ctx, pattern_result, risk)
        except Exception as exc:  # noqa: BLE001
            logger.warning("LLM call failed, using deterministic: %s", exc)
            return self._deterministic_probability(state, pattern_result, risk)

    def _deterministic_probability(
        self, state: InvestigationState, pattern_result, risk
    ) -> dict[str, Any]:
        """
        Compute fraud probability when LLM is unavailable.

        This must produce a CONTINUOUS score, not a clamped rule-table lookup.
        It combines the signals already computed by RiskEngine (risk.risk_score)
        with pattern confidence using a weighted blend — no hardcoded ceiling per rule.

        Weights are derived from the fraud policy signal hierarchy:
          - risk.risk_score already aggregates: bank_model_score, customer_dispute,
            prior_fraud, new_device, proxy, region anomaly, high_amount, etc.
          - Pattern confidence is an independent signal (pattern_detector.py)
          - We blend them; neither source alone determines the result

        Policy R1 boundary (0.70) is used as the HIGH zone anchor.
        Policy section 6 stopping criteria (0.85 with 2+ evidence) sets the
        high-confidence ceiling, but we never clamp all cases to a single value.
        """
        # Base: RiskEngine already computed a weighted sum of triggered signals
        base = risk.risk_score  # range: [0.05, 1.0], continuous

        # Pattern confidence is an independent evidence source
        # Blend with base: pattern gets 35% weight when it fires
        pat_conf = pattern_result.confidence if pattern_result.pattern.value != "none" else 0.0
        if pat_conf > 0:
            blended = base * 0.65 + pat_conf * 0.35
        else:
            blended = base

        # Apply a small calibration adjustment per trigger type based on policy guidance.
        # These are *adjustments* that preserve continuity — not overrides.
        # Policy R1: customer_report is a strong independent signal but not conclusive alone.
        # The RiskEngine already includes customer_dispute weight=0.6 when trigger_type==
        # "customer_report", so we do NOT add another boost here — that was the original bug.
        # Instead, we respect the RiskEngine output and only apply a modest confidence boost
        # when prior confirmed fraud corroborates the trigger.
        confirmed_prior_count = sum(
            1 for c in state.prior_cases if c.get("outcome") == "confirmed_fraud"
        )
        if confirmed_prior_count > 0:
            # Each confirmed prior case adds a small corroborating increment (diminishing)
            # First prior: +0.05, second: +0.03, more: +0.02 each, max total +0.12
            prior_boost = min(
                0.05 + 0.03 * min(confirmed_prior_count - 1, 1)
                + 0.02 * max(confirmed_prior_count - 2, 0),
                0.12,
            )
            blended = blended + prior_boost

        # Clamp to valid probability range — no artificial ceiling below 1.0
        p = round(max(0.01, min(0.99, blended)), 3)

        return {"fraud_probability": p, "tokens": 0}

    async def _call_llm(
        self, state: InvestigationState, ctx: dict, pattern_result, risk
    ) -> dict[str, Any]:
        """Structured LLM call — returns fraud_probability and tokens."""
        provider = settings.llm_provider.lower()
        if provider in {"grok", "groq", "openai"}:
            return await self._call_openai(state, ctx, pattern_result, risk)
        elif provider == "anthropic":
            return await self._call_anthropic(state, ctx, pattern_result, risk)
        else:
            return self._deterministic_probability(state, pattern_result, risk)

    async def _call_openai(
        self, state: InvestigationState, ctx: dict, pattern_result, risk,
    ) -> dict[str, Any]:
        try:
            provider = settings.llm_provider.lower()
            system_prompt = self._build_system_prompt()
            user_prompt = self._build_user_prompt(state, ctx)
            generation = await get_llm_provider(settings).generate_structured(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
            )
            data = generation.data
            tokens = generation.tokens or 0
            fp = float(data.get("fraud_probability", risk.risk_score))
            accepted, grounding = validate_grounded_llm_output(ctx, data)
            state.validation.update({
                "llm_provider": provider,
                "llm_runtime": "AVAILABLE",
                "llm_fallback_used": False,
                "llm_error": "",
                "llm_latency_ms": generation.latency_ms,
                "llm_model": generation.model,
                "llm_api_calls": generation.metadata.get("api_calls", 1),
                "llm_backup_used": generation.metadata.get("backup_used", False),
                **grounding,
            })
            state.graph_evidence.extend([
                EvidenceItem(
                    claim=e.get("claim", ""),
                    source=EvidenceSource.document,
                    ref="llm_reasoning",
                    entity_ids=e.get("entity_ids", []),
                )
                for e in accepted
            ])
            return {
                "fraud_probability": round(fp, 3),
                "tokens": tokens,
                "grounding": grounding,
            }
        except Exception as exc:  # noqa: BLE001
            provider = settings.llm_provider.lower()
            state.validation.update({
                "llm_provider": provider,
                "llm_runtime": "FAILED",
                "llm_fallback_used": True,
                "llm_error": type(exc).__name__,
            })
            logger.warning("%s call failed, using deterministic fallback: %s", provider, exc)
            return self._deterministic_probability(state, pattern_result, risk)

    async def _call_anthropic(
        self, state: InvestigationState, ctx: dict, pattern_result, risk
    ) -> dict[str, Any]:
        try:
            import anthropic
            client = anthropic.AsyncAnthropic(
                api_key=settings.llm_api_key,
                timeout=settings.llm_timeout_s,
            )
            user_prompt = self._build_user_prompt(state, ctx)
            resp = await client.messages.create(
                model=settings.llm_model,
                max_tokens=800,
                system=self._build_system_prompt(),
                messages=[{"role": "user", "content": user_prompt}],
            )
            content = resp.content[0].text
            # Extract JSON from response
            import re
            match = re.search(r'\{.*\}', content, re.DOTALL)
            if match:
                data = json.loads(match.group())
                fp = float(data.get("fraud_probability", risk.risk_score))
                _, grounding = validate_grounded_llm_output(ctx, data)
                state.validation.update(grounding)
                tokens = (resp.usage.input_tokens + resp.usage.output_tokens) if resp.usage else 0
                return {
                    "fraud_probability": round(fp, 3),
                    "tokens": tokens,
                    "grounding": grounding,
                }
        except Exception as exc:  # noqa: BLE001
            logger.warning("Anthropic call failed: %s", exc)
        return self._deterministic_probability(state, pattern_result, risk)

    def _build_system_prompt(self) -> str:
        return (
            "You are a fraud investigation analyst at a bank. "
            "You receive structured evidence from a graph database and must assess "
            "fraud probability based ONLY on the provided evidence. "
            "Never invent facts. Never guess transaction details. "
            "Return a JSON object with:\n"
            '  "fraud_probability": float (0.0 to 1.0)\n'
            '  "reasoning": string (2-3 sentences citing specific evidence)\n'
            '  "evidence": list of {"claim": string, "entity_ids": [string]}\n'
            '  "uncertainty": list of strings (what you do not know)\n'
            "Be calibrated. High risk score alone is NOT confirmation of fraud."
        )

    def _build_user_prompt(self, state: InvestigationState, ctx: dict) -> str:
        return (
            f"FRAUD INVESTIGATION — Case {state.case_id}\n\n"
            f"CONTEXT:\n{json.dumps(ctx, indent=2, default=str)[:4000]}\n\n"
            "Based solely on this evidence, what is the probability this is fraud? "
            "Respond in JSON."
        )

    # ── Uncertainty & evidence simulation ────────────────────────────────────

    def _check_uncertainty(
        self, state: InvestigationState, risk
    ) -> tuple[bool, EvidenceRequest | None]:
        """
        Determine if more evidence is needed before reaching a verdict.

        Policy basis:
          R1 — verify before blocking on a weak single signal (fp < 0.70)
          R2 — customer denial settles the question; no further evidence needed
          R8 — escalate when uncertain AND exposure > $500

        Gates:
          - Never request evidence if fp >= 0.80 (strong fraud) or fp <= 0.20 (strong clear).
          - For customer_report triggers, request confirmation only when fp is
            genuinely ambiguous (0.25–0.75); a denial + fp > 0.75 is already decisive.
          - For risk-score triggers, request step-up only when fp < 0.70 AND weak signals.
        """
        fp = state.fraud_probability
        uncertainty = risk.uncertainty_flags

        # Already decided — no evidence request needed
        if fp >= 0.80 or fp <= 0.20:
            return False, None

        # Customer report in the ambiguous zone: verify authorization
        # (Policy R1 — do not block on a single signal below 0.70 without verification)
        if (state.trigger_type == "customer_report"
                and not state.evidence_received
                and 0.25 <= fp <= 0.75):
            return True, EvidenceRequest(
                type=EvidenceRequestType.customer_validation,
                asked_after_step=state.step,
                assumed_response="",
                reason=(
                    "Authorization is unresolved; a verified customer response "
                    "resolves ambiguity and determines the permitted action (Policy R2/R3)."
                ),
            )

        # R1: single weak signal + below-blocking threshold
        if fp < 0.70 and risk.evidence_count <= 1:
            return True, EvidenceRequest(
                type=EvidenceRequestType.step_up_auth,
                asked_after_step=state.step,
                assumed_response="",
                reason=(
                    "Single signal below blocking threshold; step-up can distinguish "
                    "authorized activity from account misuse (Policy R1)."
                ),
            )

        # R8: high uncertainty flags in the mid-range AND significant exposure
        if len(uncertainty) >= 2 and 0.40 <= fp <= 0.70 and state.exposure_usd > 500:
            return True, EvidenceRequest(
                type=EvidenceRequestType.analyst_info,
                asked_after_step=state.step,
                assumed_response="",
                reason=(
                    "Multiple unresolved uncertainty flags with exposure > $500; "
                    "analyst information required before action (Policy R8)."
                ),
            )

        return False, None

    @staticmethod
    def _evidence_request_reason(request: EvidenceRequest, risk: Any) -> str:
        return request.reason or (
            f"Evidence gap {request.type.value}; current assessment has "
            f"{risk.evidence_count} supporting signal(s) and unresolved uncertainty."
        )

    @staticmethod
    def _assessment_snapshot(state: InvestigationState, risk: Any) -> dict[str, Any]:
        return {
            "fraud_probability": round(state.fraud_probability, 3),
            "risk_score": round(state.risk_score, 3),
            "confidence": round(state.confidence, 3),
            "pattern": state.pattern.value,
            "actions": [a.model_dump(mode="json") for a in state.initial_actions],
            "uncertainty": list(state.uncertainty_flags),
            "evidence_count": risk.evidence_count,
        }

    def _simulate_evidence_response(
        self,
        state: InvestigationState,
        request: EvidenceRequest,
    ) -> dict[str, Any]:
        """
        Simulate customer/system response to evidence request.
        Per README: simulate in own system and state the assumption.
        """
        fp = state.fraud_probability
        trigger_type = state.trigger_type

        if request.type == EvidenceRequestType.customer_validation:
            # Customer reported the issue → assume denial
            if trigger_type == "customer_report":
                outcome = "denied"
                response_text = (
                    "Customer reconfirmed dispute: 'I did not make this transaction. "
                    "Please block my card.' (simulated: customer report trigger implies denial)"
                )
            elif fp >= 0.65:
                outcome = "denied"
                response_text = (
                    f"Customer denied transaction. (simulated: fp={fp:.2f} above 0.65 "
                    "suggests likely fraud — assumed denial)"
                )
            else:
                outcome = "confirmed"
                response_text = (
                    f"Customer confirmed transaction. (simulated: fp={fp:.2f} below 0.65 "
                    "suggests likely legitimate — assumed confirmation)"
                )
            request.assumed_response = response_text
            return {"type": "customer_validation", "outcome": outcome, "detail": response_text}

        elif request.type == EvidenceRequestType.step_up_auth:
            if fp >= 0.55:
                outcome = "failed"
                response_text = (
                    f"Step-up authentication failed. (simulated: fp={fp:.2f} — "
                    "assumed failure increases fraud signal)"
                )
            else:
                outcome = "passed"
                response_text = (
                    f"Step-up authentication passed. (simulated: fp={fp:.2f} — "
                    "assumed pass reduces fraud suspicion)"
                )
            request.assumed_response = response_text
            return {"type": "step_up_auth", "outcome": outcome, "detail": response_text}

        else:  # analyst_info
            response_text = (
                "Analyst review: No additional internal information found. "
                "Evidence remains as gathered. (simulated: no new signals)"
            )
            request.assumed_response = response_text
            return {"type": "analyst_info", "outcome": "no_new_info", "detail": response_text}

    def _re_assess_probability(
        self, state: InvestigationState, evidence_response: dict
    ) -> float:
        outcome = evidence_response.get("outcome", "")
        fp = state.fraud_probability
        if outcome == "denied":
            return min(fp + 0.25, 0.96)
        elif outcome == "confirmed":
            return max(fp - 0.30, 0.04)
        elif outcome == "failed":  # step-up
            return min(fp + 0.15, 0.93)
        elif outcome == "passed":
            return max(fp - 0.15, 0.05)
        return fp

    def _diff_actions(
        self,
        initial: list[ActionRecommendation],
        final: list[ActionRecommendation],
        evidence_response: dict,
    ) -> str:
        initial_set = {a.action.value for a in initial}
        final_set = {a.action.value for a in final}
        added = final_set - initial_set
        removed = initial_set - final_set
        outcome = evidence_response.get("outcome", "unknown")
        if not added and not removed:
            return "nothing"
        parts = []
        if added:
            parts.append(f"Added {', '.join(sorted(added))}")
        if removed:
            parts.append(f"Removed {', '.join(sorted(removed))}")
        parts.append(f"after evidence response: '{outcome}'.")
        return " ".join(parts)

    # ── Verdict finalization ──────────────────────────────────────────────────

    def _finalize_verdict(self, state: InvestigationState) -> None:
        """
        Set case.verdict and case.status from fraud_probability.

        Thresholds anchored to Fraud Policy v1.0 (Datasets/README.md):

          HIGH_THRESHOLD = 0.70
            Policy R1: "if fraud probability is below 0.70, recommend VERIFY before block."
            This means >= 0.70 is the decisive FRAUD zone where action is warranted.

          LOW_THRESHOLD = 0.30
            Policy R8: "escalate when uncertain and exposure > $500."
            Cases below 0.30 have insufficient evidence for fraud — they land in the
            legitimate/low-risk zone. The policy does not state an exact number;
            0.30 is a defensible lower bound consistent with "monitoring threshold"
            language in the policy (MONITOR_CARD actions are recommended at mid-range).
            Cases between 0.30 and 0.70 are genuinely UNCERTAIN.

          0.30 < fp < 0.70 → UNCERTAIN (triggers evidence-request lifecycle if applicable)

        Note: customer_response overrides probability-based logic (direct evidence).
        Note: AWAITING_EXTERNAL_EVIDENCE only holds when no simulated/received response exists.
        """
        # Constants — defined here for visibility, not hidden in magic numbers elsewhere
        HIGH_THRESHOLD = 0.70
        LOW_THRESHOLD  = 0.30

        fp = state.fraud_probability
        evidence_responses = [r.get("outcome") for r in state.evidence_received]

        # 1. Direct customer/external responses override probability
        if "denied" in evidence_responses:
            state.verdict = Verdict.fraud
            state.status  = CaseStatus.closed_fraud
            return
        if "confirmed" in evidence_responses:
            state.verdict = Verdict.legitimate
            state.status  = CaseStatus.closed_legitimate
            return

        # 2. Still genuinely awaiting external evidence
        if state.stop_reason == "AWAITING_EXTERNAL_EVIDENCE" and not state.evidence_received:
            state.verdict = Verdict.uncertain
            state.status  = CaseStatus.escalated
            return

        # 3. Probability-based three-way classification
        if fp >= HIGH_THRESHOLD:
            state.verdict = Verdict.fraud
            state.status  = CaseStatus.closed_fraud
        elif fp <= LOW_THRESHOLD:
            state.verdict = Verdict.legitimate
            state.status  = CaseStatus.closed_legitimate
        elif any(a.action.value == "ESCALATE_TO_ANALYST" for a in state.final_actions):
            state.verdict = Verdict.uncertain
            state.status  = CaseStatus.escalated
        else:
            state.verdict = Verdict.uncertain
            state.status  = CaseStatus.open

    # ── Graph memory write ────────────────────────────────────────────────────

    async def _write_case_to_graph(
        self, state: InvestigationState, exposure
    ) -> None:
        exposure_obj = exposure if exposure else None
        case_data = {
            "case_id":          state.case_id,
            "customer_id":      state.customer_id,
            "card_id":          state.card_id,
            "trigger_type":     state.trigger_type,
            "verdict":          state.verdict.value,
            "pattern":          state.pattern.value,
            "exposure_usd":     state.exposure_usd,
            "summary":          self._generate_summary(state, exposure_obj),
            "opened_at":        state.started_at.isoformat(),
            "closed_at":        datetime.now(timezone.utc).isoformat(),
            "affected_txn_ids": [t.get("TransactionID", "") for t in state.affected_txns],
            "connected_card_ids": exposure_obj.connected_card_ids if exposure_obj else [],
            "actions_taken":    [a.action.value for a in state.final_actions],
            "report_filed":     state.sar.file,   # BOOL in TG schema
        }
        try:
            graph_case_id = await self.tg.write_case_to_graph(case_data)
            state.written_to_graph = bool(graph_case_id)
            state.graph_case_id = graph_case_id or ""
            if state.written_to_graph:
                readback = await self.tg.read_case_from_graph(graph_case_id)
                state.validation["case_memory_readback"] = bool(
                    readback and str(readback.get("v_id", readback.get("primary_id", graph_case_id))) == graph_case_id
                )
                self._audit(state.audit_trail, 10, "case_memory_readback",
                            "complete" if state.validation["case_memory_readback"] else "failed",
                            {"case_id": graph_case_id})
        except Exception as exc:  # noqa: BLE001
            logger.info("Graph write skipped: %s", exc)
            state.written_to_graph = False
            state.validation["case_memory_readback"] = False

    # ── Answer building ───────────────────────────────────────────────────────

    def _build_answer(
        self,
        state: InvestigationState,
        exposure,
        t0: float,
    ) -> CaseAnswer:
        exposure_obj = exposure
        affected_txn_ids = [t.get("TransactionID", "") for t in state.affected_txns]
        if not affected_txn_ids:
            affected_txn_ids = [state.flagged_txn_id]

        connected_card_ids = exposure_obj.connected_card_ids if exposure_obj else []
        connected_device_profiles = exposure_obj.connected_device_profiles if exposure_obj else []

        case_record = CaseRecord(
            status=state.status,
            verdict=state.verdict,
            fraud_probability=round(state.fraud_probability, 3),
            pattern=state.pattern,
            pattern_description=state.pattern_description,
            affected_txn_ids=affected_txn_ids,
            first_suspicious_txn_id=(
                exposure_obj.first_suspicious_txn_id if exposure_obj else state.flagged_txn_id
            ),
            connected_card_ids=connected_card_ids,
            connected_device_profiles=connected_device_profiles,
            exposure_usd=round(state.exposure_usd, 2),
            evidence=state.graph_evidence[:15],
            similar_prior_cases=[c.get("case_id", "") for c in state.prior_cases[:5]],
            summary=self._generate_summary(state, exposure_obj),
            written_to_graph=state.written_to_graph,
            graph_case_id=state.graph_case_id,
        )

        return CaseAnswer(
            case_id=state.case_id,
            trigger={
                "type": state.trigger_type,
                "text": state.trigger_text,
                "transaction_id": state.flagged_txn_id,
                "card_id": state.card_id,
                "customer_id": state.customer_id,
            },
            case=case_record,
            evidence_requests=state.evidence_requests,
            next_best_actions=NextBestActions(
                initial=state.initial_actions,
                final=state.final_actions,
                what_changed=state.what_changed,
            ),
            sar=state.sar,
            stop_reason=state.stop_reason,
            tool_calls=state.tool_calls,
            llm_calls=state.llm_calls,
            tokens=state.tokens,
            latency_s=round(time.monotonic() - t0, 2),
            runtime={
                "tigergraph": state.runtime.get("tigergraph", "DEGRADED"),
                "mcp": state.runtime.get("mcp", "DEGRADED"),
                "llm": state.validation.get(
                    "llm_runtime",
                    "AVAILABLE" if self._llm_available else "NOT_AVAILABLE",
                ),
                "graphrag": "AVAILABLE" if self._evidence_pack else "DEGRADED",
            },
            audit=state.audit_trail,
            validation=state.validation,
            case_memory={
                "written": state.written_to_graph,
                "graph_case_id": state.graph_case_id,
                "readback": state.validation.get("case_memory_readback", False),
            },
            policy_evidence=state.policy_evidence,
            typology_evidence=state.typology_evidence,
            lifecycle_state=(
                LifecycleState.awaiting_external_evidence
                if state.stop_reason == "AWAITING_EXTERNAL_EVIDENCE"
                else LifecycleState.escalated if state.status == CaseStatus.escalated
                else LifecycleState.closed if state.status in {
                    CaseStatus.closed_fraud, CaseStatus.closed_legitimate
                } else LifecycleState.ready_for_action
            ),
            initial_assessment=state.initial_assessment,
            reassessment_history=[],
            explanation={
                "summary": self._generate_summary(state, exposure_obj),
                "evidence_used": [e.ref for e in state.graph_evidence[:15]],
                "missing_evidence": list(state.uncertainty_flags),
                "why_evidence_requested": [r.reason for r in state.evidence_requests],
                "remaining_uncertainty": list(state.uncertainty_flags),
                "stop_reason": state.stop_reason,
            },
        )

    def _generate_summary(self, state: InvestigationState, exposure) -> str:
        txn = state.flagged_txn or {}
        amt = txn.get("TransactionAmt", "unknown")
        channel = txn.get("channel", "unknown")
        pattern_str = state.pattern.value.replace("_", " ")
        verdict_str = state.verdict.value
        fp = state.fraud_probability
        exposure_str = f"${state.exposure_usd:.2f}" if state.exposure_usd else "undetermined"
        prior_count = len([c for c in state.prior_cases if c.get("outcome") == "confirmed_fraud"])
        return (
            f"Case {state.case_id}: {state.trigger_type.replace('_', ' ')} on card "
            f"{state.card_id} (customer {state.customer_id}), ${amt} {channel} transaction. "
            f"Pattern assessed as {pattern_str} (p={fp:.2f}), verdict: {verdict_str}. "
            f"Estimated exposure: {exposure_str}. "
            f"{prior_count} prior confirmed fraud case(s) on this customer. "
            f"Evidence: {len(state.graph_evidence)} item(s) gathered from graph and local data."
        )

    # ── Utilities ─────────────────────────────────────────────────────────────

    @staticmethod
    def _init_state(row: dict[str, Any]) -> InvestigationState:
        risk_score_str = row.get("risk_score", "")
        risk_score = float(risk_score_str) if risk_score_str else None
        return InvestigationState(
            case_id=row["case_id"],
            trigger_type=row.get("trigger_type", ""),
            trigger_text=row.get("trigger_text", ""),
            flagged_txn_id=str(row.get("flagged_txn_id", "")),
            card_id=row.get("card_id", ""),
            customer_id=row.get("customer_id", ""),
            trigger_risk_score=risk_score,
        )

    @staticmethod
    def _audit(
        trail: list,
        step: int,
        action: str,
        status: str,
        data: dict | None = None,
    ) -> None:
        trail.append({
            "step": step,
            "action": action,
            "status": status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **(data or {}),
        })
