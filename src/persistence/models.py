"""
SQLAlchemy models for persistence.

Defines database schema for goals, tasks, and agent state.
"""

from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    DateTime,
    Enum as SQLEnum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.message import GoalStatus, Priority, TaskStatus
from src.persistence.database import Base


class GoalModel(Base):
    """Database model for goals."""

    __tablename__ = "goals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    context: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(
        SQLEnum(GoalStatus, values_callable=lambda x: [e.value for e in x]),
        default=GoalStatus.PENDING.value,
    )
    priority: Mapped[int] = mapped_column(
        Integer,
        default=Priority.NORMAL.value,
    )
    success_criteria: Mapped[list[str]] = mapped_column(JSON, default=list)

    # Execution details
    result: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    execution_context: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    # Metrics
    tokens_used: Mapped[int] = mapped_column(Integer, default=0)
    execution_time_ms: Mapped[int] = mapped_column(Integer, default=0)
    agents_spawned: Mapped[int] = mapped_column(Integer, default=0)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    tasks: Mapped[list["TaskModel"]] = relationship(
        "TaskModel",
        back_populates="goal",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "description": self.description,
            "context": self.context,
            "status": self.status,
            "priority": self.priority,
            "success_criteria": self.success_criteria,
            "result": self.result,
            "error": self.error,
            "tokens_used": self.tokens_used,
            "execution_time_ms": self.execution_time_ms,
            "agents_spawned": self.agents_spawned,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "tasks": [t.to_dict() for t in self.tasks],
        }


class TaskModel(Base):
    """Database model for tasks."""

    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    goal_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("goals.id", ondelete="CASCADE"),
        nullable=False,
    )
    parent_task_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("tasks.id", ondelete="SET NULL"),
        nullable=True,
    )

    description: Mapped[str] = mapped_column(Text, nullable=False)
    task_type: Mapped[str] = mapped_column(String(50), default="general")
    status: Mapped[str] = mapped_column(
        SQLEnum(TaskStatus, values_callable=lambda x: [e.value for e in x]),
        default=TaskStatus.PENDING.value,
    )
    priority: Mapped[int] = mapped_column(Integer, default=0)
    order: Mapped[int] = mapped_column(Integer, default=0)

    # Assignment
    assigned_agent_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    assigned_agent_type: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Execution
    input_data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    output_data: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Metrics
    tokens_used: Mapped[int] = mapped_column(Integer, default=0)
    execution_time_ms: Mapped[int] = mapped_column(Integer, default=0)
    retries: Mapped[int] = mapped_column(Integer, default=0)
    max_retries: Mapped[int] = mapped_column(Integer, default=3)

    # Dependencies
    dependencies: Mapped[list[str]] = mapped_column(JSON, default=list)
    required_capabilities: Mapped[list[str]] = mapped_column(JSON, default=list)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    goal: Mapped["GoalModel"] = relationship("GoalModel", back_populates="tasks")
    subtasks: Mapped[list["TaskModel"]] = relationship(
        "TaskModel",
        remote_side=[id],
        backref="parent_task",
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "goal_id": self.goal_id,
            "parent_task_id": self.parent_task_id,
            "description": self.description,
            "task_type": self.task_type,
            "status": self.status,
            "priority": self.priority,
            "order": self.order,
            "assigned_agent_id": self.assigned_agent_id,
            "assigned_agent_type": self.assigned_agent_type,
            "input_data": self.input_data,
            "output_data": self.output_data,
            "error": self.error,
            "tokens_used": self.tokens_used,
            "execution_time_ms": self.execution_time_ms,
            "retries": self.retries,
            "dependencies": self.dependencies,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class AgentStateModel(Base):
    """Database model for agent state persistence."""

    __tablename__ = "agent_states"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    agent_type: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)

    # State
    state: Mapped[str] = mapped_column(String(20), default="idle")
    current_task_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    current_goal_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    # Configuration
    provider_key: Mapped[str] = mapped_column(String(50), nullable=False)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    system_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    capabilities: Mapped[list[str]] = mapped_column(JSON, default=list)
    constraints: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    # Metrics
    total_tasks_completed: Mapped[int] = mapped_column(Integer, default=0)
    total_tokens_used: Mapped[int] = mapped_column(Integer, default=0)
    total_execution_time_ms: Mapped[int] = mapped_column(Integer, default=0)
    success_rate: Mapped[float] = mapped_column(Float, default=1.0)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    last_active_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "agent_type": self.agent_type,
            "name": self.name,
            "state": self.state,
            "current_task_id": self.current_task_id,
            "current_goal_id": self.current_goal_id,
            "provider_key": self.provider_key,
            "model_name": self.model_name,
            "capabilities": self.capabilities,
            "total_tasks_completed": self.total_tasks_completed,
            "total_tokens_used": self.total_tokens_used,
            "success_rate": self.success_rate,
            "last_active_at": self.last_active_at.isoformat() if self.last_active_at else None,
        }
