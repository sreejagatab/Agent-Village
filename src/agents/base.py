"""
Base Agent class for Agent Village.

All agents inherit from this base class, which provides:
- Lifecycle management
- LLM provider integration
- Message handling
- Reflection capabilities
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

import structlog

from src.core.message import (
    AgentMessage,
    AgentResult,
    Constraints,
    GoalContext,
    MessageType,
    Reflection,
    Task,
    generate_id,
    utc_now,
)
from src.providers.base import LLMProvider, Message, MessageRole

logger = structlog.get_logger()


class AgentType(str, Enum):
    """Types of agents in the system."""

    # Governance
    GOVERNOR = "governor"

    # Cognition
    PLANNER = "planner"
    REASONER = "reasoner"

    # Action
    TOOL = "tool"

    # Validation
    CRITIC = "critic"

    # Memory
    MEMORY_KEEPER = "memory_keeper"

    # Coordination
    SWARM_COORDINATOR = "swarm_coordinator"
    SWARM_WORKER = "swarm_worker"

    # Adaptation
    EVOLVER = "evolver"


class AgentState(str, Enum):
    """Agent lifecycle states."""

    INITIALIZING = "initializing"
    IDLE = "idle"
    BUSY = "busy"
    WAITING = "waiting"
    ERROR = "error"
    STOPPED = "stopped"


@dataclass
class AgentConstraints:
    """Constraints specific to an agent instance."""

    max_tokens_per_request: int = 4096
    max_retries: int = 3
    timeout_seconds: int = 300
    allowed_tools: set[str] = field(default_factory=set)
    can_spawn_agents: bool = False
    can_access_memory: bool = True
    risk_tolerance: str = "low"  # low, medium, high


@dataclass
class AgentMetrics:
    """Runtime metrics for an agent."""

    tasks_completed: int = 0
    tasks_failed: int = 0
    total_tokens_used: int = 0
    total_execution_time: float = 0.0
    average_confidence: float = 0.0
    average_quality: float = 0.0
    created_at: datetime = field(default_factory=utc_now)
    last_active_at: datetime = field(default_factory=utc_now)


class BaseAgent(ABC):
    """
    Abstract base class for all agents.

    Every agent in the village must inherit from this class and implement
    the required abstract methods.
    """

    def __init__(
        self,
        agent_type: AgentType,
        provider: LLMProvider,
        name: str | None = None,
        constraints: AgentConstraints | None = None,
    ):
        self.id = generate_id()
        self.agent_type = agent_type
        self.name = name or f"{agent_type.value}_{self.id[:8]}"
        self.provider = provider
        self.constraints = constraints or AgentConstraints()

        self.state = AgentState.INITIALIZING
        self.metrics = AgentMetrics()

        self.logger = logger.bind(
            agent_id=self.id,
            agent_type=self.agent_type.value,
            agent_name=self.name,
        )

        # Conversation history for this agent
        self._conversation: list[Message] = []

        # System prompt (to be set by subclasses)
        self._system_prompt: str = ""

    @property
    def system_prompt(self) -> str:
        """Get the agent's system prompt."""
        return self._system_prompt

    @system_prompt.setter
    def system_prompt(self, value: str) -> None:
        """Set the agent's system prompt."""
        self._system_prompt = value

    async def initialize(self) -> None:
        """
        Initialize the agent.

        Called once when the agent is created.
        Subclasses can override to perform custom initialization.
        """
        self.logger.info("Agent initializing")
        self.state = AgentState.IDLE
        self.logger.info("Agent initialized")

    async def shutdown(self) -> None:
        """
        Shutdown the agent.

        Called when the agent is being stopped.
        Subclasses can override to perform cleanup.
        """
        self.logger.info("Agent shutting down")
        self.state = AgentState.STOPPED
        self.logger.info("Agent stopped")

    @abstractmethod
    async def execute(self, message: AgentMessage) -> AgentResult:
        """
        Execute the agent's primary function.

        This is the main entry point for agent execution.
        Subclasses must implement this method.

        Args:
            message: The message containing the task to execute

        Returns:
            AgentResult with the execution outcome
        """
        pass

    @abstractmethod
    async def reflect(self, result: AgentResult) -> Reflection:
        """
        Reflect on the agent's performance.

        Called after task execution to assess quality and learn.
        Subclasses must implement this method.

        Args:
            result: The result of the task execution

        Returns:
            Reflection with self-assessment
        """
        pass

    async def can_handle(self, task: Task) -> float:
        """
        Assess ability to handle a task.

        Returns a confidence score between 0 and 1.

        Args:
            task: The task to assess

        Returns:
            Confidence score (0-1)
        """
        # Default implementation - subclasses should override
        return 0.5

    async def _call_llm(
        self,
        user_message: str,
        *,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        include_history: bool = True,
    ) -> str:
        """
        Call the LLM with a message.

        Args:
            user_message: The user/task message
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            include_history: Whether to include conversation history

        Returns:
            The LLM's response content
        """
        messages: list[Message] = []

        # Add system prompt
        if self._system_prompt:
            messages.append(Message(role=MessageRole.SYSTEM, content=self._system_prompt))

        # Add conversation history
        if include_history:
            messages.extend(self._conversation)

        # Add current message
        user_msg = Message(role=MessageRole.USER, content=user_message)
        messages.append(user_msg)

        # Call LLM
        completion = await self.provider.complete(
            messages,
            temperature=temperature,
            max_tokens=max_tokens or self.constraints.max_tokens_per_request,
        )

        # Update conversation history
        self._conversation.append(user_msg)
        self._conversation.append(
            Message(role=MessageRole.ASSISTANT, content=completion.content)
        )

        # Update metrics
        self.metrics.total_tokens_used += completion.total_tokens
        self.metrics.last_active_at = utc_now()

        return completion.content

    def clear_conversation(self) -> None:
        """Clear the conversation history."""
        self._conversation = []

    def _create_result(
        self,
        task_id: str,
        *,
        success: bool,
        result: Any = None,
        error: str | None = None,
        confidence: float = 0.0,
        quality_score: float = 0.0,
        tokens_used: int = 0,
        execution_time: float = 0.0,
    ) -> AgentResult:
        """Create an AgentResult with common fields filled in."""
        return AgentResult(
            task_id=task_id,
            agent_id=self.id,
            agent_type=self.agent_type.value,
            success=success,
            result=result,
            error=error,
            confidence=confidence,
            quality_score=quality_score,
            tokens_used=tokens_used,
            execution_time_seconds=execution_time,
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert agent state to dictionary."""
        return {
            "id": self.id,
            "type": self.agent_type.value,
            "name": self.name,
            "state": self.state.value,
            "provider": self.provider.name,
            "model": self.provider.model,
            "metrics": {
                "tasks_completed": self.metrics.tasks_completed,
                "tasks_failed": self.metrics.tasks_failed,
                "total_tokens_used": self.metrics.total_tokens_used,
                "created_at": self.metrics.created_at.isoformat(),
                "last_active_at": self.metrics.last_active_at.isoformat(),
            },
        }


class SimpleAgent(BaseAgent):
    """
    A simple agent implementation for basic tasks.

    Can be used directly or as a template for more complex agents.
    """

    def __init__(
        self,
        agent_type: AgentType,
        provider: LLMProvider,
        system_prompt: str,
        name: str | None = None,
        constraints: AgentConstraints | None = None,
    ):
        super().__init__(agent_type, provider, name, constraints)
        self._system_prompt = system_prompt

    async def execute(self, message: AgentMessage) -> AgentResult:
        """Execute a simple task using the LLM."""
        import time

        start_time = time.time()
        self.state = AgentState.BUSY

        try:
            task = message.task
            if not task:
                return self._create_result(
                    task_id=message.task_id or "",
                    success=False,
                    error="No task provided in message",
                )

            # Build prompt from task
            prompt = self._build_prompt(task, message.content)

            # Call LLM
            initial_tokens = self.metrics.total_tokens_used
            response = await self._call_llm(prompt)
            tokens_used = self.metrics.total_tokens_used - initial_tokens

            execution_time = time.time() - start_time

            # Update metrics
            self.metrics.tasks_completed += 1
            self.metrics.total_execution_time += execution_time

            self.state = AgentState.IDLE

            return self._create_result(
                task_id=task.id,
                success=True,
                result=response,
                confidence=0.8,  # Default confidence
                quality_score=0.8,  # Default quality
                tokens_used=tokens_used,
                execution_time=execution_time,
            )

        except Exception as e:
            self.logger.error("Task execution failed", error=str(e))
            self.metrics.tasks_failed += 1
            self.state = AgentState.ERROR

            return self._create_result(
                task_id=message.task_id or "",
                success=False,
                error=str(e),
                execution_time=time.time() - start_time,
            )

    async def reflect(self, result: AgentResult) -> Reflection:
        """Reflect on task execution."""
        reflection_prompt = f"""
Reflect on the following task execution:

Task ID: {result.task_id}
Success: {result.success}
Result: {result.result}
Error: {result.error}
Confidence: {result.confidence}
Execution Time: {result.execution_time_seconds:.2f}s

Provide a brief self-assessment including:
1. What went well
2. What could be improved
3. Key lessons learned
"""

        response = await self._call_llm(reflection_prompt, include_history=False)

        return Reflection(
            agent_id=self.id,
            task_id=result.task_id,
            performance_score=result.quality_score,
            lessons_learned=[response],
            successes=["Task completed"] if result.success else [],
            failures=[] if result.success else [result.error or "Unknown error"],
        )

    def _build_prompt(self, task: Task, context: dict[str, Any]) -> str:
        """Build a prompt from task and context."""
        prompt_parts = [
            f"## Task\n{task.description}",
            f"\n## Objective\n{task.objective}" if task.objective else "",
            f"\n## Expected Output\n{task.expected_output}" if task.expected_output else "",
        ]

        if context:
            prompt_parts.append(f"\n## Additional Context\n{context}")

        if task.constraints:
            prompt_parts.append(
                f"\n## Constraints\n"
                f"- Max tokens: {task.constraints.max_tokens}\n"
                f"- Risk level: {task.constraints.risk_level}"
            )

        return "\n".join(filter(None, prompt_parts))
