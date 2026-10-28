"""
Pydantic schemas for Workflow.
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.task import TaskResponse
from app.schemas.execution import ExecutionResponse


class WorkflowBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Name of the workflow")
    description: Optional[str] = Field(None, description="Detailed description of the workflow")
    status: str = Field(default="draft", max_length=50, description="Workflow status (e.g., draft, active, paused)")


class WorkflowCreate(WorkflowBase):
    pass


class WorkflowUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    status: Optional[str] = Field(None, max_length=50)


class WorkflowResponse(WorkflowBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
    tasks_count: Optional[int] = 0


class WorkflowDetailResponse(WorkflowResponse):
    tasks: List[TaskResponse] = []
    executions: List[ExecutionResponse] = []
