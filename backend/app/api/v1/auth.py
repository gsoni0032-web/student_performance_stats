"""Authentication endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Request, Response

from app.api.deps import CurrentUser, DbSession, client_key
from app.core.config import get_settings
from app.core.rate_limit import RateLimiter
from app.schemas.auth import ChangePasswordRequest, LoginRequest, RefreshRequest, TokenPair
from app.schemas.user import UserOut
from app.services import auth_service, user_service

router = APIRouter(prefix="/auth", tags=["auth"])

_settings = get_settings()
login_limiter = RateLimiter(_settings.login_rate_limit, _settings.login_rate_window_seconds)


@router.post("/login", response_model=TokenPair)
def login(payload: LoginRequest, request: Request, session: DbSession) -> TokenPair:
    """Exchange email and password for an access token and a refresh token."""
    login_limiter.check(client_key(request))
    user = auth_service.authenticate(session, payload.email, payload.password)
    return auth_service.issue_tokens(session, user)


@router.post("/refresh", response_model=TokenPair)
def refresh(payload: RefreshRequest, session: DbSession) -> TokenPair:
    """Rotate the refresh token; the old one stops working immediately."""
    return auth_service.refresh(session, payload.refresh_token)


@router.post("/logout", status_code=204)
def logout(payload: RefreshRequest, session: DbSession) -> Response:
    """Sign out by revoking the refresh token chain."""
    auth_service.logout(session, payload.refresh_token)
    return Response(status_code=204)


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser, session: DbSession) -> UserOut:
    """The signed-in user."""
    return user_service.to_out(session, user)


@router.post("/change-password", status_code=204)
def change_password(payload: ChangePasswordRequest, user: CurrentUser, session: DbSession) -> Response:
    """Change your own password; all other sessions are signed out."""
    auth_service.change_password(session, user, payload.current_password, payload.new_password)
    return Response(status_code=204)
