"""Aggregates for the overview dashboard. Results are cached per visible scope."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from typing import Any

import numpy as np
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.cache import dashboard_cache
from app.core.config import get_settings
from app.ml.data import point_from_record
from app.ml.explain import FEATURE_TITLES
from app.ml.features import compute_features
from app.models import Class, Intervention, MonthlyRecord, Prediction, Student, User
from app.models.enums import InterventionStatus
from app.schemas.prediction import CohortPoint, Driver, GradeRisk, Summary, WatchlistItem
from app.services import student_service


@dataclass(frozen=True)
class CohortRow:
    """Everything the dashboard needs to know about one student."""

    id: int
    name: str
    student_code: str
    department: str
    grade: int
    attendance: float | None
    score: float | None
    prob: float | None
    risk: str | None
    previous_risk: str | None
    factors: list[dict[str, Any]]
    status: str


@dataclass(frozen=True)
class Cohort:
    """The visible students plus month-level averages."""

    rows: list[CohortRow]
    latest_month: date | None
    avg_attendance: float | None
    avg_score: float | None
    attendance_change: float | None
    score_change: float | None


def _scope_key(session: Session, user: User) -> tuple[int, ...] | str:
    scope = student_service.class_scope(session, user)
    return "all" if scope is None else tuple(sorted(scope))


def _latest_ids() -> Any:
    return select(func.max(Prediction.id)).group_by(Prediction.student_id)


def _month_average(records: list[MonthlyRecord], month: date) -> tuple[float, float] | None:
    in_month = [r for r in records if r.month == month]
    if not in_month:
        return None
    return (
        float(np.mean([r.attendance_pct for r in in_month])),
        float(np.mean([r.avg_score for r in in_month])),
    )


def _build_cohort(session: Session, user: User) -> Cohort:
    scope = student_service.class_scope(session, user)
    conditions = [] if scope is None else [Student.class_id.in_(scope)]

    students = session.execute(
        select(Student.id, Student.name, Student.student_code, Class.department, Class.grade)
        .join(Class, Class.id == Student.class_id)
        .where(*conditions)
    ).all()
    ids = [row.id for row in students]

    latest = {
        p.student_id: p
        for p in session.scalars(select(Prediction).where(Prediction.id.in_(_latest_ids()), Prediction.student_id.in_(ids)))
    } if ids else {}
    previous: dict[int, str] = {}
    if ids:
        older = select(func.max(Prediction.id)).where(Prediction.id.not_in(_latest_ids())).group_by(Prediction.student_id)
        previous = {
            p.student_id: p.risk_level
            for p in session.scalars(select(Prediction).where(Prediction.id.in_(older), Prediction.student_id.in_(ids)))
        }
    statuses = (
        dict(session.execute(select(Intervention.student_id, Intervention.status).where(Intervention.student_id.in_(ids))).all())
        if ids
        else {}
    )
    records: dict[int, list[MonthlyRecord]] = defaultdict(list)
    if ids:
        for record in session.scalars(
            select(MonthlyRecord).where(MonthlyRecord.student_id.in_(ids)).order_by(MonthlyRecord.student_id, MonthlyRecord.month)
        ):
            records[record.student_id].append(record)

    rows: list[CohortRow] = []
    all_records: list[MonthlyRecord] = []
    for student in students:
        student_records = records.get(student.id, [])
        all_records.extend(student_records)
        features = compute_features([point_from_record(r) for r in student_records], student.grade)
        prediction = latest.get(student.id)
        rows.append(
            CohortRow(
                id=student.id,
                name=student.name,
                student_code=student.student_code,
                department=student.department,
                grade=student.grade,
                attendance=None if features is None else round(features["attendance"], 1),
                score=None if features is None else round(features["score"], 1),
                prob=None if prediction is None else prediction.probability,
                risk=None if prediction is None else prediction.risk_level,
                previous_risk=previous.get(student.id),
                factors=[] if prediction is None else list(prediction.top_factors),
                status=statuses.get(student.id, InterventionStatus.NOT_STARTED.value),
            )
        )

    months = sorted({r.month for r in all_records})
    latest_month = months[-1] if months else None
    current = _month_average(all_records, latest_month) if latest_month else None
    prior = _month_average(all_records, months[-2]) if len(months) > 1 else None
    return Cohort(
        rows=rows,
        latest_month=latest_month,
        avg_attendance=None if current is None else round(current[0], 1),
        avg_score=None if current is None else round(current[1], 1),
        attendance_change=None if not (current and prior) else round(current[0] - prior[0], 1),
        score_change=None if not (current and prior) else round(current[1] - prior[1], 1),
    )


def cohort(session: Session, user: User) -> Cohort:
    """The cached cohort for the user's visible scope."""
    ttl = get_settings().dashboard_cache_seconds
    return dashboard_cache.get_or_set(
        (_scope_key(session, user), "cohort"), ttl, lambda: _build_cohort(session, user)
    )


