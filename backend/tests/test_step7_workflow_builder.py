"""
Automated Test Suite for Step 7: Visual Workflow Builder & Reusable Templates.

Covers:
1. List workflow templates (GET /api/workflows/templates)
2. Instantiate workflow from pre-built template (POST /api/workflows/templates/{id}/instantiate)
3. Update task configuration & agent type (PUT /api/workflows/{wf_id}/tasks/{task_id})
4. Circular dependency prevention (returns HTTP 400 on cycle)
5. Delete task node with downstream dependency reset (DELETE /api/workflows/{wf_id}/tasks/{task_id})
6. End-to-end execution of a template-instantiated workflow with mocked LLM
"""

import json
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.db.session import SessionLocal
from app.models.workflow import Workflow
from app.models.task import Task
from app.models.execution import Execution
from app.models.task_execution import TaskExecution
from app.services import execution_engine


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


# ── 1. Templates Catalog & Instantiation ──────────────────────────────────────

def test_list_workflow_templates(client):
    """GET /api/workflows/templates returns 3 pre-built multi-agent templates."""
    res = client.get("/api/workflows/templates")
    assert res.status_code == 200
    templates = res.json()
    assert len(templates) == 3

    ids = {t["id"] for t in templates}
    assert "customer-feedback-analysis" in ids
    assert "ai-content-generation-pipeline" in ids
    assert "business-research-reporting" in ids


def test_instantiate_template_creates_executable_workflow(client, db_session):
    """
    POST /api/workflows/templates/{id}/instantiate instantiates a full workflow
    with configured task nodes, sequential ordering, and dependency links.
    """
    res = client.post(
        "/api/workflows/templates/customer-feedback-analysis/instantiate?custom_name=Custom%20Feedback%20Test"
    )
    assert res.status_code == 201
    wf_data = res.json()
    wf_id = wf_data["id"]
    assert wf_data["name"] == "Custom Feedback Test"

    try:
        # Verify tasks created
        tasks_res = client.get(f"/api/workflows/{wf_id}/tasks")
        assert tasks_res.status_code == 200
        tasks = tasks_res.json()
        assert len(tasks) == 3

        # Task 1: Research, order_index 0, no dependency
        assert tasks[0]["agent_type"] == "research"
        assert tasks[0]["order_index"] == 0
        assert tasks[0]["depends_on_task_id"] is None

        # Task 2: Data Analysis, order_index 1, depends on Task 1
        assert tasks[1]["agent_type"] == "data_analysis"
        assert tasks[1]["order_index"] == 1
        assert tasks[1]["depends_on_task_id"] == tasks[0]["id"]

        # Task 3: Reporting, order_index 2, depends on Task 2
        assert tasks[2]["agent_type"] == "reporting"
        assert tasks[2]["order_index"] == 2
        assert tasks[2]["depends_on_task_id"] == tasks[1]["id"]

    finally:
        # Cleanup
        db_session.query(Task).filter(Task.workflow_id == wf_id).delete()
        db_session.query(Workflow).filter(Workflow.id == wf_id).delete()
        db_session.commit()


# ── 2. Task Configuration & Circular Dependency Prevention ─────────────────────

def test_update_task_configuration(client, db_session):
    """PUT /api/workflows/{wf_id}/tasks/{task_id} updates agent configuration."""
    wf = Workflow(name="Update Task WF", status="active")
    db_session.add(wf)
    db_session.commit()
    db_session.refresh(wf)

    task = Task(
        workflow_id=wf.id,
        name="Initial Task",
        agent_type="research",
        order_index=0,
        max_retries=0,
        timeout_seconds=30,
    )
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)

    try:
        update_payload = {
            "name": "Updated Intelligence Gathering",
            "agent_type": "data_analysis",
            "max_retries": 2,
            "timeout_seconds": 90,
            "order_index": 1,
        }
        res = client.put(f"/api/workflows/{wf.id}/tasks/{task.id}", json=update_payload)
        assert res.status_code == 200
        data = res.json()
        assert data["name"] == "Updated Intelligence Gathering"
        assert data["agent_type"] == "data_analysis"
        assert data["max_retries"] == 2
        assert data["timeout_seconds"] == 90
        assert data["order_index"] == 1
    finally:
        db_session.delete(task)
        db_session.delete(wf)
        db_session.commit()


