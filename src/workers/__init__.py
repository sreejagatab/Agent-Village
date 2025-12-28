"""
Worker module for Agent Village.

Provides Celery-based task queue for async goal and agent execution.
"""

from src.workers.celery_app import celery_app
from src.workers.tasks import execute_goal, execute_task, spawn_agent

__all__ = [
    "celery_app",
    "execute_goal",
    "execute_task",
    "spawn_agent",
]
