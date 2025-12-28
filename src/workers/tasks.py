"""
Celery tasks for Agent Village.

Defines async tasks for goal execution, agent spawning, and system maintenance.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any

import structlog
from celery import shared_task, Task
from celery.exceptions import SoftTimeLimitExceeded

from src.workers.celery_app import celery_app, TaskPriority

logger = structlog.get_logger()


class AsyncTask(Task):
    """Base task class with async support."""

    abstract = True

    def run_async(self, coro):
        """Run an async coroutine in the task."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()


# =============================================================================
# Goal Execution Tasks
# =============================================================================

@celery_app.task(
    bind=True,
    base=AsyncTask,
    name="src.workers.tasks.execute_goal",
    max_retries=3,
    default_retry_delay=60,
    soft_time_limit=3300,
    time_limit=3600,
)
def execute_goal(self, goal_id: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
    """
    Execute a goal asynchronously.

    This is the main entry point for goal execution. It:
    1. Loads the goal from the database
    2. Initializes the Governor agent
    3. Executes the goal through the FSM
    4. Returns the result

    Args:
        goal_id: ID of the goal to execute
        context: Optional additional context

    Returns:
        Dict with execution result and metadata
    """
    logger.info("Starting goal execution", goal_id=goal_id, task_id=self.request.id)

    async def _execute():
        from src.persistence.database import get_async_session
        from src.persistence.repositories import GoalRepository
        from src.core.governor import Governor
        from src.core.message import GoalStatus
        from src.providers import create_provider_pool

        async with get_async_session() as session:
            repo = GoalRepository(session)

            # Load goal
            goal = await repo.get_by_id(goal_id)
            if not goal:
                return {"success": False, "error": f"Goal not found: {goal_id}"}

            # Update status
            goal.status = GoalStatus.RUNNING.value
            goal.started_at = datetime.utcnow()
            await session.commit()

            try:
                # Initialize provider pool
                provider_pool = create_provider_pool()

                # Create and run governor
                governor = Governor(provider_pool=provider_pool)
                await governor.initialize()

                # Execute goal
                result = await governor.execute_goal(
                    goal_id=goal_id,
                    description=goal.description,
                    context={**goal.context, **(context or {})},
                )

                # Update goal with result
                goal.status = GoalStatus.COMPLETED.value
                goal.result = result
                goal.completed_at = datetime.utcnow()
                goal.execution_time_ms = int(
                    (goal.completed_at - goal.started_at).total_seconds() * 1000
                )
                await session.commit()

                return {
                    "success": True,
                    "goal_id": goal_id,
                    "result": result,
                    "execution_time_ms": goal.execution_time_ms,
                }

            except SoftTimeLimitExceeded:
                goal.status = GoalStatus.FAILED.value
                goal.error = "Execution timed out"
                await session.commit()
                raise

            except Exception as e:
                logger.error("Goal execution failed", goal_id=goal_id, error=str(e))
                goal.status = GoalStatus.FAILED.value
                goal.error = str(e)
                await session.commit()
                return {"success": False, "error": str(e)}

            finally:
                await governor.shutdown()

    try:
        return self.run_async(_execute())
    except SoftTimeLimitExceeded:
        logger.warning("Goal execution soft time limit exceeded", goal_id=goal_id)
        raise self.retry(countdown=120, max_retries=1)
    except Exception as e:
        logger.error("Goal execution error", goal_id=goal_id, error=str(e))
        raise self.retry(exc=e, countdown=60)


@celery_app.task(
    bind=True,
    base=AsyncTask,
    name="src.workers.tasks.execute_task",
    max_retries=3,
    default_retry_delay=30,
)
def execute_task(
    self,
    task_id: str,
    agent_id: str,
    input_data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Execute a single task with a specific agent.

    Args:
        task_id: ID of the task to execute
        agent_id: ID of the agent to use
        input_data: Input data for the task

    Returns:
        Dict with task result
    """
    logger.info("Starting task execution", task_id=task_id, agent_id=agent_id)

    async def _execute():
        from src.persistence.database import get_async_session
        from src.persistence.repositories import TaskRepository
        from src.core.registry import get_agent_registry
        from src.core.message import TaskStatus

        async with get_async_session() as session:
            repo = TaskRepository(session)

            # Load task
            task = await repo.get_by_id(task_id)
            if not task:
                return {"success": False, "error": f"Task not found: {task_id}"}

            # Update status
            task.status = TaskStatus.RUNNING.value
            task.started_at = datetime.utcnow()
            await session.commit()

            try:
                # Get agent from registry
                registry = get_agent_registry()
                agent = registry.get(agent_id)
                if not agent:
                    raise ValueError(f"Agent not found: {agent_id}")

                # Execute task
                from src.core.message import AgentMessage, MessageType, Task as TaskModel

                message = AgentMessage(
                    message_type=MessageType.TASK_ASSIGNED,
                    sender="worker",
                    recipient=agent_id,
                    task=TaskModel(
                        id=task_id,
                        description=task.description,
                        input_data=input_data or task.input_data,
                    ),
                )

                result = await agent.execute(message)

                # Update task with result
                task.status = TaskStatus.COMPLETED.value
                task.output_data = result.content if result else {}
                task.completed_at = datetime.utcnow()
                task.execution_time_ms = int(
                    (task.completed_at - task.started_at).total_seconds() * 1000
                )
                await session.commit()

                return {
                    "success": True,
                    "task_id": task_id,
                    "result": task.output_data,
                }

            except Exception as e:
                logger.error("Task execution failed", task_id=task_id, error=str(e))
                task.status = TaskStatus.FAILED.value
                task.error = str(e)
                task.retries += 1
                await session.commit()
                return {"success": False, "error": str(e)}

    try:
        return self.run_async(_execute())
    except Exception as e:
        logger.error("Task execution error", task_id=task_id, error=str(e))
        raise self.retry(exc=e, countdown=30)


# =============================================================================
# Agent Management Tasks
# =============================================================================

@celery_app.task(
    bind=True,
    base=AsyncTask,
    name="src.workers.tasks.spawn_agent",
)
def spawn_agent(
    self,
    agent_type: str,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Spawn a new agent of the specified type.

    Args:
        agent_type: Type of agent to create
        config: Agent configuration

    Returns:
        Dict with agent info
    """
    logger.info("Spawning agent", agent_type=agent_type)

    async def _spawn():
        from src.core.registry import get_agent_registry
        from src.agents import create_agent

        registry = get_agent_registry()

        # Create agent
        agent = await create_agent(agent_type, config or {})
        await agent.initialize()

        # Register agent
        registry.register(agent)

        return {
            "success": True,
            "agent_id": agent.id,
            "agent_type": agent_type,
        }

    try:
        return self.run_async(_spawn())
    except Exception as e:
        logger.error("Agent spawn failed", agent_type=agent_type, error=str(e))
        return {"success": False, "error": str(e)}


# =============================================================================
# Maintenance Tasks
# =============================================================================

@celery_app.task(name="src.workers.tasks.cleanup_expired_goals")
def cleanup_expired_goals() -> dict[str, Any]:
    """
    Clean up expired or stale goals.

    Runs periodically to:
    - Cancel goals stuck in running state for too long
    - Clean up old completed goals
    """
    logger.info("Running expired goals cleanup")

    async def _cleanup():
        from src.persistence.database import get_async_session
        from src.persistence.repositories import GoalRepository
        from src.core.message import GoalStatus

        async with get_async_session() as session:
            repo = GoalRepository(session)

            # Find stuck goals (running for more than 2 hours)
            cutoff = datetime.utcnow() - timedelta(hours=2)
            stuck_goals = await repo.find_stuck(cutoff)

            cancelled_count = 0
            for goal in stuck_goals:
                goal.status = GoalStatus.CANCELLED.value
                goal.error = "Cancelled: exceeded maximum execution time"
                cancelled_count += 1

            await session.commit()

            return {
                "success": True,
                "cancelled_count": cancelled_count,
            }

    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(_cleanup())
    finally:
        loop.close()


@celery_app.task(name="src.workers.tasks.health_check")
def health_check() -> dict[str, Any]:
    """
    Periodic health check task.

    Verifies:
    - Database connectivity
    - Redis connectivity
    - Provider availability
    """
    logger.debug("Running health check")

    async def _check():
        results = {
            "timestamp": datetime.utcnow().isoformat(),
            "database": False,
            "redis": False,
            "providers": {},
        }

        # Check database
        try:
            from src.persistence.database import get_async_session
            async with get_async_session() as session:
                await session.execute("SELECT 1")
                results["database"] = True
        except Exception as e:
            results["database_error"] = str(e)

        # Check Redis
        try:
            import redis.asyncio as redis
            from src.config import get_settings
            settings = get_settings()
            client = redis.from_url(settings.memory.redis_url)
            await client.ping()
            results["redis"] = True
            await client.close()
        except Exception as e:
            results["redis_error"] = str(e)

        # Check providers
        try:
            from src.providers import create_provider_pool
            pool = create_provider_pool()
            results["providers"] = await pool.health_check_all()
        except Exception as e:
            results["providers_error"] = str(e)

        results["healthy"] = results["database"] and results["redis"]
        return results

    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(_check())
    finally:
        loop.close()


# =============================================================================
# Utility Tasks
# =============================================================================

@celery_app.task(
    bind=True,
    name="src.workers.tasks.broadcast_event",
)
def broadcast_event(
    self,
    event_type: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """
    Broadcast an event to all connected WebSocket clients.

    Args:
        event_type: Type of event
        payload: Event payload

    Returns:
        Dict with broadcast result
    """
    logger.info("Broadcasting event", event_type=event_type)

    async def _broadcast():
        from src.api.websocket import broadcast_message

        await broadcast_message({
            "type": event_type,
            "payload": payload,
            "timestamp": datetime.utcnow().isoformat(),
        })

        return {"success": True, "event_type": event_type}

    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(_broadcast())
    finally:
        loop.close()
