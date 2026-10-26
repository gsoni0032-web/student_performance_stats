"""Shared FastAPI dependencies: database session, current user, role checks."""

from __future__ import annotations

from collections.abc import Callable
from typing import Annotated

import jwt
from fastapi import Depends, Query, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.errors import forbidden, unauthorized
from app.core.security import decode_access_token
from app.models import User
from app.models.enums import Role

bearer = HTTPBearer(auto_error=False)

DbSession = Annotated[Session, Depends(get_db)]


def current_user(
    session: DbSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> User:
    """The signed-in, active user, or a 401."""
    if credentials is None:
        raise unauthorized()
    try:
        claims = decode_access_token(credentials.credentials)
        user_id = int(claims["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise unauthorized("Your session has expired. Please sign in again.", code="token_invalid") from None
    user = session.get(User, user_id)
    if user is None or not user.is_active:
        raise unauthorized("Your account is no longer active.", code="token_invalid")
    return user


CurrentUser = Annotated[User, Depends(current_user)]


def require_roles(*roles: Role) -> Callable[[User], User]:
    """Dependency factory: allow only the listed roles."""
    allowed = {role.value for role in roles}

    def check(user: CurrentUser) -> User:
        if user.role not in allowed:
            raise forbidden()
        return user

    return check


AdminUser = Annotated[User, Depends(require_roles(Role.ADMIN))]
WriterUser = Annotated[User, Depends(require_roles(Role.ADMIN, Role.TEACHER))]


def client_key(request: Request) -> str:
    """Identify the caller for rate limiting (honours the first X-Forwarded-For hop)."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


class PageParams:
    """Standard pagination query parameters."""

    def __init__(
        self,
        page: Annotated[int, Query(ge=1)] = 1,
        page_size: Annotated[int, Query(ge=1, le=100)] = 25,
    ) -> None:
        self.page = page
        self.page_size = page_size


Pagination = Annotated[PageParams, Depends()]
