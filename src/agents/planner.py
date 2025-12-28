"""
Planner Agent - The Planner Council.

Responsible for:
- Breaking goals into sub-goals
- Choosing execution strategies
- Designing task workflows
"""

import json
from dataclasses import dataclass, field
from typing import Any

import structlog

from src.agents.base import AgentConstraints, AgentState, AgentType, BaseAgent
from src.core.message import (
    AgentMessage,
    AgentResult,
    Constraints,
    Reflection,
    Task,
    utc_now,
)
from src.providers.base import LLMProvider

logger = structlog.get_logger()


PLANNER_SYSTEM_PROMPT = """You are a Planner agent in the Agent Village.

Your role is to decompose complex goals into actionable tasks and design execution strategies.

When planning, you should:
1. Understand the goal's core objective and success criteria
2. Identify required capabilities and resources
3. Break down into atomic, executable tasks
4. Consider dependencies between tasks
5. Estimate complexity and risk for each task
6. Suggest optimal execution order (sequential vs parallel)

For each task, specify:
- Clear description and objective
- Expected output format
- Required agent type (TOOL, CRITIC, MEMORY_KEEPER, etc.)
- Dependencies on other tasks
- Risk level (low, medium, high)
- Whether human approval is needed

Always respond with structured JSON for plans.
Prefer fewer, well-defined tasks over many small ones.
Consider efficiency - minimize unnecessary steps."""


@dataclass
class TaskPlan:
    """A planned task with metadata."""

    description: str
    objective: str
    expected_output: str
    agent_type: str
    dependencies: list[str] = field(default_factory=list)
    risk_level: str = "low"
    requires_approval: bool = False
    estimated_tokens: int = 1000
    parallel_group: int = 0  # Tasks in same group can run in parallel

    def to_dict(self) -> dict[str, Any]:
        return {
            "description": self.description,
            "objective": self.objective,
            "expected_output": self.expected_output,
            "agent_type": self.agent_type,
            "dependencies": self.dependencies,
            "risk_level": self.risk_level,
            "requires_approval": self.requires_approval,
            "estimated_tokens": self.estimated_tokens,
            "parallel_group": self.parallel_group,
        }


@dataclass
class ExecutionPlan:
    """Complete execution plan for a goal."""

    goal_description: str
    tasks: list[TaskPlan]
    execution_strategy: str  # sequential, parallel, mixed
    estimated_total_tokens: int
    estimated_agents: int
    risk_assessment: str
    requires_human_oversight: bool = False
    rationale: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "goal_description": self.goal_description,
            "tasks": [t.to_dict() for t in self.tasks],
            "execution_strategy": self.execution_strategy,
            "estimated_total_tokens": self.estimated_total_tokens,
            "estimated_agents": self.estimated_agents,
            "risk_assessment": self.risk_assessment,
            "requires_human_oversight": self.requires_human_oversight,
            "rationale": self.rationale,
        }


