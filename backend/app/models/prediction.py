"""Stored predictions and the registry of trained model versions."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Index, Integer, LargeBinary, String
from sqlalchemy.orm import Mapped, deferred, mapped_column

from app.core.database import Base
from app.core.timeutil import utcnow


class Prediction(Base):
    """One dropout-risk prediction for a student. New predictions are appended; none are edited."""

    __tablename__ = "predictions"
    __table_args__ = (
        Index("ix_predictions_student_latest", "student_id", "id"),
        Index("ix_predictions_risk_level", "risk_level"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"))
    model_version: Mapped[int] = mapped_column(Integer)
    probability: Mapped[float] = mapped_column(Float)
    risk_level: Mapped[str] = mapped_column(String(10))
    next_term_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    top_factors: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ModelVersion(Base):
    """A trained model artifact. The artifact bytes are also kept in the database so a
    redeploy on a host with an ephemeral disk does not lose the model."""

    __tablename__ = "model_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    version: Mapped[int] = mapped_column(Integer, unique=True)
    model_type: Mapped[str] = mapped_column(String(30))
    metrics: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    trained_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    file_path: Mapped[str] = mapped_column(String(300))
    artifact: Mapped[bytes | None] = deferred(mapped_column(LargeBinary, nullable=True))
