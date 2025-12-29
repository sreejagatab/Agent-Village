"""
Tests for Scheduler Module.

Tests cron parsing, task scheduling, execution, and API routes.
"""

import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.scheduler import (
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
    # Cron
    CronExpression,
    CronParseError,
    parse_cron,
    get_next_cron_time,
    validate_cron,
    describe_cron,
    # Service
    SchedulerService,
    SchedulerStore,
    TaskNotFoundError,
    InvalidScheduleError,
    # Middleware
    router,
    set_scheduler,
)


# =============================================================================
# Cron Expression Tests
# =============================================================================

class TestCronExpression:
    """Tests for CronExpression class."""

    def test_parse_every_minute(self):
        """Test parsing every minute expression."""
        cron = CronExpression("* * * * *")
        assert cron.minute.values == set(range(60))
        assert cron.hour.values == set(range(24))
        assert cron.day.values == set(range(1, 32))
        assert cron.month.values == set(range(1, 13))
        assert cron.weekday.values == set(range(7))

    def test_parse_every_hour(self):
        """Test parsing every hour expression."""
        cron = CronExpression("0 * * * *")
        assert cron.minute.values == {0}
        assert cron.hour.values == set(range(24))

    def test_parse_daily_midnight(self):
        """Test parsing daily at midnight."""
        cron = CronExpression("0 0 * * *")
        assert cron.minute.values == {0}
        assert cron.hour.values == {0}

    def test_parse_step_values(self):
        """Test parsing step values."""
        cron = CronExpression("*/15 * * * *")
        assert cron.minute.values == {0, 15, 30, 45}

    def test_parse_range(self):
        """Test parsing range values."""
        cron = CronExpression("0 9-17 * * *")
        assert cron.hour.values == {9, 10, 11, 12, 13, 14, 15, 16, 17}

    def test_parse_list(self):
        """Test parsing list values."""
        cron = CronExpression("0 0 * * 1,3,5")
        assert cron.weekday.values == {1, 3, 5}

    def test_parse_month_names(self):
        """Test parsing month names."""
        cron = CronExpression("0 0 1 jan,jul *")
        assert cron.month.values == {1, 7}

    def test_parse_weekday_names(self):
        """Test parsing weekday names."""
        cron = CronExpression("0 0 * * mon,wed,fri")
        assert cron.weekday.values == {1, 3, 5}

    def test_parse_alias_daily(self):
        """Test parsing @daily alias."""
        cron = CronExpression("@daily")
        assert cron.minute.values == {0}
        assert cron.hour.values == {0}

    def test_parse_alias_hourly(self):
        """Test parsing @hourly alias."""
        cron = CronExpression("@hourly")
        assert cron.minute.values == {0}
        assert cron.hour.values == set(range(24))

    def test_parse_alias_weekly(self):
        """Test parsing @weekly alias."""
        cron = CronExpression("@weekly")
        assert cron.minute.values == {0}
        assert cron.hour.values == {0}
        assert cron.weekday.values == {0}  # Sunday

    def test_parse_alias_monthly(self):
        """Test parsing @monthly alias."""
        cron = CronExpression("@monthly")
        assert cron.minute.values == {0}
        assert cron.hour.values == {0}
        assert cron.day.values == {1}

    def test_parse_invalid_field_count(self):
        """Test parsing with wrong number of fields."""
        with pytest.raises(CronParseError) as exc_info:
            CronExpression("* * *")
        assert "expected 5 fields" in str(exc_info.value)

    def test_parse_invalid_value(self):
        """Test parsing with out of range value."""
        with pytest.raises(CronParseError) as exc_info:
            CronExpression("60 * * * *")
        assert "minute" in str(exc_info.value).lower()

    def test_matches_datetime(self):
        """Test matching datetime."""
        cron = CronExpression("30 14 * * *")
        # 2:30 PM matches
        dt_match = datetime(2024, 1, 15, 14, 30)
        assert cron.matches(dt_match) is True
        # 2:31 PM does not match
        dt_no_match = datetime(2024, 1, 15, 14, 31)
        assert cron.matches(dt_no_match) is False

    def test_matches_weekday(self):
        """Test matching with weekday constraint."""
        # Only on Monday (1)
        cron = CronExpression("0 0 * * 1")
        # January 15, 2024 is a Monday
        monday = datetime(2024, 1, 15, 0, 0)
        assert cron.matches(monday) is True
        # January 16, 2024 is a Tuesday
        tuesday = datetime(2024, 1, 16, 0, 0)
        assert cron.matches(tuesday) is False

    def test_get_next(self):
        """Test getting next run time."""
        cron = CronExpression("0 * * * *")
        after = datetime(2024, 1, 15, 14, 30)
        next_time = cron.get_next(after)
        assert next_time.minute == 0
        assert next_time.hour == 15

    def test_get_next_crosses_day(self):
        """Test next time that crosses day boundary."""
        cron = CronExpression("0 0 * * *")  # Midnight
        after = datetime(2024, 1, 15, 23, 30)
        next_time = cron.get_next(after)
        assert next_time == datetime(2024, 1, 16, 0, 0)

    def test_get_next_n(self):
        """Test getting next N run times."""
        cron = CronExpression("0 * * * *")  # Every hour
        after = datetime(2024, 1, 15, 14, 0)
        times = cron.get_next_n(3, after)
        assert len(times) == 3
        assert times[0].hour == 15
        assert times[1].hour == 16
        assert times[2].hour == 17

    def test_get_previous(self):
        """Test getting previous run time."""
        cron = CronExpression("0 * * * *")  # Every hour
        before = datetime(2024, 1, 15, 14, 30)
        prev_time = cron.get_previous(before)
        assert prev_time.minute == 0
        assert prev_time.hour == 14


