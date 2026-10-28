"""
Workflow management API endpoints.
Provides CRUD for workflows and nested task creation/listing.
"""

import asyncio
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.execution import Execution
from app.schemas.workflow import (
    WorkflowCreate,
    WorkflowUpdate,
    WorkflowResponse,
    WorkflowDetailResponse,
)
from app.schemas.task import TaskCreate, TaskUpdate, TaskResponse
from app.schemas.execution import ExecutionResponse, WorkflowExecutionStartRequest
from app.services import workflow_service, execution_engine

router = APIRouter(prefix="/workflows", tags=["workflows"])


@router.get(
    "/templates",
    summary="List pre-built workflow templates",
)
def list_workflow_templates():
    """Returns available reusable workflow templates."""
    return workflow_service.WORKFLOW_TEMPLATES


@router.post(
    "/templates/{template_id}/instantiate",
    response_model=WorkflowDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create workflow from a pre-built template",
)
def instantiate_template(
    template_id: str,
    custom_name: Optional[str] = Query(None, description="Optional custom name for the workflow"),
    db: Session = Depends(get_db),
):
    """Instantiates a full executable workflow with tasks configured from a template."""
    try:
        wf = workflow_service.create_workflow_from_template(
            db=db, template_id=template_id, custom_name=custom_name
        )
        return wf
    except ValueError as val_err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(val_err))


@router.post(
    "",
    response_model=WorkflowResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new workflow",
)
def create_workflow(
    workflow_in: WorkflowCreate,
    db: Session = Depends(get_db),
):
    """Create a new workflow record."""
    return workflow_service.create_workflow(db=db, workflow_in=workflow_in)


@router.get(
    "",
    response_model=List[WorkflowResponse],
    summary="List workflows",
)
def list_workflows(
    skip: int = Query(0, ge=0, description="Offset for pagination"),
    limit: int = Query(100, ge=1, le=500, description="Max number of items to return"),
    status: Optional[str] = Query(None, description="Filter by status (e.g. draft, active, paused)"),
    search: Optional[str] = Query(None, description="Filter by name substring"),
    db: Session = Depends(get_db),
):
    """Retrieve all workflows, ordered newest first."""
    return workflow_service.list_workflows(
        db=db, skip=skip, limit=limit, status=status, search=search
    )


@router.get(
    "/{workflow_id}",
    response_model=WorkflowDetailResponse,
    summary="Get workflow details",
)
def get_workflow(
    workflow_id: int,
    db: Session = Depends(get_db),
):
    """Retrieve full details of a specific workflow, including its tasks and executions."""
    workflow = workflow_service.get_workflow(db=db, workflow_id=workflow_id)
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow with ID {workflow_id} not found",
        )
    return workflow


@router.put(
    "/{workflow_id}",
    response_model=WorkflowResponse,
    summary="Update a workflow",
)
def update_workflow(
    workflow_id: int,
    workflow_in: WorkflowUpdate,
    db: Session = Depends(get_db),
):
    """Update workflow attributes."""
    workflow = workflow_service.get_workflow(db=db, workflow_id=workflow_id)
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow with ID {workflow_id} not found",
        )
    return workflow_service.update_workflow(
        db=db, workflow=workflow, workflow_in=workflow_in
    )


@router.delete(
    "/{workflow_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a workflow",
)
def delete_workflow(
    workflow_id: int,
    db: Session = Depends(get_db),
):
    """Delete a workflow and cascade delete all its tasks and execution logs."""
    workflow = workflow_service.get_workflow(db=db, workflow_id=workflow_id)
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow with ID {workflow_id} not found",
        )
    workflow_service.delete_workflow(db=db, workflow=workflow)
    return {
        "success": True,
        "message": f"Workflow {workflow_id} deleted successfully",
        "id": workflow_id,
    }


@router.post(
    "/{workflow_id}/tasks",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a task to a workflow",
)
def add_task_to_workflow(
    workflow_id: int,
    task_in: TaskCreate,
    db: Session = Depends(get_db),
):
    """Add a new task node to the designated workflow."""
    workflow = workflow_service.get_workflow(db=db, workflow_id=workflow_id)
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow with ID {workflow_id} not found",
        )
    return workflow_service.create_task(
        db=db, workflow_id=workflow_id, task_in=task_in
    )


