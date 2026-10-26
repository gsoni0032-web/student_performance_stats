"""Train and evaluate the dropout model from a CSV, without the web app or a database.

Usage:
    python ml/train_from_csv.py ml/sample_data/students_sample.csv --out ml/artifacts

Writes model_vN.joblib and metrics_vN.json (the same artefacts the API stores) and prints a
report. Dropout is the positive class and recall on it is prioritised, so the report shows
recall and precision at the flagging threshold as well as the threshold-free scores.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib

from common import load_series
from app.ml.pipeline import build_frames, train


def main() -> None:
    """Run training and save the artefacts."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("csv", type=Path)
    parser.add_argument("--out", type=Path, default=Path("ml/artifacts"))
    parser.add_argument("--models", default="logreg,random_forest,xgboost")
    parser.add_argument("--iterations", type=int, default=12, help="hyper-parameter search iterations per model")
    parser.add_argument("--flag-threshold", type=float, default=0.3)
    parser.add_argument("--high-threshold", type=float, default=0.6)
    args = parser.parse_args()

    series, _ = load_series(args.csv)
    clf_frame, reg_frame = build_frames(series)
    bundle = train(
        clf_frame, reg_frame,
        flag_threshold=args.flag_threshold, high_threshold=args.high_threshold,
        candidates=[m.strip() for m in args.models.split(",") if m.strip()],
        search_iterations=args.iterations,
    )
    args.out.mkdir(parents=True, exist_ok=True)
    version = 1 + max(
        (int(p.stem.split("_v")[1]) for p in args.out.glob("model_v*.joblib")), default=0
    )
    bundle.version = version
    bundle.metrics["version"] = version
    joblib.dump(bundle, args.out / f"model_v{version}.joblib", compress=3)
    (args.out / f"metrics_v{version}.json").write_text(json.dumps(bundle.metrics, indent=2))

    flagged = bundle.metrics["test_at_flag_threshold"]
    print(f"Best model: {bundle.model_type}   saved as version {version} in {args.out}")
    for name, report in bundle.metrics["candidates"].items():
        print(f"  {name:14s} validation PR-AUC {report['val_pr_auc']:.3f}  ROC-AUC {report['val_roc_auc']:.3f}")
    print(f"Held-out test set at threshold {flagged['threshold']}:")
    for key in ("accuracy", "precision", "recall", "f1", "roc_auc", "pr_auc"):
        print(f"  {key:10s} {flagged[key]:.3f}")
    print(f"  confusion matrix {flagged['confusion_matrix']}")
    regression = bundle.metrics.get("regression")
    if regression:
        print(f"Next-term score: MAE {regression['mae']} (baseline {regression['baseline_mae']}), R2 {regression['r2']}")


if __name__ == "__main__":
    main()
