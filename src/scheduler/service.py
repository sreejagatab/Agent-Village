"""
Scheduler Service Layer.

Provides task scheduling, storage, and execution management.
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable, Coroutine, Dict, List, Optional, Set
import uuid
import structlog

from .models import (
    ScheduledTask,
    TaskPayload,
    TaskExecution,
    ScheduleType,
    ScheduleStatus,
    ExecutionStatus,
    TaskType,
    IntervalSchedule,
    DailySchedule,
    WeeklySchedule,
    MonthlySchedule,
    CronSchedule,
    SchedulerConfig,
    SchedulerStats,
)
from .cron import CronExpression, CronParseError


logger = structlog.get_logger()


class SchedulerError(Exception):
    """Base scheduler error."""
    pass


class TaskNotFoundError(SchedulerError):
    """Task not found."""
    pass


class TaskExecutionError(SchedulerError):
    """Task execution failed."""
    pass


class InvalidScheduleError(SchedulerError):
    """Invalid schedule configuration."""
    pass


@dataclass
class SchedulerStore:
    """
    In-memory storage for scheduled tasks.

    Provides efficient indexing for task lookups.
    """

    tasks: Dict[str, ScheduledTask] = field(default_factory=dict)
    by_status: Dict[ScheduleStatus, Set[str]] = field(default_factory=dict)
    by_type: Dict[ScheduleType, Set[str]] = field(default_factory=dict)
    by_tag: Dict[str, Set[str]] = field(default_factory=dict)
    executions: Dict[str, List[TaskExecution]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Initialize index sets."""
        for status in ScheduleStatus:
            self.by_status[status] = set()
        for stype in ScheduleType:
            self.by_type[stype] = set()

    def add(self, task: ScheduledTask) -> None:
        """Add a task to storage."""
        self.tasks[task.task_id] = task
        self.by_status[task.status].add(task.task_id)
        self.by_type[task.schedule_type].add(task.task_id)

        for tag in task.tags:
            if tag not in self.by_tag:
                self.by_tag[tag] = set()
            self.by_tag[tag].add(task.task_id)

        self.executions[task.task_id] = []

    def update(self, task: ScheduledTask) -> None:
        """Update a task in storage."""
        task_id = task.task_id

        # Remove from all status indexes first (since we might not know the old status)
        for status_set in self.by_status.values():
            status_set.discard(task_id)

        # Remove from all type indexes
        for type_set in self.by_type.values():
            type_set.discard(task_id)

        # Remove from all tag indexes
        for tag_set in self.by_tag.values():
            tag_set.discard(task_id)

        # Add to correct indexes
        self.tasks[task_id] = task
        self.by_status[task.status].add(task_id)
        self.by_type[task.schedule_type].add(task_id)

        for tag in task.tags:
            if tag not in self.by_tag:
                self.by_tag[tag] = set()
            self.by_tag[tag].add(task_id)

    def remove(self, task_id: str) -> Optional[ScheduledTask]:
        """Remove a task from storage."""
        task = self.tasks.pop(task_id, None)
        if task:
            self.by_status[task.status].discard(task_id)
            self.by_type[task.schedule_type].discard(task_id)
            for tag in task.tags:
                if tag in self.by_tag:
                    self.by_tag[tag].discard(task_id)
            self.executions.pop(task_id, None)
        return task

    def get(self, task_id: str) -> Optional[ScheduledTask]:
        """Get a task by ID."""
        return self.tasks.get(task_id)

    def get_by_status(self, status: ScheduleStatus) -> List[ScheduledTask]:
        """Get tasks by status."""
        return [self.tasks[tid] for tid in self.by_status.get(status, set())]

    def get_by_type(self, schedule_type: ScheduleType) -> List[ScheduledTask]:
        """Get tasks by schedule type."""
        return [self.tasks[tid] for tid in self.by_type.get(schedule_type, set())]

    def get_by_tag(self, tag: str) -> List[ScheduledTask]:
        """Get tasks by tag."""
        return [self.tasks[tid] for tid in self.by_tag.get(tag, set())]

    def get_all(self) -> List[ScheduledTask]:
        """Get all tasks."""
        return list(self.tasks.values())

    def add_execution(self, task_id: str, execution: TaskExecution) -> None:
        """Add an execution record for a task."""
        if task_id in self.executions:
            self.executions[task_id].append(execution)

    def get_executions(
        self,
        task_id: str,
        limit: Optional[int] = None,
    ) -> List[TaskExecution]:
        """Get execution history for a task."""
        execs = self.executions.get(task_id, [])
        if limit:
            return execs[-limit:]
        return execs

    def count(self) -> int:
        """Get total task count."""
        return len(self.tasks)

    def count_by_status(self, status: ScheduleStatus) -> int:
        """Get count of tasks with status."""
        return len(self.by_status.get(status, set()))