@router.get(
    "/{workflow_id}/tasks",
    response_model=List[TaskResponse],
    summary="List all tasks for a workflow",
)
def list_workflow_tasks(
    workflow_id: int,
    db: Session = Depends(get_db),
):
    """List all tasks associated with a workflow."""
    workflow = workflow_service.get_workflow(db=db, workflow_id=workflow_id)
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow with ID {workflow_id} not found",
        )
    return workflow_service.list_tasks_for_workflow(db=db, workflow_id=workflow_id)


@router.put(
    "/{workflow_id}/tasks/{task_id}",
    response_model=TaskResponse,
    summary="Update task configuration, ordering, or dependencies",
)
def update_task(
    workflow_id: int,
    task_id: int,
    task_in: TaskUpdate,
    db: Session = Depends(get_db),
):
    """Updates a task within a workflow, with circular dependency prevention."""
    task = workflow_service.get_task(db=db, task_id=task_id)
    if not task or task.workflow_id != workflow_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task #{task_id} not found in workflow #{workflow_id}",
        )

    # Circular dependency validation
    if task_in.depends_on_task_id is not None:
        if workflow_service.check_circular_dependency(
            db=db,
            workflow_id=workflow_id,
            task_id=task_id,
            depends_on_id=task_in.depends_on_task_id,
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Circular dependency detected! Task #{task_id} cannot depend on Task #{task_in.depends_on_task_id}.",
            )

    return workflow_service.update_task(db=db, task=task, task_in=task_in)


@router.delete(
    "/{workflow_id}/tasks/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a task from a workflow",
)
def delete_task(
    workflow_id: int,
    task_id: int,
    db: Session = Depends(get_db),
):
    """Deletes a task node and resets downstream dependencies."""
    task = workflow_service.get_task(db=db, task_id=task_id)
    if not task or task.workflow_id != workflow_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task #{task_id} not found in workflow #{workflow_id}",
        )
    workflow_service.delete_task(db=db, task=task)
    return None


@router.post(
    "/{workflow_id}/execute",
    response_model=ExecutionResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Start workflow execution",
)
async def execute_workflow(
    workflow_id: int,
    request: Optional[WorkflowExecutionStartRequest] = None,
    db: Session = Depends(get_db),
):
    """
    Executes all tasks in the workflow sequentially according to order_index.
    Prevents duplicate concurrent executions of the same workflow.
    """
    workflow = workflow_service.get_workflow(db=db, workflow_id=workflow_id)
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow with ID {workflow_id} not found",
        )

    # 1. Prevent duplicate concurrent executions
    running_execution = (
        db.query(Execution)
        .filter(Execution.workflow_id == workflow_id, Execution.status == "running")
        .first()
    )
    if running_execution:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Workflow {workflow_id} is already running (Execution ID: {running_execution.id}).",
        )

    # 2. Create new Execution record in pending state
    execution = Execution(
        workflow_id=workflow_id,
        status="pending",
        total_tasks=len(workflow.tasks),
        completed_tasks=0,
    )
    db.add(execution)
    db.commit()
    db.refresh(execution)

    initial_inputs = request.initial_inputs if request else None

    # 3. Launch background execution task without blocking HTTP response
    asyncio.create_task(
        execution_engine.execute_workflow_pipeline(
            workflow_id=workflow_id,
            execution_id=execution.id,
            initial_inputs=initial_inputs,
        )
    )

    return execution


@router.get(
    "/{workflow_id}/executions",
    response_model=List[ExecutionResponse],
    summary="List workflow execution history",
)
def list_workflow_executions(
    workflow_id: int,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """Retrieves execution run history for the given workflow."""
    workflow = workflow_service.get_workflow(db=db, workflow_id=workflow_id)
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow with ID {workflow_id} not found",
        )

    return (
        db.query(Execution)
        .filter(Execution.workflow_id == workflow_id)
        .order_by(Execution.id.desc())
        .limit(limit)
        .all()
    )

