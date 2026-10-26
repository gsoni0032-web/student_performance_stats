"""Prediction, dashboard, model and data-exchange schemas."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import Field, model_validator

from app.schemas.common import CamelModel
from app.schemas.student import Factor, RiskName, StatusName


class WhatIfRequest(CamelModel):
    """Feature values for a hypothetical student. Ranges mirror the training data."""

    attendance: float = Field(ge=0, le=100)
    score: float = Field(ge=0, le=100)
    assignments: float = Field(ge=0, le=100)
    failures: float = Field(ge=0, le=12)
    late: float = Field(ge=0, le=31)
    parent: float = Field(ge=1, le=5)
    trend: float = Field(ge=-20, le=20)
    grade: int = Field(default=2, ge=1, le=6, description="Year of study")


class PredictionOut(CamelModel):
    """Result of scoring one set of features."""

    prob: float
    risk_level: RiskName
    next_term_score: float | None
    factors: list[Factor]
    suggested_actions: list[str]
    model_version: int


class BatchResult(CamelModel):
    """Outcome of recomputing many predictions."""

    updated: int
    skipped: int
    model_version: int


class Thresholds(CamelModel):
    """Probability cut-offs for the risk bands."""

    medium: float = Field(gt=0, lt=1, default=0.3)
    high: float = Field(gt=0, lt=1, default=0.6)

    @model_validator(mode="after")
    def medium_below_high(self) -> Thresholds:
        """The medium threshold must be lower than the high one."""
        if self.medium >= self.high:
            raise ValueError("The medium threshold must be lower than the high threshold")
        return self


class Summary(CamelModel):
    """Headline numbers for the overview."""

    students_tracked: int
    avg_attendance: float | None
    avg_score: float | None
    high_risk: int
    medium_risk: int
    low_risk: int
    unscored: int
    attendance_change: float | None
    score_change: float | None
    high_risk_change: int
    latest_month: date | None


class GradeRisk(CamelModel):
    """Risk bands for one year of study."""

    grade: int
    low: int
    medium: int
    high: int
    unscored: int


class Driver(CamelModel):
    """How often a factor is among the top reasons a student is at risk."""

    key: str
    label: str
    students: int
    share: float
    avg_impact: float


class WatchlistItem(CamelModel):
    """A student who needs attention first."""

    id: int
    name: str
    student_code: str
    department: str
    grade: int
    prob: float
    risk_level: RiskName
    top_factor: str | None
    follow_up_status: StatusName


class CohortPoint(CamelModel):
    """One student on the cohort register and scatter chart."""

    id: int
    name: str
    grade: int
    prob: float | None
    risk_level: RiskName | None
    attendance: float | None
    score: float | None


class ModelInfo(CamelModel):
    """The active model, its history and the state of any training run."""

    active: dict[str, Any] | None
    versions: list[dict[str, Any]]
    training: dict[str, Any]
    thresholds: Thresholds


class RowIssue(CamelModel):
    """A problem found on one CSV row."""

    row: int
    column: str | None
    message: str


class ImportResult(CamelModel):
    """Outcome (or dry-run preview) of a CSV import."""

    dry_run: bool
    imported: bool
    rows_read: int
    rows_valid: int
    students: int
    records: int
    issues: list[RowIssue]
    preview: list[dict[str, Any]]
    finished_at: datetime | None = None
