"""
eval/calibrate.py

Two jobs:

1. Measure how well-calibrated the agent's raw `fraud_probability` is against
   closed-case outcomes (Brier score + reliability diagram), using a
   held-out slice that is NEVER used to fit anything (section 14 of the
   README: "a held-out slice that is never used to tune anything").

2. Fit a correction (isotonic regression, monotonic and simple - avoids
   overfitting a 5,565-row backtest the way a higher-capacity model would)
   on a SEPARATE calibration slice, and save it so `agent/assess.py` can
   apply it to the LLM's raw probability before it's written into any
   answer file.

Split (fixed, not random, to respect the temporal leakage rule):
  - fit slice:      closed cases opened in months 1-3 (Jul-Sep)
  - held-out slice: closed cases opened in month 4 (Oct)  <- report metrics here, never fit on it
  - the 20 benchmark cases are touched only after this script has run once
    and the agent is frozen.

Usage:
    python -m eval.calibrate --predictions data/backtest_predictions.csv \
                              --output models/probability_calibrator.pkl

`predictions.csv` is produced by running the (uncalibrated) agent over the
backtest closed cases and dumping one row per case:
    case_id, opened_at, raw_fraud_probability, actual_outcome
where actual_outcome is 1 for confirmed_fraud, 0 for cleared.
"""

from __future__ import annotations

import argparse
import json
import pickle
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import brier_score_loss


FIT_CUTOFF = "2016-10-01"     # opened_at < this -> fit slice (Jul-Sep)
HOLDOUT_CUTOFF = "2016-11-01"  # this <= opened_at < this -> held-out slice (Oct)


def load_predictions(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, parse_dates=["opened_at"])
    required = {"case_id", "opened_at", "raw_fraud_probability", "actual_outcome"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"predictions file missing columns: {missing}")
    if not df["actual_outcome"].isin([0, 1]).all():
        raise ValueError("actual_outcome must be 0 (cleared) or 1 (confirmed_fraud)")
    return df


