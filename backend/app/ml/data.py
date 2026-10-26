"""Load training data from the database."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.ml.features import MonthPoint
from app.ml.pipeline import StudentSeries
from app.models import MonthlyRecord, Student


def point_from_record(record: MonthlyRecord) -> MonthPoint:
    """Convert a `MonthlyRecord` row into the pipeline's plain value object."""
    return MonthPoint(
        avg_score=record.avg_score,
        attendance_pct=record.attendance_pct,
        assignments_pct=record.assignments_pct,
        late_arrivals=record.late_arrivals,
        failed_subjects=record.failed_subjects,
        guardian_engagement=record.guardian_engagement,
    )


def load_student_series(session: Session) -> list[StudentSeries]:
    """Every student with at least one monthly record, with their known outcome (or None)."""
    students = session.scalars(
        select(Student).options(selectinload(Student.records), selectinload(Student.klass))
    ).all()
    return [
        StudentSeries(
            grade=student.klass.grade,
            points=[point_from_record(r) for r in student.records],
            dropped_out=student.dropped_out,
        )
        for student in students
        if student.records
    ]
