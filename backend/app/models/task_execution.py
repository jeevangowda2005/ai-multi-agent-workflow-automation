"""
SQLAlchemy ORM model for TaskExecution.
Stores individual task execution attempts, inputs, outputs, retries, and errors within a workflow execution.
"""

from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import String, Text, Float, Integer, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class TaskExecution(Base):
    __tablename__ = "task_executions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, index=True)
    execution_id: Mapped[int] = mapped_column(
        ForeignKey("executions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    task_id: Mapped[int] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending", index=True)
    selected_agent: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    input_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True, default=dict)
    output_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True, default=dict)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    execution_time_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Relationships
    execution: Mapped["Execution"] = relationship("Execution", back_populates="task_executions")
    task: Mapped["Task"] = relationship("Task")

    def __repr__(self) -> str:
        return f"<TaskExecution(id={self.id}, execution_id={self.execution_id}, task_id={self.task_id}, status='{self.status}')>"
