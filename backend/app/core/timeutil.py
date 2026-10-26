"""Time helpers. SQLite returns naive datetimes, so comparisons go through `as_utc`."""

from __future__ import annotations

from datetime import UTC, date, datetime


def utcnow() -> datetime:
    """Timezone-aware current time."""
    return datetime.now(UTC)


def as_utc(value: datetime) -> datetime:
    """Treat a naive datetime (as returned by SQLite) as UTC."""
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def first_of_month(value: date) -> date:
    """The first day of the month containing `value`."""
    return value.replace(day=1)


def academic_year_for(month: date) -> str:
    """Academic year label such as '2025-26'; the year is taken to start in July."""
    start = month.year if month.month >= 7 else month.year - 1
    return f"{start}-{(start + 1) % 100:02d}"
