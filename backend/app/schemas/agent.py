"""
Pydantic schemas for Step 4 Specialized AI Agents and Intelligent Routing.
"""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional, Union
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.ai import TaskAnalysisResult

AgentType = Literal["research", "content_generation", "data_analysis", "reporting"]


# ── 1. Specialized Agent Output Schemas ─────────────────────────────────────────

class ResearchAgentResult(BaseModel):
    """Structured output produced by the Specialized Research Agent."""
    model_config = ConfigDict(from_attributes=True)

    topic: str = Field(..., description="Subject or question under research")
    executive_summary: str = Field(..., description="High-level synthesis of research findings")
    key_findings: List[str] = Field(default_factory=list, description="Primary verified takeaways")
    verified_facts: List[str] = Field(
        default_factory=list,
        description="Factual information directly extracted from user-provided context",
    )
    ai_insights_and_projections: List[str] = Field(
        default_factory=list,
        description="AI-derived inferences, forward-looking insights, and recommendations clearly distinguished from facts",
    )
    sources_or_references: List[str] = Field(
        default_factory=list,
        description="User context sections, data points, or documents referenced",
    )


class ContentGenerationResult(BaseModel):
    """Structured output produced by the Specialized Content Generation Agent."""
    model_config = ConfigDict(from_attributes=True)

    content_type: str = Field(
        ...,
        description="Format of content: email, article, social_media_post, business_description, announcement",
    )
    tone_used: str = Field(
        ...,
        description="Tone applied: professional, casual, persuasive, executive, concise",
    )
    title: str = Field(..., description="Catchy title, headline, or subject line")
    body: str = Field(..., description="Full structured body content formatted with markdown")
    alternative_headlines_or_hooks: List[str] = Field(
        default_factory=list,
        description="Alternative headline ideas or hook variants",
    )
    call_to_action: Optional[str] = Field(
        default=None,
        description="Target action requested from the audience",
    )
    target_audience: Optional[str] = Field(
        default=None,
        description="Intended audience profile",
    )


class DataAnalysisResult(BaseModel):
    """Structured output produced by the Specialized Data Analysis Agent."""
    model_config = ConfigDict(from_attributes=True)

    dataset_overview: str = Field(
        ...,
        description="Description of the provided dataset, dimensions, columns, and metric types",
    )
    key_trends_and_patterns: List[str] = Field(
        default_factory=list,
        description="Patterns, upward/downward shifts, correlations observed in data",
    )
    statistical_summary: Dict[str, Any] = Field(
        default_factory=dict,
        description="Calculated and verified numbers: totals, averages, min/max, percentage changes",
    )
    anomalies_or_outliers: List[str] = Field(
        default_factory=list,
        description="Data anomalies, missing fields, or outlier spikes",
    )
    data_backed_recommendations: List[str] = Field(
        default_factory=list,
        description="Strategic business recommendations directly supported by the numerical facts",
    )


class ReportingResult(BaseModel):
    """Structured output produced by the Specialized Reporting Agent."""
    model_config = ConfigDict(from_attributes=True)

    report_title: str = Field(..., description="Formal enterprise report title")
    executive_summary: str = Field(..., description="Concise executive briefing")
    key_findings: List[str] = Field(default_factory=list, description="Core analytical findings")
    detailed_analysis: str = Field(
        ...,
        description="In-depth sectional analysis formatted in markdown",
    )
    strategic_recommendations: List[str] = Field(
        default_factory=list,
        description="Prioritized, actionable strategic recommendations",
    )
    next_steps: List[str] = Field(
        default_factory=list,
        description="Immediate tactical milestones and roadmap steps",
    )


# ── 2. Agent Metadata Schema ──────────────────────────────────────────────────

class AgentMetadata(BaseModel):
    id: AgentType
    name: str
    description: str
    supported_inputs: List[str]
    capabilities: List[str]
    output_fields: List[str]


# ── 3. API Request / Response Schemas ──────────────────────────────────────────

class AgentExecuteRequest(BaseModel):
    task_description: str = Field(
        ...,
        min_length=3,
        max_length=10000,
        description="Natural language task prompt",
    )
    data_input: Optional[str] = Field(
        default=None,
        description="Optional JSON or CSV structured dataset for data analysis or reporting",
    )
    context: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional supplemental context or domain parameters",
    )
    agent_override: Optional[AgentType] = Field(
        default=None,
        description="Optionally force execution to a specific agent instead of auto-routing",
    )
    tone: Optional[str] = Field(
        default=None,
        description="Desired tone for Content Generation Agent (e.g., professional, casual, persuasive, executive, concise)",
    )
    workflow_id: Optional[int] = Field(
        default=None,
        description="Optional workflow ID to link this execution to an existing workflow",
    )


class AgentExecutionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    task_input: str
    data_input: Optional[str] = None
    selected_agent: AgentType
    routing_reasoning: str
    status: str
    analysis: Optional[TaskAnalysisResult] = None
    output: Dict[str, Any]
    error_message: Optional[str] = None
    execution_time_ms: float
    workflow_id: Optional[int] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
