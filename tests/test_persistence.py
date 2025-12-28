"""Tests for persistence layer."""

import pytest
import pytest_asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from src.core.message import Goal, GoalStatus, Priority, Task, TaskStatus
from src.persistence.models import GoalModel, TaskModel, AgentStateModel
from src.persistence.repositories import GoalRepository, TaskRepository, AgentStateRepository


class TestGoalModel:
    """Tests for GoalModel."""

    def test_goal_model_creation(self):
        """Test creating a goal model."""
        model = GoalModel(
            id="goal-123",
            description="Test goal",
            context={"key": "value"},
            status=GoalStatus.PENDING.value,
            priority=Priority.HIGH.value,
            success_criteria=["criterion1"],
        )

        assert model.id == "goal-123"
        assert model.description == "Test goal"
        assert model.status == GoalStatus.PENDING.value
        assert model.priority == Priority.HIGH.value

    def test_goal_model_to_dict(self):
        """Test converting goal model to dict."""
        model = GoalModel(
            id="goal-456",
            description="Another goal",
            context={},
            status=GoalStatus.COMPLETED.value,
            priority=Priority.NORMAL.value,
            success_criteria=[],
            tokens_used=1000,
            execution_time_ms=5000,
        )
        model.created_at = datetime(2024, 1, 1, 12, 0, 0)
        model.tasks = []

        data = model.to_dict()

        assert data["id"] == "goal-456"
        assert data["description"] == "Another goal"
        assert data["tokens_used"] == 1000
        assert "created_at" in data


class TestTaskModel:
    """Tests for TaskModel."""

    def test_task_model_creation(self):
        """Test creating a task model."""
        model = TaskModel(
            id="task-123",
            goal_id="goal-123",
            description="Test task",
            task_type="analysis",
            status=TaskStatus.PENDING.value,
            priority=1,
        )

        assert model.id == "task-123"
        assert model.goal_id == "goal-123"
        assert model.description == "Test task"

    def test_task_model_to_dict(self):
        """Test converting task model to dict."""
        model = TaskModel(
            id="task-456",
            goal_id="goal-456",
            description="Another task",
            task_type="execution",
            status=TaskStatus.IN_PROGRESS.value,
            priority=2,
            assigned_agent_id="agent-789",
        )
        model.created_at = datetime(2024, 1, 1, 12, 0, 0)

        data = model.to_dict()

        assert data["id"] == "task-456"
        assert data["assigned_agent_id"] == "agent-789"


class TestAgentStateModel:
    """Tests for AgentStateModel."""

    def test_agent_state_model_creation(self):
        """Test creating an agent state model."""
        model = AgentStateModel(
            id="agent-123",
            agent_type="tool",
            name="test_agent",
            provider_key="anthropic_sonnet",
            model_name="claude-sonnet",
            capabilities=["code_execution"],
        )

        assert model.id == "agent-123"
        assert model.agent_type == "tool"
        assert model.capabilities == ["code_execution"]


class TestGoalRepository:
    """Tests for GoalRepository."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        session = AsyncMock()
        session.commit = AsyncMock()
        session.refresh = AsyncMock()
        session.rollback = AsyncMock()
        return session

    @pytest.fixture
    def sample_goal(self):
        """Create a sample goal."""
        return Goal(
            description="Test goal",
            context={"test": True},
            priority=Priority.HIGH,
            success_criteria=["Success"],
        )

    @pytest.mark.asyncio
    async def test_goal_to_model_conversion(self, sample_goal):
        """Test goal can be converted to model attributes."""
        # Verify goal has expected attributes for model creation
        assert sample_goal.id is not None
        assert sample_goal.description == "Test goal"
        assert sample_goal.status == GoalStatus.CREATED  # Default status
        assert sample_goal.priority == Priority.HIGH

    @pytest.mark.asyncio
    async def test_repository_initialization(self):
        """Test repository can be initialized."""
        repo = GoalRepository()
        assert repo is not None
        assert repo._session is None

    @pytest.mark.asyncio
    async def test_repository_with_session(self, mock_session):
        """Test repository with injected session."""
        repo = GoalRepository(session=mock_session)
        assert repo._session == mock_session


class TestTaskRepository:
    """Tests for TaskRepository."""

    @pytest.fixture
    def sample_task(self):
        """Create a sample task."""
        return Task(
            description="Test task",
            objective="Analyze data",
            context={"key": "value"},
        )

    @pytest.mark.asyncio
    async def test_task_to_model_conversion(self, sample_task):
        """Test task can be converted to model attributes."""
        assert sample_task.id is not None
        assert sample_task.description == "Test task"
        assert sample_task.status == TaskStatus.PENDING

    @pytest.mark.asyncio
    async def test_repository_initialization(self):
        """Test repository can be initialized."""
        repo = TaskRepository()
        assert repo is not None


class TestAgentStateRepository:
    """Tests for AgentStateRepository."""

    @pytest.mark.asyncio
    async def test_repository_initialization(self):
        """Test repository can be initialized."""
        repo = AgentStateRepository()
        assert repo is not None


class TestDatabaseIntegration:
    """Integration tests for database operations (require running DB)."""

    @pytest.mark.skip(reason="Requires running PostgreSQL database")
    @pytest.mark.asyncio
    async def test_goal_crud_operations(self):
        """Test full CRUD cycle for goals."""
        from src.persistence.database import init_database, close_database

        await init_database()

        try:
            repo = GoalRepository()

            # Create
            goal = Goal(
                description="Integration test goal",
                priority=Priority.NORMAL,
            )
            created = await repo.create(goal)
            assert created.id == goal.id

            # Read
            fetched = await repo.get(goal.id)
            assert fetched is not None
            assert fetched.description == "Integration test goal"

            # Update
            await repo.update_status(goal.id, GoalStatus.IN_PROGRESS)
            updated = await repo.get(goal.id)
            assert updated.status == GoalStatus.IN_PROGRESS.value

            # Delete
            deleted = await repo.delete(goal.id)
            assert deleted is True

            # Verify deletion
            gone = await repo.get(goal.id)
            assert gone is None

        finally:
            await close_database()

    @pytest.mark.skip(reason="Requires running PostgreSQL database")
    @pytest.mark.asyncio
    async def test_task_crud_operations(self):
        """Test full CRUD cycle for tasks."""
        from src.persistence.database import init_database, close_database

        await init_database()

        try:
            goal_repo = GoalRepository()
            task_repo = TaskRepository()

            # Create goal first
            goal = Goal(description="Task test goal")
            await goal_repo.create(goal)

            # Create task
            task = Task(description="Integration test task")
            created = await task_repo.create(task, goal.id)
            assert created.id == task.id

            # Read
            fetched = await task_repo.get(task.id)
            assert fetched is not None

            # Update
            await task_repo.update_status(task.id, TaskStatus.COMPLETED)
            updated = await task_repo.get(task.id)
            assert updated.status == TaskStatus.COMPLETED.value

            # Cleanup
            await goal_repo.delete(goal.id)

        finally:
            await close_database()
