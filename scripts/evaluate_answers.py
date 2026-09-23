"""Produce structural benchmark and historical evaluation metrics."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path

from agent.investigation.validator import build_dataset_index, validate_answer


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def historical_metrics(predictions_path: Path) -> dict:
    with predictions_path.open("r", newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        return {}
    actual = [int(row["actual_outcome"]) for row in rows]
    raw = [float(row["raw_fraud_probability"]) for row in rows]
    return {
        "n": len(rows),
        "accuracy_at_0_5": sum((value >= 0.5) == bool(label) for value, label in zip(raw, actual)) / len(rows),
        "brier_score": sum((value - label) ** 2 for value, label in zip(raw, actual)) / len(rows),
        "fraud_prevalence": sum(actual) / len(actual),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--answers", type=Path, default=Path("cases"))
    parser.add_argument("--data-dir", type=Path, default=Path("DataSet"))
    parser.add_argument("--mapping", type=Path, default=Path("artifacts/transaction_cards.csv"))
    parser.add_argument("--predictions", type=Path, default=Path("artifacts/backtest_predictions.csv"))
    parser.add_argument("--calibration", type=Path, default=Path("artifacts/calibration_report.json"))
    parser.add_argument("--output", type=Path, default=Path("artifacts/evaluation_report.json"))
    args = parser.parse_args()

    index = build_dataset_index(args.data_dir, args.mapping)
    answers = [read_json(path) for path in sorted(args.answers.glob("*.json"))]
    errors = {answer.get("case_id", "unknown"): validate_answer(answer, index) for answer in answers}
    valid_answers = [answer for answer in answers if not errors[answer.get("case_id", "unknown")]]
    final_actions = [item for answer in valid_answers for item in answer["next_best_actions"]["final"]]
    reports = [answer for answer in valid_answers if answer["sar"]["file"]]
    changed = [answer for answer in valid_answers if answer["next_best_actions"]["what_changed"] != "nothing"]
    exposures = [float(answer["case"]["exposure_usd"]) for answer in valid_answers]
    report = {
        "answer_count": len(answers),
        "valid_answer_count": len(valid_answers),
        "validation_failure_count": sum(bool(value) for value in errors.values()),
        "verdict_counts": dict(Counter(answer["case"]["verdict"] for answer in valid_answers)),
        "pattern_counts": dict(Counter(answer["case"]["pattern"] for answer in valid_answers)),
        "sar_file_count": len(reports),
        "action_count": len(final_actions),
        "action_counts": dict(Counter(item["action"] for item in final_actions)),
        "evidence_request_transition_count": len(changed),
        "mean_exposure_usd": round(sum(exposures) / len(exposures), 2) if exposures else 0.0,
        "total_exposure_usd": round(sum(exposures), 2),
        "historical_prediction_metrics": historical_metrics(args.predictions),
        "calibration_report": read_json(args.calibration) if args.calibration.exists() else None,
        "accuracy_note": "Benchmark ground-truth labels are hidden; accuracy here is reported only for historical closed-case predictions.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    raise SystemExit(1 if report["validation_failure_count"] else 0)


if __name__ == "__main__":
    main()