"""Login, lockout, refresh-token rotation and password changes."""

from __future__ import annotations

from datetime import timedelta

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError, unauthorized
from app.core.security import (
    create_access_token,
    hash_password,
    hash_refresh_token,
    new_refresh_token,
    verify_password,
)
from app.core.timeutil import as_utc, utcnow
from app.models import RefreshToken, User
from app.schemas.auth import TokenPair
from app.services import audit_service

INVALID_CREDENTIALS = "Incorrect email or password"


def authenticate(session: Session, email: str, password: str) -> User:
    """Check credentials, enforce lockout and return the user, or raise a clear error."""
    settings = get_settings()
    user = session.scalar(select(User).where(User.email == email.lower()))
    now = utcnow()

    if user and user.locked_until and as_utc(user.locked_until) > now:
        minutes = max(1, int((as_utc(user.locked_until) - now).total_seconds() // 60) + 1)
        raise AppError(
            423,
            "account_locked",
            f"Too many failed attempts. Try again in about {minutes} minute(s).",
        )

    if not verify_password(password, user.password_hash if user else None):
        if user:
            user.failed_login_count += 1
            if user.failed_login_count >= settings.max_failed_logins:
                user.locked_until = now + timedelta(minutes=settings.lockout_minutes)
                user.failed_login_count = 0
            session.commit()
        audit_service.record(session, user.id if user else None, "login_failed", "user", user.id if user else None)
        raise unauthorized(INVALID_CREDENTIALS, code="invalid_credentials")

    if not user or not user.is_active:
        raise AppError(403, "account_disabled", "This account has been disabled. Please contact an administrator.")

    user.failed_login_count = 0
    user.locked_until = None
    session.commit()
    audit_service.record(session, user.id, "login", "user", user.id)
    return user


def issue_tokens(session: Session, user: User, family_id: str | None = None) -> TokenPair:
    """Create an access token and a fresh single-use refresh token."""
    settings = get_settings()
    refresh = new_refresh_token()
    session.add(
        RefreshToken(
            user_id=user.id,
            family_id=family_id or new_refresh_token()[:32],
            token_hash=hash_refresh_token(refresh),
            expires_at=utcnow() + timedelta(days=settings.refresh_token_days),
        )
    )
    session.commit()
    access, expires_in = create_access_token(user.id, user.role)
    return TokenPair(access_token=access, refresh_token=refresh, expires_in=expires_in)


def _revoke_family(session: Session, family_id: str) -> None:
    session.execute(
        update(RefreshToken)
        .where(RefreshToken.family_id == family_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=utcnow())
    )
    session.commit()


def refresh(session: Session, token: str) -> TokenPair:
    """Rotate a refresh token. Reusing an already-rotated token revokes the whole login chain."""
    stored = session.scalar(select(RefreshToken).where(RefreshToken.token_hash == hash_refresh_token(token)))
    if stored is None:
        raise unauthorized("Your session is no longer valid. Please sign in again.", code="invalid_refresh")
    if stored.revoked_at is not None:
        _revoke_family(session, stored.family_id)
        audit_service.record(session, stored.user_id, "refresh_reuse", "user", stored.user_id)
        raise unauthorized("Your session is no longer valid. Please sign in again.", code="invalid_refresh")
    if as_utc(stored.expires_at) <= utcnow():
        raise unauthorized("Your session has expired. Please sign in again.", code="invalid_refresh")

    user = session.get(User, stored.user_id)
    if user is None or not user.is_active:
        raise unauthorized("Your session is no longer valid. Please sign in again.", code="invalid_refresh")

    stored.revoked_at = utcnow()
    session.commit()
    return issue_tokens(session, user, family_id=stored.family_id)


def logout(session: Session, token: str) -> None:
    """Revoke the login chain the token belongs to. Unknown tokens are ignored."""
    stored = session.scalar(select(RefreshToken).where(RefreshToken.token_hash == hash_refresh_token(token)))
    if stored is not None:
        _revoke_family(session, stored.family_id)
        audit_service.record(session, stored.user_id, "logout", "user", stored.user_id)


def change_password(session: Session, user: User, current: str, new: str) -> None:
    """Change the password after checking the current one, and sign out every other session."""
    if not verify_password(current, user.password_hash):
        raise AppError(400, "wrong_password", "The current password is not correct.")
    user.password_hash = hash_password(new)
    session.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=utcnow())
    )
    session.commit()
    audit_service.record(session, user.id, "password_change", "user", user.id)
