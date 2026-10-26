"""The Alembic migration must produce exactly the schema the ORM models describe."""

from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, inspect

import app.models  # noqa: F401
from app.core.database import Base

BACKEND = Path(__file__).resolve().parents[1]


def test_migration_matches_models(tmp_path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    url = f"sqlite:///{tmp_path / 'migrated.db'}"
    monkeypatch.setenv("DATABASE_URL", url)
    from app.core import config

    config.get_settings.cache_clear()
    engine = create_engine(url)
    cfg = Config(str(BACKEND / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND / "alembic"))
    cfg.attributes["engine"] = engine
    command.upgrade(cfg, "head")
    assert {"users", "students", "monthly_records", "predictions", "model_versions", "audit_log"} <= set(
        inspect(engine).get_table_names()
    )
    with engine.connect() as connection:
        diff = compare_metadata(MigrationContext.configure(connection), Base.metadata)
    config.get_settings.cache_clear()
    assert diff == [], diff
    command.downgrade(cfg, "base")
    assert inspect(engine).get_table_names() == ["alembic_version"]
