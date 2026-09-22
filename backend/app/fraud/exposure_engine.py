"""
Exposure calculator.

Determines the financial and entity scope of a fraud episode.
All values come from actual transaction data — nothing is fabricated.
"""

from __future__ import annotations

from typing import Any


class ExposureResult:
    def __init__(self) -> None:
        self.affected_txn_ids: list[str] = []
        self.first_suspicious_txn_id: str = ""
        self.connected_card_ids: list[str] = []
        self.connected_device_profiles: list[str] = []
        self.exposure_usd: float = 0.0
        self.affected_accounts: int = 0
        self.affected_cards: int = 0
        self.affected_devices: int = 0
        self.merchant_exposure: dict[str, float] = {}


class ExposureEngine:
    """
    Calculates exposure from the fraud episode.

    Uses only transactions we have evidence to include.
    Does not speculate about transactions with no supporting evidence.
    """

    def calculate(
        self,
        flagged_txn: dict[str, Any],
        related_transactions: list[dict[str, Any]],
        connected_cards: list[str],
        shared_devices: list[dict[str, Any]],
    ) -> ExposureResult:
        result = ExposureResult()

        # Include flagged transaction
        all_txns = {flagged_txn.get("TransactionID", ""): flagged_txn}

        # Add related transactions that share the same fraud episode
        for t in related_transactions:
            tid = t.get("TransactionID", "")
            if tid and tid not in all_txns:
                all_txns[tid] = t

        # Calculate exposure from included transactions
        total = 0.0
        earliest_ts = None
        merchant_exposure: dict[str, float] = {}

        for tid, txn in all_txns.items():
            if not tid:
                continue
            result.affected_txn_ids.append(tid)
            try:
                amt = abs(float(txn.get("TransactionAmt", 0) or 0))
                total += amt
                # Merchant proxy via P_emaildomain
                merchant = txn.get("P_emaildomain", "unknown") or "unknown"
                merchant_exposure[merchant] = merchant_exposure.get(merchant, 0) + amt
            except (ValueError, TypeError):
                pass
            ts = txn.get("ts", "")
            if ts and (earliest_ts is None or ts < earliest_ts):
                earliest_ts = ts

        result.exposure_usd = round(total, 2)
        result.merchant_exposure = merchant_exposure

        # First suspicious transaction
        if earliest_ts:
            for tid, txn in all_txns.items():
                if txn.get("ts") == earliest_ts:
                    result.first_suspicious_txn_id = tid
                    break
        if not result.first_suspicious_txn_id and result.affected_txn_ids:
            result.first_suspicious_txn_id = result.affected_txn_ids[0]

        # Connected cards and devices
        result.connected_card_ids = [c for c in connected_cards if c]
        result.affected_cards = len(set(result.connected_card_ids)) + 1  # +1 for primary card

        device_profiles = set()
        for dev in shared_devices:
            key = dev.get("device_key", "")
            if key:
                device_profiles.add(key)
        result.connected_device_profiles = list(device_profiles)
        result.affected_devices = len(device_profiles)

        return result
