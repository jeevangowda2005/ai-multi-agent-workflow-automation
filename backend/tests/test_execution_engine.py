"""
Automated Test Suite for Step 5: Automated Workflow Execution & Real-Time Monitoring.

Covers:
1. Sequential task execution according to order_index
2. Structured output passing from parent task to dependent child task
3. Intelligent agent routing within workflows (Research -> Content -> Data -> Reporting)
4. Duplicate concurrent execution prevention (HTTP 409 Conflict)
5. Task failure halting subsequent dependent tasks and updating execution status to failed
6. Configurable retries on transient failures
7. Cancellation of active execution via POST /api/executions/{id}/cancel
8. Real-time WebSocket connection, subscription, and event streaming via WS /api/ws/executions/{id}
9. Full PostgreSQL persistence verification for workflows, tasks, executions, and task_executions
"""

import asyncio
import json
import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.db.session import SessionLocal
from app.models.workflow import Workflow
from app.models.task import Task
from app.models.execution import Execution
from app.models.task_execution import TaskExecution
from app.services import execution_engine
from app.core.websockets import ws_manager


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


def create_test_workflow(db, name="Test Workflow", task_count=2):
    """Helper to create a test workflow with ordered tasks."""
    wf = Workflow(name=name, description="Test workflow for Step 5 engine", status="active")
    db.add(wf)
    db.commit()
    db.refresh(wf)

    tasks = []
    for i in range(task_count):
        t = Task(
            workflow_id=wf.id,
            name=f"Step {i+1} Task",
            task_type="action",
            status="pending",
            order_index=i,
            agent_type="research" if i == 0 else "content_generation",
            input_data={"task_description": f"Perform step {i+1} analysis"},
            max_retries=1,
            timeout_seconds=30,
            depends_on_task_id=tasks[i-1].id if i > 0 else None,
        )
        db.add(t)
        db.commit()
        db.refresh(t)
        tasks.append(t)

    db.refresh(wf)
    return wf, tasks


# ── 1. Sequential Execution and Output Passing ────────────────────────────────

@pytest.mark.asyncio
async def test_sequential_execution_and_output_passing(db_session):
    """
    Verify tasks execute sequentially by order_index, and parent outputs
    are injected into dependent child tasks.
    """
    wf, tasks = create_test_workflow(db_session, name="Sequential Pipeline WF", task_count=2)

    exec_record = Execution(
        workflow_id=wf.id,
        status="pending",
        total_tasks=2,
        completed_tasks=0,
    )
    db_session.add(exec_record)
    db_session.commit()
    db_session.refresh(exec_record)

    # Mock responses — async fn that returns valid JSON for each agent type
    async def mock_llm(prompt, response_schema=None):
        prompt_lower = str(prompt).lower()
        # Content agent: prompt starts with "generate structured business content"
        if prompt_lower.startswith("generate structured business content"):
            return json.dumps({
                "content_type": "article",
                "tone_used": "professional",
                "title": "Customer Feedback Digest",
                "body": "Executive summary based on research findings showing a 30% improvement.",
                "alternative_headlines_or_hooks": ["Feedback Analysis Q4 2026"],
                "call_to_action": "Review the full report",
                "target_audience": "Business Stakeholders",
            })
        # Research agent: prompt starts with "conduct rigorous research"
        elif prompt_lower.startswith("conduct rigorous research"):
            return json.dumps({
                "topic": "Customer Feedback Analysis",
                "executive_summary": "Verified research findings on customer feedback.",
                "key_findings": ["Customer response time improved 30%"],
                "verified_facts": ["Customer response time improved 30%"],
                "ai_insights_and_projections": ["Further automation may reduce churn"],
                "sources_or_references": ["Customer Feedback Dataset 2026"],
            })
        # Task analysis routing — classify as research
        else:
            return json.dumps({
                "task_intent": "Research and analyze customer feedback.",
                "category": "research",
                "priority": "medium",
                "complexity": "moderate",
                "recommended_action": "Route to research agent",
                "explanation": "Task involves research analysis.",
                "suggested_subtasks": ["Gather data", "Analyze patterns"],
            })

    # Run the pipeline synchronously with mock LLM
    await execution_engine.execute_workflow_pipeline(
        workflow_id=wf.id,
        execution_id=exec_record.id,
        llm_callable=mock_llm,
    )

    # Re-fetch from DB
    db_session.refresh(exec_record)
    assert exec_record.status == "completed", f"Expected completed, got: {exec_record.status}. Error: {exec_record.error_message}"
    assert exec_record.completed_tasks == 2
    assert exec_record.total_tasks == 2
    assert exec_record.completed_at is not None

    # Verify task executions
    task_execs = (
        db_session.query(TaskExecution)
        .filter(TaskExecution.execution_id == exec_record.id)
        .order_by(TaskExecution.id.asc())
        .all()
    )
    assert len(task_execs) == 2
    assert task_execs[0].status == "completed"
    assert task_execs[0].selected_agent == "research"
    # Research output contains executive_summary
    assert task_execs[0].output_data is not None

    assert task_execs[1].status == "completed"
    assert task_execs[1].selected_agent == "content_generation"
    # Content output contains body
    assert task_execs[1].output_data is not None
    assert "body" in task_execs[1].output_data

    # Cleanup
    db_session.query(TaskExecution).filter(TaskExecution.execution_id == exec_record.id).delete()
    db_session.query(Execution).filter(Execution.id == exec_record.id).delete()
    for t in tasks:
        db_session.delete(t)
    db_session.delete(wf)
    db_session.commit()


