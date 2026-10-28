"""
Pydantic schemas for Task.
"""

from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict, Field


class TaskBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Name of the task")
    task_type: str = Field(default="action", max_length=100, description="Type of task (e.g., action, llm, condition, webhook)")
    status: str = Field(default="pending", max_length=50, description="Status of the task")
    input_data: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Input parameters as JSON")
    output_data: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Output results as JSON")
    order_index: int = Field(default=0, description="Sequential execution index")
    agent_type: Optional[str] = Field(default=None, description="Assigned agent (research, content_generation, data_analysis, reporting, or null for auto)")
    max_retries: int = Field(default=0, description="Maximum retry attempts on failure")
    timeout_seconds: int = Field(default=60, description="Timeout in seconds")
    depends_on_task_id: Optional[int] = Field(default=None, description="Parent task ID that must complete first")


class TaskCreate(TaskBase):
    pass


class TaskUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    task_type: Optional[str] = Field(None, max_length=100)
    status: Optional[str] = Field(None, max_length=50)
    input_data: Optional[Dict[str, Any]] = None
    output_data: Optional[Dict[str, Any]] = None
    order_index: Optional[int] = None
    agent_type: Optional[str] = None
    max_retries: Optional[int] = None
    timeout_seconds: Optional[int] = None
    depends_on_task_id: Optional[int] = None


class TaskResponse(TaskBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    workflow_id: int
    created_at: datetime

