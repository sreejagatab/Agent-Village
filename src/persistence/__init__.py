"""
Persistence layer for Agent Village.

Provides database models and repositories for:
- Goals and tasks
- Agent state
- Memory entries
"""

from src.persistence.database import (
    get_async_session,
    init_database,
    close_database,
)
from src.persistence.models import (
    GoalModel,
    TaskModel,
    AgentStateModel,
)
from src.persistence.repositories import (
    GoalRepository,
    TaskRepository,
)

__all__ = [
    "get_async_session",
    "init_database",
    "close_database",
    "GoalModel",
    "TaskModel",
    "AgentStateModel",
    "GoalRepository",
    "TaskRepository",
]
