"""
SQLAlchemy ORM model for Agent Execution.
Stores runs of the Multi-Agent Intelligent Router.
"""

from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import String, Text, Float, DateTime, ForeignKey, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class AgentExecution(Base):
    __tablename__ = "agent_executions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, index=True)
    task_input: Mapped[str] = mapped_column(Text, nullable=False)
    data_input: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    selected_agent: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending", index=True)
    analysis_result: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    output_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    execution_time_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    workflow_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("workflows.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    workflow: Mapped[Optional["Workflow"]] = relationship("Workflow")

    def __repr__(self) -> str:
        return (
            f"<AgentExecution(id={self.id}, agent='{self.selected_agent}', "
            f"status='{self.status}')>"
        )
