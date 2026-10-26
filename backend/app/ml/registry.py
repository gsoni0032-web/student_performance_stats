"""Versioned storage for trained models: files on disk, a copy in the database, one active."""

from __future__ import annotations

import io
import json
import logging
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import joblib
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError, not_found
from app.ml.pipeline import ModelBundle
from app.models import ModelVersion

logger = logging.getLogger("pathway.registry")

_cache: dict[int, ModelBundle] = {}
_lock = threading.Lock()


def _model_path(version: int) -> Path:
    return get_settings().model_dir / f"model_v{version}.joblib"


def _metrics_path(version: int) -> Path:
    return get_settings().model_dir / f"metrics_v{version}.json"


def save_bundle(session: Session, bundle: ModelBundle) -> ModelVersion:
    """Persist a freshly trained bundle as the next version and make it the active one."""
    next_version = (session.scalar(select(func.max(ModelVersion.version))) or 0) + 1
    bundle.version = next_version
    bundle.metrics["version"] = next_version
    bundle.metrics["trained_at"] = datetime.now(UTC).isoformat()

    buffer = io.BytesIO()
    joblib.dump(bundle, buffer, compress=3)
    payload = buffer.getvalue()

    path = _model_path(next_version)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    _metrics_path(next_version).write_text(json.dumps(bundle.metrics, indent=2))

    session.execute(update(ModelVersion).values(is_active=False))
    record = ModelVersion(
        version=next_version,
        model_type=bundle.model_type,
        metrics=bundle.metrics,
        is_active=True,
        file_path=str(path),
        artifact=payload,
    )
    session.add(record)
    session.commit()
    with _lock:
        _cache.clear()
    logger.info("saved model version %s (%s)", next_version, bundle.model_type)
    return record


def list_versions(session: Session) -> list[ModelVersion]:
    """All versions, newest first."""
    return list(session.scalars(select(ModelVersion).order_by(ModelVersion.version.desc())))


def active_version(session: Session) -> ModelVersion | None:
    """The currently active model record, if any."""
    return session.scalar(select(ModelVersion).where(ModelVersion.is_active.is_(True)))


def activate(session: Session, version: int) -> ModelVersion:
    """Make `version` the active model (rollback or roll-forward)."""
    record = session.scalar(select(ModelVersion).where(ModelVersion.version == version))
    if record is None:
        raise not_found(f"Model version {version}")
    session.execute(update(ModelVersion).values(is_active=False))
    record.is_active = True
    session.commit()
    with _lock:
        _cache.clear()
    return record


def _read_payload(session: Session, record: ModelVersion) -> bytes:
    """Read the artifact from disk, restoring it from the database copy if the file is gone."""
    path = Path(record.file_path)
    if path.exists():
        return path.read_bytes()
    blob = session.scalar(select(ModelVersion.artifact).where(ModelVersion.id == record.id))
    if blob is None:
        raise AppError(503, "model_missing", "The model file is missing. Please retrain the model.")
    path = _model_path(record.version)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(blob)
    record.file_path = str(path)
    session.commit()
    return bytes(blob)


def load_active_bundle(session: Session) -> ModelBundle:
    """Load (and cache) the active model, or raise a 503 explaining that none is trained yet."""
    record = active_version(session)
    if record is None:
        raise AppError(
            503,
            "no_model",
            "No prediction model is available yet. An administrator needs to train one first.",
        )
    with _lock:
        cached = _cache.get(record.version)
    if cached is not None:
        return cached
    payload = _read_payload(session, record)
    bundle: ModelBundle = joblib.load(io.BytesIO(payload))
    bundle.version = record.version
    with _lock:
        _cache.clear()
        _cache[record.version] = bundle
    return bundle


def describe(record: ModelVersion) -> dict[str, Any]:
    """A compact, API-friendly description of a model version."""
    return {
        "version": record.version,
        "modelType": record.model_type,
        "trainedAt": record.trained_at,
        "isActive": record.is_active,
        "metrics": record.metrics,
    }


def clear_cache() -> None:
    """Forget loaded bundles (used by tests)."""
    with _lock:
        _cache.clear()
