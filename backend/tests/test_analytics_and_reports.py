"""
Automated Test Suite for Step 6: AI Reports, Analytics & Execution History.

Covers:
1. Analytics Overview endpoint (GET /api/analytics/overview)
2. Analytics Trends endpoint (GET /api/analytics/trends)
3. Specialized Agent Usage & Efficiency (GET /api/analytics/agents)
4. AI Executive Report Generation (POST /api/reports/generate) with mocked Gemini
5. Reports List and Filtering (GET /api/reports)
6. Report Detail and Markdown Retrieval (GET /api/reports/{id})
7. Publication-Quality PDF Download (GET /api/reports/{id}/download)
8. Searchable Execution History (GET /api/executions with status & workflow filters)
"""

import json
from datetime import datetime, timezone, timedelta
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.db.session import SessionLocal
from app.models.workflow import Workflow
from app.models.task import Task
from app.models.execution import Execution
from app.models.task_execution import TaskExecution
from app.models.report import Report
from app.services import report_service


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def setup_test_workflow_and_execution(db, wf_name="Analytics Test WF"):
    """Creates a sample workflow with execution and completed tasks."""
    wf = Workflow(name=wf_name, description="Testing analytics and reports", status="active")
    db.add(wf)
    db.commit()
    db.refresh(wf)

    task1 = Task(
        workflow_id=wf.id,
        name="Market Research",
        task_type="action",
        status="completed",
        order_index=0,
        agent_type="research",
        input_data={"task_description": "Analyze market opportunities"},
        output_data={"summary": "Market growth projected at 25%"},
    )
    task2 = Task(
        workflow_id=wf.id,
        name="Executive Summary",
        task_type="action",
        status="completed",
        order_index=1,
        agent_type="reporting",
        input_data={"task_description": "Summarize insights"},
        output_data={"summary": "Executive briefing completed"},
    )
    db.add_all([task1, task2])
    db.commit()
    db.refresh(task1)
    db.refresh(task2)

    now = datetime.now(timezone.utc)
    started = now - timedelta(seconds=12)

    execution = Execution(
        workflow_id=wf.id,
        status="completed",
        total_tasks=2,
        completed_tasks=2,
        started_at=started,
        completed_at=now,
    )
    db.add(execution)
    db.commit()
    db.refresh(execution)

    te1 = TaskExecution(
        execution_id=execution.id,
        task_id=task1.id,
        status="completed",
        selected_agent="research",
        output_data=task1.output_data,
        retry_count=0,
        execution_time_ms=1200.0,
        started_at=started,
        completed_at=started + timedelta(seconds=5),
    )
    te2 = TaskExecution(
        execution_id=execution.id,
        task_id=task2.id,
        status="completed",
        selected_agent="reporting",
        output_data=task2.output_data,
        retry_count=0,
        execution_time_ms=800.0,
        started_at=started + timedelta(seconds=6),
        completed_at=now,
    )
    db.add_all([te1, te2])
    db.commit()

    return wf, [task1, task2], execution, [te1, te2]


# ── 1. Analytics Endpoints ───────────────────────────────────────────────────

def test_analytics_overview(client, db_session):
    """GET /api/analytics/overview returns real calculations from PostgreSQL."""
    wf, tasks, execution, task_execs = setup_test_workflow_and_execution(db_session, "Overview Test WF")
    try:
        res = client.get("/api/analytics/overview")
        assert res.status_code == 200
        data = res.json()
        assert data["total_executions"] >= 1
        assert data["completed_executions"] >= 1
        assert data["success_rate"] >= 0.0
        assert data["total_workflows"] >= 1
        assert data["total_tasks"] >= 2
    finally:
        for te in task_execs:
            db_session.delete(te)
        db_session.delete(execution)
        for t in tasks:
            db_session.delete(t)
        db_session.delete(wf)
        db_session.commit()


def test_analytics_trends(client, db_session):
    """GET /api/analytics/trends returns daily data points with status breakdown."""
    wf, tasks, execution, task_execs = setup_test_workflow_and_execution(db_session, "Trends Test WF")
    try:
        res = client.get("/api/analytics/trends?days=7")
        assert res.status_code == 200
        data = res.json()
        assert data["days"] == 7
        assert len(data["data_points"]) == 7
        for pt in data["data_points"]:
            assert "date" in pt
            assert "total" in pt
            assert "completed" in pt
            assert "failed" in pt
    finally:
        for te in task_execs:
            db_session.delete(te)
        db_session.delete(execution)
        for t in tasks:
            db_session.delete(t)
        db_session.delete(wf)
        db_session.commit()


