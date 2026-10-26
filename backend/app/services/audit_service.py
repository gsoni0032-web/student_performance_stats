"""Append-only audit trail for sensitive actions."""

from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import AuditLog, User
from app.schemas.common import Page
from app.schemas.user import AuditEntry


def record(
    session: Session,
    user_id: int | None,
    action: str,
    entity: str,
    entity_id: str | int | None = None,
    detail: dict[str, Any] | None = None,
) -> None:
    """Write one audit row and commit it."""
    session.add(
        AuditLog(
            user_id=user_id,
            action=action,
            entity=entity,
            entity_id=None if entity_id is None else str(entity_id),
            detail=detail,
        )
    )
    session.commit()


def list_entries(session: Session, page: int, page_size: int, action: str | None) -> Page[AuditEntry]:
    """Newest audit entries first, optionally filtered by action."""
    conditions = [AuditLog.action == action] if action else []
    total = session.scalar(select(func.count(AuditLog.id)).where(*conditions)) or 0
    rows = session.execute(
        select(AuditLog, User.name)
        .outerjoin(User, User.id == AuditLog.user_id)
        .where(*conditions)
        .order_by(AuditLog.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    items = [
        AuditEntry(
            id=log.id,
            user_id=log.user_id,
            user_name=name,
            action=log.action,
            entity=log.entity,
            entity_id=log.entity_id,
            detail=log.detail,
            timestamp=log.timestamp,
        )
        for log, name in rows
    ]
    return Page.of(items, total, page, page_size)
