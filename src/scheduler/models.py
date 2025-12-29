"""
Scheduled Tasks System Models.

Provides data models for task scheduling including:
- One-time and recurring schedules
- Cron expression support
- Task execution tracking
- Retry and timeout handling
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union
import uuid
import json


class ScheduleType(str, Enum):
    """Types of schedules."""
    ONCE = "once"  # Run once at a specific time
    INTERVAL = "interval"  # Run every N seconds/minutes/hours
    CRON = "cron"  # Cron expression
    DAILY = "daily"  # Run daily at a specific time
    WEEKLY = "weekly"  # Run weekly on specific days
    MONTHLY = "monthly"  # Run monthly on specific days


class ScheduleStatus(str, Enum):
    """Status of a scheduled task."""
    PENDING = "pending"  # Waiting for first run
    ACTIVE = "active"  # Actively scheduled
    RUNNING = "running"  # Currently executing
    PAUSED = "paused"  # Temporarily paused
    COMPLETED = "completed"  # Finished (for one-time tasks)
    FAILED = "failed"  # Failed after max retries
    CANCELLED = "cancelled"  # Cancelled by user


class ExecutionStatus(str, Enum):
    """Status of a task execution."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"  # Skipped due to overlap


class TaskType(str, Enum):
    """Types of tasks that can be scheduled."""
    FUNCTION = "function"  # Python function/coroutine
    HTTP = "http"  # HTTP webhook call
    GOAL = "goal"  # Agent goal execution
    COMMAND = "command"  # Shell command
    NOTIFICATION = "notification"  # Send notification


@dataclass
class IntervalSchedule:
    """Interval-based schedule configuration."""
    seconds: int = 0
    minutes: int = 0
    hours: int = 0
    days: int = 0

    @property
    def total_seconds(self) -> int:
        """Get total interval in seconds."""
        return (
            self.seconds +
            self.minutes * 60 +
            self.hours * 3600 +
            self.days * 86400
        )

    def to_dict(self) -> Dict[str, int]:
        """Convert to dictionary."""
        return {
            "seconds": self.seconds,
            "minutes": self.minutes,
            "hours": self.hours,
            "days": self.days,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, int]) -> "IntervalSchedule":
        """Create from dictionary."""
        return cls(
            seconds=data.get("seconds", 0),
            minutes=data.get("minutes", 0),
            hours=data.get("hours", 0),
            days=data.get("days", 0),
        )


@dataclass
class DailySchedule:
    """Daily schedule configuration."""
    hour: int = 0  # 0-23
    minute: int = 0  # 0-59
    second: int = 0  # 0-59
    timezone: str = "UTC"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "hour": self.hour,
            "minute": self.minute,
            "second": self.second,
            "timezone": self.timezone,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DailySchedule":
        """Create from dictionary."""
        return cls(
            hour=data.get("hour", 0),
            minute=data.get("minute", 0),
            second=data.get("second", 0),
            timezone=data.get("timezone", "UTC"),
        )


@dataclass
class WeeklySchedule:
    """Weekly schedule configuration."""
    days_of_week: List[int] = field(default_factory=lambda: [0])  # 0=Monday, 6=Sunday
    hour: int = 0
    minute: int = 0
    second: int = 0
    timezone: str = "UTC"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "days_of_week": self.days_of_week,
            "hour": self.hour,
            "minute": self.minute,
            "second": self.second,
            "timezone": self.timezone,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WeeklySchedule":
        """Create from dictionary."""
        return cls(
            days_of_week=data.get("days_of_week", [0]),
            hour=data.get("hour", 0),
            minute=data.get("minute", 0),
            second=data.get("second", 0),
            timezone=data.get("timezone", "UTC"),
        )


