"""SHAP explanations on a trained bundle."""

from __future__ import annotations

import numpy as np

from app.ml.features import to_row


def test_shap_values_have_one_column_per_feature(trained_bundle) -> None:  # type: ignore[no-untyped-def]
    rows = [
        to_row({"attendance": 58, "score": 45, "assignments": 40, "failures": 3, "late": 8, "parent": 2, "trend": -3, "grade": 2}),
        to_row({"attendance": 96, "score": 85, "assignments": 95, "failures": 0, "late": 0, "parent": 5, "trend": 1, "grade": 3}),
    ]
    values = trained_bundle.shap_values(rows)
    assert values.shape == (2, 8)
    assert np.isfinite(values).all()
    assert values[0].sum() > values[1].sum()
