"""
Swarm Agent - Swarm Coordination.

Responsible for:
- Coordinating parallel agent execution
- Search and data gathering at scale
- Brainstorming and diverse solution generation
"""

import asyncio
from dataclasses import dataclass, field
from typing import Any

import structlog

from src.agents.base import AgentConstraints, AgentState, AgentType, BaseAgent
from src.core.message import (
    AgentMessage,
    AgentResult,
    MessageType,
    Reflection,
    Task,
    utc_now,
)
from src.core.registry import AgentRegistry
from src.providers.base import LLMProvider

logger = structlog.get_logger()


SWARM_COORDINATOR_PROMPT = """You are a Swarm Coordinator in the Agent Village.

Your role is to coordinate parallel execution of multiple agents to accomplish tasks efficiently.

When coordinating a swarm:
1. Divide work into independent subtasks
2. Assign subtasks to worker agents
3. Monitor progress and handle failures
4. Aggregate results into a coherent output

Guidelines:
- Maximize parallelization where possible
- Balance load across workers
- Handle partial failures gracefully
- Provide clear progress updates

You coordinate, you don't execute directly."""


SWARM_WORKER_PROMPT = """You are a Swarm Worker in the Agent Village.

Your role is to execute assigned subtasks as part of a larger swarm operation.

When working:
1. Focus on your assigned subtask
2. Execute efficiently and thoroughly
3. Report results clearly
4. Indicate any issues or blockers

You are one of many workers. Do your part well."""


@dataclass
class SwarmTask:
    """A subtask in a swarm operation."""

    id: str
    description: str
    worker_id: str | None = None
    status: str = "pending"  # pending, running, completed, failed
    result: Any = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "description": self.description,
            "worker_id": self.worker_id,
            "status": self.status,
            "result": self.result,
            "error": self.error,
        }


@dataclass
class SwarmResult:
    """Result of a swarm operation."""

    subtasks: list[SwarmTask]
    aggregated_result: Any
    success_count: int
    failure_count: int
    total_tokens: int = 0
    total_time_seconds: float = 0.0

    @property
    def success_rate(self) -> float:
        total = self.success_count + self.failure_count
        return self.success_count / total if total > 0 else 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "subtasks": [t.to_dict() for t in self.subtasks],
            "aggregated_result": self.aggregated_result,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "success_rate": self.success_rate,
            "total_tokens": self.total_tokens,
            "total_time_seconds": self.total_time_seconds,
        }


