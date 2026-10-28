"""
Pydantic schemas for AI Task Analysis.
"""

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field

TaskCategory = Literal["research", "reporting", "content_generation", "data_analysis", "general"]
TaskPriority = Literal["low", "medium", "high", "critical"]
TaskComplexity = Literal["simple", "moderate", "complex"]


class TaskAnalysisResult(BaseModel):
    """Structured output produced by the Intelligent Task Analysis Agent."""
    model_config = ConfigDict(from_attributes=True)

    task_intent: str = Field(
        ...,
        description="Clear interpretation of the user's underlying intent and core objective",
    )
    category: TaskCategory = Field(
        ...,
        description="Classified category: research, reporting, content_generation, data_analysis, or general",
    )
    priority: TaskPriority = Field(
        ...,
        description="Estimated priority: low, medium, high, or critical",
    )
    complexity: TaskComplexity = Field(
        ...,
        description="Complexity level: simple, moderate, or complex",
    )
    recommended_action: str = Field(
        ...,
        description="Specific recommended next step or agent pipeline to execute",
    )
    explanation: str = Field(
        ...,
        description="Brief concise rationale justifying the classification and recommendation",
    )
    suggested_subtasks: List[str] = Field(
        default_factory=list,
        description="List of actionable subtasks breaking down the business requirement",
    )


class TaskAnalysisRequest(BaseModel):
    """Payload submitted to POST /api/ai/analyze."""
    task_description: str = Field(
        ...,
        min_length=3,
        max_length=5000,
        description="Natural language description of the business task",
        examples=["Analyze Q3 sales performance by region and summarize top 3 underperforming categories"],
    )
    workflow_id: Optional[int] = Field(
        default=None,
        description="Optional workflow ID to persist this analysis as an associated task",
    )
    context: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional supplemental context or domain parameters",
    )


class TaskAnalysisResponse(BaseModel):
    """Response returned by POST /api/ai/analyze."""
    success: bool = True
    analysis: TaskAnalysisResult
    workflow_id: Optional[int] = None
    saved_task_id: Optional[int] = None
    model_used: str
    execution_time_ms: float


class AIHealthResponse(BaseModel):
    """Response returned by GET /api/ai/health."""
    status: Literal["ready", "unconfigured", "error"]
    model: str
    api_key_configured: bool
    message: str
