"""
Workflow Execution Engine.
Sequentially executes tasks in a workflow, routes to specialized agents,
passes structured outputs between dependencies, handles retries/timeouts,
broadcasts real-time events via WebSockets, and supports safe cancellation.
"""

import asyncio
import time
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Set

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.workflow import Workflow
from app.models.task import Task
from app.models.execution import Execution
from app.models.task_execution import TaskExecution
from app.agents.router_agent import run_intelligent_router
from app.core.websockets import ws_manager

# Set of execution IDs that have been requested to cancel
_cancellation_requests: Set[int] = set()


def request_cancellation(execution_id: int):
    """Flags an active workflow execution for cancellation."""
    _cancellation_requests.add(execution_id)


def is_cancellation_requested(execution_id: int) -> bool:
    """Checks whether an execution has been flagged for cancellation."""
    return execution_id in _cancellation_requests


def clear_cancellation_flag(execution_id: int):
    """Cleans up the cancellation flag for an execution."""
    _cancellation_requests.discard(execution_id)


async def execute_single_task_with_retry(
    task: Task,
    prior_outputs: Dict[int, Any],
    initial_inputs: Optional[Dict[str, Any]] = None,
    execution_id: int = 0,
    llm_callable: Optional[Callable] = None,
) -> Dict[str, Any]:
    """
    Executes a single task node with retry logic, timeout enforcement, and dependency output injection.
    """
    # 1. Prepare Task Inputs & Context
    input_data = dict(task.input_data or {})
    if initial_inputs and not prior_outputs:
        input_data.update(initial_inputs)

    # Resolve dependencies: if depends_on_task_id is specified, inject parent output
    parent_output = None
    if task.depends_on_task_id and task.depends_on_task_id in prior_outputs:
        parent_output = prior_outputs[task.depends_on_task_id]

    # Task description prompt
    task_desc = input_data.get("task_description") or input_data.get("prompt") or task.name

    # Attached data (from input_data or parent output)
    data_input = input_data.get("data_input")
    if not data_input and parent_output:
        # If parent output has a body, findings, or metrics, pass it as data input
        if isinstance(parent_output, dict):
            if "body" in parent_output:
                data_input = parent_output["body"]
            elif "executive_summary" in parent_output:
                data_input = parent_output["executive_summary"]
            elif "dataset_overview" in parent_output:
                data_input = str(parent_output.get("statistical_summary", ""))

    # Supplemental context
    context = dict(input_data.get("context") or {})
    if parent_output:
        context["dependent_task_output"] = parent_output
    if prior_outputs:
        context["pipeline_history"] = {
            f"task_{tid}": out for tid, out in prior_outputs.items()
        }

    agent_override = task.agent_type or input_data.get("agent_type") or input_data.get("agent_override")
    tone = input_data.get("tone")
    timeout = task.timeout_seconds or 60
    max_retries = max(0, task.max_retries or 0)

    last_error = None

    for attempt in range(max_retries + 1):
        if is_cancellation_requested(execution_id):
            raise asyncio.CancelledError("Execution canceled by user.")

        if attempt > 0:
            await ws_manager.broadcast_event(
                execution_id,
                "task_retrying",
                {
                    "task_id": task.id,
                    "task_name": task.name,
                    "attempt": attempt,
                    "max_retries": max_retries,
                },
            )
            await asyncio.sleep(1.0)

        t0 = time.perf_counter()
        try:
            # Broadcast agent selected if known
            if agent_override:
                await ws_manager.broadcast_event(
                    execution_id,
                    "agent_selected",
                    {
                        "task_id": task.id,
                        "task_name": task.name,
                        "agent": agent_override,
                        "override": True,
                    },
                )

            # Execute router/agent with timeout
            router_coro = run_intelligent_router(
                task_description=task_desc,
                data_input=data_input,
                context=context,
                agent_override=agent_override,
                tone=tone,
                llm_callable=llm_callable,
            )
            final_state = await asyncio.wait_for(router_coro, timeout=timeout)

            selected_agent = final_state.get("selected_agent")
            output = final_state.get("agent_output") or {}
            elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)

            return {
                "selected_agent": selected_agent,
                "output": output,
                "retry_count": attempt,
                "execution_time_ms": elapsed_ms,
            }

        except asyncio.CancelledError:
            raise
        except Exception as exc:
            last_error = exc
            if attempt < max_retries:
                continue

    raise last_error or RuntimeError(f"Task {task.id} failed after {max_retries} retries.")


