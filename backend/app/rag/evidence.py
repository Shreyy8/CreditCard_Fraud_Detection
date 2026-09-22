"""
Evidence types with full provenance.

Every fact in an investigation must carry:
- source (tigergraph | document | csv | customer)
- entity type and ID
- which query or document section produced it
- why it was retrieved
- a relevance/confidence score derived from actual signals

Nothing here is fabricated.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class SourceType(str, Enum):
    tigergraph = "tigergraph"
    document   = "document"
    csv        = "csv"
    customer   = "customer"


class EntityType(str, Enum):
    transaction    = "transaction"
    card           = "card"
    customer       = "customer"
    identity       = "identity"
    fraud_case     = "fraud_case"
    closed_case    = "closed_case"
    policy_section = "policy_section"
    typology       = "typology"
    behavioral     = "behavioral"


@dataclass
class ProvenanceItem:
    """A single piece of evidence with complete traceability."""

    claim: str
    source_type: SourceType
    entity_type: EntityType
    entity_ids: list[str] = field(default_factory=list)
    query_name: str = ""          # GSQL query that produced this, or doc section
    document_id: str = ""         # policy rule ID, case ID, etc.
    relationship: str = ""        # how this entity relates to the investigation
    raw_data: dict[str, Any] = field(default_factory=dict)

    # Scoring (deterministic — derived from signals, never invented)
    relevance_score: float = 0.0  # 0.0–1.0
    confidence: float = 1.0       # 1.0 for observed facts, lower for inferences
    evidence_type: str = "observed_fact"  # observed_fact | inference | hypothesis | uncertainty

    # Ranking
    rank: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "rank": self.rank,
            "claim": self.claim,
            "source": self.source_type.value,
            "entity_type": self.entity_type.value,
            "entity_ids": self.entity_ids,
            "query": self.query_name,
            "document_id": self.document_id,
            "relationship": self.relationship,
            "relevance": round(self.relevance_score, 3),
            "confidence": round(self.confidence, 3),
            "evidence_type": self.evidence_type,
        }


@dataclass
class EvidencePack:
    """
    The complete investigation context sent to the LLM.

    Built from real retrieved evidence only.
    No fabricated data enters this structure.
    """

    case_id: str
    trigger: dict[str, Any]

    # Graph-sourced evidence (from TigerGraph queries)
    graph_evidence: list[ProvenanceItem] = field(default_factory=list)

    # Historical fraud/closed cases
    historical_cases: list[dict[str, Any]] = field(default_factory=list)

    # Policy rules applicable to this investigation
    policy_evidence: list[dict[str, Any]] = field(default_factory=list)

    # Fraud typology descriptions
    typology_evidence: list[dict[str, Any]] = field(default_factory=list)

    # Behavioral signals (velocity, amount anomalies, etc.)
    behavioral_evidence: list[ProvenanceItem] = field(default_factory=list)

    # Exposure summary
    exposure: dict[str, Any] = field(default_factory=dict)

    # Evidence gaps — what we could not retrieve
    uncertainties: list[str] = field(default_factory=list)
    evidence_gaps: list[str] = field(default_factory=list)
    recommended_retrieval: list[str] = field(default_factory=list)

    # Grounding metadata
    total_evidence_items: int = 0
    tg_queries_executed: list[str] = field(default_factory=list)
    tg_items_retrieved: int = 0
    mcp_evidence: list[ProvenanceItem] = field(default_factory=list)
    mcp_calls: list[dict[str, Any]] = field(default_factory=list)
    runtime_status: dict[str, str] = field(default_factory=dict)
    historical_cases_retrieved: int = 0
    policy_sources_retrieved: int = 0

    def all_evidence(self) -> list[ProvenanceItem]:
        return self.graph_evidence + self.mcp_evidence + self.behavioral_evidence

    def to_llm_context(self) -> dict[str, Any]:
        """
        Serialise to a compact dict for the LLM prompt.
        Long raw data is stripped; provenance is preserved.
        """
        return {
            "case_id": self.case_id,
            "trigger": self.trigger,
            "graph_evidence": [e.to_dict() for e in self.graph_evidence[:15]],
            "mcp_evidence": [e.to_dict() for e in self.mcp_evidence[:10]],
            "historical_cases": self.historical_cases[:5],
            "policy_evidence": self.policy_evidence[:6],
            "typology_evidence": self.typology_evidence[:3],
            "behavioral_evidence": [e.to_dict() for e in self.behavioral_evidence[:5]],
            "exposure": self.exposure,
            "uncertainties": self.uncertainties,
            "evidence_gaps": self.evidence_gaps,
            "metadata": {
                "tg_queries": self.tg_queries_executed,
                "tg_items": self.tg_items_retrieved,
                "mcp_calls": self.mcp_calls,
                "runtime_status": self.runtime_status,
                "historical_items": self.historical_cases_retrieved,
                "policy_items": self.policy_sources_retrieved,
                "total_items": self.total_evidence_items,
            },
        }
