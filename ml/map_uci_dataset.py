"""Convert the UCI "Predict Students' Dropout and Academic Success" file to Pathway's import format.

Download `data.csv` yourself from https://archive.ics.uci.edu/dataset/697 (CC BY 4.0, semicolon
separated) and run:

    python ml/map_uci_dataset.py data.csv ml/sample_data/uci_import.csv

Then either import it (`python -m app.cli import-csv ml/sample_data/uci_import.csv`) or train
directly (`python ml/train_from_csv.py ml/sample_data/uci_import.csv`). See ml/README.md for
what each column becomes and why the result is weaker than Pathway's monthly data.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import pandas as pd

SEMESTERS = {1: "2024-01", 2: "2024-06"}
NEEDED = [
    "Course", "Target",
    *[f"Curricular units {n}{s} sem ({what})" for n, s in ((1, "st"), (2, "nd"))
      for what in ("enrolled", "evaluations", "approved", "grade", "without evaluations")],
]


def pct(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    """Percentage with zero denominators treated as 0."""
    return (numerator / denominator.where(denominator > 0) * 100).fillna(0).clip(0, 100)


def main() -> None:
    """Write one row per student per semester; the semester plays the role of a month."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("source", type=Path)
    parser.add_argument("target", type=Path)
    args = parser.parse_args()

    frame = pd.read_csv(args.source, sep=";")
    frame.columns = [c.strip() for c in frame.columns]
    missing = [c for c in NEEDED if c not in frame.columns]
    if missing:
        raise SystemExit(f"Not the expected UCI file; missing: {missing[:3]}")
    frame = frame[frame["Target"].isin(["Dropout", "Graduate"])].reset_index(drop=True)

    with args.target.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow([
            "student_code", "name", "department", "year", "section", "month", "avg_score",
            "attendance_pct", "assignments_pct", "late_arrivals", "failed_subjects",
            "guardian_engagement", "dropped_out",
        ])
        for index, row in frame.iterrows():
            code = f"UCI-{index + 1:05d}"
            for sem, ordinal in ((1, "1st"), (2, "2nd")):
                prefix = f"Curricular units {ordinal} sem"
                enrolled = float(row[f"{prefix} (enrolled)"])
                evaluated = float(row[f"{prefix} (evaluations)"])
                approved = float(row[f"{prefix} (approved)"])
                skipped = float(row[f"{prefix} (without evaluations)"])
                writer.writerow([
                    code, f"UCI student {index + 1}", f"Course {int(row['Course'])}", 1, "A", SEMESTERS[sem],
                    round(min(100.0, float(row[f"{prefix} (grade)"]) * 5), 1),       # 0-20 scale -> 0-100
                    round(float(pct(pd.Series([evaluated - skipped]), pd.Series([evaluated])).iloc[0]), 1),
                    round(float(pct(pd.Series([approved]), pd.Series([enrolled])).iloc[0]), 1),
                    0,                                                                # not in the dataset
                    int(max(0, enrolled - approved)),
                    3,                                                                # not in the dataset
                    int(row["Target"] == "Dropout"),
                ])
    print(f"Wrote {len(frame)} students ({len(frame) * 2} rows) to {args.target}")


if __name__ == "__main__":
    main()
