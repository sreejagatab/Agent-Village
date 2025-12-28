"""
Agent Manager - Intelligent Agent Lifecycle Management.

Handles:
- Agent creation with capability matching
- Persistence to database
- Performance tracking and learning
- Intelligent agent selection and reuse
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

import structlog

if TYPE_CHECKING:
    from src.agents.base import AgentType, BaseAgent, AgentState
    from src.core.message import Task

from src.memory.strategic import Decision, StrategicMemory
from src.persistence.database import get_async_session
from src.persistence.repositories import AgentStateRepository

logger = structlog.get_logger()


@dataclass
class AgentCapability:
    """Describes what an agent can do."""

    name: str
    description: str
    keywords: list[str] = field(default_factory=list)
    required_tools: list[str] = field(default_factory=list)
    success_rate: float = 1.0  # Historical success rate for this capability
    avg_execution_time_ms: int = 0
    times_used: int = 0


@dataclass
class AgentPerformance:
    """Tracks an agent's performance metrics."""

    agent_id: str
    total_tasks: int = 0
    successful_tasks: int = 0
    failed_tasks: int = 0
    total_tokens_used: int = 0
    total_execution_time_ms: int = 0
    capability_scores: dict[str, float] = field(default_factory=dict)  # capability -> success rate
    task_type_scores: dict[str, float] = field(default_factory=dict)  # task_type -> success rate
    last_used: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def success_rate(self) -> float:
        if self.total_tasks == 0:
            return 1.0  # New agents start with perfect score
        return self.successful_tasks / self.total_tasks

    @property
    def avg_execution_time(self) -> float:
        if self.total_tasks == 0:
            return 0
        return self.total_execution_time_ms / self.total_tasks

    def record_task_result(
        self,
        success: bool,
        task_type: str,
        tokens_used: int,
        execution_time_ms: int,
        capabilities_used: list[str] | None = None,
    ) -> None:
        """Record the result of a task execution."""
        self.total_tasks += 1
        self.total_tokens_used += tokens_used
        self.total_execution_time_ms += execution_time_ms
        self.last_used = datetime.now(timezone.utc)

        if success:
            self.successful_tasks += 1
        else:
            self.failed_tasks += 1

        # Update task type score (exponential moving average)
        alpha = 0.3  # Learning rate
        current_score = self.task_type_scores.get(task_type, 1.0)
        new_score = alpha * (1.0 if success else 0.0) + (1 - alpha) * current_score
        self.task_type_scores[task_type] = new_score

        # Update capability scores
        if capabilities_used:
            for cap in capabilities_used:
                current = self.capability_scores.get(cap, 1.0)
                new = alpha * (1.0 if success else 0.0) + (1 - alpha) * current
                self.capability_scores[cap] = new


@dataclass
class AgentProfile:
    """Complete profile of an agent including capabilities and performance."""

    agent_id: str
    agent_type: AgentType
    name: str
    capabilities: list[AgentCapability] = field(default_factory=list)
    performance: AgentPerformance = field(default_factory=lambda: AgentPerformance(agent_id=""))
    specializations: list[str] = field(default_factory=list)  # Task types this agent excels at
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    is_active: bool = True

    def __post_init__(self):
        if self.performance.agent_id == "":
            self.performance.agent_id = self.agent_id

    def get_score_for_task(self, task_description: str, task_type: str) -> float:
        """Calculate how suitable this agent is for a task."""
        score = 0.5  # Base score

        # Factor 1: Success rate (40% weight)
        score += 0.4 * self.performance.success_rate

        # Factor 2: Task type specialization (30% weight)
        if task_type in self.performance.task_type_scores:
            score += 0.3 * self.performance.task_type_scores[task_type]
        elif task_type in self.specializations:
            score += 0.3 * 0.8  # Good but unproven

        # Factor 3: Keyword matching in capabilities (20% weight)
        task_lower = task_description.lower()
        capability_match = 0.0
        for cap in self.capabilities:
            for keyword in cap.keywords:
                if keyword.lower() in task_lower:
                    capability_match = max(capability_match, cap.success_rate)
        score += 0.2 * capability_match

        # Factor 4: Recent activity bonus (10% weight)
        hours_since_use = (datetime.now(timezone.utc) - self.performance.last_used).total_seconds() / 3600
        recency_score = max(0, 1 - (hours_since_use / 24))  # Decay over 24 hours
        score += 0.1 * recency_score

        return min(1.0, score)

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type.value,
            "name": self.name,
            "capabilities": [
                {
                    "name": c.name,
                    "description": c.description,
                    "keywords": c.keywords,
                    "success_rate": c.success_rate,
                }
                for c in self.capabilities
            ],
            "performance": {
                "success_rate": self.performance.success_rate,
                "total_tasks": self.performance.total_tasks,
                "avg_execution_time": self.performance.avg_execution_time,
            },
            "specializations": self.specializations,
            "is_active": self.is_active,
        }


