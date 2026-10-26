"""CSV import and export."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.ml.synthetic import CSV_COLUMNS

HEADER = ",".join(CSV_COLUMNS)
GOOD = "CS23-0001,Test Student,Computer Science,2,A,2026-08,70,90,80,1,0,4,g@example.invalid,0"


def upload(client: TestClient, headers, text: str, **params):  # type: ignore[no-untyped-def]
    query = "&".join(f"{k}={str(v).lower()}" for k, v in params.items())
    return client.post(
        f"/api/v1/data/import?{query}", headers=headers, files={"file": ("students.csv", text.encode(), "text/csv")}
    )


def test_dry_run_reports_without_writing(client: TestClient, people, admin_h) -> None:  # type: ignore[no-untyped-def]
    result = upload(client, admin_h, f"{HEADER}\n{GOOD}\n", dry_run=True).json()
    assert result["dryRun"] and not result["imported"] and result["rowsValid"] == 1
    assert client.get("/api/v1/students", headers=admin_h).json()["total"] == 0


def test_import_writes_students_classes_and_records(client: TestClient, people, admin_h) -> None:  # type: ignore[no-untyped-def]
    text = f"{HEADER}\n{GOOD}\n" + GOOD.replace("2026-08", "2026-09") + "\n"
    result = upload(client, admin_h, text, dry_run=False).json()
    assert result["imported"] and result["students"] == 1 and result["records"] == 2
    student = client.get("/api/v1/students", headers=admin_h).json()["items"][0]
    assert student["department"] == "Computer Science" and student["grade"] == 2


def test_per_row_errors_block_import_unless_skipping(client: TestClient, people, admin_h) -> None:  # type: ignore[no-untyped-def]
    bad = "CS23-0002,Bad Row,Computer Science,2,A,2026-08,170,90,80,1,0,4,,0"
    text = f"{HEADER}\n{GOOD}\n{bad}\n"
    blocked = upload(client, admin_h, text, dry_run=False).json()
    assert not blocked["imported"]
    assert blocked["issues"][0]["row"] == 3 and blocked["issues"][0]["column"] == "avg_score"
    partial = upload(client, admin_h, text, dry_run=False, skip_invalid=True).json()
    assert partial["imported"] and partial["students"] == 1 and len(partial["issues"]) == 1


def test_structural_problems_are_explained(client: TestClient, people, admin_h) -> None:  # type: ignore[no-untyped-def]
    missing = upload(client, admin_h, "student_code,name\nA1,B\n", dry_run=True).json()
    assert "Missing required column" in missing["issues"][0]["message"]
    duplicate = upload(client, admin_h, f"{HEADER}\n{GOOD}\n{GOOD}\n", dry_run=True).json()
    assert "Duplicate month" in duplicate["issues"][0]["message"]
    moved = GOOD.replace("Computer Science,2,A", "Biotechnology,2,A").replace("2026-08", "2026-09")
    conflict = upload(client, admin_h, f"{HEADER}\n{GOOD}\n{moved}\n", dry_run=True).json()
    assert "different class" in conflict["issues"][0]["message"]
    binary = client.post(
        "/api/v1/data/import", headers=admin_h, files={"file": ("x.csv", b"\xff\xfe\x00bad", "text/csv")}
    )
    assert binary.status_code == 400


def test_only_admins_import(client: TestClient, people, teacher_h) -> None:  # type: ignore[no-untyped-def]
    assert upload(client, teacher_h, f"{HEADER}\n{GOOD}\n", dry_run=True).status_code == 403


def test_export_respects_scope_and_neutralises_formulas(client: TestClient, populated, teacher_h, admin_h) -> None:  # type: ignore[no-untyped-def]
    mine = client.get("/api/v1/data/export", headers=teacher_h)
    assert mine.headers["content-type"].startswith("text/csv")
    lines = mine.text.strip().splitlines()
    everyone = client.get("/api/v1/data/export", headers=admin_h).text.strip().splitlines()
    assert 1 < len(lines) < len(everyone) == 151
    evil = f"{HEADER}\n" + GOOD.replace("Test Student", "=HYPERLINK(\"http://x\")").replace("CS23-0001", "EV-0001") + "\n"
    upload(client, admin_h, evil, dry_run=False)
    exported = client.get("/api/v1/data/export?q=EV-0001", headers=admin_h).text
    assert "'=HYPERLINK" in exported
