"""
AI Agent API endpoints.
Provides intelligent task analysis using Google Gemini and LangGraph.
"""

import time
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.schemas.ai import (
    TaskAnalysisRequest,
    TaskAnalysisResponse,
    AIHealthResponse,
)
from app.schemas.task import TaskCreate
from app.services import gemini_service, workflow_service
from app.agents.task_analyzer import run_task_analysis_agent

router = APIRouter(prefix="/ai", tags=["ai"])


@router.get(
    "/health",
    response_model=AIHealthResponse,
    summary="Check AI configuration readiness",
)
def check_ai_health():
    """
    Checks whether Gemini API is configured and ready without making paid API calls
    or exposing secret keys.
    """
    settings = get_settings()
    configured = settings.is_gemini_configured

    if configured:
        return AIHealthResponse(
            status="ready",
            model=settings.gemini_model,
            api_key_configured=True,
            message=f"Gemini API is ready using model '{settings.gemini_model}'.",
        )
    else:
        return AIHealthResponse(
            status="unconfigured",
            model=settings.gemini_model,
            api_key_configured=False,
            message=(
                "GEMINI_API_KEY is not configured or using the default placeholder in backend/.env. "
                "Please configure a valid API key to enable live AI task analysis."
            ),
        )


@router.post(
    "/analyze",
    response_model=TaskAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Analyze a business task with the AI agent",
)
async def analyze_task(
    request: TaskAnalysisRequest,
    db: Session = Depends(get_db),
):
    """
    Executes the Intelligent Task Analysis Agent against a user-provided task.
    Classifies intent, category, priority, complexity, and recommends next actions.
    If workflow_id is provided, stores the result as a task in that workflow.
    """
    settings = get_settings()

    # 1. Verify workflow exists first if workflow_id was provided
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
            detail=(
                "Gemini API key is not configured. "
                "Please add a valid GEMINI_API_KEY in backend/.env to use the AI Task Analyzer."
            ),
        )

    # 3. Execute LangGraph agent
    start_time = time.perf_counter()
    try:
        analysis_result = await run_task_analysis_agent(
            task_description=request.task_description,
            context=request.context,
        )
    except gemini_service.GeminiNotConfiguredError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except gemini_service.GeminiRateLimitError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(exc),
        ) from exc
    except gemini_service.GeminiTimeoutError as exc:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=str(exc),
        ) from exc
    except gemini_service.GeminiAPIError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI provider failure: {str(exc)}",
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal agent execution error: {str(exc)}",
        ) from exc

    elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)

    # 4. If workflow_id provided, persist as an associated task
    saved_task_id: Optional[int] = None
    if request.workflow_id is not None:
        task_in = TaskCreate(
            name=f"AI Analysis: {analysis_result.category.replace('_', ' ').title()}",
            task_type="llm",
            status="completed",
            input_data={
                "task_description": request.task_description,
                "context": request.context or {},
            },
            output_data=analysis_result.model_dump(),
        )
        saved_task = workflow_service.create_task(
            db=db,
            workflow_id=request.workflow_id,
            task_in=task_in,
        )
        saved_task_id = saved_task.id

    return TaskAnalysisResponse(
        success=True,
        analysis=analysis_result,
        workflow_id=request.workflow_id,
        saved_task_id=saved_task_id,
        model_used=settings.gemini_model,
        execution_time_ms=elapsed_ms,
    )