# Type alias for task handlers
TaskHandler = Callable[[ScheduledTask], Coroutine[Any, Any, Any]]


class SchedulerService:
    """
    Main scheduler service.

    Manages task scheduling, execution, and lifecycle.
    """

    def __init__(self, config: Optional[SchedulerConfig] = None):
        """
        Initialize the scheduler service.

        Args:
            config: Scheduler configuration.
        """
        self.config = config or SchedulerConfig()
        self.store = SchedulerStore()
        self._running = False
        self._loop_task: Optional[asyncio.Task] = None
        self._handlers: Dict[TaskType, TaskHandler] = {}
        self._lock = asyncio.Lock()

        # Stats
        self._total_executions = 0
        self._successful_executions = 0
        self._failed_executions = 0
        self._start_time: Optional[datetime] = None

    async def start(self) -> None:
        """Start the scheduler loop."""
        if self._running:
            return

        self._running = True
        self._start_time = datetime.utcnow()
        self._loop_task = asyncio.create_task(self._scheduler_loop())

        logger.info(
            "scheduler_started",
            poll_interval=self.config.poll_interval_seconds,
        )

    async def stop(self) -> None:
        """Stop the scheduler loop."""
        self._running = False

        if self._loop_task:
            self._loop_task.cancel()
            try:
                await self._loop_task
            except asyncio.CancelledError:
                pass
            self._loop_task = None

        logger.info("scheduler_stopped")

    def register_handler(
        self,
        task_type: TaskType,
        handler: TaskHandler,
    ) -> None:
        """
        Register a handler for a task type.

        Args:
            task_type: Type of task to handle.
            handler: Async function to execute the task.
        """
        self._handlers[task_type] = handler
        logger.debug("handler_registered", task_type=task_type.value)

    async def create_task(self, task: ScheduledTask) -> ScheduledTask:
        """
        Create a new scheduled task.

        Args:
            task: Task to create.

        Returns:
            Created task with calculated next_run_at.
        """
        # Validate schedule configuration
        self._validate_schedule(task)

        # Calculate initial next_run_at
        task.next_run_at = self._calculate_next_run(task)
        task.created_at = datetime.utcnow()
        task.updated_at = task.created_at

        # Activate task if auto-start
        if task.status == ScheduleStatus.PENDING:
            task.status = ScheduleStatus.ACTIVE

        async with self._lock:
            self.store.add(task)

        logger.info(
            "task_created",
            task_id=task.task_id,
            name=task.name,
            schedule_type=task.schedule_type.value,
            next_run_at=task.next_run_at.isoformat() if task.next_run_at else None,
        )

        return task

    async def update_task(
        self,
        task_id: str,
        **updates: Any,
    ) -> ScheduledTask:
        """
        Update a scheduled task.

        Args:
            task_id: Task ID to update.
            **updates: Fields to update.

        Returns:
            Updated task.
        """
        async with self._lock:
            task = self.store.get(task_id)
            if not task:
                raise TaskNotFoundError(f"Task not found: {task_id}")

            # Apply updates
            for key, value in updates.items():
                if hasattr(task, key):
                    setattr(task, key, value)

            task.updated_at = datetime.utcnow()

            # Recalculate next_run_at if schedule changed
            if any(k in updates for k in ['schedule_type', 'schedule_config']):
                self._validate_schedule(task)
                task.next_run_at = self._calculate_next_run(task)

            self.store.update(task)

        logger.info(
            "task_updated",
            task_id=task_id,
            updates=list(updates.keys()),
        )

        return task

    async def delete_task(self, task_id: str) -> bool:
        """
        Delete a scheduled task.

        Args:
            task_id: Task ID to delete.

        Returns:
            True if deleted, False if not found.
        """
        async with self._lock:
            task = self.store.remove(task_id)

        if task:
            logger.info("task_deleted", task_id=task_id)
            return True
        return False

    async def get_task(self, task_id: str) -> Optional[ScheduledTask]:
        """Get a task by ID."""
        return self.store.get(task_id)

    async def list_tasks(
        self,
        status: Optional[ScheduleStatus] = None,
        schedule_type: Optional[ScheduleType] = None,
        tag: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[ScheduledTask]:
        """
        List scheduled tasks with filters.

        Args:
            status: Filter by status.
            schedule_type: Filter by schedule type.
            tag: Filter by tag.
            limit: Maximum results.
            offset: Skip first N results.

        Returns:
            List of matching tasks.
        """
        tasks: List[ScheduledTask]

        if status:
            tasks = self.store.get_by_status(status)
        elif schedule_type:
            tasks = self.store.get_by_type(schedule_type)
        elif tag:
            tasks = self.store.get_by_tag(tag)
        else:
            tasks = self.store.get_all()

        # Apply additional filters
        if status and (schedule_type or tag):
            if schedule_type:
                tasks = [t for t in tasks if t.schedule_type == schedule_type]
            if tag:
                tasks = [t for t in tasks if tag in t.tags]

        # Sort by next_run_at
        tasks.sort(key=lambda t: t.next_run_at or datetime.max)

        return tasks[offset:offset + limit]

    async def pause_task(self, task_id: str) -> ScheduledTask:
        """
        Pause a scheduled task.

        Args:
            task_id: Task ID to pause.

        Returns:
            Updated task.
        """
        return await self.update_task(task_id, status=ScheduleStatus.PAUSED)

    async def resume_task(self, task_id: str) -> ScheduledTask:
        """
        Resume a paused task.

        Args:
            task_id: Task ID to resume.

        Returns:
            Updated task.
        """
        task = await self.update_task(task_id, status=ScheduleStatus.ACTIVE)

        # Recalculate next_run_at
        task.next_run_at = self._calculate_next_run(task)
        async with self._lock:
            self.store.update(task)

        return task

    async def trigger_task(self, task_id: str) -> TaskExecution:
        """
        Manually trigger a task execution.

        Args:
            task_id: Task ID to trigger.

        Returns:
            Execution result.
        """
        task = self.store.get(task_id)
        if not task:
            raise TaskNotFoundError(f"Task not found: {task_id}")

        return await self._execute_task(task, manual=True)

    async def get_due_tasks(self) -> List[ScheduledTask]:
        """
        Get all tasks that are due for execution.

        Returns:
            List of due tasks.
        """
        now = datetime.utcnow()
        active_tasks = self.store.get_by_status(ScheduleStatus.ACTIVE)

        due_tasks = [
            task for task in active_tasks
            if task.next_run_at and task.next_run_at <= now
        ]

        # Sort by next_run_at (oldest first)
        due_tasks.sort(key=lambda t: t.next_run_at or datetime.min)

        return due_tasks

    async def get_executions(
        self,
        task_id: str,
        limit: int = 50,
    ) -> List[TaskExecution]:
        """
        Get execution history for a task.

        Args:
            task_id: Task ID.
            limit: Maximum results.

        Returns:
            List of executions.
        """
        return self.store.get_executions(task_id, limit)

    def get_stats(self) -> SchedulerStats:
        """Get scheduler statistics."""
        active = self.store.count_by_status(ScheduleStatus.ACTIVE)
        paused = self.store.count_by_status(ScheduleStatus.PAUSED)

        # Get upcoming tasks
        now = datetime.utcnow()
        active_tasks = self.store.get_by_status(ScheduleStatus.ACTIVE)
        upcoming = [
            t for t in active_tasks
            if t.next_run_at and t.next_run_at > now
        ][:5]

        return SchedulerStats(
            total_tasks=self.store.count(),
            active_tasks=active,
            paused_tasks=paused,
            total_executions=self._total_executions,
            successful_executions=self._successful_executions,
            failed_executions=self._failed_executions,
        )

    def _validate_schedule(self, task: ScheduledTask) -> None:
        """Validate task schedule configuration."""
        if task.schedule_type == ScheduleType.CRON:
            config = task.schedule_config
            if isinstance(config, CronSchedule):
                try:
                    CronExpression(config.expression)
                except CronParseError as e:
                    raise InvalidScheduleError(f"Invalid cron expression: {e}")
            elif isinstance(config, dict) and 'expression' in config:
                try:
                    CronExpression(config['expression'])
                except CronParseError as e:
                    raise InvalidScheduleError(f"Invalid cron expression: {e}")
            else:
                raise InvalidScheduleError(
                    "CRON schedule requires CronSchedule config with expression"
                )

        elif task.schedule_type == ScheduleType.INTERVAL:
            config = task.schedule_config
            if isinstance(config, IntervalSchedule):
                if config.total_seconds < 1:
                    raise InvalidScheduleError("Interval must be at least 1 second")
            elif isinstance(config, dict):
                total = config.get('seconds', 0)
                if total < 1:
                    raise InvalidScheduleError("Interval must be at least 1 second")
            else:
                raise InvalidScheduleError(
                    "INTERVAL schedule requires IntervalSchedule config"
                )

    def _calculate_next_run(
        self,
        task: ScheduledTask,
        after: Optional[datetime] = None,
    ) -> Optional[datetime]:
        """
        Calculate the next run time for a task.

        Args:
            task: Task to calculate for.
            after: Calculate next run after this time.

        Returns:
            Next run datetime or None if no more runs.
        """
        now = after or datetime.utcnow()
        config = task.schedule_config

        # Check end_date
        if task.end_date and now >= task.end_date:
            return None

        # Use start_date if in future
        base_time = max(now, task.start_date) if task.start_date else now

        if task.schedule_type == ScheduleType.ONCE:
            # One-time task - use run_at if set, otherwise now
            if task.total_runs > 0:
                return None
            return task.run_at or now

        elif task.schedule_type == ScheduleType.INTERVAL:
            if isinstance(config, IntervalSchedule):
                seconds = config.total_seconds
            elif isinstance(config, dict):
                seconds = config.get('seconds', 60)
            else:
                seconds = 60

            return base_time + timedelta(seconds=seconds)

        elif task.schedule_type == ScheduleType.CRON:
            if isinstance(config, CronSchedule):
                expression = config.expression
            elif isinstance(config, dict):
                expression = config.get('expression', '* * * * *')
            else:
                expression = '* * * * *'

            try:
                cron = CronExpression(expression)
                next_time = cron.get_next(base_time)

                # Check against end_date
                if task.end_date and next_time > task.end_date:
                    return None

                return next_time
            except CronParseError:
                return None

        elif task.schedule_type == ScheduleType.DAILY:
            if isinstance(config, DailySchedule):
                hour = config.hour
                minute = config.minute
            elif isinstance(config, dict):
                hour = config.get('hour', 0)
                minute = config.get('minute', 0)
            else:
                hour, minute = 0, 0

            # Calculate next occurrence
            next_run = base_time.replace(
                hour=hour,
                minute=minute,
                second=0,
                microsecond=0,
            )

            if next_run <= now:
                next_run += timedelta(days=1)

            return next_run

        elif task.schedule_type == ScheduleType.WEEKLY:
            if isinstance(config, WeeklySchedule):
                # WeeklySchedule has days_of_week list, take first
                weekday = config.days_of_week[0] if config.days_of_week else 0
                hour = config.hour
                minute = config.minute
            elif isinstance(config, dict):
                weekday = config.get('weekday', 0)
                hour = config.get('hour', 0)
                minute = config.get('minute', 0)
            else:
                weekday, hour, minute = 0, 0, 0

            # Calculate next occurrence
            days_ahead = weekday - base_time.weekday()
            if days_ahead < 0:
                days_ahead += 7

            next_run = base_time.replace(
                hour=hour,
                minute=minute,
                second=0,
                microsecond=0,
            ) + timedelta(days=days_ahead)

            if next_run <= now:
                next_run += timedelta(weeks=1)

            return next_run

        elif task.schedule_type == ScheduleType.MONTHLY:
            if isinstance(config, MonthlySchedule):
                # MonthlySchedule has days_of_month list, take first
                day = config.days_of_month[0] if config.days_of_month else 1
                hour = config.hour
                minute = config.minute
            elif isinstance(config, dict):
                day = config.get('day', 1)
                hour = config.get('hour', 0)
                minute = config.get('minute', 0)
            else:
                day, hour, minute = 1, 0, 0

            # Calculate next occurrence
            year = base_time.year
            month = base_time.month

            # Handle day overflow
            actual_day = min(day, self._days_in_month(year, month))

            next_run = base_time.replace(
                day=actual_day,
                hour=hour,
                minute=minute,
                second=0,
                microsecond=0,
            )

            if next_run <= now:
                # Move to next month
                if month == 12:
                    year += 1
                    month = 1
                else:
                    month += 1

                actual_day = min(day, self._days_in_month(year, month))
                next_run = next_run.replace(year=year, month=month, day=actual_day)

            return next_run

        return None

    def _days_in_month(self, year: int, month: int) -> int:
        """Get number of days in a month."""
        if month == 12:
            next_month = datetime(year + 1, 1, 1)
        else:
            next_month = datetime(year, month + 1, 1)
        return (next_month - timedelta(days=1)).day

    async def _scheduler_loop(self) -> None:
        """Main scheduler loop."""
        logger.info("scheduler_loop_started")

        while self._running:
            try:
                # Get due tasks
                due_tasks = await self.get_due_tasks()

                # Execute tasks
                for task in due_tasks:
                    if not self._running:
                        break

                    try:
                        await self._execute_task(task)
                    except Exception as e:
                        logger.error(
                            "task_execution_error",
                            task_id=task.task_id,
                            error=str(e),
                        )

                # Wait for next poll
                await asyncio.sleep(self.config.poll_interval_seconds)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("scheduler_loop_error", error=str(e))
                await asyncio.sleep(self.config.poll_interval_seconds)

        logger.info("scheduler_loop_stopped")

    async def _execute_task(
        self,
        task: ScheduledTask,
        manual: bool = False,
    ) -> TaskExecution:
        """
        Execute a scheduled task.

        Args:
            task: Task to execute.
            manual: Whether this is a manual trigger.

        Returns:
            Execution result.
        """
        execution = TaskExecution(
            task_id=task.task_id,
            scheduled_time=task.next_run_at or datetime.utcnow(),
        )
        execution.start()

        logger.info(
            "task_execution_started",
            task_id=task.task_id,
            execution_id=execution.execution_id,
            manual=manual,
        )

        self._total_executions += 1

        try:
            # Get handler for task type
            handler = self._handlers.get(task.payload.task_type)

            if handler:
                result = await asyncio.wait_for(
                    handler(task),
                    timeout=task.timeout_seconds,
                )
                execution.complete(result)
            else:
                # Default execution based on task type
                result = await self._default_execute(task)
                execution.complete(result)

            self._successful_executions += 1

            logger.info(
                "task_execution_completed",
                task_id=task.task_id,
                execution_id=execution.execution_id,
                duration_ms=execution.duration_ms,
            )

        except asyncio.TimeoutError:
            execution.timeout()
            self._failed_executions += 1

            logger.warning(
                "task_execution_timeout",
                task_id=task.task_id,
                execution_id=execution.execution_id,
            )

        except Exception as e:
            execution.fail(str(e))
            self._failed_executions += 1

            logger.error(
                "task_execution_failed",
                task_id=task.task_id,
                execution_id=execution.execution_id,
                error=str(e),
            )

        # Use model's add_execution which updates stats
        task.add_execution(execution)

        # Calculate next run
        task.next_run_at = self._calculate_next_run(task, after=datetime.utcnow())

        # Complete task if no more runs
        if task.next_run_at is None:
            task.status = ScheduleStatus.COMPLETED
            logger.info("task_completed", task_id=task.task_id)

        # Store execution and update task
        async with self._lock:
            self.store.add_execution(task.task_id, execution)
            self.store.update(task)

        return execution

    async def _default_execute(self, task: ScheduledTask) -> Any:
        """
        Default task execution.

        Args:
            task: Task to execute.

        Returns:
            Execution result.
        """
        payload = task.payload

        if payload.task_type == TaskType.FUNCTION:
            # Function tasks require a registered handler
            raise TaskExecutionError(
                f"No handler registered for FUNCTION task: {task.task_id}"
            )

        elif payload.task_type == TaskType.HTTP:
            # HTTP webhook call
            return await self._execute_http(payload)

        elif payload.task_type == TaskType.GOAL:
            # Goal execution - placeholder
            return {
                "status": "submitted",
                "goal": payload.target,
                "data": payload.data,
            }

        elif payload.task_type == TaskType.COMMAND:
            # Command execution - placeholder for safety
            return {
                "status": "skipped",
                "reason": "Command execution disabled by default",
                "command": payload.target,
            }

        elif payload.task_type == TaskType.NOTIFICATION:
            # Notification - placeholder
            return {
                "status": "submitted",
                "target": payload.target,
                "data": payload.data,
            }

        else:
            raise TaskExecutionError(f"Unknown task type: {payload.task_type}")

    async def _execute_http(self, payload: Any) -> Dict[str, Any]:
        """Execute HTTP task."""
        import aiohttp

        url = payload.target if hasattr(payload, 'target') else payload.get('target')
        data = payload.data if hasattr(payload, 'data') else payload.get('data', {})
        method = data.get('method', 'POST') if isinstance(data, dict) else 'POST'
        headers = data.get('headers', {}) if isinstance(data, dict) else {}
        body = data.get('body') if isinstance(data, dict) else None

        async with aiohttp.ClientSession() as session:
            async with session.request(
                method=method,
                url=url,
                headers=headers,
                json=body,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as response:
                return {
                    "status_code": response.status,
                    "headers": dict(response.headers),
                    "body": await response.text(),
                }
