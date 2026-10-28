"""
API endpoints for Step 4 Specialized AI Agents and Intelligent Task Routing.
"""

import time
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.models.agent_execution import AgentExecution
from app.schemas.agent import (
    AgentExecuteRequest,
    AgentExecutionResponse,
    AgentMetadata,
)
from app.services import gemini_service, workflow_service
from app.agents.router_agent import run_intelligent_router

router = APIRouter(prefix="/agents", tags=["agents"])

# Static Agent Metadata Registry
AVAILABLE_AGENTS: List[AgentMetadata] = [
    AgentMetadata(
        id="research",
        name="Research Agent",
        description="Analyzes research queries, extracts verified facts from user context, and produces structured summaries with clearly distinguished AI projections.",
        supported_inputs=["Natural language queries", "User background context", "Document excerpts"],
        capabilities=[
            "Strict fact-vs-hypothesis separation",
            "Contextual synthesis",
            "Forward-looking strategic projections",
            "Reference and source citation",
        ],
        output_fields=[
            "topic",
            "executive_summary",
            "key_findings",
            "verified_facts",
            "ai_insights_and_projections",
            "sources_or_references",
        ],
    ),
    AgentMetadata(
        id="content_generation",
        name="Content Generation Agent",
        description="Generates professional emails, articles, social media posts, corporate announcements, and business copy across multiple writing tones.",
        supported_inputs=["Task description", "Writing tone specification", "Target audience profile"],
        capabilities=[
            "Tone adaptation (professional, executive, persuasive, casual, concise)",
            "Alternative headline and hook generation",
            "Call-to-action formulation",
            "Markdown-formatted copywriting",
        ],
        output_fields=[
            "content_type",
            "tone_used",
            "title",
            "body",
            "alternative_headlines_or_hooks",
            "call_to_action",
            "target_audience",
        ],
    ),
    AgentMetadata(
        id="data_analysis",
        name="Data Analysis Agent",
        description="Parses CSV and JSON datasets to identify empirical trends, calculate verified statistics, and formulate data-backed recommendations without hallucinating numbers.",
        supported_inputs=["CSV data text", "JSON array/object data", "Tabular metrics"],
        capabilities=[
            "Zero numerical hallucination guarantee",
            "Ground-truth statistical extraction",
            "Trend and correlation detection",
            "Anomaly and missing value auditing",
            "Data-backed business recommendations",
        ],
        output_fields=[
            "dataset_overview",
            "key_trends_and_patterns",
            "statistical_summary",
            "anomalies_or_outliers",
            "data_backed_recommendations",
        ],
    ),
    AgentMetadata(
        id="reporting",
        name="Enterprise Reporting Agent",
        description="Synthesizes multi-source findings, analytical outputs, and project requirements into formal, publication-ready enterprise briefings.",
        supported_inputs=["Multi-agent findings", "Project logs", "Metrics summaries"],
        capabilities=[
            "Executive briefings and summaries",
            "Structured markdown sectional breakdown",
            "Prioritized strategic recommendations",
            "Tactical milestone roadmap",
        ],
        output_fields=[
            "report_title",
            "executive_summary",
            "key_findings",
            "detailed_analysis",
            "strategic_recommendations",
            "next_steps",
        ],
    ),
]


@router.get(
    "",
    response_model=List[AgentMetadata],
    summary="List all available specialized AI agents",
)
def list_available_agents():
    """Returns catalog of all registered specialized AI agents with capabilities and schemas."""
    return AVAILABLE_AGENTS


