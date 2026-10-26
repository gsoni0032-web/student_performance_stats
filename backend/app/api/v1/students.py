"""Student endpoints."""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, Response

from app.api.deps import AdminUser, CurrentUser, DbSession, Pagination, WriterUser
from app.schemas.common import Page
from app.schemas.student import (
    FollowUp,
    InterventionIn,
    MonthlyRecordIn,
    StudentCreate,
    StudentDetail,
    StudentSummary,
    StudentUpdate,
)
from app.services import student_service
from app.services.student_service import StudentFilters

router = APIRouter(prefix="/students", tags=["students"])


def filters_from_query(
    q: Annotated[str | None, Query(max_length=100, description="Search name or student code")] = None,
    class_id: int | None = None,
    grade: Annotated[int | None, Query(ge=1, le=6, description="Year of study")] = None,
    department: Annotated[str | None, Query(max_length=80)] = None,
    risk: Literal["low", "medium", "high", "unscored"] | None = None,
    status: Literal["not_started", "guardian_contacted", "support_plan_active", "resolved"] | None = None,
) -> StudentFilters:
    """Collect the filters shared by the list and the CSV export."""
    return StudentFilters(q=q, class_id=class_id, grade=grade, department=department, risk=risk, status=status)


Filters = Annotated[StudentFilters, Depends(filters_from_query)]


@router.get("", response_model=Page[StudentSummary])
def list_students(
    user: CurrentUser,
    session: DbSession,
    paging: Pagination,
    filters: Filters,
    sort: Literal["risk", "name", "code", "grade", "status"] = "risk",
    order: Literal["asc", "desc"] = "desc",
) -> Page[StudentSummary]:
    """Search, filter, sort and page through the students you are allowed to see."""
    return student_service.list_students(
        session, user, filters, paging.page, paging.page_size, sort, order == "desc"
    )


@router.post("", response_model=StudentDetail, status_code=201)
def create_student(payload: StudentCreate, user: WriterUser, session: DbSession) -> StudentDetail:
    """Add a student. Teachers can add students to their own classes; admins to any class."""
    return student_service.create_student(session, user, payload)


@router.get("/{student_id}", response_model=StudentDetail)
def get_student(student_id: int, user: CurrentUser, session: DbSession) -> StudentDetail:
    """Profile, monthly series, latest prediction, factors and follow-up."""
    return student_service.get_detail(session, user, student_id)


@router.put("/{student_id}", response_model=StudentDetail)
def update_student(
    student_id: int, payload: StudentUpdate, user: WriterUser, session: DbSession
) -> StudentDetail:
    """Edit a student's name, class, guardian contact or known outcome."""
    return student_service.update_student(session, user, student_id, payload)


@router.delete("/{student_id}", status_code=204)
def delete_student(student_id: int, user: AdminUser, session: DbSession) -> Response:
    """Delete a student and all of their data (administrators only)."""
    student_service.delete_student(session, user, student_id)
    return Response(status_code=204)


@router.post("/{student_id}/records", response_model=StudentDetail)
def save_record(
    student_id: int, payload: MonthlyRecordIn, user: WriterUser, session: DbSession
) -> StudentDetail:
    """Add or replace one month of data; the student is re-scored when a model exists."""
    return student_service.upsert_record(session, user, student_id, payload)


@router.post("/{student_id}/predict", response_model=StudentDetail)
def recompute_prediction(student_id: int, user: WriterUser, session: DbSession) -> StudentDetail:
    """Re-score one student with the active model."""
    return student_service.recompute_prediction(session, user, student_id)


@router.get("/{student_id}/intervention", response_model=FollowUp)
def get_intervention(student_id: int, user: CurrentUser, session: DbSession) -> FollowUp:
    """Follow-up status and notes."""
    return student_service.get_follow_up(session, user, student_id)


@router.put("/{student_id}/intervention", response_model=FollowUp)
def put_intervention(
    student_id: int, payload: InterventionIn, user: WriterUser, session: DbSession
) -> FollowUp:
    """Update follow-up status and notes (admins and teachers)."""
    return student_service.set_follow_up(session, user, student_id, payload)
