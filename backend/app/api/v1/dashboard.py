"""Dashboard aggregates for the overview page."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import CurrentUser, DbSession
from app.schemas.prediction import CohortPoint, Driver, GradeRisk, Summary, WatchlistItem
from app.services import dashboard_service

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=Summary)
def summary(user: CurrentUser, session: DbSession) -> Summary:
    """Counts, averages and the change since the previous month."""
    return dashboard_service.summary(session, user)


@router.get("/risk-by-grade", response_model=list[GradeRisk])
def risk_by_grade(user: CurrentUser, session: DbSession) -> list[GradeRisk]:
    """Risk bands for each year of study."""
    return dashboard_service.risk_by_grade(session, user)


@router.get("/drivers", response_model=list[Driver])
def drivers(
    user: CurrentUser, session: DbSession, limit: Annotated[int, Query(ge=1, le=10)] = 6
) -> list[Driver]:
    """The factors that most often raise risk across the cohort."""
    return dashboard_service.drivers(session, user, limit)


@router.get("/watchlist", response_model=list[WatchlistItem])
def watchlist(
    user: CurrentUser, session: DbSession, limit: Annotated[int, Query(ge=1, le=50)] = 10
) -> list[WatchlistItem]:
    """Students who need attention first."""
    return dashboard_service.watchlist(session, user, limit)


@router.get("/cohort", response_model=list[CohortPoint])
def cohort(
    user: CurrentUser, session: DbSession, limit: Annotated[int, Query(ge=1, le=2000)] = 1000
) -> list[CohortPoint]:
    """One compact point per student, riskiest first (register and scatter chart)."""
    return dashboard_service.cohort_points(session, user, limit)
