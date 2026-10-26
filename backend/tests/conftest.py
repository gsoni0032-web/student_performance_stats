"""Shared fixtures. Environment variables are set before the app is imported."""

from __future__ import annotations

import copy
import os
import tempfile
from collections.abc import Iterator
from pathlib import Path

_TMP = Path(tempfile.mkdtemp(prefix="pathway-tests-"))
os.environ.update(
    APP_ENV="test",
    SECRET_KEY="test-secret-key-that-is-long-enough-0123456789",
    DATABASE_URL=f"sqlite:///{_TMP / 'test.db'}",
    MODEL_DIR=str(_TMP / "models"),
    ML_CANDIDATES="logreg,random_forest",
    TRAINING_SEARCH_ITERATIONS="2",
    LOG_JSON="false",
    LOG_LEVEL="WARNING",
    DASHBOARD_CACHE_SECONDS="0",
    LOGIN_RATE_LIMIT="1000",
)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

import app.models  # noqa: E402,F401
from app.api.v1.auth import login_limiter  # noqa: E402
from app.core.cache import dashboard_cache  # noqa: E402
from app.core.database import Base, get_engine, get_session_factory  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.main import app  # noqa: E402
from app.ml import registry  # noqa: E402
from app.ml.pipeline import ModelBundle, build_frames, train  # noqa: E402
from app.ml.synthetic import generate_students, to_csv  # noqa: E402
from app.models import Class, TeacherClass, User  # noqa: E402
from app.services import data_service, prediction_service, training_service  # noqa: E402
from tests.helpers import series_from  # noqa: E402

PASSWORD = "Sturdy-Pass-123"


@pytest.fixture(scope="session")
def trained_bundle() -> ModelBundle:
    """One model trained on synthetic data without touching the database (reused by many tests)."""
    clf, reg = build_frames(series_from(generate_students(count=500, seed=7)))
    return train(clf, reg, candidates=["logreg", "random_forest"], search_iterations=2)


@pytest.fixture(autouse=True)
def fresh_database() -> Iterator[None]:
    """A clean schema and clean in-process state for every test."""
    engine = get_engine()
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    dashboard_cache.clear()
    registry.clear_cache()
    login_limiter.reset()
    training_service.reset()
    yield


@pytest.fixture
def db() -> Iterator[Session]:
    """A database session."""
    with get_session_factory()() as session:
        yield session


@pytest.fixture
def client() -> Iterator[TestClient]:
    """HTTP client for the app."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def people(db: Session) -> dict[str, User]:
    """An admin, a teacher, a viewer and a second teacher."""
    users = {
        "admin": User(name="Ada Admin", email="admin@test.example", role="admin"),
        "teacher": User(name="Tess Teacher", email="teacher@test.example", role="teacher"),
        "other": User(name="Omar Other", email="other@test.example", role="teacher"),
        "viewer": User(name="Vera Viewer", email="viewer@test.example", role="viewer"),
    }
    for user in users.values():
        user.password_hash = hash_password(PASSWORD)
        db.add(user)
    db.commit()
    return users


@pytest.fixture
def populated(db: Session, people: dict[str, User]) -> dict[str, User]:
    """150 synthetic students; `teacher` owns the Computer Science classes, `other` the rest."""
    csv_text = to_csv(generate_students(count=150, seed=3))
    result = data_service.import_csv(db, people["admin"], csv_text.encode(), dry_run=False, skip_invalid=False)
    assert not result.issues
    for klass in db.query(Class).all():
        owner = people["teacher"] if klass.department == "Computer Science" else people["other"]
        db.add(TeacherClass(teacher_id=owner.id, class_id=klass.id))
    db.commit()
    return people


@pytest.fixture
def with_model(db: Session, populated: dict[str, User], trained_bundle: ModelBundle) -> ModelBundle:
    """Register the shared trained model and score everybody."""
    bundle = copy.deepcopy(trained_bundle)
    registry.save_bundle(db, bundle)
    prediction_service.predict_students(db)
    return bundle


def sign_in(client: TestClient, email: str, password: str = PASSWORD) -> dict[str, str]:
    """Log in and return the Authorization header."""
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['accessToken']}"}


@pytest.fixture
def admin_h(client: TestClient, people: dict[str, User]) -> dict[str, str]:
    """Admin auth header."""
    return sign_in(client, "admin@test.example")


@pytest.fixture
def teacher_h(client: TestClient, people: dict[str, User]) -> dict[str, str]:
    """Teacher auth header."""
    return sign_in(client, "teacher@test.example")


@pytest.fixture
def viewer_h(client: TestClient, people: dict[str, User]) -> dict[str, str]:
    """Viewer auth header."""
    return sign_in(client, "viewer@test.example")
