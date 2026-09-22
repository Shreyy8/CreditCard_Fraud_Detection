"""
Real TigerGraph graph retriever.

Executes the installed GSQL queries against the live FraudCaseGraph
and normalises results into ProvenanceItems.

CRITICAL CONTRACT:
- Every ProvenanceItem produced here has source_type = tigergraph
- Every query_name field names the actual installed GSQL query used
- Raw TigerGraph vertex/edge data is stored in raw_data for traceability
- We never fabricate relationships — if TigerGraph returns nothing, we say so
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from ..tigergraph.client import TigerGraphClient, get_client
from .evidence import EntityType, ProvenanceItem, SourceType

logger = logging.getLogger(__name__)

# ── Helpers ───────────────────────────────────────────────────────────────────

def _v_list(result_block: Any, key: str) -> list[dict]:
    """Extract a vertex list from a pyTigerGraph result block."""
    if isinstance(result_block, dict):
        return result_block.get(key, [])
    return []


def _vattr(vertex: dict) -> dict:
    """Return the attributes dict from a vertex result."""
    return vertex.get("attributes", vertex)


# ── GraphRetriever ────────────────────────────────────────────────────────────

class GraphRetriever:
    """
    Executes installed GSQL queries and returns structured ProvenanceItems.

    All methods are async and non-fatal — if TigerGraph is unavailable,
    they return empty lists with uncertainty notes rather than crashing.
    """

    QUERY_TIMEOUT = 20  # seconds per query

    def __init__(self, client: TigerGraphClient | None = None) -> None:
        self._tg = client or get_client()
        self._queries_executed: list[str] = []
        self._tg_available: bool | None = None  # None = untested

    async def _check_availability(self) -> bool:
        if self._tg_available is None:
            self._tg_available = await self._tg.ping()
        return self._tg_available

    async def _run(self, query_name: str, params: dict) -> list[dict]:
        """
        Run one installed query, recording provenance.
        VERTEX<T> parameters must be passed as 1-tuples per pyTigerGraph v2.
        Returns the raw results list (empty on any failure).
        """
        if not await self._check_availability():
            return []
        # Convert plain string values for VERTEX<T> params to 1-tuples
        # pyTigerGraph v2 requires {"param": ("vertex_id",)} for VERTEX params
        fixed_params = {
            k: (v,) if isinstance(v, str) else v
            for k, v in params.items()
        }
        try:
            t0 = time.monotonic()
            results = await asyncio.wait_for(
                self._tg.async_run_query(query_name, fixed_params),
                timeout=self.QUERY_TIMEOUT,
            )
            elapsed = round(time.monotonic() - t0, 2)
            self._queries_executed.append(query_name)
            logger.debug("TG query %s → %d result blocks in %.2fs",
                         query_name, len(results or []), elapsed)
            return results or []
        except asyncio.TimeoutError:
            logger.warning("TG query %s timed out after %ds", query_name, self.QUERY_TIMEOUT)
            return []
        except Exception as exc:  # noqa: BLE001
            logger.warning("TG query %s failed: %s", query_name, exc)
            return []

    # ── Core investigation retrievals ─────────────────────────────────────────

    async def get_transaction_full_context(
        self, txn_id: str
    ) -> tuple[list[ProvenanceItem], list[str]]:
        """
        Run Transaction_Fraud for the flagged transaction.
        Returns (evidence_items, uncertainty_notes).
        """
        evidence: list[ProvenanceItem] = []
        uncertainties: list[str] = []

        results = await self._run("Transaction_Fraud", {"txn": txn_id})
        if not results:
            uncertainties.append(
                f"Transaction {txn_id} not found in TigerGraph — "
                "may not have been loaded yet"
            )
            return evidence, uncertainties

        # Parse each result block
        for block in results:
            # Transaction vertex
            txns = _v_list(block, "T")
            for v in txns:
                attrs = _vattr(v)
                evidence.append(ProvenanceItem(
                    claim=(
                        f"Transaction {v.get('v_id', txn_id)}: "
                        f"${attrs.get('transaction_amt', '?')} via "
                        f"{attrs.get('channel', '?')} channel, "
                        f"product {attrs.get('product_cd', '?')}, "
                        f"risk_score={attrs.get('risk_score', '?')}"
                    ),
                    source_type=SourceType.tigergraph,
                    entity_type=EntityType.transaction,
                    entity_ids=[v.get("v_id", txn_id)],
                    query_name="Transaction_Fraud",
                    relationship="trigger_transaction",
                    raw_data=attrs,
                    relevance_score=1.0,
                    confidence=1.0,
                    evidence_type="observed_fact",
                ))

            # Card vertex
            cards = _v_list(block, "Cards")
            for v in cards:
                attrs = _vattr(v)
                evidence.append(ProvenanceItem(
                    claim=(
                        f"Card {v.get('v_id', '?')}: "
                        f"network={attrs.get('card4', '?')} "
                        f"type={attrs.get('card6', '?')}"
                    ),
                    source_type=SourceType.tigergraph,
                    entity_type=EntityType.card,
                    entity_ids=[v.get("v_id", "")],
                    query_name="Transaction_Fraud",
                    relationship="card_used_in_transaction",
                    raw_data=attrs,
                    relevance_score=0.95,
                    confidence=1.0,
                    evidence_type="observed_fact",
                ))

            # Identity vertex
            identities = _v_list(block, "Identities")
            for v in identities:
                attrs = _vattr(v)
                dev_status = attrs.get("id_15", "")
                proxy = attrs.get("id_23", "")
                device_info = attrs.get("device_info", "")
                os_info = attrs.get("id_30", "")
                browser = attrs.get("id_31", "")

                risk_boost = 0.0
                flags = []
                if dev_status == "New":
                    risk_boost += 0.3
                    flags.append("new device")
                if proxy in ("anonymous", "hidden"):
                    risk_boost += 0.25
                    flags.append(f"proxy={proxy}")

                claim = (
                    f"Identity record: device={device_info or 'unknown'}, "
                    f"OS={os_info or '?'}, browser={browser or '?'}, "
                    f"device_status={dev_status or '?'}"
                )
                if flags:
                    claim += f" [FLAGS: {', '.join(flags)}]"

                evidence.append(ProvenanceItem(
                    claim=claim,
                    source_type=SourceType.tigergraph,
                    entity_type=EntityType.identity,
                    entity_ids=[v.get("v_id", txn_id)],
                    query_name="Transaction_Fraud",
                    relationship="transaction_identity_record",
                    raw_data=attrs,
                    relevance_score=0.85 + risk_boost,
                    confidence=1.0,
                    evidence_type="observed_fact",
                ))

            # Customer vertex
            customers = _v_list(block, "Customers")
            for v in customers:
                evidence.append(ProvenanceItem(
                    claim=f"Transaction belongs to customer {v.get('v_id', '?')}",
                    source_type=SourceType.tigergraph,
                    entity_type=EntityType.customer,
                    entity_ids=[v.get("v_id", "")],
                    query_name="Transaction_Fraud",
                    relationship="transaction_owner",
                    raw_data=_vattr(v),
                    relevance_score=0.90,
                    confidence=1.0,
                    evidence_type="observed_fact",
                ))

        if not evidence:
            uncertainties.append(
                f"Transaction {txn_id} returned empty result from Transaction_Fraud query"
            )

        return evidence, uncertainties

    async def get_customer_history(
        self, customer_id: str, limit: int = 50
    ) -> tuple[list[ProvenanceItem], list[str]]:
        """Run get_customer_history and return behavioural evidence."""
        evidence: list[ProvenanceItem] = []
        uncertainties: list[str] = []

        results = await self._run("get_customer_history", {"customer": customer_id, "lim": limit})
        if not results:
            uncertainties.append(f"No transaction history for customer {customer_id} in TigerGraph")
            return evidence, uncertainties

        txn_list: list[dict] = []
        for block in results:
            txn_list.extend(_v_list(block, "Txns"))

        if not txn_list:
            uncertainties.append(f"Customer {customer_id} has no transactions in graph")
            return evidence, uncertainties

        # Summarise history as one evidence item (don't send every transaction to LLM)
        amounts = []
        channels: set[str] = set()
        regions: set[str] = set()
        timestamps = []

        for v in txn_list:
            a = _vattr(v)
            try:
                amounts.append(float(a.get("transaction_amt", 0) or 0))
            except (ValueError, TypeError):
                pass
            ch = a.get("channel", "")
            if ch:
                channels.add(ch)
            r = str(a.get("addr2", "") or "")
            if r:
                regions.add(r)
            ts = a.get("ts", "")
            if ts:
                timestamps.append(ts)

        avg_amt = round(sum(amounts) / len(amounts), 2) if amounts else 0
        max_amt = round(max(amounts), 2) if amounts else 0

        evidence.append(ProvenanceItem(
            claim=(
                f"Customer {customer_id} has {len(txn_list)} transaction(s) in graph: "
                f"avg ${avg_amt}, max ${max_amt}, "
                f"channels={sorted(channels)}, "
                f"regions={sorted(regions)[:5]}"
            ),
            source_type=SourceType.tigergraph,
            entity_type=EntityType.customer,
            entity_ids=[customer_id],
            query_name="get_customer_history",
            relationship="customer_transaction_history",
            raw_data={
                "count": len(txn_list),
                "avg_amt": avg_amt,
                "max_amt": max_amt,
                "channels": list(channels),
                "regions": list(regions)[:10],
                "first_ts": min(timestamps) if timestamps else "",
                "last_ts": max(timestamps) if timestamps else "",
            },
            relevance_score=0.85,
            confidence=1.0,
            evidence_type="observed_fact",
        ))

        return evidence, uncertainties

    async def get_connected_cards(
        self, card_id: str
    ) -> tuple[list[ProvenanceItem], list[str]]:
        """Run find_connected_cards."""
        evidence: list[ProvenanceItem] = []
        uncertainties: list[str] = []

        results = await self._run("find_connected_cards", {"card": card_id})
        if not results:
            return evidence, uncertainties

        card_ids: list[str] = []
        for block in results:
            raw = block.get("card_ids")
            if isinstance(raw, list):
                card_ids.extend([str(x) for x in raw if x])
            elif isinstance(raw, set):
                card_ids.extend([str(x) for x in raw if x])

        if card_ids:
            evidence.append(ProvenanceItem(
                claim=(
                    f"Card {card_id} is connected to {len(card_ids)} other card(s) "
                    f"via shared customer: {card_ids[:5]}"
                ),
                source_type=SourceType.tigergraph,
                entity_type=EntityType.card,
                entity_ids=[card_id] + card_ids[:5],
                query_name="find_connected_cards",
                relationship="connected_card_network",
                raw_data={"connected_card_ids": card_ids},
                relevance_score=0.80,
                confidence=1.0,
                evidence_type="observed_fact",
            ))
        else:
            evidence.append(ProvenanceItem(
                claim=f"No other cards connected to {card_id} in graph",
                source_type=SourceType.tigergraph,
                entity_type=EntityType.card,
                entity_ids=[card_id],
                query_name="find_connected_cards",
                relationship="connected_card_network",
                raw_data={},
                relevance_score=0.3,
                confidence=1.0,
                evidence_type="observed_fact",
            ))

        return evidence, uncertainties

    async def get_shared_identity(
        self, txn_id: str
    ) -> tuple[list[ProvenanceItem], list[str]]:
        """Run find_shared_identity — are other transactions using the same device?"""
        evidence: list[ProvenanceItem] = []
        uncertainties: list[str] = []

        results = await self._run("find_shared_identity", {"txn": txn_id})
        if not results:
            return evidence, uncertainties

        for block in results:
            other_txns = _v_list(block, "OtherTxns")
            shared = block.get("shared_signals", {})

            if other_txns:
                evidence.append(ProvenanceItem(
                    claim=(
                        f"Transaction {txn_id} shares its identity/device record "
                        f"with {len(other_txns)} other transaction(s): "
                        f"{[v.get('v_id', '') for v in other_txns[:5]]}"
                    ),
                    source_type=SourceType.tigergraph,
                    entity_type=EntityType.identity,
                    entity_ids=[txn_id] + [v.get("v_id", "") for v in other_txns[:5]],
                    query_name="find_shared_identity",
                    relationship="shared_identity_signal",
                    raw_data={"other_txns": len(other_txns), "shared": shared},
                    relevance_score=0.88,
                    confidence=1.0,
                    evidence_type="observed_fact",
                ))
            else:
                uncertainties.append(
                    f"No shared identity signals found for transaction {txn_id}"
                )

        return evidence, uncertainties

    async def get_prior_fraud_cases(
        self, customer_id: str, card_id: str
    ) -> tuple[list[ProvenanceItem], list[str]]:
        """Run find_prior_fraud_cases — any existing FraudCase vertices for this entity."""
        evidence: list[ProvenanceItem] = []
        uncertainties: list[str] = []

        results = await self._run(
            "find_prior_fraud_cases",
            {"customer": customer_id, "card": card_id},
        )
        if not results:
            return evidence, uncertainties

        cases: list[dict] = []
        for block in results:
            cases.extend(_v_list(block, "cases"))
            # Some versions return AllCases directly
            if not cases:
                cases.extend(_v_list(block, "AllCases"))

        if cases:
            for v in cases:
                attrs = _vattr(v)
                evidence.append(ProvenanceItem(
                    claim=(
                        f"Prior fraud case {v.get('v_id', '?')} found in graph: "
                        f"outcome={attrs.get('outcome', '?')}, "
                        f"pattern={attrs.get('pattern', '?')}, "
                        f"exposure=${attrs.get('exposure_usd', 0)}"
                    ),
                    source_type=SourceType.tigergraph,
                    entity_type=EntityType.fraud_case,
                    entity_ids=[v.get("v_id", ""), customer_id],
                    query_name="find_prior_fraud_cases",
                    relationship="historical_fraud_case",
                    raw_data=attrs,
                    relevance_score=0.92,
                    confidence=1.0,
                    evidence_type="observed_fact",
                ))
        else:
            uncertainties.append(
                f"No prior fraud cases in graph for customer {customer_id} / card {card_id}"
            )

        return evidence, uncertainties

    async def get_behavioral_anomalies(
        self, card_id: str
    ) -> tuple[list[ProvenanceItem], list[str]]:
        """Run find_behavioral_anomalies for velocity analysis."""
        evidence: list[ProvenanceItem] = []
        uncertainties: list[str] = []

        results = await self._run("find_behavioral_anomalies", {"card": card_id})
        if not results:
            uncertainties.append(f"No behavioral data retrieved for card {card_id}")
            return evidence, uncertainties

        for block in results:
            count = block.get("txn_count", 0)
            total = block.get("total_amount", 0)
            max_a = block.get("max_amount", 0)
            min_a = block.get("min_amount", 0)

            if count:
                avg = round(total / count, 2) if count else 0
                evidence.append(ProvenanceItem(
                    claim=(
                        f"Card {card_id} behavioral profile (last 100 txns): "
                        f"count={count}, avg=${avg}, max=${max_a}, min=${min_a}"
                    ),
                    source_type=SourceType.tigergraph,
                    entity_type=EntityType.behavioral,
                    entity_ids=[card_id],
                    query_name="find_behavioral_anomalies",
                    relationship="transaction_velocity",
                    raw_data={
                        "txn_count": count,
                        "total": total,
                        "avg": avg,
                        "max": max_a,
                        "min": min_a,
                    },
                    relevance_score=0.75,
                    confidence=1.0,
                    evidence_type="observed_fact",
                ))

        return evidence, uncertainties

    async def get_card_transactions(
        self, card_id: str, limit: int = 50
    ) -> tuple[list[ProvenanceItem], list[str]]:
        """Run find_card_transactions for recent transaction list."""
        evidence: list[ProvenanceItem] = []
        uncertainties: list[str] = []

        results = await self._run("find_card_transactions", {"card": card_id, "lim": limit})
        if not results:
            return evidence, uncertainties

        txn_list: list[dict] = []
        for block in results:
            txn_list.extend(_v_list(block, "Txns"))

        if txn_list:
            amounts = []
            online_count = 0
            for v in txn_list:
                a = _vattr(v)
                try:
                    amounts.append(float(a.get("transaction_amt", 0) or 0))
                except (ValueError, TypeError):
                    pass
                if a.get("channel") == "online":
                    online_count += 1

            evidence.append(ProvenanceItem(
                claim=(
                    f"Card {card_id} recent transactions: {len(txn_list)} total, "
                    f"{online_count} online, "
                    f"avg ${round(sum(amounts)/len(amounts), 2) if amounts else 0}"
                ),
                source_type=SourceType.tigergraph,
                entity_type=EntityType.card,
                entity_ids=[card_id] + [v.get("v_id", "") for v in txn_list[:5]],
                query_name="find_card_transactions",
                relationship="card_transaction_history",
                raw_data={
                    "count": len(txn_list),
                    "online_count": online_count,
                    "txn_ids": [v.get("v_id", "") for v in txn_list[:10]],
                },
                relevance_score=0.80,
                confidence=1.0,
                evidence_type="observed_fact",
            ))

        return evidence, uncertainties

    # ── Bulk retrieval for an investigation ───────────────────────────────────

    async def retrieve_all(
        self,
        txn_id: str,
        card_id: str,
        customer_id: str,
    ) -> tuple[list[ProvenanceItem], list[str], list[str]]:
        """
        Run all investigation-relevant queries in parallel.
        Returns (evidence_items, uncertainty_notes, queries_executed).
        """
        self._queries_executed = []

        # Run queries concurrently where safe
        results = await asyncio.gather(
            self.get_transaction_full_context(txn_id),
            self.get_customer_history(customer_id),
            self.get_connected_cards(card_id),
            self.get_shared_identity(txn_id),
            self.get_prior_fraud_cases(customer_id, card_id),
            self.get_behavioral_anomalies(card_id),
            self.get_card_transactions(card_id),
            return_exceptions=True,
        )

        all_evidence: list[ProvenanceItem] = []
        all_uncertainties: list[str] = []

        for r in results:
            if isinstance(r, Exception):
                logger.warning("GraphRetriever parallel query failed: %s", r)
                all_uncertainties.append(f"Query failed: {r}")
            else:
                ev, unc = r
                all_evidence.extend(ev)
                all_uncertainties.extend(unc)

        return all_evidence, all_uncertainties, self._queries_executed
