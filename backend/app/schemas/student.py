"""Student, monthly record and follow-up schemas."""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import Field, StringConstraints, field_validator

from app.schemas.common import CamelModel, ShortText, clean_text

StatusName = Literal["not_started", "guardian_contacted", "support_plan_active", "resolved"]
RiskName = Literal["low", "medium", "high"]
StudentCode = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=30)]
_CODE_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def _check_code(value: str) -> str:
    if not _CODE_PATTERN.match(value):
        raise ValueError("Use letters, digits, dots, dashes or underscores (no spaces)")
    return value


class Features(CamelModel):
    """The academic signals the model reads (year of study is returned as `grade`)."""

    attendance: float
    score: float
    assignments: float
    failures: float
    late: float
    parent: float
    trend: float


class Factor(CamelModel):
    """One reason behind a prediction."""

    key: str
    label: str
    display: str
    impact: float
    driver: Literal["raises", "lowers"]


class FollowUp(CamelModel):
    """Follow-up status and notes."""

    status: StatusName = "not_started"
    notes: str = ""
    updated_at: datetime | None = None
    updated_by: str | None = None


class StudentSummary(CamelModel):
    """A student as shown in lists."""

    id: int
    student_code: str
    name: str
    department: str
    grade: int
    section: str
    class_id: int
    score_series: list[float]
    att_series: list[float]
    features: Features | None
    prob: float | None
    risk_level: RiskName | None
    follow_up_status: StatusName


class StudentDetail(StudentSummary):
    """A student with everything needed for the detail view."""

    guardian_contact: str | None
    dropped_out: bool | None
    months: list[str]
    next_term_score: float | None
    model_version: int | None
    predicted_at: datetime | None
    factors: list[Factor]
    suggested_actions: list[str]
    follow_up: FollowUp


class MonthlyRecordIn(CamelModel):
    """One month of data for a student. Re-sending a month replaces it."""

    month: date
    avg_score: float = Field(ge=0, le=100)
    attendance_pct: float = Field(ge=0, le=100)
    assignments_pct: float = Field(ge=0, le=100)
    late_arrivals: int = Field(ge=0, le=31)
    failed_subjects: int = Field(ge=0, le=12)
    guardian_engagement: int = Field(ge=1, le=5)


class StudentCreate(CamelModel):
    """Add a student, optionally with their first monthly record."""

    student_code: StudentCode
    name: ShortText
    class_id: int
    guardian_contact: Annotated[str, StringConstraints(strip_whitespace=True, max_length=120)] | None = None
    record: MonthlyRecordIn | None = None

    @field_validator("student_code")
    @classmethod
    def valid_code(cls, value: str) -> str:
        """Student codes are used in URLs and CSV files, so keep them simple."""
        return _check_code(value)

    @field_validator("name")
    @classmethod
    def tidy_name(cls, value: str) -> str:
        """Collapse whitespace and drop control characters."""
        return clean_text(value)


class StudentUpdate(CamelModel):
    """Edit a student; omitted fields stay as they are."""

    name: ShortText | None = None
    class_id: int | None = None
    guardian_contact: Annotated[str, StringConstraints(strip_whitespace=True, max_length=120)] | None = None
    dropped_out: bool | None = None

    @field_validator("name")
    @classmethod
    def tidy_name(cls, value: str | None) -> str | None:
        """Collapse whitespace and drop control characters."""
        return None if value is None else clean_text(value)


class InterventionIn(CamelModel):
    """Set the follow-up status and notes."""

    status: StatusName
    notes: str = Field(default="", max_length=2000)

    @field_validator("notes")
    @classmethod
    def tidy_notes(cls, value: str) -> str:
        """Drop control characters but keep line breaks."""
        return "\n".join(clean_text(line) for line in value.splitlines()).strip()
