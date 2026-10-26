"""Class (cohort) administration."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.cache import dashboard_cache
from app.core.errors import conflict, not_found
from app.models import Class, Student, TeacherClass
from app.schemas.common import Page
from app.schemas.user import ClassIn, ClassOut


def _out(klass: Class, student_count: int, teacher_ids: list[int]) -> ClassOut:
    return ClassOut(
        id=klass.id,
        department=klass.department,
        grade=klass.grade,
        section=klass.section,
        academic_year=klass.academic_year,
        label=klass.label,
        student_count=student_count,
        teacher_ids=sorted(teacher_ids),
    )


def list_classes(
    session: Session, page: int, page_size: int, only_ids: list[int] | None = None
) -> Page[ClassOut]:
    """Paginated classes with student counts. `only_ids` restricts the list (for teachers)."""
    conditions = [] if only_ids is None else [Class.id.in_(only_ids)]
    total = session.scalar(select(func.count(Class.id)).where(*conditions)) or 0
    classes = session.scalars(
        select(Class)
        .where(*conditions)
        .order_by(Class.department, Class.grade, Class.section)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    ids = [c.id for c in classes]
    counts = dict(
        session.execute(
            select(Student.class_id, func.count(Student.id)).where(Student.class_id.in_(ids)).group_by(Student.class_id)
        ).all()
    )
    teachers: dict[int, list[int]] = {}
    for class_id, teacher_id in session.execute(
        select(TeacherClass.class_id, TeacherClass.teacher_id).where(TeacherClass.class_id.in_(ids))
    ):
        teachers.setdefault(class_id, []).append(teacher_id)
    return Page.of(
        [_out(c, counts.get(c.id, 0), teachers.get(c.id, [])) for c in classes], total, page, page_size
    )


def get_class(session: Session, class_id: int) -> Class:
    """Fetch a class or raise 404."""
    klass = session.get(Class, class_id)
    if klass is None:
        raise not_found("Class")
    return klass


def _ensure_unique(session: Session, payload: ClassIn, ignore_id: int | None = None) -> None:
    existing = session.scalar(
        select(Class.id).where(
            Class.department == payload.department,
            Class.grade == payload.grade,
            Class.section == payload.section,
            Class.academic_year == payload.academic_year,
        )
    )
    if existing is not None and existing != ignore_id:
        raise conflict("This class already exists")


def create_class(session: Session, payload: ClassIn) -> ClassOut:
    """Create a class, refusing duplicates."""
    _ensure_unique(session, payload)
    klass = Class(**payload.model_dump())
    session.add(klass)
    session.commit()
    return _out(klass, 0, [])


def update_class(session: Session, class_id: int, payload: ClassIn) -> ClassOut:
    """Edit a class."""
    klass = get_class(session, class_id)
    _ensure_unique(session, payload, ignore_id=class_id)
    for field, value in payload.model_dump().items():
        setattr(klass, field, value)
    session.commit()
    dashboard_cache.clear()
    count = session.scalar(select(func.count(Student.id)).where(Student.class_id == class_id)) or 0
    teacher_ids = list(session.scalars(select(TeacherClass.teacher_id).where(TeacherClass.class_id == class_id)))
    return _out(klass, count, teacher_ids)


def delete_class(session: Session, class_id: int) -> None:
    """Delete an empty class."""
    klass = get_class(session, class_id)
    count = session.scalar(select(func.count(Student.id)).where(Student.class_id == class_id)) or 0
    if count:
        raise conflict(f"This class still has {count} student(s). Move or remove them first.")
    session.delete(klass)
    session.commit()
