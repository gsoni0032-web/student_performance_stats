"""Compare error rates across groups. For auditing only: group data is never a model input.

The model sees academic signals only. Group attributes (for example gender or a scholarship
flag) live in a separate file and are joined on student_code purely to measure whether the
model's mistakes fall unevenly on some groups.

Usage:
    python ml/fairness_check.py MODEL.joblib DATA.csv GROUPS.csv [--group-column audit_group]

GROUPS.csv needs a student_code column and one column per attribute to audit.
Exit code is 0 when no gap exceeds --max-gap, 2 otherwise (handy in CI or a release checklist).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from common import load_series
from app.ml.features import compute_features, to_row


def group_rates(truth: np.ndarray, flagged: np.ndarray) -> dict[str, float | int | None]:
    """Counts and error rates for one group (None when a rate has no denominator)."""
    positives, negatives = int((truth == 1).sum()), int((truth == 0).sum())
    tp = int(((truth == 1) & (flagged == 1)).sum())
    fp = int(((truth == 0) & (flagged == 1)).sum())
    return {
        "students": int(len(truth)),
        "dropout_rate": round(float(truth.mean()), 3),
        "flag_rate": round(float(flagged.mean()), 3),
        "recall": None if positives == 0 else round(tp / positives, 3),
        "missed_dropout_rate": None if positives == 0 else round(1 - tp / positives, 3),
        "false_positive_rate": None if negatives == 0 else round(fp / negatives, 3),
        "precision": None if (tp + fp) == 0 else round(tp / (tp + fp), 3),
    }


def main() -> int:
    """Print per-group rates and flag gaps larger than the allowed maximum."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("model", type=Path)
    parser.add_argument("data", type=Path)
    parser.add_argument("groups", type=Path)
    parser.add_argument("--group-column", action="append", help="column(s) to audit; default: all but student_code")
    parser.add_argument("--threshold", type=float, default=0.3)
    parser.add_argument("--max-gap", type=float, default=0.10, help="largest tolerated gap in recall or FPR")
    parser.add_argument("--min-group-size", type=int, default=30)
    parser.add_argument("--json", type=Path, help="also write the full report as JSON")
    args = parser.parse_args()

    bundle = joblib.load(args.model)
    series, codes = load_series(args.data)
    rows, labels, kept = [], [], []
    for code, student in zip(codes, series, strict=True):
        features = compute_features(student.points, student.grade)
        if features is not None and student.dropped_out is not None:
            rows.append(to_row(features))
            labels.append(int(student.dropped_out))
            kept.append(code)
    if not rows:
        raise SystemExit("No labelled students found in the data file.")

    frame = pd.DataFrame(
        {"student_code": kept, "truth": labels, "flagged": (bundle.predict_proba(rows) >= args.threshold).astype(int)}
    )
    groups = pd.read_csv(args.groups, dtype=str)
    merged = frame.merge(groups, on="student_code", how="inner")
    if merged.empty:
        raise SystemExit("No student_code values match between the data and the groups file.")
    columns = args.group_column or [c for c in groups.columns if c != "student_code"]

    report: dict[str, dict[str, dict[str, float | int | None]]] = {}
    worst_gap = 0.0
    for column in columns:
        report[column] = {}
        for value, part in merged.groupby(column):
            if len(part) < args.min_group_size:
                continue
            report[column][str(value)] = group_rates(part["truth"].to_numpy(), part["flagged"].to_numpy())
        print(f"\n{column}  (threshold {args.threshold})")
        print(f"  {'group':20s} {'n':>5s} {'dropout':>8s} {'flagged':>8s} {'recall':>7s} {'FPR':>6s} {'prec.':>6s}")
        for name, r in report[column].items():
            show = lambda v: "  n/a" if v is None else f"{v:5.2f}"  # noqa: E731
            print(f"  {name:20s} {r['students']:5d} {r['dropout_rate']:8.2f} {r['flag_rate']:8.2f} "
                  f"{show(r['recall']):>7s} {show(r['false_positive_rate']):>6s} {show(r['precision']):>6s}")
        for metric in ("recall", "false_positive_rate"):
            values = [r[metric] for r in report[column].values() if r[metric] is not None]
            if len(values) >= 2:
                gap = max(values) - min(values)
                worst_gap = max(worst_gap, gap)
                print(f"  gap in {metric}: {gap:.2f}")

    if args.json:
        args.json.write_text(json.dumps(report, indent=2))
    if worst_gap > args.max_gap:
        print(f"\nLargest gap {worst_gap:.2f} exceeds {args.max_gap:.2f}: review before relying on this model.")
        return 2
    print(f"\nLargest gap {worst_gap:.2f} is within {args.max_gap:.2f}. Small groups can still hide problems.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
