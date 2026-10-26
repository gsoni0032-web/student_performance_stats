"""Application errors and the handlers that render them in one consistent shape.

Every error response looks like::

    {"error": {"code": "not_found", "message": "Student not found", "details": []}}
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("pathway.errors")


class AppError(Exception):
    """An expected, user-facing failure with a stable machine-readable code."""

    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        details: list[dict[str, Any]] | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details or []
        self.headers = headers


def not_found(what: str) -> AppError:
    """404 for a missing entity."""
    return AppError(404, "not_found", f"{what} not found")


def forbidden(message: str = "You do not have permission to do that") -> AppError:
    """403 for a role or scope violation."""
    return AppError(403, "forbidden", message)


def conflict(message: str) -> AppError:
    """409 for a uniqueness or state conflict."""
    return AppError(409, "conflict", message)


def bad_request(message: str, details: list[dict[str, Any]] | None = None) -> AppError:
    """400 for a request that is well-formed but cannot be processed."""
    return AppError(400, "bad_request", message, details)


def unauthorized(message: str = "Authentication required", code: str = "unauthorized") -> AppError:
    """401 with the WWW-Authenticate header clients expect."""
    return AppError(401, code, message, headers={"WWW-Authenticate": "Bearer"})


def _payload(code: str, message: str, details: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return {"error": {"code": code, "message": message, "details": details or []}}


def register_error_handlers(app: FastAPI) -> None:
    """Attach handlers so every failure uses the same JSON envelope."""

    @app.exception_handler(AppError)
    async def handle_app_error(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            _payload(exc.code, exc.message, exc.details),
            status_code=exc.status_code,
            headers=exc.headers,
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_error(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = {404: "not_found", 405: "method_not_allowed"}.get(exc.status_code, "http_error")
        return JSONResponse(
            _payload(code, str(exc.detail)),
            status_code=exc.status_code,
            headers=getattr(exc, "headers", None),
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        details = [
            {
                "field": ".".join(str(part) for part in error["loc"] if part != "body"),
                "message": error["msg"],
            }
            for error in exc.errors()
        ]
        return JSONResponse(
            _payload("validation_error", "Some fields are not valid", details),
            status_code=422,
        )

    @app.exception_handler(Exception)
    async def handle_unexpected(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled error on %s %s", request.method, request.url.path, exc_info=exc)
        return JSONResponse(
            _payload("internal_error", "Something went wrong on our side. Please try again."),
            status_code=500,
        )
