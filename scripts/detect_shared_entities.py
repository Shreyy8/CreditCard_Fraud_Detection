"""Find cross-customer device and billing-region neighbors for case profiles."""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path


def rows(path: Path):
    with path.open("r", newline="", encoding="utf-8") as handle:
        yield from csv.DictReader(handle)


def parse_ts(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)


def profile(row: dict[str, str]) -> str:
    return " | ".join(row.get(field, "") for field in ("DeviceInfo", "id_30", "id_31", "id_33"))


def detect(data_dir: Path, profiles_path: Path, mapping_path: Path) -> dict:
    profiles = json.loads(profiles_path.read_text(encoding="utf-8"))
    mapping = {row["TransactionID"]: row["card_id"] for row in rows(mapping_path) if row["card_id"]}
    targets: dict[str, dict] = {}
    for case in profiles:
        flagged_ts = parse_ts(case["flagged_transaction"]["ts"])
        targets[case["case_id"]] = {
            "customer_id": case["trigger"]["customer_id"],
            "opened_at": flagged_ts,
            "start": flagged_ts - timedelta(hours=48),
            "end": flagged_ts + timedelta(hours=48),
            "devices": set(case["window_48h"]["device_profiles"]),
            "regions": set(case["window_48h"]["billing_regions"]),
        }

    device_transactions: defaultdict[str, set[str]] = defaultdict(set)
    for identity in rows(data_dir / "identity.csv"):
        current_profile = profile(identity)
        for target in targets.values():
            if current_profile in target["devices"]:
                device_transactions[current_profile].add(identity["TransactionID"])

    transaction_rows: dict[str, dict] = {}
    wanted_transactions = {transaction_id for values in device_transactions.values() for transaction_id in values}
    for transaction in rows(data_dir / "transactions.csv"):
        if transaction["TransactionID"] in wanted_transactions:
            transaction_rows[transaction["TransactionID"]] = transaction

    result = {}
    for case_id, target in targets.items():
        shared_devices = {}
        for device in target["devices"]:
            matches = []
            for transaction_id in device_transactions.get(device, set()):
                transaction = transaction_rows.get(transaction_id)
                if transaction is None:
                    continue
                transaction_ts = parse_ts(transaction["ts"])
                if target["start"] <= transaction_ts <= target["end"]:
                    matches.append({
                        "transaction_id": transaction_id,
                        "customer_id": transaction["customer_id"],
                        "card_id": mapping.get(transaction_id, ""),
                        "ts": transaction["ts"],
                        "amount": transaction["TransactionAmt"],
                    })
            if matches:
                shared_devices[device] = matches
        result[case_id] = {
            "shared_devices": shared_devices,
            "connected_customer_ids": sorted({
                match["customer_id"]
                for matches in shared_devices.values()
                for match in matches
                if match["customer_id"] != target["customer_id"]
            }),
            "connected_card_ids": sorted({
                match["card_id"]
                for matches in shared_devices.values()
                for match in matches
                if match["card_id"] and match["card_id"] != mapping.get(next(
                    transaction_id for transaction_id in wanted_transactions
                    if transaction_id in transaction_rows and transaction_rows[transaction_id]["customer_id"] == target["customer_id"]
                ), "")
            }),
        }
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path("DataSet"))
    parser.add_argument("--profiles", type=Path, default=Path("artifacts/case_profiles.json"))
    parser.add_argument("--mapping", type=Path, default=Path("artifacts/transaction_cards.csv"))
    parser.add_argument("--output", type=Path, default=Path("artifacts/shared_entities.json"))
    args = parser.parse_args()
    result = detect(args.data_dir, args.profiles, args.mapping)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({case_id: {
        "connected_customers": len(value["connected_customer_ids"]),
        "connected_cards": len(value["connected_card_ids"]),
    } for case_id, value in result.items()}, indent=2))


if __name__ == "__main__":
    main()