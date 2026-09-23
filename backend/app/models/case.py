"""Pydantic models for fraud cases — mirrors the Answer Format exactly."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


# ── Enumerations ────────────────────────────────────────────────────────────


class CaseStatus(str, Enum):
    open = "open"
    closed_fraud = "closed_fraud"
    closed_legitimate = "closed_legitimate"
    escalated = "escalated"


class LifecycleState(str, Enum):
    new = "NEW"
    investigating = "INVESTIGATING"
    awaiting_external_evidence = "AWAITING_EXTERNAL_EVIDENCE"
    reassessing = "REASSESSING"
    ready_for_action = "READY_FOR_ACTION"
    awaiting_approval = "AWAITING_APPROVAL"
    action_executing = "ACTION_EXECUTING"
    action_executed = "ACTION_EXECUTED"
    action_failed = "ACTION_FAILED"
    escalated = "ESCALATED"
    closed = "CLOSED"
    failed = "FAILED"


class Verdict(str, Enum):
    fraud = "fraud"
    legitimate = "legitimate"
    uncertain = "uncertain"


class FraudPattern(str, Enum):
    card_testing = "card_testing"
    card_not_present_fraud = "card_not_present_fraud"
    card_not_present_new_device = "card_not_present_new_device"
    out_of_region_use = "out_of_region_use"
    account_takeover = "account_takeover"
    undocumented = "undocumented"
    none = "none"


class ApprovalRoute(str, Enum):
    auto = "auto"
    L1 = "L1"
    L2 = "L2"


class ActionType(str, Enum):
    ALLOW_TRANSACTION = "ALLOW_TRANSACTION"
    DECLINE_TRANSACTION = "DECLINE_TRANSACTION"
    MONITOR_CARD = "MONITOR_CARD"
    MONITOR_CONNECTED_CARDS = "MONITOR_CONNECTED_CARDS"
    WARN_CUSTOMER = "WARN_CUSTOMER"
    VERIFY_WITH_CUSTOMER = "VERIFY_WITH_CUSTOMER"
    STEP_UP_AUTH = "STEP_UP_AUTH"
    BLOCK_CARD = "BLOCK_CARD"
    BLOCK_ALL_CARDS = "BLOCK_ALL_CARDS"
    GENERATE_REPORT = "GENERATE_REPORT"
    CREATE_CASE = "CREATE_CASE"
    FILE_REPORT = "FILE_REPORT"
    ESCALATE_TO_ANALYST = "ESCALATE_TO_ANALYST"
    CLOSE_NO_FRAUD = "CLOSE_NO_FRAUD"


class EvidenceSource(str, Enum):
    graph = "graph"
    document = "document"
    customer = "customer"
    external = "external"


class EvidenceRequestType(str, Enum):
    customer_validation = "customer_validation"
    step_up_auth = "step_up_auth"
    analyst_info = "analyst_info"


# ── Sub-models ───────────────────────────────────────────────────────────────


class EvidenceItem(BaseModel):
    claim: str
    source: EvidenceSource
    ref: str = ""
    entity_ids: list[str] = Field(default_factory=list)


class EvidenceRequest(BaseModel):
    request_id: str = Field(default_factory=lambda: str(uuid4()))
    type: EvidenceRequestType
    asked_after_step: int
    assumed_response: str = ""
    status: str = "pending"
    requested_from: str = "external_provider"
    reason: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    received_at: Optional[datetime] = None
    response: dict[str, Any] = Field(default_factory=dict)


class ActionRecommendation(BaseModel):
    action: ActionType
    route: ApprovalRoute
    reason: str


class NextBestActions(BaseModel):
    initial: list[ActionRecommendation] = Field(default_factory=list)
    final: list[ActionRecommendation] = Field(default_factory=list)
    what_changed: str = "nothing"


class SAR(BaseModel):
    file: bool = False
    reason: str = ""
    narrative: str = ""
    subjects: list[str] = Field(default_factory=list)
    total_amount_usd: float = 0.0
    activity_dates: list[str] = Field(default_factory=list)


class CaseRecord(BaseModel):
    status: CaseStatus = CaseStatus.open
    verdict: Verdict = Verdict.uncertain
    fraud_probability: float = 0.0
    pattern: FraudPattern = FraudPattern.none
    pattern_description: str = ""
    affected_txn_ids: list[str] = Field(default_factory=list)
    first_suspicious_txn_id: str = ""
    connected_card_ids: list[str] = Field(default_factory=list)
    connected_device_profiles: list[str] = Field(default_factory=list)
    exposure_usd: float = 0.0
    evidence: list[EvidenceItem] = Field(default_factory=list)
    similar_prior_cases: list[str] = Field(default_factory=list)
    summary: str = ""
    written_to_graph: bool = False
    graph_case_id: str = ""


# ── Top-level answer file ────────────────────────────────────────────────────


class CaseAnswer(BaseModel):
    """The exact structure graded by the answer key."""

    case_id: str
    trigger: dict[str, Any] = Field(default_factory=dict)
    case: CaseRecord = Field(default_factory=CaseRecord)
    evidence_requests: list[EvidenceRequest] = Field(default_factory=list)
    next_best_actions: NextBestActions = Field(default_factory=NextBestActions)
    sar: SAR = Field(default_factory=SAR)
    stop_reason: str = ""
    tool_calls: int = 0
    llm_calls: int = 0
    tokens: int = 0
    latency_s: float = 0.0
    runtime: dict[str, str] = Field(default_factory=dict)
    audit: list[dict[str, Any]] = Field(default_factory=list)
    validation: dict[str, Any] = Field(default_factory=dict)
    case_memory: dict[str, Any] = Field(default_factory=dict)
    action_decisions: dict[str, dict[str, Any]] = Field(default_factory=dict)
    policy_evidence: list[dict[str, Any]] = Field(default_factory=list)
    typology_evidence: list[dict[str, Any]] = Field(default_factory=list)
    lifecycle_state: LifecycleState = LifecycleState.investigating
    initial_assessment: dict[str, Any] = Field(default_factory=dict)
    reassessment_history: list[dict[str, Any]] = Field(default_factory=list)
    explanation: dict[str, Any] = Field(default_factory=dict)


# ── Internal investigation state (not in the answer file) ────────────────────


class InvestigationState(BaseModel):
    """Runtime state preserved throughout an investigation run."""

    case_id: str
    trigger_type: str
    trigger_text: str
    flagged_txn_id: str
    card_id: str
    customer_id: str
    trigger_risk_score: Optional[float] = None

    # Progressive fields
    step: int = 0
    tool_calls: int = 0
    llm_calls: int = 0
    tokens: int = 0
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    flagged_txn: Optional[dict[str, Any]] = None
    customer_history: list[dict[str, Any]] = Field(default_factory=list)
    connected_entities: dict[str, Any] = Field(default_factory=dict)
    prior_cases: list[dict[str, Any]] = Field(default_factory=list)
    graph_evidence: list[EvidenceItem] = Field(default_factory=list)

    fraud_probability: float = 0.0
    risk_level: str = "UNKNOWN"
    risk_score: float = 0.0
    confidence: float = 0.0
    uncertainty_flags: list[str] = Field(default_factory=list)

    pattern: FraudPattern = FraudPattern.none
    pattern_description: str = ""
    affected_txns: list[dict[str, Any]] = Field(default_factory=list)
    exposure_usd: float = 0.0

    evidence_requests: list[EvidenceRequest] = Field(default_factory=list)
    evidence_received: list[dict[str, Any]] = Field(default_factory=list)

    initial_actions: list[ActionRecommendation] = Field(default_factory=list)
    final_actions: list[ActionRecommendation] = Field(default_factory=list)
    what_changed: str = "nothing"

    verdict: Verdict = Verdict.uncertain
    status: CaseStatus = CaseStatus.open
    stop_reason: str = ""

    audit_trail: list[dict[str, Any]] = Field(default_factory=list)
    sar: SAR = Field(default_factory=SAR)

    # Graph write
    written_to_graph: bool = False
    graph_case_id: str = ""
    runtime: dict[str, str] = Field(default_factory=dict)
    validation: dict[str, Any] = Field(default_factory=dict)
    mcp_calls: list[dict[str, Any]] = Field(default_factory=list)
    mcp_evidence: list[dict[str, Any]] = Field(default_factory=list)
    policy_evidence: list[dict[str, Any]] = Field(default_factory=list)
    typology_evidence: list[dict[str, Any]] = Field(default_factory=list)
    lifecycle_state: LifecycleState = LifecycleState.investigating
    initial_assessment: dict[str, Any] = Field(default_factory=dict)
    reassessment_history: list[dict[str, Any]] = Field(default_factory=list)
