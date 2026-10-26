"""CSV import (validated row by row) and CSV export."""

from __future__ import annotations

import csv
import io
import logging
import re
from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.cache import dashboard_cache
from app.core.errors import bad_request
from app.core.timeutil import academic_year_for, first_of_month, utcnow
from app.models import Class, MonthlyRecord, Student, User
from app.schemas.common import clean_text
from app.schemas.prediction import ImportResult, RowIssue
from app.services import audit_service, prediction_service, student_service

logger = logging.getLogger("pathway.import")

MAX_BYTES = 5 * 1024 * 1024
MAX_ROWS = 50_000
REQUIRED_COLUMNS = [
    "student_code",
    "name",
    "department",
    "year",
    "section",
    "month",
    "avg_score",
    "attendance_pct",
    "assignments_pct",
    "late_arrivals",
    "failed_subjects",
    "guardian_engagement",
]
OPTIONAL_COLUMNS = ["academic_year", "guardian_contact", "dropped_out"]
EXPORT_COLUMNS = [
    "student_code",
    "name",
    "department",
    "year",
    "section",
    "attendance",
    "score",
    "assignments",
    "failures",
    "late_per_month",
    "guardian_engagement",
    "score_trend_per_month",
    "dropout_probability",
    "risk_level",
    "next_term_score",
    "follow_up_status",
]
_TRUE = {"1", "true", "yes", "y", "dropped", "dropped_out"}
_FALSE = {"0", "false", "no", "n", "active", "enrolled"}


class ImportRow(BaseModel):
    """One validated CSV row (one student in one month)."""

    model_config = ConfigDict(str_strip_whitespace=True)

    student_code: str = Field(min_length=2, max_length=30, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
    name: str = Field(min_length=1, max_length=120)
    department: str = Field(min_length=1, max_length=80)
    year: int = Field(ge=1, le=6)
    section: str = Field(min_length=1, max_length=10)
    month: date
    avg_score: float = Field(ge=0, le=100)
    attendance_pct: float = Field(ge=0, le=100)
    assignments_pct: float = Field(ge=0, le=100)
    late_arrivals: int = Field(ge=0, le=31)
    failed_subjects: int = Field(ge=0, le=12)
    guardian_engagement: int = Field(ge=1, le=5)
    academic_year: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}$")
    guardian_contact: str | None = Field(default=None, max_length=120)
    dropped_out: bool | None = None

    @field_validator("academic_year", "guardian_contact", "dropped_out", mode="before")
    @classmethod
    def blank_is_none(cls, value: Any) -> Any:
        """Optional columns may be left empty."""
        return None if isinstance(value, str) and not value.strip() else value

    @field_validator("month", mode="before")
    @classmethod
    def parse_month(cls, value: Any) -> Any:
        """Accept YYYY-MM as well as full ISO dates; the month is normalised to its first day."""
        if isinstance(value, str):
            text = value.strip()
            if len(text) == 7 and text[4] == "-":
                text = f"{text}-01"
            try:
                return first_of_month(date.fromisoformat(text))
            except ValueError as error:
                raise ValueError("Use a month like 2026-03 or 2026-03-01") from error
        return value

    @field_validator("dropped_out", mode="before")
    @classmethod
    def parse_outcome(cls, value: Any) -> Any:
        """Accept 1/0, true/false, yes/no."""
        if isinstance(value, str):
            lowered = value.strip().lower()
            if lowered in _TRUE:
                return True
            if lowered in _FALSE:
                return False
            raise ValueError("Use 1/0, true/false or yes/no")
        return value

    @field_validator("student_code", "name", "department", "section", "guardian_contact")
    @classmethod
    def no_formula_prefix(cls, value: str | None) -> str | None:
        """Reject cells that spreadsheet programs would treat as formulas."""
        if value and value[0] in "=@":
            raise ValueError("Must not start with '=' or '@'")
        if value and value[0] in "+-" and not re.sub(r"[ \-()]", "", value[1:]).isdigit():
            raise ValueError("Must not start with '+' or '-' unless it is a phone number")
        return clean_text(value) if value else value


