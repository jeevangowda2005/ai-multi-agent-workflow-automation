"""
SQLAlchemy ORM model for Execution.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import String, Text, DateTime, ForeignKey, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Execution(Base):
    __tablename__ = "executions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, index=True)
    workflow_id: Mapped[int] = mapped_column(
        ForeignKey("workflows.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending", index=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    current_task_id: Mapped[Optional[int]] = mapped_column(nullable=True)
    total_tasks: Mapped[int] = mapped_column(default=0, server_default="0", nullable=False)
    completed_tasks: Mapped[int] = mapped_column(default=0, server_default="0", nullable=False)
    execution_metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, default=dict)

    # Relationships
    workflow: Mapped["Workflow"] = relationship("Workflow", back_populates="executions")
    task_executions: Mapped[list["TaskExecution"]] = relationship(
        "TaskExecution",
        back_populates="execution",
        cascade="all, delete-orphan",
        order_by="TaskExecution.id",
    )

    def __repr__(self) -> str:
        return f"<Execution(id={self.id}, workflow_id={self.workflow_id}, status='{self.status}')>"
