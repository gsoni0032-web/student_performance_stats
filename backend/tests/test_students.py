"""Students: listing, scoping by role, adding students, records and follow-up."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.models import AuditLog, Class


def first_class_id(db, department: str = "Computer Science") -> int:  # type: ignore[no-untyped-def]
    return db.scalars(select(Class.id).where(Class.department == department)).first()


def new_student(class_id: int, code: str = "NEW-0001", **extra):  # type: ignore[no-untyped-def]
    body = {"studentCode": code, "name": "  Priya   Sharma ", "classId": class_id}
    body.update(extra)
    return body


def test_list_is_paginated_searchable_and_sortable(client: TestClient, populated, admin_h) -> None:  # type: ignore[no-untyped-def]
    page = client.get("/api/v1/students?page_size=10&sort=name&order=asc", headers=admin_h).json()
    assert page["total"] == 150 and len(page["items"]) == 10 and page["pages"] == 15
    names = [s["name"] for s in page["items"]]
    assert names == sorted(names)
    code = page["items"][0]["studentCode"]
    found = client.get(f"/api/v1/students?q={code}", headers=admin_h).json()
    assert found["total"] == 1
    cs = client.get("/api/v1/students?department=Computer%20Science&page_size=100", headers=admin_h).json()
    assert cs["total"] > 0 and all(s["department"] == "Computer Science" for s in cs["items"])


def test_teacher_only_sees_their_own_classes(client: TestClient, populated, teacher_h, admin_h) -> None:  # type: ignore[no-untyped-def]
    mine = client.get("/api/v1/students?page_size=100", headers=teacher_h).json()
    assert 0 < mine["total"] < 150
    assert {s["department"] for s in mine["items"]} == {"Computer Science"}
    other = client.get("/api/v1/students?department=Biotechnology", headers=admin_h).json()["items"][0]
    assert client.get(f"/api/v1/students/{other['id']}", headers=teacher_h).status_code == 404


def test_student_shape_matches_the_contract(client: TestClient, with_model, admin_h) -> None:  # type: ignore[no-untyped-def]
    summary = client.get("/api/v1/students?page_size=1", headers=admin_h).json()["items"][0]
    detail = client.get(f"/api/v1/students/{summary['id']}", headers=admin_h).json()
    for key in ("id", "name", "grade", "section", "scoreSeries", "attSeries", "features", "prob", "factors"):
        assert key in detail
    assert set(detail["features"]) == {"attendance", "score", "assignments", "failures", "late", "parent", "trend"}
    assert len(detail["scoreSeries"]) == len(detail["attSeries"]) == 6
    assert detail["factors"] and set(detail["factors"][0]) == {"key", "label", "display", "impact", "driver"}


def test_admin_adds_a_student_with_first_record(client: TestClient, populated, admin_h, db) -> None:  # type: ignore[no-untyped-def]
    class_id = first_class_id(db)
    record = {
        "month": "2026-09-01", "avgScore": 71.5, "attendancePct": 88, "assignmentsPct": 76,
        "lateArrivals": 2, "failedSubjects": 0, "guardianEngagement": 4,
    }
    created = client.post("/api/v1/students", headers=admin_h, json=new_student(class_id, record=record))
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["name"] == "Priya Sharma"
    assert body["features"]["score"] == 71.5
    assert client.get("/api/v1/students?q=NEW-0001", headers=admin_h).json()["total"] == 1
    assert db.scalar(select(AuditLog.id).where(AuditLog.action == "student_create")) is not None


def test_teacher_can_add_only_to_their_own_class(client: TestClient, populated, teacher_h, db) -> None:  # type: ignore[no-untyped-def]
    own = client.post("/api/v1/students", headers=teacher_h, json=new_student(first_class_id(db)))
    assert own.status_code == 201
    foreign = client.post(
        "/api/v1/students", headers=teacher_h, json=new_student(first_class_id(db, "Biotechnology"), "NEW-0002")
    )
    assert foreign.status_code == 403


def test_add_student_validation(client: TestClient, populated, admin_h, db) -> None:  # type: ignore[no-untyped-def]
    class_id = first_class_id(db)
    assert client.post("/api/v1/students", headers=admin_h, json=new_student(class_id)).status_code == 201
    duplicate = client.post("/api/v1/students", headers=admin_h, json=new_student(class_id))
    assert duplicate.status_code == 409
    bad_code = client.post("/api/v1/students", headers=admin_h, json=new_student(class_id, "has space"))
    assert bad_code.status_code == 422
    missing_class = client.post("/api/v1/students", headers=admin_h, json=new_student(99999, "NEW-0003"))
    assert missing_class.status_code == 404


def test_viewer_cannot_write_and_does_not_see_guardian_contact(client: TestClient, populated, viewer_h, db) -> None:  # type: ignore[no-untyped-def]
    assert client.post("/api/v1/students", headers=viewer_h, json=new_student(first_class_id(db))).status_code == 403
    student = client.get("/api/v1/students?page_size=1", headers=viewer_h).json()["items"][0]
    assert client.get(f"/api/v1/students/{student['id']}", headers=viewer_h).json()["guardianContact"] is None
    assert client.put(
        f"/api/v1/students/{student['id']}/intervention",
        headers=viewer_h,
        json={"status": "resolved", "notes": ""},
    ).status_code == 403


def test_update_and_delete_rules(client: TestClient, populated, admin_h, teacher_h) -> None:  # type: ignore[no-untyped-def]
    mine = client.get("/api/v1/students?page_size=1", headers=teacher_h).json()["items"][0]["id"]
    renamed = client.put(f"/api/v1/students/{mine}", headers=teacher_h, json={"name": "Renamed Person"})
    assert renamed.status_code == 200 and renamed.json()["name"] == "Renamed Person"
    outcome = client.put(f"/api/v1/students/{mine}", headers=teacher_h, json={"droppedOut": True})
    assert outcome.status_code == 403
    assert client.delete(f"/api/v1/students/{mine}", headers=teacher_h).status_code == 403
    assert client.delete(f"/api/v1/students/{mine}", headers=admin_h).status_code == 204
    assert client.get(f"/api/v1/students/{mine}", headers=admin_h).status_code == 404


def test_follow_up_status_and_notes_are_audited(client: TestClient, populated, teacher_h, db) -> None:  # type: ignore[no-untyped-def]
    sid = client.get("/api/v1/students?page_size=1", headers=teacher_h).json()["items"][0]["id"]
    saved = client.put(
        f"/api/v1/students/{sid}/intervention",
        headers=teacher_h,
        json={"status": "guardian_contacted", "notes": "Called on Monday.\nWill review in two weeks."},
    )
    assert saved.status_code == 200 and saved.json()["updatedBy"] == "Tess Teacher"
    assert client.get(f"/api/v1/students/{sid}/intervention", headers=teacher_h).json()["status"] == "guardian_contacted"
    assert client.put(
        f"/api/v1/students/{sid}/intervention", headers=teacher_h, json={"status": "bogus", "notes": ""}
    ).status_code == 422
    assert db.scalar(select(AuditLog.id).where(AuditLog.action == "status_change")) is not None
    by_status = client.get("/api/v1/students?status=guardian_contacted", headers=teacher_h).json()
    assert by_status["total"] == 1


def test_monthly_record_upsert_replaces_the_month(client: TestClient, populated, admin_h) -> None:  # type: ignore[no-untyped-def]
    item = client.get("/api/v1/students?page_size=1", headers=admin_h).json()["items"][0]
    detail = client.get(f"/api/v1/students/{item['id']}", headers=admin_h).json()
    month = detail["months"][-1] + "-01"
    payload = {
        "month": month, "avgScore": 40, "attendancePct": 50, "assignmentsPct": 30,
        "lateArrivals": 9, "failedSubjects": 3, "guardianEngagement": 1,
    }
    updated = client.post(f"/api/v1/students/{item['id']}/records", headers=admin_h, json=payload).json()
    assert len(updated["scoreSeries"]) == len(detail["scoreSeries"])
    assert updated["scoreSeries"][-1] == 40
    out_of_range = {**payload, "avgScore": 140}
    assert client.post(f"/api/v1/students/{item['id']}/records", headers=admin_h, json=out_of_range).status_code == 422
