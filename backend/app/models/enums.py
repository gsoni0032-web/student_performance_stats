"""String enumerations shared by models, schemas and services."""

from __future__ import annotations

from enum import StrEnum


class Role(StrEnum):
    """Account roles."""

    ADMIN = "admin"
    TEACHER = "teacher"
    VIEWER = "viewer"


class RiskLevel(StrEnum):
    """Dropout risk bands derived from probability and the configured thresholds."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class InterventionStatus(StrEnum):
    """Follow-up progress for a student."""

    NOT_STARTED = "not_started"
    GUARDIAN_CONTACTED = "guardian_contacted"
    SUPPORT_PLAN_ACTIVE = "support_plan_active"
    RESOLVED = "resolved"