@dataclass
class ParsedImport:
    """The outcome of parsing and validating a file, before anything is written."""

    rows_read: int = 0
    rows: list[tuple[int, ImportRow]] = field(default_factory=list)
    issues: list[RowIssue] = field(default_factory=list)


def _decode(content: bytes) -> str:
    if len(content) > MAX_BYTES:
        raise bad_request(f"The file is larger than {MAX_BYTES // (1024 * 1024)} MB")
    try:
        return content.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise bad_request("The file is not valid UTF-8 text. Save it as 'CSV UTF-8' and try again.") from error


def parse_csv(content: bytes) -> ParsedImport:
    """Validate every row and collect all problems instead of stopping at the first."""
    reader = csv.DictReader(io.StringIO(_decode(content)))
    result = ParsedImport()
    header = [(name or "").strip().lower() for name in (reader.fieldnames or [])]
    missing = [column for column in REQUIRED_COLUMNS if column not in header]
    if missing:
        result.issues.append(
            RowIssue(row=1, column=None, message="Missing required column(s): " + ", ".join(missing))
        )
        return result
    reader.fieldnames = header

    identity: dict[str, tuple[int, tuple[str, int, str]]] = {}
    seen_months: dict[tuple[str, date], int] = {}
    for line_number, raw in enumerate(reader, start=2):
        result.rows_read += 1
        if result.rows_read > MAX_ROWS:
            result.issues.append(RowIssue(row=line_number, column=None, message=f"More than {MAX_ROWS} rows; split the file"))
            break
        data = {key: value for key, value in raw.items() if key in REQUIRED_COLUMNS + OPTIONAL_COLUMNS and value is not None}
        try:
            row = ImportRow(**data)
        except ValidationError as error:
            for problem in error.errors():
                column = str(problem["loc"][0]) if problem["loc"] else None
                shown = str(problem.get("input", ""))[:40]
                result.issues.append(
                    RowIssue(row=line_number, column=column, message=f"{problem['msg']} (got '{shown}')")
                )
            continue

        who = (row.department, row.year, row.section)
        first = identity.setdefault(row.student_code, (line_number, who))
        if first[1] != who:
            result.issues.append(
                RowIssue(
                    row=line_number,
                    column="department",
                    message=f"{row.student_code} appears in a different class on row {first[0]}",
                )
            )
            continue
        month_key = (row.student_code, row.month)
        if month_key in seen_months:
            result.issues.append(
                RowIssue(
                    row=line_number,
                    column="month",
                    message=f"Duplicate month for {row.student_code}; first seen on row {seen_months[month_key]}",
                )
            )
            continue
        seen_months[month_key] = line_number
        result.rows.append((line_number, row))
    return result


def _chunks(items: Sequence[str], size: int = 500) -> Iterator[Sequence[str]]:
    for start in range(0, len(items), size):
        yield items[start : start + size]


