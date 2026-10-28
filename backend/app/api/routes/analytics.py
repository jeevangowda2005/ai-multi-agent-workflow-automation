"""
API endpoints for Platform Analytics and Telemetry.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.analytics import (
    AnalyticsOverviewResponse,
    AnalyticsTrendsResponse,
    AnalyticsAgentsResponse,
)
from app.services import analytics_service

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get(
    "/overview",
    response_model=AnalyticsOverviewResponse,
    summary="Get overall platform execution metrics and success rates",
)
def get_analytics_overview(db: Session = Depends(get_db)):
    """Calculates total executions, completions, failures, success rate, and duration metrics."""
    return analytics_service.get_analytics_overview(db=db)


@router.get(
    "/trends",
    response_model=AnalyticsTrendsResponse,
    summary="Get daily execution trends over time",
)
def get_analytics_trends(
    days: int = Query(7, ge=1, le=90, description="Number of past days to query"),
    db: Session = Depends(get_db),
):
    """Returns daily execution counts categorized by status."""
    return analytics_service.get_analytics_trends(db=db, days=days)


@router.get(
    "/agents",
    response_model=AnalyticsAgentsResponse,
    summary="Get specialized agent usage distribution and efficiency statistics",
)
def get_analytics_agents(db: Session = Depends(get_db)):
    """Returns dispatch count, success rate, and average latency per AI agent."""
    return analytics_service.get_analytics_agents(db=db)