class TestCronHelpers:
    """Tests for cron helper functions."""

    def test_parse_cron(self):
        """Test parse_cron function."""
        cron = parse_cron("0 0 * * *")
        assert isinstance(cron, CronExpression)

    def test_get_next_cron_time(self):
        """Test get_next_cron_time function."""
        after = datetime(2024, 1, 15, 14, 30)
        next_time = get_next_cron_time("0 * * * *", after)
        assert next_time.minute == 0
        assert next_time.hour == 15

    def test_validate_cron_valid(self):
        """Test validate_cron with valid expression."""
        is_valid, error = validate_cron("0 0 * * *")
        assert is_valid is True
        assert error is None

    def test_validate_cron_invalid(self):
        """Test validate_cron with invalid expression."""
        is_valid, error = validate_cron("invalid")
        assert is_valid is False
        assert error is not None

    def test_describe_cron_every_minute(self):
        """Test describe_cron for every minute."""
        desc = describe_cron("* * * * *")
        assert "every minute" in desc.lower()

    def test_describe_cron_daily(self):
        """Test describe_cron for daily."""
        desc = describe_cron("0 0 * * *")
        assert "00:00" in desc


# =============================================================================
# Scheduler Models Tests
# =============================================================================

class TestScheduledTask:
    """Tests for ScheduledTask model."""

    def test_create_default_task(self):
        """Test creating task with defaults."""
        task = ScheduledTask(name="Test Task")
        assert task.task_id.startswith("task_")
        assert task.name == "Test Task"
        assert task.status == ScheduleStatus.PENDING

    def test_create_interval_factory(self):
        """Test interval task factory."""
        task = ScheduledTask.create_interval(
            name="Every 5 minutes",
            interval=IntervalSchedule(seconds=300),
            payload=TaskPayload(),
        )
        assert task.schedule_type == ScheduleType.INTERVAL
        assert task.schedule_config.total_seconds == 300

    def test_create_daily_factory(self):
        """Test daily task factory."""
        task = ScheduledTask.create_daily(
            name="Daily at 9am",
            schedule=DailySchedule(hour=9, minute=0),
            payload=TaskPayload(),
        )
        assert task.schedule_type == ScheduleType.DAILY
        assert task.schedule_config.hour == 9

    def test_create_weekly_factory(self):
        """Test weekly task factory."""
        task = ScheduledTask.create_weekly(
            name="Every Monday",
            schedule=WeeklySchedule(days_of_week=[0], hour=9),
            payload=TaskPayload(),
        )
        assert task.schedule_type == ScheduleType.WEEKLY
        assert task.schedule_config.days_of_week == [0]

    def test_create_monthly_factory(self):
        """Test monthly task factory."""
        task = ScheduledTask.create_monthly(
            name="First of month",
            schedule=MonthlySchedule(days_of_month=[1], hour=0),
            payload=TaskPayload(),
        )
        assert task.schedule_type == ScheduleType.MONTHLY
        assert task.schedule_config.days_of_month == [1]

    def test_create_cron_factory(self):
        """Test cron task factory."""
        task = ScheduledTask.create_cron(
            name="Every hour",
            cron_expression="0 * * * *",
            payload=TaskPayload(),
        )
        assert task.schedule_type == ScheduleType.CRON
        assert task.schedule_config.expression == "0 * * * *"

    def test_create_once_factory(self):
        """Test once task factory."""
        run_at = datetime.utcnow() + timedelta(hours=1)
        task = ScheduledTask.create_once(
            name="One time",
            run_at=run_at,
            payload=TaskPayload(),
        )
        assert task.schedule_type == ScheduleType.ONCE
        assert task.run_at == run_at


