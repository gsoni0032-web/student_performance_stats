"""Command line tools: create the first admin, seed demo data, import a CSV, train a model.

Run from the backend directory, for example ``python -m app.cli seed``.
"""

from __future__ import annotations

import argparse
import getpass
import os
import secrets
import sys
from collections.abc import Sequence
from pathlib import Path

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_session_factory
from app.core.security import hash_password, validate_password_policy
from app.ml.pipeline import TrainingError
from app.ml.synthetic import generate_students, to_csv
from app.models import Class, TeacherClass, User
from app.models.enums import Role
from app.services import data_service, prediction_service, training_service

DEMO_ADMIN_EMAIL = "admin@pathway.example"
DEMO_TEACHERS = [
    ("Dr. Meera Kulkarni", "meera.kulkarni@pathway.example", "Computer Science"),
    ("Prof. Daniel Okoye", "daniel.okoye@pathway.example", "Mechanical Engineering"),
    ("Dr. Sara Lindgren", "sara.lindgren@pathway.example", "Business Administration"),
    ("Prof. Ravi Menon", "ravi.menon@pathway.example", "Biotechnology"),
]


def _password(provided: str | None, env_name: str, prompt: str) -> tuple[str, bool]:
    """Password from the flag, the environment or a prompt; returns (password, was_generated)."""
    value = provided or os.environ.get(env_name)
    if value:
        return validate_password_policy(value), False
    if sys.stdin.isatty():
        value = getpass.getpass(prompt)
        if value != getpass.getpass("Repeat password: "):
            raise SystemExit("The passwords did not match.")
        return validate_password_policy(value), False
    return f"Pw-{secrets.token_urlsafe(12)}9a", True


def _ensure_user(session: Session, name: str, email: str, role: Role, password: str) -> User:
    user = session.scalar(select(User).where(User.email == email.lower()))
    if user is None:
        user = User(name=name, email=email.lower(), password_hash=hash_password(password), role=role.value)
        session.add(user)
        session.flush()
    return user


def cmd_create_admin(args: argparse.Namespace) -> int:
    """Create an administrator account (or reset its password with --reset)."""
    password, generated = _password(args.password, "ADMIN_PASSWORD", "Admin password: ")
    with get_session_factory()() as session:
        existing = session.scalar(select(User).where(User.email == args.email.lower()))
        if existing is not None and not args.reset:
            print(f"{args.email} already exists. Use --reset to set a new password.")
            return 1
        if existing is not None:
            existing.password_hash = hash_password(password)
            existing.role = Role.ADMIN.value
            existing.is_active = True
        else:
            _ensure_user(session, args.name, args.email, Role.ADMIN, password)
        session.commit()
    print(f"Administrator ready: {args.email}")
    if generated:
        print(f"Generated password (shown once): {password}")
    return 0


def cmd_seed(args: argparse.Namespace) -> int:
    """Load synthetic students, demo accounts and (optionally) train the first model."""
    password, generated = _password(args.demo_password, "SEED_DEMO_PASSWORD", "Password for the demo accounts: ")
    students = generate_students(count=args.students, months=args.months, seed=args.seed)
    with get_session_factory()() as session:
        result = data_service.import_csv(session, None, to_csv(students).encode(), dry_run=False, skip_invalid=False)
        if result.issues:
            print(f"Seed data had problems: {result.issues[:3]}")
            return 1
        _ensure_user(session, "Pathway Administrator", DEMO_ADMIN_EMAIL, Role.ADMIN, password)
        classes = list(session.scalars(select(Class)))
        for name, email, department in DEMO_TEACHERS:
            teacher = _ensure_user(session, name, email, Role.TEACHER, password)
            for klass in classes:
                if klass.department == department:
                    link = session.get(TeacherClass, (teacher.id, klass.id))
                    if link is None:
                        session.add(TeacherClass(teacher_id=teacher.id, class_id=klass.id))
        session.commit()
        print(f"Loaded {result.students} students and {result.records} monthly records.")
        print(f"Demo accounts: {DEMO_ADMIN_EMAIL} and " + ", ".join(email for _, email, _ in DEMO_TEACHERS))
        if generated:
            print(f"Generated demo password (shown once): {password}")
        if not args.skip_train:
            return _train(session)
    return 0


def _train(session: Session) -> int:
    try:
        version = training_service.run_training(session, None)
    except TrainingError as error:
        print(f"Training stopped: {error}")
        return 1
    print(f"Trained and activated model version {version}.")
    return 0


def cmd_train(_: argparse.Namespace) -> int:
    """Train a model on the data in the database and activate it."""
    with get_session_factory()() as session:
        return _train(session)


def cmd_predict_all(_: argparse.Namespace) -> int:
    """Re-score every student with the active model."""
    with get_session_factory()() as session:
        result = prediction_service.predict_students(session)
    print(f"Scored {result.updated} students with model v{result.model_version} ({result.skipped} skipped).")
    return 0


def cmd_import_csv(args: argparse.Namespace) -> int:
    """Validate and import a CSV file, printing every problem with its row number."""
    content = Path(args.path).read_bytes()
    with get_session_factory()() as session:
        result = data_service.import_csv(session, None, content, dry_run=args.dry_run, skip_invalid=args.skip_invalid)
    for issue in result.issues:
        where = f" [{issue.column}]" if issue.column else ""
        print(f"row {issue.row}{where}: {issue.message}")
    verb = "Would import" if not result.imported else "Imported"
    print(f"{verb} {result.students} students / {result.records} records; {len(result.issues)} problem(s).")
    return 0 if not result.issues else 2


def build_parser() -> argparse.ArgumentParser:
    """The CLI argument parser."""
    parser = argparse.ArgumentParser(prog="python -m app.cli", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    admin = sub.add_parser("create-admin", help="create an administrator")
    admin.add_argument("--email", required=True)
    admin.add_argument("--name", default="Administrator")
    admin.add_argument("--password", help="or set ADMIN_PASSWORD, or you will be prompted")
    admin.add_argument("--reset", action="store_true", help="reset the password if the account exists")
    admin.set_defaults(func=cmd_create_admin)

    seed = sub.add_parser("seed", help="load synthetic demo data and train the first model")
    seed.add_argument("--students", type=int, default=600)
    seed.add_argument("--months", type=int, default=6)
    seed.add_argument("--seed", type=int, default=42)
    seed.add_argument("--demo-password", help="or set SEED_DEMO_PASSWORD")
    seed.add_argument("--skip-train", action="store_true")
    seed.set_defaults(func=cmd_seed)

    train = sub.add_parser("train", help="train and activate a model")
    train.set_defaults(func=cmd_train)

    predict = sub.add_parser("predict-all", help="re-score every student")
    predict.set_defaults(func=cmd_predict_all)

    importer = sub.add_parser("import-csv", help="import students from a CSV file")
    importer.add_argument("path")
    importer.add_argument("--dry-run", action="store_true")
    importer.add_argument("--skip-invalid", action="store_true")
    importer.set_defaults(func=cmd_import_csv)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point."""
    args = build_parser().parse_args(argv)
    get_settings()
    try:
        return int(args.func(args))
    except ValidationError as error:
        print(error)
        return 1
    except ValueError as error:
        print(error)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
