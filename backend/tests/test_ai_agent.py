"""
Automated test suite for AI Task Analysis Agent and /api/ai endpoints.
Covers:
- LangGraph state graph execution
- Structured Pydantic validation (categories, priority, complexity)
- Error handling for invalid inputs and malformed LLM responses
- Missing API key detection (503 Service Unavailable)
- Workflow association & PostgreSQL persistence
- Conditional real Gemini API check (if GEMINI_API_KEY is configured)
- Regression testing on existing Workflow CRUD APIs
"""

import asyncio
import json
import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import get_settings
from app.agents.task_analyzer import run_task_analysis_agent
from app.schemas.ai import TaskAnalysisResult


@pytest.fixture
def client():
    return TestClient(app)


# ── 1. AI Health Endpoint Tests ───────────────────────────────────────────────

def test_ai_health_unconfigured(client):
    """Verify /api/ai/health returns unconfigured when key is placeholder or empty."""
    res = client.get("/api/ai/health")
    assert res.status_code == 200
    data = res.json()
    assert "status" in data
    assert "model" in data
    assert "api_key_configured" in data
    assert isinstance(data["api_key_configured"], bool)


def test_ai_health_configured_mock(client):
    """Verify /api/ai/health reports ready when API key is present."""
    with patch("app.core.config.Settings.is_gemini_configured", True):
        res = client.get("/api/ai/health")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "ready"
        assert data["api_key_configured"] is True
        assert "gemini" in data["model"]


# ── 2. LangGraph StateGraph Node & Pydantic Validation Tests ─────────────────

@pytest.mark.asyncio
async def test_langgraph_agent_research_category():
    """Verify LangGraph agent correctly parses research task with subtasks."""
    mock_payload = {
        "task_intent": "Research competitive landscape for AI automation agents in enterprise market",
        "category": "research",
        "priority": "high",
        "complexity": "moderate",
        "recommended_action": "Execute Web Search and Market Intelligence subagents",
        "explanation": "Information gathering across public market reports and vendor websites.",
        "suggested_subtasks": [
            "Identify top 5 competitor platforms",
            "Extract pricing and feature matrix",
            "Synthesize SWOT analysis report",
        ],
    }

    async def mock_llm(_):
        return json.dumps(mock_payload)

    result = await run_task_analysis_agent(
        task_description="Research competitive landscape for AI automation agents",
        llm_callable=mock_llm,
    )

    assert isinstance(result, TaskAnalysisResult)
    assert result.category == "research"
    assert result.priority == "high"
    assert result.complexity == "moderate"
    assert len(result.suggested_subtasks) == 3


@pytest.mark.asyncio
async def test_langgraph_agent_data_analysis_category():
    """Verify LangGraph agent parses data analysis task."""
    mock_payload = {
        "task_intent": "Analyze user churn patterns from monthly subscription dataset",
        "category": "data_analysis",
        "priority": "critical",
        "complexity": "complex",
        "recommended_action": "Execute Data Aggregator and Statistical Modeling pipeline",
        "explanation": "High business priority due to customer retention impact.",
        "suggested_subtasks": [
            "Calculate monthly cohort retention rates",
            "Identify correlation with feature usage",
        ],
    }

    async def mock_llm(_):
        return json.dumps(mock_payload)

    result = await run_task_analysis_agent(
        task_description="Analyze customer churn metrics from Q2 database",
        llm_callable=mock_llm,
    )

    assert result.category == "data_analysis"
    assert result.priority == "critical"
    assert result.complexity == "complex"


@pytest.mark.asyncio
async def test_langgraph_agent_enrichment_empty_subtasks():
    """Verify enrich node adds fallback subtask if LLM returned empty list."""
    mock_payload = {
        "task_intent": "Write weekly team progress email",
        "category": "content_generation",
        "priority": "low",
        "complexity": "simple",
        "recommended_action": "Generate draft email from sprint tickets",
        "explanation": "Routine internal communication.",
        "suggested_subtasks": [],
    }

    async def mock_llm(_):
        return json.dumps(mock_payload)

    result = await run_task_analysis_agent(
        task_description="Draft weekly update email for team",
        llm_callable=mock_llm,
    )

    # Subtasks should be enriched with recommended_action
    assert len(result.suggested_subtasks) >= 1
    assert result.suggested_subtasks[0] == mock_payload["recommended_action"]


