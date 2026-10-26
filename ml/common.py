"""Helpers shared by the stand-alone ML scripts (no database or web framework needed)."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

BACKEND = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND))

from app.ml.features import MonthPoint  # noqa: E402
from app.ml.pipeline import StudentSeries  # noqa: E402

REQUIRED = [
    "student_code", "department", "year", "month", "avg_score", "attendance_pct",
    "assignments_pct", "late_arrivals", "failed_subjects", "guardian_engagement",
]


def load_series(path: Path) -> tuple[list[StudentSeries], list[str]]:
    """Read an import-format CSV into one `StudentSeries` per student, plus their codes."""
    frame = pd.read_csv(path, dtype={"student_code": str})
    missing = [column for column in REQUIRED if column not in frame.columns]
    if missing:
        raise SystemExit(f"{path} is missing column(s): {', '.join(missing)}")
    frame["month"] = pd.to_datetime(frame["month"])
    series: list[StudentSeries] = []
    codes: list[str] = []
    for code, rows in frame.sort_values("month").groupby("student_code", sort=True):
        outcome = None
        if "dropped_out" in rows and rows["dropped_out"].notna().any():
            outcome = bool(int(rows["dropped_out"].dropna().iloc[-1]))
        points = [
            MonthPoint(
                float(r.avg_score), float(r.attendance_pct), float(r.assignments_pct),
                int(r.late_arrivals), int(r.failed_subjects), int(r.guardian_engagement),
            )
            for r in rows.itertuples()
        ]
        series.append(StudentSeries(grade=int(rows["year"].iloc[0]), points=points, dropped_out=outcome))
        codes.append(str(code))
    return series, codes
