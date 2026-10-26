"""Prediction endpoints: what-if scoring and batch recompute."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import AdminUser, CurrentUser, DbSession
from app.schemas.prediction import BatchResult, PredictionOut, WhatIfRequest
from app.services import audit_service, prediction_service

router = APIRouter(tags=["predictions"])


@router.post("/predict", response_model=PredictionOut)
def predict(payload: WhatIfRequest, _: CurrentUser, session: DbSession) -> PredictionOut:
    """Score hypothetical feature values. Nothing is stored."""
    return prediction_service.what_if(session, payload)


@router.post("/predictions/batch", response_model=BatchResult)
def predict_all(admin: AdminUser, session: DbSession) -> BatchResult:
    """Recompute the prediction for every student with data."""
    result = prediction_service.predict_students(session)
    audit_service.record(session, admin.id, "predict_batch", "predictions", None, {"updated": result.updated})
    return result
