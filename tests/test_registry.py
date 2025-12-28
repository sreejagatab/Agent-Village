"""Tests for agent registry."""

import pytest
import pytest_asyncio

from src.agents import ToolAgent
from src.agents.base import AgentType, SimpleAgent
from src.core.registry import AgentRegistry


class TestAgentRegistry:
    """Tests for AgentRegistry."""

    @pytest.mark.asyncio
    async def test_register_agent(self, registry, mock_provider):
        """Test registering an agent."""
        agent = SimpleAgent(
            agent_type=AgentType.TOOL,
            provider=mock_provider,
            system_prompt="Test prompt",
        )
        await agent.initialize()
        await registry.register(agent)

        retrieved = registry.get(agent.id)

        assert retrieved is not None
        assert retrieved.id == agent.id

    @pytest.mark.asyncio
    async def test_unregister_agent(self, registry, mock_provider):
        """Test unregistering an agent."""
        agent = SimpleAgent(
            agent_type=AgentType.TOOL,
            provider=mock_provider,
            system_prompt="Test prompt",
        )
        await agent.initialize()
        await registry.register(agent)
        await registry.unregister(agent.id)

        retrieved = registry.get(agent.id)

        assert retrieved is None

    @pytest.mark.asyncio
    async def test_get_by_type(self, registry, mock_provider):
        """Test getting agents by type."""
        # Register agents of different types
        tool_agent = SimpleAgent(
            agent_type=AgentType.TOOL,
            provider=mock_provider,
            system_prompt="Tool",
        )
        await tool_agent.initialize()
        await registry.register(tool_agent)

        planner_agent = SimpleAgent(
            agent_type=AgentType.PLANNER,
            provider=mock_provider,
            system_prompt="Planner",
        )
        await planner_agent.initialize()
        await registry.register(planner_agent)

        tools = registry.get_by_type(AgentType.TOOL)
        planners = registry.get_by_type(AgentType.PLANNER)

        assert len(tools) == 1
        assert len(planners) == 1
        assert tools[0].agent_type == AgentType.TOOL

    @pytest.mark.asyncio
    async def test_get_available(self, registry, mock_provider):
        """Test getting available agents."""
        agent = SimpleAgent(
            agent_type=AgentType.TOOL,
            provider=mock_provider,
            system_prompt="Test",
        )
        await agent.initialize()
        await registry.register(agent)

        available = registry.get_available(AgentType.TOOL)

        assert len(available) == 1

    @pytest.mark.asyncio
    async def test_get_stats(self, registry, mock_provider):
        """Test getting registry statistics."""
        agent = SimpleAgent(
            agent_type=AgentType.TOOL,
            provider=mock_provider,
            system_prompt="Test",
        )
        await agent.initialize()
        await registry.register(agent)

        stats = registry.get_stats()

        assert stats["total_agents"] == 1
        assert "tool" in stats["by_type"]

    @pytest.mark.asyncio
    async def test_list_agents(self, registry, mock_provider):
        """Test listing all agents."""
        agent = SimpleAgent(
            agent_type=AgentType.TOOL,
            provider=mock_provider,
            system_prompt="Test",
            name="test_agent",
        )
        await agent.initialize()
        await registry.register(agent)

        agents = registry.list_agents()

        assert len(agents) == 1
        assert agents[0]["name"] == "test_agent"

    @pytest.mark.asyncio
    async def test_shutdown_all(self, registry, mock_provider):
        """Test shutting down all agents."""
        for i in range(3):
            agent = SimpleAgent(
                agent_type=AgentType.TOOL,
                provider=mock_provider,
                system_prompt=f"Agent {i}",
            )
            await agent.initialize()
            await registry.register(agent)

        await registry.shutdown_all()

        assert len(registry._agents) == 0

    @pytest.mark.asyncio
    async def test_register_factory(self, registry, mock_provider):
        """Test registering an agent factory."""
        registry.register_factory(
            agent_type=AgentType.TOOL,
            agent_class=ToolAgent,
            default_provider_key="mock",
        )

        # Create agent via factory
        agent = await registry.create_agent(AgentType.TOOL)

        assert agent is not None
        assert agent.agent_type == AgentType.TOOL
