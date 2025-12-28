"""
Governor - The Meta-Agent for Agent Village.

The Governor is the supreme orchestrator that:
- Receives goals
- Analyzes intent
- Spawns and assigns agents
- Enforces limits
- Decides when to stop
"""

import asyncio
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

import structlog

from src.agents.base import AgentConstraints, AgentState, AgentType, BaseAgent
from src.core.fsm import ExecutionFSM, ExecutionState, FSMContext, create_execution_fsm
from src.core.message import (
    AgentMessage,
    AgentResult,
    Constraints,
    Goal,
    GoalContext,
    GoalStatus,
    MessageType,
    Priority,
    Reflection,
    Task,
    TaskStatus,
    generate_id,
    utc_now,
)
from src.core.registry import AgentRegistry
from src.core.safety import SafetyGate, get_safety_gate
from src.providers.base import LLMProvider, Message, MessageRole, ToolCall, ToolDefinition

logger = structlog.get_logger()


class TaskComplexity(str, Enum):
    """Complexity levels for tasks."""

    TRIVIAL = "trivial"  # Single agent, no memory
    SIMPLE = "simple"  # Single agent, with memory
    MODERATE = "moderate"  # Council planning, sequential execution
    COMPLEX = "complex"  # Council + parallel execution
    STRATEGIC = "strategic"  # Full market-based coordination


class ExecutionPattern(str, Enum):
    """Patterns for task execution."""

    SINGLE_AGENT = "single_agent"
    COUNCIL = "council"
    SWARM = "swarm"
    MARKET = "market"


GOVERNOR_SYSTEM_PROMPT = """You are the Governor, the supreme orchestrator of the Agent Village.

Your responsibilities:
1. Analyze incoming goals to understand intent and requirements
2. Assess task complexity and select appropriate execution patterns
3. Decompose goals into tasks and assign them to specialized agents
4. Monitor execution and make decisions about replanning or escalation
5. Enforce safety limits and ensure goal completion

When analyzing a goal, consider:
- What is the core objective?
- What capabilities are required (reasoning, tool use, memory, etc.)?
- What is the complexity level?
- Are there safety concerns or human approval requirements?
- What execution pattern is most appropriate?

Available agent types:
- PLANNER: Task decomposition and strategic planning
- TOOL: Executing actions, API calls, code execution
- CRITIC: Validating outputs and detecting issues
- MEMORY_KEEPER: Managing long-term memory
- SWARM_COORDINATOR: Coordinating parallel agents
- EVOLVER: Optimizing prompts and workflows

You must make decisions that are:
- Safe: Never exceed resource limits or bypass safety checks
- Efficient: Minimize token usage and agent spawns
- Effective: Achieve goals with high quality results

Always respond with structured JSON when making decisions."""


@dataclass
class GovernorDecision:
    """A decision made by the Governor."""

    decision_type: str  # complexity_assessment, pattern_selection, task_assignment, etc.
    rationale: str
    result: Any
    confidence: float = 0.0
    timestamp: datetime = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision_type": self.decision_type,
            "rationale": self.rationale,
            "result": self.result,
            "confidence": self.confidence,
            "timestamp": self.timestamp.isoformat(),
        }


