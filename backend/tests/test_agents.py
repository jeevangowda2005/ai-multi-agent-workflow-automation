"""
Automated test suite for Step 4 Specialized AI Agents & Intelligent Routing.
Covers:
- Metadata discovery (GET /api/agents)
- Unit tests for all 4 specialized agents (Research, Content, Data, Reporting)
- Intelligent routing and conditional graph execution across categories
- Manual agent override
- Input validation and 404 / 422 error handling
- Database persistence in agent_executions table (GET /api/agents/executions/{id})
- Conditional real Gemini API execution (with reporting of mock vs real)
"""

import json
import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import get_settings
from app.agents.specialized.research_agent import run_research_agent
from app.agents.specialized.content_agent import run_content_agent
from app.agents.specialized.data_agent import run_data_agent
from app.agents.specialized.reporting_agent import run_reporting_agent
from app.agents.router_agent import run_intelligent_router
from app.schemas.ai import TaskAnalysisResult
from app.schemas.agent import (
    ResearchAgentResult,
    ContentGenerationResult,
    DataAnalysisResult,
    ReportingResult,
)


@pytest.fixture
def client():
    return TestClient(app)


# ── 1. Metadata Endpoint ──────────────────────────────────────────────────────

def test_get_agents_metadata(client):
    """GET /api/agents should return all 4 specialized agents with schemas and capabilities."""
    res = client.get("/api/agents")
    assert res.status_code == 200
    agents = res.json()
    assert len(agents) == 4
    agent_ids = {a["id"] for a in agents}
    assert agent_ids == {"research", "content_generation", "data_analysis", "reporting"}
    for agent in agents:
        assert len(agent["capabilities"]) > 0
        assert len(agent["output_fields"]) > 0
        assert len(agent["supported_inputs"]) > 0


# ── 2. Specialized Agents Unit Tests (Mocked) ─────────────────────────────────

@pytest.mark.asyncio
async def test_research_agent_mocked():
    """Verify Research Agent generates structured output separating facts and AI projections."""
    mock_response = {
        "topic": "Zero Trust Architecture Adoption in Enterprise Cloud",
        "executive_summary": "Adoption of Zero Trust has accelerated due to remote work and cloud migration.",
        "key_findings": [
            "Microsegmentation reduces lateral attack surface by up to 70%.",
            "Identity-first security architecture is the primary adoption driver."
        ],
        "verified_facts": [
            "Source document states identity verification is required at every hop.",
            "Legacy VPNs lack continuous authentication capabilities."
        ],
        "ai_insights_and_projections": [
            "By 2027, automated policy generation via AI will replace static access rules.",
            "Continuous behavioural biometrics may become standard in tier-1 financial systems."
        ],
        "sources_or_references": [
            "Internal Security Whitepaper 2026.pdf",
            "Context Section 4: Authentication"
        ]
    }

    async def mock_llm(_):
        return json.dumps(mock_response)

    result = await run_research_agent(
        task_description="Research Zero Trust enterprise adoption",
        context={"document": "Security Whitepaper 2026"},
        llm_callable=mock_llm,
    )

    assert isinstance(result, ResearchAgentResult)
    assert result.topic == mock_response["topic"]
    assert len(result.verified_facts) == 2
    assert len(result.ai_insights_and_projections) == 2
    assert len(result.sources_or_references) == 2


@pytest.mark.asyncio
async def test_content_agent_mocked():
    """Verify Content Generation Agent produces structured content matching specified tone."""
    mock_response = {
        "content_type": "email",
        "tone_used": "persuasive",
        "title": "Unlock 10x Efficiency with AI Multi-Agent Workflows",
        "body": "Dear Enterprise Leader,\n\nAutomate complex workflows seamlessly with our new agentic platform...",
        "alternative_headlines_or_hooks": [
            "Transform your business operations with autonomous agents",
            "The future of intelligent workflow automation is here"
        ],
        "call_to_action": "Schedule a 15-minute executive demo today",
        "target_audience": "Chief Technology Officers and VPs of Engineering"
    }

    async def mock_llm(_):
        return json.dumps(mock_response)

    result = await run_content_agent(
        task_description="Write an outreach email for enterprise automation platform",
        tone="persuasive",
        llm_callable=mock_llm,
    )

    assert isinstance(result, ContentGenerationResult)
    assert result.content_type == "email"
    assert result.tone_used == "persuasive"
    assert "Unlock 10x" in result.title
    assert len(result.alternative_headlines_or_hooks) == 2


