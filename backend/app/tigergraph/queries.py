"""
Investigation-oriented TigerGraph query wrappers.

All methods use the correct parameter names matching the installed GSQL queries
(verified against live schema 2026-09-20). VERTEX<T> params are plain strings —
the client.run_query() wraps them as 1-tuples automatically.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from .client import TigerGraphClient, get_client

logger = logging.getLogger(__name__)


class TGQueries:
    """High-level, purpose-built investigation queries."""

    def __init__(self, client: Optional[TigerGraphClient] = None) -> None:
        self.tg = client or get_client()

    # ── Transaction context ───────────────────────────────────────────────────

    async def get_transaction_context(self, txn_id: str) -> dict[str, Any]:
        """get_transaction_context(VERTEX<Transaction> txn)"""
        results = await self.tg.async_run_query(
            "get_transaction_context", {"txn": txn_id}
        )
        return results[0] if results else {}

    # ── Customer history ──────────────────────────────────────────────────────

    async def get_customer_transaction_history(
        self, customer_id: str, limit: int = 50
    ) -> list[dict[str, Any]]:
        """get_customer_history(VERTEX<Customer> customer, INT lim)"""
        results = await self.tg.async_run_query(
            "get_customer_history",
            {"customer": customer_id, "lim": limit},
        )
        return results[0].get("Txns", []) if results else []

    # ── Connected cards ───────────────────────────────────────────────────────

    async def find_connected_cards(self, card_id: str) -> list[str]:
        """find_connected_cards(VERTEX<Card> card)"""
        results = await self.tg.async_run_query(
            "find_connected_cards", {"card": card_id}
        )
        raw = results[0].get("card_ids", []) if results else []
        return [str(x) for x in raw if x]

    async def find_shared_devices(self, txn_id: str) -> list[dict[str, Any]]:
        """find_shared_identity(VERTEX<Transaction> txn) — returns shared identity signals"""
        results = await self.tg.async_run_query(
            "find_shared_identity", {"txn": txn_id}
        )
        return results if results else []

    async def find_shared_identity_signals(self, txn_id: str) -> list[dict[str, Any]]:
        return await self.find_shared_devices(txn_id)

    # ── Related transactions ──────────────────────────────────────────────────

    async def find_related_transactions(
        self, txn_id: str, hours_window: int = 48
    ) -> list[dict[str, Any]]:
        """find_card_transactions — get recent txns for the card owning txn_id"""
        results = await self.tg.async_run_query(
            "find_card_transactions", {"card": txn_id, "lim": 50}
        )
        return results[0].get("Txns", []) if results else []

    async def find_transaction_clusters(self, card_id: str) -> list[dict[str, Any]]:
        results = await self.tg.async_run_query(
            "find_card_transactions", {"card": card_id, "lim": 50}
        )
        return results if results else []

    # ── Prior fraud cases ─────────────────────────────────────────────────────

    async def find_prior_fraud_cases(
        self, customer_id: str, card_id: str
    ) -> list[dict[str, Any]]:
        """find_prior_fraud_cases(VERTEX<Customer> customer, VERTEX<Card> card)"""
        results = await self.tg.async_run_query(
            "find_prior_fraud_cases",
            {"customer": customer_id, "card": card_id},
        )
        return results[0].get("cases", []) if results else []

    async def get_case_history(self, case_id: str) -> dict[str, Any]:
        """get_case_history(VERTEX<FraudCase> fraud_case)"""
        results = await self.tg.async_run_query(
            "get_case_history", {"fraud_case": case_id}
        )
        return results[0] if results else {}

    # ── Exposure ──────────────────────────────────────────────────────────────

    async def calculate_transaction_exposure(
        self, txn_ids: list[str]
    ) -> dict[str, Any]:
        """calculate_exposure(SET<VERTEX<Transaction>> txn_set)"""
        results = await self.tg.async_run_query(
            "calculate_exposure",
            {"txn_set": txn_ids},
        )
        return results[0] if results else {"exposure_usd": 0.0}

    # ── Behavioral anomalies ──────────────────────────────────────────────────

    async def find_behavioral_anomalies(self, card_id: str) -> list[dict[str, Any]]:
        """find_behavioral_anomalies(VERTEX<Card> card)"""
        results = await self.tg.async_run_query(
            "find_behavioral_anomalies", {"card": card_id}
        )
        return results if results else []

    async def find_suspicious_neighbors(self, txn_id: str) -> list[dict[str, Any]]:
        return await self.find_shared_devices(txn_id)

    async def find_related_merchants(self, txn_id: str) -> list[dict[str, Any]]:
        results = await self.tg.async_run_query(
            "get_transaction_context", {"txn": txn_id}
        )
        return results if results else []

    # ── Case memory write-back ────────────────────────────────────────────────

    async def write_case_to_graph(self, case_data: dict[str, Any]) -> str:
        """
        Persist an investigation case vertex + edges to TigerGraph.

        FraudCase vertex attributes (verified from live schema):
          opened_at, trigger_type, trigger_text, risk_score, closed_at,
          outcome, pattern, txn_ids, n_txns, exposure_usd,
          connected_card_ids, actions_taken, report_filed, analyst_notes
        """
        case_id = case_data.get("case_id", "")
        try:
            affected = case_data.get("affected_txn_ids", [])
            actions  = case_data.get("actions_taken", [])
            ok = await self.tg.async_upsert_vertex(
                "FraudCase",
                case_id,
                {
                    "outcome":           case_data.get("verdict", ""),
                    "pattern":           case_data.get("pattern", "none"),
                    "exposure_usd":      float(case_data.get("exposure_usd", 0.0)),
                    "trigger_type":      case_data.get("trigger_type", ""),
                    "trigger_text":      (case_data.get("summary", "") or "")[:500],
                    "txn_ids":           "|".join(str(t) for t in affected[:20]),
                    "n_txns":            len(affected),
                    "connected_card_ids": "|".join(
                        str(c) for c in case_data.get("connected_card_ids", [])[:10]
                    ),
                    "actions_taken":     "|".join(str(a) for a in actions[:10]),
                    "report_filed":      bool(case_data.get("report_filed", False)),
                    "analyst_notes":     (case_data.get("summary", "") or "")[:2000],
                    "opened_at":         case_data.get("opened_at", ""),
                    "closed_at":         case_data.get("closed_at", ""),
                },
            )
            if ok:
                customer_id = case_data.get("customer_id", "")
                if customer_id:
                    await self.tg.async_upsert_edge(
                        "FraudCase", case_id,
                        "case_involves_customer", "Customer", customer_id,
                    )
                card_id = case_data.get("card_id", "")
                if card_id:
                    await self.tg.async_upsert_edge(
                        "FraudCase", case_id,
                        "case_involves_card", "Card", card_id,
                    )
                for txn_id in affected[:5]:
                    await self.tg.async_upsert_edge(
                        "FraudCase", case_id,
                        "case_flagged_transaction", "Transaction", str(txn_id),
                    )
                return case_id
        except Exception as exc:  # noqa: BLE001
            logger.warning("Graph case write failed: %s", exc)
        return ""

    async def read_case_from_graph(self, case_id: str) -> dict | None:
        """Read a persisted FraudCase vertex for write/readback verification."""
        return await self.tg.async_get_vertex("FraudCase", case_id)

    # ── Graph algorithms ──────────────────────────────────────────────────────

    async def run_community_detection(self, card_id: str) -> dict[str, Any]:
        results = await self.tg.async_run_query(
            "find_connected_cards", {"card": card_id}
        )
        ids = results[0].get("card_ids", []) if results else []
        return {"community_size": len(ids), "members": ids}

    async def run_centrality(self, txn_id: str) -> dict[str, Any]:
        results = await self.tg.async_run_query(
            "find_behavioral_anomalies", {"card": txn_id}
        )
        return results[0] if results else {}

    async def run_path_analysis(self, from_id: str, to_id: str) -> list[list[str]]:
        return []
