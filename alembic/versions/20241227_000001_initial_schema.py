"""Initial schema for Agent Village.

Revision ID: 20241227_000001
Revises:
Create Date: 2024-12-27 00:00:01

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20241227_000001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create initial database schema."""

    # Goals table
    op.create_table(
        "goals",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("context", postgresql.JSON(), server_default="{}"),
        sa.Column(
            "status",
            sa.Enum(
                "pending", "created", "planning", "in_progress",
                "executing", "verifying", "reflecting", "awaiting_human",
                "completed", "failed", "cancelled",
                name="goalstatus"
            ),
            server_default="pending",
        ),
        sa.Column("priority", sa.Integer(), server_default="3"),
        sa.Column("success_criteria", postgresql.JSON(), server_default="[]"),
        sa.Column("result", postgresql.JSON(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("execution_context", postgresql.JSON(), server_default="{}"),
        sa.Column("tokens_used", sa.Integer(), server_default="0"),
        sa.Column("execution_time_ms", sa.Integer(), server_default="0"),
        sa.Column("agents_spawned", sa.Integer(), server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )

    # Create index on status for filtering
    op.create_index("ix_goals_status", "goals", ["status"])
    op.create_index("ix_goals_created_at", "goals", ["created_at"])

    # Tasks table
    op.create_table(
        "tasks",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "goal_id",
            sa.String(36),
            sa.ForeignKey("goals.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "parent_task_id",
            sa.String(36),
            sa.ForeignKey("tasks.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("task_type", sa.String(50), server_default="general"),
        sa.Column(
            "status",
            sa.Enum(
                "pending", "assigned", "in_progress", "awaiting_approval",
                "completed", "failed", "cancelled",
                name="taskstatus"
            ),
            server_default="pending",
        ),
        sa.Column("priority", sa.Integer(), server_default="0"),
        sa.Column("order", sa.Integer(), server_default="0"),
        sa.Column("assigned_agent_id", sa.String(36), nullable=True),
        sa.Column("assigned_agent_type", sa.String(50), nullable=True),
        sa.Column("input_data", postgresql.JSON(), server_default="{}"),
        sa.Column("output_data", postgresql.JSON(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("tokens_used", sa.Integer(), server_default="0"),
        sa.Column("execution_time_ms", sa.Integer(), server_default="0"),
        sa.Column("retries", sa.Integer(), server_default="0"),
        sa.Column("max_retries", sa.Integer(), server_default="3"),
        sa.Column("dependencies", postgresql.JSON(), server_default="[]"),
        sa.Column("required_capabilities", postgresql.JSON(), server_default="[]"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Create indexes
    op.create_index("ix_tasks_goal_id", "tasks", ["goal_id"])
    op.create_index("ix_tasks_status", "tasks", ["status"])
    op.create_index("ix_tasks_assigned_agent_id", "tasks", ["assigned_agent_id"])

    # Agent states table
    op.create_table(
        "agent_states",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("agent_type", sa.String(50), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("state", sa.String(20), server_default="idle"),
        sa.Column("current_task_id", sa.String(36), nullable=True),
        sa.Column("current_goal_id", sa.String(36), nullable=True),
        sa.Column("provider_key", sa.String(50), nullable=False),
        sa.Column("model_name", sa.String(100), nullable=False),
        sa.Column("system_prompt", sa.Text(), nullable=True),
        sa.Column("capabilities", postgresql.JSON(), server_default="[]"),
        sa.Column("constraints", postgresql.JSON(), server_default="{}"),
        sa.Column("total_tasks_completed", sa.Integer(), server_default="0"),
        sa.Column("total_tokens_used", sa.Integer(), server_default="0"),
        sa.Column("total_execution_time_ms", sa.Integer(), server_default="0"),
        sa.Column("success_rate", sa.Float(), server_default="1.0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column("last_active_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )

    # Create indexes
    op.create_index("ix_agent_states_agent_type", "agent_states", ["agent_type"])
    op.create_index("ix_agent_states_state", "agent_states", ["state"])

    # Memory tables
    op.create_table(
        "episodic_memories",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("goal_id", sa.String(36), nullable=True),
        sa.Column("task_id", sa.String(36), nullable=True),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("agents_involved", postgresql.JSON(), server_default="[]"),
        sa.Column("outcome", sa.String(20), nullable=True),
        sa.Column("importance", sa.Float(), server_default="0.5"),
        sa.Column("tags", postgresql.JSON(), server_default="[]"),
        sa.Column("metadata", postgresql.JSON(), server_default="{}"),
        sa.Column(
            "timestamp",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )

    op.create_index("ix_episodic_memories_goal_id", "episodic_memories", ["goal_id"])
    op.create_index("ix_episodic_memories_event_type", "episodic_memories", ["event_type"])
    op.create_index("ix_episodic_memories_timestamp", "episodic_memories", ["timestamp"])

    op.create_table(
        "strategic_memories",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("goal_id", sa.String(36), nullable=True),
        sa.Column("decision", sa.Text(), nullable=False),
        sa.Column("context", sa.Text(), nullable=False),
        sa.Column("alternatives", postgresql.JSON(), server_default="[]"),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("outcome", sa.String(50), nullable=True),
        sa.Column("lessons_learned", sa.Text(), nullable=True),
        sa.Column("confidence", sa.Float(), server_default="0.5"),
        sa.Column("tags", postgresql.JSON(), server_default="[]"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )

    op.create_index("ix_strategic_memories_goal_id", "strategic_memories", ["goal_id"])
    op.create_index("ix_strategic_memories_outcome", "strategic_memories", ["outcome"])

    # Tool execution logs
    op.create_table(
        "tool_executions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("task_id", sa.String(36), nullable=True),
        sa.Column("agent_id", sa.String(36), nullable=True),
        sa.Column("tool_name", sa.String(100), nullable=False),
        sa.Column("input_params", postgresql.JSON(), server_default="{}"),
        sa.Column("output", postgresql.JSON(), nullable=True),
        sa.Column("success", sa.Boolean(), server_default="true"),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("execution_time_ms", sa.Integer(), server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )

    op.create_index("ix_tool_executions_task_id", "tool_executions", ["task_id"])
    op.create_index("ix_tool_executions_tool_name", "tool_executions", ["tool_name"])


def downgrade() -> None:
    """Drop all tables."""
    op.drop_table("tool_executions")
    op.drop_table("strategic_memories")
    op.drop_table("episodic_memories")
    op.drop_table("agent_states")
    op.drop_table("tasks")
    op.drop_table("goals")

    # Drop enums
    op.execute("DROP TYPE IF EXISTS goalstatus")
    op.execute("DROP TYPE IF EXISTS taskstatus")
