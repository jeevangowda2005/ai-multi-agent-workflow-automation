"""
Pydantic schemas for AI Report Generation.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class ReportGenerateRequest(BaseModel):
    execution_id: int = Field(..., description="ID of completed workflow execution to report on")
    title: Optional[str] = Field(default=None, description="Optional custom title for the report")
    notes: Optional[str] = Field(default=None, description="Optional instructions or focus points for the report")


class ReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    execution_id: int
    workflow_id: int
    workflow_name: Optional[str] = None
    title: str
    executive_summary: str
    findings: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    next_steps: List[str] = Field(default_factory=list)
    detailed_analysis: Optional[str] = None
    raw_markdown: str
    task_outcomes: List[Dict[str, Any]] = Field(default_factory=list)
    generated_by_agent: str
    created_at: datetime


class ReportListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    execution_id: int
    workflow_id: int
    workflow_name: Optional[str] = None
    title: str
    executive_summary: str
    findings_count: int = 0
    recommendations_count: int = 0
    created_at: datetime