class AgentManager:
    """
    Manages agent lifecycle with persistence and learning.

    Key responsibilities:
    - Create agents with appropriate capabilities
    - Save/load agents from database
    - Track performance and learn from outcomes
    - Select best agents for tasks
    - Retire underperforming agents
    """

    def __init__(
        self,
        strategic_memory: StrategicMemory | None = None,
        min_success_rate: float = 0.3,  # Minimum success rate before retirement consideration
        max_agents_per_type: int = 10,  # Maximum agents to keep per type
    ):
        self.strategic_memory = strategic_memory or StrategicMemory()
        self.min_success_rate = min_success_rate
        self.max_agents_per_type = max_agents_per_type

        self._profiles: dict[str, AgentProfile] = {}
        self._agents: dict[str, BaseAgent] = {}  # Live agent instances
        self._lock = asyncio.Lock()

        self.logger = logger.bind(component="agent_manager")

    async def initialize(self) -> None:
        """Load existing agent profiles from database."""
        try:
            async with get_async_session() as session:
                repo = AgentStateRepository(session)
                active_states = await repo.list_active()

                for state in active_states:
                    profile = AgentProfile(
                        agent_id=state.id,
                        agent_type=AgentType(state.agent_type),
                        name=state.name,
                        capabilities=self._capabilities_from_json(state.capabilities),
                        performance=AgentPerformance(
                            agent_id=state.id,
                            total_tasks=state.total_tasks_completed,
                            successful_tasks=int(state.total_tasks_completed * state.success_rate),
                            failed_tasks=int(state.total_tasks_completed * (1 - state.success_rate)),
                            total_tokens_used=state.total_tokens_used,
                            total_execution_time_ms=state.total_execution_time_ms,
                        ),
                        is_active=state.state != "stopped",
                    )
                    self._profiles[state.id] = profile

                self.logger.info(
                    "Loaded agent profiles from database",
                    count=len(self._profiles),
                )
        except Exception as e:
            self.logger.warning("Failed to load agent profiles", error=str(e))

    def _capabilities_from_json(self, capabilities_json: list) -> list[AgentCapability]:
        """Convert JSON capabilities to AgentCapability objects."""
        result = []
        for cap in capabilities_json:
            if isinstance(cap, dict):
                result.append(AgentCapability(
                    name=cap.get("name", "unknown"),
                    description=cap.get("description", ""),
                    keywords=cap.get("keywords", []),
                    required_tools=cap.get("required_tools", []),
                    success_rate=cap.get("success_rate", 1.0),
                ))
            elif isinstance(cap, str):
                result.append(AgentCapability(name=cap, description=cap))
        return result

    async def register_agent(
        self,
        agent: BaseAgent,
        capabilities: list[AgentCapability] | None = None,
        specializations: list[str] | None = None,
    ) -> AgentProfile:
        """
        Register a new agent with the manager.

        Args:
            agent: The agent instance
            capabilities: Agent's capabilities
            specializations: Task types the agent specializes in

        Returns:
            AgentProfile for the registered agent
        """
        async with self._lock:
            # Create profile
            profile = AgentProfile(
                agent_id=agent.id,
                agent_type=agent.agent_type,
                name=agent.name,
                capabilities=capabilities or self._default_capabilities(agent.agent_type),
                specializations=specializations or self._default_specializations(agent.agent_type),
            )

            self._profiles[agent.id] = profile
            self._agents[agent.id] = agent

            # Save to database
            await self._save_agent_state(agent, profile)

            # Record decision in strategic memory
            decision = Decision(
                decision_type="agent_creation",
                description=f"Created {agent.agent_type.value} agent: {agent.name}",
                rationale=f"New agent needed for {agent.agent_type.value} tasks",
                alternatives_considered=["reuse_existing", "create_specialized"],
            )
            await self.strategic_memory.record_decision(
                decision,
                agent_id=agent.id,
            )

            self.logger.info(
                "Agent registered",
                agent_id=agent.id,
                agent_type=agent.agent_type.value,
                capabilities=len(profile.capabilities),
            )

            return profile

    def _default_capabilities(self, agent_type: AgentType) -> list[AgentCapability]:
        """Get default capabilities for an agent type."""
        if agent_type == AgentType.TOOL:
            return [
                AgentCapability(
                    name="code_execution",
                    description="Execute Python code and shell commands",
                    keywords=["execute", "run", "script", "code", "python", "shell"],
                    required_tools=["execute_python", "shell_command"],
                ),
                AgentCapability(
                    name="file_operations",
                    description="Read, write, and manage files",
                    keywords=["file", "read", "write", "create", "save", "load"],
                    required_tools=["read_file", "write_file", "create_directory"],
                ),
                AgentCapability(
                    name="web_requests",
                    description="Make HTTP requests and fetch data",
                    keywords=["http", "api", "fetch", "request", "web", "url"],
                    required_tools=["http_get", "http_post", "http_request"],
                ),
                AgentCapability(
                    name="data_analysis",
                    description="Analyze and process data",
                    keywords=["analyze", "calculate", "statistics", "data", "process"],
                    required_tools=["execute_python", "calculate"],
                ),
            ]
        elif agent_type == AgentType.PLANNER:
            return [
                AgentCapability(
                    name="task_decomposition",
                    description="Break down complex goals into tasks",
                    keywords=["plan", "decompose", "break down", "steps", "tasks"],
                ),
                AgentCapability(
                    name="strategy_selection",
                    description="Choose execution strategies",
                    keywords=["strategy", "approach", "method", "how to"],
                ),
            ]
        elif agent_type == AgentType.CRITIC:
            return [
                AgentCapability(
                    name="code_review",
                    description="Review and critique code",
                    keywords=["review", "check", "validate", "verify", "quality"],
                ),
                AgentCapability(
                    name="output_validation",
                    description="Validate task outputs",
                    keywords=["validate", "correct", "accurate", "complete"],
                ),
            ]
        return []

    def _default_specializations(self, agent_type: AgentType) -> list[str]:
        """Get default specializations for an agent type."""
        if agent_type == AgentType.TOOL:
            return ["action", "execution", "implementation"]
        elif agent_type == AgentType.PLANNER:
            return ["planning", "decomposition", "strategy"]
        elif agent_type == AgentType.CRITIC:
            return ["review", "validation", "quality"]
        return []

    async def _save_agent_state(self, agent: BaseAgent, profile: AgentProfile) -> None:
        """Save agent state to database."""
        try:
            async with get_async_session() as session:
                repo = AgentStateRepository(session)

                state_dict = {
                    "agent_type": agent.agent_type.value,
                    "name": agent.name,
                    "state": agent.state.value,
                    "provider_key": getattr(agent.provider, 'model', 'unknown'),
                    "model_name": getattr(agent.provider, 'model', 'unknown'),
                    "system_prompt": getattr(agent, '_system_prompt', None),
                    "capabilities": [
                        {
                            "name": c.name,
                            "description": c.description,
                            "keywords": c.keywords,
                            "success_rate": c.success_rate,
                        }
                        for c in profile.capabilities
                    ],
                    "constraints": agent.constraints.to_dict() if hasattr(agent.constraints, 'to_dict') else {},
                    "total_tasks_completed": profile.performance.total_tasks,
                    "total_tokens_used": profile.performance.total_tokens_used,
                    "total_execution_time_ms": profile.performance.total_execution_time_ms,
                    "success_rate": profile.performance.success_rate,
                }

                await repo.save(agent.id, state_dict)

        except Exception as e:
            self.logger.error("Failed to save agent state", agent_id=agent.id, error=str(e))

    async def find_best_agent(
        self,
        agent_type: AgentType,
        task: Task,
        available_agents: list[BaseAgent],
    ) -> tuple[BaseAgent | None, float, str]:
        """
        Find the best agent for a task using intelligent scoring.

        Args:
            agent_type: Required agent type
            task: Task to be executed
            available_agents: Currently available agent instances

        Returns:
            Tuple of (best_agent, score, rationale)
        """
        if not available_agents:
            return None, 0.0, "No available agents"

        # Check strategic memory for similar past decisions
        past_decisions = await self.strategic_memory.find_similar_decisions(
            decision_type="agent_assignment",
            context_description=task.description,
            min_outcome_score=0.7,
            limit=3,
        )

        # Build scoring context from past decisions
        preferred_agents = set()
        for decision in past_decisions:
            content = decision.content
            if isinstance(content, dict) and content.get("outcome") == "success":
                if "selected_agent_id" in content:
                    preferred_agents.add(content["selected_agent_id"])

        # Score each available agent
        scored_agents = []
        task_type = self._infer_task_type(task.description)

        for agent in available_agents:
            if agent.agent_type != agent_type:
                continue

            profile = self._profiles.get(agent.id)
            if profile:
                base_score = profile.get_score_for_task(task.description, task_type)
            else:
                base_score = 0.5  # Unknown agent

            # Bonus for agents that worked well on similar tasks
            if agent.id in preferred_agents:
                base_score = min(1.0, base_score + 0.2)

            scored_agents.append((agent, base_score))

        if not scored_agents:
            return None, 0.0, f"No agents of type {agent_type.value}"

        # Sort by score and select best
        scored_agents.sort(key=lambda x: x[1], reverse=True)
        best_agent, best_score = scored_agents[0]

        rationale = f"Selected {best_agent.name} (score: {best_score:.2f}) based on "
        if best_agent.id in preferred_agents:
            rationale += "past success on similar tasks and "
        rationale += f"capability match for {task_type} task"

        self.logger.info(
            "Agent selected",
            agent_id=best_agent.id,
            score=best_score,
            task_type=task_type,
            candidates=len(scored_agents),
        )

        return best_agent, best_score, rationale

    def _infer_task_type(self, description: str) -> str:
        """Infer the type of task from its description."""
        description_lower = description.lower()

        if any(kw in description_lower for kw in ["create", "write", "generate", "build"]):
            return "creation"
        elif any(kw in description_lower for kw in ["fetch", "get", "download", "api"]):
            return "data_retrieval"
        elif any(kw in description_lower for kw in ["analyze", "calculate", "compute"]):
            return "analysis"
        elif any(kw in description_lower for kw in ["review", "check", "validate"]):
            return "validation"
        elif any(kw in description_lower for kw in ["execute", "run", "shell"]):
            return "execution"
        elif any(kw in description_lower for kw in ["plan", "decompose", "break"]):
            return "planning"
        else:
            return "general"

    async def record_task_outcome(
        self,
        agent_id: str,
        task: Task,
        success: bool,
        tokens_used: int,
        execution_time_ms: int,
        error: str | None = None,
    ) -> None:
        """
        Record the outcome of a task execution for learning.

        Args:
            agent_id: ID of the agent that executed the task
            task: The executed task
            success: Whether the task succeeded
            tokens_used: Tokens consumed
            execution_time_ms: Execution time
            error: Error message if failed
        """
        async with self._lock:
            profile = self._profiles.get(agent_id)
            if not profile:
                self.logger.warning("No profile found for agent", agent_id=agent_id)
                return

            # Update performance metrics
            task_type = self._infer_task_type(task.description)
            profile.performance.record_task_result(
                success=success,
                task_type=task_type,
                tokens_used=tokens_used,
                execution_time_ms=execution_time_ms,
            )

            # Record in strategic memory
            decision = Decision(
                decision_type="agent_assignment",
                description=f"Assigned {profile.name} to: {task.description[:100]}",
                rationale=f"Agent selected for {task_type} task",
                outcome="success" if success else "failure",
                outcome_score=1.0 if success else 0.0,
                lessons=[
                    f"Agent {profile.name} {'succeeded' if success else 'failed'} on {task_type} task",
                    f"Execution time: {execution_time_ms}ms, tokens: {tokens_used}",
                ] + ([f"Error: {error}"] if error else []),
            )
            await self.strategic_memory.record_decision(
                decision,
                agent_id=agent_id,
                task_id=task.id,
            )

            # Update database
            agent = self._agents.get(agent_id)
            if agent:
                await self._save_agent_state(agent, profile)

            self.logger.info(
                "Task outcome recorded",
                agent_id=agent_id,
                task_type=task_type,
                success=success,
                new_success_rate=profile.performance.success_rate,
            )

            # Check if agent should be retired
            if profile.performance.total_tasks >= 5:  # Minimum tasks before evaluation
                if profile.performance.success_rate < self.min_success_rate:
                    self.logger.warning(
                        "Agent underperforming, consider retirement",
                        agent_id=agent_id,
                        success_rate=profile.performance.success_rate,
                    )

    async def get_agent_recommendations(
        self,
        task_description: str,
        agent_type: AgentType,
        top_n: int = 3,
    ) -> list[dict[str, Any]]:
        """
        Get recommendations for which agents to use for a task.

        Args:
            task_description: Description of the task
            agent_type: Required agent type
            top_n: Number of recommendations

        Returns:
            List of recommendations with scores and rationales
        """
        task_type = self._infer_task_type(task_description)
        recommendations = []

        for agent_id, profile in self._profiles.items():
            if profile.agent_type != agent_type or not profile.is_active:
                continue

            score = profile.get_score_for_task(task_description, task_type)
            recommendations.append({
                "agent_id": agent_id,
                "agent_name": profile.name,
                "score": score,
                "success_rate": profile.performance.success_rate,
                "total_tasks": profile.performance.total_tasks,
                "specializations": profile.specializations,
                "rationale": self._generate_recommendation_rationale(profile, task_type, score),
            })

        # Sort by score
        recommendations.sort(key=lambda x: x["score"], reverse=True)

        return recommendations[:top_n]

    def _generate_recommendation_rationale(
        self,
        profile: AgentProfile,
        task_type: str,
        score: float,
    ) -> str:
        """Generate a human-readable rationale for a recommendation."""
        parts = []

        if profile.performance.success_rate >= 0.9:
            parts.append(f"High success rate ({profile.performance.success_rate:.0%})")
        elif profile.performance.success_rate >= 0.7:
            parts.append(f"Good success rate ({profile.performance.success_rate:.0%})")

        if task_type in profile.specializations:
            parts.append(f"Specializes in {task_type} tasks")

        if task_type in profile.performance.task_type_scores:
            type_score = profile.performance.task_type_scores[task_type]
            if type_score >= 0.8:
                parts.append(f"Proven track record on {task_type}")

        if profile.performance.total_tasks > 10:
            parts.append(f"Experienced ({profile.performance.total_tasks} tasks)")

        if not parts:
            parts.append("Available for task")

        return "; ".join(parts)

    async def get_lessons_for_task_type(self, task_type: str) -> list[str]:
        """Get lessons learned for a specific task type."""
        return await self.strategic_memory.get_lessons_learned(
            decision_type="agent_assignment",
            limit=10,
        )

    def get_profile(self, agent_id: str) -> AgentProfile | None:
        """Get the profile for an agent."""
        return self._profiles.get(agent_id)

    def get_all_profiles(self) -> list[AgentProfile]:
        """Get all agent profiles."""
        return list(self._profiles.values())

    async def retire_agent(self, agent_id: str, reason: str = "manual") -> bool:
        """
        Retire an agent, marking it inactive.

        Args:
            agent_id: Agent to retire
            reason: Reason for retirement

        Returns:
            True if retired successfully
        """
        async with self._lock:
            profile = self._profiles.get(agent_id)
            if not profile:
                return False

            profile.is_active = False

            # Record retirement decision
            decision = Decision(
                decision_type="agent_retirement",
                description=f"Retired agent {profile.name}",
                rationale=reason,
                outcome="completed",
                lessons=[
                    f"Agent retired after {profile.performance.total_tasks} tasks",
                    f"Final success rate: {profile.performance.success_rate:.0%}",
                ],
            )
            await self.strategic_memory.record_decision(decision, agent_id=agent_id)

            # Update database
            try:
                async with get_async_session() as session:
                    repo = AgentStateRepository(session)
                    await repo.save(agent_id, {"state": "stopped"})
            except Exception as e:
                self.logger.error("Failed to update retired agent in database", error=str(e))

            self.logger.info(
                "Agent retired",
                agent_id=agent_id,
                reason=reason,
                total_tasks=profile.performance.total_tasks,
            )

            return True