@pytest.mark.asyncio
async def test_data_agent_mocked_csv():
    """Verify Data Analysis Agent analyzes CSV dataset without numerical hallucination."""
    csv_data = "Region,Revenue,Target,Achieved\nNorth,120000,100000,Yes\nSouth,85000,90000,No\nEast,145000,130000,Yes\nWest,70000,80000,No"
    
    mock_response = {
        "dataset_overview": "Regional sales dataset covering 4 operating territories with targets and achievements.",
        "key_trends_and_patterns": [
            "North and East exceeded their targets, contributing 63% of total revenue.",
            "South and West underperformed by an aggregate of $15,000."
        ],
        "statistical_summary": {
            "total_revenue": "$420,000",
            "average_revenue": "$105,000",
            "target_achievement_rate": "50% (2 of 4 regions)"
        },
        "anomalies_or_outliers": [
            "West territory lagged behind target by 12.5%."
        ],
        "data_backed_recommendations": [
            "Reallocate Q4 field marketing spend to South and West territories to close the gap.",
            "Document East territory's sales playbook for regional cross-training."
        ]
    }

    async def mock_llm(_):
        return json.dumps(mock_response)

    result = await run_data_agent(
        task_description="Analyze regional sales performance CSV and provide recommendations",
        data_input=csv_data,
        llm_callable=mock_llm,
    )

    assert isinstance(result, DataAnalysisResult)
    assert "4 operating territories" in result.dataset_overview
    assert result.statistical_summary["total_revenue"] == "$420,000"
    assert len(result.data_backed_recommendations) == 2


@pytest.mark.asyncio
async def test_reporting_agent_mocked():
    """Verify Reporting Agent synthesizes findings into an executive report."""
    mock_response = {
        "report_title": "Q3 Infrastructure Reliability & Performance Briefing",
        "executive_summary": "System availability reached 99.98% during Q3, meeting all enterprise SLAs.",
        "key_findings": [
            "P99 API latency decreased by 34% following caching layer deployment.",
            "Database connection pooling resolved intermittent weekend timeout spikes."
        ],
        "detailed_analysis": "### Infrastructure Overview\nDuring Q3, overall request volume increased by 42%...",
        "strategic_recommendations": [
            "Complete multi-region failover testing before peak holiday load.",
            "Increase automated anomaly detection thresholds in alerting stack."
        ],
        "next_steps": [
            "Initiate chaos engineering drill on staging cluster by Nov 15",
            "Publish post-mortem report for sprint 41 outage"
        ]
    }

    async def mock_llm(_):
        return json.dumps(mock_response)

    result = await run_reporting_agent(
        task_description="Generate Q3 infrastructure reliability executive report",
        llm_callable=mock_llm,
    )

    assert isinstance(result, ReportingResult)
    assert result.report_title == mock_response["report_title"]
    assert len(result.key_findings) == 2
    assert len(result.next_steps) == 2


# ── 3. Intelligent Router StateGraph Tests (Mocked) ───────────────────────────

