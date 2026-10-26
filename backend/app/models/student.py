"""Classes, students, monthly academic records and follow-up interventions."""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.timeutil import utcnow
from app.models.enums import InterventionStatus
from app.models.user import User


class Class(Base):
    """A cohort of students: department, year of study and section for one academic year."""

    __tablename__ = "classes"
    __table_args__ = (
        UniqueConstraint("department", "grade", "section", "academic_year", name="uq_classes_cohort"),
        CheckConstraint("grade BETWEEN 1 AND 6", name="grade_range"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    department: Mapped[str] = mapped_column(String(80))
    grade: Mapped[int] = mapped_column(Integer)  # year of study
    section: Mapped[str] = mapped_column(String(10))
    academic_year: Mapped[str] = mapped_column(String(9))

    teachers: Mapped[list[User]] = relationship(secondary="teacher_classes", back_populates="classes")
    students: Mapped[list[Student]] = relationship(back_populates="klass")

    @property
    def label(self) -> str:
        """Human-readable name such as 'Computer Science · Year 2 · A'."""
        return f"{self.department} · Year {self.grade} · {self.section}"


class Student(Base):
    """An enrolled student. `dropped_out` is the known outcome (null while still unknown)."""

    __tablename__ = "students"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_code: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120), index=True)
    class_id: Mapped[int] = mapped_column(ForeignKey("classes.id", ondelete="RESTRICT"), index=True)
    guardian_contact: Mapped[str | None] = mapped_column(String(120), nullable=True)
    dropped_out: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    klass: Mapped[Class] = relationship(back_populates="students")
    records: Mapped[list[MonthlyRecord]] = relationship(
        back_populates="student", cascade="all, delete-orphan", order_by="MonthlyRecord.month"
    )
    intervention: Mapped[Intervention | None] = relationship(
        back_populates="student", cascade="all, delete-orphan", uselist=False
    )


class MonthlyRecord(Base):
    """One month of academic data for one student."""

    __tablename__ = "monthly_records"
    __table_args__ = (
        UniqueConstraint("student_id", "month", name="uq_monthly_records_student_month"),
        CheckConstraint("avg_score BETWEEN 0 AND 100", name="score_range"),
        CheckConstraint("attendance_pct BETWEEN 0 AND 100", name="attendance_range"),
        CheckConstraint("assignments_pct BETWEEN 0 AND 100", name="assignments_range"),
        CheckConstraint("guardian_engagement BETWEEN 1 AND 5", name="engagement_range"),
        CheckConstraint("late_arrivals >= 0", name="late_non_negative"),
        CheckConstraint("failed_subjects >= 0", name="failed_non_negative"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"), index=True
    )
    month: Mapped[date] = mapped_column(Date)
    avg_score: Mapped[float] = mapped_column(Float)
    attendance_pct: Mapped[float] = mapped_column(Float)
    assignments_pct: Mapped[float] = mapped_column(Float)
    late_arrivals: Mapped[int] = mapped_column(Integer)
    failed_subjects: Mapped[int] = mapped_column(Integer)
    guardian_engagement: Mapped[int] = mapped_column(Integer)

    student: Mapped[Student] = relationship(back_populates="records")


class Intervention(Base):
    """Follow-up status and notes for one student."""

    __tablename__ = "interventions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"), unique=True
    )
    status: Mapped[str] = mapped_column(String(30), default=InterventionStatus.NOT_STARTED.value)
    notes: Mapped[str] = mapped_column(Text, default="")
    updated_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    student: Mapped[Student] = relationship(back_populates="intervention")
    author: Mapped[User | None] = relationship()
