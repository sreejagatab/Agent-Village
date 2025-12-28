"""
Agent Registry for Agent Village.

Manages agent lifecycle, discovery, and coordination.
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Type

import structlog

from src.agents.base import AgentState, AgentType, BaseAgent
from src.core.message import AgentMessage, MessageType, generate_id
from src.providers.base import LLMProvider, ProviderPool

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
    """

    def __init__(self, provider_pool: ProviderPool):
        self.provider_pool = provider_pool
        self._agents: dict[str, AgentRegistration] = {}
        self._factories: dict[AgentType, AgentFactory] = {}
        self._message_handlers: dict[str, Callable] = {}
        self._lock = asyncio.Lock()
        self.logger = logger.bind(component="agent_registry")

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
    ) -> BaseAgent | None:
        """
        Find the best available agent for a task.

        Args:
            agent_type: Required agent type
            task_description: Description of the task

        Returns:
            Best matching agent or None
        """
        available = self.get_available(agent_type)
        if not available:
            return None

        # For now, return the first available
        # TODO: Implement scoring based on agent capabilities and task
        return available[0]

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
