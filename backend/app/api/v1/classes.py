"""Class (cohort) endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Response

from app.api.deps import AdminUser, CurrentUser, DbSession, Pagination
from app.schemas.common import Page
from app.schemas.user import ClassIn, ClassOut
from app.services import audit_service, class_service, student_service

router = APIRouter(prefix="/classes", tags=["classes"])


@router.get("", response_model=Page[ClassOut])
def list_classes(user: CurrentUser, session: DbSession, paging: Pagination) -> Page[ClassOut]:
    """Classes you can see: all of them, or only your own if you are a teacher."""
    scope = student_service.class_scope(session, user)
    return class_service.list_classes(session, paging.page, paging.page_size, scope)


@router.post("", response_model=ClassOut, status_code=201)
def create_class(payload: ClassIn, user: AdminUser, session: DbSession) -> ClassOut:
    """Create a class."""
    created = class_service.create_class(session, payload)
    audit_service.record(session, user.id, "class_create", "class", created.id)
    return created


@router.put("/{class_id}", response_model=ClassOut)
def update_class(class_id: int, payload: ClassIn, user: AdminUser, session: DbSession) -> ClassOut:
    """Edit a class."""
    updated = class_service.update_class(session, class_id, payload)
    audit_service.record(session, user.id, "class_update", "class", class_id)
    return updated


@router.delete("/{class_id}", status_code=204)
def delete_class(class_id: int, user: AdminUser, session: DbSession) -> Response:
    """Delete an empty class."""
    class_service.delete_class(session, class_id)
    audit_service.record(session, user.id, "class_delete", "class", class_id)
    return Response(status_code=204)