def _write_rows(session: Session, rows: Iterable[ImportRow]) -> tuple[int, int, list[int]]:
    """Insert or update classes, students and monthly records. Returns counts and student ids."""
    rows = list(rows)
    classes = {(c.department, c.grade, c.section, c.academic_year): c for c in session.scalars(select(Class))}
    codes = sorted({r.student_code for r in rows})
    students: dict[str, Student] = {}
    for chunk in _chunks(codes):
        for student in session.scalars(select(Student).where(Student.student_code.in_(list(chunk)))):
            students[student.student_code] = student

    pre_existing = set(students)
    touched: dict[str, Student] = {}
    record_count = 0
    existing_records: dict[tuple[int, date], MonthlyRecord] = {}
    loaded: set[int] = set()
    for row in rows:
        year_label = row.academic_year or academic_year_for(row.month)
        key = (row.department, row.year, row.section, year_label)
        klass = classes.get(key)
        if klass is None:
            klass = Class(department=row.department, grade=row.year, section=row.section, academic_year=year_label)
            session.add(klass)
            session.flush()
            classes[key] = klass

        student = students.get(row.student_code)
        if student is None:
            student = Student(student_code=row.student_code, name=row.name, class_id=klass.id)
            session.add(student)
            session.flush()
            students[row.student_code] = student
        student.name = row.name
        student.class_id = klass.id
        if row.guardian_contact is not None:
            student.guardian_contact = row.guardian_contact
        if row.dropped_out is not None:
            student.dropped_out = row.dropped_out
        touched[row.student_code] = student

        if row.student_code in pre_existing and student.id not in loaded:
            loaded.add(student.id)
            for existing in session.scalars(select(MonthlyRecord).where(MonthlyRecord.student_id == student.id)):
                existing_records[(existing.student_id, existing.month)] = existing
        record = existing_records.get((student.id, row.month))
        if record is None:
            record = MonthlyRecord(student_id=student.id, month=row.month)
            session.add(record)
            existing_records[(student.id, row.month)] = record
        record.avg_score = row.avg_score
        record.attendance_pct = row.attendance_pct
        record.assignments_pct = row.assignments_pct
        record.late_arrivals = row.late_arrivals
        record.failed_subjects = row.failed_subjects
        record.guardian_engagement = row.guardian_engagement
        record_count += 1

    session.commit()
    return len(touched), record_count, [s.id for s in touched.values()]


def import_csv(
    session: Session, user: User | None, content: bytes, dry_run: bool, skip_invalid: bool
) -> ImportResult:
    """Validate a CSV and, unless `dry_run`, write it.

    By default nothing is written if any row has a problem, so a file is either imported
    completely or not at all. `skip_invalid` imports the valid rows and reports the rest.
    """
    parsed = parse_csv(content)
    preview = [
        {
            "row": line,
            "studentCode": row.student_code,
            "name": row.name,
            "department": row.department,
            "year": row.year,
            "section": row.section,
            "month": row.month.isoformat(),
            "avgScore": row.avg_score,
            "attendancePct": row.attendance_pct,
        }
        for line, row in parsed.rows[:10]
    ]
    can_write = not dry_run and bool(parsed.rows) and (not parsed.issues or skip_invalid)
    students = len({row.student_code for _, row in parsed.rows})
    records = len(parsed.rows)
    if can_write:
        students, records, ids = _write_rows(session, (row for _, row in parsed.rows))
        audit_service.record(
            session,
            user.id if user else None,
            "import",
            "students",
            None,
            {"students": students, "records": records, "issues": len(parsed.issues)},
        )
        try:
            prediction_service.predict_students_if_model(session, ids)
        except Exception:  # the data is already saved; a scoring failure must not hide that
            logger.exception("scoring after import failed")
        dashboard_cache.clear()
    return ImportResult(
        dry_run=dry_run,
        imported=can_write,
        rows_read=parsed.rows_read,
        rows_valid=len(parsed.rows),
        students=students,
        records=records,
        issues=parsed.issues[:200],
        preview=preview,
        finished_at=utcnow() if can_write else None,
    )


# --------------------------------------------------------------------------- export


def _safe_cell(value: Any) -> Any:
    """Neutralise text that spreadsheet software would run as a formula."""
    if isinstance(value, str) and value and value[0] in "=+-@\t\r":
        return "'" + value
    return value


def export_csv(session: Session, user: User, filters: student_service.StudentFilters) -> tuple[str, int]:
    """CSV of the students matching `filters` that the user is allowed to see."""
    rows = student_service.export_rows(session, user, filters)
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(EXPORT_COLUMNS)
    for row in rows:
        writer.writerow([_safe_cell(row[column]) for column in EXPORT_COLUMNS])
    audit_service.record(session, user.id, "export", "students", None, {"rows": len(rows)})
    return buffer.getvalue(), len(rows)
