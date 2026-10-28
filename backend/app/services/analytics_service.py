"""
Analytics calculation service.
Computes real-time execution statistics, success rates, duration averages,
daily execution trends, and agent usage metrics directly from PostgreSQL.
"""

from datetime import datetime, timedelta, timezone
from typing import Dict, List
from sqlalchemy import func, case
from sqlalchemy.orm import Session

from app.models.workflow import Workflow
from app.models.task import Task
from app.models.execution import Execution
from app.models.task_execution import TaskExecution
from app.models.agent_execution import AgentExecution
from app.schemas.analytics import (
    AnalyticsOverviewResponse,
    AnalyticsTrendsResponse,
    AnalyticsAgentsResponse,
    AgentUsageStat,
    TrendDataPoint,
)

AGENT_DISPLAY_NAMES = {
    "research": "Research Agent",
    "content_generation": "Content Generation Agent",
    "data_analysis": "Data Analysis Agent",
    "reporting": "Reporting Agent",
}


def get_analytics_overview(db: Session) -> AnalyticsOverviewResponse:
    """Calculates overall platform metrics from PostgreSQL records."""
    total_execs = db.query(func.count(Execution.id)).scalar() or 0
    completed_execs = db.query(func.count(Execution.id)).filter(Execution.status == "completed").scalar() or 0
    failed_execs = db.query(func.count(Execution.id)).filter(Execution.status == "failed").scalar() or 0
    canceled_execs = db.query(func.count(Execution.id)).filter(Execution.status == "canceled").scalar() or 0
    running_execs = db.query(func.count(Execution.id)).filter(Execution.status == "running").scalar() or 0

    success_rate = round((completed_execs / total_execs * 100), 2) if total_execs > 0 else 0.0

    # Calculate average duration in seconds for executions that have completed_at & started_at
    durations = (
        db.query(
            func.avg(
                func.extract("epoch", Execution.completed_at) - func.extract("epoch", Execution.started_at)
            )
        )
        .filter(Execution.completed_at.isnot(None), Execution.started_at.isnot(None))
        .scalar()
    )
    avg_duration = round(float(durations), 2) if durations is not None else 0.0

    total_wf = db.query(func.count(Workflow.id)).scalar() or 0
    total_tasks = db.query(func.count(Task.id)).scalar() or 0

    return AnalyticsOverviewResponse(
        total_executions=total_execs,
        completed_executions=completed_execs,
        failed_executions=failed_execs,
        canceled_executions=canceled_execs,
        running_executions=running_execs,
        success_rate=success_rate,
        avg_duration_seconds=avg_duration,
        total_workflows=total_wf,
        total_tasks=total_tasks,
    )


def get_analytics_trends(db: Session, days: int = 7) -> AnalyticsTrendsResponse:
    """Calculates daily execution counts (total, completed, failed, canceled) for the last N days."""
    days = max(1, min(days, 90))
    now = datetime.now(timezone.utc)
    start_date = (now - timedelta(days=days - 1)).replace(hour=0, minute=0, second=0, microsecond=0)

    # Initialize buckets for each date
    date_map: Dict[str, Dict[str, int]] = {}
    for i in range(days):
        day_str = (start_date + timedelta(days=i)).strftime("%Y-%m-%d")
        date_map[day_str] = {"total": 0, "completed": 0, "failed": 0, "canceled": 0}

    # Query executions grouped by date
    results = (
        db.query(
            func.to_char(Execution.started_at, "YYYY-MM-DD").label("exec_date"),
            Execution.status,
            func.count(Execution.id).label("count"),
        )
        .filter(Execution.started_at >= start_date)
        .group_by(func.to_char(Execution.started_at, "YYYY-MM-DD"), Execution.status)
        .all()
    )

    for row in results:
        day_key = row.exec_date
        status = (row.status or "").lower()
        cnt = int(row.count)
        if day_key in date_map:
            date_map[day_key]["total"] += cnt
            if status == "completed":
                date_map[day_key]["completed"] += cnt
            elif status == "failed":
                date_map[day_key]["failed"] += cnt
            elif status == "canceled":
                date_map[day_key]["canceled"] += cnt

    points = [
        TrendDataPoint(
            date=day,
            total=data["total"],
            completed=data["completed"],
            failed=data["failed"],
            canceled=data["canceled"],
        )
        for day, data in date_map.items()
    ]

    return AnalyticsTrendsResponse(days=days, data_points=points)


def get_analytics_agents(db: Session) -> AnalyticsAgentsResponse:
    """Aggregates usage, success rate, and duration for all 4 specialized agents."""
    # Group by selected_agent from TaskExecution
    task_exec_stats = (
        db.query(
            TaskExecution.selected_agent,
            func.count(TaskExecution.id).label("total_runs"),
            func.sum(case((TaskExecution.status == "completed", 1), else_=0)).label("successful_runs"),
            func.sum(case((TaskExecution.status == "failed", 1), else_=0)).label("failed_runs"),
            func.avg(TaskExecution.execution_time_ms).label("avg_time_ms"),
        )
        .filter(TaskExecution.selected_agent.isnot(None))
        .group_by(TaskExecution.selected_agent)
        .all()
    )

    # Group by selected_agent from AgentExecution (Step 4 standalone workspace runs)
    standalone_stats = (
        db.query(
            AgentExecution.selected_agent,
            func.count(AgentExecution.id).label("total_runs"),
            func.sum(case((AgentExecution.status == "completed", 1), else_=0)).label("successful_runs"),
            func.sum(case((AgentExecution.status == "failed", 1), else_=0)).label("failed_runs"),
            func.avg(AgentExecution.execution_time_ms).label("avg_time_ms"),
        )
        .group_by(AgentExecution.selected_agent)
        .all()
    )

    # Combine metrics per agent
    combined: Dict[str, Dict[str, Any]] = {
        k: {"total": 0, "successful": 0, "failed": 0, "time_sum": 0.0, "time_count": 0}
        for k in AGENT_DISPLAY_NAMES.keys()
    }

    for row in list(task_exec_stats) + list(standalone_stats):
        agent_key = (row.selected_agent or "").lower()
        if agent_key in combined:
            tot = int(row.total_runs or 0)
            succ = int(row.successful_runs or 0)
            fail = int(row.failed_runs or 0)
            avg_t = float(row.avg_time_ms or 0.0)

            combined[agent_key]["total"] += tot
            combined[agent_key]["successful"] += succ
            combined[agent_key]["failed"] += fail
            if avg_t > 0:
                combined[agent_key]["time_sum"] += avg_t * tot
                combined[agent_key]["time_count"] += tot

    agent_items: List[AgentUsageStat] = []
    total_dispatches = 0

    for agent_id, name in AGENT_DISPLAY_NAMES.items():
        data = combined[agent_id]
        tot = data["total"]
        succ = data["successful"]
        fail = data["failed"]
        total_dispatches += tot
        rate = round((succ / tot * 100), 2) if tot > 0 else 0.0
        avg_ms = round(data["time_sum"] / data["time_count"], 2) if data["time_count"] > 0 else 0.0

        agent_items.append(
            AgentUsageStat(
                agent_type=agent_id,
                name=name,
                total_runs=tot,
                successful_runs=succ,
                failed_runs=fail,
                success_rate=rate,
                avg_time_ms=avg_ms,
            )
        )

    return AnalyticsAgentsResponse(
        agents=agent_items,
        total_agent_dispatches=total_dispatches,
    )