def test_analytics_agents(client, db_session):
    """GET /api/analytics/agents aggregates usage across all 4 specialized agents."""
    wf, tasks, execution, task_execs = setup_test_workflow_and_execution(db_session, "Agents Test WF")
    try:
        res = client.get("/api/analytics/agents")
        assert res.status_code == 200
        data = res.json()
        agents = data["agents"]
        assert len(agents) == 4
        agent_types = {a["agent_type"] for a in agents}
        assert agent_types == {"research", "content_generation", "data_analysis", "reporting"}
        # Both research and reporting were dispatched in setup
        research_stat = next(a for a in agents if a["agent_type"] == "research")
        assert research_stat["total_runs"] >= 1
    finally:
        for te in task_execs:
            db_session.delete(te)
        db_session.delete(execution)
        for t in tasks:
            db_session.delete(t)
        db_session.delete(wf)
        db_session.commit()


# ── 2. AI Report Generation & Download ────────────────────────────────────────

@pytest.mark.asyncio
async def test_report_generation_mocked(client, db_session):
    """
    POST /api/reports/generate synthesizes execution outcomes with the Reporting Agent
    and persists structured findings and markdown in PostgreSQL.
    """
    wf, tasks, execution, task_execs = setup_test_workflow_and_execution(db_session, "Report Gen WF")

    mock_reporting_response = {
        "report_title": "Enterprise Cloud Migration Intelligence Briefing",
        "executive_summary": "Successful automated pipeline execution delivering market analysis and strategic roadmap.",
        "key_findings": [
            "25% projected compound annual growth in target segment",
            "Automation reduces operational latency by 40%",
        ],
        "detailed_analysis": "### Analytical Context\nDetailed breakdown of telemetry and outcomes.",
        "strategic_recommendations": [
            "Scale pipeline automation to customer onboarding",
            "Integrate continuous data telemetry monitoring",
        ],
        "next_steps": [
            "Review findings with executive stakeholders",
            "Deploy production webhooks for automated alerting",
        ],
    }

    async def mock_llm(_):
        return json.dumps(mock_reporting_response)

    try:
        # Generate report directly using service with mock LLM
        report = await report_service.generate_report_for_execution(
            db=db_session,
            execution_id=execution.id,
            title="Custom Intelligence Report",
            notes="Focus on Q4 revenue impact",
            llm_callable=mock_llm,
        )

        assert report.id is not None
        assert report.title == "Custom Intelligence Report"
        assert len(report.findings) == 2
        assert len(report.recommendations) == 2
        assert len(report.next_steps) == 2
        assert "## Executive Summary" in report.raw_markdown
        assert len(report.task_outcomes) == 2

        # Verify API retrieval GET /api/reports/{id}
        res_get = client.get(f"/api/reports/{report.id}")
        assert res_get.status_code == 200
        get_data = res_get.json()
        assert get_data["id"] == report.id
        assert get_data["workflow_id"] == wf.id

        # Verify PDF download GET /api/reports/{id}/download
        res_pdf = client.get(f"/api/reports/{report.id}/download")
        assert res_pdf.status_code == 200
        assert res_pdf.headers["content-type"] == "application/pdf"
        assert res_pdf.content.startswith(b"%PDF")
        assert len(res_pdf.content) > 500

        # Verify listing GET /api/reports
        res_list = client.get(f"/api/reports?workflow_id={wf.id}")
        assert res_list.status_code == 200
        items = res_list.json()
        assert any(r["id"] == report.id for r in items)

    finally:
        db_session.query(Report).filter(Report.execution_id == execution.id).delete()
        for te in task_execs:
            db_session.delete(te)
        db_session.delete(execution)
        for t in tasks:
            db_session.delete(t)
        db_session.delete(wf)
        db_session.commit()


# ── 3. Searchable Execution History ───────────────────────────────────────────

def test_searchable_execution_history(client, db_session):
    """GET /api/executions supports filtering by status and workflow_id."""
    wf, tasks, execution, task_execs = setup_test_workflow_and_execution(db_session, "History Filter WF")
    try:
        # Filter by workflow_id
        res = client.get(f"/api/executions?workflow_id={wf.id}")
        assert res.status_code == 200
        items = res.json()
        assert any(e["id"] == execution.id for e in items)

        # Filter by status completed
        res_status = client.get(f"/api/executions?status=completed&workflow_id={wf.id}")
        assert res_status.status_code == 200
        assert all(e["status"] == "completed" for e in res_status.json())

        # Filter by status failed should not include our completed execution
        res_failed = client.get(f"/api/executions?status=failed&workflow_id={wf.id}")
        assert res_failed.status_code == 200
        assert not any(e["id"] == execution.id for e in res_failed.json())
    finally:
        for te in task_execs:
            db_session.delete(te)
        db_session.delete(execution)
        for t in tasks:
            db_session.delete(t)
        db_session.delete(wf)
        db_session.commit()
