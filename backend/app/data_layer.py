"""
Local CSV data layer.

Loads transactions, identity, and closed cases into memory-efficient
structures. Used as:
  1. Primary fallback when TigerGraph is unavailable
  2. Graph loading source (schema population)
  3. Evidence gathering for the agent

All data is READ-ONLY — we never modify source files.
"""

from __future__ import annotations

import csv
import logging
import os
from collections import defaultdict
from pathlib import Path
from typing import Any, Optional

from .config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Resolve dataset paths relative to project root (parent of backend/)
_PROJECT_ROOT = Path(__file__).parent.parent.parent


def _resolve_path(setting_path: str) -> str:
    """Return absolute path, resolving relative paths from project root."""
    p = Path(setting_path)
    if p.is_absolute():
        return str(p)
    # Try relative to cwd first
    if p.exists():
        return str(p)
    # Try relative to project root
    candidate = _PROJECT_ROOT / p
    if candidate.exists():
        return str(candidate)
    return str(p)  # Return original if not found — caller handles missing


# ── Lazy-loaded data stores ───────────────────────────────────────────────────

class DataLayer:
    """Singleton data access layer over the CSV files."""

    _instance: Optional["DataLayer"] = None
    _loaded: bool = False

    def __init__(self) -> None:
        # Core data
        self.transactions: dict[str, dict] = {}          # txn_id → row
        self.identity: dict[str, dict] = {}              # txn_id → identity row
        self.closed_cases: dict[str, dict] = {}          # case_id → case row
        self.case_pack: dict[str, dict] = {}             # case_id → pack row

        # Indexes for fast lookup
        self.card_transactions: dict[str, list[str]] = defaultdict(list)      # card_id → [txn_ids]
        self.customer_transactions: dict[str, list[str]] = defaultdict(list)  # customer_id → [txn_ids]
        self.customer_cards: dict[str, set[str]] = defaultdict(set)           # customer_id → {card_ids}
        self.device_transactions: dict[str, list[str]] = defaultdict(list)    # device_key → [txn_ids]
        self.email_transactions: dict[str, list[str]] = defaultdict(list)     # email → [txn_ids]
        self.region_transactions: dict[str, list[str]] = defaultdict(list)    # addr1 → [txn_ids]
        self.customer_cases: dict[str, list[str]] = defaultdict(list)         # customer_id → [case_ids]
        self.card_cases: dict[str, list[str]] = defaultdict(list)             # card_id → [case_ids]
        self.transaction_cards: dict[str, dict[str, str]] = {}                # txn_id → derived mapping

    @classmethod
    def get(cls) -> "DataLayer":
        if cls._instance is None:
            cls._instance = DataLayer()
        if not cls._instance._loaded:
            cls._instance._load()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Force reload — useful in tests."""
        cls._instance = None

    def _load(self) -> None:
        logger.info("Loading CSV data into memory...")
        self._load_case_pack()
        self._load_closed_cases()
        self._load_transaction_cards()
        self._load_transactions()
        self._load_identity()
        self._loaded = True
        logger.info(
            "Data loaded: %d txns, %d identity, %d closed cases, %d case pack",
            len(self.transactions),
            len(self.identity),
            len(self.closed_cases),
            len(self.case_pack),
        )

    def _load_case_pack(self) -> None:
        path = _resolve_path(settings.case_pack_csv)
        if not os.path.exists(path):
            logger.warning("Case pack not found: %s", path)
            return
        with open(path, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                self.case_pack[row["case_id"]] = row

    def _load_closed_cases(self) -> None:
        path = _resolve_path(settings.closed_cases_csv)
        if not os.path.exists(path):
            logger.warning("Closed cases not found: %s", path)
            return
        with open(path, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                cid = row["case_id"]
                self.closed_cases[cid] = row
                self.customer_cases[row["customer_id"]].append(cid)
                self.card_cases[row["card_id"]].append(cid)

    def _load_transactions(self) -> None:
        path = _resolve_path(settings.transactions_csv)
        if not os.path.exists(path):
            logger.warning("Transactions CSV not found: %s", path)
            return
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                tid = row["TransactionID"]
                mapping = self.transaction_cards.get(tid, {})
                card_id = mapping.get("card_id", "")
                if card_id:
                    row["card_id"] = card_id
                self.transactions[tid] = row
                customer_id = row.get("customer_id", "")
                if card_id:
                    self.card_transactions[card_id].append(tid)
                if customer_id:
                    self.customer_transactions[customer_id].append(tid)
                if card_id and customer_id:
                    self.customer_cards[customer_id].add(card_id)
                # email index
                for e_col in ("P_emaildomain", "R_emaildomain"):
                    e = row.get(e_col, "").strip()
                    if e:
                        self.email_transactions[e].append(tid)
                # region index
                r = row.get("addr1", "").strip()
                if r:
                    self.region_transactions[r].append(tid)

    def _load_transaction_cards(self) -> None:
        """Load the derived card mapping without treating unresolved rows as cards."""
        path = _resolve_path(settings.transaction_cards_csv)
        if not os.path.exists(path):
            logger.warning("Transaction card mapping not found: %s", path)
            return
        with open(path, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                transaction_id = row.get("TransactionID", "")
                card_id = row.get("card_id", "").strip()
                if transaction_id:
                    self.transaction_cards[transaction_id] = {
                        "customer_id": row.get("customer_id", "").strip(),
                        "card_id": card_id,
                        "mapping_source": row.get("mapping_source", "").strip(),
                    }

    def _load_identity(self) -> None:
        path = _resolve_path(settings.identity_csv)
        if not os.path.exists(path):
            logger.warning("Identity CSV not found: %s", path)
            return
        with open(path, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                tid = row["TransactionID"]
                self.identity[tid] = row
                # device index
                device_key = self._device_key(row)
                if device_key:
                    self.device_transactions[device_key].append(tid)

    @staticmethod
    def _device_key(identity_row: dict) -> str:
        parts = [
            identity_row.get("DeviceInfo", "").strip(),
            identity_row.get("id_30", "").strip(),  # OS
            identity_row.get("id_31", "").strip(),  # browser
            identity_row.get("id_33", "").strip(),  # screen
        ]
        key = " | ".join(p for p in parts if p)
        return key if key != " |  |  | " else ""

    # ── Public query methods ─────────────────────────────────────────────────

    def get_transaction(self, txn_id: str) -> Optional[dict]:
        return self.transactions.get(str(txn_id))

    def get_identity(self, txn_id: str) -> Optional[dict]:
        return self.identity.get(str(txn_id))

    def get_card_transactions(self, card_id: str, limit: int = 200) -> list[dict]:
        """Get transactions for a card_id. card_id format: C01234-K1."""
        txn_ids = self.card_transactions.get(card_id, [])
        txns = [self.transactions[tid] for tid in txn_ids[-limit:] if tid in self.transactions]
        return sorted(txns, key=lambda r: r.get("ts", ""))

    def get_customer_transactions(self, customer_id: str, limit: int = 200) -> list[dict]:
        txn_ids = self.customer_transactions.get(customer_id, [])
        txns = [self.transactions[tid] for tid in txn_ids if tid in self.transactions]
        return sorted(txns, key=lambda r: r.get("ts", ""))[-limit:]

    def get_closed_cases_for_customer(self, customer_id: str) -> list[dict]:
        return [
            self.closed_cases[cid]
            for cid in self.customer_cases.get(customer_id, [])
            if cid in self.closed_cases
        ]

    def get_closed_cases_for_card(self, card_id: str) -> list[dict]:
        # card_id e.g. C12382-K1 — try both exact and prefix
        cases = [
            self.closed_cases[cid]
            for cid in self.card_cases.get(card_id, [])
            if cid in self.closed_cases
        ]
        if not cases:
            # Try customer prefix
            prefix = card_id.split("-")[0]
            customer_id = prefix
            cases = self.get_closed_cases_for_customer(customer_id)
        return cases

    def get_transactions_by_device(self, device_key: str, limit: int = 100) -> list[dict]:
        txn_ids = self.device_transactions.get(device_key, [])[:limit]
        return [self.transactions[tid] for tid in txn_ids if tid in self.transactions]

    def get_transactions_by_region(self, region: str, limit: int = 200) -> list[dict]:
        txn_ids = self.region_transactions.get(region, [])[:limit]
        return [self.transactions[tid] for tid in txn_ids if tid in self.transactions]

    def find_similar_closed_cases(
        self,
        pattern: str | None,
        customer_id: str,
        card_id: str,
        max_results: int = 5,
    ) -> list[dict]:
        """Retrieve closed cases similar to current investigation."""
        results = []
        # Same customer / card first
        for case in self.get_closed_cases_for_customer(customer_id):
            if case not in results:
                results.append(case)
        for case in self.get_closed_cases_for_card(card_id):
            if case not in results:
                results.append(case)
        # Same pattern from broader pool
        if pattern and pattern != "none":
            for case in self.closed_cases.values():
                if case.get("pattern") == pattern and case not in results:
                    results.append(case)
                    if len(results) >= max_results * 2:
                        break
        return results[:max_results]

    def get_all_case_pack_rows(self) -> list[dict]:
        return list(self.case_pack.values())

    def get_case_pack_row(self, case_id: str) -> Optional[dict]:
        return self.case_pack.get(case_id)


def get_data_layer() -> DataLayer:
    return DataLayer.get()