@dataclass
class MonthlySchedule:
    """Monthly schedule configuration."""
    days_of_month: List[int] = field(default_factory=lambda: [1])  # 1-31, -1 for last day
    hour: int = 0
    minute: int = 0
    second: int = 0
    timezone: str = "UTC"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "days_of_month": self.days_of_month,
            "hour": self.hour,
            "minute": self.minute,
            "second": self.second,
            "timezone": self.timezone,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MonthlySchedule":
        """Create from dictionary."""
        return cls(
            days_of_month=data.get("days_of_month", [1]),
            hour=data.get("hour", 0),
            minute=data.get("minute", 0),
            second=data.get("second", 0),
            timezone=data.get("timezone", "UTC"),
        )


@dataclass
class CronSchedule:
    """Cron expression schedule configuration."""
    expression: str = "* * * * *"  # minute hour day month weekday
    timezone: str = "UTC"

    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary."""
        return {
            "expression": self.expression,
            "timezone": self.timezone,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> "CronSchedule":
        """Create from dictionary."""
        return cls(
            expression=data.get("expression", "* * * * *"),
            timezone=data.get("timezone", "UTC"),
        )


@dataclass
class TaskPayload:
    """Payload for task execution."""
    task_type: TaskType = TaskType.FUNCTION

    # For FUNCTION type
    function_name: Optional[str] = None
    function_args: List[Any] = field(default_factory=list)
    function_kwargs: Dict[str, Any] = field(default_factory=dict)

    # For HTTP type
    http_url: Optional[str] = None
    http_method: str = "POST"
    http_headers: Dict[str, str] = field(default_factory=dict)
    http_body: Optional[Dict[str, Any]] = None
    http_timeout: int = 30

    # For GOAL type
    goal_description: Optional[str] = None
    goal_config: Dict[str, Any] = field(default_factory=dict)

    # For COMMAND type
    command: Optional[str] = None
    command_args: List[str] = field(default_factory=list)
    command_timeout: int = 300

    # For NOTIFICATION type
    notification_type: Optional[str] = None
    notification_recipient: Optional[str] = None
    notification_content: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "task_type": self.task_type.value,
            "function_name": self.function_name,
            "function_args": self.function_args,
            "function_kwargs": self.function_kwargs,
            "http_url": self.http_url,
            "http_method": self.http_method,
            "http_headers": self.http_headers,
            "http_body": self.http_body,
            "http_timeout": self.http_timeout,
            "goal_description": self.goal_description,
            "goal_config": self.goal_config,
            "command": self.command,
            "command_args": self.command_args,
            "command_timeout": self.command_timeout,
            "notification_type": self.notification_type,
            "notification_recipient": self.notification_recipient,
            "notification_content": self.notification_content,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TaskPayload":
        """Create from dictionary."""
        return cls(
            task_type=TaskType(data.get("task_type", "function")),
            function_name=data.get("function_name"),
            function_args=data.get("function_args", []),
            function_kwargs=data.get("function_kwargs", {}),
            http_url=data.get("http_url"),
            http_method=data.get("http_method", "POST"),
            http_headers=data.get("http_headers", {}),
            http_body=data.get("http_body"),
            http_timeout=data.get("http_timeout", 30),
            goal_description=data.get("goal_description"),
            goal_config=data.get("goal_config", {}),
            command=data.get("command"),
            command_args=data.get("command_args", []),
            command_timeout=data.get("command_timeout", 300),
            notification_type=data.get("notification_type"),
            notification_recipient=data.get("notification_recipient"),
            notification_content=data.get("notification_content", {}),
        )


@dataclass
class TaskExecution:
    """Record of a task execution."""
    execution_id: str = field(default_factory=lambda: f"exec_{uuid.uuid4().hex[:12]}")
    task_id: str = ""
    scheduled_time: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    status: ExecutionStatus = ExecutionStatus.PENDING

    # Result
    result: Optional[Any] = None
    error: Optional[str] = None
    error_traceback: Optional[str] = None

    # Metrics
    retry_count: int = 0
    duration_ms: Optional[int] = None

    # Metadata
    worker_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def start(self, worker_id: Optional[str] = None) -> None:
        """Mark execution as started."""
        self.status = ExecutionStatus.RUNNING
        self.started_at = datetime.utcnow()
        self.worker_id = worker_id

    def complete(self, result: Any = None) -> None:
        """Mark execution as completed."""
        self.status = ExecutionStatus.COMPLETED
        self.completed_at = datetime.utcnow()
        self.result = result
        if self.started_at:
            delta = self.completed_at - self.started_at
            self.duration_ms = int(delta.total_seconds() * 1000)

    def fail(self, error: str, traceback: Optional[str] = None) -> None:
        """Mark execution as failed."""
        self.status = ExecutionStatus.FAILED
        self.completed_at = datetime.utcnow()
        self.error = error
        self.error_traceback = traceback
        if self.started_at:
            delta = self.completed_at - self.started_at
            self.duration_ms = int(delta.total_seconds() * 1000)

    def timeout(self) -> None:
        """Mark execution as timed out."""
        self.status = ExecutionStatus.TIMEOUT
        self.completed_at = datetime.utcnow()
        self.error = "Task execution timed out"
        if self.started_at:
            delta = self.completed_at - self.started_at
            self.duration_ms = int(delta.total_seconds() * 1000)

    def skip(self, reason: str = "Overlapping execution") -> None:
        """Mark execution as skipped."""
        self.status = ExecutionStatus.SKIPPED
        self.completed_at = datetime.utcnow()
        self.error = reason

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "execution_id": self.execution_id,
            "task_id": self.task_id,
            "scheduled_time": self.scheduled_time.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "status": self.status.value,
            "result": self.result if isinstance(self.result, (str, int, float, bool, type(None))) else str(self.result),
            "error": self.error,
            "retry_count": self.retry_count,
            "duration_ms": self.duration_ms,
            "worker_id": self.worker_id,
        }


@dataclass
class ScheduledTask:
    """A scheduled task."""
    task_id: str = field(default_factory=lambda: f"task_{uuid.uuid4().hex[:12]}")
    name: str = ""
    description: Optional[str] = None

    # Schedule configuration
    schedule_type: ScheduleType = ScheduleType.ONCE
    schedule_config: Union[
        IntervalSchedule,
        DailySchedule,
        WeeklySchedule,
        MonthlySchedule,
        CronSchedule,
        Dict[str, Any],
    ] = field(default_factory=dict)

    # For ONCE type
    run_at: Optional[datetime] = None

    # Task payload
    payload: TaskPayload = field(default_factory=TaskPayload)

    # Status
    status: ScheduleStatus = ScheduleStatus.PENDING

    # Execution settings
    timeout_seconds: int = 300
    max_retries: int = 3
    retry_delay_seconds: int = 60
    allow_overlap: bool = False  # Allow concurrent executions

    # Timing
    next_run_at: Optional[datetime] = None
    last_run_at: Optional[datetime] = None
    start_date: Optional[datetime] = None  # Don't run before this
    end_date: Optional[datetime] = None  # Don't run after this

    # Execution history
    executions: List[TaskExecution] = field(default_factory=list)
    total_runs: int = 0
    successful_runs: int = 0
    failed_runs: int = 0

    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    # Ownership
    owner_id: Optional[str] = None
    tenant_id: Optional[str] = None

    # Tags and metadata
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_active(self) -> bool:
        """Check if task is active and should run."""
        if self.status not in (ScheduleStatus.ACTIVE, ScheduleStatus.PENDING):
            return False

        now = datetime.utcnow()

        if self.start_date and now < self.start_date:
            return False

        if self.end_date and now > self.end_date:
            return False

        return True

    @property
    def is_due(self) -> bool:
        """Check if task is due to run."""
        if not self.is_active:
            return False

        if self.next_run_at is None:
            return False

        return datetime.utcnow() >= self.next_run_at

    @property
    def is_running(self) -> bool:
        """Check if task is currently running."""
        return self.status == ScheduleStatus.RUNNING

    @property
    def last_execution(self) -> Optional[TaskExecution]:
        """Get the last execution."""
        return self.executions[-1] if self.executions else None

    @property
    def success_rate(self) -> float:
        """Get success rate."""
        if self.total_runs == 0:
            return 0.0
        return self.successful_runs / self.total_runs

    def add_execution(self, execution: TaskExecution) -> None:
        """Add an execution record."""
        self.executions.append(execution)
        self.total_runs += 1
        self.last_run_at = execution.scheduled_time
        self.updated_at = datetime.utcnow()

        if execution.status == ExecutionStatus.COMPLETED:
            self.successful_runs += 1
        elif execution.status in (ExecutionStatus.FAILED, ExecutionStatus.TIMEOUT):
            self.failed_runs += 1

        # For one-time tasks, mark as completed
        if self.schedule_type == ScheduleType.ONCE:
            self.status = ScheduleStatus.COMPLETED

    def pause(self) -> bool:
        """Pause the task."""
        if self.status in (ScheduleStatus.ACTIVE, ScheduleStatus.PENDING):
            self.status = ScheduleStatus.PAUSED
            self.updated_at = datetime.utcnow()
            return True
        return False

    def resume(self) -> bool:
        """Resume the task."""
        if self.status == ScheduleStatus.PAUSED:
            self.status = ScheduleStatus.ACTIVE
            self.updated_at = datetime.utcnow()
            return True
        return False

    def cancel(self) -> bool:
        """Cancel the task."""
        if self.status not in (ScheduleStatus.COMPLETED, ScheduleStatus.CANCELLED):
            self.status = ScheduleStatus.CANCELLED
            self.updated_at = datetime.utcnow()
            return True
        return False

    def to_dict(self, include_executions: bool = False) -> Dict[str, Any]:
        """Convert to dictionary."""
        # Convert schedule config
        if hasattr(self.schedule_config, 'to_dict'):
            schedule_config = self.schedule_config.to_dict()
        else:
            schedule_config = self.schedule_config

        result = {
            "task_id": self.task_id,
            "name": self.name,
            "description": self.description,
            "schedule_type": self.schedule_type.value,
            "schedule_config": schedule_config,
            "run_at": self.run_at.isoformat() if self.run_at else None,
            "payload": self.payload.to_dict(),
            "status": self.status.value,
            "timeout_seconds": self.timeout_seconds,
            "max_retries": self.max_retries,
            "retry_delay_seconds": self.retry_delay_seconds,
            "allow_overlap": self.allow_overlap,
            "next_run_at": self.next_run_at.isoformat() if self.next_run_at else None,
            "last_run_at": self.last_run_at.isoformat() if self.last_run_at else None,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "total_runs": self.total_runs,
            "successful_runs": self.successful_runs,
            "failed_runs": self.failed_runs,
            "success_rate": self.success_rate,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "owner_id": self.owner_id,
            "tenant_id": self.tenant_id,
            "tags": self.tags,
        }

        if include_executions:
            result["executions"] = [e.to_dict() for e in self.executions[-10:]]  # Last 10

        return result

    @classmethod
    def create_once(
        cls,
        name: str,
        run_at: datetime,
        payload: TaskPayload,
        **kwargs,
    ) -> "ScheduledTask":
        """Create a one-time task."""
        return cls(
            name=name,
            schedule_type=ScheduleType.ONCE,
            run_at=run_at,
            next_run_at=run_at,
            payload=payload,
            **kwargs,
        )

    @classmethod
    def create_interval(
        cls,
        name: str,
        interval: IntervalSchedule,
        payload: TaskPayload,
        **kwargs,
    ) -> "ScheduledTask":
        """Create an interval-based task."""
        task = cls(
            name=name,
            schedule_type=ScheduleType.INTERVAL,
            schedule_config=interval,
            payload=payload,
            status=ScheduleStatus.ACTIVE,
            **kwargs,
        )
        task.next_run_at = datetime.utcnow() + timedelta(seconds=interval.total_seconds)
        return task

    @classmethod
    def create_daily(
        cls,
        name: str,
        schedule: DailySchedule,
        payload: TaskPayload,
        **kwargs,
    ) -> "ScheduledTask":
        """Create a daily task."""
        return cls(
            name=name,
            schedule_type=ScheduleType.DAILY,
            schedule_config=schedule,
            payload=payload,
            status=ScheduleStatus.ACTIVE,
            **kwargs,
        )

    @classmethod
    def create_weekly(
        cls,
        name: str,
        schedule: WeeklySchedule,
        payload: TaskPayload,
        **kwargs,
    ) -> "ScheduledTask":
        """Create a weekly task."""
        return cls(
            name=name,
            schedule_type=ScheduleType.WEEKLY,
            schedule_config=schedule,
            payload=payload,
            status=ScheduleStatus.ACTIVE,
            **kwargs,
        )

    @classmethod
    def create_monthly(
        cls,
        name: str,
        schedule: MonthlySchedule,
        payload: TaskPayload,
        **kwargs,
    ) -> "ScheduledTask":
        """Create a monthly task."""
        return cls(
            name=name,
            schedule_type=ScheduleType.MONTHLY,
            schedule_config=schedule,
            payload=payload,
            status=ScheduleStatus.ACTIVE,
            **kwargs,
        )

    @classmethod
    def create_cron(
        cls,
        name: str,
        cron_expression: str,
        payload: TaskPayload,
        timezone: str = "UTC",
        **kwargs,
    ) -> "ScheduledTask":
        """Create a cron-based task."""
        return cls(
            name=name,
            schedule_type=ScheduleType.CRON,
            schedule_config=CronSchedule(expression=cron_expression, timezone=timezone),
            payload=payload,
            status=ScheduleStatus.ACTIVE,
            **kwargs,
        )


@dataclass
class SchedulerConfig:
    """Scheduler system configuration."""
    # Polling
    poll_interval_seconds: int = 1
    batch_size: int = 100

    # Execution
    default_timeout_seconds: int = 300
    default_max_retries: int = 3
    max_concurrent_tasks: int = 10

    # Retention
    execution_retention_days: int = 30
    max_executions_per_task: int = 100

    # Limits
    max_tasks_per_owner: int = 100

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "poll_interval_seconds": self.poll_interval_seconds,
            "batch_size": self.batch_size,
            "default_timeout_seconds": self.default_timeout_seconds,
            "default_max_retries": self.default_max_retries,
            "max_concurrent_tasks": self.max_concurrent_tasks,
            "execution_retention_days": self.execution_retention_days,
            "max_executions_per_task": self.max_executions_per_task,
            "max_tasks_per_owner": self.max_tasks_per_owner,
        }


@dataclass
class TaskListResponse:
    """Paginated list of tasks."""
    tasks: List[ScheduledTask]
    total: int
    offset: int
    limit: int

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "tasks": [t.to_dict() for t in self.tasks],
            "total": self.total,
            "offset": self.offset,
            "limit": self.limit,
        }


@dataclass
class ExecutionListResponse:
    """Paginated list of executions."""
    executions: List[TaskExecution]
    total: int
    offset: int
    limit: int

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "executions": [e.to_dict() for e in self.executions],
            "total": self.total,
            "offset": self.offset,
            "limit": self.limit,
        }


@dataclass
class SchedulerStats:
    """Scheduler statistics."""
    total_tasks: int = 0
    active_tasks: int = 0
    paused_tasks: int = 0
    running_tasks: int = 0

    total_executions: int = 0
    successful_executions: int = 0
    failed_executions: int = 0

    # By type
    by_schedule_type: Dict[str, int] = field(default_factory=dict)
    by_task_type: Dict[str, int] = field(default_factory=dict)

    # Timing
    avg_duration_ms: float = 0.0
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_tasks": self.total_tasks,
            "active_tasks": self.active_tasks,
            "paused_tasks": self.paused_tasks,
            "running_tasks": self.running_tasks,
            "total_executions": self.total_executions,
            "successful_executions": self.successful_executions,
            "failed_executions": self.failed_executions,
            "by_schedule_type": self.by_schedule_type,
            "by_task_type": self.by_task_type,
            "avg_duration_ms": self.avg_duration_ms,
            "period_start": self.period_start.isoformat() if self.period_start else None,
            "period_end": self.period_end.isoformat() if self.period_end else None,
        }