def summary(session: Session, user: User) -> Summary:
    """Headline counts, averages and month-over-month changes."""
    data = cohort(session, user)
    counts = {"high": 0, "medium": 0, "low": 0}
    high_before = 0
    unscored = 0
    for row in data.rows:
        if row.risk is None:
            unscored += 1
            continue
        counts[row.risk] += 1
        before = row.previous_risk or row.risk
        high_before += before == "high"
    return Summary(
        students_tracked=len(data.rows),
        avg_attendance=data.avg_attendance,
        avg_score=data.avg_score,
        high_risk=counts["high"],
        medium_risk=counts["medium"],
        low_risk=counts["low"],
        unscored=unscored,
        attendance_change=data.attendance_change,
        score_change=data.score_change,
        high_risk_change=counts["high"] - high_before,
        latest_month=data.latest_month,
    )


def risk_by_grade(session: Session, user: User) -> list[GradeRisk]:
    """Risk band counts for each year of study."""
    data = cohort(session, user)
    grouped: dict[int, dict[str, int]] = defaultdict(lambda: {"low": 0, "medium": 0, "high": 0, "unscored": 0})
    for row in data.rows:
        grouped[row.grade][row.risk or "unscored"] += 1
    return [GradeRisk(grade=grade, **counts) for grade, counts in sorted(grouped.items())]


def drivers(session: Session, user: User, limit: int = 6) -> list[Driver]:
    """Factors that most often raise risk among students at medium or high risk."""
    data = cohort(session, user)
    at_risk = [r for r in data.rows if r.risk in ("medium", "high")]
    tallies: dict[str, list[float]] = defaultdict(list)
    for row in at_risk:
        for factor in row.factors:
            if factor["driver"] == "raises":
                tallies[factor["key"]].append(float(factor["impact"]))
    ranked = sorted(tallies.items(), key=lambda item: (-len(item[1]), -float(np.mean(item[1]))))[:limit]
    return [
        Driver(
            key=key,
            label=FEATURE_TITLES.get(key, key),
            students=len(impacts),
            share=round(len(impacts) / len(at_risk), 3),
            avg_impact=round(float(np.mean(impacts)), 1),
        )
        for key, impacts in ranked
    ]


def watchlist(session: Session, user: User, limit: int = 10) -> list[WatchlistItem]:
    """The highest-risk students that are not yet resolved."""
    data = cohort(session, user)
    candidates = [
        r
        for r in data.rows
        if r.risk in ("medium", "high") and r.prob is not None and r.status != InterventionStatus.RESOLVED.value
    ]
    candidates.sort(key=lambda r: -(r.prob or 0.0))
    items = []
    for row in candidates[:limit]:
        raising = next((f for f in row.factors if f["driver"] == "raises"), None)
        items.append(
            WatchlistItem(
                id=row.id,
                name=row.name,
                student_code=row.student_code,
                department=row.department,
                grade=row.grade,
                prob=round(row.prob or 0.0, 4),
                risk_level=row.risk,  # type: ignore[arg-type]
                top_factor=None if raising is None else f"{raising['label']} ({raising['display']})",
                follow_up_status=row.status,  # type: ignore[arg-type]
            )
        )
    return items


def cohort_points(session: Session, user: User, limit: int) -> list[CohortPoint]:
    """Compact per-student points for the register and the scatter chart, riskiest first."""
    data = cohort(session, user)
    ordered = sorted(data.rows, key=lambda r: (r.prob is None, -(r.prob or 0.0), r.name))
    return [
        CohortPoint(
            id=r.id,
            name=r.name,
            grade=r.grade,
            prob=None if r.prob is None else round(r.prob, 4),
            risk_level=r.risk,  # type: ignore[arg-type]
            attendance=r.attendance,
            score=r.score,
        )
        for r in ordered[:limit]
    ]
