"""
SQLAlchemy ORM model for Task.
"""

from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import String, DateTime, ForeignKey, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, index=True)
    workflow_id: Mapped[int] = mapped_column(
        ForeignKey("workflows.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    task_type: Mapped[str] = mapped_column(String(100), nullable=False, default="action")
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending", index=True)
    input_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True, default=dict)
    output_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True, default=dict)
    order_index: Mapped[int] = mapped_column(default=0, server_default="0", nullable=False, index=True)
    agent_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    max_retries: Mapped[int] = mapped_column(default=0, server_default="0", nullable=False)
    timeout_seconds: Mapped[int] = mapped_column(default=60, server_default="60", nullable=False)
    depends_on_task_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("tasks.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    workflow: Mapped["Workflow"] = relationship("Workflow", back_populates="tasks")
    dependency: Mapped[Optional["Task"]] = relationship("Task", remote_side=[id])

    def __repr__(self) -> str:
        return f"<Task(id={self.id}, workflow_id={self.workflow_id}, name='{self.name}', status='{self.status}')>"
