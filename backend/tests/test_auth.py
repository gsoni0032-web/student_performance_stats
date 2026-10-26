"""Login, lockout, refresh rotation, logout and password change."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.api.v1.auth import login_limiter
from tests.conftest import PASSWORD, sign_in


def login(client: TestClient, email: str, password: str):  # type: ignore[no-untyped-def]
    return client.post("/api/v1/auth/login", json={"email": email, "password": password})


def test_login_and_me(client: TestClient, people) -> None:  # type: ignore[no-untyped-def]
    response = login(client, "ADMIN@test.example", PASSWORD)
    assert response.status_code == 200
    token = response.json()["accessToken"]
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["role"] == "admin"


def test_wrong_password_and_unknown_user_look_the_same(client: TestClient, people) -> None:  # type: ignore[no-untyped-def]
    wrong = login(client, "admin@test.example", "nope")
    unknown = login(client, "ghost@test.example", "nope")
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json()["error"]["message"] == unknown.json()["error"]["message"]


def test_protected_routes_require_a_token(client: TestClient) -> None:
    assert client.get("/api/v1/students").status_code == 401
    bad = client.get("/api/v1/students", headers={"Authorization": "Bearer not-a-token"})
    assert bad.status_code == 401
    assert bad.json()["error"]["code"] == "token_invalid"


def test_lockout_after_repeated_failures(client: TestClient, people) -> None:  # type: ignore[no-untyped-def]
    for _ in range(5):
        assert login(client, "teacher@test.example", "bad").status_code == 401
    locked = login(client, "teacher@test.example", PASSWORD)
    assert locked.status_code == 423
    assert locked.json()["error"]["code"] == "account_locked"


def test_disabled_account_cannot_sign_in(client: TestClient, people, db) -> None:  # type: ignore[no-untyped-def]
    people["viewer"].is_active = False
    db.commit()
    assert login(client, "viewer@test.example", PASSWORD).status_code == 403


def test_refresh_rotates_and_reuse_revokes_the_chain(client: TestClient, people) -> None:  # type: ignore[no-untyped-def]
    first = login(client, "admin@test.example", PASSWORD).json()
    second = client.post("/api/v1/auth/refresh", json={"refreshToken": first["refreshToken"]})
    assert second.status_code == 200
    reuse = client.post("/api/v1/auth/refresh", json={"refreshToken": first["refreshToken"]})
    assert reuse.status_code == 401
    after = client.post("/api/v1/auth/refresh", json={"refreshToken": second.json()["refreshToken"]})
    assert after.status_code == 401


def test_logout_revokes_refresh_token(client: TestClient, people) -> None:  # type: ignore[no-untyped-def]
    tokens = login(client, "admin@test.example", PASSWORD).json()
    assert client.post("/api/v1/auth/logout", json={"refreshToken": tokens["refreshToken"]}).status_code == 204
    again = client.post("/api/v1/auth/refresh", json={"refreshToken": tokens["refreshToken"]})
    assert again.status_code == 401


def test_change_password(client: TestClient, people) -> None:  # type: ignore[no-untyped-def]
    headers = sign_in(client, "teacher@test.example")
    wrong = client.post(
        "/api/v1/auth/change-password",
        headers=headers,
        json={"currentPassword": "bad", "newPassword": "Another-Pass-456"},
    )
    assert wrong.status_code == 400
    weak = client.post(
        "/api/v1/auth/change-password",
        headers=headers,
        json={"currentPassword": PASSWORD, "newPassword": "short"},
    )
    assert weak.status_code == 422
    ok = client.post(
        "/api/v1/auth/change-password",
        headers=headers,
        json={"currentPassword": PASSWORD, "newPassword": "Another-Pass-456"},
    )
    assert ok.status_code == 204
    assert login(client, "teacher@test.example", "Another-Pass-456").status_code == 200


def test_login_is_rate_limited(client: TestClient, people) -> None:  # type: ignore[no-untyped-def]
    login_limiter.limit = 3
    try:
        codes = [login(client, "ghost@test.example", "x").status_code for _ in range(5)]
    finally:
        login_limiter.limit = 1000
    assert codes[-1] == 429


def test_health_and_security_headers(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-request-id"]
    assert client.get("/api/v1/health").json()["status"] == "ok"


def test_error_envelope_for_validation_and_missing_routes(client: TestClient) -> None:
    invalid = client.post("/api/v1/auth/login", json={"email": "not-an-email"})
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "validation_error"
    missing = client.get("/api/v1/nothing-here")
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "not_found"
