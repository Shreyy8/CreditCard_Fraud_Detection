"""Stream and verify the supplied fraud-investigation dataset.

This is intentionally independent of TigerGraph. It establishes the local
data contract before a graph load can turn a bad identity mapping into bad
investigation evidence.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path


EXPECTED_TRANSACTION_COLUMNS = 397
EXPECTED_IDENTITY_COLUMNS = 41
DATASET_START = datetime(2016, 7, 2)
CARD_FIELDS = ("card1", "card2", "card3", "card4", "card5", "card6")


def read_rows(path: Path):
    with path.open("r", newline="", encoding="utf-8") as handle:
        yield from csv.DictReader(handle)


def card_signature(row: dict[str, str]) -> tuple[str, ...]:
    return tuple(row.get(field, "") for field in CARD_FIELDS)


def collect_known_card_links(data_dir: Path) -> dict[str, str]:
    links: dict[str, str] = {}
    for row in read_rows(data_dir / "closed_cases_history.csv"):
        for transaction_id in row["txn_ids"].split("|"):
            if transaction_id:
                links[transaction_id] = row["card_id"]
    for row in read_rows(data_dir / "case_pack.csv"):
        links[row["flagged_txn_id"]] = row["card_id"]
    return links


def verify(data_dir: Path) -> dict:
    transaction_path = data_dir / "transactions.csv"
    identity_path = data_dir / "identity.csv"
    case_path = data_dir / "case_pack.csv"
    closed_path = data_dir / "closed_cases_history.csv"

    with transaction_path.open("r", newline="", encoding="utf-8") as handle:
        transaction_reader = csv.DictReader(handle)
        transaction_columns = transaction_reader.fieldnames or []
        transaction_count = 0
        identity_like_rows = 0
        bad_timestamps = 0
        bad_channels = 0
        transaction_ids: set[str] = set()
        known_links = collect_known_card_links(data_dir)
        known_rows: dict[str, tuple[str, tuple[str, ...]]] = {}
        signatures_by_customer: defaultdict[str, set[tuple[str, ...]]] = defaultdict(set)

        for row in transaction_reader:
            transaction_count += 1
            transaction_id = row["TransactionID"]
            transaction_ids.add(transaction_id)
            customer_id = row["customer_id"]
            signatures_by_customer[customer_id].add(card_signature(row))
            if row["channel"] == "online":
                identity_like_rows += 1
            if (row["ProductCD"] == "W") != (row["channel"] == "in_person"):
                bad_channels += 1
            try:
                expected_ts = DATASET_START + timedelta(seconds=int(row["TransactionDT"]))
                actual_ts = datetime.fromisoformat(row["ts"].replace("Z", "+00:00")).replace(tzinfo=None)
                if actual_ts != expected_ts:
                    bad_timestamps += 1
            except (TypeError, ValueError):
                bad_timestamps += 1
            if transaction_id in known_links:
                known_rows[transaction_id] = (customer_id, card_signature(row))

    identity_count = sum(1 for _ in read_rows(identity_path))
    case_rows = list(read_rows(case_path))
    closed_rows = list(read_rows(closed_path))

    expected_by_signature: defaultdict[tuple[str, tuple[str, ...]], set[str]] = defaultdict(set)
    for transaction_id, expected_card in known_links.items():
        if transaction_id in known_rows:
            customer_id, signature = known_rows[transaction_id]
            expected_by_signature[(customer_id, signature)].add(expected_card)

    signature_conflicts = {
        f"{customer_id}:{signature}": sorted(cards)
        for (customer_id, signature), cards in expected_by_signature.items()
        if len(cards) > 1
    }

    missing_known_transactions = sorted(set(known_links) - set(known_rows))
    known_cards_by_customer: defaultdict[str, set[str]] = defaultdict(set)
    for expected_card in known_links.values():
        customer_id = expected_card.split("-K", 1)[0]
        known_cards_by_customer[customer_id].add(expected_card)
    resolution_warning_customers = sorted(
        customer_id
        for customer_id, signatures in signatures_by_customer.items()
        if customer_id not in known_cards_by_customer
        or len(signatures) > len(known_cards_by_customer[customer_id])
    )
    return {
        "transactions": {
            "rows": transaction_count,
            "columns": len(transaction_columns),
            "expected_columns": EXPECTED_TRANSACTION_COLUMNS,
            "ids_unique": len(transaction_ids) == transaction_count,
            "online_rows": identity_like_rows,
            "bad_channel_rows": bad_channels,
            "bad_timestamp_rows": bad_timestamps,
        },
        "identity": {"rows": identity_count, "expected_columns": EXPECTED_IDENTITY_COLUMNS},
        "closed_cases": {
            "rows": len(closed_rows),
            "outcomes": dict(Counter(row["outcome"] for row in closed_rows)),
        },
        "case_pack": {"rows": len(case_rows), "case_ids": [row["case_id"] for row in case_rows]},
        "card_mapping": {
            "known_transaction_links": len(known_links),
            "missing_known_transactions": missing_known_transactions,
            "customers": len(signatures_by_customer),
            "max_signatures_per_customer": max(map(len, signatures_by_customer.values())),
            "signature_conflicts": signature_conflicts,
            "resolution_warning_customers": resolution_warning_customers,
            "mapping_is_unambiguous": (
                not signature_conflicts
                and not missing_known_transactions
                and not resolution_warning_customers
            ),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path("DataSet"))
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON")
    args = parser.parse_args()
    report = verify(args.data_dir)
    if args.json:
        print(json.dumps(report, indent=2))
        return
    print(json.dumps(report, indent=2))
    if not report["card_mapping"]["mapping_is_unambiguous"]:
        raise SystemExit("Dataset verification found ambiguous card mappings")


if __name__ == "__main__":
    main()