class Governor(BaseAgent):
    """
    The Governor meta-agent.

    Orchestrates all other agents and manages goal execution.
    """

    def __init__(
        self,
        provider: LLMProvider,
        registry: AgentRegistry,
        safety_gate: SafetyGate | None = None,
    ):
        constraints = AgentConstraints(
            max_tokens_per_request=8192,
            can_spawn_agents=True,
            can_access_memory=True,
            risk_tolerance="high",
        )

        super().__init__(
            agent_type=AgentType.GOVERNOR,
            provider=provider,
            name="governor",
            constraints=constraints,
        )

        self.registry = registry
        self.safety_gate = safety_gate or get_safety_gate()
        self.fsm = create_execution_fsm(self.safety_gate)

        self._system_prompt = GOVERNOR_SYSTEM_PROMPT
        self._active_goals: dict[str, GoalContext] = {}
        self._decisions: list[GovernorDecision] = []

        # Register FSM state handlers
        self._register_fsm_handlers()

    def _register_fsm_handlers(self) -> None:
        """Register handlers for FSM states."""
        self.fsm.register_state_handler(
            ExecutionState.INTENT_ANALYSIS, self._handle_intent_analysis
        )
        self.fsm.register_state_handler(
            ExecutionState.TASK_DECOMPOSITION, self._handle_task_decomposition
        )
        self.fsm.register_state_handler(
            ExecutionState.AGENT_ASSIGNMENT, self._handle_agent_assignment
        )
        self.fsm.register_state_handler(
            ExecutionState.EXECUTING, self._handle_execution
        )
        self.fsm.register_state_handler(
            ExecutionState.PARALLEL_EXECUTING, self._handle_parallel_execution
        )
        self.fsm.register_state_handler(
            ExecutionState.VERIFYING, self._handle_verification
        )
        self.fsm.register_state_handler(
            ExecutionState.WRITING_MEMORY, self._handle_memory_write
        )
        self.fsm.register_state_handler(
            ExecutionState.REFLECTING, self._handle_reflection
        )

    async def execute(self, message: AgentMessage) -> AgentResult:
        """
        Execute a goal received via message.

        The Governor doesn't execute tasks directly - it orchestrates
        other agents to achieve the goal.
        """
        import time

        start_time = time.time()
        self.state = AgentState.BUSY

        try:
            # Extract or create goal
            if message.task:
                goal = Goal(
                    description=message.task.description,
                    context=message.content,
                    constraints=message.constraints,
                )
            else:
                goal = Goal(
                    description=message.content.get("description", ""),
                    context=message.content,
                )

            # Execute through FSM
            goal = await self.fsm.execute(goal)

            execution_time = time.time() - start_time
            self.state = AgentState.IDLE

            return self._create_result(
                task_id=message.task_id or goal.id,
                success=goal.status == GoalStatus.COMPLETED,
                result=goal.to_dict(),
                error=goal.error,
                confidence=0.9 if goal.status == GoalStatus.COMPLETED else 0.3,
                quality_score=0.9 if goal.status == GoalStatus.COMPLETED else 0.3,
                tokens_used=goal.total_tokens_used,
                execution_time=execution_time,
            )

        except Exception as e:
            self.logger.exception("Goal execution failed", error=str(e))
            self.state = AgentState.ERROR

            return self._create_result(
                task_id=message.task_id or "",
                success=False,
                error=str(e),
                execution_time=time.time() - start_time,
            )

    async def reflect(self, result: AgentResult) -> Reflection:
        """Reflect on goal execution."""
        return Reflection(
            agent_id=self.id,
            task_id=result.task_id,
            performance_score=result.quality_score,
            lessons_learned=[
                f"Goal completed with {'success' if result.success else 'failure'}",
                f"Used {result.tokens_used} tokens in {result.execution_time_seconds:.2f}s",
            ],
            successes=["Goal orchestrated successfully"] if result.success else [],
            failures=[] if result.success else [result.error or "Unknown failure"],
        )

    # FSM State Handlers

    async def _handle_intent_analysis(self, context: FSMContext) -> ExecutionState:
        """Analyze the intent of the goal."""
        goal = context.goal_context.goal
        self.logger.info("Analyzing goal intent", goal_id=goal.id)

        # Use LLM to analyze intent
        analysis_prompt = f"""Analyze this goal and determine:
1. The core objective
2. Required capabilities
3. Potential risks or concerns
4. Suggested approach

Goal: {goal.description}

Context: {json.dumps(goal.context, indent=2) if goal.context else 'None'}

Respond with a JSON object containing:
{{
    "objective": "clear statement of what needs to be achieved",
    "capabilities_needed": ["list", "of", "capabilities"],
    "complexity": "trivial|simple|moderate|complex|strategic",
    "risks": ["list", "of", "risks"],
    "approach": "recommended execution approach",
    "requires_human_approval": true/false,
    "approval_reason": "reason if approval needed"
}}"""

        response = await self._call_llm(analysis_prompt, temperature=0.3)

        try:
            analysis = json.loads(response)
            context.data["intent_analysis"] = analysis

            # Record decision
            self._decisions.append(
                GovernorDecision(
                    decision_type="intent_analysis",
                    rationale=analysis.get("approach", ""),
                    result=analysis,
                    confidence=0.8,
                )
            )

            # Update goal metadata
            goal.metadata["intent_analysis"] = analysis
            goal.metadata["complexity"] = analysis.get("complexity", "moderate")

        except json.JSONDecodeError:
            self.logger.warning("Failed to parse intent analysis", response=response[:200])
            context.data["intent_analysis"] = {"complexity": "moderate"}

        return ExecutionState.TASK_DECOMPOSITION

    async def _handle_task_decomposition(self, context: FSMContext) -> ExecutionState:
        """Decompose the goal into tasks."""
        goal = context.goal_context.goal
        analysis = context.data.get("intent_analysis", {})
        complexity = analysis.get("complexity", "moderate")

        self.logger.info(
            "Decomposing goal into tasks",
            goal_id=goal.id,
            complexity=complexity,
        )

        decomposition_prompt = f"""Decompose this goal into executable tasks.

Goal: {goal.description}
Complexity: {complexity}
Analysis: {json.dumps(analysis, indent=2)}

Create a list of tasks that can be executed by specialized agents.
Each task should be:
- Atomic and well-defined
- Assignable to a single agent type
- Have clear success criteria

Respond with a JSON array of tasks:
[
    {{
        "description": "task description",
        "objective": "what this task achieves",
        "expected_output": "what output to expect",
        "agent_type": "PLANNER|TOOL|CRITIC|MEMORY_KEEPER",
        "dependencies": ["task_ids this depends on"],
        "risk_level": "low|medium|high",
        "requires_approval": false
    }}
]

Keep tasks focused and minimal. Prefer fewer, well-defined tasks over many small ones."""

        response = await self._call_llm(decomposition_prompt, temperature=0.3)

        try:
            tasks_data = json.loads(response)

            for task_data in tasks_data:
                task = Task(
                    goal_id=goal.id,
                    description=task_data.get("description", ""),
                    objective=task_data.get("objective", ""),
                    expected_output=task_data.get("expected_output", ""),
                    constraints=Constraints(
                        risk_level=task_data.get("risk_level", "low"),
                        requires_approval=task_data.get("requires_approval", False),
                    ),
                )
                task.assigned_agent_type = task_data.get("agent_type", "TOOL")
                goal.tasks.append(task)

            self.logger.info(
                "Tasks created",
                goal_id=goal.id,
                task_count=len(goal.tasks),
            )

            self._decisions.append(
                GovernorDecision(
                    decision_type="task_decomposition",
                    rationale=f"Created {len(goal.tasks)} tasks for complexity {complexity}",
                    result=[t.to_dict() for t in goal.tasks],
                    confidence=0.8,
                )
            )

        except json.JSONDecodeError:
            self.logger.warning("Failed to parse task decomposition", response=response[:200])
            # Create a single task as fallback
            goal.tasks.append(
                Task(
                    goal_id=goal.id,
                    description=goal.description,
                    objective="Achieve the goal",
                    assigned_agent_type="TOOL",
                )
            )

        return ExecutionState.AGENT_ASSIGNMENT

    async def _handle_agent_assignment(self, context: FSMContext) -> ExecutionState:
        """Assign agents to tasks."""
        goal = context.goal_context.goal

        self.logger.info(
            "Assigning agents to tasks",
            goal_id=goal.id,
            task_count=len(goal.tasks),
        )

        for task in goal.tasks:
            if task.assigned_agent_type:
                # Find or create appropriate agent
                agent_type = AgentType(task.assigned_agent_type.lower())

                # Try to find existing available agent
                agent = await self.registry.find_best_agent(
                    agent_type, task.description
                )

                if agent is None:
                    # Create new agent
                    try:
                        agent = await self.registry.create_agent(agent_type)
                    except Exception as e:
                        self.logger.error(
                            "Failed to create agent",
                            agent_type=agent_type.value,
                            error=str(e),
                        )
                        continue

                task.assigned_agent_id = agent.id
                task.status = TaskStatus.ASSIGNED
                context.goal_context.agents_spawned += 1

                self.logger.debug(
                    "Agent assigned to task",
                    task_id=task.id,
                    agent_id=agent.id,
                    agent_type=agent_type.value,
                )

        # Decide execution pattern
        if len(goal.tasks) == 1:
            return ExecutionState.EXECUTING
        else:
            return ExecutionState.PARALLEL_EXECUTING

    async def _handle_execution(self, context: FSMContext) -> ExecutionState:
        """Execute a single task."""
        goal = context.goal_context.goal
        task = goal.tasks[0] if goal.tasks else None

        if not task:
            return ExecutionState.FAILED

        self.logger.info("Executing task", task_id=task.id)

        result = await self._execute_task(task, context.goal_context)

        if result.success:
            task.status = TaskStatus.COMPLETED
            task.result = result.result
        else:
            task.status = TaskStatus.FAILED
            task.error = result.error

        context.goal_context.tokens_used += result.tokens_used

        return ExecutionState.VERIFYING

    async def _handle_parallel_execution(self, context: FSMContext) -> ExecutionState:
        """Execute multiple tasks in parallel."""
        goal = context.goal_context.goal

        self.logger.info(
            "Executing tasks in parallel",
            goal_id=goal.id,
            task_count=len(goal.tasks),
        )

        # Group tasks by dependencies
        ready_tasks = [t for t in goal.tasks if not t.dependencies]

        # Execute ready tasks in parallel
        tasks_to_run = []
        for task in ready_tasks:
            tasks_to_run.append(self._execute_task(task, context.goal_context))

        results = await asyncio.gather(*tasks_to_run, return_exceptions=True)

        # Process results
        for task, result in zip(ready_tasks, results):
            if isinstance(result, Exception):
                task.status = TaskStatus.FAILED
                task.error = str(result)
            elif result.success:
                task.status = TaskStatus.COMPLETED
                task.result = result.result
                context.goal_context.tokens_used += result.tokens_used
            else:
                task.status = TaskStatus.FAILED
                task.error = result.error

        return ExecutionState.VERIFYING

    async def _execute_task(self, task: Task, goal_context: GoalContext) -> AgentResult:
        """Execute a single task using the assigned agent."""
        agent = self.registry.get(task.assigned_agent_id) if task.assigned_agent_id else None

        if not agent:
            return AgentResult(
                task_id=task.id,
                agent_id="",
                agent_type="",
                success=False,
                error="No agent assigned to task",
            )

        # Create message for agent
        message = AgentMessage(
            message_type=MessageType.TASK_ASSIGNED,
            sender=self.id,
            sender_type=self.agent_type.value,
            recipient=agent.id,
            recipient_type=agent.agent_type.value,
            goal_id=goal_context.goal.id,
            task_id=task.id,
            task=task,
            content={"context": goal_context.goal.context},
            constraints=task.constraints,
        )

        task.status = TaskStatus.IN_PROGRESS
        task.started_at = utc_now()

        try:
            result = await agent.execute(message)
            task.completed_at = utc_now()
            return result

        except Exception as e:
            self.logger.error(
                "Task execution failed",
                task_id=task.id,
                agent_id=agent.id,
                error=str(e),
            )
            return AgentResult(
                task_id=task.id,
                agent_id=agent.id,
                agent_type=agent.agent_type.value,
                success=False,
                error=str(e),
            )

    async def _handle_verification(self, context: FSMContext) -> ExecutionState:
        """Verify task results."""
        goal = context.goal_context.goal

        all_completed = all(t.status == TaskStatus.COMPLETED for t in goal.tasks)
        any_failed = any(t.status == TaskStatus.FAILED for t in goal.tasks)

        self.logger.info(
            "Verifying task results",
            goal_id=goal.id,
            all_completed=all_completed,
            any_failed=any_failed,
        )

        if all_completed:
            return ExecutionState.WRITING_MEMORY
        elif any_failed:
            # Check if we should replan
            replan_count = goal.metadata.get("replan_count", 0)
            if replan_count < 3:
                goal.metadata["replan_count"] = replan_count + 1
                return ExecutionState.REPLANNING
            else:
                return ExecutionState.FAILED
        else:
            # Some tasks still pending - continue execution
            return ExecutionState.EXECUTING

    async def _handle_memory_write(self, context: FSMContext) -> ExecutionState:
        """Write results to memory."""
        goal = context.goal_context.goal

        self.logger.info("Writing to memory", goal_id=goal.id)

        # Collect all results
        results = [
            {
                "task_id": task.id,
                "description": task.description,
                "result": task.result,
                "status": task.status.value,
            }
            for task in goal.tasks
        ]

        goal.result = results
        goal.metadata["memory_written"] = True

        return ExecutionState.REFLECTING

    async def _handle_reflection(self, context: FSMContext) -> ExecutionState:
        """Reflect on goal execution."""
        goal = context.goal_context.goal

        self.logger.info("Reflecting on execution", goal_id=goal.id)

        reflection_prompt = f"""Reflect on this goal execution:

Goal: {goal.description}
Status: {goal.status.value}
Tasks completed: {sum(1 for t in goal.tasks if t.status == TaskStatus.COMPLETED)}/{len(goal.tasks)}
Total tokens used: {context.goal_context.tokens_used}

Provide a brief assessment of:
1. What went well
2. What could be improved
3. Key lessons for future similar goals

Keep response concise."""

        response = await self._call_llm(reflection_prompt, temperature=0.5)
        goal.metadata["reflection"] = response

        return ExecutionState.COMPLETED

    async def assess_complexity(self, goal: Goal) -> TaskComplexity:
        """Assess the complexity of a goal."""
        analysis = goal.metadata.get("intent_analysis", {})
        return TaskComplexity(analysis.get("complexity", "moderate"))

    async def select_pattern(self, complexity: TaskComplexity) -> ExecutionPattern:
        """Select execution pattern based on complexity."""
        pattern_map = {
            TaskComplexity.TRIVIAL: ExecutionPattern.SINGLE_AGENT,
            TaskComplexity.SIMPLE: ExecutionPattern.SINGLE_AGENT,
            TaskComplexity.MODERATE: ExecutionPattern.COUNCIL,
            TaskComplexity.COMPLEX: ExecutionPattern.SWARM,
            TaskComplexity.STRATEGIC: ExecutionPattern.MARKET,
        }
        return pattern_map.get(complexity, ExecutionPattern.COUNCIL)

    def get_decisions(self) -> list[dict[str, Any]]:
        """Get all decisions made by the Governor."""
        return [d.to_dict() for d in self._decisions]


async def create_governor(
    provider: LLMProvider,
    registry: AgentRegistry,
    safety_gate: SafetyGate | None = None,
) -> Governor:
    """Create and initialize a Governor."""
    governor = Governor(provider, registry, safety_gate)
    await governor.initialize()
    await registry.register(governor)
    return governor
