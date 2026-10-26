"""Turn SHAP values into short, readable factors and suggested next steps."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import numpy as np

from app.ml.features import FEATURE_NAMES

TOP_FACTORS = 5

FEATURE_TITLES: dict[str, str] = {
    "attendance": "Attendance",
    "score": "Average score",
    "assignments": "Assignment completion",
    "failures": "Failed or backlog courses",
    "late": "Late arrivals",
    "parent": "Guardian engagement",
    "trend": "Score trend",
    "grade": "Year of study",
}

# key -> (label when it raises risk, label when it lowers risk, formatter for the value)
_LABELS: dict[str, tuple[str, str, Callable[[float], str]]] = {
    "attendance": ("Low attendance", "Strong attendance", lambda v: f"{v:.0f}%"),
    "score": ("Low average score", "Solid average score", lambda v: f"{v:.0f}"),
    "assignments": ("Missed assignments", "Assignments on time", lambda v: f"{v:.0f}%"),
    "failures": ("Failed or backlog courses", "No failed courses", lambda v: f"{v:.0f}"),
    "late": ("Frequent late arrivals", "Rarely late", lambda v: f"{v:.1f}/mo"),
    "parent": ("Low guardian engagement", "Engaged guardian", lambda v: f"{v:.1f}/5"),
    "trend": ("Falling scores", "Improving scores", lambda v: f"{v:+.1f}/mo"),
    "grade": ("Year of study carries more risk", "Year of study carries less risk", lambda v: f"Year {v:.0f}"),
}

_ACTIONS: dict[str, str] = {
    "attendance": "Talk with the student about what is keeping them out of class (travel, work, health, timetable clashes).",
    "score": "Offer a tutoring slot or peer study group for the courses with the weakest marks.",
    "assignments": "Agree a realistic catch-up plan for outstanding assignments and check in weekly.",
    "failures": "Review the failed courses with the academic advisor and plan re-examination or credit recovery.",
    "late": "Ask whether commute, hostel or schedule problems are behind the late arrivals.",
    "parent": "Contact the guardian to share progress and agree how to support the student.",
    "trend": "Check in soon: scores have been sliding, so a short conversation now may prevent a bigger drop.",
    "grade": "Connect the student with a mentor who has been through this year of the programme.",
}

_FALLBACK_ACTIONS = {
    "high": "Schedule a one-to-one meeting this week and record the outcome in the follow-up notes.",
    "medium": "Keep the student on the watch list and review their numbers again next month.",
    "low": "No action needed beyond routine monitoring.",
}


def build_factors(
    features: dict[str, float], shap_row: np.ndarray, top_n: int = TOP_FACTORS
) -> list[dict[str, Any]]:
    """The `top_n` features that moved this student's risk the most.

    `impact` is the feature's share (percent) of the total absolute SHAP movement, so the
    numbers are comparable across students. `driver` says whether it raises or lowers risk.
    """
    magnitudes = np.abs(shap_row)
    total = float(magnitudes.sum())
    if total <= 0:
        return []
    order = np.argsort(-magnitudes)[:top_n]
    factors: list[dict[str, Any]] = []
    for index in order:
        value = float(shap_row[index])
        if abs(value) < 1e-9:
            continue
        key = FEATURE_NAMES[int(index)]
        raises_label, lowers_label, fmt = _LABELS[key]
        raises = value > 0
        factors.append(
            {
                "key": key,
                "label": raises_label if raises else lowers_label,
                "display": fmt(features[key]),
                "impact": round(abs(value) / total * 100, 1),
                "driver": "raises" if raises else "lowers",
            }
        )
    return factors


def suggest_actions(factors: list[dict[str, Any]], risk_level: str) -> list[str]:
    """Plain-language next steps based on what raises this student's risk."""
    actions = [_ACTIONS[f["key"]] for f in factors if f["driver"] == "raises"][:3]
    if not actions:
        return [_FALLBACK_ACTIONS.get(risk_level, _FALLBACK_ACTIONS["low"])]
    if risk_level == "high":
        actions.append(_FALLBACK_ACTIONS["high"])
    return actions