@pytest.mark.asyncio
async def test_router_research_routing_mocked():
    """Verify router automatically selects Research Agent for research category task."""
    analysis = TaskAnalysisResult(
        task_intent="Examine quantum encryption developments in financial services",
        category="research",
        priority="high",
        complexity="moderate",
        recommended_action="Execute research agent pipeline",
        explanation="Deep research requirement across technical literature.",
        suggested_subtasks=["Survey NIST post-quantum standards", "Assess migration timeline"],
    )

    research_output = {
        "topic": "Quantum Encryption in FinTech",
        "executive_summary": "Post-quantum cryptography migration is essential by 2030.",
        "key_findings": ["NIST finalized initial PQC standards."],
        "verified_facts": ["NIST standard published in 2024."],
        "ai_insights_and_projections": ["Early adopters will gain significant trust advantage."],
        "sources_or_references": ["NIST PQC Standardization Roadmap"]
    }

    call_count = 0

    async def mock_llm(prompt):
        nonlocal call_count
        call_count += 1
        if "analyze this business task" in prompt.lower():
            return json.dumps(analysis.model_dump())
        return json.dumps(research_output)

    state = await run_intelligent_router(
        task_description="Research post-quantum encryption standards for banking sector",
        llm_callable=mock_llm,
    )

    assert state["selected_agent"] == "research"
    assert state["agent_output"]["topic"] == "Quantum Encryption in FinTech"
    assert "research_agent_success" in state["execution_log"]


@pytest.mark.asyncio
async def test_router_content_generation_routing_mocked():
    """Verify router automatically routes writing tasks to Content Generation Agent."""
    analysis = TaskAnalysisResult(
        task_intent="Draft an announcement post for new AI feature launch",
        category="content_generation",
        priority="medium",
        complexity="simple",
        recommended_action="Generate announcement copy",
        explanation="Copywriting and external messaging task.",
        suggested_subtasks=["Draft headline", "Draft body copy"],
    )

    content_output = {
        "content_type": "article",
        "tone_used": "executive",
        "title": "Introducing Autonomous Multi-Agent Workflows",
        "body": "Today we are excited to announce our next-generation enterprise automation engine...",
        "alternative_headlines_or_hooks": ["Next-gen AI workflows are here"],
        "call_to_action": "Read the documentation",
        "target_audience": "Enterprise developers"
    }

    async def mock_llm(prompt):
        if "analyze this business task" in prompt.lower():
            return json.dumps(analysis.model_dump())
        return json.dumps(content_output)

    state = await run_intelligent_router(
        task_description="Write an official announcement article for our multi-agent platform launch",
        tone="executive",
        llm_callable=mock_llm,
    )

    assert state["selected_agent"] == "content_generation"
    assert state["agent_output"]["content_type"] == "article"
    assert "content_agent_success" in state["execution_log"]


@pytest.mark.asyncio
async def test_router_manual_override():
    """Verify agent_override bypasses Task Analysis routing and invokes the chosen agent directly."""
    reporting_output = {
        "report_title": "Forced Reporting Audit",
        "executive_summary": "Manually routed reporting briefing.",
        "key_findings": ["Manual routing confirmed."],
        "detailed_analysis": "### Analysis\nExecution proceeded directly to reporting.",
        "strategic_recommendations": ["Maintain override capability."],
        "next_steps": ["Verify in integration test."]
    }

    async def mock_llm(_):
        return json.dumps(reporting_output)

    state = await run_intelligent_router(
        task_description="Summarize status of sprint backlog",
        agent_override="reporting",
        llm_callable=mock_llm,
    )

    assert state["selected_agent"] == "reporting"
    assert "router_manual_override:reporting" in state["execution_log"]
    assert state["agent_output"]["report_title"] == "Forced Reporting Audit"


# ── 4. API Endpoints & DB Persistence Tests ───────────────────────────────────

def test_execute_agent_input_validation_empty(client):
    """Submitting empty or short task description returns 422 Unprocessable Entity."""
    res = client.post(
        "/api/agents/execute",
        json={"task_description": "no"}
    )
    assert res.status_code == 422


def test_execute_agent_invalid_workflow_id(client):
    """Submitting a non-existent workflow_id returns 404 before calling AI."""
    res = client.post(
        "/api/agents/execute",
        json={"task_description": "Analyze operational metrics", "workflow_id": 999999}
    )
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()


