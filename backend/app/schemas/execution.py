"""
Pydantic schemas for Workflow and Task Executions.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class TaskExecutionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    execution_id: int
    task_id: int
    status: str
    selected_agent: Optional[str] = None
    input_data: Optional[Dict[str, Any]] = None
    output_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    execution_time_ms: Optional[float] = None

    # Denormalized task fields for frontend rendering (populated via validator)
    task_name: Optional[str] = None
    order_index: int = 0
    agent_type: Optional[str] = None
    duration_seconds: Optional[float] = None

    @classmethod
    def from_orm_with_task(cls, obj) -> "TaskExecutionResponse":
        """Build response including task metadata from relationship."""
        data = {
            "id": obj.id,
            "execution_id": obj.execution_id,
            "task_id": obj.task_id,
            "status": obj.status,
            "selected_agent": obj.selected_agent,
            "input_data": obj.input_data,
            "output_data": obj.output_data,
            "error_message": obj.error_message,
            "retry_count": obj.retry_count,
            "started_at": obj.started_at,
            "completed_at": obj.completed_at,
            "execution_time_ms": obj.execution_time_ms,
        }
        if obj.task:
            data["task_name"] = obj.task.name
            data["order_index"] = obj.task.order_index or 0
            data["agent_type"] = obj.selected_agent or obj.task.agent_type
        if obj.execution_time_ms is not None:
            data["duration_seconds"] = round(obj.execution_time_ms / 1000, 3)
        return cls(**data)


class ExecutionBase(BaseModel):
    status: str = Field(default="pending", max_length=50)
    error_message: Optional[str] = None
    current_task_id: Optional[int] = None
    total_tasks: int = 0
    completed_tasks: int = 0
    execution_metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class ExecutionCreate(ExecutionBase):
    workflow_id: int


class ExecutionResponse(ExecutionBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    workflow_id: int
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    task_executions: List[TaskExecutionResponse] = Field(default_factory=list)

    @classmethod
    def from_orm_enriched(cls, obj) -> "ExecutionResponse":
        """Build execution response with enriched task_executions (task_name, order_index, agent_type)."""
        task_execs = [
            TaskExecutionResponse.from_orm_with_task(te)
            for te in (obj.task_executions or [])
        ]
        return cls(
            id=obj.id,
            workflow_id=obj.workflow_id,
            status=obj.status,
            error_message=obj.error_message,
            current_task_id=obj.current_task_id,
            total_tasks=obj.total_tasks or 0,
            completed_tasks=obj.completed_tasks or 0,
            execution_metadata=obj.execution_metadata,
            started_at=obj.started_at,
            completed_at=obj.completed_at,
            task_executions=task_execs,
        )


class WorkflowExecutionStartRequest(BaseModel):
    initial_inputs: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional initial parameters passed into the first task of the workflow",
    )