class PlannerAgent(BaseAgent):
    """
    Planner agent for task decomposition and strategy design.

    Part of the Planner Council that helps the Governor
    break down complex goals.
    """

    def __init__(
        self,
        provider: LLMProvider,
        name: str | None = None,
        constraints: AgentConstraints | None = None,
    ):
        if constraints is None:
            constraints = AgentConstraints(
                max_tokens_per_request=8192,
                can_spawn_agents=False,
                can_access_memory=True,
                risk_tolerance="medium",
            )

        super().__init__(
            agent_type=AgentType.PLANNER,
            provider=provider,
            name=name or "planner",
            constraints=constraints,
        )

        self._system_prompt = PLANNER_SYSTEM_PROMPT

    async def execute(self, message: AgentMessage) -> AgentResult:
        """Create an execution plan for a goal or task."""
        import time

        start_time = time.time()
        self.state = AgentState.BUSY

        try:
            task = message.task
            if not task:
                return self._create_result(
                    task_id=message.task_id or "",
                    success=False,
                    error="No task provided for planning",
                )

            # Create plan
            plan = await self._create_plan(task, message.content)

            execution_time = time.time() - start_time
            self.metrics.tasks_completed += 1
            self.metrics.total_execution_time += execution_time
            self.state = AgentState.IDLE

            return self._create_result(
                task_id=task.id,
                success=True,
                result=plan.to_dict(),
                confidence=0.85,
                quality_score=0.85,
                tokens_used=self.metrics.total_tokens_used,
                execution_time=execution_time,
            )

        except Exception as e:
            self.logger.error("Planning failed", error=str(e))
            self.metrics.tasks_failed += 1
            self.state = AgentState.ERROR

            return self._create_result(
                task_id=message.task_id or "",
                success=False,
                error=str(e),
                execution_time=time.time() - start_time,
            )

    async def _create_plan(
        self, task: Task, context: dict[str, Any]
    ) -> ExecutionPlan:
        """Create an execution plan for a task."""
        planning_prompt = f"""Create an execution plan for this goal:

Goal: {task.description}
Objective: {task.objective}
Expected Output: {task.expected_output}

Additional Context:
{json.dumps(context, indent=2) if context else 'None'}

Constraints:
- Max tokens: {task.constraints.max_tokens}
- Risk level allowed: {task.constraints.risk_level}
- Requires approval: {task.constraints.requires_approval}

Provide a detailed execution plan as JSON:
{{
    "tasks": [
        {{
            "description": "what needs to be done",
            "objective": "what this achieves",
            "expected_output": "expected result format",
            "agent_type": "TOOL|CRITIC|MEMORY_KEEPER",
            "dependencies": [],
            "risk_level": "low|medium|high",
            "requires_approval": false,
            "estimated_tokens": 1000,
            "parallel_group": 0
        }}
    ],
    "execution_strategy": "sequential|parallel|mixed",
    "risk_assessment": "overall risk analysis",
    "requires_human_oversight": false,
    "rationale": "why this plan is optimal"
}}

Guidelines:
- Prefer TOOL agents for actions, CRITIC for validation
- Group independent tasks with same parallel_group
- Keep tasks atomic and well-defined
- Minimize number of tasks while maintaining clarity"""

        response = await self._call_llm(planning_prompt, temperature=0.3)

        try:
            plan_data = json.loads(response)

            tasks = [
                TaskPlan(
                    description=t.get("description", ""),
                    objective=t.get("objective", ""),
                    expected_output=t.get("expected_output", ""),
                    agent_type=t.get("agent_type", "TOOL"),
                    dependencies=t.get("dependencies", []),
                    risk_level=t.get("risk_level", "low"),
                    requires_approval=t.get("requires_approval", False),
                    estimated_tokens=t.get("estimated_tokens", 1000),
                    parallel_group=t.get("parallel_group", 0),
                )
                for t in plan_data.get("tasks", [])
            ]

            return ExecutionPlan(
                goal_description=task.description,
                tasks=tasks,
                execution_strategy=plan_data.get("execution_strategy", "sequential"),
                estimated_total_tokens=sum(t.estimated_tokens for t in tasks),
                estimated_agents=len(set(t.agent_type for t in tasks)),
                risk_assessment=plan_data.get("risk_assessment", "low"),
                requires_human_oversight=plan_data.get("requires_human_oversight", False),
                rationale=plan_data.get("rationale", ""),
            )

        except json.JSONDecodeError:
            self.logger.warning("Failed to parse plan JSON", response=response[:200])
            # Create fallback single-task plan
            return ExecutionPlan(
                goal_description=task.description,
                tasks=[
                    TaskPlan(
                        description=task.description,
                        objective=task.objective,
                        expected_output=task.expected_output,
                        agent_type="TOOL",
                    )
                ],
                execution_strategy="sequential",
                estimated_total_tokens=2000,
                estimated_agents=1,
                risk_assessment="unknown - fallback plan",
                rationale="Fallback plan due to parsing error",
            )

    async def reflect(self, result: AgentResult) -> Reflection:
        """Reflect on planning quality."""
        if not result.success:
            return Reflection(
                agent_id=self.id,
                task_id=result.task_id,
                performance_score=0.2,
                failures=[result.error or "Planning failed"],
            )

        plan = result.result
        task_count = len(plan.get("tasks", []))
        strategy = plan.get("execution_strategy", "sequential")

        return Reflection(
            agent_id=self.id,
            task_id=result.task_id,
            performance_score=result.quality_score,
            lessons_learned=[
                f"Created plan with {task_count} tasks using {strategy} strategy",
            ],
            successes=["Plan created successfully"],
            recommendations=[
                "Consider parallelization opportunities",
                "Validate risk assessments against actual execution",
            ],
        )

    async def can_handle(self, task: Task) -> float:
        """Assess ability to handle planning task."""
        description_lower = task.description.lower()

        # High confidence for planning-related tasks
        planning_keywords = ["plan", "design", "strategy", "decompose", "break down", "organize"]
        if any(kw in description_lower for kw in planning_keywords):
            return 0.9

        # Medium confidence for complex tasks that might need planning
        complexity_indicators = ["multiple", "complex", "steps", "workflow", "process"]
        if any(ind in description_lower for ind in complexity_indicators):
            return 0.7

        return 0.3
