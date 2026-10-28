"""
SQLAlchemy ORM model for Workflow.
"""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import String, Text, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Workflow(Base):
    __tablename__ = "workflows"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="draft", index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    tasks: Mapped[List["Task"]] = relationship(
        "Task",
        back_populates="workflow",
        cascade="all, delete-orphan",
        order_by="Task.id",
    )
    executions: Mapped[List["Execution"]] = relationship(
        "Execution",
        back_populates="workflow",
        cascade="all, delete-orphan",
        order_by="Execution.id.desc()",
    )

    def __repr__(self) -> str:
        return f"<Workflow(id={self.id}, name='{self.name}', status='{self.status}')>"
