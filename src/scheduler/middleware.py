"""
Scheduler API Routes.

FastAPI routes for scheduled task management.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from .models import (
    ScheduledTask,
    TaskExecution,
    ScheduleType,
    ScheduleStatus,
    TaskType,
    IntervalSchedule,
    DailySchedule,
    WeeklySchedule,
    MonthlySchedule,
    CronSchedule,
    TaskPayload,
    SchedulerStats,
)
from .service import (
    SchedulerService,
    TaskNotFoundError,
    InvalidScheduleError,
)


router = APIRouter(prefix="/scheduler", tags=["scheduler"])

# Global scheduler service instance
_scheduler: Optional[SchedulerService] = None


def get_scheduler() -> SchedulerService:
    """Get the scheduler service instance."""
    global _scheduler
    if _scheduler is None:
        _scheduler = SchedulerService()
    return _scheduler


def set_scheduler(scheduler: SchedulerService) -> None:
    """Set the scheduler service instance."""
    global _scheduler
    _scheduler = scheduler


# Request/Response Models

class IntervalScheduleRequest(BaseModel):
    """Interval schedule configuration."""
    seconds: int = Field(ge=1, description="Interval in seconds")


class DailyScheduleRequest(BaseModel):
    """Daily schedule configuration."""
    hour: int = Field(ge=0, le=23, description="Hour (0-23)")
    minute: int = Field(ge=0, le=59, default=0, description="Minute (0-59)")


class WeeklyScheduleRequest(BaseModel):
    """Weekly schedule configuration."""
    weekday: int = Field(ge=0, le=6, description="Day of week (0=Monday, 6=Sunday)")
    hour: int = Field(ge=0, le=23, default=0, description="Hour (0-23)")
    minute: int = Field(ge=0, le=59, default=0, description="Minute (0-59)")


class MonthlyScheduleRequest(BaseModel):
    """Monthly schedule configuration."""
    day: int = Field(ge=1, le=31, description="Day of month (1-31)")
    hour: int = Field(ge=0, le=23, default=0, description="Hour (0-23)")
    minute: int = Field(ge=0, le=59, default=0, description="Minute (0-59)")


class CronScheduleRequest(BaseModel):
    """Cron schedule configuration."""
    expression: str = Field(description="Cron expression (minute hour day month weekday)")


class TaskPayloadRequest(BaseModel):
    """Task payload configuration."""
    task_type: TaskType = Field(default=TaskType.FUNCTION, description="Type of task")
    target: Optional[str] = Field(default=None, description="Target (URL, function name, etc)")
    data: Dict[str, Any] = Field(default_factory=dict, description="Task data/parameters")


class CreateTaskRequest(BaseModel):
    """Request to create a scheduled task."""
    name: str = Field(min_length=1, max_length=200, description="Task name")
    description: str = Field(default="", description="Task description")
    schedule_type: ScheduleType = Field(description="Type of schedule")
    schedule_config: Union[
        IntervalScheduleRequest,
        DailyScheduleRequest,
        WeeklyScheduleRequest,
        MonthlyScheduleRequest,
        CronScheduleRequest,
        Dict[str, Any],
    ] = Field(description="Schedule configuration")
    payload: TaskPayloadRequest = Field(
        default_factory=TaskPayloadRequest,
        description="Task payload"
    )
    tags: List[str] = Field(default_factory=list, description="Task tags")
    start_date: Optional[datetime] = Field(default=None, description="Start date")
    end_date: Optional[datetime] = Field(default=None, description="End date")
    max_retries: int = Field(default=3, ge=0, description="Maximum retries on failure")
    timeout_seconds: int = Field(default=300, ge=1, description="Execution timeout")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Custom metadata")

    model_config = {"extra": "forbid"}


class UpdateTaskRequest(BaseModel):
    """Request to update a scheduled task."""
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = None
    schedule_type: Optional[ScheduleType] = None
    schedule_config: Optional[Union[
        IntervalScheduleRequest,
        DailyScheduleRequest,
        WeeklyScheduleRequest,
        MonthlyScheduleRequest,
        CronScheduleRequest,
        Dict[str, Any],
    ]] = None
    payload: Optional[TaskPayloadRequest] = None
    tags: Optional[List[str]] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    max_retries: Optional[int] = Field(default=None, ge=0)
    timeout_seconds: Optional[int] = Field(default=None, ge=1)
    metadata: Optional[Dict[str, Any]] = None

    model_config = {"extra": "forbid"}


class TaskResponse(BaseModel):
    """Task response model."""
    task_id: str
    name: str
    description: Optional[str]
    schedule_type: ScheduleType
    schedule_config: Dict[str, Any]
    payload: Dict[str, Any]
    status: ScheduleStatus
    tags: List[str]
    created_at: datetime
    updated_at: datetime
    start_date: Optional[datetime]
    end_date: Optional[datetime]
    next_run_at: Optional[datetime]
    last_run_at: Optional[datetime]
    total_runs: int
    successful_runs: int
    failed_runs: int
    timeout_seconds: int
    max_retries: int
    metadata: Dict[str, Any]

    model_config = {"from_attributes": True}


class ExecutionResponse(BaseModel):
    """Execution response model."""
    execution_id: str
    task_id: str
    scheduled_time: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    status: str
    result: Optional[Any]
    error: Optional[str]
    retry_count: int
    duration_ms: Optional[int]

    model_config = {"from_attributes": True}


class TaskListResponse(BaseModel):
    """Task list response."""
    tasks: List[TaskResponse]
    total: int
    limit: int
    offset: int


class StatsResponse(BaseModel):
    """Scheduler statistics response."""
    total_tasks: int
    active_tasks: int
    paused_tasks: int
    total_executions: int
    successful_executions: int
    failed_executions: int
    success_rate: float


# Helper functions

def task_to_response(task: ScheduledTask) -> TaskResponse:
    """Convert ScheduledTask to TaskResponse."""
    # Convert schedule_config to dict
    config = task.schedule_config
    if hasattr(config, 'to_dict'):
        config_dict = config.to_dict()
    elif hasattr(config, '__dict__'):
        config_dict = {
            k: v for k, v in config.__dict__.items()
            if not k.startswith('_')
        }
    elif isinstance(config, dict):
        config_dict = config
    else:
        config_dict = {}

    # Convert payload to dict
    payload = task.payload
    if hasattr(payload, 'to_dict'):
        payload_dict = payload.to_dict()
    elif hasattr(payload, '__dict__'):
        payload_dict = {
            k: (v.value if hasattr(v, 'value') else v)
            for k, v in payload.__dict__.items()
            if not k.startswith('_')
        }
    elif isinstance(payload, dict):
        payload_dict = payload
    else:
        payload_dict = {}

    return TaskResponse(
        task_id=task.task_id,
        name=task.name,
        description=task.description,
        schedule_type=task.schedule_type,
        schedule_config=config_dict,
        payload=payload_dict,
        status=task.status,
        tags=task.tags,
        created_at=task.created_at,
        updated_at=task.updated_at,
        start_date=task.start_date,
        end_date=task.end_date,
        next_run_at=task.next_run_at,
        last_run_at=task.last_run_at,
        total_runs=task.total_runs,
        successful_runs=task.successful_runs,
        failed_runs=task.failed_runs,
        timeout_seconds=task.timeout_seconds,
        max_retries=task.max_retries,
        metadata=task.metadata,
    )


def execution_to_response(execution: TaskExecution) -> ExecutionResponse:
    """Convert TaskExecution to ExecutionResponse."""
    return ExecutionResponse(
        execution_id=execution.execution_id,
        task_id=execution.task_id,
        scheduled_time=execution.scheduled_time,
        started_at=execution.started_at,
        completed_at=execution.completed_at,
        status=execution.status.value,
        result=execution.result,
        error=execution.error,
        retry_count=execution.retry_count,
        duration_ms=execution.duration_ms,
    )


def request_to_schedule_config(
    schedule_type: ScheduleType,
    config: Union[
        IntervalScheduleRequest,
        DailyScheduleRequest,
        WeeklyScheduleRequest,
        MonthlyScheduleRequest,
        CronScheduleRequest,
        Dict[str, Any],
    ],
) -> Union[IntervalSchedule, DailySchedule, WeeklySchedule, MonthlySchedule, CronSchedule]:
    """Convert request config to schedule config dataclass."""
    if isinstance(config, dict):
        config_dict = config
    else:
        config_dict = config.model_dump()

    if schedule_type == ScheduleType.INTERVAL:
        return IntervalSchedule(**config_dict)
    elif schedule_type == ScheduleType.DAILY:
        return DailySchedule(**config_dict)
    elif schedule_type == ScheduleType.WEEKLY:
        # Map weekday to days_of_week list
        weekday = config_dict.pop('weekday', 0)
        config_dict['days_of_week'] = [weekday]
        return WeeklySchedule(**config_dict)
    elif schedule_type == ScheduleType.MONTHLY:
        # Map day to days_of_month list
        day = config_dict.pop('day', 1)
        config_dict['days_of_month'] = [day]
        return MonthlySchedule(**config_dict)
    elif schedule_type == ScheduleType.CRON:
        return CronSchedule(**config_dict)
    else:
        return config_dict


# Routes

@router.get("/stats", response_model=StatsResponse)
async def get_stats() -> StatsResponse:
    """Get scheduler statistics."""
    scheduler = get_scheduler()
    stats = scheduler.get_stats()

    success_rate = 0.0
    if stats.total_executions > 0:
        success_rate = stats.successful_executions / stats.total_executions

    return StatsResponse(
        total_tasks=stats.total_tasks,
        active_tasks=stats.active_tasks,
        paused_tasks=stats.paused_tasks,
        total_executions=stats.total_executions,
        successful_executions=stats.successful_executions,
        failed_executions=stats.failed_executions,
        success_rate=success_rate,
    )


@router.post("/tasks", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(request: CreateTaskRequest) -> TaskResponse:
    """Create a new scheduled task."""
    scheduler = get_scheduler()

    # Convert request to ScheduledTask
    schedule_config = request_to_schedule_config(
        request.schedule_type,
        request.schedule_config,
    )

    # Build TaskPayload based on task type
    payload_data = request.payload
    if payload_data.task_type == TaskType.HTTP:
        payload = TaskPayload(
            task_type=TaskType.HTTP,
            http_url=payload_data.target,
            http_body=payload_data.data.get("body") if payload_data.data else None,
            http_method=payload_data.data.get("method", "POST") if payload_data.data else "POST",
            http_headers=payload_data.data.get("headers", {}) if payload_data.data else {},
        )
    elif payload_data.task_type == TaskType.FUNCTION:
        payload = TaskPayload(
            task_type=TaskType.FUNCTION,
            function_name=payload_data.target,
            function_kwargs=payload_data.data if payload_data.data else {},
        )
    elif payload_data.task_type == TaskType.GOAL:
        payload = TaskPayload(
            task_type=TaskType.GOAL,
            goal_description=payload_data.target,
            goal_config=payload_data.data if payload_data.data else {},
        )
    elif payload_data.task_type == TaskType.COMMAND:
        payload = TaskPayload(
            task_type=TaskType.COMMAND,
            command=payload_data.target,
            command_args=payload_data.data.get("args", []) if payload_data.data else [],
        )
    elif payload_data.task_type == TaskType.NOTIFICATION:
        payload = TaskPayload(
            task_type=TaskType.NOTIFICATION,
            notification_recipient=payload_data.target,
            notification_content=payload_data.data if payload_data.data else {},
        )
    else:
        payload = TaskPayload(task_type=payload_data.task_type)

    task = ScheduledTask(
        name=request.name,
        description=request.description,
        schedule_type=request.schedule_type,
        schedule_config=schedule_config,
        payload=payload,
        tags=request.tags,
        start_date=request.start_date,
        end_date=request.end_date,
        max_retries=request.max_retries,
        timeout_seconds=request.timeout_seconds,
        metadata=request.metadata,
    )

    try:
        created_task = await scheduler.create_task(task)
        return task_to_response(created_task)
    except InvalidScheduleError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/tasks", response_model=TaskListResponse)
async def list_tasks(
    status_filter: Optional[ScheduleStatus] = Query(None, alias="status"),
    schedule_type: Optional[ScheduleType] = None,
    tag: Optional[str] = None,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
) -> TaskListResponse:
    """List scheduled tasks with optional filters."""
    scheduler = get_scheduler()

    tasks = await scheduler.list_tasks(
        status=status_filter,
        schedule_type=schedule_type,
        tag=tag,
        limit=limit,
        offset=offset,
    )

    # Get total count (without pagination)
    all_tasks = await scheduler.list_tasks(
        status=status_filter,
        schedule_type=schedule_type,
        tag=tag,
        limit=10000,
        offset=0,
    )

    return TaskListResponse(
        tasks=[task_to_response(t) for t in tasks],
        total=len(all_tasks),
        limit=limit,
        offset=offset,
    )


@router.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str) -> TaskResponse:
    """Get a scheduled task by ID."""
    scheduler = get_scheduler()
    task = await scheduler.get_task(task_id)

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task not found: {task_id}",
        )

    return task_to_response(task)


@router.patch("/tasks/{task_id}", response_model=TaskResponse)
async def update_task(task_id: str, request: UpdateTaskRequest) -> TaskResponse:
    """Update a scheduled task."""
    scheduler = get_scheduler()

    # Get existing task
    existing = await scheduler.get_task(task_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task not found: {task_id}",
        )

    # Build updates dict
    updates: Dict[str, Any] = {}

    if request.name is not None:
        updates["name"] = request.name
    if request.description is not None:
        updates["description"] = request.description
    if request.tags is not None:
        updates["tags"] = request.tags
    if request.start_date is not None:
        updates["start_date"] = request.start_date
    if request.end_date is not None:
        updates["end_date"] = request.end_date
    if request.max_retries is not None:
        updates["max_retries"] = request.max_retries
    if request.timeout_seconds is not None:
        updates["timeout_seconds"] = request.timeout_seconds
    if request.metadata is not None:
        updates["metadata"] = request.metadata

    # Handle schedule changes
    if request.schedule_type is not None:
        updates["schedule_type"] = request.schedule_type
    if request.schedule_config is not None:
        stype = request.schedule_type or existing.schedule_type
        updates["schedule_config"] = request_to_schedule_config(
            stype,
            request.schedule_config,
        )

    # Handle payload changes
    if request.payload is not None:
        updates["payload"] = TaskPayload(
            task_type=request.payload.task_type,
            target=request.payload.target,
            data=request.payload.data,
        )

    try:
        updated_task = await scheduler.update_task(task_id, **updates)
        return task_to_response(updated_task)
    except TaskNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task not found: {task_id}",
        )
    except InvalidScheduleError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(task_id: str) -> None:
    """Delete a scheduled task."""
    scheduler = get_scheduler()
    deleted = await scheduler.delete_task(task_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task not found: {task_id}",
        )


@router.post("/tasks/{task_id}/pause", response_model=TaskResponse)
async def pause_task(task_id: str) -> TaskResponse:
    """Pause a scheduled task."""
    scheduler = get_scheduler()

    try:
        task = await scheduler.pause_task(task_id)
        return task_to_response(task)
    except TaskNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task not found: {task_id}",
        )


@router.post("/tasks/{task_id}/resume", response_model=TaskResponse)
async def resume_task(task_id: str) -> TaskResponse:
    """Resume a paused task."""
    scheduler = get_scheduler()

    try:
        task = await scheduler.resume_task(task_id)
        return task_to_response(task)
    except TaskNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task not found: {task_id}",
        )


@router.post("/tasks/{task_id}/trigger", response_model=ExecutionResponse)
async def trigger_task(task_id: str) -> ExecutionResponse:
    """Manually trigger a task execution."""
    scheduler = get_scheduler()

    try:
        execution = await scheduler.trigger_task(task_id)
        return execution_to_response(execution)
    except TaskNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task not found: {task_id}",
        )


@router.get("/tasks/{task_id}/executions", response_model=List[ExecutionResponse])
async def get_task_executions(
    task_id: str,
    limit: int = Query(50, ge=1, le=500),
) -> List[ExecutionResponse]:
    """Get execution history for a task."""
    scheduler = get_scheduler()

    # Verify task exists
    task = await scheduler.get_task(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task not found: {task_id}",
        )

    executions = await scheduler.get_executions(task_id, limit)
    return [execution_to_response(e) for e in executions]


@router.get("/due", response_model=List[TaskResponse])
async def get_due_tasks() -> List[TaskResponse]:
    """Get all tasks that are currently due for execution."""
    scheduler = get_scheduler()
    tasks = await scheduler.get_due_tasks()
    return [task_to_response(t) for t in tasks]


@router.post("/start", status_code=status.HTTP_200_OK)
async def start_scheduler() -> Dict[str, str]:
    """Start the scheduler loop."""
    scheduler = get_scheduler()
    await scheduler.start()
    return {"status": "started"}


@router.post("/stop", status_code=status.HTTP_200_OK)
async def stop_scheduler() -> Dict[str, str]:
    """Stop the scheduler loop."""
    scheduler = get_scheduler()
    await scheduler.stop()
    return {"status": "stopped"}
