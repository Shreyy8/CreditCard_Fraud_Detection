"""Fit a dependency-free isotonic calibrator from temporal backtest predictions."""

from __future__ import annotations

import argparse
from pathlib import Path

from agent.investigation.calibration import fit_from_csv, save_calibrator


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("predictions", type=Path)
    parser.add_argument("--output", type=Path, default=Path("models/probability_calibrator.json"))
    args = parser.parse_args()
    calibrator = fit_from_csv(args.predictions)
    save_calibrator(calibrator, args.output)
    print(f"saved {len(calibrator.knots)} calibration knots to {args.output}")


if __name__ == "__main__":
    main()