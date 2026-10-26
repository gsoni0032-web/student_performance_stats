"""What-if scoring, batch recompute, retraining, rollback and the dashboard."""

from __future__ import annotations

import time

from fastapi.testclient import TestClient

from app.ml import registry

WHAT_IF = {"attendance": 62, "score": 48, "assignments": 40, "failures": 3, "late": 8, "parent": 2, "trend": -3.5, "grade": 2}
STRONG = {"attendance": 97, "score": 88, "assignments": 96, "failures": 0, "late": 0, "parent": 5, "trend": 1.5, "grade": 2}


def test_what_if_needs_a_model(client: TestClient, populated, admin_h) -> None:  # type: ignore[no-untyped-def]
    response = client.post("/api/v1/predict", headers=admin_h, json=WHAT_IF)
    assert response.status_code == 503 and response.json()["error"]["code"] == "no_model"


def test_what_if_orders_risk_sensibly(client: TestClient, with_model, teacher_h) -> None:  # type: ignore[no-untyped-def]
    weak = client.post("/api/v1/predict", headers=teacher_h, json=WHAT_IF).json()
    strong = client.post("/api/v1/predict", headers=teacher_h, json=STRONG).json()
    assert weak["prob"] > strong["prob"]
    assert weak["factors"][0]["driver"] == "raises"
    assert weak["suggestedActions"] and weak["modelVersion"] == 1
    assert 0 <= weak["nextTermScore"] <= 100


def test_what_if_validates_ranges(client: TestClient, with_model, admin_h) -> None:  # type: ignore[no-untyped-def]
    assert client.post("/api/v1/predict", headers=admin_h, json={**WHAT_IF, "attendance": 140}).status_code == 422
    assert client.post("/api/v1/predict", headers=admin_h, json={"attendance": 50}).status_code == 422


def test_batch_and_single_recompute(client: TestClient, with_model, admin_h, teacher_h) -> None:  # type: ignore[no-untyped-def]
    batch = client.post("/api/v1/predictions/batch", headers=admin_h).json()
    assert batch["updated"] == 150 and batch["skipped"] == 0
    sid = client.get("/api/v1/students?page_size=1", headers=teacher_h).json()["items"][0]["id"]
    again = client.post(f"/api/v1/students/{sid}/predict", headers=teacher_h)
    assert again.status_code == 200 and again.json()["prob"] is not None


def test_dashboard_endpoints(client: TestClient, with_model, admin_h, teacher_h) -> None:  # type: ignore[no-untyped-def]
    summary = client.get("/api/v1/dashboard/summary", headers=admin_h).json()
    assert summary["studentsTracked"] == 150
    assert summary["highRisk"] + summary["mediumRisk"] + summary["lowRisk"] + summary["unscored"] == 150
    mine = client.get("/api/v1/dashboard/summary", headers=teacher_h).json()
    assert 0 < mine["studentsTracked"] < 150
    by_grade = client.get("/api/v1/dashboard/risk-by-grade", headers=admin_h).json()
    assert [g["grade"] for g in by_grade] == sorted(g["grade"] for g in by_grade)
    drivers = client.get("/api/v1/dashboard/drivers?limit=3", headers=admin_h).json()
    assert 0 < len(drivers) <= 3 and {"key", "label", "students", "share"} <= set(drivers[0])
    watch = client.get("/api/v1/dashboard/watchlist?limit=5", headers=admin_h).json()
    assert len(watch) == 5 and watch == sorted(watch, key=lambda w: -w["prob"])
    cohort = client.get("/api/v1/dashboard/cohort", headers=admin_h).json()
    assert len(cohort) == 150 and cohort[0]["prob"] >= cohort[-1]["prob"]


def test_dashboard_with_no_data(client: TestClient, people, admin_h) -> None:  # type: ignore[no-untyped-def]
    summary = client.get("/api/v1/dashboard/summary", headers=admin_h).json()
    assert summary["studentsTracked"] == 0 and summary["avgScore"] is None
    assert client.get("/api/v1/dashboard/watchlist", headers=admin_h).json() == []


def test_retrain_in_background_then_rollback(client: TestClient, with_model, admin_h) -> None:  # type: ignore[no-untyped-def]
    started = client.post("/api/v1/model/retrain", headers=admin_h)
    assert started.status_code == 202
    for _ in range(300):
        info = client.get("/api/v1/model/info", headers=admin_h).json()
        if info["training"]["status"] in ("succeeded", "failed"):
            break
        time.sleep(0.5)
    assert info["training"]["status"] == "succeeded", info["training"]
    assert info["active"]["version"] == 2 and len(info["versions"]) == 2
    assert {"accuracy", "precision", "recall", "f1", "roc_auc", "pr_auc", "confusion_matrix"} <= set(
        info["active"]["metrics"]["test_at_flag_threshold"]
    )
    rolled = client.post("/api/v1/model/activate/1", headers=admin_h).json()
    assert rolled["active"]["version"] == 1
    assert client.post("/api/v1/model/activate/99", headers=admin_h).status_code == 404


def test_model_restores_from_database_copy(client: TestClient, with_model, admin_h, db) -> None:  # type: ignore[no-untyped-def]
    from pathlib import Path

    record = registry.active_version(db)
    Path(record.file_path).unlink()
    registry.clear_cache()
    assert client.post("/api/v1/predict", headers=admin_h, json=WHAT_IF).status_code == 200


def test_training_refuses_tiny_datasets(client: TestClient, people, admin_h, db) -> None:  # type: ignore[no-untyped-def]
    from app.ml.pipeline import TrainingError
    from app.services import training_service

    try:
        training_service.run_training(db, people["admin"].id)
    except TrainingError as error:
        assert "at least" in str(error)
    else:  # pragma: no cover
        raise AssertionError("expected TrainingError")
