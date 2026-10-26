"""Users, classes, thresholds and the audit log."""

from __future__ import annotations

from fastapi.testclient import TestClient

from tests.conftest import PASSWORD, sign_in


def test_admin_only_routes_reject_others(client: TestClient, populated, teacher_h, viewer_h) -> None:  # type: ignore[no-untyped-def]
    for headers in (teacher_h, viewer_h):
        assert client.get("/api/v1/users", headers=headers).status_code == 403
        assert client.get("/api/v1/audit", headers=headers).status_code == 403
        assert client.post("/api/v1/model/retrain", headers=headers).status_code == 403
        assert client.post("/api/v1/predictions/batch", headers=headers).status_code == 403
        assert client.put("/api/v1/settings/thresholds", headers=headers, json={"medium": 0.2, "high": 0.5}).status_code == 403
        assert client.post("/api/v1/classes", headers=headers, json={}).status_code == 403


def test_user_lifecycle(client: TestClient, populated, admin_h) -> None:  # type: ignore[no-untyped-def]
    class_id = client.get("/api/v1/classes", headers=admin_h).json()["items"][0]["id"]
    payload = {
        "name": "New Teacher", "email": "New.Teacher@test.example", "password": PASSWORD,
        "role": "teacher", "classIds": [class_id],
    }
    created = client.post("/api/v1/users", headers=admin_h, json=payload)
    assert created.status_code == 201 and created.json()["classIds"] == [class_id]
    assert client.post("/api/v1/users", headers=admin_h, json=payload).status_code == 409
    weak = client.post("/api/v1/users", headers=admin_h, json={**payload, "email": "x@test.example", "password": "weak"})
    assert weak.status_code == 422
    uid = created.json()["id"]
    assert sign_in(client, "new.teacher@test.example")
    updated = client.put(f"/api/v1/users/{uid}", headers=admin_h, json={"isActive": False, "classIds": []})
    assert updated.json()["isActive"] is False
    assert client.post("/api/v1/auth/login", json={"email": "new.teacher@test.example", "password": PASSWORD}).status_code == 403
    assert client.get("/api/v1/users?q=new.teacher", headers=admin_h).json()["total"] == 1
    assert client.delete(f"/api/v1/users/{uid}", headers=admin_h).status_code == 204
    assert client.put("/api/v1/users/9999", headers=admin_h, json={"name": "Nobody"}).status_code == 404


def test_last_admin_and_self_protection(client: TestClient, people, admin_h) -> None:  # type: ignore[no-untyped-def]
    admin_id = people["admin"].id
    assert client.put(f"/api/v1/users/{admin_id}", headers=admin_h, json={"role": "teacher"}).status_code == 409
    assert client.put(f"/api/v1/users/{admin_id}", headers=admin_h, json={"isActive": False}).status_code == 409
    assert client.delete(f"/api/v1/users/{admin_id}", headers=admin_h).status_code == 409


def test_unknown_class_assignment_is_rejected(client: TestClient, people, admin_h) -> None:  # type: ignore[no-untyped-def]
    response = client.post(
        "/api/v1/users", headers=admin_h,
        json={"name": "T", "email": "t@test.example", "password": PASSWORD, "role": "teacher", "classIds": [999]},
    )
    assert response.status_code == 400


def test_class_lifecycle(client: TestClient, people, admin_h) -> None:  # type: ignore[no-untyped-def]
    body = {"department": "Physics", "grade": 2, "section": "A", "academicYear": "2026-27"}
    created = client.post("/api/v1/classes", headers=admin_h, json=body)
    assert created.status_code == 201 and created.json()["label"] == "Physics · Year 2 · A"
    assert client.post("/api/v1/classes", headers=admin_h, json=body).status_code == 409
    cid = created.json()["id"]
    assert client.put(f"/api/v1/classes/{cid}", headers=admin_h, json={**body, "section": "B"}).json()["section"] == "B"
    assert client.post("/api/v1/classes", headers=admin_h, json={**body, "grade": 9}).status_code == 422
    assert client.delete(f"/api/v1/classes/{cid}", headers=admin_h).status_code == 204
    assert client.delete(f"/api/v1/classes/{cid}", headers=admin_h).status_code == 404


def test_class_with_students_cannot_be_deleted(client: TestClient, populated, admin_h) -> None:  # type: ignore[no-untyped-def]
    cid = client.get("/api/v1/classes", headers=admin_h).json()["items"][0]["id"]
    assert client.delete(f"/api/v1/classes/{cid}", headers=admin_h).status_code == 409


def test_teacher_sees_only_own_classes(client: TestClient, populated, teacher_h, admin_h) -> None:  # type: ignore[no-untyped-def]
    mine = client.get("/api/v1/classes", headers=teacher_h).json()
    everything = client.get("/api/v1/classes", headers=admin_h).json()
    assert 0 < mine["total"] < everything["total"]


def test_thresholds_relabel_predictions(client: TestClient, with_model, admin_h) -> None:  # type: ignore[no-untyped-def]
    before = client.get("/api/v1/dashboard/summary", headers=admin_h).json()
    assert client.put("/api/v1/settings/thresholds", headers=admin_h, json={"medium": 0.8, "high": 0.4}).status_code == 422
    saved = client.put("/api/v1/settings/thresholds", headers=admin_h, json={"medium": 0.05, "high": 0.2})
    assert saved.status_code == 200
    after = client.get("/api/v1/dashboard/summary", headers=admin_h).json()
    assert after["highRisk"] >= before["highRisk"]
    assert client.get("/api/v1/settings/thresholds", headers=admin_h).json()["high"] == 0.2


def test_audit_log_records_sensitive_actions(client: TestClient, populated, admin_h) -> None:  # type: ignore[no-untyped-def]
    client.get("/api/v1/data/export", headers=admin_h)
    entries = client.get("/api/v1/audit?action=export", headers=admin_h).json()
    assert entries["total"] == 1 and entries["items"][0]["entity"] == "students"
    logins = client.get("/api/v1/audit?action=login", headers=admin_h).json()
    assert logins["total"] >= 1
