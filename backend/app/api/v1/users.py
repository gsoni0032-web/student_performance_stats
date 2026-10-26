"""User administration and the audit log (administrators only)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query, Response

from app.api.deps import AdminUser, DbSession, Pagination
from app.schemas.common import Page
from app.schemas.user import AuditEntry, UserCreate, UserOut, UserUpdate
from app.services import audit_service, user_service

router = APIRouter(tags=["admin"])


@router.get("/users", response_model=Page[UserOut])
def list_users(
    _: AdminUser,
    session: DbSession,
    paging: Pagination,
    q: Annotated[str | None, Query(max_length=100)] = None,
) -> Page[UserOut]:
    """Accounts, optionally filtered by name or email."""
    return user_service.list_users(session, paging.page, paging.page_size, q)


@router.post("/users", response_model=UserOut, status_code=201)
def create_user(payload: UserCreate, admin: AdminUser, session: DbSession) -> UserOut:
    """Create an account."""
    created = user_service.create_user(session, payload)
    audit_service.record(session, admin.id, "user_create", "user", created.id, {"role": created.role})
    return created


@router.put("/users/{user_id}", response_model=UserOut)
def update_user(user_id: int, payload: UserUpdate, admin: AdminUser, session: DbSession) -> UserOut:
    """Change a name, role, active flag, password or class assignment."""
    updated = user_service.update_user(session, admin, user_id, payload)
    audit_service.record(session, admin.id, "user_update", "user", user_id)
    return updated


@router.delete("/users/{user_id}", status_code=204)
def delete_user(user_id: int, admin: AdminUser, session: DbSession) -> Response:
    """Delete an account."""
    user_service.delete_user(session, admin, user_id)
    audit_service.record(session, admin.id, "user_delete", "user", user_id)
    return Response(status_code=204)


@router.get("/audit", response_model=Page[AuditEntry])
def audit_log(
    _: AdminUser,
    session: DbSession,
    paging: Pagination,
    action: Annotated[str | None, Query(max_length=40)] = None,
) -> Page[AuditEntry]:
    """Newest audit entries first."""
    return audit_service.list_entries(session, paging.page, paging.page_size, action)
