"""
Investigation context builder.

Orchestrates all retrieval sources into a single EvidencePack:
  1. TigerGraph graph retrieval  (GraphRetriever)
  2. Closed-case similarity      (CaseSimilarityIndex)
  3. Policy / typology docs      (DocumentRetriever)
  4. Evidence ranking            (EvidenceRanker)

The LLM only ever sees the EvidencePack — never raw CSVs or full graph dumps.
Every item in the pack has provenance.
"""

from __future__ import annotations

import logging
from typing import Any

from ..data_layer import DataLayer, get_data_layer
from .document_retriever import DocumentRetriever
from .embeddings import ensure_index_built, get_case_index
from .evidence import (
    EntityType,
    EvidencePack,
    ProvenanceItem,
    SourceType,
)
from .graph_retriever import GraphRetriever
from .ranker import EvidenceRanker

logger = logging.getLogger(__name__)


class InvestigationContextBuilder:
    """
    Builds a complete, grounded EvidencePack for a single investigation case.
    """

    # Maximum items per category sent to LLM
    MAX_GRAPH_ITEMS    = 15
    MAX_HIST_CASES     = 5
    MAX_POLICY_ITEMS   = 6
    MAX_TYPOLOGY_ITEMS = 2

    def __init__(self) -> None:
        self._graph   = GraphRetriever()
        self._docs    = DocumentRetriever()
        self._ranker  = EvidenceRanker()
        self._data    = get_data_layer()
        self._index_ready = False

    def _ensure_index(self) -> None:
        if not self._index_ready:
            cases = list(self._data.closed_cases.values())
            ensure_index_built(cases)
            self._index_ready = True

    # ── Primary entry-point ───────────────────────────────────────────────────

    async def build(
        self,
        case_id:       str,
        txn_id:        str,
        card_id:       str,
        customer_id:   str,
        trigger_type:  str,
        trigger_text:  str,
        # Partial state already computed by deterministic engines
        pattern:       str  = "none",
        fraud_probability: float = 0.0,
        risk_score:    float = 0.0,
        exposure_usd:  float = 0.0,
        num_signals:   int   = 0,
        mcp_results: list[dict[str, Any]] | None = None,
        runtime_status: dict[str, str] | None = None,
    ) -> EvidencePack:
        """
        Build a full EvidencePack for one investigation.
        Runs TigerGraph retrieval + document retrieval in parallel.
        """

        pack = EvidencePack(
            case_id=case_id,
            trigger={
                "type":        trigger_type,
                "text":        trigger_text,
                "txn_id":      txn_id,
                "card_id":     card_id,
                "customer_id": customer_id,
            },
        )

        # ── 1. TigerGraph graph retrieval ─────────────────────────────────────
        logger.info("[%s] Starting TigerGraph retrieval (txn=%s card=%s cust=%s)",
                    case_id, txn_id, card_id, customer_id)

        tg_evidence, tg_uncertainties, tg_queries = await self._graph.retrieve_all(
            txn_id=txn_id,
            card_id=card_id,
            customer_id=customer_id,
        )

        pack.tg_queries_executed = tg_queries
        pack.tg_items_retrieved  = len(tg_evidence)
        pack.uncertainties.extend(tg_uncertainties)
        pack.runtime_status.update(runtime_status or {})

        # MCP is an agent-facing graph access path. Its results are kept
        # separate from direct pyTigerGraph evidence so provenance is explicit.
        mcp_items = self._build_mcp_evidence(mcp_results or [])
        pack.mcp_evidence = mcp_items
        pack.mcp_calls = [
            {
                "tool_name": r.get("tool_name", ""),
                "query_name": r.get("query_name", ""),
                "entity_ids": r.get("entity_ids", []),
                "success": bool(r.get("success")),
                "error": r.get("error", ""),
                "retrieved_at": r.get("retrieved_at", ""),
                "duration_ms": r.get("duration_ms", 0),
            }
            for r in (mcp_results or [])
        ]
        if mcp_results and not mcp_items:
            pack.evidence_gaps.append(
                "MCP calls completed without verified evidence"
            )

        logger.info("[%s] TigerGraph: %d items from %d queries",
                    case_id, len(tg_evidence), len(tg_queries))

        # ── 2. CSV-sourced evidence (fills gaps when TG data is sparse) ───────
        csv_evidence = self._build_csv_evidence(
            txn_id, card_id, customer_id, trigger_type, trigger_text
        )
        # Mark CSV items with lower confidence than graph items
        for item in csv_evidence:
            item.confidence = 0.85

        all_evidence = tg_evidence + mcp_items + csv_evidence

        # ── 3. Check if connected cards detected ──────────────────────────────
        has_shared_device = any(
            "shared" in e.relationship or "connected" in e.relationship
            for e in all_evidence
        )
        connected_card_ids = []
        for e in all_evidence:
            if e.relationship == "connected_card_network":
                connected_card_ids.extend(
                    i for i in e.entity_ids if i != card_id
                )

        # ── 4. Rank all graph evidence ─────────────────────────────────────────
        has_prior = any(
            e.entity_type == EntityType.fraud_case for e in all_evidence
        )
        ranked = self._ranker.rank(
            all_evidence,
            flagged_txn_id=txn_id,
            pattern=pattern,
            has_prior_fraud=has_prior,
        )
        pack.graph_evidence = ranked[: self.MAX_GRAPH_ITEMS]

        # Separate out behavioural items
        pack.behavioral_evidence = [
            e for e in ranked
            if e.entity_type == EntityType.behavioral
        ][:5]

        pack.mcp_evidence = [
            item for item in ranked if item.source_type == SourceType.tigergraph
            and item.query_name.startswith("mcp:")
        ][:10]

        # ── 5. Historical-case retrieval (similarity search) ──────────────────
        self._ensure_index()
        query_case = {
            "case_id":       case_id,
            "customer_id":   customer_id,
            "card_id":       card_id,
            "pattern":       pattern,
            "exposure_usd":  str(exposure_usd),
            "outcome":       "",          # unknown — we're investigating
            "analyst_notes": trigger_text,
        }
        similar = get_case_index().find_similar(
            query_case, top_k=self.MAX_HIST_CASES, min_score=0.05
        )
        pack.historical_cases      = similar
        pack.historical_cases_retrieved = len(similar)
        logger.info("[%s] Historical cases: %d retrieved", case_id, len(similar))

        # If similarity returns nothing, fallback to same-customer CSV cases
        if not similar:
            fallback_cases = self._data.get_closed_cases_for_customer(customer_id)
            if not fallback_cases:
                fallback_cases = self._data.get_closed_cases_for_card(card_id)
            pack.historical_cases = [
                {
                    "case_id":     c.get("case_id"),
                    "outcome":     c.get("outcome"),
                    "pattern":     c.get("pattern"),
                    "exposure_usd":c.get("exposure_usd"),
                    "n_txns":      c.get("n_txns"),
                    "analyst_notes":(c.get("analyst_notes") or "")[:300],
                    "why_similar": "same customer/card",
                    "relevance":   0.80,
                }
                for c in fallback_cases[: self.MAX_HIST_CASES]
            ]
            pack.historical_cases_retrieved = len(pack.historical_cases)
            if not pack.historical_cases:
                pack.evidence_gaps.append(
                    f"No prior closed cases found for customer {customer_id} or card {card_id}"
                )

        # ── 6. Policy + typology document retrieval ───────────────────────────
        policy_docs = self._docs.get_policy_rules(
            trigger_type=trigger_type,
            pattern=pattern,
            fraud_probability=fraud_probability,
            has_shared_device=has_shared_device,
            exposure_usd=exposure_usd,
            num_signals=num_signals,
        )
        typology_docs = self._docs.get_typology(pattern)
        reg_refs      = self._docs.get_regulatory_refs(pattern, trigger_type)

        pack.policy_evidence   = policy_docs[: self.MAX_POLICY_ITEMS]
        pack.typology_evidence = typology_docs[: self.MAX_TYPOLOGY_ITEMS]
        pack.policy_sources_retrieved = len(policy_docs) + len(typology_docs) + len(reg_refs)
        logger.info("[%s] Policy/typology: %d items", case_id, pack.policy_sources_retrieved)

        # ── 7. Exposure summary ───────────────────────────────────────────────
        pack.exposure = {
            "exposure_usd":        exposure_usd,
            "connected_card_ids":  connected_card_ids[:5],
            "has_shared_device":   has_shared_device,
        }

        # ── 8. Evidence gaps ──────────────────────────────────────────────────
        if not tg_evidence:
            pack.evidence_gaps.append(
                "No TigerGraph evidence retrieved — transaction may not be loaded in graph"
            )
            pack.recommended_retrieval.append(
                "Load transactions into FraudCaseGraph and retry"
            )
        if not any(e.entity_type == EntityType.identity for e in pack.graph_evidence):
            pack.evidence_gaps.append(
                "No identity/device record for this transaction "
                "(in-person transaction or identity not loaded)"
            )
        if not similar and not pack.historical_cases:
            pack.evidence_gaps.append("No similar historical cases found")

        # ── 9. Final metadata ─────────────────────────────────────────────────
        pack.total_evidence_items = (
            len(pack.graph_evidence)
            + len(pack.mcp_evidence)
            + len(pack.historical_cases)
            + len(pack.policy_evidence)
            + len(pack.typology_evidence)
        )

        logger.info(
            "[%s] EvidencePack complete: graph=%d hist=%d policy=%d total=%d",
            case_id,
            len(pack.graph_evidence),
            len(pack.historical_cases),
            len(pack.policy_evidence),
            pack.total_evidence_items,
        )

        return pack

    @staticmethod
    def _build_mcp_evidence(results: list[dict[str, Any]]) -> list[ProvenanceItem]:
        """Convert only successful, provenance-bearing MCP results to evidence."""
        evidence: list[ProvenanceItem] = []
        for result in results:
            if not result.get("success"):
                continue
            query_name = str(result.get("query_name", ""))
            tool_name = str(result.get("tool_name", ""))
            entity_ids = [str(v) for v in result.get("entity_ids", []) if v]
            data = result.get("evidence")
            if not isinstance(data, dict):
                data = {"result": data}
            summary = data.get("summary") or data.get("message") or "verified result"
            evidence.append(ProvenanceItem(
                claim=f"MCP {query_name or tool_name}: {str(summary)[:300]}",
                source_type=SourceType.tigergraph,
                entity_type=EntityType.transaction if query_name == "Transaction_Fraud"
                    else EntityType.behavioral if "behavior" in query_name
                    else EntityType.card if "card" in query_name
                    else EntityType.customer if "customer" in query_name
                    else EntityType.fraud_case if "fraud" in query_name
                    else EntityType.transaction,
                entity_ids=entity_ids,
                query_name=f"mcp:{query_name or tool_name}",
                relationship="mcp_verified_graph_result",
                raw_data={"tool_name": tool_name, "data": data},
                relevance_score=0.95,
                confidence=1.0,
                evidence_type="observed_fact",
            ))
        return evidence

    # ── CSV gap-fill evidence ─────────────────────────────────────────────────

    def _build_csv_evidence(
        self,
        txn_id:       str,
        card_id:      str,
        customer_id:  str,
        trigger_type: str,
        trigger_text: str,
    ) -> list[ProvenanceItem]:
        """
        Build ProvenanceItems from local CSV data.
        These fill the gap when TigerGraph hasn't been loaded with data yet.
        Always marked source_type=csv so provenance is honest.
        """
        items: list[ProvenanceItem] = []

        # Trigger alert itself
        items.append(ProvenanceItem(
            claim=f"Alert: {trigger_text[:200]}",
            source_type=SourceType.csv,
            entity_type=EntityType.transaction,
            entity_ids=[txn_id, card_id],
            query_name="case_pack.csv",
            relationship="trigger_alert",
            raw_data={"trigger_type": trigger_type, "txn_id": txn_id},
            relevance_score=1.0,
            confidence=1.0,
            evidence_type="observed_fact",
        ))

        # Customer dispute
        if trigger_type == "customer_report":
            items.append(ProvenanceItem(
                claim=f"Customer {customer_id} explicitly disputed transaction {txn_id}",
                source_type=SourceType.customer,
                entity_type=EntityType.customer,
                entity_ids=[customer_id, txn_id],
                query_name="case_pack.csv",
                relationship="customer_dispute",
                raw_data={"trigger_type": "customer_report"},
                relevance_score=0.95,
                confidence=1.0,
                evidence_type="observed_fact",
            ))

        # Flagged transaction from CSV
        txn = self._data.get_transaction(txn_id)
        if txn:
            identity = self._data.get_identity(txn_id)
            amt       = txn.get("TransactionAmt", "?")
            channel   = txn.get("channel", "?")
            ts        = txn.get("ts", "?")
            risk      = txn.get("risk_score", "?")
            addr2     = txn.get("addr2", "")
            card4     = txn.get("card4", "")
            card6     = txn.get("card6", "")

            items.append(ProvenanceItem(
                claim=(
                    f"Transaction {txn_id}: ${amt} via {channel} at {ts}, "
                    f"risk_score={risk}, "
                    f"card_network={card4} ({card6}), "
                    f"billing_country={addr2}"
                ),
                source_type=SourceType.csv,
                entity_type=EntityType.transaction,
                entity_ids=[txn_id],
                query_name="transactions_clean.csv",
                relationship="trigger_transaction",
                raw_data={
                    "amount": amt, "channel": channel, "ts": ts,
                    "risk_score": risk, "addr2": addr2,
                },
                relevance_score=0.92,
                confidence=1.0,
                evidence_type="observed_fact",
            ))

            if identity:
                dev_status = identity.get("id_15", "").strip()
                proxy      = identity.get("id_23", "").strip()
                device_info = identity.get("DeviceInfo", "").strip()
                os_info     = identity.get("id_30", "").strip()
                browser     = identity.get("id_31", "").strip()

                flags = []
                rscore = 0.80
                if dev_status == "New":
                    flags.append("NEW DEVICE (id_15=New)")
                    rscore = 0.92
                if proxy in ("anonymous", "hidden"):
                    flags.append(f"PROXY={proxy} (id_23)")
                    rscore = min(rscore + 0.05, 0.97)

                items.append(ProvenanceItem(
                    claim=(
                        f"Identity record for {txn_id}: "
                        f"device={device_info or 'unknown'}, "
                        f"OS={os_info or '?'}, browser={browser or '?'}, "
                        f"device_status={dev_status or '?'}"
                        + (f" [FLAGS: {', '.join(flags)}]" if flags else "")
                    ),
                    source_type=SourceType.csv,
                    entity_type=EntityType.identity,
                    entity_ids=[txn_id],
                    query_name="identity.csv",
                    relationship="device_flag" if flags else "transaction_identity_record",
                    raw_data={
                        "device_info": device_info, "os": os_info, "browser": browser,
                        "id_15": dev_status, "id_23": proxy,
                    },
                    relevance_score=rscore,
                    confidence=1.0,
                    evidence_type="observed_fact",
                ))

            # Region anomaly check
            if addr2 and addr2 != "87":
                history = self._data.get_customer_transactions(customer_id, limit=30)
                known_regions = {str(t.get("addr2", "")) for t in history if t.get("addr2")}
                if addr2 not in known_regions and known_regions:
                    items.append(ProvenanceItem(
                        claim=(
                            f"Transaction country {addr2} not in customer {customer_id}'s "
                            f"known regions: {sorted(known_regions)[:5]}"
                        ),
                        source_type=SourceType.csv,
                        entity_type=EntityType.transaction,
                        entity_ids=[txn_id, customer_id],
                        query_name="transactions_clean.csv:addr2",
                        relationship="region_anomaly",
                        raw_data={"txn_region": addr2, "known_regions": list(known_regions)[:5]},
                        relevance_score=0.78,
                        confidence=0.9,
                        evidence_type="inference",
                    ))

        # Prior confirmed fraud from CSV
        prior = self._data.get_closed_cases_for_customer(customer_id)
        confirmed_prior = [c for c in prior if c.get("outcome") == "confirmed_fraud"]
        if confirmed_prior:
            items.append(ProvenanceItem(
                claim=(
                    f"Customer {customer_id} has {len(confirmed_prior)} "
                    f"prior confirmed fraud case(s): "
                    f"{[c.get('case_id') for c in confirmed_prior[:3]]}"
                ),
                source_type=SourceType.csv,
                entity_type=EntityType.closed_case,
                entity_ids=[c.get("case_id", "") for c in confirmed_prior[:3]],
                query_name="closed_cases_history.csv",
                relationship="prior_confirmed_fraud",
                raw_data={"count": len(confirmed_prior)},
                relevance_score=0.90,
                confidence=1.0,
                evidence_type="observed_fact",
            ))

        return items
