"""
Pydantic schemas for Analytics Dashboard.
"""

from typing import List
from pydantic import BaseModel, ConfigDict


class AnalyticsOverviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    total_executions: int
    completed_executions: int
    failed_executions: int
    canceled_executions: int
    running_executions: int
    success_rate: float
    avg_duration_seconds: float
    total_workflows: int
    total_tasks: int


class TrendDataPoint(BaseModel):
    date: str
    total: int
    completed: int
    failed: int
    canceled: int


class AnalyticsTrendsResponse(BaseModel):
    days: int
    data_points: List[TrendDataPoint]


class AgentUsageStat(BaseModel):
    agent_type: str
    name: str
    total_runs: int
    successful_runs: int
    failed_runs: int
    success_rate: float
    avg_time_ms: float


class AnalyticsAgentsResponse(BaseModel):
    agents: List[AgentUsageStat]
    total_agent_dispatches: int
