"""Model information, retraining, rollback and risk thresholds."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, status

from app.api.deps import AdminUser, CurrentUser, DbSession
from app.core.database import get_session_factory
from app.ml import registry
from app.schemas.prediction import ModelInfo, Thresholds
from app.services import audit_service, prediction_service, settings_service, training_service

router = APIRouter(tags=["model"])


def _info(session: DbSession) -> ModelInfo:
    versions = [registry.describe(v) for v in registry.list_versions(session)]
    active = next((v for v in versions if v["isActive"]), None)
    return ModelInfo(
        active=active,
        versions=versions,
        training=training_service.status(),
        thresholds=settings_service.get_thresholds(session),
    )


@router.get("/model/info", response_model=ModelInfo)
def model_info(_: CurrentUser, session: DbSession) -> ModelInfo:
    """The active model, every saved version and the state of any training run."""
    return _info(session)


@router.post("/model/retrain", status_code=status.HTTP_202_ACCEPTED)
def retrain(admin: AdminUser) -> dict[str, Any]:
    """Start training in the background. Poll `GET /model/info` for progress."""
    return training_service.start_background(get_session_factory(), admin.id)


@router.post("/model/activate/{version}", response_model=ModelInfo)
def activate(version: int, admin: AdminUser, session: DbSession) -> ModelInfo:
    """Roll back (or forward) to a saved model version and rescore every student."""
    registry.activate(session, version)
    prediction_service.predict_students(session)
    audit_service.record(session, admin.id, "model_activate", "model", version)
    return _info(session)


@router.get("/settings/thresholds", response_model=Thresholds)
def get_thresholds(_: CurrentUser, session: DbSession) -> Thresholds:
    """Probability cut-offs for the medium and high risk bands."""
    return settings_service.get_thresholds(session)


@router.put("/settings/thresholds", response_model=Thresholds)
def put_thresholds(payload: Thresholds, admin: AdminUser, session: DbSession) -> Thresholds:
    """Change the cut-offs; stored predictions are relabelled immediately."""
    saved = settings_service.set_thresholds(session, payload)
    audit_service.record(
        session, admin.id, "thresholds_update", "settings", None, {"medium": saved.medium, "high": saved.high}
    )
    return saved
