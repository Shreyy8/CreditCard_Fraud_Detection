"""Apply a frozen calibrator to benchmark answer probabilities."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from agent.investigation.calibration import load_calibrator


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--answers", type=Path, default=Path("cases"))
    parser.add_argument("--calibrator", type=Path, default=Path("models/probability_calibrator.json"))
    parser.add_argument("--report", type=Path, default=Path("artifacts/benchmark_probabilities.json"))
    args = parser.parse_args()
    calibrator = load_calibrator(args.calibrator)
    probabilities = []
    for path in sorted(args.answers.glob("*.json")):
        answer = json.loads(path.read_text(encoding="utf-8"))
        raw = float(answer["case"]["fraud_probability"])
        calibrated = round(calibrator.predict(raw), 6)
        answer["case"]["fraud_probability_raw"] = raw
        answer["case"]["fraud_probability"] = calibrated
        path.write_text(json.dumps(answer, indent=2), encoding="utf-8")
        probabilities.append({"case_id": answer["case_id"], "raw": raw, "calibrated": calibrated})
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(probabilities, indent=2), encoding="utf-8")
    print(f"calibrated {len(probabilities)} benchmark answers")


if __name__ == "__main__":
    main()