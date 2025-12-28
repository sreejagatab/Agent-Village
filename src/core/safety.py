"""
Safety gates for Agent Village.

This module implements hard safety limits that CANNOT be bypassed.
Every execution must pass through these gates before proceeding.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

import structlog

from src.config import get_settings
from src.core.message import GoalContext, Task

logger = structlog.get_logger()


class SafetyCheckResult(str, Enum):
    """Result of a safety check."""

    PASSED = "passed"
    FAILED = "failed"
    REQUIRES_APPROVAL = "requires_approval"


@dataclass
class SafetyViolation:
    """Details of a safety violation."""

    check_name: str
    message: str
    current_value: Any
    limit_value: Any
    severity: str = "error"  # warning, error, critical
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "check_name": self.check_name,
            "message": self.message,
            "current_value": self.current_value,
            "limit_value": self.limit_value,
            "severity": self.severity,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class SafetyLimits:
    """
    Hard safety limits for the system.

    These limits CANNOT be exceeded under any circumstances.
    """

    # Recursion control
    max_recursion_depth: int = 10

    # Agent spawn limits
    max_agent_spawns: int = 50
    max_concurrent_agents: int = 20

    # Token budgets
    max_tokens_per_task: int = 100_000
    max_tokens_per_goal: int = 500_000

    # Time limits
    max_execution_time_seconds: int = 3600  # 1 hour
    max_task_time_seconds: int = 300  # 5 minutes

    # Action controls
    require_human_approval: set[str] = field(
        default_factory=lambda: {"deploy", "delete", "payment", "admin", "execute_code"}
    )
    blocked_actions: set[str] = field(
        default_factory=lambda: {"rm -rf", "drop database", "format"}
    )
    allowed_tools: set[str] = field(default_factory=set)

    # Risk levels
    max_risk_level: str = "high"  # low, medium, high, critical

    @classmethod
    def from_settings(cls) -> "SafetyLimits":
        """Create SafetyLimits from application settings."""
        settings = get_settings()
        safety = settings.safety

        return cls(
            max_recursion_depth=safety.max_recursion_depth,
            max_agent_spawns=safety.max_agent_spawns,
            max_tokens_per_task=safety.max_tokens_per_task,
            max_execution_time_seconds=safety.max_execution_time_seconds,
            require_human_approval=set(safety.require_human_approval),
            allowed_tools=safety.allowed_tools,
        )


@dataclass
class SafetyCheckReport:
    """Complete report of all safety checks."""

    passed: bool
    checks: dict[str, SafetyCheckResult]
    violations: list[SafetyViolation]
    requires_approval: bool = False
    approval_reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "passed": self.passed,
            "checks": {k: v.value for k, v in self.checks.items()},
            "violations": [v.to_dict() for v in self.violations],
            "requires_approval": self.requires_approval,
            "approval_reasons": self.approval_reasons,
        }


class SafetyGate:
    """
    Safety gate that enforces hard limits.

    All execution must pass through this gate.
    No exceptions. No overrides.
    """

    def __init__(self, limits: SafetyLimits | None = None):
        self.limits = limits or SafetyLimits.from_settings()
        self.logger = logger.bind(component="safety_gate")

    def check_all(self, context: GoalContext, task: Task | None = None) -> SafetyCheckReport:
        """
        Run all safety checks.

        Args:
            context: Current execution context
            task: Optional task being executed

        Returns:
            SafetyCheckReport with all results
        """
        checks: dict[str, SafetyCheckResult] = {}
        violations: list[SafetyViolation] = []
        approval_reasons: list[str] = []

        # Run all checks
        checks["recursion"] = self._check_recursion(context, violations)
        checks["tokens"] = self._check_tokens(context, violations)
        checks["agents"] = self._check_agent_spawns(context, violations)
        checks["time"] = self._check_execution_time(context, violations)

        if task:
            checks["risk"] = self._check_risk_level(task, violations)
            approval_result = self._check_requires_approval(task, approval_reasons)
            checks["approval"] = approval_result

        # Determine overall result
        passed = all(v == SafetyCheckResult.PASSED for v in checks.values())
        requires_approval = SafetyCheckResult.REQUIRES_APPROVAL in checks.values()

        report = SafetyCheckReport(
            passed=passed,
            checks=checks,
            violations=violations,
            requires_approval=requires_approval,
            approval_reasons=approval_reasons,
        )

        if not passed:
            self.logger.warning(
                "Safety check failed",
                violations=[v.to_dict() for v in violations],
            )

        return report

    def _check_recursion(
        self, context: GoalContext, violations: list[SafetyViolation]
    ) -> SafetyCheckResult:
        """Check recursion depth."""
        total_depth = context.get_total_depth()

        if total_depth >= self.limits.max_recursion_depth:
            violations.append(
                SafetyViolation(
                    check_name="recursion_depth",
                    message=f"Recursion depth {total_depth} exceeds limit {self.limits.max_recursion_depth}",
                    current_value=total_depth,
                    limit_value=self.limits.max_recursion_depth,
                    severity="critical",
                )
            )
            return SafetyCheckResult.FAILED

        return SafetyCheckResult.PASSED

    def _check_tokens(
        self, context: GoalContext, violations: list[SafetyViolation]
    ) -> SafetyCheckResult:
        """Check token budget."""
        total_tokens = context.get_total_tokens()

        if total_tokens >= self.limits.max_tokens_per_goal:
            violations.append(
                SafetyViolation(
                    check_name="token_budget",
                    message=f"Token usage {total_tokens} exceeds goal limit {self.limits.max_tokens_per_goal}",
                    current_value=total_tokens,
                    limit_value=self.limits.max_tokens_per_goal,
                    severity="critical",
                )
            )
            return SafetyCheckResult.FAILED

        return SafetyCheckResult.PASSED

    def _check_agent_spawns(
        self, context: GoalContext, violations: list[SafetyViolation]
    ) -> SafetyCheckResult:
        """Check agent spawn count."""
        total_agents = context.get_total_agents()

        if total_agents >= self.limits.max_agent_spawns:
            violations.append(
                SafetyViolation(
                    check_name="agent_spawns",
                    message=f"Agent count {total_agents} exceeds limit {self.limits.max_agent_spawns}",
                    current_value=total_agents,
                    limit_value=self.limits.max_agent_spawns,
                    severity="critical",
                )
            )
            return SafetyCheckResult.FAILED

        return SafetyCheckResult.PASSED

    def _check_execution_time(
        self, context: GoalContext, violations: list[SafetyViolation]
    ) -> SafetyCheckResult:
        """Check execution time."""
        elapsed = (datetime.now(timezone.utc) - context.start_time).total_seconds()

        if elapsed >= self.limits.max_execution_time_seconds:
            violations.append(
                SafetyViolation(
                    check_name="execution_time",
                    message=f"Execution time {elapsed:.0f}s exceeds limit {self.limits.max_execution_time_seconds}s",
                    current_value=elapsed,
                    limit_value=self.limits.max_execution_time_seconds,
                    severity="critical",
                )
            )
            return SafetyCheckResult.FAILED

        return SafetyCheckResult.PASSED

    def _check_risk_level(
        self, task: Task, violations: list[SafetyViolation]
    ) -> SafetyCheckResult:
        """Check task risk level."""
        risk_levels = {"low": 1, "medium": 2, "high": 3, "critical": 4}

        task_risk = risk_levels.get(task.constraints.risk_level, 1)
        max_risk = risk_levels.get(self.limits.max_risk_level, 3)

        if task_risk > max_risk:
            violations.append(
                SafetyViolation(
                    check_name="risk_level",
                    message=f"Task risk level '{task.constraints.risk_level}' exceeds maximum '{self.limits.max_risk_level}'",
                    current_value=task.constraints.risk_level,
                    limit_value=self.limits.max_risk_level,
                    severity="error",
                )
            )
            return SafetyCheckResult.FAILED

        return SafetyCheckResult.PASSED

    def _check_requires_approval(
        self, task: Task, approval_reasons: list[str]
    ) -> SafetyCheckResult:
        """Check if task requires human approval."""
        if task.constraints.requires_approval:
            reason = task.constraints.approval_reason or "Task marked as requiring approval"
            approval_reasons.append(reason)
            return SafetyCheckResult.REQUIRES_APPROVAL

        # Check if task description contains approval-required keywords
        description_lower = task.description.lower()
        for action in self.limits.require_human_approval:
            if action.lower() in description_lower:
                approval_reasons.append(f"Action '{action}' requires human approval")
                return SafetyCheckResult.REQUIRES_APPROVAL

        return SafetyCheckResult.PASSED

    def check_tool_permission(self, tool_name: str, action: str = "") -> bool:
        """
        Check if a tool action is permitted.

        Args:
            tool_name: Name of the tool
            action: Specific action being performed

        Returns:
            True if permitted
        """
        # Check blocked actions
        full_action = f"{tool_name} {action}".strip().lower()
        for blocked in self.limits.blocked_actions:
            if blocked.lower() in full_action:
                self.logger.warning("Blocked action attempted", action=full_action)
                return False

        # Check allowed tools if list is specified
        if self.limits.allowed_tools:
            return tool_name in self.limits.allowed_tools

        return True

    def enforce(self, context: GoalContext, task: Task | None = None) -> None:
        """
        Enforce safety limits, raising an exception if violated.

        Args:
            context: Current execution context
            task: Optional task being executed

        Raises:
            SafetyViolationError: If any safety check fails
        """
        report = self.check_all(context, task)

        if not report.passed:
            raise SafetyViolationError(report)


class SafetyViolationError(Exception):
    """Exception raised when safety limits are violated."""

    def __init__(self, report: SafetyCheckReport):
        self.report = report
        violations = "; ".join(v.message for v in report.violations)
        super().__init__(f"Safety violation: {violations}")


# Global safety gate instance
_safety_gate: SafetyGate | None = None


def get_safety_gate() -> SafetyGate:
    """Get the global safety gate instance."""
    global _safety_gate
    if _safety_gate is None:
        _safety_gate = SafetyGate()
    return _safety_gate


def reset_safety_gate(limits: SafetyLimits | None = None) -> SafetyGate:
    """Reset the global safety gate with new limits."""
    global _safety_gate
    _safety_gate = SafetyGate(limits)
    return _safety_gate
