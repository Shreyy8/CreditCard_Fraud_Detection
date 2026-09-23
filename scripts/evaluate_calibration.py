"""Fit and evaluate temporal probability calibration without third-party packages."""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime
from pathlib import Path

from agent.investigation.calibration import fit_isotonic, save_calibrator


FIT_CUTOFF = datetime.fromisoformat("2016-10-01")
HOLDOUT_CUTOFF = datetime.fromisoformat("2016-11-01")


def load(path: Path) -> list[dict]:
    with path.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def brier(rows: list[dict], field: str) -> float:
    return sum((float(row[field]) - int(row["actual_outcome"])) ** 2 for row in rows) / len(rows)


def reliability(rows: list[dict], field: str, bins: int = 10) -> list[dict]:
    report = []
    for bucket in range(bins):
        low = bucket / bins
        high = (bucket + 1) / bins
        selected = [row for row in rows if low <= float(row[field]) < high or (bucket == bins - 1 and float(row[field]) == high)]
        if not selected:
            continue
        predicted = sum(float(row[field]) for row in selected) / len(selected)
        actual = sum(int(row["actual_outcome"]) for row in selected) / len(selected)
        report.append({
            "bin_range": f"{low:.1f}-{high:.1f}",
            "n": len(selected),
            "mean_predicted": round(predicted, 6),
            "actual_fraud_rate": round(actual, 6),
            "gap": round(predicted - actual, 6),
        })
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--predictions", type=Path, default=Path("artifacts/backtest_predictions.csv"))
    parser.add_argument("--calibrator", type=Path, default=Path("models/probability_calibrator.json"))
    parser.add_argument("--report", type=Path, default=Path("artifacts/calibration_report.json"))
    args = parser.parse_args()

    all_rows = load(args.predictions)
    fit_rows = [row for row in all_rows if datetime.fromisoformat(row["opened_at"]) < FIT_CUTOFF]
    holdout_rows = [row for row in all_rows if FIT_CUTOFF <= datetime.fromisoformat(row["opened_at"]) < HOLDOUT_CUTOFF]
    if not fit_rows or not holdout_rows:
        raise ValueError("temporal fit and holdout slices must both contain rows")

    calibrator = fit_isotonic(
        [float(row["raw_fraud_probability"]) for row in fit_rows],
        [int(row["actual_outcome"]) for row in fit_rows],
    )
    for row in holdout_rows:
        row["calibrated_probability"] = round(calibrator.predict(float(row["raw_fraud_probability"])), 6)
    raw_brier = brier(holdout_rows, "raw_fraud_probability")
    calibrated_brier = brier(holdout_rows, "calibrated_probability")
    apply_calibrator = calibrated_brier <= raw_brier
    save_calibrator(calibrator, args.calibrator)
    report = {
        "fit_cutoff_exclusive": FIT_CUTOFF.isoformat(sep=" "),
        "holdout_start_inclusive": FIT_CUTOFF.isoformat(sep=" "),
        "holdout_cutoff_exclusive": HOLDOUT_CUTOFF.isoformat(sep=" "),
        "fit_n": len(fit_rows),
        "holdout_n": len(holdout_rows),
        "raw_brier": round(raw_brier, 8),
        "calibrated_brier": round(calibrated_brier, 8),
        "apply_calibrator": apply_calibrator,
        "raw_reliability": reliability(holdout_rows, "raw_fraud_probability"),
        "calibrated_reliability": reliability(holdout_rows, "calibrated_probability"),
        "calibrator_knots": len(calibrator.knots),
        "source_predictions": str(args.predictions),
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()