@router.post(
    "/execute",
    response_model=AgentExecutionResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute a task using intelligent multi-agent routing",
)
async def execute_agent_task(
    request: AgentExecuteRequest,
    db: Session = Depends(get_db),
):
    """
    Intelligently routes a business task to the appropriate specialized agent
    (Research, Content Generation, Data Analysis, Reporting) or executes user's chosen override.
    Saves execution lifecycle and output into PostgreSQL.
    """
    settings = get_settings()

    # 1. Verify workflow if workflow_id provided
    if request.workflow_id is not None:
        workflow = workflow_service.get_workflow(db, request.workflow_id)
        if not workflow:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workflow with ID {request.workflow_id} not found.",
            )

    # 2. Check Gemini configuration readiness
    if not settings.is_gemini_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Gemini API is not configured. Please configure GEMINI_API_KEY in backend/.env",
        )

    # 3. Create initial database record
    db_exec = AgentExecution(
        task_input=request.task_description,
        data_input=request.data_input,
        selected_agent=request.agent_override or "auto-routing",
        status="running",
        workflow_id=request.workflow_id,
    )
    db.add(db_exec)
    db.commit()
    db.refresh(db_exec)

    start_time = time.perf_counter()

    # 4. Execute LangGraph Intelligent Router
    try:
        final_state = await run_intelligent_router(
            task_description=request.task_description,
            data_input=request.data_input,
            context=request.context,
            agent_override=request.agent_override,
            tone=request.tone,
        )
    except gemini_service.GeminiNotConfiguredError as exc:
        db_exec.status = "failed"
        db_exec.error_message = str(exc)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except gemini_service.GeminiRateLimitError as exc:
        db_exec.status = "failed"
        db_exec.error_message = str(exc)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(exc),
        ) from exc
    except gemini_service.GeminiTimeoutError as exc:
        db_exec.status = "failed"
        db_exec.error_message = str(exc)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=str(exc),
        ) from exc
    except gemini_service.GeminiAPIError as exc:
        db_exec.status = "failed"
        db_exec.error_message = str(exc)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI Provider error: {str(exc)}",
        ) from exc
    except ValueError as exc:
        db_exec.status = "failed"
        db_exec.error_message = str(exc)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        db_exec.status = "failed"
        db_exec.error_message = str(exc)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Execution error: {str(exc)}",
        ) from exc

    elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)

    # 5. Update record with results
    analysis_dict = None
    if final_state.get("task_analysis"):
        analysis_dict = final_state["task_analysis"].model_dump()

    db_exec.selected_agent = final_state.get("selected_agent") or "unknown"
    db_exec.status = "completed"
    db_exec.analysis_result = analysis_dict
    db_exec.output_data = final_state.get("agent_output")
    db_exec.execution_time_ms = elapsed_ms
    db_exec.completed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(db_exec)

    return AgentExecutionResponse(
        id=db_exec.id,
        task_input=db_exec.task_input,
        data_input=db_exec.data_input,
        selected_agent=db_exec.selected_agent,
        routing_reasoning=final_state.get("routing_reasoning") or "Auto-routed by Task Analysis",
        status=db_exec.status,
        analysis=final_state.get("task_analysis"),
        output=db_exec.output_data or {},
        error_message=db_exec.error_message,
        execution_time_ms=elapsed_ms,
        workflow_id=db_exec.workflow_id,
        created_at=db_exec.created_at,
        completed_at=db_exec.completed_at,
    )


@router.get(
    "/executions",
    response_model=List[AgentExecutionResponse],
    summary="List recent agent executions",
)
def list_agent_executions(
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """Returns recent agent executions for history logs."""
    records = (
        db.query(AgentExecution)
        .order_by(AgentExecution.id.desc())
        .limit(min(limit, 100))
        .all()
    )
    results = []
    for r in records:
        results.append(
            AgentExecutionResponse(
                id=r.id,
                task_input=r.task_input,
                data_input=r.data_input,
                selected_agent=r.selected_agent,
                routing_reasoning=(
                    r.analysis_result.get("explanation")
                    if r.analysis_result
                    else "Auto-routed"
                ),
                status=r.status,
                analysis=r.analysis_result,
                output=r.output_data or {},
                error_message=r.error_message,
                execution_time_ms=r.execution_time_ms or 0.0,
                workflow_id=r.workflow_id,
                created_at=r.created_at,
                completed_at=r.completed_at,
            )
        )
    return results


@router.get(
    "/executions/{execution_id}",
    response_model=AgentExecutionResponse,
    summary="Retrieve execution results by ID",
)
def get_agent_execution(
    execution_id: int,
    db: Session = Depends(get_db),
):
    """Fetches details and structured output of a specific agent execution."""
    r = db.query(AgentExecution).filter(AgentExecution.id == execution_id).first()
    if not r:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent execution with ID {execution_id} not found.",
        )

    return AgentExecutionResponse(
        id=r.id,
        task_input=r.task_input,
        data_input=r.data_input,
        selected_agent=r.selected_agent,
        routing_reasoning=(
            r.analysis_result.get("explanation")
            if r.analysis_result
            else "Auto-routed"
        ),
        status=r.status,
        analysis=r.analysis_result,
        output=r.output_data or {},
        error_message=r.error_message,
        execution_time_ms=r.execution_time_ms or 0.0,
        workflow_id=r.workflow_id,
        created_at=r.created_at,
        completed_at=r.completed_at,
    )
