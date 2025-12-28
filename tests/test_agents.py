"""Tests for agent implementations."""

import pytest
import pytest_asyncio

from src.agents.base import AgentState, AgentType, BaseAgent, SimpleAgent
from src.agents.planner import PlannerAgent
from src.agents.tool_agent import ToolAgent
from src.agents.critic import CriticAgent
from src.core.message import AgentMessage, MessageType, Task


class TestBaseAgent:
    """Tests for BaseAgent."""

    @pytest.mark.asyncio
    async def test_agent_initialization(self, simple_agent):
        """Test agent initializes correctly."""
        assert simple_agent.state == AgentState.IDLE
        assert simple_agent.agent_type == AgentType.TOOL
        assert simple_agent.id is not None

    @pytest.mark.asyncio
    async def test_agent_execute(self, simple_agent, sample_message):
        """Test agent execution."""
        result = await simple_agent.execute(sample_message)

        assert result.task_id == sample_message.task.id
        assert result.agent_id == simple_agent.id
        assert result.success is True

    @pytest.mark.asyncio
    async def test_agent_shutdown(self, simple_agent):
        """Test agent shutdown."""
        await simple_agent.shutdown()

        assert simple_agent.state == AgentState.STOPPED

    @pytest.mark.asyncio
    async def test_agent_metrics_updated(self, simple_agent, sample_message):
        """Test that metrics are updated after execution."""
        initial_completed = simple_agent.metrics.tasks_completed

        await simple_agent.execute(sample_message)

        assert simple_agent.metrics.tasks_completed == initial_completed + 1
        assert simple_agent.metrics.total_tokens_used > 0

    @pytest.mark.asyncio
    async def test_agent_to_dict(self, simple_agent):
        """Test agent serialization."""
        data = simple_agent.to_dict()

        assert data["id"] == simple_agent.id
        assert data["type"] == simple_agent.agent_type.value
        assert data["state"] == simple_agent.state.value
        assert "metrics" in data


class TestPlannerAgent:
    """Tests for PlannerAgent."""

    @pytest_asyncio.fixture
    async def planner(self, mock_provider_with_json):
        """Create a planner agent."""
        agent = PlannerAgent(
            provider=mock_provider_with_json,
            name="test_planner",
        )
        await agent.initialize()
        return agent

    @pytest.mark.asyncio
    async def test_planner_creates_plan(self, planner, sample_message):
        """Test planner creates execution plan."""
        result = await planner.execute(sample_message)

        assert result.success is True
        assert "tasks" in result.result or "goal_description" in result.result

    @pytest.mark.asyncio
    async def test_planner_can_handle_planning_task(self, planner):
        """Test planner confidence for planning tasks."""
        task = Task(description="Plan the implementation of a new feature")
        confidence = await planner.can_handle(task)

        assert confidence >= 0.7


class TestToolAgent:
    """Tests for ToolAgent."""

    @pytest_asyncio.fixture
    async def tool_agent(self, mock_provider):
        """Create a tool agent."""
        agent = ToolAgent(
            provider=mock_provider,
            name="test_tool_agent",
        )
        await agent.initialize()
        return agent

    @pytest.mark.asyncio
    async def test_tool_agent_executes(self, tool_agent, sample_message):
        """Test tool agent execution."""
        result = await tool_agent.execute(sample_message)

        assert result.task_id == sample_message.task.id
        assert result.agent_id == tool_agent.id

    @pytest.mark.asyncio
    async def test_tool_agent_can_handle_action_task(self, tool_agent):
        """Test tool agent confidence for action tasks."""
        task = Task(description="Execute the API call and fetch user data")
        confidence = await tool_agent.can_handle(task)

        assert confidence >= 0.7


class TestCriticAgent:
    """Tests for CriticAgent."""

    @pytest_asyncio.fixture
    async def critic(self, mock_provider_with_json):
        """Create a critic agent."""
        # Override mock to return review JSON
        mock_provider_with_json.responses = [
            '{"validity": "valid", "quality_score": 85, "issues": [], "strengths": ["good"], "recommendations": [], "summary": "Good work"}'
        ]
        agent = CriticAgent(
            provider=mock_provider_with_json,
            name="test_critic",
        )
        await agent.initialize()
        return agent

    @pytest.mark.asyncio
    async def test_critic_reviews_content(self, critic):
        """Test critic reviews content."""
        task = Task(description="Review the implementation")
        message = AgentMessage(
            message_type=MessageType.TASK_ASSIGNED,
            sender="governor",
            sender_type="governor",
            recipient=critic.id,
            recipient_type="critic",
            task=task,
            content={
                "content_to_review": "def add(a, b): return a + b",
                "original_task": "Implement add function",
            },
        )

        result = await critic.execute(message)

        assert result.success is True
        assert "validity" in result.result

    @pytest.mark.asyncio
    async def test_critic_can_handle_review_task(self, critic):
        """Test critic confidence for review tasks."""
        task = Task(description="Review and validate the code quality")
        confidence = await critic.can_handle(task)

        assert confidence >= 0.8


class TestAgentReflection:
    """Tests for agent reflection."""

    @pytest.mark.asyncio
    async def test_successful_reflection(self, simple_agent, sample_message):
        """Test reflection on successful execution."""
        result = await simple_agent.execute(sample_message)
        reflection = await simple_agent.reflect(result)

        assert reflection.agent_id == simple_agent.id
        assert reflection.task_id == result.task_id
        assert len(reflection.successes) > 0 or reflection.performance_score > 0

    @pytest.mark.asyncio
    async def test_failed_reflection(self, simple_agent):
        """Test reflection on failed execution."""
        from src.core.message import AgentResult

        failed_result = AgentResult(
            task_id="test_task",
            agent_id=simple_agent.id,
            agent_type=simple_agent.agent_type.value,
            success=False,
            error="Task failed",
        )

        reflection = await simple_agent.reflect(failed_result)

        assert len(reflection.failures) > 0
