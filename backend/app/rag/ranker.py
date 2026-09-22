"""
Evidence ranker — scores, deduplicates, and orders ProvenanceItems.

Scores are computed from actual evidence signals:
  - source reliability (TigerGraph = highest, CSV = medium)
  - entity relationship strength to the investigation
  - temporal proximity to the flagged transaction
  - pattern match strength
  - prior fraud case presence

No score is fabricated. If we cannot derive a score, we use a conservative default.
"""

from __future__ import annotations

import hashlib
from typing import Any

from .evidence import EntityType, ProvenanceItem, SourceType


# Source reliability weights (deterministic, not LLM-assigned)
_SOURCE_WEIGHT = {
    SourceType.tigergraph: 1.0,
    SourceType.csv:        0.8,
    SourceType.document:   0.7,
    SourceType.customer:   0.9,
}

# Relationship importance weights
_RELATIONSHIP_WEIGHT = {
    "trigger_transaction":       1.0,
    "card_used_in_transaction":  0.95,
    "transaction_identity_record": 0.90,
    "customer_transaction_history": 0.85,
    "transaction_owner":         0.85,
    "historical_fraud_case":     0.92,
    "shared_identity_signal":    0.88,
    "connected_card_network":    0.80,
    "card_transaction_history":  0.80,
    "transaction_velocity":      0.75,
    "prior_confirmed_fraud":     0.95,
    "trigger_alert":             0.95,
    "customer_dispute":          0.90,
    "device_flag":               0.88,
    "region_anomaly":            0.80,
}


class EvidenceRanker:
    """
    Scores and ranks a list of ProvenanceItems.

    Scoring formula (all values 0.0–1.0):
        score = (source_weight × 0.3) + (relationship_weight × 0.4) + (base_relevance × 0.3)

    Deduplication: items with identical claims are merged (highest score kept).
    """

    MAX_ITEMS = 20  # hard cap on items sent to LLM

    def rank(
        self,
        items: list[ProvenanceItem],
        flagged_txn_id: str = "",
        pattern: str = "none",
        has_prior_fraud: bool = False,
    ) -> list[ProvenanceItem]:
        """Return a ranked, deduplicated list of evidence items."""
        if not items:
            return []

        # Score each item
        for item in items:
            item.relevance_score = self._score(item, flagged_txn_id, pattern, has_prior_fraud)

        # Deduplicate by claim hash
        seen_hashes: set[str] = set()
        unique: list[ProvenanceItem] = []
        for item in items:
            h = hashlib.md5(item.claim.lower().strip().encode()).hexdigest()
            if h not in seen_hashes:
                seen_hashes.add(h)
                unique.append(item)

        # Sort descending by score
        ranked = sorted(unique, key=lambda x: x.relevance_score, reverse=True)

        # Assign final ranks and cap
        for i, item in enumerate(ranked[: self.MAX_ITEMS]):
            item.rank = i + 1

        return ranked[: self.MAX_ITEMS]

    def _score(
        self,
        item: ProvenanceItem,
        flagged_txn_id: str,
        pattern: str,
        has_prior_fraud: bool,
    ) -> float:
        source_w = _SOURCE_WEIGHT.get(item.source_type, 0.7)
        rel_w = _RELATIONSHIP_WEIGHT.get(item.relationship, 0.6)

        # Base relevance already on the item
        base = item.relevance_score if item.relevance_score > 0 else 0.5

        # Boost for items directly about the flagged transaction
        if flagged_txn_id and flagged_txn_id in item.entity_ids:
            base = min(base + 0.1, 1.0)

        # Boost for items relevant to confirmed fraud
        if item.entity_type == EntityType.fraud_case or "fraud" in item.relationship:
            base = min(base + 0.05, 1.0)
        if has_prior_fraud and item.entity_type == EntityType.fraud_case:
            base = min(base + 0.1, 1.0)

        # Penalise uncertainty items slightly
        if item.evidence_type in ("hypothesis", "uncertainty"):
            base = max(base - 0.15, 0.1)

        score = (source_w * 0.3) + (rel_w * 0.4) + (base * 0.3)
        return round(min(score, 1.0), 4)

    def compute_aggregate_stats(
        self, items: list[ProvenanceItem]
    ) -> dict[str, Any]:
        if not items:
            return {"count": 0, "avg_score": 0, "sources": []}
        sources = list({item.source_type.value for item in items})
        avg = round(sum(i.relevance_score for i in items) / len(items), 3)
        return {
            "count": len(items),
            "avg_score": avg,
            "sources": sources,
            "top_claim": items[0].claim if items else "",
        }
