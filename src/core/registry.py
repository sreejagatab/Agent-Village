"""
Agent Registry for Agent Village.

Manages agent lifecycle, discovery, and coordination.
Integrates with AgentManager for persistence and learning.
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Callable, Type

import structlog

from src.agents.base import AgentState, AgentType, BaseAgent
from src.core.message import AgentMessage, MessageType, Task, generate_id
from src.providers.base import LLMProvider, ProviderPool

if TYPE_CHECKING:
    from src.core.agent_manager import AgentManager

logger = structlog.get_logger()


@dataclass
class AgentRegistration:
    """Registration record for an agent."""

    agent: BaseAgent
    registered_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_heartbeat: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    task_count: int = 0
    error_count: int = 0


@dataclass
class AgentFactory:
    """Factory for creating agents of a specific type."""

    agent_type: AgentType
    agent_class: Type[BaseAgent]
    default_provider_key: str
    default_kwargs: dict[str, Any] = field(default_factory=dict)


class AgentRegistry:
    """
    Central registry for all agents in the village.

    Handles:
    - Agent registration and discovery
    - Agent lifecycle management
    - Agent-to-agent message routing
    - Provider assignment
    - Integration with AgentManager for persistence and learning
    """

    def __init__(
        self,
        provider_pool: ProviderPool,
        agent_manager: "AgentManager | None" = None,
    ):
        self.provider_pool = provider_pool
        self.agent_manager = agent_manager
        self._agents: dict[str, AgentRegistration] = {}
        self._factories: dict[AgentType, AgentFactory] = {}
        self._message_handlers: dict[str, Callable] = {}
        self._lock = asyncio.Lock()
        self.logger = logger.bind(component="agent_registry")

    def set_agent_manager(self, agent_manager: "AgentManager") -> None:
        """Set the agent manager for persistence and learning."""
        self.agent_manager = agent_manager
        self.logger.info("AgentManager connected to registry")

    def register_factory(
        self,
        agent_type: AgentType,
        agent_class: Type[BaseAgent],
        default_provider_key: str = "anthropic_sonnet",
        **default_kwargs: Any,
    ) -> None:
        """
        Register a factory for creating agents of a type.

        Args:
            agent_type: Type of agent this factory creates
            agent_class: Class to instantiate
            default_provider_key: Default LLM provider key
            **default_kwargs: Default keyword arguments for agent creation
        """
        self._factories[agent_type] = AgentFactory(
            agent_type=agent_type,
            agent_class=agent_class,
            default_provider_key=default_provider_key,
            default_kwargs=default_kwargs,
        )
        self.logger.info(
            "Agent factory registered",
            agent_type=agent_type.value,
            agent_class=agent_class.__name__,
        )

    async def create_agent(
        self,
        agent_type: AgentType,
        provider: LLMProvider | None = None,
        **kwargs: Any,
    ) -> BaseAgent:
        """
        Create and register a new agent.

        Args:
            agent_type: Type of agent to create
            provider: Optional specific LLM provider
            **kwargs: Additional arguments for agent creation

        Returns:
            The created agent

        Raises:
            ValueError: If no factory is registered for the agent type
        """
        factory = self._factories.get(agent_type)
        if factory is None:
            raise ValueError(f"No factory registered for agent type: {agent_type}")

        # Get provider
        if provider is None:
            provider = await self.provider_pool.get_for_agent_type(agent_type.value)

        # Merge default kwargs with provided kwargs
        merged_kwargs = {**factory.default_kwargs, **kwargs}

        # Create agent (don't pass agent_type - each class knows its own type)
        agent = factory.agent_class(
            provider=provider,
            **merged_kwargs,
        )

        # Initialize and register
        await agent.initialize()
        await self.register(agent)

        # Register with AgentManager for persistence and learning
        if self.agent_manager:
            await self.agent_manager.register_agent(agent)

        return agent

    async def register(self, agent: BaseAgent) -> None:
        """
        Register an existing agent.

        Args:
            agent: Agent to register
        """
        async with self._lock:
            self._agents[agent.id] = AgentRegistration(agent=agent)
            self.logger.info(
                "Agent registered",
                agent_id=agent.id,
                agent_type=agent.agent_type.value,
                agent_name=agent.name,
            )

    async def unregister(self, agent_id: str) -> None:
        """
        Unregister and shutdown an agent.

        Args:
            agent_id: ID of agent to unregister
        """
        async with self._lock:
            registration = self._agents.pop(agent_id, None)
            if registration:
                await registration.agent.shutdown()
                self.logger.info("Agent unregistered", agent_id=agent_id)

    def get(self, agent_id: str) -> BaseAgent | None:
        """
        Get an agent by ID.

        Args:
            agent_id: Agent ID

        Returns:
            Agent or None if not found
        """
        registration = self._agents.get(agent_id)
        return registration.agent if registration else None

    def get_by_type(self, agent_type: AgentType) -> list[BaseAgent]:
        """
        Get all agents of a specific type.

        Args:
            agent_type: Type of agents to find

        Returns:
            List of matching agents
        """
        return [
            reg.agent
            for reg in self._agents.values()
            if reg.agent.agent_type == agent_type
        ]

    def get_available(self, agent_type: AgentType | None = None) -> list[BaseAgent]:
        """
        Get all available (idle) agents.

        Args:
            agent_type: Optional filter by type

        Returns:
            List of available agents
        """
        agents = []
        for reg in self._agents.values():
            if reg.agent.state != AgentState.IDLE:
                continue
            if agent_type and reg.agent.agent_type != agent_type:
                continue
            agents.append(reg.agent)
        return agents

    async def find_best_agent(
        self,
        agent_type: AgentType,
        task_description: str,
        task: Task | None = None,
    ) -> tuple[BaseAgent | None, float, str]:
        """
        Find the best available agent for a task using intelligent scoring.

        Args:
            agent_type: Required agent type
            task_description: Description of the task
            task: Optional Task object for more context

        Returns:
            Tuple of (best_agent, score, rationale)
        """
        available = self.get_available(agent_type)
        if not available:
            return None, 0.0, "No available agents"

        # Use AgentManager for intelligent selection if available
        if self.agent_manager and task:
            best_agent, score, rationale = await self.agent_manager.find_best_agent(
                agent_type=agent_type,
                task=task,
                available_agents=available,
            )
            if best_agent:
                return best_agent, score, rationale

        # Fallback: Use simple scoring based on agent metrics
        scored_agents = []
        for agent in available:
            score = self._calculate_agent_score(agent, task_description)
            scored_agents.append((agent, score))

        # Sort by score descending
        scored_agents.sort(key=lambda x: x[1], reverse=True)
        best_agent, best_score = scored_agents[0]

        return best_agent, best_score, f"Selected based on availability and metrics (score: {best_score:.2f})"

    def _calculate_agent_score(self, agent: BaseAgent, task_description: str) -> float:
        """Calculate a simple score for an agent based on its metrics."""
        score = 0.5  # Base score

        # Factor in success rate from metrics
        if agent.metrics.tasks_completed > 0:
            success_rate = 1 - (agent.metrics.tasks_failed / agent.metrics.tasks_completed)
            score += 0.3 * success_rate
        else:
            score += 0.3  # New agents get benefit of the doubt

        # Factor in state (prefer idle agents)
        if agent.state == AgentState.IDLE:
            score += 0.2

        return min(1.0, score)

    async def record_task_outcome(
        self,
        agent_id: str,
        task: Task,
        success: bool,
        tokens_used: int = 0,
        execution_time_ms: int = 0,
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
        # Update agent registration stats
        registration = self._agents.get(agent_id)
        if registration:
            registration.task_count += 1
            if not success:
                registration.error_count += 1

        # Record with AgentManager for learning
        if self.agent_manager:
            await self.agent_manager.record_task_outcome(
                agent_id=agent_id,
                task=task,
                success=success,
                tokens_used=tokens_used,
                execution_time_ms=execution_time_ms,
                error=error,
            )

    async def route_message(self, message: AgentMessage) -> None:
        """
        Route a message to its recipient agent.

        Args:
            message: Message to route
        """
        if message.recipient == "broadcast":
            # Broadcast to all agents of the recipient type
            agents = self.get_by_type(AgentType(message.recipient_type))
            for agent in agents:
                await self._deliver_message(agent, message)
        else:
            # Direct delivery
            agent = self.get(message.recipient)
            if agent:
                await self._deliver_message(agent, message)
            else:
                self.logger.warning(
                    "Message recipient not found",
                    recipient=message.recipient,
                    message_id=message.id,
                )

    async def _deliver_message(self, agent: BaseAgent, message: AgentMessage) -> None:
        """Deliver a message to an agent."""
        handler = self._message_handlers.get(agent.id)
        if handler:
            await handler(message)
        else:
            self.logger.debug(
                "No message handler for agent",
                agent_id=agent.id,
                message_id=message.id,
            )

    def register_message_handler(
        self, agent_id: str, handler: Callable[[AgentMessage], Any]
    ) -> None:
        """
        Register a message handler for an agent.

        Args:
            agent_id: Agent ID
            handler: Async callable to handle messages
        """
        self._message_handlers[agent_id] = handler

    def unregister_message_handler(self, agent_id: str) -> None:
        """Unregister a message handler."""
        self._message_handlers.pop(agent_id, None)

    async def heartbeat(self, agent_id: str) -> None:
        """
        Update agent heartbeat timestamp.

        Args:
            agent_id: Agent ID
        """
        registration = self._agents.get(agent_id)
        if registration:
            registration.last_heartbeat = datetime.now(timezone.utc)

    def get_stats(self) -> dict[str, Any]:
        """Get registry statistics."""
        by_type: dict[str, int] = {}
        by_state: dict[str, int] = {}

        for reg in self._agents.values():
            agent_type = reg.agent.agent_type.value
            agent_state = reg.agent.state.value

            by_type[agent_type] = by_type.get(agent_type, 0) + 1
            by_state[agent_state] = by_state.get(agent_state, 0) + 1

        return {
            "total_agents": len(self._agents),
            "by_type": by_type,
            "by_state": by_state,
            "factories_registered": len(self._factories),
        }

    def list_agents(self) -> list[dict[str, Any]]:
        """List all registered agents."""
        return [
            {
                **reg.agent.to_dict(),
                "registered_at": reg.registered_at.isoformat(),
                "last_heartbeat": reg.last_heartbeat.isoformat(),
                "task_count": reg.task_count,
                "error_count": reg.error_count,
            }
            for reg in self._agents.values()
        ]

    async def shutdown_all(self) -> None:
        """Shutdown all registered agents."""
        self.logger.info("Shutting down all agents", count=len(self._agents))

        tasks = []
        for agent_id in list(self._agents.keys()):
            tasks.append(self.unregister(agent_id))

        await asyncio.gather(*tasks, return_exceptions=True)
        self.logger.info("All agents shut down")


# Global registry instance
_registry: AgentRegistry | None = None


def get_registry() -> AgentRegistry:
    """Get the global agent registry."""
    global _registry
    if _registry is None:
        raise RuntimeError("Agent registry not initialized. Call init_registry() first.")
    return _registry


def init_registry(provider_pool: ProviderPool) -> AgentRegistry:
    """Initialize the global agent registry."""
    global _registry
    _registry = AgentRegistry(provider_pool)
    return _registry