async def execute_workflow_pipeline(
    workflow_id: int,
    execution_id: int,
    initial_inputs: Optional[Dict[str, Any]] = None,
    llm_callable: Optional[Callable] = None,
):
    """
    Main asynchronous background worker executing workflow tasks in sequence.
    Updates PostgreSQL state, tracks individual TaskExecutions, and streams WebSocket events.
    """
    db: Session = SessionLocal()

    try:
        if is_cancellation_requested(execution_id):
            execution = db.query(Execution).filter(Execution.id == execution_id).first()
            if execution and execution.status not in ("completed", "failed", "canceled"):
                execution.status = "canceled"
                execution.completed_at = datetime.now(timezone.utc)
                execution.error_message = "Execution canceled before starting."
                db.commit()
                await ws_manager.broadcast_event(
                    execution_id,
                    "workflow_canceled",
                    {"message": "Execution canceled before starting."},
                )
            return

        # 1. Fetch workflow and sorted tasks
        workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
        execution = db.query(Execution).filter(Execution.id == execution_id).first()

        if not workflow or not execution:
            return

        tasks: List[Task] = (
            db.query(Task)
            .filter(Task.workflow_id == workflow_id)
            .order_by(Task.order_index.asc(), Task.id.asc())
            .all()
        )

        execution.status = "running"
        execution.total_tasks = len(tasks)
        execution.completed_tasks = 0
        db.commit()

        await ws_manager.broadcast_event(
            execution_id,
            "workflow_started",
            {
                "workflow_id": workflow_id,
                "workflow_name": workflow.name,
                "total_tasks": len(tasks),
            },
        )

        if not tasks:
            execution.status = "completed"
            execution.completed_at = datetime.now(timezone.utc)
            db.commit()
            await ws_manager.broadcast_event(
                execution_id,
                "workflow_completed",
                {"message": "Workflow completed with 0 tasks.", "total_tasks": 0},
            )
            return

        prior_outputs: Dict[int, Any] = {}

        # 2. Sequential Task Execution Loop
        for task in tasks:
            # Check cancellation between tasks
            if is_cancellation_requested(execution_id):
                execution.status = "canceled"
                execution.completed_at = datetime.now(timezone.utc)
                execution.error_message = "Execution was canceled by user."
                db.commit()
                await ws_manager.broadcast_event(
                    execution_id,
                    "workflow_canceled",
                    {"message": "Workflow execution was canceled."},
                )
                return

            execution.current_task_id = task.id
            db.commit()

            # Create TaskExecution DB record
            task_exec = TaskExecution(
                execution_id=execution_id,
                task_id=task.id,
                status="running",
                started_at=datetime.now(timezone.utc),
                input_data=task.input_data,
            )
            db.add(task_exec)
            db.commit()
            db.refresh(task_exec)

            await ws_manager.broadcast_event(
                execution_id,
                "task_started",
                {
                    "task_id": task.id,
                    "task_name": task.name,
                    "order_index": task.order_index or 0,
                    "agent_type": task.agent_type,
                    "task_execution_id": task_exec.id,
                    "task_execution": {
                        "id": task_exec.id,
                        "task_id": task.id,
                        "execution_id": execution_id,
                        "task_name": task.name,
                        "order_index": task.order_index or 0,
                        "agent_type": task.agent_type,
                        "status": "running",
                        "selected_agent": None,
                        "output_data": {},
                        "error_message": None,
                        "retry_count": 0,
                        "duration_seconds": None,
                    },
                },
            )

            try:
                task_result = await execute_single_task_with_retry(
                    task=task,
                    prior_outputs=prior_outputs,
                    initial_inputs=initial_inputs,
                    execution_id=execution_id,
                    llm_callable=llm_callable,
                )

                # Success
                task_exec.status = "completed"
                task_exec.selected_agent = task_result["selected_agent"]
                task_exec.output_data = task_result["output"]
                task_exec.retry_count = task_result["retry_count"]
                task_exec.execution_time_ms = task_result["execution_time_ms"]
                task_exec.completed_at = datetime.now(timezone.utc)

                # Also cache task output on the Task model itself for inspection
                task.output_data = task_result["output"]
                task.status = "completed"

                prior_outputs[task.id] = task_result["output"]
                execution.completed_tasks += 1
                db.commit()

                duration_s = round(task_result["execution_time_ms"] / 1000, 3) if task_result["execution_time_ms"] else None
                await ws_manager.broadcast_event(
                    execution_id,
                    "task_completed",
                    {
                        "task_id": task.id,
                        "task_name": task.name,
                        "selected_agent": task_result["selected_agent"],
                        "output": task_result["output"],
                        "execution_time_ms": task_result["execution_time_ms"],
                        "task_execution": {
                            "id": task_exec.id,
                            "task_id": task.id,
                            "execution_id": execution_id,
                            "task_name": task.name,
                            "order_index": task.order_index or 0,
                            "agent_type": task_result["selected_agent"] or task.agent_type,
                            "status": "completed",
                            "selected_agent": task_result["selected_agent"],
                            "output_data": task_result["output"],
                            "error_message": None,
                            "retry_count": task_result["retry_count"],
                            "duration_seconds": duration_s,
                        },
                    },
                )

            except asyncio.CancelledError:
                task_exec.status = "canceled"
                task_exec.completed_at = datetime.now(timezone.utc)
                execution.status = "canceled"
                execution.completed_at = datetime.now(timezone.utc)
                execution.error_message = "Execution was canceled by user."
                db.commit()
                await ws_manager.broadcast_event(
                    execution_id,
                    "workflow_canceled",
                    {"message": "Workflow execution canceled."},
                )
                return

            except Exception as task_err:
                # Task Failure
                task_exec.status = "failed"
                task_exec.error_message = str(task_err)
                task_exec.completed_at = datetime.now(timezone.utc)
                task.status = "failed"

                execution.status = "failed"
                execution.completed_at = datetime.now(timezone.utc)
                execution.error_message = (
                    f"Workflow failed at task '{task.name}' (ID: {task.id}): {str(task_err)}"
                )
                db.commit()

                await ws_manager.broadcast_event(
                    execution_id,
                    "task_failed",
                    {
                        "task_id": task.id,
                        "task_name": task.name,
                        "error": str(task_err),
                    },
                )
                await ws_manager.broadcast_event(
                    execution_id,
                    "workflow_failed",
                    {
                        "failed_task_id": task.id,
                        "error": execution.error_message,
                    },
                )
                return

        # 3. All tasks completed successfully
        execution.status = "completed"
        execution.current_task_id = None
        execution.completed_at = datetime.now(timezone.utc)
        execution.execution_metadata = {"completed_task_ids": list(prior_outputs.keys())}
        db.commit()

        await ws_manager.broadcast_event(
            execution_id,
            "workflow_completed",
            {
                "workflow_id": workflow_id,
                "completed_tasks": execution.completed_tasks,
                "total_tasks": execution.total_tasks,
            },
        )

    finally:
        clear_cancellation_flag(execution_id)
        db.close()
