"""
SQLAlchemy ORM model for Report.
Stores AI-generated executive reports, analytical findings, recommendations, and markdown exports.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import String, Text, Integer, DateTime, ForeignKey, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, index=True)
    execution_id: Mapped[int] = mapped_column(
        ForeignKey("executions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    workflow_id: Mapped[int] = mapped_column(
        ForeignKey("workflows.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    executive_summary: Mapped[str] = mapped_column(Text, nullable=False)
    findings: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True, default=list)
    recommendations: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True, default=list)
    next_steps: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True, default=list)
    detailed_analysis: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    raw_markdown: Mapped[str] = mapped_column(Text, nullable=False)
    task_outcomes: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(JSON, nullable=True, default=list)
    generated_by_agent: Mapped[str] = mapped_column(String(50), nullable=False, default="reporting")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    execution: Mapped["Execution"] = relationship("Execution")
    workflow: Mapped["Workflow"] = relationship("Workflow")

    def __repr__(self) -> str:
        return f"<Report(id={self.id}, execution_id={self.execution_id}, title='{self.title}')>"
