"""Tests for message protocol."""

import pytest
from datetime import datetime, timezone

from src.core.message import (
    AgentMessage,
    AgentResult,
    Constraints,
    Goal,
    GoalContext,
    GoalStatus,
    MessageType,
    Priority,
    Reflection,
    Task,
    TaskStatus,
    generate_id,
)


class TestGenerateId:
    """Tests for ID generation."""

    def test_generates_unique_ids(self):
        """IDs should be unique."""
        ids = [generate_id() for _ in range(100)]
        assert len(set(ids)) == 100

    def test_id_is_string(self):
        """ID should be a string."""
        id_ = generate_id()
        assert isinstance(id_, str)
        assert len(id_) > 0


class TestConstraints:
    """Tests for Constraints dataclass."""

    def test_default_values(self):
        """Test default constraint values."""
        constraints = Constraints()
        assert constraints.max_tokens == 10_000
        assert constraints.max_time_seconds == 300
        assert constraints.risk_level == "low"
        assert constraints.requires_approval is False

    def test_to_dict(self):
        """Test serialization to dict."""
        constraints = Constraints(
            max_tokens=5000,
            risk_level="high",
            requires_approval=True,
        )
        data = constraints.to_dict()

        assert data["max_tokens"] == 5000
        assert data["risk_level"] == "high"
        assert data["requires_approval"] is True

    def test_from_dict(self):
        """Test deserialization from dict."""
        data = {
            "max_tokens": 5000,
            "risk_level": "high",
            "requires_approval": True,
        }
        constraints = Constraints.from_dict(data)

        assert constraints.max_tokens == 5000
        assert constraints.risk_level == "high"
        assert constraints.requires_approval is True


class TestTask:
    """Tests for Task dataclass."""

    def test_create_task(self):
        """Test task creation."""
        task = Task(
            description="Test task",
            objective="Test objective",
        )

        assert task.description == "Test task"
        assert task.objective == "Test objective"
        assert task.status == TaskStatus.PENDING
        assert task.id is not None

    def test_task_to_dict(self):
        """Test task serialization."""
        task = Task(
            description="Test task",
            objective="Test objective",
            expected_output="Test output",
        )
        data = task.to_dict()

        assert data["description"] == "Test task"
        assert data["objective"] == "Test objective"
        assert data["status"] == "pending"
        assert "id" in data
        assert "created_at" in data


class TestGoal:
    """Tests for Goal dataclass."""

    def test_create_goal(self):
        """Test goal creation."""
        goal = Goal(
            description="Test goal",
            success_criteria=["Criterion 1", "Criterion 2"],
        )

        assert goal.description == "Test goal"
        assert len(goal.success_criteria) == 2
        assert goal.status == GoalStatus.CREATED
        assert goal.priority == Priority.NORMAL

    def test_goal_with_tasks(self):
        """Test goal with tasks."""
        goal = Goal(description="Test goal")
        task1 = Task(goal_id=goal.id, description="Task 1")
        task2 = Task(goal_id=goal.id, description="Task 2")
        goal.tasks = [task1, task2]

        assert len(goal.tasks) == 2
        assert goal.tasks[0].goal_id == goal.id

    def test_goal_to_dict(self):
        """Test goal serialization."""
        goal = Goal(
            description="Test goal",
            priority=Priority.HIGH,
        )
        data = goal.to_dict()

        assert data["description"] == "Test goal"
        assert data["priority"] == 3
        assert data["status"] == "created"


class TestGoalContext:
    """Tests for GoalContext."""

    def test_create_context(self, sample_goal):
        """Test context creation."""
        context = GoalContext(goal=sample_goal)

        assert context.goal == sample_goal
        assert context.depth == 0
        assert context.tokens_used == 0

    def test_nested_depth(self, sample_goal):
        """Test nested context depth calculation."""
        parent = GoalContext(goal=sample_goal, depth=1)
        child = GoalContext(goal=sample_goal, depth=2, parent_context=parent)
        grandchild = GoalContext(goal=sample_goal, depth=1, parent_context=child)

        assert parent.get_total_depth() == 1
        assert child.get_total_depth() == 3
        assert grandchild.get_total_depth() == 4

    def test_nested_tokens(self, sample_goal):
        """Test nested context token calculation."""
        parent = GoalContext(goal=sample_goal, tokens_used=100)
        child = GoalContext(goal=sample_goal, tokens_used=200, parent_context=parent)

        assert parent.get_total_tokens() == 100
        assert child.get_total_tokens() == 300


class TestAgentMessage:
    """Tests for AgentMessage."""

    def test_create_message(self):
        """Test message creation."""
        message = AgentMessage(
            message_type=MessageType.REQUEST,
            sender="agent1",
            recipient="agent2",
            content={"key": "value"},
        )

        assert message.message_type == MessageType.REQUEST
        assert message.sender == "agent1"
        assert message.recipient == "agent2"
        assert message.content == {"key": "value"}

    def test_create_response(self):
        """Test creating response to a message."""
        original = AgentMessage(
            message_type=MessageType.REQUEST,
            sender="agent1",
            sender_type="planner",
            recipient="agent2",
            recipient_type="tool",
            goal_id="goal_123",
        )

        response = original.create_response(
            sender="agent2",
            sender_type="tool",
            content={"result": "success"},
        )

        assert response.message_type == MessageType.RESPONSE
        assert response.sender == "agent2"
        assert response.recipient == "agent1"
        assert response.parent_message_id == original.id
        assert response.goal_id == original.goal_id


class TestAgentResult:
    """Tests for AgentResult."""

    def test_successful_result(self):
        """Test successful result."""
        result = AgentResult(
            task_id="task_123",
            agent_id="agent_456",
            agent_type="tool",
            success=True,
            result={"output": "data"},
            confidence=0.9,
        )

        assert result.success is True
        assert result.confidence == 0.9
        assert result.error is None

    def test_failed_result(self):
        """Test failed result."""
        result = AgentResult(
            task_id="task_123",
            agent_id="agent_456",
            agent_type="tool",
            success=False,
            error="Task failed",
        )

        assert result.success is False
        assert result.error == "Task failed"


class TestReflection:
    """Tests for Reflection."""

    def test_create_reflection(self):
        """Test reflection creation."""
        reflection = Reflection(
            agent_id="agent_123",
            task_id="task_456",
            performance_score=0.8,
            lessons_learned=["Lesson 1"],
            successes=["Success 1"],
            failures=["Failure 1"],
        )

        assert reflection.performance_score == 0.8
        assert len(reflection.lessons_learned) == 1
        assert len(reflection.successes) == 1
        assert len(reflection.failures) == 1
