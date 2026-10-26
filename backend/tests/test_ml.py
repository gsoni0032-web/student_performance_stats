"""ML pipeline: features, training metrics, calibration, explanations and fairness of inputs."""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd
import pytest

from app.ml.explain import build_factors, suggest_actions
from app.ml.features import FEATURE_NAMES, MonthPoint, clip_features, compute_features, to_row
from app.ml.pipeline import TrainingError, build_frames, clean_frame, train
from app.ml.synthetic import generate_students, month_starts
from tests.helpers import series_from

SENSITIVE = {"gender", "sex", "religion", "caste", "ethnicity", "race", "name", "guardian_contact"}


def test_features_never_include_sensitive_attributes() -> None:
    assert not SENSITIVE & set(FEATURE_NAMES)


def test_compute_features_uses_rolling_window_and_trend() -> None:
    points = [MonthPoint(60 + i * 2, 90 - i, 80, 1, 0, 4) for i in range(6)]
    features = compute_features(points, grade=3)
    assert features is not None
    assert features["grade"] == 3 and features["failures"] == 0
    assert features["trend"] == pytest.approx(2.0)
    assert features["score"] == pytest.approx(np.mean([p.avg_score for p in points[-3:]]))
    assert compute_features([], 1) is None
    assert len(to_row(clip_features(features))) == len(FEATURE_NAMES)


def test_clean_frame_fills_and_clips() -> None:
    frame = pd.DataFrame([{**dict.fromkeys(FEATURE_NAMES, 50.0), "attendance": 150.0}, {**dict.fromkeys(FEATURE_NAMES, np.nan)}])
    cleaned = clean_frame(frame)
    assert cleaned["attendance"].max() <= 100 and not cleaned.isna().any().any()


def test_synthetic_data_is_anonymous_and_complete() -> None:
    students = generate_students(count=520, months=6, seed=1)
    assert len(students) == 520 and len({s.code for s in students}) == 520
    assert {s.grade for s in students} == {1, 2, 3, 4}
    assert all(len(s.months) == 6 and s.guardian_contact.endswith("@example.invalid") for s in students)
    assert month_starts(date(2026, 2, 10), 3)[0].month == 12


def test_training_reports_required_metrics(trained_bundle) -> None:  # type: ignore[no-untyped-def]
    metrics = trained_bundle.metrics
    flagged = metrics["test_at_flag_threshold"]
    for key in ("accuracy", "precision", "recall", "f1", "roc_auc", "pr_auc"):
        assert 0 <= flagged[key] <= 1
    assert set(flagged["confusion_matrix"]) == {"tn", "fp", "fn", "tp"}
    assert flagged["roc_auc"] > 0.7 and flagged["recall"] > 0.5
    assert set(metrics["candidates"]) == {"logreg", "random_forest"}
    assert "recall" in metrics["recall_note"]
    assert metrics["regression"]["mae"] <= metrics["regression"]["baseline_mae"] + 1.0


def test_probabilities_are_calibrated_and_ordered(trained_bundle) -> None:  # type: ignore[no-untyped-def]
    weak = to_row({"attendance": 55, "score": 40, "assignments": 35, "failures": 4, "late": 9, "parent": 1.5, "trend": -4, "grade": 2})
    strong = to_row({"attendance": 98, "score": 90, "assignments": 97, "failures": 0, "late": 0, "parent": 5, "trend": 2, "grade": 2})
    probabilities = trained_bundle.predict_proba([weak, strong])
    assert probabilities[0] > 0.5 > probabilities[1]
    scores = trained_bundle.predict_next_score([weak, strong])
    assert scores is not None and scores[0] < scores[1]


def test_training_rejects_unusable_data() -> None:
    small, _ = build_frames(series_from(generate_students(count=30, seed=2)))
    with pytest.raises(TrainingError, match="at least"):
        train(small, None, candidates=["logreg"])
    enough, _ = build_frames(series_from(generate_students(count=300, seed=2)))
    with pytest.raises(TrainingError, match="dropouts"):
        train(enough.assign(dropped_out=0.0), None, candidates=["logreg"])


def test_unknown_candidate_is_rejected() -> None:
    clf, _ = build_frames(series_from(generate_students(count=300, seed=2)))
    with pytest.raises(TrainingError):
        train(clf, None, candidates=["telepathy"], search_iterations=1)


def test_factor_labels_show_direction_and_value() -> None:
    features = {"attendance": 61, "score": 72, "assignments": 80, "failures": 0, "late": 1.0, "parent": 4, "trend": -2.5, "grade": 2}
    shap_row = np.array([0.9, -0.2, 0.1, -0.3, 0.05, -0.1, 0.4, 0.0])
    factors = build_factors(features, shap_row)
    assert factors[0] == {"key": "attendance", "label": "Low attendance", "display": "61%", "impact": factors[0]["impact"], "driver": "raises"}
    assert any(f["driver"] == "lowers" for f in factors)
    assert sum(f["impact"] for f in build_factors(features, shap_row, top_n=8)) == pytest.approx(100, abs=0.5)
    assert build_factors(features, np.zeros(8)) == []
    assert suggest_actions(factors, "high")[-1].startswith("Schedule")
    assert "routine monitoring" in suggest_actions([], "low")[0]
