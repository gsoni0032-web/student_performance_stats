"""Risk thresholds stored in the settings table."""

from __future__ import annotations

from sqlalchemy import case, update
from sqlalchemy.orm import Session

from app.core.cache import dashboard_cache
from app.core.timeutil import utcnow
from app.models import Prediction, Setting
from app.models.enums import RiskLevel
from app.schemas.prediction import Thresholds

THRESHOLD_KEY = "risk_thresholds"


def get_thresholds(session: Session) -> Thresholds:
    """Current thresholds, falling back to the defaults (medium 0.3, high 0.6)."""
    row = session.get(Setting, THRESHOLD_KEY)
    return Thresholds(**row.value) if row else Thresholds()


def risk_level_for(probability: float, thresholds: Thresholds) -> str:
    """Map a probability to a risk band."""
    if probability >= thresholds.high:
        return RiskLevel.HIGH.value
    if probability >= thresholds.medium:
        return RiskLevel.MEDIUM.value
    return RiskLevel.LOW.value


def set_thresholds(session: Session, thresholds: Thresholds) -> Thresholds:
    """Save new thresholds and relabel every stored prediction so lists and charts agree."""
    value = {"medium": thresholds.medium, "high": thresholds.high}
    row = session.get(Setting, THRESHOLD_KEY)
    if row is None:
        session.add(Setting(key=THRESHOLD_KEY, value=value))
    else:
        row.value = value
        row.updated_at = utcnow()
    session.execute(
        update(Prediction).values(
            risk_level=case(
                (Prediction.probability >= thresholds.high, RiskLevel.HIGH.value),
                (Prediction.probability >= thresholds.medium, RiskLevel.MEDIUM.value),
                else_=RiskLevel.LOW.value,
            )
        )
    )
    session.commit()
    dashboard_cache.clear()
    return thresholds
