"""Students: listing, detail, creation, editing, monthly records and follow-up."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session
from sqlalchemy.sql import Select

from app.core.cache import dashboard_cache
from app.core.errors import conflict, forbidden, not_found
from app.core.timeutil import first_of_month, utcnow
from app.ml.data import point_from_record
from app.ml.explain import suggest_actions
from app.ml.features import compute_features
from app.models import Class, Intervention, MonthlyRecord, Prediction, Student, TeacherClass, User
from app.models.enums import InterventionStatus, Role
from app.schemas.common import Page
from app.schemas.student import (
    Features,
    FollowUp,
    InterventionIn,
    MonthlyRecordIn,
    StudentCreate,
    StudentDetail,
    StudentSummary,
    StudentUpdate,
)
from app.services import audit_service, prediction_service

SORT_COLUMNS = {
    "name": Student.name,
    "code": Student.student_code,
    "grade": Class.grade,
    "risk": Prediction.probability,
    "status": Intervention.status,
}
SERIES_LENGTH = 12


@dataclass(frozen=True)
class StudentFilters:
    """Filters shared by the list and the CSV export."""

    q: str | None = None
    class_id: int | None = None
    grade: int | None = None
    department: str | None = None
    risk: str | None = None
    status: str | None = None


# --------------------------------------------------------------------------- access control


def class_scope(session: Session, user: User) -> list[int] | None:
    """Class ids the user may see, or None for everyone (administrators and viewers)."""
    if user.role == Role.TEACHER.value:
        return list(session.scalars(select(TeacherClass.class_id).where(TeacherClass.teacher_id == user.id)))
    return None


def require_writer(user: User) -> None:
    """Administrators and teachers may change data; viewers may not."""
    if user.role == Role.VIEWER.value:
        raise forbidden("Viewer accounts are read-only")


def _require_class_access(session: Session, user: User, class_id: int) -> None:
    scope = class_scope(session, user)
    if scope is not None and class_id not in scope:
        raise forbidden("You can only manage students in your own classes")


# --------------------------------------------------------------------------- queries


def _latest_prediction_ids() -> Select[Any]:
    return select(func.max(Prediction.id)).group_by(Prediction.student_id)


def _joined(stmt: Select[Any]) -> Select[Any]:
    return (
        stmt.select_from(Student)
        .join(Class, Class.id == Student.class_id)
        .outerjoin(
            Prediction,
            and_(Prediction.student_id == Student.id, Prediction.id.in_(_latest_prediction_ids())),
        )
        .outerjoin(Intervention, Intervention.student_id == Student.id)
    )


def _conditions(session: Session, user: User, filters: StudentFilters) -> list[Any]:
    conditions: list[Any] = []
    scope = class_scope(session, user)
    if scope is not None:
        conditions.append(Student.class_id.in_(scope))
    if filters.q:
        escaped = filters.q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_").lower()
        pattern = f"%{escaped}%"
        conditions.append(
            func.lower(Student.name).like(pattern, escape="\\")
            | func.lower(Student.student_code).like(pattern, escape="\\")
        )
    if filters.class_id is not None:
        conditions.append(Student.class_id == filters.class_id)
    if filters.grade is not None:
        conditions.append(Class.grade == filters.grade)
    if filters.department:
        conditions.append(Class.department == filters.department)
    if filters.risk == "unscored":
        conditions.append(Prediction.id.is_(None))
    elif filters.risk:
        conditions.append(Prediction.risk_level == filters.risk)
    if filters.status:
        if filters.status == InterventionStatus.NOT_STARTED.value:
            conditions.append(Intervention.id.is_(None) | (Intervention.status == filters.status))
        else:
            conditions.append(Intervention.status == filters.status)
    return conditions


def _records_by_student(session: Session, student_ids: Sequence[int]) -> dict[int, list[MonthlyRecord]]:
    grouped: dict[int, list[MonthlyRecord]] = {sid: [] for sid in student_ids}
    if not student_ids:
        return grouped
    rows = session.scalars(
        select(MonthlyRecord)
        .where(MonthlyRecord.student_id.in_(list(student_ids)))
        .order_by(MonthlyRecord.student_id, MonthlyRecord.month)
    )
    for record in rows:
        grouped[record.student_id].append(record)
    return grouped


def _features_out(records: Sequence[MonthlyRecord], grade: int) -> Features | None:
    values = compute_features([point_from_record(r) for r in records], grade)
    if values is None:
        return None
    return Features(**{k: round(v, 2) for k, v in values.items() if k != "grade"})


def _summary_fields(
    student: Student,
    klass: Class,
    prediction: Prediction | None,
    intervention: Intervention | None,
    records: Sequence[MonthlyRecord],
) -> dict[str, Any]:
    recent = list(records)[-SERIES_LENGTH:]
    return {
        "id": student.id,
        "student_code": student.student_code,
        "name": student.name,
        "department": klass.department,
        "grade": klass.grade,
        "section": klass.section,
        "class_id": klass.id,
        "score_series": [r.avg_score for r in recent],
        "att_series": [r.attendance_pct for r in recent],
        "features": _features_out(records, klass.grade),
        "prob": None if prediction is None else round(prediction.probability, 4),
        "risk_level": None if prediction is None else prediction.risk_level,
        "follow_up_status": intervention.status if intervention else InterventionStatus.NOT_STARTED.value,
    }


def list_students(
    session: Session,
    user: User,
    filters: StudentFilters,
    page: int,
    page_size: int,
    sort: str,
    descending: bool,
) -> Page[StudentSummary]:
    """One page of students visible to `user`."""
    conditions = _conditions(session, user, filters)
    total = session.scalar(_joined(select(func.count(Student.id))).where(*conditions)) or 0

    sort_column = SORT_COLUMNS.get(sort, Prediction.probability)
    ordering = sort_column.desc().nulls_last() if descending else sort_column.asc().nulls_last()
    rows = session.execute(
        _joined(select(Student, Class, Prediction, Intervention))
        .where(*conditions)
        .order_by(ordering, Student.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()

    records = _records_by_student(session, [student.id for student, *_ in rows])
    items = [
        StudentSummary(**_summary_fields(student, klass, prediction, intervention, records[student.id]))
        for student, klass, prediction, intervention in rows
    ]
    return Page.of(items, total, page, page_size)


def get_student(session: Session, user: User, student_id: int) -> Student:
    """Fetch a student the user is allowed to see; out-of-scope students look like missing ones."""
    conditions = _conditions(session, user, StudentFilters())
    student = session.scalar(select(Student).where(Student.id == student_id, *conditions).limit(1))
    if student is None:
        raise not_found("Student")
    return student


def get_detail(session: Session, user: User, student_id: int) -> StudentDetail:
    """Full detail for one student."""
    student = get_student(session, user, student_id)
    klass = session.get(Class, student.class_id)
    assert klass is not None  # foreign key guarantees the class exists
    prediction = session.scalar(
        select(Prediction).where(Prediction.student_id == student.id).order_by(Prediction.id.desc()).limit(1)
    )
    intervention = session.scalar(select(Intervention).where(Intervention.student_id == student.id))
    records = _records_by_student(session, [student.id])[student.id]

    author = None
    if intervention is not None and intervention.updated_by is not None:
        author = session.scalar(select(User.name).where(User.id == intervention.updated_by))
    factors = list(prediction.top_factors) if prediction else []
    risk = prediction.risk_level if prediction else "low"

    return StudentDetail(
        **_summary_fields(student, klass, prediction, intervention, records),
        guardian_contact=None if user.role == Role.VIEWER.value else student.guardian_contact,
        dropped_out=student.dropped_out,
        months=[r.month.strftime("%Y-%m") for r in records[-SERIES_LENGTH:]],
        next_term_score=None if prediction is None else prediction.next_term_score,
        model_version=None if prediction is None else prediction.model_version,
        predicted_at=None if prediction is None else prediction.created_at,
        factors=factors,
        suggested_actions=suggest_actions(factors, risk) if prediction else [],
        follow_up=FollowUp(
            status=intervention.status if intervention else InterventionStatus.NOT_STARTED.value,
            notes=intervention.notes if intervention else "",
            updated_at=intervention.updated_at if intervention else None,
            updated_by=author,
        ),
    )


# --------------------------------------------------------------------------- writes


def _save_record(session: Session, student_id: int, payload: MonthlyRecordIn) -> None:
    month = first_of_month(payload.month)
    record = session.scalar(
        select(MonthlyRecord).where(MonthlyRecord.student_id == student_id, MonthlyRecord.month == month)
    )
    if record is None:
        record = MonthlyRecord(student_id=student_id, month=month)
        session.add(record)
    record.avg_score = payload.avg_score
    record.attendance_pct = payload.attendance_pct
    record.assignments_pct = payload.assignments_pct
    record.late_arrivals = payload.late_arrivals
    record.failed_subjects = payload.failed_subjects
    record.guardian_engagement = payload.guardian_engagement


def create_student(session: Session, user: User, payload: StudentCreate) -> StudentDetail:
    """Add a student (and optionally their first monthly record), then score them."""
    require_writer(user)
    if session.get(Class, payload.class_id) is None:
        raise not_found("Class")
    _require_class_access(session, user, payload.class_id)
    if session.scalar(select(Student.id).where(Student.student_code == payload.student_code)) is not None:
        raise conflict(f"A student with code {payload.student_code} already exists")

    student = Student(
        student_code=payload.student_code,
        name=payload.name,
        class_id=payload.class_id,
        guardian_contact=payload.guardian_contact or None,
    )
    session.add(student)
    session.flush()
    if payload.record is not None:
        _save_record(session, student.id, payload.record)
    session.commit()
    audit_service.record(session, user.id, "student_create", "student", student.id, {"code": student.student_code})
    if payload.record is not None:
        prediction_service.predict_students_if_model(session, [student.id])
    dashboard_cache.clear()
    return get_detail(session, user, student.id)


def update_student(session: Session, user: User, student_id: int, payload: StudentUpdate) -> StudentDetail:
    """Edit a student's name, class, guardian contact or known outcome."""
    require_writer(user)
    student = get_student(session, user, student_id)
    if payload.class_id is not None and payload.class_id != student.class_id:
        if session.get(Class, payload.class_id) is None:
            raise not_found("Class")
        _require_class_access(session, user, payload.class_id)
        student.class_id = payload.class_id
    if payload.name is not None:
        student.name = payload.name
    if "guardian_contact" in payload.model_fields_set:
        student.guardian_contact = payload.guardian_contact or None
    if "dropped_out" in payload.model_fields_set:
        if user.role != Role.ADMIN.value:
            raise forbidden("Only administrators can record a dropout outcome")
        student.dropped_out = payload.dropped_out
    session.commit()
    audit_service.record(session, user.id, "student_update", "student", student.id)
    if payload.class_id is not None:
        prediction_service.predict_students_if_model(session, [student.id])
    dashboard_cache.clear()
    return get_detail(session, user, student.id)