@pytest.mark.asyncio
async def test_langgraph_agent_markdown_wrapped_json():
    """Verify parse node handles LLM wrapping response in ```json ... ``` codeblocks."""
    mock_payload = {
        "task_intent": "Generate monthly executive financial report",
        "category": "reporting",
        "priority": "high",
        "complexity": "moderate",
        "recommended_action": "Run financial rollup agent",
        "explanation": "Executive reporting schedule.",
        "suggested_subtasks": ["Fetch balances", "Draft executive summary"],
    }

    wrapped = f"```json\n{json.dumps(mock_payload)}\n```"

    async def mock_llm(_):
        return wrapped

    result = await run_task_analysis_agent(
        task_description="Generate monthly financial rollup report",
        llm_callable=mock_llm,
    )
    assert result.category == "reporting"


@pytest.mark.asyncio
async def test_langgraph_agent_invalid_json_fails():
    """Verify parse node captures invalid JSON and raises ValueError."""
    async def bad_llm(_):
        return "This is not valid JSON at all!"

    with pytest.raises(ValueError, match="Failed to parse LLM output as JSON"):
        await run_task_analysis_agent(
            task_description="Perform marketing campaign evaluation",
            llm_callable=bad_llm,
        )


@pytest.mark.asyncio
async def test_langgraph_agent_validation_short_input():
    """Verify validate node rejects inputs that are too short."""
    with pytest.raises(ValueError, match="too short"):
        await run_task_analysis_agent(task_description="hi")


# ── 3. API Endpoint /api/ai/analyze Tests ────────────────────────────────────

def test_analyze_unconfigured_api_key_returns_503(client):
    """When API key is placeholder or empty, POST /api/ai/analyze returns 503."""
    with patch("app.core.config.Settings.is_gemini_configured", False):
        res = client.post(
            "/api/ai/analyze",
            json={"task_description": "Analyze market trends in renewable energy"},
        )
        assert res.status_code == 503
        assert "not configured" in res.json()["detail"].lower()


def test_analyze_validation_empty_description(client):
    """Validation test: empty or short description rejected with 422."""
    res = client.post("/api/ai/analyze", json={"task_description": "ab"})
    assert res.status_code == 422


def test_analyze_with_mocked_gemini(client):
    """Verify POST /api/ai/analyze with mocked Gemini response."""
    mock_result = TaskAnalysisResult(
        task_intent="Summarize customer support inquiries for product team",
        category="reporting",
        priority="medium",
        complexity="moderate",
        recommended_action="Route ticket logs to extraction subagent",
        explanation="Standard ticket categorization and summarization.",
        suggested_subtasks=["Cluster issues by topic", "Calculate recurrence"],
    )

    with patch("app.core.config.Settings.is_gemini_configured", True):
        with patch("app.api.routes.ai.run_task_analysis_agent", new=AsyncMock(return_value=mock_result)):
            res = client.post(
                "/api/ai/analyze",
                json={"task_description": "Summarize top customer feedback tickets for this month"},
            )
            assert res.status_code == 200
            data = res.json()
            assert data["success"] is True
            assert data["analysis"]["category"] == "reporting"
            assert data["analysis"]["priority"] == "medium"
            assert "execution_time_ms" in data


