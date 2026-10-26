"""User and class management schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import EmailStr, Field, field_validator

from app.core.security import validate_password_policy
from app.schemas.common import CamelModel, ShortText

RoleName = Literal["admin", "teacher", "viewer"]


class UserOut(CamelModel):
    """A user as shown to administrators and to themselves."""

    id: int
    name: str
    email: str
    role: RoleName
    is_active: bool
    created_at: datetime
    class_ids: list[int] = []


class UserCreate(CamelModel):
    """Create an account."""

    name: ShortText
    email: EmailStr
    password: str
    role: RoleName
    class_ids: list[int] = []

    @field_validator("password")
    @classmethod
    def check_policy(cls, value: str) -> str:
        """Apply the password policy."""
        return validate_password_policy(value)


class UserUpdate(CamelModel):
    """Change an account; omitted fields stay as they are."""

    name: ShortText | None = None
    role: RoleName | None = None
    is_active: bool | None = None
    password: str | None = None
    class_ids: list[int] | None = None

    @field_validator("password")
    @classmethod
    def check_policy(cls, value: str | None) -> str | None:
        """Apply the password policy when a new password is supplied."""
        return None if value is None else validate_password_policy(value)


class ClassIn(CamelModel):
    """Create or edit a class (a department, year of study and section)."""

    department: ShortText
    grade: int = Field(ge=1, le=6, description="Year of study")
    section: str = Field(min_length=1, max_length=10)
    academic_year: str = Field(pattern=r"^\d{4}-\d{2}$", examples=["2025-26"])


class ClassOut(CamelModel):
    """A class with its size and teachers."""

    id: int
    department: str
    grade: int
    section: str
    academic_year: str
    label: str
    student_count: int = 0
    teacher_ids: list[int] = []


class AuditEntry(CamelModel):
    """One audit log row."""

    id: int
    user_id: int | None
    user_name: str | None
    action: str
    entity: str
    entity_id: str | None
    detail: dict | None
    timestamp: datetime
