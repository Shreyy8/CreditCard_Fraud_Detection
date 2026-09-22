"""Resolve transaction card IDs from the supplied card fields.

Known links from closed cases and the case pack are treated as anchors. For a
customer, remaining signatures are assigned only to unused K slots when the
number of signatures makes that assignment forced. Customers with no anchor
remain explicitly marked as inferred so downstream code cannot mistake a
heuristic for ground truth.
"""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path

CARD_FIELDS = ("card1", "card2", "card3", "card4", "card5", "card6")


def rows(path: Path):
    with path.open("r", newline="", encoding="utf-8") as handle:
        yield from csv.DictReader(handle)


def signature(row: dict[str, str]) -> tuple[str, ...]:
    return tuple(row.get(field, "") for field in CARD_FIELDS)


def known_links(data_dir: Path) -> dict[str, str]:
    links: dict[str, str] = {}
    for row in rows(data_dir / "closed_cases_history.csv"):
        for transaction_id in row["txn_ids"].split("|"):
            if transaction_id:
                links[transaction_id] = row["card_id"]
    for row in rows(data_dir / "case_pack.csv"):
        links[row["flagged_txn_id"]] = row["card_id"]
    return links


def build_signature_map(data_dir: Path) -> tuple[dict[tuple[str, tuple[str, ...]], str], set[str]]:
    links = known_links(data_dir)
    all_signatures: defaultdict[str, set[tuple[str, ...]]] = defaultdict(set)
    anchored: dict[tuple[str, tuple[str, ...]], str] = {}
    customers_with_anchors: set[str] = set()

    for row in rows(data_dir / "transactions.csv"):
        customer_id = row["customer_id"]
        current_signature = signature(row)
        all_signatures[customer_id].add(current_signature)
        expected_card = links.get(row["TransactionID"])
        if expected_card is not None:
            key = (customer_id, current_signature)
            previous = anchored.get(key)
            if previous is not None and previous != expected_card:
                raise ValueError(f"conflicting card anchors for {key}: {previous}, {expected_card}")
            anchored[key] = expected_card
            customers_with_anchors.add(customer_id)

    for customer_id, customer_signatures in all_signatures.items():
        anchored_for_customer = {
            current_signature: card_id.rsplit("-K", 1)[-1]
            for (anchored_customer, current_signature), card_id in anchored.items()
            if anchored_customer == customer_id
        }
        used_slots = set(anchored_for_customer.values())
        remaining_signatures = sorted(set(customer_signatures) - set(anchored_for_customer))
        remaining_slots = sorted(
            {str(slot) for slot in range(1, len(customer_signatures) + 1)} - used_slots,
            key=int,
        )
        if len(remaining_signatures) == len(remaining_slots):
            for current_signature, slot in zip(remaining_signatures, remaining_slots):
                anchored[(customer_id, current_signature)] = f"{customer_id}-K{slot}"

    return anchored, customers_with_anchors


def derive(data_dir: Path, output: Path) -> dict[str, int]:
    mapping, anchored_customers = build_signature_map(data_dir)
    links = known_links(data_dir)
    output.parent.mkdir(parents=True, exist_ok=True)
    rows_written = 0
    verified_rows = 0
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["TransactionID", "customer_id", "card_id", "mapping_source"])
        writer.writeheader()
        for row in rows(data_dir / "transactions.csv"):
            card_id = mapping.get((row["customer_id"], signature(row)), "")
            is_verified = row["TransactionID"] in links
            writer.writerow({
                "TransactionID": row["TransactionID"],
                "customer_id": row["customer_id"],
                "card_id": card_id,
                "mapping_source": "known_anchor" if is_verified else ("unresolved" if not card_id else (
                    "anchored_customer" if row["customer_id"] in anchored_customers else "inferred"
                )),
            })
            rows_written += 1
            verified_rows += is_verified
            if is_verified and card_id != links[row["TransactionID"]]:
                raise ValueError(f"derived card mismatch for transaction {row['TransactionID']}")
    unresolved_rows = sum(1 for row in rows(data_dir / "transactions.csv") if not mapping.get((row["customer_id"], signature(row))) )
    return {
        "rows": rows_written,
        "known_links_verified": verified_rows,
        "anchored_customers": len(anchored_customers),
        "unresolved_rows": unresolved_rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path("DataSet"))
    parser.add_argument("--output", type=Path, default=Path("artifacts/transaction_cards.csv"))
    args = parser.parse_args()
    print(derive(args.data_dir, args.output))


if __name__ == "__main__":
    main()