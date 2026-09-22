"""Build local, structured evidence profiles for the 20 benchmark cases.

The profiler is the pre-graph reference implementation. It uses no fraud
labels from transactions and only retrieves closed cases that predate each
benchmark case.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path


CORE_FIELDS = (
    "TransactionID", "TransactionDT", "TransactionAmt", "ProductCD", "addr1", "addr2",
    "P_emaildomain", "R_emaildomain", "customer_id", "ts", "channel", "risk_score",
)
IDENTITY_FIELDS = ("DeviceType", "DeviceInfo", "id_15", "id_23", "id_30", "id_31", "id_33")
WINDOW_HOURS = 48


def read_rows(path: Path):
    with path.open("r", newline="", encoding="utf-8") as handle:
        yield from csv.DictReader(handle)


def parse_ts(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)


def compact_transaction(row: dict[str, str], card_by_transaction: dict[str, str]) -> dict:
    result = {field: row.get(field, "") for field in CORE_FIELDS}
    result["card_id"] = card_by_transaction.get(row["TransactionID"], "")
    return result


def device_profile(identity: dict[str, str]) -> str:
    return " | ".join(identity.get(field, "") for field in ("DeviceInfo", "id_30", "id_31", "id_33"))


def build_profiles(data_dir: Path, mapping_path: Path) -> list[dict]:
    case_rows = sorted(read_rows(data_dir / "case_pack.csv"), key=lambda row: row["opened_at"])
    case_by_customer: defaultdict[str, list[dict]] = defaultdict(list)
    for case in case_rows:
        case_by_customer[case["customer_id"]].append(case)

    card_by_transaction: dict[str, str] = {}
    for row in read_rows(mapping_path):
        if row["card_id"]:
            card_by_transaction[row["TransactionID"]] = row["card_id"]

    customer_ids = set(case_by_customer)
    transactions_by_customer: defaultdict[str, list[dict]] = defaultdict(list)
    transaction_by_id: dict[str, dict] = {}
    for row in read_rows(data_dir / "transactions.csv"):
        if row["customer_id"] in customer_ids:
            compact = compact_transaction(row, card_by_transaction)
            compact["_ts"] = parse_ts(row["ts"])
            transactions_by_customer[row["customer_id"]].append(compact)
            transaction_by_id[row["TransactionID"]] = compact

    identity_by_transaction: dict[str, dict] = {}
    relevant_transaction_ids = set(transaction_by_id)
    for row in read_rows(data_dir / "identity.csv"):
        if row["TransactionID"] in relevant_transaction_ids:
            identity_by_transaction[row["TransactionID"]] = {
                field: row.get(field, "") for field in IDENTITY_FIELDS
            }

    closed_rows = list(read_rows(data_dir / "closed_cases_history.csv"))
    profiles = []
    for case in case_rows:
        flagged = transaction_by_id.get(case["flagged_txn_id"])
        if flagged is None:
            raise ValueError(f"flagged transaction missing: {case['flagged_txn_id']}")
        opened_at = parse_ts(case["opened_at"])
        customer_transactions = transactions_by_customer[case["customer_id"]]
        window_start = parse_ts(flagged["ts"]) - timedelta(hours=WINDOW_HOURS)
        window_end = parse_ts(flagged["ts"]) + timedelta(hours=WINDOW_HOURS)
        window = [
            transaction for transaction in customer_transactions
            if window_start <= parse_ts(transaction["ts"]) <= window_end
        ]
        devices = {
            device_profile(identity_by_transaction[transaction["TransactionID"]])
            for transaction in window
            if transaction["TransactionID"] in identity_by_transaction
            and device_profile(identity_by_transaction[transaction["TransactionID"]]).strip(" | ")
        }
        regions = sorted({transaction["addr1"] for transaction in window if transaction["addr1"]})
        prior_cases = [
            {
                "case_id": row["case_id"],
                "outcome": row["outcome"],
                "pattern": row["pattern"],
                "card_id": row["card_id"],
                "exposure_usd": row["exposure_usd"],
                "analyst_notes": row["analyst_notes"],
            }
            for row in closed_rows
            if parse_ts(row["closed_at"]) < opened_at
            and (row["customer_id"] == case["customer_id"] or row["card_id"] == case["card_id"])
        ]
        profiles.append({
            "case_id": case["case_id"],
            "opened_at": case["opened_at"],
            "trigger": {key: case[key] for key in case if key != "case_id"},
            "flagged_transaction": {key: value for key, value in flagged.items() if key != "_ts"},
            "customer_history": {
                "transaction_count": len(customer_transactions),
                "online_count": sum(transaction["channel"] == "online" for transaction in customer_transactions),
                "amount_total_usd": round(sum(abs(float(transaction["TransactionAmt"])) for transaction in customer_transactions), 2),
                "known_card_ids": sorted({transaction["card_id"] for transaction in customer_transactions if transaction["card_id"]}),
            },
            "window_48h": {
                "transaction_count": len(window),
                "transactions": [{key: value for key, value in transaction.items() if key != "_ts"} for transaction in window],
                "device_profiles": sorted(devices),
                "billing_regions": regions,
            },
            "identity": {
                transaction_id: identity_by_transaction[transaction_id]
                for transaction_id in (transaction["TransactionID"] for transaction in window)
                if transaction_id in identity_by_transaction
            },
            "similar_prior_cases": prior_cases,
        })
    return profiles


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path("DataSet"))
    parser.add_argument("--mapping", type=Path, default=Path("artifacts/transaction_cards.csv"))
    parser.add_argument("--output", type=Path, default=Path("artifacts/case_profiles.json"))
    args = parser.parse_args()
    profiles = build_profiles(args.data_dir, args.mapping)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as handle:
        json.dump(profiles, handle, indent=2)
    print(f"wrote {len(profiles)} profiles to {args.output}")
    print(json.dumps({
        "case_ids": [profile["case_id"] for profile in profiles],
        "window_transaction_counts": {
            profile["case_id"]: profile["window_48h"]["transaction_count"] for profile in profiles
        },
    }, indent=2))


if __name__ == "__main__":
    main()