def delete_student(session: Session, user: User, student_id: int) -> None:
    """Delete a student and everything recorded about them (administrators only)."""
    if user.role != Role.ADMIN.value:
        raise forbidden("Only administrators can delete students")
    student = get_student(session, user, student_id)
    code = student.student_code
    session.delete(student)
    session.commit()
    audit_service.record(session, user.id, "student_delete", "student", student_id, {"code": code})
    dashboard_cache.clear()


def upsert_record(session: Session, user: User, student_id: int, payload: MonthlyRecordIn) -> StudentDetail:
    """Add or replace one month of data for a student and refresh their prediction."""
    require_writer(user)
    student = get_student(session, user, student_id)
    _save_record(session, student.id, payload)
    session.commit()
    prediction_service.predict_students_if_model(session, [student.id])
    dashboard_cache.clear()
    return get_detail(session, user, student.id)


def recompute_prediction(session: Session, user: User, student_id: int) -> StudentDetail:
    """Re-score one student with the active model."""
    student = get_student(session, user, student_id)
    prediction_service.predict_students(session, [student.id])
    return get_detail(session, user, student.id)


# --------------------------------------------------------------------------- follow-up


def get_follow_up(session: Session, user: User, student_id: int) -> FollowUp:
    """Current follow-up status and notes."""
    get_student(session, user, student_id)
    intervention = session.scalar(select(Intervention).where(Intervention.student_id == student_id))
    if intervention is None:
        return FollowUp()
    author = None
    if intervention.updated_by is not None:
        author = session.scalar(select(User.name).where(User.id == intervention.updated_by))
    return FollowUp(
        status=intervention.status,  # type: ignore[arg-type]
        notes=intervention.notes,
        updated_at=intervention.updated_at,
        updated_by=author,
    )


