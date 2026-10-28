"""
Health check and system status routes.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/health", tags=["health"])


@router.get(
    "",
    summary="Health check",
    response_description="Application health status",
)
async def health_check() -> dict:
    """
    Returns a simple health status.

    Used by load balancers, monitoring tools, and the frontend to verify
    the backend is reachable and running.
    """
    return {"status": "healthy"}