class SwarmCoordinator(BaseAgent):
    """
    Swarm Coordinator for parallel agent execution.

    Manages a swarm of worker agents to accomplish tasks in parallel.
    """

    def __init__(
        self,
        provider: LLMProvider,
        registry: AgentRegistry,
        name: str | None = None,
        constraints: AgentConstraints | None = None,
        max_workers: int = 10,
    ):
        if constraints is None:
            constraints = AgentConstraints(
                max_tokens_per_request=4096,
                can_spawn_agents=True,
                can_access_memory=True,
                risk_tolerance="medium",
            )

        super().__init__(
            agent_type=AgentType.SWARM_COORDINATOR,
            provider=provider,
            name=name or "swarm_coordinator",
            constraints=constraints,
        )

        self.registry = registry
        self.max_workers = max_workers
        self._system_prompt = SWARM_COORDINATOR_PROMPT
        self._active_workers: dict[str, BaseAgent] = {}

    async def execute(self, message: AgentMessage) -> AgentResult:
        """Execute a swarm operation."""
        import time

        start_time = time.time()
        self.state = AgentState.BUSY

        try:
            task = message.task
            if not task:
                return self._create_result(
                    task_id=message.task_id or "",
                    success=False,
                    error="No task provided for swarm",
                )

            # Divide into subtasks
            subtasks = await self._divide_task(task, message.content)

            if not subtasks:
                return self._create_result(
                    task_id=task.id,
                    success=False,
                    error="Failed to divide task into subtasks",
                )

            # Execute subtasks in parallel
            swarm_result = await self._execute_swarm(subtasks, task)

            execution_time = time.time() - start_time
            swarm_result.total_time_seconds = execution_time

            self.metrics.tasks_completed += 1
            self.metrics.total_execution_time += execution_time
            self.state = AgentState.IDLE

            success = swarm_result.success_rate >= 0.5

            return self._create_result(
                task_id=task.id,
                success=success,
                result=swarm_result.to_dict(),
                confidence=swarm_result.success_rate,
                quality_score=swarm_result.success_rate,
                tokens_used=swarm_result.total_tokens,
                execution_time=execution_time,
            )

        except Exception as e:
            self.logger.error("Swarm execution failed", error=str(e))
            self.metrics.tasks_failed += 1
            self.state = AgentState.ERROR

            return self._create_result(
                task_id=message.task_id or "",
                success=False,
                error=str(e),
                execution_time=time.time() - start_time,
            )

        finally:
            # Cleanup workers
            await self._cleanup_workers()

    async def _divide_task(
        self, task: Task, context: dict[str, Any]
    ) -> list[SwarmTask]:
        """Divide a task into parallelizable subtasks."""
        import json
        from src.core.message import generate_id

        prompt = f"""Divide this task into independent subtasks that can be executed in parallel.

Task: {task.description}
Objective: {task.objective}
Context: {json.dumps(context) if context else 'None'}

Create 2-{self.max_workers} subtasks. Each subtask should be:
- Independent (no dependencies on other subtasks)
- Self-contained
- Roughly equal in complexity

Respond with JSON array:
[
    {{
        "description": "subtask description"
    }}
]"""

        response = await self._call_llm(prompt, temperature=0.3)

        try:
            subtasks_data = json.loads(response)
            return [
                SwarmTask(
                    id=generate_id(),
                    description=st.get("description", ""),
                )
                for st in subtasks_data
            ]
        except json.JSONDecodeError:
            self.logger.warning("Failed to parse subtasks", response=response[:200])
            # Fallback: single subtask
            return [
                SwarmTask(
                    id=generate_id(),
                    description=task.description,
                )
            ]

    async def _execute_swarm(
        self, subtasks: list[SwarmTask], parent_task: Task
    ) -> SwarmResult:
        """Execute subtasks using worker agents."""
        # Create workers
        workers = []
        for i, subtask in enumerate(subtasks[:self.max_workers]):
            try:
                worker = await self.registry.create_agent(
                    AgentType.SWARM_WORKER,
                    name=f"swarm_worker_{i}",
                )
                workers.append(worker)
                subtask.worker_id = worker.id
                self._active_workers[worker.id] = worker
            except Exception as e:
                self.logger.error("Failed to create worker", error=str(e))

        # Execute in parallel
        async def execute_subtask(subtask: SwarmTask, worker: BaseAgent) -> SwarmTask:
            subtask.status = "running"
            try:
                message = AgentMessage(
                    message_type=MessageType.TASK_ASSIGNED,
                    sender=self.id,
                    sender_type=self.agent_type.value,
                    recipient=worker.id,
                    recipient_type=worker.agent_type.value,
                    goal_id=parent_task.goal_id,
                    task=Task(
                        goal_id=parent_task.goal_id,
                        description=subtask.description,
                        objective=f"Complete: {subtask.description}",
                    ),
                )

                result = await worker.execute(message)

                if result.success:
                    subtask.status = "completed"
                    subtask.result = result.result
                else:
                    subtask.status = "failed"
                    subtask.error = result.error

            except Exception as e:
                subtask.status = "failed"
                subtask.error = str(e)

            return subtask

        # Run all subtasks
        tasks = [
            execute_subtask(subtask, worker)
            for subtask, worker in zip(subtasks, workers)
        ]

        completed_subtasks = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        success_count = 0
        failure_count = 0
        total_tokens = 0

        for subtask in completed_subtasks:
            if isinstance(subtask, Exception):
                failure_count += 1
            elif subtask.status == "completed":
                success_count += 1
            else:
                failure_count += 1

        # Aggregate results
        aggregated = await self._aggregate_results(
            [st for st in completed_subtasks if not isinstance(st, Exception)],
            parent_task,
        )

        return SwarmResult(
            subtasks=subtasks,
            aggregated_result=aggregated,
            success_count=success_count,
            failure_count=failure_count,
            total_tokens=total_tokens,
        )

    async def _aggregate_results(
        self, subtasks: list[SwarmTask], parent_task: Task
    ) -> Any:
        """Aggregate subtask results into final output."""
        import json

        results = [
            {"subtask": st.description, "result": st.result}
            for st in subtasks
            if st.status == "completed"
        ]

        prompt = f"""Aggregate these subtask results into a coherent final result.

Original Task: {parent_task.description}

Subtask Results:
{json.dumps(results, indent=2)}

Provide a unified summary that combines all subtask outputs."""

        response = await self._call_llm(prompt, temperature=0.3)
        return response

    async def _cleanup_workers(self) -> None:
        """Cleanup worker agents."""
        for worker_id in list(self._active_workers.keys()):
            try:
                await self.registry.unregister(worker_id)
            except Exception as e:
                self.logger.warning("Failed to cleanup worker", worker_id=worker_id, error=str(e))
        self._active_workers.clear()

    async def reflect(self, result: AgentResult) -> Reflection:
        """Reflect on swarm operation."""
        if not result.success:
            return Reflection(
                agent_id=self.id,
                task_id=result.task_id,
                performance_score=0.3,
                failures=[result.error or "Swarm operation failed"],
            )

        swarm_data = result.result or {}
        success_rate = swarm_data.get("success_rate", 0)

        return Reflection(
            agent_id=self.id,
            task_id=result.task_id,
            performance_score=success_rate,
            lessons_learned=[
                f"Swarm success rate: {success_rate:.1%}",
                f"Completed {swarm_data.get('success_count', 0)} subtasks",
            ],
            successes=["Parallel execution completed"] if success_rate > 0.5 else [],
            failures=[] if success_rate > 0.5 else ["Low swarm success rate"],
        )

    async def can_handle(self, task: Task) -> float:
        """Assess ability to handle task as swarm."""
        description_lower = task.description.lower()

        swarm_keywords = [
            "parallel", "multiple", "batch", "bulk", "many",
            "search", "gather", "collect", "survey", "scan",
        ]

        if any(kw in description_lower for kw in swarm_keywords):
            return 0.85

        return 0.3