def set_follow_up(session: Session, user: User, student_id: int, payload: InterventionIn) -> FollowUp:
    """Update follow-up status and notes, recording who changed what."""
    require_writer(user)
    get_student(session, user, student_id)
    intervention = session.scalar(select(Intervention).where(Intervention.student_id == student_id))
    previous = intervention.status if intervention else InterventionStatus.NOT_STARTED.value
    if intervention is None:
        intervention = Intervention(student_id=student_id)
        session.add(intervention)
    intervention.status = payload.status
    intervention.notes = payload.notes
    intervention.updated_by = user.id
    intervention.updated_at = utcnow()
    session.commit()
    audit_service.record(
        session, user.id, "status_change", "student", student_id, {"from": previous, "to": payload.status}
    )
    dashboard_cache.clear()
    return get_follow_up(session, user, student_id)


# --------------------------------------------------------------------------- export


def export_rows(session: Session, user: User, filters: StudentFilters) -> list[dict[str, Any]]:
    """Flat rows (all matching students, no paging) for the CSV export."""
    rows = session.execute(
        _joined(select(Student, Class, Prediction, Intervention))
        .where(*_conditions(session, user, filters))
        .order_by(Class.department, Class.grade, Class.section, Student.name)
    ).all()
    records = _records_by_student(session, [student.id for student, *_ in rows])
    exported: list[dict[str, Any]] = []
    for student, klass, prediction, intervention in rows:
        features = _features_out(records[student.id], klass.grade)
        exported.append(
            {
                "student_code": student.student_code,
                "name": student.name,
                "department": klass.department,
                "year": klass.grade,
                "section": klass.section,
                "attendance": None if features is None else features.attendance,
                "score": None if features is None else features.score,
                "assignments": None if features is None else features.assignments,
                "failures": None if features is None else features.failures,
                "late_per_month": None if features is None else features.late,
                "guardian_engagement": None if features is None else features.parent,
                "score_trend_per_month": None if features is None else features.trend,
                "dropout_probability": None if prediction is None else round(prediction.probability, 4),
                "risk_level": None if prediction is None else prediction.risk_level,
                "next_term_score": None if prediction is None else prediction.next_term_score,
                "follow_up_status": intervention.status if intervention else InterventionStatus.NOT_STARTED.value,
            }
        )
    return exported