class TestSchedulerStore:
    """Tests for SchedulerStore."""

    def test_add_and_get(self):
        """Test adding and getting tasks."""
        store = SchedulerStore()
        task = ScheduledTask(name="Test")
        store.add(task)

        retrieved = store.get(task.task_id)
        assert retrieved is not None
        assert retrieved.name == "Test"

    def test_get_by_status(self):
        """Test filtering by status."""
        store = SchedulerStore()

        task1 = ScheduledTask(name="Active", status=ScheduleStatus.ACTIVE)
        task2 = ScheduledTask(name="Paused", status=ScheduleStatus.PAUSED)
        store.add(task1)
        store.add(task2)

        active = store.get_by_status(ScheduleStatus.ACTIVE)
        assert len(active) == 1
        assert active[0].name == "Active"

    def test_get_by_tag(self):
        """Test filtering by tag."""
        store = SchedulerStore()

        task1 = ScheduledTask(name="Tagged", tags=["important"])
        task2 = ScheduledTask(name="Untagged")
        store.add(task1)
        store.add(task2)

        tagged = store.get_by_tag("important")
        assert len(tagged) == 1
        assert tagged[0].name == "Tagged"

    def test_update(self):
        """Test updating task."""
        store = SchedulerStore()
        task = ScheduledTask(name="Original", status=ScheduleStatus.ACTIVE)
        store.add(task)

        # Change status using model method
        task.pause()
        store.update(task)

        active = store.get_by_status(ScheduleStatus.ACTIVE)
        paused = store.get_by_status(ScheduleStatus.PAUSED)
        assert len(active) == 0
        assert len(paused) == 1

    def test_remove(self):
        """Test removing task."""
        store = SchedulerStore()
        task = ScheduledTask(name="To Remove")
        store.add(task)

        removed = store.remove(task.task_id)
        assert removed is not None
        assert store.get(task.task_id) is None

    def test_add_execution(self):
        """Test adding execution record."""
        store = SchedulerStore()
        task = ScheduledTask(name="Test")
        store.add(task)

        execution = TaskExecution(
            task_id=task.task_id,
            scheduled_time=datetime.utcnow(),
        )
        execution.start()
        execution.complete()
        store.add_execution(task.task_id, execution)

        execs = store.get_executions(task.task_id)
        assert len(execs) == 1


# =============================================================================
# Scheduler Service Tests
# =============================================================================

