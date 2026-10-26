"""Synthetic college cohort generator.

Everything here is invented. Names come from two short word lists and are combined at random;
no real person is represented. Outcomes are drawn from a latent "struggle" score that the
monthly numbers only partly reveal, so the model has real signal but cannot be perfect.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

import numpy as np

DEPARTMENTS: list[tuple[str, str]] = [
    ("Computer Science", "CS"),
    ("Mechanical Engineering", "ME"),
    ("Business Administration", "BA"),
    ("Biotechnology", "BT"),
]
SECTIONS = ["A", "B"]
YEARS = [1, 2, 3, 4]

_FIRST = [
    "Aarav", "Maya", "Noah", "Leila", "Kofi", "Sofia", "Ethan", "Priya", "Lucas", "Amara",
    "Daniel", "Hana", "Mateo", "Zara", "Oliver", "Isha", "Samuel", "Nina", "Omar", "Elena",
    "Rohan", "Grace", "Tariq", "Mei", "Julian", "Anika", "Felix", "Yara", "Arjun", "Clara",
    "Diego", "Salma", "Kevin", "Tara", "Victor", "Ines", "Nathan", "Riya", "Hugo", "Lina",
]
_LAST = [
    "Anderson", "Banerjee", "Castillo", "Dubois", "Eriksen", "Fernandes", "Gupta", "Hoffmann",
    "Ibrahim", "Jensen", "Kapoor", "Lindqvist", "Mensah", "Nakamura", "Okafor", "Petrov",
    "Quinn", "Rahman", "Sato", "Thompson", "Uddin", "Varga", "Walker", "Xu", "Yilmaz",
    "Zhang", "Bose", "Costa", "Das", "Evans", "Ferreira", "Garcia", "Haddad", "Iyer", "Joshi",
    "Khan", "Lopez", "Mehta", "Nair", "Ortiz",
]


@dataclass
class SyntheticMonth:
    """One generated month of data."""

    month: date
    avg_score: float
    attendance_pct: float
    assignments_pct: float
    late_arrivals: int
    failed_subjects: int
    guardian_engagement: int


@dataclass
class SyntheticStudent:
    """One generated student with a known outcome."""

    code: str
    name: str
    department: str
    grade: int
    section: str
    guardian_contact: str
    dropped_out: bool
    months: list[SyntheticMonth] = field(default_factory=list)


def month_starts(end: date, count: int) -> list[date]:
    """The first day of `count` consecutive months ending with the month of `end`."""
    months: list[date] = []
    year, month = end.year, end.month
    for _ in range(count):
        months.append(date(year, month, 1))
        month -= 1
        if month == 0:
            month, year = 12, year - 1
    return list(reversed(months))


def _sigmoid(x: float) -> float:
    return float(1.0 / (1.0 + np.exp(-x)))


def generate_students(
    count: int = 600, months: int = 6, end_month: date | None = None, seed: int = 42
) -> list[SyntheticStudent]:
    """Generate `count` students across four years of study with `months` of monthly data."""
    rng = np.random.default_rng(seed)
    end = end_month or date.today().replace(day=1)
    month_list = month_starts(end, months)
    seen_names: set[str] = set()
    students: list[SyntheticStudent] = []
    sequence: dict[str, int] = {}

    for _ in range(count):
        department, prefix = DEPARTMENTS[int(rng.integers(len(DEPARTMENTS)))]
        grade = int(rng.choice(YEARS, p=[0.32, 0.27, 0.23, 0.18]))
        section = SECTIONS[int(rng.integers(len(SECTIONS)))]

        name = ""
        while not name or name in seen_names:
            name = f"{_FIRST[int(rng.integers(len(_FIRST)))]} {_LAST[int(rng.integers(len(_LAST)))]}"
            if len(seen_names) > len(_FIRST) * len(_LAST) - 10:
                name = f"{name} {len(seen_names)}"
        seen_names.add(name)

        admission_year = end.year - grade
        key = f"{prefix}{admission_year % 100:02d}"
        sequence[key] = sequence.get(key, 0) + 1
        code = f"{key}-{sequence[key]:04d}"

        engagement = rng.normal()
        ability = rng.normal()
        struggle = -0.85 * engagement - 0.75 * ability + rng.normal(scale=0.55)
        declining = bool(struggle > 0.2 and rng.random() < 0.65)
        drift = rng.normal(-1.1 if declining else 0.15, 0.5)

        base_attendance = float(np.clip(86 + 7 * engagement + rng.normal(0, 3), 35, 99))
        base_score = float(np.clip(67 + 9 * ability + 3 * engagement + rng.normal(0, 3), 22, 97))
        base_assign = float(np.clip(80 + 9 * engagement + 4 * ability + rng.normal(0, 4), 15, 100))
        parent_level = float(np.clip(3.2 + 0.7 * engagement + rng.normal(0, 0.5), 1, 5))
        failed_level = max(0.0, (58 - base_score) / 9 + rng.normal(0, 0.6))

        student = SyntheticStudent(
            code=code,
            name=name,
            department=department,
            grade=grade,
            section=section,
            guardian_contact=f"guardian.{code.lower().replace('-', '')}@example.invalid",
            dropped_out=bool(rng.random() < _sigmoid(-2.05 + 1.9 * struggle + (0.5 if declining else 0))),
        )
        for index, month in enumerate(month_list):
            score = float(np.clip(base_score + drift * index + rng.normal(0, 2.2), 0, 100))
            attendance = float(
                np.clip(base_attendance + (drift * 0.9 * index if declining else 0) + rng.normal(0, 2.5), 0, 100)
            )
            assignments = float(np.clip(base_assign + drift * 0.8 * index + rng.normal(0, 4), 0, 100))
            student.months.append(
                SyntheticMonth(
                    month=month,
                    avg_score=round(score, 1),
                    attendance_pct=round(attendance, 1),
                    assignments_pct=round(assignments, 1),
                    late_arrivals=int(np.clip(rng.poisson(max(0.2, (100 - attendance) / 7)), 0, 25)),
                    failed_subjects=int(np.clip(round(failed_level + (0.4 if declining else 0) + rng.normal(0, 0.4)), 0, 8)),
                    guardian_engagement=int(np.clip(round(parent_level + rng.normal(0, 0.4)), 1, 5)),
                )
            )
        students.append(student)
    return students


CSV_COLUMNS = [
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
    "guardian_contact",
    "dropped_out",
]


def to_csv(students: list[SyntheticStudent]) -> str:
    """Render generated students in the import format (one row per student per month)."""
    import csv
    import io

    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(CSV_COLUMNS)
    for student in students:
        for entry in student.months:
            writer.writerow(
                [
                    student.code,
                    student.name,
                    student.department,
                    student.grade,
                    student.section,
                    entry.month.strftime("%Y-%m"),
                    entry.avg_score,
                    entry.attendance_pct,
                    entry.assignments_pct,
                    entry.late_arrivals,
                    entry.failed_subjects,
                    entry.guardian_engagement,
                    student.guardian_contact,
                    int(student.dropped_out),
                ]
            )
    return buffer.getvalue()
