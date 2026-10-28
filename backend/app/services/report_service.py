"""
AI Report Service.
Synthesizes completed workflow execution outcomes into formal reports using the Reporting Agent,
converts findings to clean Markdown, stores reports in PostgreSQL, and generates PDFs.
"""

from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional
from sqlalchemy.orm import Session, joinedload

from app.models.execution import Execution
from app.models.task_execution import TaskExecution
from app.models.report import Report
from app.agents.specialized.reporting_agent import run_reporting_agent
from app.schemas.agent import ReportingResult
from app.services.pdf_service import generate_report_pdf


def compile_markdown_report(
    title: str,
    executive_summary: str,
    findings: List[str],
    recommendations: List[str],
    next_steps: List[str],
    detailed_analysis: Optional[str] = None,
    task_outcomes: Optional[List[Dict[str, Any]]] = None,
    workflow_name: Optional[str] = None,
    execution_id: Optional[int] = None,
    created_at: Optional[datetime] = None,
) -> str:
    """Produces GitHub-flavored Markdown document from report components."""
    date_str = created_at.strftime("%Y-%m-%d %H:%M UTC") if created_at else datetime.now(timezone.utc).strftime("%Y-%m-%d")

    md = [
        f"# {title}",
        "",
        f"> **Workflow:** {workflow_name or 'N/A'} | **Execution ID:** #{execution_id or 'N/A'} | **Generated:** {date_str}",
        "",
        "## Executive Summary",
        "",
        executive_summary,
        "",
    ]

    if findings:
        md.append("## Key Findings")
        md.append("")
        for f in findings:
            md.append(f"- {f}")
        md.append("")

    if recommendations:
        md.append("## Strategic Recommendations")
        md.append("")
        for idx, rec in enumerate(recommendations, 1):
            md.append(f"{idx}. {rec}")
        md.append("")

    if next_steps:
        md.append("## Roadmap & Next Steps")
        md.append("")
        for s in next_steps:
            md.append(f"- [ ] {s}")
        md.append("")

    if detailed_analysis and detailed_analysis.strip():
        md.append("## Detailed Analysis")
        md.append("")
        md.append(detailed_analysis.strip())
        md.append("")

    if task_outcomes:
        md.append("## Task Execution Telemetry")
        md.append("")
        md.append("| Step | Task Name | Agent | Status | Duration |")
        md.append("| :--- | :-------- | :---- | :----- | :------- |")
        for idx, t in enumerate(task_outcomes, 1):
            dur = f"{t.get('duration_seconds', 0):.2f}s" if t.get("duration_seconds") else "—"
            md.append(f"| #{idx} | {t.get('task_name', 'Task')} | {t.get('agent_type', 'llm')} | {t.get('status', 'completed')} | {dur} |")
        md.append("")

    return "\n".join(md)


async def generate_report_for_execution(
    db: Session,
    execution_id: int,
    title: Optional[str] = None,
    notes: Optional[str] = None,
    llm_callable: Optional[Callable] = None,
) -> Report:
    """
    Executes the Reporting Agent against an Execution's task outcomes
    and persists the Report in PostgreSQL.
    """
    execution = (
        db.query(Execution)
        .options(
            joinedload(Execution.workflow),
            joinedload(Execution.task_executions).joinedload(TaskExecution.task),
        )
        .filter(Execution.id == execution_id)
        .first()
    )

    if not execution:
        raise ValueError(f"Execution #{execution_id} not found.")

    workflow_name = execution.workflow.name if execution.workflow else f"Workflow #{execution.workflow_id}"

    # Build structured task outcomes summary
    task_outcomes: List[Dict[str, Any]] = []
    task_outputs_context: Dict[str, Any] = {}

    for te in (execution.task_executions or []):
        t_name = te.task.name if te.task else f"Task #{te.task_id}"
        dur_s = round(te.execution_time_ms / 1000, 3) if te.execution_time_ms else None
        item = {
            "task_id": te.task_id,
            "task_name": t_name,
            "order_index": te.task.order_index if te.task else 0,
            "agent_type": te.selected_agent or (te.task.agent_type if te.task else "llm"),
            "status": te.status,
            "retry_count": te.retry_count,
            "duration_seconds": dur_s,
            "output_data": te.output_data or {},
            "error_message": te.error_message,
        }
        task_outcomes.append(item)
        task_outputs_context[f"task_{te.task_id}_{t_name}"] = {
            "agent": item["agent_type"],
            "status": te.status,
            "output": te.output_data or {},
        }

    # Prompt the Reporting Agent
    report_task_desc = (
        f"Generate a comprehensive executive report for the automated workflow '{workflow_name}' "
        f"(Execution #{execution.id}, overall status: {execution.status})."
    )
    if notes:
        report_task_desc += f"\nSpecific Stakeholder Focus: {notes}"

    context_payload = {
        "workflow_id": execution.workflow_id,
        "workflow_name": workflow_name,
        "execution_id": execution.id,
        "execution_status": execution.status,
        "total_tasks": execution.total_tasks,
        "completed_tasks": execution.completed_tasks,
        "started_at": execution.started_at.isoformat() if execution.started_at else None,
        "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
        "task_results": task_outputs_context,
    }

    # Run specialized Reporting Agent
    reporting_result: ReportingResult = await run_reporting_agent(
        task_description=report_task_desc,
        context=context_payload,
        llm_callable=llm_callable,
    )

    final_title = title.strip() if title and title.strip() else reporting_result.report_title

    # Generate Markdown
    created_now = datetime.now(timezone.utc)
    raw_md = compile_markdown_report(
        title=final_title,
        executive_summary=reporting_result.executive_summary,
        findings=reporting_result.key_findings,
        recommendations=reporting_result.strategic_recommendations,
        next_steps=reporting_result.next_steps,
        detailed_analysis=reporting_result.detailed_analysis,
        task_outcomes=task_outcomes,
        workflow_name=workflow_name,
        execution_id=execution.id,
        created_at=created_now,
    )

    report = Report(
        execution_id=execution.id,
        workflow_id=execution.workflow_id,
        title=final_title,
        executive_summary=reporting_result.executive_summary,
        findings=reporting_result.key_findings,
        recommendations=reporting_result.strategic_recommendations,
        next_steps=reporting_result.next_steps,
        detailed_analysis=reporting_result.detailed_analysis,
        raw_markdown=raw_md,
        task_outcomes=task_outcomes,
        generated_by_agent="reporting",
        created_at=created_now,
    )

    db.add(report)
    db.commit()
    db.refresh(report)
    return report


def get_report_pdf_bytes(report: Report) -> bytes:
    """Generates PDF bytes for an existing Report model."""
    wf_name = report.workflow.name if report.workflow else f"Workflow #{report.workflow_id}"
    return generate_report_pdf(
        title=report.title,
        executive_summary=report.executive_summary,
        findings=report.findings or [],
        recommendations=report.recommendations or [],
        next_steps=report.next_steps or [],
        detailed_analysis=report.detailed_analysis,
        task_outcomes=report.task_outcomes or [],
        workflow_name=wf_name,
        execution_id=report.execution_id,
        created_at=report.created_at,
    )