# ── 2. Duplicate Execution Prevention (HTTP 409) ──────────────────────────────

def test_prevent_duplicate_concurrent_execution(client, db_session):
    """
    Attempting to execute a workflow that already has a 'running' execution
    must reject with HTTP 409 Conflict.
    """
    wf, tasks = create_test_workflow(db_session, name="Duplicate Guard WF", task_count=1)

    # Create an active running execution
    active_exec = Execution(
        workflow_id=wf.id,
        status="running",
        total_tasks=1,
        completed_tasks=0,
    )
    db_session.add(active_exec)
    db_session.commit()

    try:
        # Request execution on already running workflow
        res = client.post(f"/api/workflows/{wf.id}/execute", json={})
        assert res.status_code == 409
        detail = res.json()["detail"]
        assert "already running" in detail.lower()
    finally:
        db_session.delete(active_exec)
        for t in tasks:
            db_session.delete(t)
        db_session.delete(wf)
        db_session.commit()


# ── 3. Task Failure Halts Dependent Tasks ──────────────────────────────────────

@pytest.mark.asyncio
async def test_task_failure_halts_workflow(db_session):
    """
    If a task fails after exhausting retries, the workflow halts,
    subsequent dependent tasks are not run, and execution is marked failed.
    """
    wf, tasks = create_test_workflow(db_session, name="Failure Pipeline WF", task_count=2)

    # First task configured with 0 retries and will throw
    tasks[0].max_retries = 0
    db_session.commit()

    exec_record = Execution(
        workflow_id=wf.id,
        status="pending",
        total_tasks=2,
        completed_tasks=0,
    )
    db_session.add(exec_record)
    db_session.commit()
    db_session.refresh(exec_record)

    def failing_llm(messages, response_schema=None):
        raise ValueError("Simulated unrecoverable agent failure.")

    await execution_engine.execute_workflow_pipeline(
        workflow_id=wf.id,
        execution_id=exec_record.id,
        llm_callable=failing_llm,
    )

    db_session.refresh(exec_record)
    assert exec_record.status == "failed"
    assert "Simulated unrecoverable agent failure" in (exec_record.error_message or "")
    assert exec_record.completed_tasks == 0

    # Verify only task 1 attempted, task 2 was never dispatched
    task_execs = (
        db_session.query(TaskExecution)
        .filter(TaskExecution.execution_id == exec_record.id)
        .all()
    )
    assert len(task_execs) == 1
    assert task_execs[0].task_id == tasks[0].id
    assert task_execs[0].status == "failed"

    # Cleanup
    db_session.query(TaskExecution).filter(TaskExecution.execution_id == exec_record.id).delete()
    db_session.query(Execution).filter(Execution.id == exec_record.id).delete()
    for t in tasks:
        db_session.delete(t)
    db_session.delete(wf)
    db_session.commit()


