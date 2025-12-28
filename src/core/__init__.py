"""Core framework for Agent Village."""

from src.core.message import (
    AgentMessage,
    AgentResult,
    Goal,
    GoalContext,
    MessageType,
    Priority,
    Task,
)

# Lazy imports to avoid circular dependencies
def get_agent_manager():
    """Get AgentManager class (lazy import)."""
    from src.core.agent_manager import AgentManager
    return AgentManager


__all__ = [
    "AgentMessage",
    "AgentResult",
    "Goal",
    "GoalContext",
    "MessageType",
    "Priority",
    "Task",
    "get_agent_manager",
]
