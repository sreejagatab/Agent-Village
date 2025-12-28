"""
Evolver Agent - Self-improvement.

Responsible for:
- Improving prompts
- Optimizing workflows
- Learning from experience
- Retiring ineffective patterns
"""

import json
import re
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


def extract_json_from_response(response: str) -> dict[str, Any]:
    """Extract JSON from LLM response, handling markdown code blocks."""
    # Try to extract JSON from markdown code blocks
    json_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', response, re.DOTALL)
    if json_match:
        json_str = json_match.group(1).strip()
    else:
        # Try to find JSON object directly
        json_str = response.strip()

    # Try to parse the JSON
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        # Try to find JSON-like content between braces
        brace_match = re.search(r'\{[\s\S]*\}', json_str)
        if brace_match:
            try:
                return json.loads(brace_match.group(0))
            except json.JSONDecodeError:
                pass
    return {}


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
        data = extract_json_from_response(response)

        if not data:
            self.logger.warning("Failed to parse prompt optimization", response=response[:200])
            return EvolutionReport(
                lessons_learned=["Prompt optimization analysis completed but parsing failed"],
            )

        optimization = PromptOptimization(
            agent_type=agent_type,
            original_prompt=current_prompt,
            optimized_prompt=data.get("optimized_prompt", current_prompt),
            rationale=data.get("rationale", ""),
            expected_improvement=float(data.get("expected_improvement", 0.0)),
            confidence=float(data.get("confidence", 0.5)),
        )

        return EvolutionReport(
            prompt_optimizations=[optimization],
            lessons_learned=data.get("changes", []),
        )

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
        data = extract_json_from_response(response)

        if not data:
            self.logger.warning("Failed to parse workflow optimization", response=response[:200])
            return EvolutionReport(
                lessons_learned=["Workflow optimization analysis completed but parsing failed"],
            )

        optimization = WorkflowOptimization(
            workflow_name=workflow_name,
            current_steps=current_steps,
            optimized_steps=data.get("optimized_steps", current_steps),
            rationale=data.get("rationale", ""),
            expected_speedup=float(data.get("expected_speedup", 1.0)),
            expected_quality_change=float(data.get("expected_quality_change", 0.0)),
        )

        # Include parallelization suggestions in lessons
        lessons = []
        parallelization = data.get("parallelization", [])
        if parallelization:
            lessons.append(f"Steps that can run in parallel: {', '.join(parallelization)}")

        return EvolutionReport(
            workflow_optimizations=[optimization],
            patterns_to_retire=data.get("removed_steps", []),
            lessons_learned=lessons,
        )

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

IMPORTANT: Provide SPECIFIC, ACTIONABLE recommendations based on the data.

Analyze and provide:
1. Patterns that are working well (cite specific agent success rates)
2. Patterns that should be retired (cite specific issues)
3. Prompt improvements needed (be specific about what to change)
4. Workflow improvements needed (identify bottlenecks)
5. Overall system health assessment with clear reasoning

Calculate health_score based on:
- Average success rate across agents
- Token efficiency (tokens per successful task)
- Error patterns and their frequency

You MUST respond with valid JSON (no markdown, no extra text):
{{
    "successful_patterns": ["specific patterns working well with evidence"],
    "patterns_to_retire": ["specific ineffective patterns with reasoning"],
    "prompt_improvements": [
        {{
            "agent_type": "specific agent type",
            "current_issue": "what is wrong",
            "improvement": "specific change to make",
            "rationale": "expected benefit",
            "priority": "high/medium/low"
        }}
    ],
    "workflow_improvements": [
        {{
            "workflow": "workflow name",
            "bottleneck": "identified bottleneck",
            "improvement": "specific change to make",
            "expected_speedup": 1.2,
            "expected_quality_change": 0.1,
            "priority": "high/medium/low"
        }}
    ],
    "lessons_learned": ["key actionable insights from analysis"],
    "health_score": 0.75,
    "health_score_reasoning": "explanation of how score was calculated",
    "recommendations": [
        {{
            "action": "specific action to take",
            "priority": "high/medium/low",
            "expected_impact": "what improvement this will bring"
        }}
    ]
}}"""

        response = await self._call_llm(prompt, temperature=0.3)
        data = extract_json_from_response(response)

        if not data:
            self.logger.warning("Failed to parse evolution analysis", response=response[:500])
            # Generate basic analysis from available data
            agents = historical_data.get("agents", [])
            total_tasks = sum(a.get("total_tasks", 0) for a in agents)
            avg_success = sum(a.get("success_rate", 0) for a in agents) / max(len(agents), 1)

            return EvolutionReport(
                lessons_learned=[
                    f"System has {len(agents)} agents with {total_tasks} total tasks",
                    f"Average success rate: {avg_success:.0%}",
                    "Detailed analysis requires manual review",
                ],
                overall_health_score=avg_success,
            )

        # Parse prompt improvements into PromptOptimization objects
        prompt_opts = []
        for p in data.get("prompt_improvements", []):
            if isinstance(p, dict):
                prompt_opts.append(PromptOptimization(
                    agent_type=p.get("agent_type", "unknown"),
                    original_prompt=p.get("current_issue", ""),
                    optimized_prompt=p.get("improvement", ""),
                    rationale=p.get("rationale", ""),
                    expected_improvement=0.1 if p.get("priority") == "high" else 0.05,
                    confidence=0.7,
                ))

        # Parse workflow improvements into WorkflowOptimization objects
        workflow_opts = []
        for w in data.get("workflow_improvements", []):
            if isinstance(w, dict):
                workflow_opts.append(WorkflowOptimization(
                    workflow_name=w.get("workflow", "unknown"),
                    current_steps=[w.get("bottleneck", "")],
                    optimized_steps=[w.get("improvement", "")],
                    rationale=w.get("rationale", w.get("improvement", "")),
                    expected_speedup=float(w.get("expected_speedup", 1.0)),
                    expected_quality_change=float(w.get("expected_quality_change", 0.0)),
                ))

        # Build comprehensive lessons learned including recommendations
        lessons_learned = data.get("lessons_learned", [])
        recommendations = data.get("recommendations", [])
        if isinstance(recommendations, list):
            for rec in recommendations:
                if isinstance(rec, dict):
                    lessons_learned.append(f"[{rec.get('priority', 'medium').upper()}] {rec.get('action', '')}")
                elif isinstance(rec, str):
                    lessons_learned.append(rec)

        if data.get("health_score_reasoning"):
            lessons_learned.append(f"Health Assessment: {data.get('health_score_reasoning')}")

        return EvolutionReport(
            prompt_optimizations=prompt_opts,
            workflow_optimizations=workflow_opts,
            patterns_to_retire=data.get("patterns_to_retire", []),
            lessons_learned=lessons_learned,
            overall_health_score=float(data.get("health_score", 0.5)),
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
