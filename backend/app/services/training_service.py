"""Model training, run in a background thread so the API stays responsive."""

from __future__ import annotations

import logging
import threading
from typing import Any

from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.core.errors import conflict
from app.core.timeutil import utcnow
from app.ml import registry
from app.ml.data import load_student_series
from app.ml.pipeline import TrainingError, build_frames, train
from app.services import audit_service, prediction_service, settings_service

logger = logging.getLogger("pathway.training")

_lock = threading.Lock()
_state: dict[str, Any] = {"status": "idle", "message": None, "started_at": None, "finished_at": None, "version": None}


def status() -> dict[str, Any]:
    """Current training state: idle, running, succeeded or failed."""
    with _lock:
        return dict(_state)


def _set(**changes: Any) -> None:
    with _lock:
        _state.update(changes)


def reset() -> None:
    """Return to the idle state (used by tests)."""
    _set(status="idle", message=None, started_at=None, finished_at=None, version=None)


def run_training(session: Session, user_id: int | None) -> int:
    """Train on everything in the database, save and activate the result, rescore all students.

    Returns the new model version. Raises `TrainingError` when the data cannot support a model.
    """
    thresholds = settings_service.get_thresholds(session)
    config = get_settings()
    clf_frame, reg_frame = build_frames(load_student_series(session))
    bundle = train(
        clf_frame,
        reg_frame,
        flag_threshold=thresholds.medium,
        high_threshold=thresholds.high,
        candidates=config.ml_candidate_list,
        search_iterations=config.training_search_iterations,
    )
    record = registry.save_bundle(session, bundle)
    audit_service.record(
        session, user_id, "retrain", "model", record.version, {"model_type": record.model_type}
    )
    prediction_service.predict_students(session)
    return record.version


def start_background(factory: sessionmaker[Session], user_id: int) -> dict[str, Any]:
    """Begin training in a thread. Raises 409 if a run is already in progress."""
    with _lock:
        if _state["status"] == "running":
            raise conflict("A training run is already in progress")
        _state.update(status="running", message=None, started_at=utcnow().isoformat(), finished_at=None, version=None)

    def work() -> None:
        with factory() as session:
            try:
                version = run_training(session, user_id)
                _set(status="succeeded", version=version, message=None, finished_at=utcnow().isoformat())
            except TrainingError as error:
                _set(status="failed", message=str(error), finished_at=utcnow().isoformat())
            except Exception:
                logger.exception("training failed")
                _set(
                    status="failed",
                    message="Training failed unexpectedly. Check the server logs.",
                    finished_at=utcnow().isoformat(),
                )

    threading.Thread(target=work, name="pathway-training", daemon=True).start()
    return status()