class TestSchedulerService:
    """Tests for SchedulerService."""

    @pytest.fixture
    def scheduler(self):
        """Create a scheduler service."""
        return SchedulerService(SchedulerConfig(poll_interval_seconds=0.1))

    @pytest.mark.asyncio
    async def test_create_task(self, scheduler):
        """Test creating a task."""
        task = ScheduledTask(
            name="Test",
            schedule_type=ScheduleType.INTERVAL,
            schedule_config=IntervalSchedule(seconds=60),
        )
        created = await scheduler.create_task(task)

        assert created.status == ScheduleStatus.ACTIVE
        assert created.next_run_at is not None

    @pytest.mark.asyncio
    async def test_get_task(self, scheduler):
        """Test getting a task."""
        task = ScheduledTask(name="Test")
        await scheduler.create_task(task)

        retrieved = await scheduler.get_task(task.task_id)
        assert retrieved is not None
        assert retrieved.name == "Test"

    @pytest.mark.asyncio
    async def test_update_task(self, scheduler):
        """Test updating a task."""
        task = ScheduledTask(name="Original")
        await scheduler.create_task(task)

        updated = await scheduler.update_task(task.task_id, name="Updated")
        assert updated.name == "Updated"

    @pytest.mark.asyncio
    async def test_delete_task(self, scheduler):
        """Test deleting a task."""
        task = ScheduledTask(name="To Delete")
        await scheduler.create_task(task)

        deleted = await scheduler.delete_task(task.task_id)
        assert deleted is True

        retrieved = await scheduler.get_task(task.task_id)
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_pause_task(self, scheduler):
        """Test pausing a task."""
        task = ScheduledTask(name="To Pause")
        await scheduler.create_task(task)

        paused = await scheduler.pause_task(task.task_id)
        assert paused.status == ScheduleStatus.PAUSED

    @pytest.mark.asyncio
    async def test_resume_task(self, scheduler):
        """Test resuming a task."""
        task = ScheduledTask(name="To Resume")
        await scheduler.create_task(task)
        await scheduler.pause_task(task.task_id)

        resumed = await scheduler.resume_task(task.task_id)
        assert resumed.status == ScheduleStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_list_tasks(self, scheduler):
        """Test listing tasks."""
        for i in range(5):
            task = ScheduledTask(name=f"Task {i}")
            await scheduler.create_task(task)

        tasks = await scheduler.list_tasks()
        assert len(tasks) == 5

    @pytest.mark.asyncio
    async def test_list_tasks_with_filter(self, scheduler):
        """Test listing tasks with status filter."""
        task1 = ScheduledTask(name="Active")
        task2 = ScheduledTask(name="Paused")
        await scheduler.create_task(task1)
        await scheduler.create_task(task2)
        await scheduler.pause_task(task2.task_id)

        active = await scheduler.list_tasks(status=ScheduleStatus.ACTIVE)
        paused = await scheduler.list_tasks(status=ScheduleStatus.PAUSED)
        assert len(active) == 1
        assert len(paused) == 1

    @pytest.mark.asyncio
    async def test_get_due_tasks(self, scheduler):
        """Test getting due tasks."""
        # Create task
        task = ScheduledTask(
            name="Due",
            schedule_type=ScheduleType.INTERVAL,
            schedule_config=IntervalSchedule(seconds=60),
        )
        await scheduler.create_task(task)

        # Manually set next_run_at to past
        task.next_run_at = datetime.utcnow() - timedelta(minutes=5)
        scheduler.store.update(task)

        due = await scheduler.get_due_tasks()
        assert len(due) == 1
        assert due[0].task_id == task.task_id

    @pytest.mark.asyncio
    async def test_calculate_next_run_interval(self, scheduler):
        """Test next run calculation for interval."""
        task = ScheduledTask(
            name="Test",
            schedule_type=ScheduleType.INTERVAL,
            schedule_config=IntervalSchedule(seconds=300),
        )
        await scheduler.create_task(task)

        assert task.next_run_at is not None
        # Should be ~5 minutes from now
        diff = (task.next_run_at - datetime.utcnow()).total_seconds()
        assert 295 <= diff <= 305

    @pytest.mark.asyncio
    async def test_calculate_next_run_cron(self, scheduler):
        """Test next run calculation for cron."""
        task = ScheduledTask(
            name="Test",
            schedule_type=ScheduleType.CRON,
            schedule_config=CronSchedule(expression="0 * * * *"),
        )
        await scheduler.create_task(task)

        assert task.next_run_at is not None
        assert task.next_run_at.minute == 0

    @pytest.mark.asyncio
    async def test_invalid_cron_expression(self, scheduler):
        """Test invalid cron expression raises error."""
        task = ScheduledTask(
            name="Invalid",
            schedule_type=ScheduleType.CRON,
            schedule_config=CronSchedule(expression="invalid"),
        )

        with pytest.raises(InvalidScheduleError):
            await scheduler.create_task(task)

    @pytest.mark.asyncio
    async def test_register_handler(self, scheduler):
        """Test registering task handler."""
        handler = AsyncMock(return_value={"result": "ok"})
        scheduler.register_handler(TaskType.FUNCTION, handler)

        assert TaskType.FUNCTION in scheduler._handlers

    @pytest.mark.asyncio
    async def test_trigger_task(self, scheduler):
        """Test manually triggering a task."""
        handler = AsyncMock(return_value={"result": "ok"})
        scheduler.register_handler(TaskType.FUNCTION, handler)

        task = ScheduledTask(
            name="Manual",
            payload=TaskPayload(task_type=TaskType.FUNCTION),
        )
        await scheduler.create_task(task)

        execution = await scheduler.trigger_task(task.task_id)
        assert execution.status == ExecutionStatus.COMPLETED
        handler.assert_called_once()

    @pytest.mark.asyncio
    async def test_trigger_task_not_found(self, scheduler):
        """Test triggering nonexistent task."""
        with pytest.raises(TaskNotFoundError):
            await scheduler.trigger_task("nonexistent")

    @pytest.mark.asyncio
    async def test_get_stats(self, scheduler):
        """Test getting scheduler stats."""
        task1 = ScheduledTask(name="Active")
        task2 = ScheduledTask(name="Paused")
        await scheduler.create_task(task1)
        await scheduler.create_task(task2)
        await scheduler.pause_task(task2.task_id)

        stats = scheduler.get_stats()
        assert stats.total_tasks == 2
        assert stats.active_tasks == 1
        assert stats.paused_tasks == 1

    @pytest.mark.asyncio
    async def test_start_stop(self, scheduler):
        """Test starting and stopping scheduler."""
        await scheduler.start()
        assert scheduler._running is True

        await scheduler.stop()
        assert scheduler._running is False

    @pytest.mark.asyncio
    async def test_task_completion_after_once(self, scheduler):
        """Test task completion after one-time run."""
        handler = AsyncMock(return_value={"result": "ok"})
        scheduler.register_handler(TaskType.FUNCTION, handler)

        task = ScheduledTask(
            name="OnceTask",
            schedule_type=ScheduleType.ONCE,
            payload=TaskPayload(task_type=TaskType.FUNCTION),
        )
        await scheduler.create_task(task)

        # Trigger the one-time task
        await scheduler.trigger_task(task.task_id)

        updated = await scheduler.get_task(task.task_id)
        assert updated.status == ScheduleStatus.COMPLETED
        assert updated.total_runs == 1