def test_execute_agent_database_persistence(client):
    """POST /api/agents/execute persists record in PostgreSQL and is retrievable via GET /api/agents/executions/{id}."""
    mock_research_output = {
        "topic": "Microservice Distributed Tracing",
        "executive_summary": "OpenTelemetry is the leading standard for microservice observability.",
        "key_findings": ["OTel provides vendor-neutral instrumentation."],
        "verified_facts": ["OpenTelemetry is an active CNCF project."],
        "ai_insights_and_projections": ["eBPF will increasingly automate tracing without code changes."],
        "sources_or_references": ["CNCF Observability Whitepaper"]
    }

    mock_state = {
        "selected_agent": "research",
        "routing_reasoning": "Auto-routed to research based on task intent.",
        "task_analysis": TaskAnalysisResult(
            task_intent="Research distributed tracing alternatives",
            category="research",
            priority="medium",
            complexity="moderate",
            recommended_action="Execute research agent",
            explanation="Technical evaluation requirement.",
            suggested_subtasks=["Compare OpenTelemetry vs Jaeger native"],
        ),
        "agent_output": mock_research_output,
        "execution_log": ["router_started", "routed_to:research", "research_agent_success"],
    }

    with patch("app.core.config.Settings.is_gemini_configured", True):
        with patch("app.api.routes.agents.run_intelligent_router", new=AsyncMock(return_value=mock_state)):
            # 1. Execute
            exec_res = client.post(
                "/api/agents/execute",
                json={"task_description": "Research best distributed tracing frameworks for Kubernetes"}
            )
            assert exec_res.status_code == 200
            data = exec_res.json()
            assert data["selected_agent"] == "research"
            assert data["status"] == "completed"
            assert data["output"]["topic"] == "Microservice Distributed Tracing"
            exec_id = data["id"]
            assert isinstance(exec_id, int)

            # 2. Retrieve by ID (GET /api/agents/executions/{id})
            get_res = client.get(f"/api/agents/executions/{exec_id}")
            assert get_res.status_code == 200
            fetched = get_res.json()
            assert fetched["id"] == exec_id
            assert fetched["selected_agent"] == "research"
            assert fetched["status"] == "completed"
            assert fetched["output"]["topic"] == "Microservice Distributed Tracing"

            # 3. Retrieve list (GET /api/agents/executions)
            list_res = client.get("/api/agents/executions")
            assert list_res.status_code == 200
            items = list_res.json()
            matching = [item for item in items if item["id"] == exec_id]
            assert len(matching) == 1


# ── 5. Real Gemini API Execution Test (Conditional) ───────────────────────────

@pytest.mark.asyncio
async def test_live_gemini_agent_execution():
    """
    Real end-to-end execution using live Google Gemini API.
    Only executed if GEMINI_API_KEY is configured.
    Tests intelligent routing, specialized agent output, and schema compliance.
    """
    settings = get_settings()
    if not settings.is_gemini_configured:
        pytest.skip(
            "[MOCK ONLY] Real Gemini API test skipped: GEMINI_API_KEY not configured. "
            "Mocked tests validated all agent logic."
        )

    print(f"\n[REAL GEMINI] Testing intelligent router using model: {settings.gemini_model}")
    try:
        state = await run_intelligent_router(
            task_description="Analyze customer feedback trends and identify the top recurring complaints.",
            data_input="Ticket_ID,Issue_Category,Wait_Time_Min,CSAT\n101,Billing,45,2\n102,Product Bug,12,3\n103,Billing,55,1\n104,Feature Request,8,5\n105,Billing,60,1",
        )
        assert state.get("selected_agent") in ("data_analysis", "research", "reporting")
        assert state.get("agent_output") is not None
        print(f"[REAL GEMINI] Successfully routed to: {state['selected_agent']}")
        print(f"[REAL GEMINI] Output keys: {list(state['agent_output'].keys())}")
    except ValueError as exc:
        if "rate limit" in str(exc).lower() or "quota" in str(exc).lower():
            pytest.skip(f"Gemini API free tier rate limit reached: {exc}")
        raise

