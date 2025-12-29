"""
Scheduler Module.

Provides scheduled task management with support for:
- One-time tasks
- Interval-based schedules
- Cron expressions
- Daily/Weekly/Monthly schedules

Usage:
    from src.scheduler import SchedulerService, ScheduledTask, ScheduleType

    # Create scheduler
    scheduler = SchedulerService()

    # Create a cron task
    task = ScheduledTask.cron(
        name="Daily Report",
        expression="0 9 * * *",  # Every day at 9am
        payload=TaskPayload(
            task_type=TaskType.HTTP,
            target="https://api.example.com/reports",
        ),
    )

    await scheduler.create_task(task)
    await scheduler.start()
"""

from .models import (
    # Enums
    ScheduleType,
    ScheduleStatus,
    ExecutionStatus,
    TaskType,
    # Schedule configs
    IntervalSchedule,
    DailySchedule,
    WeeklySchedule,
    MonthlySchedule,
    CronSchedule,
    # Core models
    TaskPayload,
    TaskExecution,
    ScheduledTask,
    SchedulerConfig,
    SchedulerStats,
    TaskListResponse,
)

from .cron import (
    CronExpression,
    CronField,
    CronParseError,
    parse_cron,
    get_next_cron_time,
    validate_cron,
    describe_cron,
)

from .service import (
    SchedulerService,
    SchedulerStore,
    SchedulerError,
    TaskNotFoundError,
    TaskExecutionError,
    InvalidScheduleError,
    TaskHandler,
)

from .middleware import (
    router,
    get_scheduler,
    set_scheduler,
)


__all__ = [
    # Enums
    "ScheduleType",
    "ScheduleStatus",
    "ExecutionStatus",
    "TaskType",
    # Schedule configs
    "IntervalSchedule",
    "DailySchedule",
    "WeeklySchedule",
    "MonthlySchedule",
    "CronSchedule",
    # Core models
    "TaskPayload",
    "TaskExecution",
    "ScheduledTask",
    "SchedulerConfig",
    "SchedulerStats",
    "TaskListResponse",
    # Cron
    "CronExpression",
    "CronField",
    "CronParseError",
    "parse_cron",
    "get_next_cron_time",
    "validate_cron",
    "describe_cron",
    # Service
    "SchedulerService",
    "SchedulerStore",
    "SchedulerError",
    "TaskNotFoundError",
    "TaskExecutionError",
    "InvalidScheduleError",
    "TaskHandler",
    # Middleware
    "router",
    "get_scheduler",
    "set_scheduler",
]