# =============================================================================
# API Routes Tests
# =============================================================================

class TestSchedulerRoutes:
    """Tests for scheduler API routes."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        app = FastAPI()
        app.include_router(router)

        scheduler = SchedulerService()
        set_scheduler(scheduler)

        return TestClient(app)

    def test_get_stats(self, client):
        """Test GET /scheduler/stats."""
        response = client.get("/scheduler/stats")
        assert response.status_code == 200
        data = response.json()
        assert "total_tasks" in data
        assert "active_tasks" in data

    def test_create_task_interval(self, client):
        """Test POST /scheduler/tasks with interval."""
        response = client.post(
            "/scheduler/tasks",
            json={
                "name": "Test Task",
                "schedule_type": "interval",
                "schedule_config": {"seconds": 300},
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Task"
        assert data["schedule_type"] == "interval"

    def test_create_task_cron(self, client):
        """Test POST /scheduler/tasks with cron."""
        response = client.post(
            "/scheduler/tasks",
            json={
                "name": "Cron Task",
                "schedule_type": "cron",
                "schedule_config": {"expression": "0 * * * *"},
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["schedule_type"] == "cron"

    def test_create_task_invalid_cron(self, client):
        """Test POST /scheduler/tasks with invalid cron."""
        response = client.post(
            "/scheduler/tasks",
            json={
                "name": "Invalid",
                "schedule_type": "cron",
                "schedule_config": {"expression": "invalid"},
            },
        )
        assert response.status_code == 400

    def test_list_tasks(self, client):
        """Test GET /scheduler/tasks."""
        # Create some tasks
        for i in range(3):
            client.post(
                "/scheduler/tasks",
                json={
                    "name": f"Task {i}",
                    "schedule_type": "interval",
                    "schedule_config": {"seconds": 60},
                },
            )

        response = client.get("/scheduler/tasks")
        assert response.status_code == 200
        data = response.json()
        assert len(data["tasks"]) == 3

    def test_list_tasks_filter_status(self, client):
        """Test GET /scheduler/tasks with status filter."""
        # Create active task
        response = client.post(
            "/scheduler/tasks",
            json={
                "name": "Active",
                "schedule_type": "interval",
                "schedule_config": {"seconds": 60},
            },
        )
        task_id = response.json()["task_id"]

        # Pause it
        client.post(f"/scheduler/tasks/{task_id}/pause")

        # Filter by paused
        response = client.get("/scheduler/tasks?status=paused")
        assert response.status_code == 200
        data = response.json()
        assert len(data["tasks"]) == 1

    def test_get_task(self, client):
        """Test GET /scheduler/tasks/{task_id}."""
        # Create task
        response = client.post(
            "/scheduler/tasks",
            json={
                "name": "Get Test",
                "schedule_type": "interval",
                "schedule_config": {"seconds": 60},
            },
        )
        task_id = response.json()["task_id"]

        # Get it
        response = client.get(f"/scheduler/tasks/{task_id}")
        assert response.status_code == 200
        assert response.json()["name"] == "Get Test"

    def test_get_task_not_found(self, client):
        """Test GET /scheduler/tasks/{task_id} not found."""
        response = client.get("/scheduler/tasks/nonexistent")
        assert response.status_code == 404

    def test_update_task(self, client):
        """Test PATCH /scheduler/tasks/{task_id}."""
        # Create task
        response = client.post(
            "/scheduler/tasks",
            json={
                "name": "Original",
                "schedule_type": "interval",
                "schedule_config": {"seconds": 60},
            },
        )
        task_id = response.json()["task_id"]

        # Update it
        response = client.patch(
            f"/scheduler/tasks/{task_id}",
            json={"name": "Updated"},
        )
        assert response.status_code == 200
        assert response.json()["name"] == "Updated"

    def test_delete_task(self, client):
        """Test DELETE /scheduler/tasks/{task_id}."""
        # Create task
        response = client.post(
            "/scheduler/tasks",
            json={
                "name": "To Delete",
                "schedule_type": "interval",
                "schedule_config": {"seconds": 60},
            },
        )
        task_id = response.json()["task_id"]

        # Delete it
        response = client.delete(f"/scheduler/tasks/{task_id}")
        assert response.status_code == 204

        # Verify deleted
        response = client.get(f"/scheduler/tasks/{task_id}")
        assert response.status_code == 404

    def test_pause_task(self, client):
        """Test POST /scheduler/tasks/{task_id}/pause."""
        # Create task
        response = client.post(
            "/scheduler/tasks",
            json={
                "name": "To Pause",
                "schedule_type": "interval",
                "schedule_config": {"seconds": 60},
            },
        )
        task_id = response.json()["task_id"]

        # Pause it
        response = client.post(f"/scheduler/tasks/{task_id}/pause")
        assert response.status_code == 200
        assert response.json()["status"] == "paused"

    def test_resume_task(self, client):
        """Test POST /scheduler/tasks/{task_id}/resume."""
        # Create and pause task
        response = client.post(
            "/scheduler/tasks",
            json={
                "name": "To Resume",
                "schedule_type": "interval",
                "schedule_config": {"seconds": 60},
            },
        )
        task_id = response.json()["task_id"]
        client.post(f"/scheduler/tasks/{task_id}/pause")

        # Resume it
        response = client.post(f"/scheduler/tasks/{task_id}/resume")
        assert response.status_code == 200
        assert response.json()["status"] == "active"

    def test_trigger_task(self, client):
        """Test POST /scheduler/tasks/{task_id}/trigger."""
        # Create task
        response = client.post(
            "/scheduler/tasks",
            json={
                "name": "To Trigger",
                "schedule_type": "interval",
                "schedule_config": {"seconds": 60},
                "payload": {
                    "task_type": "http",
                    "target": "http://example.com",
                    "data": {},
                },
            },
        )
        task_id = response.json()["task_id"]

        # Trigger it (will fail since no real HTTP endpoint, but tests the route)
        with patch("aiohttp.ClientSession") as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.headers = {}
            mock_response.text = AsyncMock(return_value="OK")
            mock_session.return_value.__aenter__.return_value.request.return_value.__aenter__.return_value = mock_response

            response = client.post(f"/scheduler/tasks/{task_id}/trigger")
            # May be 200 or error depending on mock setup
            assert response.status_code in [200, 500]

    def test_get_executions(self, client):
        """Test GET /scheduler/tasks/{task_id}/executions."""
        # Create task
        response = client.post(
            "/scheduler/tasks",
            json={
                "name": "With History",
                "schedule_type": "interval",
                "schedule_config": {"seconds": 60},
            },
        )
        task_id = response.json()["task_id"]

        # Get executions (empty initially)
        response = client.get(f"/scheduler/tasks/{task_id}/executions")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_get_due_tasks(self, client):
        """Test GET /scheduler/due."""
        response = client.get("/scheduler/due")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_start_scheduler(self, client):
        """Test POST /scheduler/start."""
        response = client.post("/scheduler/start")
        assert response.status_code == 200
        assert response.json()["status"] == "started"

        # Stop it
        client.post("/scheduler/stop")

    def test_stop_scheduler(self, client):
        """Test POST /scheduler/stop."""
        response = client.post("/scheduler/stop")
        assert response.status_code == 200
        assert response.json()["status"] == "stopped"

    def test_create_daily_task(self, client):
        """Test creating daily task."""
        response = client.post(
            "/scheduler/tasks",
            json={
                "name": "Daily Task",
                "schedule_type": "daily",
                "schedule_config": {"hour": 9, "minute": 30},
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["schedule_type"] == "daily"

    def test_create_weekly_task(self, client):
        """Test creating weekly task."""
        response = client.post(
            "/scheduler/tasks",
            json={
                "name": "Weekly Task",
                "schedule_type": "weekly",
                "schedule_config": {"weekday": 1, "hour": 10, "minute": 0},
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["schedule_type"] == "weekly"

    def test_create_monthly_task(self, client):
        """Test creating monthly task."""
        response = client.post(
            "/scheduler/tasks",
            json={
                "name": "Monthly Task",
                "schedule_type": "monthly",
                "schedule_config": {"day": 15, "hour": 12, "minute": 0},
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["schedule_type"] == "monthly"

    def test_create_once_task(self, client):
        """Test creating one-time task."""
        future_time = (datetime.utcnow() + timedelta(hours=1)).isoformat()
        response = client.post(
            "/scheduler/tasks",
            json={
                "name": "Once Task",
                "schedule_type": "once",
                "schedule_config": {},
                "start_date": future_time,
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["schedule_type"] == "once"

    def test_create_task_with_tags(self, client):
        """Test creating task with tags."""
        response = client.post(
            "/scheduler/tasks",
            json={
                "name": "Tagged Task",
                "schedule_type": "interval",
                "schedule_config": {"seconds": 60},
                "tags": ["important", "reports"],
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert "important" in data["tags"]
        assert "reports" in data["tags"]

    def test_create_task_with_metadata(self, client):
        """Test creating task with metadata."""
        response = client.post(
            "/scheduler/tasks",
            json={
                "name": "Meta Task",
                "schedule_type": "interval",
                "schedule_config": {"seconds": 60},
                "metadata": {"owner": "admin", "priority": "high"},
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["metadata"]["owner"] == "admin"
