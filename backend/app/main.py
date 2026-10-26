"""FastAPI application factory."""

from __future__ import annotations

import logging
import time
import uuid
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app import __version__
from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.database import get_engine
from app.core.errors import register_error_handlers
from app.core.logging import configure_logging

logger = logging.getLogger("pathway.http")

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    "Cache-Control": "no-store",
    "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'",
}
DOCS_PATH_PREFIXES = ("/api/v1/docs", "/api/v1/redoc", "/api/v1/openapi.json")


def create_app() -> FastAPI:
    """Build the application with middleware, error handlers and routes."""
    settings = get_settings()
    configure_logging(settings.log_level, settings.log_json)

    app = FastAPI(
        title="Pathway API",
        version=__version__,
        description="Student performance and dropout prediction. Predictions support human decisions "
        "and must not be the only basis for action.",
        docs_url="/api/v1/docs" if settings.enable_docs else None,
        redoc_url=None,
        openapi_url="/api/v1/openapi.json" if settings.enable_docs else None,
    )
    register_error_handlers(app)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
        expose_headers=["Content-Disposition", "Retry-After", "X-Request-ID"],
    )

    @app.middleware("http")
    async def request_pipeline(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Enforce HTTPS in production, add security headers and log each request."""
        started = time.perf_counter()
        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex[:12]
        forwarded_proto = request.headers.get("x-forwarded-proto", request.url.scheme)
        if settings.force_https and forwarded_proto != "https" and request.url.path != "/health":
            return Response(status_code=308, headers={"Location": str(request.url.replace(scheme="https"))})
        response = await call_next(request)
        for name, value in SECURITY_HEADERS.items():
            if request.url.path.startswith(DOCS_PATH_PREFIXES) and name == "Content-Security-Policy":
                continue
            response.headers.setdefault(name, value)
        if settings.force_https:
            response.headers.setdefault("Strict-Transport-Security", "max-age=63072000; includeSubDomains")
        response.headers["X-Request-ID"] = request_id
        logger.info(
            "request",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "ms": round((time.perf_counter() - started) * 1000, 1),
            },
        )
        return response

    def health() -> dict[str, str]:
        """Liveness plus a database round trip."""
        with get_engine().connect() as connection:
            connection.execute(text("SELECT 1"))
        return {"status": "ok", "version": __version__}

    app.add_api_route("/health", health, methods=["GET"], tags=["health"])
    app.add_api_route("/api/v1/health", health, methods=["GET"], tags=["health"])
    app.include_router(api_router, prefix="/api/v1")
    return app


app = create_app()
