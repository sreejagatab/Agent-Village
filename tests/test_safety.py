"""Tests for safety gates."""

import pytest
from datetime import datetime, timezone, timedelta

from src.core.message import Constraints, Goal, GoalContext, Task
from src.core.safety import (
    SafetyCheckResult,
    SafetyGate,
    SafetyLimits,
    SafetyViolation,
    SafetyViolationError,
)


class TestSafetyLimits:
    """Tests for SafetyLimits."""

    def test_default_limits(self):
        """Test default safety limits."""
        limits = SafetyLimits()

        assert limits.max_recursion_depth == 10
        assert limits.max_agent_spawns == 50
        assert limits.max_tokens_per_task == 100_000
        assert limits.max_execution_time_seconds == 3600

    def test_custom_limits(self):
        """Test custom safety limits."""
        limits = SafetyLimits(
            max_recursion_depth=5,
            max_agent_spawns=20,
        )

        assert limits.max_recursion_depth == 5
        assert limits.max_agent_spawns == 20


class TestSafetyGate:
    """Tests for SafetyGate."""

    def test_check_all_passes(self, safety_gate, goal_context):
        """Test that check_all passes for valid context."""
        report = safety_gate.check_all(goal_context)

        assert report.passed is True
        assert len(report.violations) == 0

    def test_recursion_limit_exceeded(self, safety_gate, sample_goal):
        """Test recursion limit violation."""
        context = GoalContext(goal=sample_goal, depth=10)
        report = safety_gate.check_all(context)

        assert report.passed is False
        assert any(v.check_name == "recursion_depth" for v in report.violations)

    def test_token_limit_exceeded(self, safety_gate, sample_goal):
        """Test token limit violation."""
        context = GoalContext(goal=sample_goal, tokens_used=100_000)
        report = safety_gate.check_all(context)

        assert report.passed is False
        assert any(v.check_name == "token_budget" for v in report.violations)

    def test_agent_spawn_limit_exceeded(self, safety_gate, sample_goal):
        """Test agent spawn limit violation."""
        context = GoalContext(goal=sample_goal, agents_spawned=15)
        report = safety_gate.check_all(context)

        assert report.passed is False
        assert any(v.check_name == "agent_spawns" for v in report.violations)

    def test_execution_time_limit(self, safety_gate, sample_goal):
        """Test execution time limit."""
        # Create context with old start time
        context = GoalContext(goal=sample_goal)
        context.start_time = datetime.now(timezone.utc) - timedelta(hours=2)

        report = safety_gate.check_all(context)

        assert report.passed is False
        assert any(v.check_name == "execution_time" for v in report.violations)

    def test_requires_approval(self, safety_gate, sample_goal):
        """Test approval requirement detection."""
        task = Task(
            description="Deploy the application to production",
            constraints=Constraints(risk_level="high"),
        )
        context = GoalContext(goal=sample_goal)

        report = safety_gate.check_all(context, task)

        assert report.requires_approval is True
        assert "deploy" in report.approval_reasons[0].lower()

    def test_enforce_raises_on_violation(self, safety_gate, sample_goal):
        """Test that enforce raises exception on violation."""
        context = GoalContext(goal=sample_goal, depth=10)

        with pytest.raises(SafetyViolationError) as exc_info:
            safety_gate.enforce(context)

        assert "recursion" in str(exc_info.value).lower()

    def test_tool_permission_check(self, safety_gate):
        """Test tool permission checking."""
        # Should allow normal tools
        assert safety_gate.check_tool_permission("read_file", "test.txt") is True

        # Should block dangerous commands
        assert safety_gate.check_tool_permission("shell", "rm -rf /") is False


class TestSafetyViolation:
    """Tests for SafetyViolation."""

    def test_violation_to_dict(self):
        """Test violation serialization."""
        violation = SafetyViolation(
            check_name="test_check",
            message="Test violation",
            current_value=10,
            limit_value=5,
            severity="error",
        )

        data = violation.to_dict()

        assert data["check_name"] == "test_check"
        assert data["message"] == "Test violation"
        assert data["current_value"] == 10
        assert data["limit_value"] == 5
        assert data["severity"] == "error"


class TestNestedContextSafety:
    """Tests for safety in nested contexts."""

    def test_nested_recursion_depth(self, safety_gate, sample_goal):
        """Test recursion depth is calculated across nested contexts."""
        parent = GoalContext(goal=sample_goal, depth=3)
        child = GoalContext(goal=sample_goal, depth=3, parent_context=parent)

        # Total depth is 6, limit is 5
        report = safety_gate.check_all(child)

        assert report.passed is False
        assert any(v.check_name == "recursion_depth" for v in report.violations)

    def test_nested_token_budget(self, safety_gate, sample_goal):
        """Test token budget is calculated across nested contexts."""
        parent = GoalContext(goal=sample_goal, tokens_used=30_000)
        child = GoalContext(goal=sample_goal, tokens_used=25_000, parent_context=parent)

        # Total tokens is 55,000, limit is 50,000
        report = safety_gate.check_all(child)

        assert report.passed is False
        assert any(v.check_name == "token_budget" for v in report.violations)
