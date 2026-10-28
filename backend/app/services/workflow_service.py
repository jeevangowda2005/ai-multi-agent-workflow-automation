"""
Workflow and Task service layer.
Encapsulates database operations for Workflows, Tasks, and Executions.
"""

from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, select

from app.models.workflow import Workflow
from app.models.task import Task
from app.schemas.workflow import WorkflowCreate, WorkflowUpdate
from app.schemas.task import TaskCreate


def create_workflow(db: Session, workflow_in: WorkflowCreate) -> Workflow:
    """Create and persist a new workflow."""
    workflow = Workflow(
        name=workflow_in.name.strip(),
        description=workflow_in.description.strip() if workflow_in.description else None,
        status=workflow_in.status.strip() if workflow_in.status else "draft",
    )
    db.add(workflow)
    db.commit()
    db.refresh(workflow)
    return workflow


def list_workflows(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    search: Optional[str] = None,
) -> List[Workflow]:
    """Retrieve workflows with optional filtering and pagination."""
    query = db.query(Workflow)
    if status:
        query = query.filter(Workflow.status == status)
    if search:
        query = query.filter(Workflow.name.ilike(f"%{search}%"))

    workflows = query.order_by(Workflow.created_at.desc()).offset(skip).limit(limit).all()

    # Pre-populate tasks_count for each workflow
    for wf in workflows:
        wf.tasks_count = len(wf.tasks)

    return workflows


def get_workflow(db: Session, workflow_id: int) -> Optional[Workflow]:
    """Get a single workflow by ID."""
    workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    if workflow:
        workflow.tasks_count = len(workflow.tasks)
    return workflow


def update_workflow(
    db: Session,
    workflow: Workflow,
    workflow_in: WorkflowUpdate,
) -> Workflow:
    """Update an existing workflow."""
    update_data = workflow_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if value is not None and isinstance(value, str):
            value = value.strip()
        setattr(workflow, field, value)

    db.add(workflow)
    db.commit()
    db.refresh(workflow)
    workflow.tasks_count = len(workflow.tasks)
    return workflow


def delete_workflow(db: Session, workflow: Workflow) -> None:
    """Delete a workflow and its associated tasks/executions (via DB cascade)."""
    db.delete(workflow)
    db.commit()


