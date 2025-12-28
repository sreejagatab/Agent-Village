"""
Celery application configuration for Agent Village.

Provides distributed task queue for goal and agent execution.
"""

import os
from celery import Celery
from kombu import Exchange, Queue

from src.config import get_settings

settings = get_settings()

# Celery configuration
celery_app = Celery(
    "agent_village",
    broker=settings.memory.redis_url,
    backend=settings.memory.redis_url,
    include=[
        "src.workers.tasks",
    ],
)

# Celery configuration
celery_app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,

    # Task execution settings
    task_acks_late=True,  # Acknowledge after task completes
    task_reject_on_worker_lost=True,  # Requeue if worker dies
    task_time_limit=3600,  # 1 hour hard limit
    task_soft_time_limit=3300,  # 55 min soft limit (for cleanup)

    # Result settings
    result_expires=86400,  # Results expire after 24 hours
    result_extended=True,  # Store additional metadata

    # Worker settings
    worker_prefetch_multiplier=1,  # One task at a time
    worker_concurrency=4,  # Number of concurrent workers
    worker_max_tasks_per_child=100,  # Restart worker after 100 tasks

    # Rate limiting
    task_default_rate_limit="10/s",

    # Task routing
    task_routes={
        "src.workers.tasks.execute_goal": {"queue": "goals"},
        "src.workers.tasks.execute_task": {"queue": "tasks"},
        "src.workers.tasks.spawn_agent": {"queue": "agents"},
        "src.workers.tasks.health_check": {"queue": "default"},
    },

    # Queue definitions
    task_queues=(
        Queue("default", Exchange("default"), routing_key="default"),
        Queue("goals", Exchange("goals"), routing_key="goals"),
        Queue("tasks", Exchange("tasks"), routing_key="tasks"),
        Queue("agents", Exchange("agents"), routing_key="agents"),
        Queue("priority", Exchange("priority"), routing_key="priority"),
    ),

    task_default_queue="default",
    task_default_exchange="default",
    task_default_routing_key="default",

    # Beat scheduler (for periodic tasks)
    beat_schedule={
        "cleanup-expired-goals": {
            "task": "src.workers.tasks.cleanup_expired_goals",
            "schedule": 3600.0,  # Every hour
        },
        "health-check": {
            "task": "src.workers.tasks.health_check",
            "schedule": 60.0,  # Every minute
        },
    },

    # Error handling
    task_annotations={
        "*": {
            "rate_limit": "10/s",
            "max_retries": 3,
            "default_retry_delay": 60,
        },
    },
)


# Task priority configuration
class TaskPriority:
    """Task priority levels."""

    CRITICAL = 0
    HIGH = 3
    NORMAL = 5
    LOW = 7
    BACKGROUND = 9


def get_celery_app() -> Celery:
    """Get the configured Celery application."""
    return celery_app
