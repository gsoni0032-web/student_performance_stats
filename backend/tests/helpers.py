"""Test helpers that do not depend on the web framework."""

from __future__ import annotations

from collections.abc import Sequence

from app.ml.features import MonthPoint
from app.ml.pipeline import StudentSeries
from app.ml.synthetic import SyntheticStudent


def series_from(students: Sequence[SyntheticStudent]) -> list[StudentSeries]:
    """Convert generated students into the pipeline's input type."""
    return [
        StudentSeries(
            grade=s.grade,
            points=[
                MonthPoint(
                    m.avg_score, m.attendance_pct, m.assignments_pct,
                    m.late_arrivals, m.failed_subjects, m.guardian_engagement,
                )
                for m in s.months
            ],
            dropped_out=s.dropped_out,
        )
        for s in students
    ]