def test_circular_dependency_prevention(client, db_session):
    """
    Attempting to set a circular dependency (e.g. Task A depends on Task B,
    and Task B is set to depend on Task A) must be rejected with HTTP 400.
    """
    wf = Workflow(name="Cycle Test WF", status="active")
    db_session.add(wf)
    db_session.commit()
    db_session.refresh(wf)

    task_a = Task(workflow_id=wf.id, name="Task A", order_index=0)
    task_b = Task(workflow_id=wf.id, name="Task B", order_index=1)
    db_session.add_all([task_a, task_b])
    db_session.commit()
    db_session.refresh(task_a)
    db_session.refresh(task_b)

    try:
        # Set Task B depends on Task A
        res_b = client.put(
            f"/api/workflows/{wf.id}/tasks/{task_b.id}",
            json={"depends_on_task_id": task_a.id},
        )
        assert res_b.status_code == 200

        # Now attempt to set Task A depends on Task B -> CIRCULAR!
        res_cycle = client.put(
            f"/api/workflows/{wf.id}/tasks/{task_a.id}",
            json={"depends_on_task_id": task_b.id},
        )
        assert res_cycle.status_code == 400
        assert "Circular dependency detected" in res_cycle.json()["detail"]

        # Attempt self-dependency: Task A depends on Task A -> CIRCULAR!
        res_self = client.put(
            f"/api/workflows/{wf.id}/tasks/{task_a.id}",
            json={"depends_on_task_id": task_a.id},
        )
        assert res_self.status_code == 400
        assert "Circular dependency detected" in res_self.json()["detail"]

    finally:
        db_session.delete(task_b)
        db_session.delete(task_a)
        db_session.delete(wf)
        db_session.commit()


def test_delete_task_resets_downstream_dependencies(client, db_session):
    """
    DELETE /api/workflows/{wf_id}/tasks/{task_id} deletes the task and resets
    any downstream tasks depending on it to depends_on_task_id = None.
    """
    wf = Workflow(name="Delete Task WF", status="active")
    db_session.add(wf)
    db_session.commit()
    db_session.refresh(wf)

    task_parent = Task(workflow_id=wf.id, name="Parent Step", order_index=0)
    db_session.add(task_parent)
    db_session.commit()
    db_session.refresh(task_parent)

    task_child = Task(
        workflow_id=wf.id,
        name="Child Step",
        order_index=1,
        depends_on_task_id=task_parent.id,
    )
    db_session.add(task_child)
    db_session.commit()
    db_session.refresh(task_child)

    try:
        # Delete parent task
        res_del = client.delete(f"/api/workflows/{wf.id}/tasks/{task_parent.id}")
        assert res_del.status_code == 204

        # Verify child dependency was reset
        db_session.refresh(task_child)
        assert task_child.depends_on_task_id is None

    finally:
        db_session.delete(task_child)
        db_session.delete(wf)
        db_session.commit()


# ── 3. Execution of Template-Instantiated Workflow ─────────────────────────────

@pytest.mark.asyncio
async def test_template_workflow_executes_cleanly(client, db_session):
    """
    Instantiates the 'business-research-reporting' template and executes
    it through the execution engine with mocked LLM responses.
    """
    # 1. Instantiate template
    res_inst = client.post(
        "/api/workflows/templates/business-research-reporting/instantiate?custom_name=Execution%20Test%20Template"
    )
    assert res_inst.status_code == 201
    wf_id = res_inst.json()["id"]

    # Mock responses for research and reporting
    async def mock_llm(prompt, response_schema=None):
        prompt_lower = str(prompt).lower()
        if "formal, publication-ready enterprise report" in prompt_lower:
            return json.dumps({
                "report_title": "Enterprise Strategic Report",
                "executive_summary": "Comprehensive briefing based on competitive intelligence.",
                "key_findings": ["Market share shifts indicate window of opportunity"],
                "detailed_analysis": "### Strategic Positioning\nExpanded market presence required.",
                "strategic_recommendations": ["Accelerate go-to-market automation"],
                "next_steps": ["Deploy multi-agent pipelines to field teams"],
            })
        else:
            return json.dumps({
                "topic": "Competitive Intelligence Analysis",
                "executive_summary": "Verified industry intelligence findings.",
                "key_findings": ["Competitor market share shifted by 15%"],
                "verified_facts": ["Shift of 15% verified from benchmarks"],
                "ai_insights_and_projections": ["Consolidation expected in H2"],
                "sources_or_references": ["Market Dataset 2026"],
            })

    exec_record = Execution(
        workflow_id=wf_id,
        status="pending",
        total_tasks=2,
        completed_tasks=0,
    )
    db_session.add(exec_record)
    db_session.commit()
    db_session.refresh(exec_record)

    try:
        await execution_engine.execute_workflow_pipeline(
            workflow_id=wf_id,
            execution_id=exec_record.id,
            llm_callable=mock_llm,
        )

        db_session.refresh(exec_record)
        assert exec_record.status == "completed"
        assert exec_record.completed_tasks == 2

        # Verify task executions persisted
        task_execs = (
            db_session.query(TaskExecution)
            .filter(TaskExecution.execution_id == exec_record.id)
            .all()
        )
        assert len(task_execs) == 2
        assert all(te.status == "completed" for te in task_execs)

    finally:
        db_session.query(TaskExecution).filter(TaskExecution.execution_id == exec_record.id).delete()
        db_session.delete(exec_record)
        db_session.query(Task).filter(Task.workflow_id == wf_id).delete()
        db_session.query(Workflow).filter(Workflow.id == wf_id).delete()
        db_session.commit()