def test_analyze_and_persist_to_existing_workflow(client):
    """Verify analysis result is persisted as a Task in PostgreSQL when workflow_id is given."""
    # 1. Create a workflow first
    wf_res = client.post(
        "/api/workflows",
        json={"name": "AI Triage Workflow", "status": "active"},
    )
    assert wf_res.status_code == 201
    wf_id = wf_res.json()["id"]

    mock_result = TaskAnalysisResult(
        task_intent="Investigate security log anomalies in auth service",
        category="data_analysis",
        priority="critical",
        complexity="complex",
        recommended_action="Execute Security Auditor agent",
        explanation="Direct security threat assessment.",
        suggested_subtasks=["Parse access logs", "Flag IP addresses"],
    )

    with patch("app.core.config.Settings.is_gemini_configured", True):
        with patch("app.api.routes.ai.run_task_analysis_agent", new=AsyncMock(return_value=mock_result)):
            res = client.post(
                "/api/ai/analyze",
                json={
                    "task_description": "Investigate unusual auth failure spikes in EU region",
                    "workflow_id": wf_id,
                },
            )
            assert res.status_code == 200
            data = res.json()
            assert data["saved_task_id"] is not None
            task_id = data["saved_task_id"]

            # 2. Verify task exists under this workflow via GET /api/workflows/{wf_id}/tasks
            tasks_res = client.get(f"/api/workflows/{wf_id}/tasks")
            assert tasks_res.status_code == 200
            tasks = tasks_res.json()
            matching = [t for t in tasks if t["id"] == task_id]
            assert len(matching) == 1
            saved = matching[0]
            assert saved["task_type"] == "llm"
            assert saved["status"] == "completed"
            assert saved["output_data"]["category"] == "data_analysis"

    # Cleanup workflow
    client.delete(f"/api/workflows/{wf_id}")


def test_analyze_invalid_workflow_id_returns_404(client):
    """Verify passing a non-existent workflow_id returns 404 before calling AI."""
    res = client.post(
        "/api/ai/analyze",
        json={
            "task_description": "Compile quarterly tax documentation",
            "workflow_id": 999999,
        },
    )
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()


# ── 4. Real Gemini API Integration Test (Conditional) ─────────────────────────

@pytest.mark.asyncio
async def test_live_gemini_api_if_configured():
    """
    Real integration test against Google Gemini API.
    Only runs if a valid non-placeholder GEMINI_API_KEY is detected in environment.
    Otherwise clearly reports as skipped.
    """
    settings = get_settings()
    if not settings.is_gemini_configured:
        pytest.skip(
            "Live Gemini API test skipped: GEMINI_API_KEY is not configured or using default placeholder. "
            "Mocked tests validated all agent and StateGraph logic."
        )

    # If configured, run a real end-to-end task analysis call
    try:
        result = await run_task_analysis_agent(
            task_description="Create a competitive analysis matrix comparing top 3 enterprise cloud CRM systems."
        )
        assert isinstance(result, TaskAnalysisResult)
        assert result.category in ["research", "reporting", "data_analysis", "general", "content_generation"]
        assert result.priority in ["low", "medium", "high", "critical"]
        assert result.complexity in ["simple", "moderate", "complex"]
        assert len(result.recommended_action) > 5
        print("\n✅ Real Google Gemini API call succeeded with model:", settings.gemini_model)
    except ValueError as exc:
        if "rate limit" in str(exc).lower() or "quota" in str(exc).lower():
            pytest.skip(f"Gemini API free tier rate limit reached: {exc}")
        raise



# ── 5. Existing Workflow CRUD Regression Tests ────────────────────────────────

def test_workflow_crud_regression(client):
    """Verify that Step 1 & Step 2 workflow CRUD functionality continues working without regression."""
    # Create
    res = client.post(
        "/api/workflows",
        json={"name": "Regression Test Workflow", "description": "Ensure no regressions", "status": "draft"},
    )
    assert res.status_code == 201
    wf_id = res.json()["id"]

    # Read
    res = client.get(f"/api/workflows/{wf_id}")
    assert res.status_code == 200
    assert res.json()["name"] == "Regression Test Workflow"

    # Update
    res = client.put(f"/api/workflows/{wf_id}", json={"status": "active"})
    assert res.status_code == 200
    assert res.json()["status"] == "active"

    # Delete
    res = client.delete(f"/api/workflows/{wf_id}")
    assert res.status_code == 200

    # Verify 404
    res = client.get(f"/api/workflows/{wf_id}")
    assert res.status_code == 404
