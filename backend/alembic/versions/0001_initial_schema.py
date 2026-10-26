"""Initial schema: users, classes, students, monthly records, predictions, models, audit.

Revision ID: 0001
Revises:
Create Date: 2026-10-24
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create every table, index and constraint."""
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("email", sa.String(254), nullable=False),
        sa.Column("password_hash", sa.String(100), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("failed_login_count", sa.Integer(), nullable=False),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)
    op.create_index(op.f("ix_users_role"), "users", ["role"])

    op.create_table(
        "classes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("department", sa.String(80), nullable=False),
        sa.Column("grade", sa.Integer(), nullable=False),
        sa.Column("section", sa.String(10), nullable=False),
        sa.Column("academic_year", sa.String(9), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_classes")),
        sa.UniqueConstraint(
            "department", "grade", "section", "academic_year", name=op.f("uq_classes_cohort")
        ),
        sa.CheckConstraint("grade BETWEEN 1 AND 6", name=op.f("ck_classes_grade_range")),
    )

    op.create_table(
        "teacher_classes",
        sa.Column("teacher_id", sa.Integer(), nullable=False),
        sa.Column("class_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["teacher_id"], ["users.id"], name=op.f("fk_teacher_classes_teacher_id_users"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["class_id"], ["classes.id"], name=op.f("fk_teacher_classes_class_id_classes"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("teacher_id", "class_id", name=op.f("pk_teacher_classes")),
    )
    op.create_index(op.f("ix_teacher_classes_class_id"), "teacher_classes", ["class_id"])

    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("family_id", sa.String(32), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_refresh_tokens_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_refresh_tokens")),
        sa.UniqueConstraint("token_hash", name=op.f("uq_refresh_tokens_token_hash")),
    )
    op.create_index(op.f("ix_refresh_tokens_user_id"), "refresh_tokens", ["user_id"])
    op.create_index(op.f("ix_refresh_tokens_family_id"), "refresh_tokens", ["family_id"])

    op.create_table(
        "students",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("student_code", sa.String(30), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("class_id", sa.Integer(), nullable=False),
        sa.Column("guardian_contact", sa.String(120), nullable=True),
        sa.Column("dropped_out", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["class_id"], ["classes.id"], name=op.f("fk_students_class_id_classes"), ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_students")),
    )
    op.create_index(op.f("ix_students_student_code"), "students", ["student_code"], unique=True)
    op.create_index(op.f("ix_students_name"), "students", ["name"])
    op.create_index(op.f("ix_students_class_id"), "students", ["class_id"])

    op.create_table(
        "monthly_records",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("month", sa.Date(), nullable=False),
        sa.Column("avg_score", sa.Float(), nullable=False),
        sa.Column("attendance_pct", sa.Float(), nullable=False),
        sa.Column("assignments_pct", sa.Float(), nullable=False),
        sa.Column("late_arrivals", sa.Integer(), nullable=False),
        sa.Column("failed_subjects", sa.Integer(), nullable=False),
        sa.Column("guardian_engagement", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["student_id"], ["students.id"], name=op.f("fk_monthly_records_student_id_students"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_monthly_records")),
        sa.UniqueConstraint("student_id", "month", name=op.f("uq_monthly_records_student_month")),
        sa.CheckConstraint("avg_score BETWEEN 0 AND 100", name=op.f("ck_monthly_records_score_range")),
        sa.CheckConstraint("attendance_pct BETWEEN 0 AND 100", name=op.f("ck_monthly_records_attendance_range")),
        sa.CheckConstraint("assignments_pct BETWEEN 0 AND 100", name=op.f("ck_monthly_records_assignments_range")),
        sa.CheckConstraint("guardian_engagement BETWEEN 1 AND 5", name=op.f("ck_monthly_records_engagement_range")),
        sa.CheckConstraint("late_arrivals >= 0", name=op.f("ck_monthly_records_late_non_negative")),
        sa.CheckConstraint("failed_subjects >= 0", name=op.f("ck_monthly_records_failed_non_negative")),
    )
    op.create_index(op.f("ix_monthly_records_student_id"), "monthly_records", ["student_id"])

    op.create_table(
        "interventions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["student_id"], ["students.id"], name=op.f("fk_interventions_student_id_students"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"], ["users.id"], name=op.f("fk_interventions_updated_by_users"), ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_interventions")),
        sa.UniqueConstraint("student_id", name=op.f("uq_interventions_student_id")),
    )

    op.create_table(
        "predictions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("model_version", sa.Integer(), nullable=False),
        sa.Column("probability", sa.Float(), nullable=False),
        sa.Column("risk_level", sa.String(10), nullable=False),
        sa.Column("next_term_score", sa.Float(), nullable=True),
        sa.Column("top_factors", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["student_id"], ["students.id"], name=op.f("fk_predictions_student_id_students"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_predictions")),
    )
    op.create_index("ix_predictions_student_latest", "predictions", ["student_id", "id"])
    op.create_index("ix_predictions_risk_level", "predictions", ["risk_level"])

    op.create_table(
        "model_versions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("model_type", sa.String(30), nullable=False),
        sa.Column("metrics", sa.JSON(), nullable=False),
        sa.Column("trained_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("file_path", sa.String(300), nullable=False),
        sa.Column("artifact", sa.LargeBinary(), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_model_versions")),
        sa.UniqueConstraint("version", name=op.f("uq_model_versions_version")),
    )
    op.create_index(op.f("ix_model_versions_is_active"), "model_versions", ["is_active"])

    op.create_table(
        "settings",
        sa.Column("key", sa.String(60), nullable=False),
        sa.Column("value", sa.JSON(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("key", name=op.f("pk_settings")),
    )

    op.create_table(
        "audit_log",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("action", sa.String(40), nullable=False),
        sa.Column("entity", sa.String(40), nullable=False),
        sa.Column("entity_id", sa.String(60), nullable=True),
        sa.Column("detail", sa.JSON(), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_audit_log_user_id_users"), ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_audit_log")),
    )
    op.create_index(op.f("ix_audit_log_user_id"), "audit_log", ["user_id"])
    op.create_index("ix_audit_log_timestamp", "audit_log", ["timestamp"])


def downgrade() -> None:
    """Drop everything in reverse dependency order."""
    for table in (
        "audit_log",
        "settings",
        "model_versions",
        "predictions",
        "interventions",
        "monthly_records",
        "students",
        "refresh_tokens",
        "teacher_classes",
        "classes",
        "users",
    ):
        op.drop_table(table)