def split(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    fit = df[df["opened_at"] < FIT_CUTOFF]
    holdout = df[(df["opened_at"] >= FIT_CUTOFF) & (df["opened_at"] < HOLDOUT_CUTOFF)]
    if len(fit) < 200:
        raise ValueError(f"fit slice too small ({len(fit)} rows) to calibrate reliably")
    if len(holdout) < 50:
        raise ValueError(f"held-out slice too small ({len(holdout)} rows) for a trustworthy metric")
    return fit, holdout


def reliability_table(y_true: np.ndarray, y_pred: np.ndarray, n_bins: int = 10) -> pd.DataFrame:
    bins = np.linspace(0, 1, n_bins + 1)
    bin_ids = np.clip(np.digitize(y_pred, bins) - 1, 0, n_bins - 1)
    rows = []
    for b in range(n_bins):
        mask = bin_ids == b
        if mask.sum() == 0:
            continue
        rows.append({
            "bin_range": f"{bins[b]:.1f}-{bins[b+1]:.1f}",
            "n": int(mask.sum()),
            "mean_predicted": float(y_pred[mask].mean()),
            "actual_fraud_rate": float(y_true[mask].mean()),
            "gap": float(y_pred[mask].mean() - y_true[mask].mean()),
        })
    return pd.DataFrame(rows)


def rebalance_to_target_prevalence(df: pd.DataFrame, target_prevalence: float, seed: int = 0) -> pd.DataFrame:
    """
    Closed-case history is ~84% fraud; the benchmark is described as ~50%
    legitimate. Fitting/reporting on the raw 84%-fraud distribution risks
    baking in the wrong prior (see README section 14, "the base-rate trap").
    This downsamples the majority class so metrics and the fitted
    calibrator reflect the benchmark's expected balance instead.
    """
    rng = np.random.default_rng(seed)
    pos = df[df.actual_outcome == 1]
    neg = df[df.actual_outcome == 0]
    # solve for n_pos given n_neg fixed at its size, or vice versa, whichever downsamples
    if len(pos) / len(df) > target_prevalence:
        n_pos = int(round(len(neg) * target_prevalence / (1 - target_prevalence)))
        n_pos = min(n_pos, len(pos))
        pos = pos.sample(n=n_pos, random_state=seed)
    else:
        n_neg = int(round(len(pos) * (1 - target_prevalence) / target_prevalence))
        n_neg = min(n_neg, len(neg))
        neg = neg.sample(n=n_neg, random_state=seed)
    return pd.concat([pos, neg]).sample(frac=1, random_state=seed).reset_index(drop=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--predictions", required=True, help="CSV: case_id, opened_at, raw_fraud_probability, actual_outcome")
    ap.add_argument("--output", default="models/probability_calibrator.pkl")
    ap.add_argument("--target-prevalence", type=float, default=0.5,
                     help="Rebalance fit/report to this fraud prevalence (benchmark is ~50%%, closed-case history is ~84%%)")
    ap.add_argument("--report", default="models/calibration_report.json")
    args = ap.parse_args()

    df = load_predictions(args.predictions)
    fit_df, holdout_df = split(df)

    print(f"fit slice:     {len(fit_df)} cases ({fit_df.actual_outcome.mean():.1%} fraud)")
    print(f"held-out slice:{len(holdout_df)} cases ({holdout_df.actual_outcome.mean():.1%} fraud)")

    fit_bal = rebalance_to_target_prevalence(fit_df, args.target_prevalence)
    holdout_bal = rebalance_to_target_prevalence(holdout_df, args.target_prevalence, seed=1)
    print(f"fit slice (rebalanced to {args.target_prevalence:.0%}):     {len(fit_bal)} cases")
    print(f"held-out slice (rebalanced to {args.target_prevalence:.0%}): {len(holdout_bal)} cases")

    # --- Before calibration ---
    raw_brier = brier_score_loss(holdout_bal.actual_outcome, holdout_bal.raw_fraud_probability)
    raw_table = reliability_table(holdout_bal.actual_outcome.values, holdout_bal.raw_fraud_probability.values)
    print("\n=== RAW (uncalibrated) reliability, held-out slice ===")
    print(raw_table.to_string(index=False))
    print(f"Raw Brier score: {raw_brier:.4f}  (lower is better; 0 = perfect, 0.25 = uninformative coin flip)")

    # --- Fit isotonic calibrator on the FIT slice only ---
    calibrator = IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0)
    calibrator.fit(fit_bal.raw_fraud_probability.values, fit_bal.actual_outcome.values)

    # --- After calibration, measured on the untouched held-out slice ---
    calibrated_pred = calibrator.predict(holdout_bal.raw_fraud_probability.values)
    cal_brier = brier_score_loss(holdout_bal.actual_outcome, calibrated_pred)
    cal_table = reliability_table(holdout_bal.actual_outcome.values, calibrated_pred, n_bins=10)
    print("\n=== CALIBRATED reliability, held-out slice ===")
    print(cal_table.to_string(index=False))
    print(f"Calibrated Brier score: {cal_brier:.4f}  (delta vs raw: {cal_brier - raw_brier:+.4f})")

    if cal_brier > raw_brier:
        print(
            "\nWARNING: calibration made the held-out Brier score worse. "
            "The raw probabilities may already be reasonably calibrated, or "
            "the fit slice is too small/unrepresentative. Consider not "
            "applying the calibrator, or gathering more backtest cases first."
        )

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "wb") as f:
        pickle.dump(calibrator, f)
    print(f"\nSaved calibrator to {args.output}")

    report = {
        "fit_n": len(fit_bal),
        "holdout_n": len(holdout_bal),
        "target_prevalence": args.target_prevalence,
        "raw_brier": raw_brier,
        "calibrated_brier": cal_brier,
        "raw_reliability": raw_table.to_dict(orient="records"),
        "calibrated_reliability": cal_table.to_dict(orient="records"),
        "apply_calibrator": bool(cal_brier <= raw_brier),
    }
    Path(args.report).parent.mkdir(parents=True, exist_ok=True)
    with open(args.report, "w") as f:
        json.dump(report, f, indent=2)
    print(f"Saved report to {args.report}")


if __name__ == "__main__":
    main()
