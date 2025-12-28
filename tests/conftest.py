"""
Pytest configuration and fixtures for Agent Village tests.
"""

import asyncio
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio

from src.agents.base import AgentType, BaseAgent, SimpleAgent, AgentConstraints
from src.core.message import (
    AgentMessage,
    Constraints,
    Goal,
    GoalContext,
    MessageType,
    Priority,
    Task,
)
from src.core.registry import AgentRegistry
from src.core.safety import SafetyGate, SafetyLimits
from src.memory.base import InMemoryStore, MemoryEntry, MemoryType
from src.providers.base import Completion, LLMProvider, Message, MessageRole, ProviderPool


# Event loop fixture
@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# Mock LLM Provider
class MockLLMProvider(LLMProvider):
    """Mock LLM provider for testing."""

    def __init__(self, responses: list[str] | None = None):
        super().__init__(name="mock", model="mock-model")
        self.responses = responses or ["Mock response"]
        self.call_count = 0
        self.last_messages: list[Message] = []

    async def complete(
        self,
        messages: list[Message],
        *,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        tools=None,
        tool_choice=None,
        stop=None,
    ) -> Completion:
        self.last_messages = messages
        response = self.responses[self.call_count % len(self.responses)]
        self.call_count += 1

        return Completion(
            content=response,
            tool_calls=[],
            finish_reason="stop",
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            model=self.model,
            provider=self.name,
        )

    async def stream(self, messages, **kwargs):
        yield "Mock stream response"

    def count_tokens(self, text: str) -> int:
        return len(text) // 4

    def supports_function_calling(self) -> bool:
        return True

    def supports_vision(self) -> bool:
        return False

    async def health_check(self) -> bool:
        return True


@pytest.fixture
def mock_provider() -> MockLLMProvider:
    """Create a mock LLM provider."""
    return MockLLMProvider()


@pytest.fixture
def mock_provider_with_json() -> MockLLMProvider:
    """Create a mock provider that returns JSON responses."""
    responses = [
        '{"objective": "test", "complexity": "simple", "risks": [], "approach": "test"}',
        '[{"description": "test task", "agent_type": "TOOL"}]',
    ]
    return MockLLMProvider(responses=responses)


@pytest_asyncio.fixture
async def provider_pool(mock_provider: MockLLMProvider) -> ProviderPool:
    """Create a provider pool with mock provider."""
    pool = ProviderPool()
    pool.register("mock", mock_provider)
    pool.register("anthropic_sonnet", mock_provider)
    pool.register("anthropic_opus", mock_provider)
    return pool


@pytest_asyncio.fixture
async def registry(provider_pool: ProviderPool) -> AsyncGenerator[AgentRegistry, None]:
    """Create an agent registry."""
    reg = AgentRegistry(provider_pool)
    yield reg
    await reg.shutdown_all()


@pytest.fixture
def safety_limits() -> SafetyLimits:
    """Create test safety limits."""
    return SafetyLimits(
        max_recursion_depth=5,
        max_agent_spawns=10,
        max_tokens_per_task=10000,
        max_tokens_per_goal=50000,
        max_execution_time_seconds=60,
    )


@pytest.fixture
def safety_gate(safety_limits: SafetyLimits) -> SafetyGate:
    """Create a safety gate."""
    return SafetyGate(limits=safety_limits)


@pytest.fixture
def sample_goal() -> Goal:
    """Create a sample goal for testing."""
    return Goal(
        description="Test goal: Build a simple calculator",
        success_criteria=["Calculator works", "Tests pass"],
        priority=Priority.NORMAL,
        context={"language": "python"},
    )


@pytest.fixture
def sample_task() -> Task:
    """Create a sample task for testing."""
    return Task(
        description="Implement add function",
        objective="Create a function that adds two numbers",
        expected_output="Python function code",
        constraints=Constraints(
            max_tokens=1000,
            risk_level="low",
        ),
    )


@pytest.fixture
def sample_message(sample_task: Task) -> AgentMessage:
    """Create a sample agent message."""
    return AgentMessage(
        message_type=MessageType.TASK_ASSIGNED,
        sender="test_sender",
        sender_type="governor",
        recipient="test_recipient",
        recipient_type="tool",
        goal_id="test_goal_id",
        task_id=sample_task.id,
        task=sample_task,
        content={"context": "test"},
    )


@pytest.fixture
def goal_context(sample_goal: Goal) -> GoalContext:
    """Create a goal context for testing."""
    return GoalContext(goal=sample_goal)


@pytest.fixture
def memory_store() -> InMemoryStore:
    """Create an in-memory store for testing."""
    return InMemoryStore()


@pytest_asyncio.fixture
async def simple_agent(mock_provider: MockLLMProvider) -> SimpleAgent:
    """Create a simple agent for testing."""
    agent = SimpleAgent(
        agent_type=AgentType.TOOL,
        provider=mock_provider,
        system_prompt="You are a test agent.",
        name="test_agent",
    )
    await agent.initialize()
    return agent
