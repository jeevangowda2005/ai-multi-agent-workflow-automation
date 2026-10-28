"""
PDF Report Generation Service using ReportLab.
Produces structured, professional enterprise PDF reports for workflow executions.
"""

import io
from datetime import datetime
from typing import Any, Dict, List, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


def generate_report_pdf(
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
) -> bytes:
    """
    Renders an executive PDF report into an in-memory byte buffer.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=45,
        leftMargin=45,
        topMargin=45,
        bottomMargin=45,
    )

    styles = getSampleStyleSheet()

    # Custom typography & styles
    primary_color = colors.HexColor("#3B82F6")   # Blue 500
    dark_neutral = colors.HexColor("#0F172A")    # Slate 900
    slate_subtext = colors.HexColor("#475569")   # Slate 600
    card_bg = colors.HexColor("#F8FAFC")         # Slate 50
    border_color = colors.HexColor("#E2E8F0")    # Slate 200

    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=22,
        leading=26,
        textColor=dark_neutral,
        spaceAfter=6,
    )

    subtitle_style = ParagraphStyle(
        "ReportSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=slate_subtext,
    )

    h2_style = ParagraphStyle(
        "SectionHeading",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=17,
        textColor=primary_color,
        spaceBefore=14,
        spaceAfter=6,
    )

    body_style = ParagraphStyle(
        "ReportBody",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=dark_neutral,
        spaceAfter=6,
    )

    bullet_style = ParagraphStyle(
        "BulletPoint",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=13.5,
        textColor=dark_neutral,
        leftIndent=15,
        firstLineIndent=-10,
        spaceAfter=4,
    )

    story = []

    # 1. Header Banner
    story.append(Paragraph(title, title_style))
    date_str = created_at.strftime("%B %d, %Y - %H:%M UTC") if created_at else datetime.utcnow().strftime("%B %d, %Y")
    meta_info = f"Workflow: <b>{workflow_name or 'Automation Pipeline'}</b> | Execution ID: <b>#{execution_id or 'N/A'}</b> | Generated: {date_str}"
    story.append(Paragraph(meta_info, subtitle_style))
    story.append(Spacer(1, 8))
    story.append(HRFlowable(width="100%", thickness=1.5, color=primary_color, spaceBefore=4, spaceAfter=14))

    # 2. Executive Summary Box
    story.append(Paragraph("Executive Summary", h2_style))
    exec_table = Table(
        [[Paragraph(executive_summary, body_style)]],
        colWidths=[520],
    )
    exec_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), card_bg),
            ("BOX", (0, 0), (-1, -1), 1, border_color),
            ("LEFTPADDING", (0, 0), (-1, -1), 14),
            ("RIGHTPADDING", (0, 0), (-1, -1), 14),
            ("TOPPADDING", (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ])
    )
    story.append(exec_table)
    story.append(Spacer(1, 10))

    # 3. Key Findings
    if findings:
        story.append(Paragraph("Key Findings & Analytical Insights", h2_style))
        for item in findings:
            bullet_html = f"&bull; {item}"
            story.append(Paragraph(bullet_html, bullet_style))
        story.append(Spacer(1, 10))

    # 4. Strategic Recommendations
    if recommendations:
        story.append(Paragraph("Strategic Recommendations", h2_style))
        for i, rec in enumerate(recommendations, 1):
            rec_html = f"<b>{i}.</b> {rec}"
            story.append(Paragraph(rec_html, bullet_style))
        story.append(Spacer(1, 10))

    # 5. Next Steps / Action Items
    if next_steps:
        story.append(Paragraph("Roadmap & Next Steps", h2_style))
        for step in next_steps:
            step_html = f"&bull; {step}"
            story.append(Paragraph(step_html, bullet_style))
        story.append(Spacer(1, 10))

    # 6. Detailed Analysis (if available)
    if detailed_analysis and detailed_analysis.strip():
        story.append(Paragraph("Detailed Analytical Breakdown", h2_style))
        for p in detailed_analysis.split("\n\n"):
            clean_p = p.strip()
            if clean_p:
                story.append(Paragraph(clean_p, body_style))
        story.append(Spacer(1, 10))

    # 7. Workflow Task Execution Summary Table
    if task_outcomes:
        story.append(Paragraph("Task Execution Telemetry", h2_style))
        table_data = [
            [
                Paragraph("<b>Step</b>", body_style),
                Paragraph("<b>Task Name</b>", body_style),
                Paragraph("<b>Agent</b>", body_style),
                Paragraph("<b>Status</b>", body_style),
                Paragraph("<b>Duration</b>", body_style),
            ]
        ]
        for idx, task in enumerate(task_outcomes, 1):
            duration = f"{task.get('duration_seconds', 0):.2f}s" if task.get('duration_seconds') else "—"
            table_data.append([
                Paragraph(f"#{idx}", body_style),
                Paragraph(task.get("task_name", "Task"), body_style),
                Paragraph(task.get("agent_type", "llm").capitalize(), body_style),
                Paragraph(task.get("status", "completed").capitalize(), body_style),
                Paragraph(duration, body_style),
            ])

        task_table = Table(table_data, colWidths=[40, 220, 110, 80, 70])
        task_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), card_bg),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("GRID", (0, 0), (-1, -1), 0.5, border_color),
            ])
        )
        story.append(task_table)

    # Build PDF document
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()
