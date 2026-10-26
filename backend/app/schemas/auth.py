"""Authentication schemas."""

from __future__ import annotations

from pydantic import EmailStr, Field, field_validator

from app.core.security import validate_password_policy
from app.schemas.common import CamelModel


class LoginRequest(CamelModel):
    """Email and password."""

    email: EmailStr
    password: str = Field(min_length=1, max_length=200)


class TokenPair(CamelModel):
    """Access and refresh tokens returned by login and refresh."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshRequest(CamelModel):
    """A refresh token to rotate or revoke."""

    refresh_token: str = Field(min_length=20, max_length=200)


class ChangePasswordRequest(CamelModel):
    """Current password plus a new one that must satisfy the policy."""

    current_password: str = Field(min_length=1, max_length=200)
    new_password: str

    @field_validator("new_password")
    @classmethod
    def check_policy(cls, value: str) -> str:
        """Apply the password policy."""
        return validate_password_policy(value)