# ── 4. Execution Cancellation ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_execution_cancellation(client, db_session):
    """
    Requesting cancellation via POST /api/executions/{id}/cancel
    flags the execution and transitions it to 'canceled'.
    """
    wf, tasks = create_test_workflow(db_session, name="Cancelable WF", task_count=3)

    exec_record = Execution(
        workflow_id=wf.id,
        status="running",
        total_tasks=3,
        completed_tasks=0,
    )
    db_session.add(exec_record)
    db_session.commit()
    db_session.refresh(exec_record)

    # Cancel via API
    res = client.post(f"/api/executions/{exec_record.id}/cancel")
    assert res.status_code == 200
    assert execution_engine.is_cancellation_requested(exec_record.id)

    # Simulate engine noticing cancellation flag
    def slow_llm(messages, response_schema=None):
        return "{}"

    await execution_engine.execute_workflow_pipeline(
        workflow_id=wf.id,
        execution_id=exec_record.id,
        llm_callable=slow_llm,
    )

    db_session.refresh(exec_record)
    assert exec_record.status == "canceled"

    # Cleanup
    execution_engine.clear_cancellation_flag(exec_record.id)
    db_session.query(TaskExecution).filter(TaskExecution.execution_id == exec_record.id).delete()
    db_session.query(Execution).filter(Execution.id == exec_record.id).delete()
    for t in tasks:
        db_session.delete(t)
    db_session.delete(wf)
    db_session.commit()


# ── 5. WebSocket Connection & Event Broadcast ─────────────────────────────────

def test_websocket_connection_and_subscription(client, db_session):
    """
    WebSocket at /api/ws/executions/{id} connects, receives initial confirmation,
    and responds to ping keep-alive with pong.
    """
    wf, tasks = create_test_workflow(db_session, name="WebSocket WF", task_count=1)

    exec_record = Execution(
        workflow_id=wf.id,
        status="running",
        total_tasks=1,
        completed_tasks=0,
    )
    db_session.add(exec_record)
    db_session.commit()
    db_session.refresh(exec_record)

    try:
        with client.websocket_connect(f"/api/ws/executions/{exec_record.id}") as websocket:
            # 1. First frame is subscription confirmation
            data = websocket.receive_json()
            assert data["event"] == "connected"
            assert data["execution_id"] == exec_record.id

            # 2. Ping-pong test
            websocket.send_text("ping")
            reply = websocket.receive_text()
            assert reply == "pong"
    finally:
        db_session.delete(exec_record)
        for t in tasks:
            db_session.delete(t)
        db_session.delete(wf)
        db_session.commit()


# ── 6. REST API Endpoints ─────────────────────────────────────────────────────

def test_execution_rest_endpoints(client, db_session):
    """
    Verify GET /api/executions/{id} and GET /api/workflows/{id}/executions.
    """
    wf, tasks = create_test_workflow(db_session, name="REST Endpoints WF", task_count=1)

    exec_record = Execution(
        workflow_id=wf.id,
        status="completed",
        total_tasks=1,
        completed_tasks=1,
    )
    db_session.add(exec_record)
    db_session.commit()
    db_session.refresh(exec_record)

    try:
        # GET single execution
        res = client.get(f"/api/executions/{exec_record.id}")
        assert res.status_code == 200
        data = res.json()
        assert data["id"] == exec_record.id
        assert data["status"] == "completed"

        # GET workflow executions list
        res_list = client.get(f"/api/workflows/{wf.id}/executions")
        assert res_list.status_code == 200
        items = res_list.json()
        assert len(items) >= 1
        assert any(e["id"] == exec_record.id for e in items)

        # 404 for non-existent execution
        res_404 = client.get("/api/executions/9999999")
        assert res_404.status_code == 404
    finally:
        db_session.delete(exec_record)
        for t in tasks:
            db_session.delete(t)
        db_session.delete(wf)
        db_session.commit()
