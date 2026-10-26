"""Score a saved model on a labelled CSV and print the metrics (useful after importing new data).

Usage:  python ml/evaluate_model.py ml/artifacts/model_v1.joblib ml/sample_data/students_sample.csv
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import numpy as np

from common import load_series
from app.ml.features import compute_features, to_row
from app.ml.pipeline import classification_metrics


def main() -> None:
    """Evaluate on every labelled student in the CSV."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("model", type=Path)
    parser.add_argument("csv", type=Path)
    parser.add_argument("--threshold", type=float, default=0.3)
    args = parser.parse_args()

    bundle = joblib.load(args.model)
    series, _ = load_series(args.csv)
    rows, labels = [], []
    for student in series:
        features = compute_features(student.points, student.grade)
        if features is not None and student.dropped_out is not None:
            rows.append(to_row(features))
            labels.append(int(student.dropped_out))
    if not rows:
        raise SystemExit("No labelled students found (the CSV needs a dropped_out column).")
    metrics = classification_metrics(np.array(labels), bundle.predict_proba(rows), args.threshold)
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
