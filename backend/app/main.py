"""
FastAPI application factory.

Responsibilities:
- Creates and configures the FastAPI instance.
- Registers CORS middleware and request-size limit.
- Adds a global exception handler that suppresses internal details.
- Mounts the central API router.
- Adds startup / shutdown lifecycle hooks.
"""

import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import get_settings
from app.api.router import api_router

settings = get_settings()
logger = logging.getLogger(__name__)

# ── Request-size limit middleware ──────────────────────────────────────────────
_MAX_BODY_BYTES = 5 * 1024 * 1024  # 5 MB


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Reject requests whose body exceeds *_MAX_BODY_BYTES*."""

    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > _MAX_BODY_BYTES:
            return JSONResponse(
                status_code=413,
                content={"detail": "Request body too large (max 5 MB)."},
            )
        return await call_next(request)


def create_app() -> FastAPI:
    """Construct and return the configured FastAPI application."""

    app = FastAPI(
        title=settings.app_name,
        version="1.0.0",
        description=(
            "Backend API for the AI Multi-Agent Workflow Automation Platform. "
            "Powered by Google Gemini and LangGraph."
        ),
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # ── Request size limit ─────────────────────────────────────────────────────
    app.add_middleware(RequestSizeLimitMiddleware)

    # ── CORS ───────────────────────────────────────────────────────────────────
    # Origins are configured via ALLOWED_ORIGINS env var (comma-separated).
    # Never hard-code "*" in production.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Global unhandled-exception handler ─────────────────────────────────────
    # Returns a generic 500 without leaking stack traces or internal state.
    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        logger.exception("Unhandled exception on %s %s", request.method, request.url)
        return JSONResponse(
            status_code=500,
            content={"detail": "An internal server error occurred."},
        )

    # ── Routes ─────────────────────────────────────────────────────────────────
    app.include_router(api_router)

    # ── Root ───────────────────────────────────────────────────────────────────
    @app.get("/", include_in_schema=False)
    async def root():
        return {"message": f"Welcome to {settings.app_name}", "docs": "/docs"}

    # ── Lifecycle hooks ────────────────────────────────────────────────────────
    @app.on_event("startup")
    async def on_startup():
        logger.info("🚀  %s starting in [%s] mode", settings.app_name, settings.app_env)

    @app.on_event("shutdown")
    async def on_shutdown():
        logger.info("🛑  Application shutting down")

    return app


app = create_app()
