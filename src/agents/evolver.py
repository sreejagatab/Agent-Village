"""
Evolver Agent - Self-improvement.

Responsible for:
- Improving prompts
- Optimizing workflows
- Learning from experience
- Retiring ineffective patterns
"""

import json
from dataclasses import dataclass, field
from typing import Any

import structlog

from src.agents.base import AgentConstraints, AgentState, AgentType, BaseAgent
from src.core.message import (
    AgentMessage,
    AgentResult,
    Reflection,
    Task,
)
from src.memory.strategic import StrategicMemory
from src.providers.base import LLMProvider

logger = structlog.get_logger()


EVOLVER_SYSTEM_PROMPT = """You are an Evolver agent in the Agent Village.

Your role is to improve the system by:
1. Analyzing patterns of success and failure
2. Optimizing prompts and workflows
3. Identifying ineffective strategies to retire
4. Proposing improvements based on experience

When evolving:
- Use data-driven decisions based on past performance
- Make incremental improvements (avoid dramatic changes)
- Consider tradeoffs (speed vs quality, cost vs capability)
- Document rationale for all changes

You are the system's path to continuous improvement."""


@dataclass
class PromptOptimization:
    """A suggested prompt optimization."""

    agent_type: str
    original_prompt: str
    optimized_prompt: str
    rationale: str
    expected_improvement: float  # 0-1
    confidence: float  # 0-1

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_type": self.agent_type,
            "original_prompt": self.original_prompt[:200] + "...",
            "optimized_prompt": self.optimized_prompt[:200] + "...",
            "rationale": self.rationale,
            "expected_improvement": self.expected_improvement,
            "confidence": self.confidence,
        }


@dataclass
class WorkflowOptimization:
    """A suggested workflow optimization."""

    workflow_name: str
    current_steps: list[str]
    optimized_steps: list[str]
    rationale: str
    expected_speedup: float  # multiplier
    expected_quality_change: float  # -1 to 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "workflow_name": self.workflow_name,
            "current_steps": self.current_steps,
            "optimized_steps": self.optimized_steps,
            "rationale": self.rationale,
            "expected_speedup": self.expected_speedup,
            "expected_quality_change": self.expected_quality_change,
        }


@dataclass
class EvolutionReport:
    """Report of evolution analysis."""

    prompt_optimizations: list[PromptOptimization] = field(default_factory=list)
    workflow_optimizations: list[WorkflowOptimization] = field(default_factory=list)
    patterns_to_retire: list[str] = field(default_factory=list)
    lessons_learned: list[str] = field(default_factory=list)
    overall_health_score: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "prompt_optimizations": [p.to_dict() for p in self.prompt_optimizations],
            "workflow_optimizations": [w.to_dict() for w in self.workflow_optimizations],
            "patterns_to_retire": self.patterns_to_retire,
            "lessons_learned": self.lessons_learned,
            "overall_health_score": self.overall_health_score,
        }