def create_task(db: Session, workflow_id: int, task_in: TaskCreate) -> Task:
    """Create and add a task to an existing workflow with execution configuration."""
    task = Task(
        workflow_id=workflow_id,
        name=task_in.name.strip(),
        task_type=task_in.task_type.strip() if task_in.task_type else "action",
        status=task_in.status.strip() if task_in.status else "pending",
        input_data=task_in.input_data or {},
        output_data=task_in.output_data or {},
        order_index=task_in.order_index if task_in.order_index is not None else 0,
        agent_type=task_in.agent_type,
        max_retries=task_in.max_retries if task_in.max_retries is not None else 0,
        timeout_seconds=task_in.timeout_seconds if task_in.timeout_seconds is not None else 60,
        depends_on_task_id=task_in.depends_on_task_id,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def get_task(db: Session, task_id: int) -> Optional[Task]:
    """Get a single task by ID."""
    return db.query(Task).filter(Task.id == task_id).first()


def update_task(db: Session, task: Task, task_in: TaskUpdate) -> Task:
    """Update task configuration, ordering, agent assignment, or dependencies."""
    update_data = task_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if value is not None and isinstance(value, str):
            value = value.strip()
        setattr(task, field, value)

    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def delete_task(db: Session, task: Task) -> None:
    """Delete a task from a workflow."""
    # Reset any tasks depending on this task
    db.query(Task).filter(Task.depends_on_task_id == task.id).update(
        {"depends_on_task_id": None}
    )
    db.delete(task)
    db.commit()


def check_circular_dependency(db: Session, workflow_id: int, task_id: int, depends_on_id: Optional[int]) -> bool:
    """
    Checks if setting task_id to depend on depends_on_id introduces a cycle in the DAG.
    Returns True if a circular dependency is detected.
    """
    if not depends_on_id:
        return False
    if task_id == depends_on_id:
        return True

    visited = {task_id}
    current_id: Optional[int] = depends_on_id

    while current_id:
        if current_id in visited:
            return True
        visited.add(current_id)
        parent_task = db.query(Task).filter(Task.id == current_id, Task.workflow_id == workflow_id).first()
        if not parent_task:
            break
        current_id = parent_task.depends_on_task_id

    return False


def list_tasks_for_workflow(db: Session, workflow_id: int) -> List[Task]:
    """List all tasks belonging to a specific workflow ordered sequentially."""
    return (
        db.query(Task)
        .filter(Task.workflow_id == workflow_id)
        .order_by(Task.order_index.asc(), Task.id.asc())
        .all()
    )


# ── 3 Pre-Built Reusable Workflow Templates ───────────────────────────────────

WORKFLOW_TEMPLATES = [
    {
        "id": "customer-feedback-analysis",
        "name": "Customer Feedback Analysis",
        "description": "Multi-agent pipeline that ingests customer reviews, extracts numerical trends and complaint patterns, and compiles an executive summary briefing.",
        "tasks": [
            {
                "name": "Ingest & Research Feedback",
                "task_type": "action",
                "agent_type": "research",
                "order_index": 0,
                "max_retries": 1,
                "timeout_seconds": 60,
                "input_data": {
                    "task_description": "Analyze customer feedback dataset, extract core complaint themes, and identify verified factual issues.",
                },
            },
            {
                "name": "Statistical Sentiment & Churn Analysis",
                "task_type": "action",
                "agent_type": "data_analysis",
                "order_index": 1,
                "max_retries": 1,
                "timeout_seconds": 60,
                "input_data": {
                    "task_description": "Calculate statistical frequency of identified complaints, score churn risks, and provide data-backed priorities.",
                },
            },
            {
                "name": "Customer Experience Executive Report",
                "task_type": "action",
                "agent_type": "reporting",
                "order_index": 2,
                "max_retries": 1,
                "timeout_seconds": 60,
                "input_data": {
                    "task_description": "Draft an executive briefing summarizing customer satisfaction findings, prioritized remediations, and roadmap steps.",
                },
            },
        ],
    },
    {
        "id": "ai-content-generation-pipeline",
        "name": "AI Content Generation Pipeline",
        "description": "Researches domain facts, crafts engaging multi-channel copy across requested tones, and produces an executive distribution report.",
        "tasks": [
            {
                "name": "Topic Research & Source Discovery",
                "task_type": "action",
                "agent_type": "research",
                "order_index": 0,
                "max_retries": 1,
                "timeout_seconds": 60,
                "input_data": {
                    "task_description": "Gather verified facts, statistics, and industry benchmarks for the targeted content theme.",
                },
            },
            {
                "name": "Professional Article & Copy Drafting",
                "task_type": "action",
                "agent_type": "content_generation",
                "order_index": 1,
                "max_retries": 1,
                "timeout_seconds": 60,
                "input_data": {
                    "task_description": "Generate an authoritative article with compelling hooks, key takeaways, and call-to-action based on research.",
                    "tone": "executive",
                },
            },
            {
                "name": "Distribution Briefing & Performance Report",
                "task_type": "action",
                "agent_type": "reporting",
                "order_index": 2,
                "max_retries": 1,
                "timeout_seconds": 60,
                "input_data": {
                    "task_description": "Prepare a content performance briefing with channel distribution recommendations and audience profile notes.",
                },
            },
        ],
    },
    {
        "id": "business-research-reporting",
        "name": "Business Research & Reporting",
        "description": "Deep-dives into competitive intelligence or operational initiatives and generates a formal publication-ready enterprise report.",
        "tasks": [
            {
                "name": "Competitive & Market Intelligence",
                "task_type": "action",
                "agent_type": "research",
                "order_index": 0,
                "max_retries": 1,
                "timeout_seconds": 60,
                "input_data": {
                    "task_description": "Conduct deep competitive analysis, market share evaluation, and technology adoption trends.",
                },
            },
            {
                "name": "Strategic Executive Report",
                "task_type": "action",
                "agent_type": "reporting",
                "order_index": 1,
                "max_retries": 1,
                "timeout_seconds": 60,
                "input_data": {
                    "task_description": "Synthesize market findings into a comprehensive strategic report with prioritized business recommendations and milestones.",
                },
            },
        ],
    },
]


def create_workflow_from_template(db: Session, template_id: str, custom_name: Optional[str] = None) -> Workflow:
    """Instantiates a full executable workflow with configured task nodes from a pre-built template."""
    tmpl = next((t for t in WORKFLOW_TEMPLATES if t["id"] == template_id), None)
    if not tmpl:
        raise ValueError(f"Workflow template '{template_id}' not found.")

    name = custom_name.strip() if custom_name and custom_name.strip() else tmpl["name"]
    wf = Workflow(
        name=name,
        description=tmpl["description"],
        status="active",
    )
    db.add(wf)
    db.commit()
    db.refresh(wf)

    created_tasks: List[Task] = []
    for idx, t_data in enumerate(tmpl["tasks"]):
        prev_task_id = created_tasks[idx - 1].id if idx > 0 else None
        task = Task(
            workflow_id=wf.id,
            name=t_data["name"],
            task_type=t_data["task_type"],
            status="pending",
            order_index=t_data["order_index"],
            agent_type=t_data["agent_type"],
            max_retries=t_data["max_retries"],
            timeout_seconds=t_data["timeout_seconds"],
            depends_on_task_id=prev_task_id,
            input_data=t_data["input_data"],
            output_data={},
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        created_tasks.append(task)

    db.refresh(wf)
    wf.tasks_count = len(created_tasks)
    return wf
