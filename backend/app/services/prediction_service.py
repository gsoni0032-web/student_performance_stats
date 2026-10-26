"""Scoring students and storing predictions."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.cache import dashboard_cache
from app.core.errors import AppError
from app.ml import registry
from app.ml.data import point_from_record
from app.ml.explain import build_factors, suggest_actions
from app.ml.features import compute_features, clip_features, to_row
from app.ml.pipeline import ModelBundle
from app.models import Prediction, Student
from app.schemas.prediction import BatchResult, PredictionOut, Thresholds, WhatIfRequest
from app.services import settings_service


@dataclass(frozen=True)
class Scored:
    """The result of scoring one feature set."""

    probability: float
    risk_level: str
    next_term_score: float | None
    factors: list[dict[str, Any]]


def score_features(
    bundle: ModelBundle, thresholds: Thresholds, feature_sets: Sequence[dict[str, float]]
) -> list[Scored]:
    """Score many feature sets in one vectorised pass."""
    if not feature_sets:
        return []
    clipped = [clip_features(f) for f in feature_sets]
    rows = [to_row(f) for f in clipped]
    probabilities = bundle.predict_proba(rows)
    next_scores = bundle.predict_next_score(rows)
    contributions = bundle.shap_values(rows)
    results: list[Scored] = []
    for index, features in enumerate(clipped):
        probability = float(probabilities[index])
        results.append(
            Scored(
                probability=probability,
                risk_level=settings_service.risk_level_for(probability, thresholds),
                next_term_score=None if next_scores is None else round(float(next_scores[index]), 1),
                factors=build_factors(features, contributions[index]),
            )
        )
    return results


def what_if(session: Session, payload: WhatIfRequest) -> PredictionOut:
    """Score hypothetical feature values without storing anything."""
    bundle = registry.load_active_bundle(session)
    thresholds = settings_service.get_thresholds(session)
    features = payload.model_dump()
    scored = score_features(bundle, thresholds, [features])[0]
    return PredictionOut(
        prob=round(scored.probability, 4),
        risk_level=scored.risk_level,  # type: ignore[arg-type]
        next_term_score=scored.next_term_score,
        factors=scored.factors,  # type: ignore[arg-type]
        suggested_actions=suggest_actions(scored.factors, scored.risk_level),
        model_version=bundle.version,
    )


def predict_students(session: Session, student_ids: Sequence[int] | None = None) -> BatchResult:
    """Recompute and store a prediction for each student that has monthly data.

    Passing `None` recomputes everyone. Raises 503 when no model has been trained yet.
    """
    bundle = registry.load_active_bundle(session)
    thresholds = settings_service.get_thresholds(session)
    query = select(Student).options(selectinload(Student.records), selectinload(Student.klass))
    if student_ids is not None:
        query = query.where(Student.id.in_(list(student_ids)))
    students = session.scalars(query).all()

    pending: list[tuple[Student, dict[str, float]]] = []
    skipped = 0
    for student in students:
        features = compute_features([point_from_record(r) for r in student.records], student.klass.grade)
        if features is None:
            skipped += 1
        else:
            pending.append((student, features))

    scored = score_features(bundle, thresholds, [f for _, f in pending])
    session.add_all(
        [
            Prediction(
                student_id=student.id,
                model_version=bundle.version,
                probability=result.probability,
                risk_level=result.risk_level,
                next_term_score=result.next_term_score,
                top_factors=result.factors,
            )
            for (student, _), result in zip(pending, scored, strict=True)
        ]
    )
    session.commit()
    dashboard_cache.clear()
    return BatchResult(updated=len(pending), skipped=skipped, model_version=bundle.version)


def predict_students_if_model(session: Session, student_ids: Sequence[int]) -> None:
    """Best-effort scoring used after data changes: silently skipped while no model exists."""
    try:
        predict_students(session, student_ids)
    except AppError as error:
        if error.code != "no_model":
            raise
