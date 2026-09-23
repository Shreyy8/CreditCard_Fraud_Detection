"""Generate pre-outcome probability predictions for closed-case backtesting.

The scorer intentionally reads only transaction features and structural case
metadata. It does not read pattern, outcome, actions, report status, or notes.
Those fields are joined only after scoring to create evaluation labels.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


def rows(path: Path):
    with path.open("r", newline="", encoding="utf-8") as handle:
        yield from csv.DictReader(handle)


def clamp(value: float) -> float:
    return max(0.01, min(0.99, value))


def score_case(case: dict[str, str], transaction: dict[str, str] | None) -> float:
    """Score only signals available before the closed-case outcome."""
    score = 0.35
    if transaction:
        risk_score = transaction.get("risk_score", "")
        if risk_score:
            score = 0.20 + 0.60 * float(risk_score)
        if transaction.get("channel") == "online":
            score += 0.04
        if transaction.get("ProductCD") not in {"", "W"}:
            score += 0.02
    try:
        transaction_count = int(case.get("n_txns") or 0)
        score += min(0.12, max(0, transaction_count - 1) * 0.03)
    except ValueError:
        pass
    if case.get("connected_card_ids", "").strip():
        score += 0.10
    try:
        score += min(0.08, float(case.get("exposure_usd") or 0.0) / 10000.0)
    except ValueError:
        pass
    return round(clamp(score), 6)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path("DataSet"))
    parser.add_argument("--output", type=Path, default=Path("artifacts/backtest_predictions.csv"))
    args = parser.parse_args()

    wanted_ids = {row["first_fraud_txn_id"] for row in rows(args.data_dir / "closed_cases_history.csv") if row.get("first_fraud_txn_id")}
    transactions = {
        row["TransactionID"]: row
        for row in rows(args.data_dir / "transactions.csv")
        if row["TransactionID"] in wanted_ids
    }
    output_rows = []
    for case in rows(args.data_dir / "closed_cases_history.csv"):
        transaction = transactions.get(case.get("first_fraud_txn_id", ""))
        output_rows.append({
            "case_id": case["case_id"],
            "opened_at": case["opened_at"],
            "raw_fraud_probability": score_case(case, transaction),
            "actual_outcome": 1 if case["outcome"] == "confirmed_fraud" else 0,
        })
    output_rows.sort(key=lambda row: row["opened_at"])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(output_rows[0]))
        writer.writeheader()
        writer.writerows(output_rows)
    print(f"wrote {len(output_rows)} predictions to {args.output}")


if __name__ == "__main__":
    main()