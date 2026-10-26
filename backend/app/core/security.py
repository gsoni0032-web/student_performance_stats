"""Password hashing, password policy and JWT helpers."""

from __future__ import annotations

import hashlib
import re
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
import jwt

from app.core.config import get_settings

ALGORITHM = "HS256"
PASSWORD_MIN_LENGTH = 10
_DUMMY_HASH = bcrypt.hashpw(
    b"not-a-real-password", bcrypt.gensalt(rounds=4 if get_settings().app_env == "test" else 12)
)


def validate_password_policy(password: str) -> str:
    """Return the password if it meets the policy, else raise ValueError with a clear message."""
    problems = []
    if len(password) < PASSWORD_MIN_LENGTH:
        problems.append(f"at least {PASSWORD_MIN_LENGTH} characters")
    if len(password.encode()) > 72:
        problems.append("at most 72 bytes")
    if not re.search(r"[a-z]", password):
        problems.append("a lowercase letter")
    if not re.search(r"[A-Z]", password):
        problems.append("an uppercase letter")
    if not re.search(r"\d", password):
        problems.append("a digit")
    if problems:
        raise ValueError("Password needs " + ", ".join(problems))
    return password


def hash_password(password: str) -> str:
    """Hash a password with bcrypt."""
    rounds = 4 if get_settings().app_env == "test" else 12
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=rounds)).decode()


def verify_password(password: str, password_hash: str | None) -> bool:
    """Check a password; always does a hash comparison so timing does not reveal unknown users."""
    candidate = password_hash.encode() if password_hash else _DUMMY_HASH
    try:
        matches = bcrypt.checkpw(password.encode()[:72], candidate)
    except ValueError:
        return False
    return matches and password_hash is not None


def create_access_token(user_id: int, role: str) -> tuple[str, int]:
    """Create a signed access token and return it with its lifetime in seconds."""
    settings = get_settings()
    now = datetime.now(UTC)
    lifetime = timedelta(minutes=settings.access_token_minutes)
    claims = {
        "sub": str(user_id),
        "role": role,
        "type": "access",
        "iat": now,
        "exp": now + lifetime,
        "jti": uuid.uuid4().hex,
    }
    token = jwt.encode(claims, settings.secret_key, algorithm=ALGORITHM)
    return token, int(lifetime.total_seconds())


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and validate an access token; raises `jwt.PyJWTError` on any problem."""
    claims: dict[str, Any] = jwt.decode(token, get_settings().secret_key, algorithms=[ALGORITHM])
    if claims.get("type") != "access":
        raise jwt.InvalidTokenError("not an access token")
    return claims


def new_refresh_token() -> str:
    """Create an opaque random refresh token (only its hash is stored)."""
    return secrets.token_urlsafe(48)


def hash_refresh_token(token: str) -> str:
    """Hash a refresh token for storage and lookup."""
    return hashlib.sha256(token.encode()).hexdigest()
