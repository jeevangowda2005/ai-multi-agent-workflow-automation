"""
API endpoints for AI Report Generation, retrieval, and PDF download.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session, joinedload

from app.db.session import get_db
from app.models.report import Report
from app.schemas.report import ReportGenerateRequest, ReportResponse, ReportListItem
from app.services import report_service

router = APIRouter(prefix="/reports", tags=["reports"])


@router.post(
    "/generate",
    response_model=ReportResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate an AI executive report from a workflow execution",
)
async def generate_report(
    payload: ReportGenerateRequest,
    db: Session = Depends(get_db),
):
    """
    Synthesizes task execution outputs and metrics into a formal enterprise report
    using the Reporting Agent and stores it in PostgreSQL.
    """
    try:
        report = await report_service.generate_report_for_execution(
            db=db,
            execution_id=payload.execution_id,
            title=payload.title,
            notes=payload.notes,
        )
        return ReportResponse(
            id=report.id,
            execution_id=report.execution_id,
            workflow_id=report.workflow_id,
            workflow_name=report.workflow.name if report.workflow else None,
            title=report.title,
            executive_summary=report.executive_summary,
            findings=report.findings or [],
            recommendations=report.recommendations or [],
            next_steps=report.next_steps or [],
            detailed_analysis=report.detailed_analysis,
            raw_markdown=report.raw_markdown,
            task_outcomes=report.task_outcomes or [],
            generated_by_agent=report.generated_by_agent,
            created_at=report.created_at,
        )
    except ValueError as val_err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(val_err))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Report generation failed: {str(exc)}",
        )


@router.get(
    "",
    response_model=List[ReportListItem],
    summary="List all generated AI reports",
)
def list_reports(
    workflow_id: Optional[int] = Query(None, description="Filter by workflow ID"),
    execution_id: Optional[int] = Query(None, description="Filter by execution ID"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """Lists generated reports with summary metadata."""
    query = db.query(Report).options(joinedload(Report.workflow))
    if workflow_id:
        query = query.filter(Report.workflow_id == workflow_id)
    if execution_id:
        query = query.filter(Report.execution_id == execution_id)

    reports = query.order_by(Report.id.desc()).offset(offset).limit(limit).all()

    return [
        ReportListItem(
            id=r.id,
            execution_id=r.execution_id,
            workflow_id=r.workflow_id,
            workflow_name=r.workflow.name if r.workflow else f"Workflow #{r.workflow_id}",
            title=r.title,
            executive_summary=r.executive_summary,
            findings_count=len(r.findings or []),
            recommendations_count=len(r.recommendations or []),
            created_at=r.created_at,
        )
        for r in reports
    ]


@router.get(
    "/{report_id}",
    response_model=ReportResponse,
    summary="Retrieve full report details and markdown export",
)
def get_report(
    report_id: int,
    db: Session = Depends(get_db),
):
    """Retrieves full report content, findings, recommendations, and telemetry."""
    report = (
        db.query(Report)
        .options(joinedload(Report.workflow))
        .filter(Report.id == report_id)
        .first()
    )
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report #{report_id} not found.",
        )

    return ReportResponse(
        id=report.id,
        execution_id=report.execution_id,
        workflow_id=report.workflow_id,
        workflow_name=report.workflow.name if report.workflow else None,
        title=report.title,
        executive_summary=report.executive_summary,
        findings=report.findings or [],
        recommendations=report.recommendations or [],
        next_steps=report.next_steps or [],
        detailed_analysis=report.detailed_analysis,
        raw_markdown=report.raw_markdown,
        task_outcomes=report.task_outcomes or [],
        generated_by_agent=report.generated_by_agent,
        created_at=report.created_at,
    )


@router.get(
    "/{report_id}/download",
    summary="Download publication-quality PDF report",
)
def download_report_pdf(
    report_id: int,
    db: Session = Depends(get_db),
):
    """Renders and streams the report as a downloadable binary PDF document."""
    report = (
        db.query(Report)
        .options(joinedload(Report.workflow))
        .filter(Report.id == report_id)
        .first()
    )
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report #{report_id} not found.",
        )

    pdf_bytes = report_service.get_report_pdf_bytes(report)
    clean_title = "".join(c for c in report.title if c.isalnum() or c in ("-", "_")).rstrip()
    filename = f"Report_{report.id}_{clean_title[:30]}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Type": "application/pdf",
        },
    )