class EvolverAgent(BaseAgent):
    """
    Evolver agent for system self-improvement.

    Analyzes performance and suggests optimizations.
    """

    def __init__(
        self,
        provider: LLMProvider,
        strategic_memory: StrategicMemory | None = None,
        name: str | None = None,
        constraints: AgentConstraints | None = None,
    ):
        if constraints is None:
            constraints = AgentConstraints(
                max_tokens_per_request=8192,
                can_spawn_agents=False,
                can_access_memory=True,
                risk_tolerance="low",
            )

        super().__init__(
            agent_type=AgentType.EVOLVER,
            provider=provider,
            name=name or "evolver",
            constraints=constraints,
        )

        self.strategic_memory = strategic_memory
        self._system_prompt = EVOLVER_SYSTEM_PROMPT

    async def execute(self, message: AgentMessage) -> AgentResult:
        """Analyze and suggest improvements."""
        import time

        start_time = time.time()
        self.state = AgentState.BUSY

        try:
            task = message.task
            if not task:
                return self._create_result(
                    task_id=message.task_id or "",
                    success=False,
                    error="No task provided for evolution",
                )

            # Get evolution context
            context = message.content
            evolution_type = context.get("type", "full")

            if evolution_type == "prompt":
                report = await self._optimize_prompts(context)
            elif evolution_type == "workflow":
                report = await self._optimize_workflows(context)
            else:
                report = await self._full_evolution_analysis(context)

            execution_time = time.time() - start_time
            self.metrics.tasks_completed += 1
            self.state = AgentState.IDLE

            return self._create_result(
                task_id=task.id,
                success=True,
                result=report.to_dict(),
                confidence=0.75,
                quality_score=0.75,
                tokens_used=self.metrics.total_tokens_used,
                execution_time=execution_time,
            )

        except Exception as e:
            self.logger.error("Evolution failed", error=str(e))
            self.metrics.tasks_failed += 1
            self.state = AgentState.ERROR

            return self._create_result(
                task_id=message.task_id or "",
                success=False,
                error=str(e),
                execution_time=time.time() - start_time,
            )

    async def _optimize_prompts(self, context: dict[str, Any]) -> EvolutionReport:
        """Analyze and optimize agent prompts."""
        agent_type = context.get("agent_type", "unknown")
        current_prompt = context.get("current_prompt", "")
        performance_data = context.get("performance_data", {})

        prompt = f"""Analyze this agent prompt and suggest improvements.

Agent Type: {agent_type}
Current Prompt:
{current_prompt}

Performance Data:
{json.dumps(performance_data, indent=2)}

Consider:
1. Clarity and specificity
2. Task alignment
3. Output format guidance
4. Error handling instructions
5. Efficiency (token usage)

Respond with JSON:
{{
    "optimized_prompt": "your improved prompt",
    "changes": ["list of specific changes made"],
    "rationale": "why these changes should improve performance",
    "expected_improvement": 0.1,  // 0-1 scale
    "confidence": 0.7  // 0-1 scale
}}"""

        response = await self._call_llm(prompt, temperature=0.4)

        try:
            data = json.loads(response)
            optimization = PromptOptimization(
                agent_type=agent_type,
                original_prompt=current_prompt,
                optimized_prompt=data.get("optimized_prompt", current_prompt),
                rationale=data.get("rationale", ""),
                expected_improvement=data.get("expected_improvement", 0.0),
                confidence=data.get("confidence", 0.5),
            )

            return EvolutionReport(
                prompt_optimizations=[optimization],
                lessons_learned=data.get("changes", []),
            )

        except json.JSONDecodeError:
            self.logger.warning("Failed to parse optimization", response=response[:200])
            return EvolutionReport()

    async def _optimize_workflows(self, context: dict[str, Any]) -> EvolutionReport:
        """Analyze and optimize workflows."""
        workflow_name = context.get("workflow_name", "unknown")
        current_steps = context.get("steps", [])
        execution_data = context.get("execution_data", {})

        prompt = f"""Analyze this workflow and suggest improvements.

Workflow: {workflow_name}
Current Steps: {json.dumps(current_steps, indent=2)}

Execution Data:
{json.dumps(execution_data, indent=2)}

Consider:
1. Unnecessary steps that can be removed
2. Steps that can be parallelized
3. Bottlenecks that slow execution
4. Error-prone steps that need hardening
5. Missing validation or checkpoints

Respond with JSON:
{{
    "optimized_steps": ["list of improved steps"],
    "removed_steps": ["steps removed and why"],
    "parallelization": ["steps that can run in parallel"],
    "rationale": "overall improvement rationale",
    "expected_speedup": 1.2,  // multiplier
    "expected_quality_change": 0.1  // -1 to 1
}}"""

        response = await self._call_llm(prompt, temperature=0.4)

        try:
            data = json.loads(response)
            optimization = WorkflowOptimization(
                workflow_name=workflow_name,
                current_steps=current_steps,
                optimized_steps=data.get("optimized_steps", current_steps),
                rationale=data.get("rationale", ""),
                expected_speedup=data.get("expected_speedup", 1.0),
                expected_quality_change=data.get("expected_quality_change", 0.0),
            )

            return EvolutionReport(
                workflow_optimizations=[optimization],
                patterns_to_retire=data.get("removed_steps", []),
            )

        except json.JSONDecodeError:
            return EvolutionReport()

    async def _full_evolution_analysis(self, context: dict[str, Any]) -> EvolutionReport:
        """Perform full system evolution analysis."""
        # Get lessons from strategic memory
        lessons = []
        if self.strategic_memory:
            lessons = await self.strategic_memory.get_lessons_learned(limit=20)

        historical_data = context.get("historical_data", {})
        current_metrics = context.get("current_metrics", {})

        prompt = f"""Perform a comprehensive evolution analysis of the agent system.

Historical Performance:
{json.dumps(historical_data, indent=2)}

Current Metrics:
{json.dumps(current_metrics, indent=2)}

Lessons from Past Decisions:
{json.dumps(lessons, indent=2) if lessons else "No lessons recorded yet"}

Analyze and provide:
1. Patterns that are working well
2. Patterns that should be retired
3. Prompt improvements needed
4. Workflow improvements needed
5. Overall system health assessment

Respond with JSON:
{{
    "successful_patterns": ["patterns working well"],
    "patterns_to_retire": ["ineffective patterns to stop using"],
    "prompt_improvements": [
        {{
            "agent_type": "type",
            "improvement": "what to change",
            "rationale": "why"
        }}
    ],
    "workflow_improvements": [
        {{
            "workflow": "name",
            "improvement": "what to change",
            "rationale": "why"
        }}
    ],
    "lessons_learned": ["key insights from analysis"],
    "health_score": 0.75,  // 0-1 overall health
    "recommendations": ["prioritized action items"]
}}"""

        response = await self._call_llm(prompt, temperature=0.3)

        try:
            data = json.loads(response)

            return EvolutionReport(
                patterns_to_retire=data.get("patterns_to_retire", []),
                lessons_learned=data.get("lessons_learned", []) + data.get("recommendations", []),
                overall_health_score=data.get("health_score", 0.5),
            )

        except json.JSONDecodeError:
            return EvolutionReport(
                lessons_learned=["Analysis parsing failed - manual review recommended"],
                overall_health_score=0.5,
            )

    async def reflect(self, result: AgentResult) -> Reflection:
        """Reflect on evolution analysis."""
        if not result.success:
            return Reflection(
                agent_id=self.id,
                task_id=result.task_id,
                performance_score=0.3,
                failures=[result.error or "Evolution analysis failed"],
            )

        report = result.result or {}
        health = report.get("overall_health_score", 0.5)

        return Reflection(
            agent_id=self.id,
            task_id=result.task_id,
            performance_score=result.quality_score,
            lessons_learned=report.get("lessons_learned", []),
            successes=["Evolution analysis completed"],
            recommendations=[
                f"System health: {health:.0%}",
                f"Patterns to retire: {len(report.get('patterns_to_retire', []))}",
            ],
        )

    async def can_handle(self, task: Task) -> float:
        """Assess ability to handle evolution task."""
        description_lower = task.description.lower()

        evolution_keywords = [
            "improve", "optimize", "evolve", "learn",
            "analyze", "performance", "efficiency",
        ]

        if any(kw in description_lower for kw in evolution_keywords):
            return 0.85

        return 0.3
