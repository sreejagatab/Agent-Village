"""
Structured message protocol for Agent Village.

This module defines the core communication primitives used by all agents.
All inter-agent communication must use these structured messages - no free chat.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from ulid import ULID


class MessageType(str, Enum):
    """Types of messages in the system."""

    # Goal lifecycle
    GOAL_CREATED = "goal_created"
    GOAL_UPDATED = "goal_updated"
    GOAL_COMPLETED = "goal_completed"
    GOAL_FAILED = "goal_failed"
    GOAL_CANCELLED = "goal_cancelled"

    # Task lifecycle
    TASK_ASSIGNED = "task_assigned"
    TASK_STARTED = "task_started"
    TASK_PROGRESS = "task_progress"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"

    # Agent lifecycle
    AGENT_SPAWNED = "agent_spawned"
    AGENT_READY = "agent_ready"
    AGENT_BUSY = "agent_busy"
    AGENT_STOPPED = "agent_stopped"

    # Control flow
    REQUEST = "request"
    RESPONSE = "response"
    DELEGATE = "delegate"
    ESCALATE = "escalate"

    # Human interaction
    APPROVAL_REQUIRED = "approval_required"
    APPROVAL_GRANTED = "approval_granted"
    APPROVAL_DENIED = "approval_denied"

    # System
    HEARTBEAT = "heartbeat"
    ERROR = "error"


class Priority(int, Enum):
    """Message priority levels."""

    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4
    EMERGENCY = 5


class TaskStatus(str, Enum):
    """Task execution status."""

    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    AWAITING_APPROVAL = "awaiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class GoalStatus(str, Enum):
    """Goal execution status."""

    PENDING = "pending"
    CREATED = "created"
    PLANNING = "planning"
    IN_PROGRESS = "in_progress"
    EXECUTING = "executing"
    VERIFYING = "verifying"
    REFLECTING = "reflecting"
    AWAITING_HUMAN = "awaiting_human"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


def generate_id() -> str:
    """Generate a unique ID using ULID (sortable, time-based)."""
    return str(ULID())


def utc_now() -> datetime:
    """Get current UTC timestamp."""
    return datetime.now(timezone.utc)


@dataclass
class Constraints:
    """Constraints for task execution."""

    # Resource limits
    max_tokens: int = 10_000
    max_time_seconds: int = 300
    max_retries: int = 3

    # Tool permissions
    allowed_tools: set[str] = field(default_factory=set)
    denied_tools: set[str] = field(default_factory=set)

    # Risk level
    risk_level: str = "low"  # low, medium, high, critical

    # Human approval
    requires_approval: bool = False
    approval_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "max_tokens": self.max_tokens,
            "max_time_seconds": self.max_time_seconds,
            "max_retries": self.max_retries,
            "allowed_tools": list(self.allowed_tools),
            "denied_tools": list(self.denied_tools),
            "risk_level": self.risk_level,
            "requires_approval": self.requires_approval,
            "approval_reason": self.approval_reason,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Constraints":
        """Create from dictionary."""
        return cls(
            max_tokens=data.get("max_tokens", 10_000),
            max_time_seconds=data.get("max_time_seconds", 300),
            max_retries=data.get("max_retries", 3),
            allowed_tools=set(data.get("allowed_tools", [])),
            denied_tools=set(data.get("denied_tools", [])),
            risk_level=data.get("risk_level", "low"),
            requires_approval=data.get("requires_approval", False),
            approval_reason=data.get("approval_reason"),
        )


@dataclass
class Task:
    """A unit of work to be executed by an agent."""

    id: str = field(default_factory=generate_id)
    goal_id: str = ""
    parent_task_id: str | None = None

    # Task definition
    description: str = ""
    objective: str = ""
    expected_output: str = ""

    # Execution
    status: TaskStatus = TaskStatus.PENDING
    assigned_agent_id: str | None = None
    assigned_agent_type: str | None = None

    # Constraints
    constraints: Constraints = field(default_factory=Constraints)

    # Context
    context: dict[str, Any] = field(default_factory=dict)
    dependencies: list[str] = field(default_factory=list)

    # Results
    result: Any = None
    error: str | None = None

    # Timestamps
    created_at: datetime = field(default_factory=utc_now)
    started_at: datetime | None = None
    completed_at: datetime | None = None

    # Metrics
    tokens_used: int = 0
    retry_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "goal_id": self.goal_id,
            "parent_task_id": self.parent_task_id,
            "description": self.description,
            "objective": self.objective,
            "expected_output": self.expected_output,
            "status": self.status.value,
            "assigned_agent_id": self.assigned_agent_id,
            "assigned_agent_type": self.assigned_agent_type,
            "constraints": self.constraints.to_dict(),
            "context": self.context,
            "dependencies": self.dependencies,
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "tokens_used": self.tokens_used,
            "retry_count": self.retry_count,
        }


@dataclass
class Goal:
    """A high-level objective to be achieved by the agent system."""

    id: str = field(default_factory=generate_id)

    # Goal definition
    description: str = ""
    success_criteria: list[str] = field(default_factory=list)
    priority: Priority = Priority.NORMAL

    # Execution
    status: GoalStatus = GoalStatus.CREATED
    tasks: list[Task] = field(default_factory=list)

    # Context
    context: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    # Safety
    constraints: Constraints = field(default_factory=Constraints)

    # Results
    result: Any = None
    error: str | None = None

    # Timestamps
    created_at: datetime = field(default_factory=utc_now)
    started_at: datetime | None = None
    completed_at: datetime | None = None

    # Metrics
    total_tokens_used: int = 0
    total_agents_spawned: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "description": self.description,
            "success_criteria": self.success_criteria,
            "priority": self.priority.value,
            "status": self.status.value,
            "tasks": [t.to_dict() for t in self.tasks],
            "context": self.context,
            "metadata": self.metadata,
            "constraints": self.constraints.to_dict(),
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "total_tokens_used": self.total_tokens_used,
            "total_agents_spawned": self.total_agents_spawned,
        }


@dataclass
class GoalContext:
    """Runtime context for goal execution."""

    goal: Goal
    depth: int = 0
    tokens_used: int = 0
    agents_spawned: int = 0
    start_time: datetime = field(default_factory=utc_now)
    parent_context: "GoalContext | None" = None

    # Execution state
    current_task_id: str | None = None
    completed_tasks: list[str] = field(default_factory=list)
    failed_tasks: list[str] = field(default_factory=list)

    def get_total_depth(self) -> int:
        """Calculate total depth including parent contexts."""
        if self.parent_context is None:
            return self.depth
        return self.depth + self.parent_context.get_total_depth()

    def get_total_tokens(self) -> int:
        """Calculate total tokens including parent contexts."""
        if self.parent_context is None:
            return self.tokens_used
        return self.tokens_used + self.parent_context.get_total_tokens()

    def get_total_agents(self) -> int:
        """Calculate total agents spawned including parent contexts."""
        if self.parent_context is None:
            return self.agents_spawned
        return self.agents_spawned + self.parent_context.get_total_agents()


@dataclass
class AgentMessage:
    """
    Structured message for inter-agent communication.

    All communication between agents MUST use this format.
    No free-form chat is allowed.
    """

    id: str = field(default_factory=generate_id)
    message_type: MessageType = MessageType.REQUEST

    # Routing
    sender: str = ""  # Agent ID
    sender_type: str = ""  # Agent type (governor, planner, tool, etc.)
    recipient: str = ""  # Agent ID or "broadcast"
    recipient_type: str = ""  # Target agent type

    # Content
    goal_id: str = ""
    task_id: str | None = None
    task: Task | None = None

    # Payload
    content: dict[str, Any] = field(default_factory=dict)
    constraints: Constraints = field(default_factory=Constraints)

    # Metadata
    priority: Priority = Priority.NORMAL
    parent_message_id: str | None = None
    correlation_id: str | None = None  # For request/response matching

    # Timestamps
    timestamp: datetime = field(default_factory=utc_now)
    expires_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "message_type": self.message_type.value,
            "sender": self.sender,
            "sender_type": self.sender_type,
            "recipient": self.recipient,
            "recipient_type": self.recipient_type,
            "goal_id": self.goal_id,
            "task_id": self.task_id,
            "task": self.task.to_dict() if self.task else None,
            "content": self.content,
            "constraints": self.constraints.to_dict(),
            "priority": self.priority.value,
            "parent_message_id": self.parent_message_id,
            "correlation_id": self.correlation_id,
            "timestamp": self.timestamp.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }

    def create_response(
        self,
        sender: str,
        sender_type: str,
        content: dict[str, Any],
        message_type: MessageType = MessageType.RESPONSE,
    ) -> "AgentMessage":
        """Create a response message to this message."""
        return AgentMessage(
            message_type=message_type,
            sender=sender,
            sender_type=sender_type,
            recipient=self.sender,
            recipient_type=self.sender_type,
            goal_id=self.goal_id,
            task_id=self.task_id,
            content=content,
            priority=self.priority,
            parent_message_id=self.id,
            correlation_id=self.correlation_id or self.id,
        )


@dataclass
class AgentResult:
    """Result of an agent's task execution."""

    task_id: str
    agent_id: str
    agent_type: str

    # Outcome
    success: bool = False
    result: Any = None
    error: str | None = None

    # Quality metrics
    confidence: float = 0.0  # 0-1 confidence in the result
    quality_score: float = 0.0  # 0-1 quality assessment

    # Resource usage
    tokens_used: int = 0
    execution_time_seconds: float = 0.0

    # Metadata
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "task_id": self.task_id,
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "success": self.success,
            "result": self.result,
            "error": self.error,
            "confidence": self.confidence,
            "quality_score": self.quality_score,
            "tokens_used": self.tokens_used,
            "execution_time_seconds": self.execution_time_seconds,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class Reflection:
    """Agent's self-reflection on its performance."""

    agent_id: str
    task_id: str

    # Assessment
    performance_score: float = 0.0  # 0-1
    improvements: list[str] = field(default_factory=list)
    lessons_learned: list[str] = field(default_factory=list)

    # What went well/poorly
    successes: list[str] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)

    # Recommendations
    recommendations: list[str] = field(default_factory=list)

    timestamp: datetime = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "agent_id": self.agent_id,
            "task_id": self.task_id,
            "performance_score": self.performance_score,
            "improvements": self.improvements,
            "lessons_learned": self.lessons_learned,
            "successes": self.successes,
            "failures": self.failures,
            "recommendations": self.recommendations,
            "timestamp": self.timestamp.isoformat(),
        }
