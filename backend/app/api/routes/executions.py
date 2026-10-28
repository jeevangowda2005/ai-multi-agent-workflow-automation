"""
API endpoints and WebSocket handler for Workflow Executions.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from sqlalchemy.orm import Session, joinedload

from app.db.session import get_db
from app.models.execution import Execution
from app.models.task_execution import TaskExecution
from app.schemas.execution import ExecutionResponse
from app.services import execution_engine
from app.core.websockets import ws_manager

router = APIRouter(tags=["executions"])


@router.get(
    "/executions",
    response_model=List[ExecutionResponse],
    summary="List and filter execution history across workflows",
)
def list_executions(
    workflow_id: Optional[int] = Query(None, description="Filter by workflow ID"),
    status: Optional[str] = Query(None, description="Filter by status: pending, running, completed, failed, canceled"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """Search and filter execution runs across all workflows."""
    query = db.query(Execution).options(
        joinedload(Execution.task_executions).joinedload(TaskExecution.task)
    )
    if workflow_id:
        query = query.filter(Execution.workflow_id == workflow_id)
    if status:
        query = query.filter(Execution.status == status.lower())

    executions = query.order_by(Execution.id.desc()).offset(offset).limit(limit).all()
    return [ExecutionResponse.from_orm_enriched(e) for e in executions]


@router.get(
    "/executions/{execution_id}",
    response_model=ExecutionResponse,
    summary="Retrieve execution details and task outputs",
)
def get_execution_details(
    execution_id: int,
    db: Session = Depends(get_db),
):
    """Retrieves full status, metadata, and task-by-task execution outputs."""
    execution = (
        db.query(Execution)
        .options(joinedload(Execution.task_executions).joinedload(TaskExecution.task))
        .filter(Execution.id == execution_id)
        .first()
    )
    if not execution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Execution with ID {execution_id} not found.",
        )
    return ExecutionResponse.from_orm_enriched(execution)


@router.post(
    "/executions/{execution_id}/cancel",
    response_model=ExecutionResponse,
    summary="Cancel an active workflow execution",
)
async def cancel_execution(
    execution_id: int,
    db: Session = Depends(get_db),
):
    """Requests safe cancellation of a pending or running workflow execution."""
    execution = (
        db.query(Execution)
        .options(joinedload(Execution.task_executions).joinedload(TaskExecution.task))
        .filter(Execution.id == execution_id)
        .first()
    )
    if not execution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Execution with ID {execution_id} not found.",
        )

    if execution.status in ("completed", "failed", "canceled"):
        return ExecutionResponse.from_orm_enriched(execution)

    # Flag for cancellation
    execution_engine.request_cancellation(execution_id)

    # If it was still pending before starting, immediately mark canceled
    if execution.status == "pending":
        execution.status = "canceled"
        execution.error_message = "Execution canceled before starting."
        db.commit()
        db.refresh(execution)
        await ws_manager.broadcast_event(
            execution_id,
            "workflow_canceled",
            {"message": "Execution canceled before starting."},
        )

    return ExecutionResponse.from_orm_enriched(execution)


@router.websocket("/ws/executions/{execution_id}")
async def execution_events_websocket(
    websocket: WebSocket,
    execution_id: int,
):
    """
    WebSocket endpoint streaming live execution lifecycle events:
    workflow_started, task_started, agent_selected, task_completed, task_failed, workflow_completed, workflow_canceled.
    """
    await ws_manager.connect(execution_id, websocket)
    try:
        # Send initial connection confirmation event
        await websocket.send_json({
            "event": "connected",
            "execution_id": execution_id,
            "message": f"Subscribed to execution {execution_id} live events.",
        })
        while True:
            # Keep socket open and receive client pings/messages
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        await ws_manager.disconnect(execution_id, websocket)
    except Exception:
        await ws_manager.disconnect(execution_id, websocket)
