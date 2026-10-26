"""Training pipeline for the dropout classifier and the next-term score regressor.

Steps: build frames -> clean -> stratified train/validation/test split -> tune three model
families with cross-validated search -> pick the best on the validation set -> calibrate the
winner on the validation set -> report honest metrics on the untouched test set.

Class imbalance is handled with class weights (balanced weights for logistic regression and
random forest, `scale_pos_weight` for XGBoost). Dropout is the positive class and recall on it
is prioritised: a missed student costs far more than an extra check-in conversation, so the
flagging threshold is deliberately low and both recall and precision are reported at it.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
import sklearn
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import RandomForestClassifier
from sklearn.frozen import FrozenEstimator
from sklearn.linear_model import LogisticRegression, RidgeCV
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    confusion_matrix,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    precision_recall_curve,
    precision_score,
    r2_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import RandomizedSearchCV, StratifiedKFold, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from app.ml.features import (
    FEATURE_NAMES,
    FEATURE_RANGES,
    MIN_MONTHS_FOR_REGRESSION,
    MonthPoint,
    compute_features,
)

logger = logging.getLogger("pathway.ml")

CANDIDATES: tuple[str, ...] = ("logreg", "random_forest", "xgboost")
TARGET = "dropped_out"
REGRESSION_TARGET = "next_score"
MIN_LABELLED_ROWS = 60
MIN_PER_CLASS = 12
MIN_REGRESSION_ROWS = 60
TARGET_RECALL = 0.85


class TrainingError(Exception):
    """Training cannot proceed; the message is safe to show to an administrator."""


@dataclass(frozen=True)
class StudentSeries:
    """What the pipeline needs from one student."""

    grade: int
    points: Sequence[MonthPoint]
    dropped_out: bool | None


class ModelBundle:
    """Everything needed to score and explain: calibrated classifier, regressor, metadata."""

    def __init__(
        self,
        model_type: str,
        calibrated: Any,
        explain_model: Any,
        explain_scaler: Any | None,
        background: np.ndarray,
        regressor: Any | None,
        metrics: dict[str, Any],
    ) -> None:
        self.model_type = model_type
        self.calibrated = calibrated
        self.explain_model = explain_model
        self.explain_scaler = explain_scaler
        self.background = background
        self.regressor = regressor
        self.metrics = metrics
        self.version = 0
        self._explainer: Any | None = None

    def __getstate__(self) -> dict[str, Any]:
        """Pickle without the cached SHAP explainer; it is rebuilt on demand."""
        state = self.__dict__.copy()
        state["_explainer"] = None
        return state

    @staticmethod
    def frame(rows: Sequence[Sequence[float]] | np.ndarray) -> pd.DataFrame:
        """Wrap raw rows in a DataFrame with the training column names."""
        return pd.DataFrame(np.asarray(rows, dtype=float), columns=FEATURE_NAMES)

    def predict_proba(self, rows: Sequence[Sequence[float]] | np.ndarray) -> np.ndarray:
        """Calibrated dropout probability for each row."""
        return np.asarray(self.calibrated.predict_proba(self.frame(rows))[:, 1], dtype=float)

    def predict_next_score(self, rows: Sequence[Sequence[float]] | np.ndarray) -> np.ndarray | None:
        """Predicted next-term average score (0-100), or None when no regressor was trained."""
        if self.regressor is None:
            return None
        return np.clip(np.asarray(self.regressor.predict(self.frame(rows)), dtype=float), 0, 100)

    def shap_values(self, rows: Sequence[Sequence[float]] | np.ndarray) -> np.ndarray:
        """SHAP contributions per feature; positive values push the dropout risk up."""
        import shap  # imported lazily: it is slow to import and only needed for explanations

        data = self.frame(rows)
        if self._explainer is None:
            if self.model_type == "logreg":
                background = self.explain_scaler.transform(self.frame(self.background))
                self._explainer = shap.LinearExplainer(self.explain_model, background)
            else:
                self._explainer = shap.TreeExplainer(self.explain_model)
        matrix = self.explain_scaler.transform(data) if self.model_type == "logreg" else data
        values = self._explainer.shap_values(matrix)
        if isinstance(values, list):
            values = values[1]
        values = np.asarray(values, dtype=float)
        if values.ndim == 3:
            values = values[:, :, 1]
        return values


# --------------------------------------------------------------------------- data frames


def build_frames(series: Sequence[StudentSeries]) -> tuple[pd.DataFrame, pd.DataFrame | None]:
    """Create the classification frame (labelled students) and the regression frame.

    Classification rows use features from all months. Regression rows use features from every
    month except the last and take the last month's score as the target, so no extra label column
    is required.
    """
    clf_rows: list[dict[str, float]] = []
    reg_rows: list[dict[str, float]] = []
    for student in series:
        features = compute_features(student.points, student.grade)
        if features is not None and student.dropped_out is not None:
            clf_rows.append({**features, TARGET: float(student.dropped_out)})
        if len(student.points) >= MIN_MONTHS_FOR_REGRESSION:
            earlier = compute_features(student.points[:-1], student.grade)
            if earlier is not None:
                reg_rows.append({**earlier, REGRESSION_TARGET: student.points[-1].avg_score})
    clf = pd.DataFrame(clf_rows, columns=[*FEATURE_NAMES, TARGET])
    reg = pd.DataFrame(reg_rows, columns=[*FEATURE_NAMES, REGRESSION_TARGET])
    return clean_frame(clf), (clean_frame(reg) if len(reg) >= MIN_REGRESSION_ROWS else None)


def clean_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """Fill gaps with column medians and clip every feature into its valid range."""
    cleaned = frame.copy()
    for name in FEATURE_NAMES:
        cleaned[name] = pd.to_numeric(cleaned[name], errors="coerce")
        median = cleaned[name].median()
        cleaned[name] = cleaned[name].fillna(0.0 if pd.isna(median) else median)
        low, high = FEATURE_RANGES[name]
        cleaned[name] = cleaned[name].clip(low, high)
    return cleaned.reset_index(drop=True)


# --------------------------------------------------------------------------- candidates


def _grid_size(grid: dict[str, list[Any]]) -> int:
    return int(np.prod([len(v) for v in grid.values()]))


def candidate_spec(name: str, positive_weight: float, seed: int) -> tuple[Any, dict[str, list[Any]]]:
    """Return an untrained estimator and its hyper-parameter search space."""
    if name == "logreg":
        estimator = Pipeline(
            [
                ("scale", StandardScaler()),
                ("clf", LogisticRegression(max_iter=3000, class_weight="balanced")),
            ]
        )
        return estimator, {"clf__C": [0.01, 0.03, 0.1, 0.3, 1.0, 3.0, 10.0]}
    if name == "random_forest":
        estimator = RandomForestClassifier(
            class_weight="balanced_subsample", random_state=seed, n_jobs=1
        )
        return estimator, {
            "n_estimators": [100, 200],
            "max_depth": [3, 4, 6, 8],
            "min_samples_leaf": [3, 5, 10],
            "max_features": ["sqrt", 0.6],
        }
    if name == "xgboost":
        from xgboost import XGBClassifier  # imported lazily so the other models work without it

        estimator = XGBClassifier(
            eval_metric="logloss",
            scale_pos_weight=positive_weight,
            tree_method="hist",
            random_state=seed,
            n_jobs=1,
        )
        return estimator, {
            "n_estimators": [100, 200, 300],
            "max_depth": [2, 3, 4],
            "learning_rate": [0.03, 0.05, 0.1],
            "subsample": [0.8, 1.0],
            "colsample_bytree": [0.8, 1.0],
            "min_child_weight": [1, 3, 5],
        }
    raise TrainingError(f"Unknown model type: {name}")


# --------------------------------------------------------------------------- metrics


def classification_metrics(y_true: np.ndarray, proba: np.ndarray, threshold: float) -> dict[str, Any]:
    """Threshold-dependent and threshold-free metrics for the dropout class."""
    predicted = (proba >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, predicted, labels=[0, 1]).ravel()
    return {
        "threshold": round(float(threshold), 4),
        "accuracy": round(float(accuracy_score(y_true, predicted)), 4),
        "precision": round(float(precision_score(y_true, predicted, zero_division=0)), 4),
        "recall": round(float(recall_score(y_true, predicted, zero_division=0)), 4),
        "f1": round(float(f1_score(y_true, predicted, zero_division=0)), 4),
        "roc_auc": round(float(roc_auc_score(y_true, proba)), 4),
        "pr_auc": round(float(average_precision_score(y_true, proba)), 4),
        "confusion_matrix": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
    }


def recommended_threshold(y_true: np.ndarray, proba: np.ndarray, target_recall: float) -> float:
    """Highest threshold that still catches `target_recall` of dropouts on the given data."""
    _, recalls, thresholds = precision_recall_curve(y_true, proba)
    eligible = [t for r, t in zip(recalls[:-1], thresholds, strict=True) if r >= target_recall]
    return float(max(eligible)) if eligible else float(thresholds.min())


# --------------------------------------------------------------------------- training


def train(
    clf_frame: pd.DataFrame,
    reg_frame: pd.DataFrame | None,
    flag_threshold: float = 0.3,
    high_threshold: float = 0.6,
    candidates: Sequence[str] = CANDIDATES,
    search_iterations: int = 12,
    seed: int = 42,
) -> ModelBundle:
    """Train, compare, calibrate and evaluate. Raises `TrainingError` on unusable data."""
    if len(clf_frame) < MIN_LABELLED_ROWS:
        raise TrainingError(
            f"Need at least {MIN_LABELLED_ROWS} students with a known outcome; found {len(clf_frame)}."
        )
    counts = clf_frame[TARGET].value_counts()
    if counts.get(1.0, 0) < MIN_PER_CLASS or counts.get(0.0, 0) < MIN_PER_CLASS:
        raise TrainingError(
            f"Need at least {MIN_PER_CLASS} dropouts and {MIN_PER_CLASS} non-dropouts; "
            f"found {int(counts.get(1.0, 0))} and {int(counts.get(0.0, 0))}."
        )

    features = clf_frame[FEATURE_NAMES]
    target = clf_frame[TARGET].astype(int)
    x_rest, x_test, y_rest, y_test = train_test_split(
        features, target, test_size=0.2, stratify=target, random_state=seed
    )
    x_train, x_val, y_train, y_val = train_test_split(
        x_rest, y_rest, test_size=0.25, stratify=y_rest, random_state=seed
    )
    positive_weight = float((y_train == 0).sum() / max((y_train == 1).sum(), 1))
    cv = StratifiedKFold(n_splits=3, shuffle=True, random_state=seed)

    reports: dict[str, Any] = {}
    fitted: dict[str, Any] = {}
    for name in candidates:
        estimator, grid = candidate_spec(name, positive_weight, seed)
        search = RandomizedSearchCV(
            estimator,
            grid,
            n_iter=min(search_iterations, _grid_size(grid)),
            scoring="average_precision",
            cv=cv,
            random_state=seed,
            n_jobs=1,
            refit=True,
        )
        search.fit(x_train, y_train)
        val_proba = search.best_estimator_.predict_proba(x_val)[:, 1]
        reports[name] = {
            "best_params": {k: _plain(v) for k, v in search.best_params_.items()},
            "cv_pr_auc": round(float(search.best_score_), 4),
            "val_pr_auc": round(float(average_precision_score(y_val, val_proba)), 4),
            "val_roc_auc": round(float(roc_auc_score(y_val, val_proba)), 4),
            "val_recall_at_flag": round(
                float(recall_score(y_val, val_proba >= flag_threshold, zero_division=0)), 4
            ),
        }
        fitted[name] = search.best_estimator_
        logger.info("candidate %s: %s", name, reports[name])

    winner = max(reports, key=lambda n: (reports[n]["val_pr_auc"], reports[n]["val_roc_auc"]))
    best = fitted[winner]
    calibrated = CalibratedClassifierCV(FrozenEstimator(best), method="sigmoid")
    calibrated.fit(x_val, y_val)

    test_proba = calibrated.predict_proba(x_test)[:, 1]
    val_proba = calibrated.predict_proba(x_val)[:, 1]
    metrics: dict[str, Any] = {
        "model_type": winner,
        "sklearn_version": sklearn.__version__,
        "samples": {
            "labelled": int(len(clf_frame)),
            "train": int(len(x_train)),
            "validation": int(len(x_val)),
            "test": int(len(x_test)),
            "dropout_rate": round(float(target.mean()), 4),
        },
        "candidates": reports,
        "features": FEATURE_NAMES,
        "test_at_flag_threshold": classification_metrics(y_test.to_numpy(), test_proba, flag_threshold),
        "test_at_high_threshold": classification_metrics(y_test.to_numpy(), test_proba, high_threshold),
        "recommended_flag_threshold": round(
            recommended_threshold(y_val.to_numpy(), val_proba, TARGET_RECALL), 4
        ),
        "target_recall": TARGET_RECALL,
        "recall_note": (
            "Dropout is the positive class and recall on it is prioritised: missing a student "
            "who needs help is costlier than an unnecessary check-in."
        ),
    }

    regressor, regression_metrics = _train_regressor(reg_frame, seed)
    metrics["regression"] = regression_metrics

    if winner == "logreg":
        explain_model, explain_scaler = best.named_steps["clf"], best.named_steps["scale"]
    else:
        explain_model, explain_scaler = best, None
    background = x_train.sample(n=min(100, len(x_train)), random_state=seed).to_numpy(dtype=float)
    return ModelBundle(winner, calibrated, explain_model, explain_scaler, background, regressor, metrics)


def _train_regressor(
    frame: pd.DataFrame | None, seed: int
) -> tuple[Pipeline | None, dict[str, Any] | None]:
    """Fit the next-term score regressor and report its error against a naive baseline.

    A ridge regression is used on purpose: next month's score is mostly "current level plus
    trend", a relationship a linear model extrapolates well and tree models flatten.
    """
    if frame is None:
        return None, None
    x_train, x_test, y_train, y_test = train_test_split(
        frame[FEATURE_NAMES], frame[REGRESSION_TARGET], test_size=0.2, random_state=seed
    )
    model = Pipeline(
        [("scale", StandardScaler()), ("ridge", RidgeCV(alphas=[0.1, 1.0, 10.0, 100.0]))]
    )
    model.fit(x_train, y_train)
    predicted = np.clip(model.predict(x_test), 0, 100)
    baseline = x_test["score"].to_numpy()
    return model, {
        "samples": int(len(frame)),
        "mae": round(float(mean_absolute_error(y_test, predicted)), 3),
        "rmse": round(float(np.sqrt(mean_squared_error(y_test, predicted))), 3),
        "r2": round(float(r2_score(y_test, predicted)), 3),
        "baseline_mae": round(float(mean_absolute_error(y_test, baseline)), 3),
        "baseline": "carry the current rolling average score forward",
    }


def _plain(value: Any) -> Any:
    """Convert numpy scalars into JSON-friendly Python values."""
    return value.item() if isinstance(value, np.generic) else value
