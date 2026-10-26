"""Feature engineering shared by training, prediction and the what-if endpoint.

The model never sees names, contact details or any sensitive attribute. It sees only
eight academic signals derived from a student's monthly records.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

FEATURE_NAMES: list[str] = [
    "attendance",
    "score",
    "assignments",
    "failures",
    "late",
    "parent",
    "trend",
    "grade",
]
ROLLING_WINDOW = 3
MIN_MONTHS_FOR_REGRESSION = 4

FEATURE_RANGES: dict[str, tuple[float, float]] = {
    "attendance": (0.0, 100.0),
    "score": (0.0, 100.0),
    "assignments": (0.0, 100.0),
    "failures": (0.0, 12.0),
    "late": (0.0, 31.0),
    "parent": (1.0, 5.0),
    "trend": (-20.0, 20.0),
    "grade": (1.0, 6.0),
}


@dataclass(frozen=True)
class MonthPoint:
    """The numbers recorded for one student in one month."""

    avg_score: float
    attendance_pct: float
    assignments_pct: float
    late_arrivals: int
    failed_subjects: int
    guardian_engagement: int


def _slope(values: Sequence[float]) -> float:
    """Least-squares slope per month; 0 when there are fewer than two points."""
    if len(values) < 2:
        return 0.0
    x = np.arange(len(values), dtype=float)
    return float(np.polyfit(x, np.asarray(values, dtype=float), 1)[0])


def compute_features(points: Sequence[MonthPoint], grade: int) -> dict[str, float] | None:
    """Turn a student's monthly points (oldest first) into the model's feature dict.

    Level features are rolling means over the last three months so a single bad month does not
    dominate; failures is the latest count; trend is the score slope per month over the whole
    series. Returns None when there is no data at all.
    """
    if not points:
        return None
    recent = points[-ROLLING_WINDOW:]
    return {
        "attendance": float(np.mean([p.attendance_pct for p in recent])),
        "score": float(np.mean([p.avg_score for p in recent])),
        "assignments": float(np.mean([p.assignments_pct for p in recent])),
        "failures": float(points[-1].failed_subjects),
        "late": float(np.mean([p.late_arrivals for p in recent])),
        "parent": float(np.mean([p.guardian_engagement for p in recent])),
        "trend": _slope([p.avg_score for p in points]),
        "grade": float(grade),
    }


def clip_features(features: dict[str, float]) -> dict[str, float]:
    """Clip every feature into its valid range (defensive; inputs are validated earlier)."""
    return {
        name: float(np.clip(features[name], *FEATURE_RANGES[name])) for name in FEATURE_NAMES
    }


def to_row(features: dict[str, float]) -> list[float]:
    """Order a feature dict the way the model expects."""
    return [float(features[name]) for name in FEATURE_NAMES]
