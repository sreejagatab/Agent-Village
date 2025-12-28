"""
Repository pattern implementations for database operations.

Provides clean abstractions for CRUD operations on Goals and Tasks.
"""

from datetime import datetime
from typing import Any

import structlog
from sqlalchemy import select, update, delete, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.message import Goal, GoalStatus, Priority, Task, TaskStatus
from src.persistence.database import get_async_session
from src.persistence.models import GoalModel, TaskModel, AgentStateModel

logger = structlog.get_logger()


class GoalRepository:
    """Repository for Goal persistence operations."""

    def __init__(self, session: AsyncSession | None = None):
        self._session = session
        self.logger = logger.bind(repository="goal")

    async def _get_session(self) -> AsyncSession:
        """Get session (injected or create new)."""
        if self._session:
            return self._session
        async with get_async_session() as session:
            return session

    async def create(self, goal: Goal) -> GoalModel:
        """Create a new goal in the database."""
        async with get_async_session() as session:
            model = GoalModel(
                id=goal.id,
                description=goal.description,
                context=goal.context,
                status=goal.status.value,
                priority=goal.priority.value,
                success_criteria=goal.success_criteria,
                created_at=goal.created_at,
            )
            session.add(model)
            await session.commit()
            await session.refresh(model)

            self.logger.info("Goal created", goal_id=goal.id)
            return model

    async def get(self, goal_id: str) -> GoalModel | None:
        """Get a goal by ID."""
        async with get_async_session() as session:
            result = await session.execute(
                select(GoalModel).where(GoalModel.id == goal_id)
            )
            return result.scalar_one_or_none()

    async def get_with_tasks(self, goal_id: str) -> GoalModel | None:
        """Get a goal with all its tasks."""
        async with get_async_session() as session:
            result = await session.execute(
                select(GoalModel)
                .where(GoalModel.id == goal_id)
            )
            goal = result.scalar_one_or_none()
            if goal:
                # Tasks are loaded via selectin relationship
                _ = goal.tasks
            return goal

    async def update(self, goal_id: str, updates: dict[str, Any]) -> bool:
        """Update a goal."""
        async with get_async_session() as session:
            # Convert enum values
            if "status" in updates and isinstance(updates["status"], GoalStatus):
                updates["status"] = updates["status"].value
            if "priority" in updates and isinstance(updates["priority"], Priority):
                updates["priority"] = updates["priority"].value

            result = await session.execute(
                update(GoalModel)
                .where(GoalModel.id == goal_id)
                .values(**updates)
            )
            await session.commit()

            success = result.rowcount > 0
            if success:
                self.logger.info("Goal updated", goal_id=goal_id, updates=list(updates.keys()))
            return success

    async def update_status(
        self,
        goal_id: str,
        status: GoalStatus,
        error: str | None = None,
        result: dict[str, Any] | None = None,
    ) -> bool:
        """Update goal status with optional error/result."""
        updates: dict[str, Any] = {"status": status.value}

        if status == GoalStatus.IN_PROGRESS:
            updates["started_at"] = datetime.utcnow()
        elif status in (GoalStatus.COMPLETED, GoalStatus.FAILED, GoalStatus.CANCELLED):
            updates["completed_at"] = datetime.utcnow()

        if error:
            updates["error"] = error
        if result:
            updates["result"] = result

        return await self.update(goal_id, updates)

    async def delete(self, goal_id: str) -> bool:
        """Delete a goal and its tasks."""
        async with get_async_session() as session:
            result = await session.execute(
                delete(GoalModel).where(GoalModel.id == goal_id)
            )
            await session.commit()

            success = result.rowcount > 0
            if success:
                self.logger.info("Goal deleted", goal_id=goal_id)
            return success

    async def list_by_status(
        self,
        status: GoalStatus | list[GoalStatus] | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[GoalModel]:
        """List goals filtered by status."""
        async with get_async_session() as session:
            query = select(GoalModel).order_by(GoalModel.created_at.desc())

            if status:
                if isinstance(status, list):
                    query = query.where(
                        GoalModel.status.in_([s.value for s in status])
                    )
                else:
                    query = query.where(GoalModel.status == status.value)

            query = query.limit(limit).offset(offset)

            result = await session.execute(query)
            return list(result.scalars().all())

    async def list_recent(self, limit: int = 10) -> list[GoalModel]:
        """List most recent goals."""
        return await self.list_by_status(limit=limit)

    async def list_active(self) -> list[GoalModel]:
        """List all active (in progress or pending) goals."""
        return await self.list_by_status(
            status=[GoalStatus.PENDING, GoalStatus.IN_PROGRESS]
        )

    async def get_stats(self) -> dict[str, Any]:
        """Get goal statistics."""
        async with get_async_session() as session:
            from sqlalchemy import func

            # Count by status
            result = await session.execute(
                select(GoalModel.status, func.count(GoalModel.id))
                .group_by(GoalModel.status)
            )
            status_counts = {row[0]: row[1] for row in result.all()}

            # Total tokens and execution time
            result = await session.execute(
                select(
                    func.sum(GoalModel.tokens_used),
                    func.sum(GoalModel.execution_time_ms),
                    func.count(GoalModel.id),
                )
            )
            row = result.one()

            return {
                "by_status": status_counts,
                "total_goals": row[2] or 0,
                "total_tokens": row[0] or 0,
                "total_execution_time_ms": row[1] or 0,
            }


class TaskRepository:
    """Repository for Task persistence operations."""

    def __init__(self, session: AsyncSession | None = None):
        self._session = session
        self.logger = logger.bind(repository="task")

    async def create(self, task: Task, goal_id: str) -> TaskModel:
        """Create a new task."""
        async with get_async_session() as session:
            model = TaskModel(
                id=task.id,
                goal_id=goal_id,
                parent_task_id=task.parent_task_id,
                description=task.description,
                task_type=task.task_type,
                status=task.status.value,
                priority=task.priority,
                input_data=task.input_data,
                dependencies=list(task.dependencies),
                required_capabilities=list(task.required_capabilities),
                created_at=task.created_at,
            )
            session.add(model)
            await session.commit()
            await session.refresh(model)

            self.logger.debug("Task created", task_id=task.id, goal_id=goal_id)
            return model

    async def create_bulk(self, tasks: list[Task], goal_id: str) -> list[TaskModel]:
        """Create multiple tasks."""
        async with get_async_session() as session:
            models = []
            for i, task in enumerate(tasks):
                model = TaskModel(
                    id=task.id,
                    goal_id=goal_id,
                    parent_task_id=task.parent_task_id,
                    description=task.description,
                    task_type=task.task_type,
                    status=task.status.value,
                    priority=task.priority,
                    order=i,
                    input_data=task.input_data,
                    dependencies=list(task.dependencies),
                    required_capabilities=list(task.required_capabilities),
                    created_at=task.created_at,
                )
                models.append(model)
                session.add(model)

            await session.commit()
            for model in models:
                await session.refresh(model)

            self.logger.info("Tasks created", count=len(models), goal_id=goal_id)
            return models

    async def get(self, task_id: str) -> TaskModel | None:
        """Get a task by ID."""
        async with get_async_session() as session:
            result = await session.execute(
                select(TaskModel).where(TaskModel.id == task_id)
            )
            return result.scalar_one_or_none()

    async def update(self, task_id: str, updates: dict[str, Any]) -> bool:
        """Update a task."""
        async with get_async_session() as session:
            if "status" in updates and isinstance(updates["status"], TaskStatus):
                updates["status"] = updates["status"].value

            result = await session.execute(
                update(TaskModel)
                .where(TaskModel.id == task_id)
                .values(**updates)
            )
            await session.commit()
            return result.rowcount > 0

    async def update_status(
        self,
        task_id: str,
        status: TaskStatus,
        output: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> bool:
        """Update task status with output or error."""
        updates: dict[str, Any] = {"status": status.value}

        if status == TaskStatus.IN_PROGRESS:
            updates["started_at"] = datetime.utcnow()
        elif status in (TaskStatus.COMPLETED, TaskStatus.FAILED):
            updates["completed_at"] = datetime.utcnow()

        if output:
            updates["output_data"] = output
        if error:
            updates["error"] = error

        return await self.update(task_id, updates)

    async def assign_agent(
        self,
        task_id: str,
        agent_id: str,
        agent_type: str,
    ) -> bool:
        """Assign an agent to a task."""
        return await self.update(task_id, {
            "assigned_agent_id": agent_id,
            "assigned_agent_type": agent_type,
            "status": TaskStatus.ASSIGNED.value,
        })

    async def get_by_goal(
        self,
        goal_id: str,
        status: TaskStatus | None = None,
    ) -> list[TaskModel]:
        """Get all tasks for a goal."""
        async with get_async_session() as session:
            query = (
                select(TaskModel)
                .where(TaskModel.goal_id == goal_id)
                .order_by(TaskModel.order, TaskModel.created_at)
            )

            if status:
                query = query.where(TaskModel.status == status.value)

            result = await session.execute(query)
            return list(result.scalars().all())

    async def get_pending_tasks(self, goal_id: str) -> list[TaskModel]:
        """Get pending tasks that have their dependencies satisfied."""
        async with get_async_session() as session:
            # Get all tasks for the goal
            all_tasks = await self.get_by_goal(goal_id)

            # Find completed task IDs
            completed_ids = {
                t.id for t in all_tasks
                if t.status == TaskStatus.COMPLETED.value
            }

            # Filter pending tasks with satisfied dependencies
            pending = []
            for task in all_tasks:
                if task.status == TaskStatus.PENDING.value:
                    deps = set(task.dependencies or [])
                    if deps.issubset(completed_ids):
                        pending.append(task)

            return pending

    async def delete(self, task_id: str) -> bool:
        """Delete a task."""
        async with get_async_session() as session:
            result = await session.execute(
                delete(TaskModel).where(TaskModel.id == task_id)
            )
            await session.commit()
            return result.rowcount > 0


class AgentStateRepository:
    """Repository for agent state persistence."""

    def __init__(self, session: AsyncSession | None = None):
        self._session = session
        self.logger = logger.bind(repository="agent_state")

    async def save(self, agent_id: str, state: dict[str, Any]) -> AgentStateModel:
        """Save or update agent state."""
        async with get_async_session() as session:
            # Check if exists
            result = await session.execute(
                select(AgentStateModel).where(AgentStateModel.id == agent_id)
            )
            existing = result.scalar_one_or_none()

            if existing:
                # Update
                for key, value in state.items():
                    if hasattr(existing, key):
                        setattr(existing, key, value)
                existing.last_active_at = datetime.utcnow()
                await session.commit()
                return existing
            else:
                # Create
                model = AgentStateModel(
                    id=agent_id,
                    agent_type=state.get("agent_type", "unknown"),
                    name=state.get("name", ""),
                    provider_key=state.get("provider_key", ""),
                    model_name=state.get("model_name", ""),
                    **{k: v for k, v in state.items()
                       if k not in ("agent_type", "name", "provider_key", "model_name")}
                )
                session.add(model)
                await session.commit()
                await session.refresh(model)
                return model

    async def get(self, agent_id: str) -> AgentStateModel | None:
        """Get agent state by ID."""
        async with get_async_session() as session:
            result = await session.execute(
                select(AgentStateModel).where(AgentStateModel.id == agent_id)
            )
            return result.scalar_one_or_none()

    async def update_metrics(
        self,
        agent_id: str,
        tokens_used: int = 0,
        execution_time_ms: int = 0,
        task_completed: bool = False,
        success: bool = True,
    ) -> bool:
        """Update agent metrics after task execution."""
        async with get_async_session() as session:
            model = await self.get(agent_id)
            if not model:
                return False

            model.total_tokens_used += tokens_used
            model.total_execution_time_ms += execution_time_ms
            model.last_active_at = datetime.utcnow()

            if task_completed:
                model.total_tasks_completed += 1
                # Update success rate with exponential moving average
                alpha = 0.1
                model.success_rate = (
                    alpha * (1.0 if success else 0.0) +
                    (1 - alpha) * model.success_rate
                )

            await session.commit()
            return True

    async def list_active(self) -> list[AgentStateModel]:
        """List all active agents."""
        async with get_async_session() as session:
            result = await session.execute(
                select(AgentStateModel)
                .where(AgentStateModel.state != "stopped")
                .order_by(AgentStateModel.last_active_at.desc())
            )
            return list(result.scalars().all())

    async def delete(self, agent_id: str) -> bool:
        """Delete agent state."""
        async with get_async_session() as session:
            result = await session.execute(
                delete(AgentStateModel).where(AgentStateModel.id == agent_id)
            )
            await session.commit()
            return result.rowcount > 0