class SwarmWorker(BaseAgent):
    """Simple worker agent for swarm operations."""

    def __init__(
        self,
        provider: LLMProvider,
        name: str | None = None,
    ):
        constraints = AgentConstraints(
            max_tokens_per_request=2048,
            can_spawn_agents=False,
            can_access_memory=False,
            risk_tolerance="low",
        )

        super().__init__(
            agent_type=AgentType.SWARM_WORKER,
            provider=provider,
            name=name or "swarm_worker",
            constraints=constraints,
        )

        self._system_prompt = SWARM_WORKER_PROMPT

    async def execute(self, message: AgentMessage) -> AgentResult:
        """Execute assigned subtask."""
        import time

        start_time = time.time()
        self.state = AgentState.BUSY

        try:
            task = message.task
            if not task:
                return self._create_result(
                    task_id=message.task_id or "",
                    success=False,
                    error="No task provided",
                )

            prompt = f"""Execute this subtask:

{task.description}

Provide a clear, concise result."""

            response = await self._call_llm(prompt, temperature=0.5)

            execution_time = time.time() - start_time
            self.state = AgentState.IDLE

            return self._create_result(
                task_id=task.id,
                success=True,
                result=response,
                confidence=0.7,
                quality_score=0.7,
                tokens_used=self.metrics.total_tokens_used,
                execution_time=execution_time,
            )

        except Exception as e:
            self.state = AgentState.ERROR
            return self._create_result(
                task_id=message.task_id or "",
                success=False,
                error=str(e),
                execution_time=time.time() - start_time,
            )

    async def reflect(self, result: AgentResult) -> Reflection:
        """Simple reflection for worker."""
        return Reflection(
            agent_id=self.id,
            task_id=result.task_id,
            performance_score=0.7 if result.success else 0.3,
            successes=["Subtask completed"] if result.success else [],
            failures=[] if result.success else [result.error or "Failed"],
        )
