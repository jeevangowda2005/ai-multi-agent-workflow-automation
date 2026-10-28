"""
Central API router — registers all route modules under /api prefix.
"""

from fastapi import APIRouter

from app.api.routes import health, workflows, ai, agents, executions, analytics, reports

api_router = APIRouter(prefix="/api")

api_router.include_router(health.router)
api_router.include_router(workflows.router)
api_router.include_router(ai.router)
api_router.include_router(agents.router)
api_router.include_router(executions.router)
api_router.include_router(analytics.router)
api_router.include_router(reports.router)

