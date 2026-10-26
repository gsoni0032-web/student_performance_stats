"""Write synthetic sample data: the import CSV, and an audit-groups file for the fairness check.

Everything is invented. Usage:  python ml/generate_sample_data.py [--students 600]
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np

from common import BACKEND  # noqa: F401  (puts the backend on sys.path)
from app.ml.synthetic import generate_students, to_csv  # noqa: E402

OUT = Path(__file__).parent / "sample_data"


def main() -> None:
    """Generate `students_sample.csv` and `audit_groups_sample.csv`."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--students", type=int, default=600)
    parser.add_argument("--months", type=int, default=6)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    students = generate_students(count=args.students, months=args.months, seed=args.seed)
    OUT.mkdir(exist_ok=True)
    (OUT / "students_sample.csv").write_text(to_csv(students))

    rng = np.random.default_rng(args.seed)
    lines = ["student_code,audit_group"]
    for student in students:
        lines.append(f"{student.code},{'group_' + 'AB'[int(rng.integers(2))]}")
    (OUT / "audit_groups_sample.csv").write_text("\n".join(lines) + "\n")
    print(f"Wrote {len(students)} students to {OUT}")


if __name__ == "__main__":
    main()
