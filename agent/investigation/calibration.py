"""Small dependency-free isotonic probability calibrator.

The fit data must come from a temporal backtest, never from benchmark answer
outcomes. The implementation uses the pool-adjacent-violators algorithm and
stores only the fitted probability knots.
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ProbabilityCalibrator:
    knots: tuple[tuple[float, float], ...]

    def predict(self, raw_probability: float) -> float:
        if not self.knots:
            return max(0.0, min(1.0, raw_probability))
        value = max(0.0, min(1.0, raw_probability))
        if value <= self.knots[0][0]:
            return self.knots[0][1]
        for (left_x, left_y), (right_x, right_y) in zip(self.knots, self.knots[1:]):
            if value <= right_x:
                fraction = (value - left_x) / (right_x - left_x) if right_x != left_x else 0.0
                return left_y + fraction * (right_y - left_y)
        return self.knots[-1][1]


def fit_isotonic(raw_probabilities: list[float], outcomes: list[int]) -> ProbabilityCalibrator:
    if len(raw_probabilities) != len(outcomes) or not raw_probabilities:
        raise ValueError("raw probabilities and outcomes must be non-empty and the same length")
    ordered = sorted((max(0.0, min(1.0, float(raw))), int(outcome)) for raw, outcome in zip(raw_probabilities, outcomes))
    blocks: list[list[float]] = []
    for raw, outcome in ordered:
        blocks.append([raw, raw, float(outcome), 1.0])
        while len(blocks) >= 2 and blocks[-2][2] / blocks[-2][3] > blocks[-1][2] / blocks[-1][3]:
            right = blocks.pop()
            left = blocks.pop()
            blocks.append([left[0], right[1], left[2] + right[2], left[3] + right[3]])
    knots = tuple((block[1], block[2] / block[3]) for block in blocks)
    return ProbabilityCalibrator(knots)


def fit_from_csv(path: Path) -> ProbabilityCalibrator:
    with path.open("r", newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    required = {"raw_fraud_probability", "actual_outcome"}
    if not rows or not required.issubset(rows[0]):
        raise ValueError(f"predictions CSV must contain {sorted(required)}")
    return fit_isotonic(
        [float(row["raw_fraud_probability"]) for row in rows],
        [int(row["actual_outcome"]) for row in rows],
    )


def save_calibrator(calibrator: ProbabilityCalibrator, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"knots": calibrator.knots}, indent=2), encoding="utf-8")


def load_calibrator(path: Path) -> ProbabilityCalibrator:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return ProbabilityCalibrator(tuple((float(x), float(y)) for x, y in payload["knots"]))