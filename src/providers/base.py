"""
Base LLM Provider abstraction.

Defines the interface that all LLM providers must implement.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, AsyncIterator

import structlog

logger = structlog.get_logger()


class MessageRole(str, Enum):
    """Message roles in a conversation."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass
class Message:
    """A message in a conversation."""

    role: MessageRole
    content: str
    name: str | None = None  # For tool messages
    tool_call_id: str | None = None  # For tool responses
    tool_calls: list["ToolCall"] | None = None  # For assistant tool calls

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API calls."""
        result: dict[str, Any] = {
            "role": self.role.value,
            "content": self.content,
        }
        if self.name:
            result["name"] = self.name
        if self.tool_call_id:
            result["tool_call_id"] = self.tool_call_id
        if self.tool_calls:
            result["tool_calls"] = [tc.to_dict() for tc in self.tool_calls]
        return result


@dataclass
class ToolCall:
    """A tool call made by the model."""

    id: str
    name: str
    arguments: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "arguments": self.arguments,
        }


@dataclass
class ToolDefinition:
    """Definition of a tool that can be called."""

    name: str
    description: str
    parameters: dict[str, Any]  # JSON Schema

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API calls."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
        }


@dataclass
class Completion:
    """Result of an LLM completion."""

    content: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    finish_reason: str = "stop"

    # Usage metrics
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

    # Metadata
    model: str = ""
    provider: str = ""

    @property
    def has_tool_calls(self) -> bool:
        """Check if completion includes tool calls."""
        return len(self.tool_calls) > 0


class LLMProvider(ABC):
    """
    Abstract base class for LLM providers.

    All providers (Anthropic, OpenAI, Ollama) must implement this interface.
    """

    def __init__(self, name: str, model: str):
        self.name = name
        self.model = model
        self.logger = logger.bind(provider=name, model=model)

    @abstractmethod
    async def complete(
        self,
        messages: list[Message],
        *,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        tools: list[ToolDefinition] | None = None,
        tool_choice: str | None = None,  # "auto", "none", or specific tool name
        stop: list[str] | None = None,
    ) -> Completion:
        """
        Generate a completion from the model.

        Args:
            messages: Conversation history
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens to generate
            tools: Available tools for function calling
            tool_choice: Tool selection preference
            stop: Stop sequences

        Returns:
            Completion object with content and metadata
        """
        pass

    @abstractmethod
    async def stream(
        self,
        messages: list[Message],
        *,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        stop: list[str] | None = None,
    ) -> AsyncIterator[str]:
        """
        Stream a completion from the model.

        Args:
            messages: Conversation history
            temperature: Sampling temperature
            max_tokens: Maximum tokens
            stop: Stop sequences

        Yields:
            Text chunks as they are generated
        """
        pass

    @abstractmethod
    def count_tokens(self, text: str) -> int:
        """
        Count tokens in a text string.

        Args:
            text: Text to count tokens for

        Returns:
            Number of tokens
        """
        pass

    @abstractmethod
    def supports_function_calling(self) -> bool:
        """
        Check if this provider supports native function calling.

        Returns:
            True if function calling is supported
        """
        pass

    @abstractmethod
    def supports_vision(self) -> bool:
        """
        Check if this provider supports vision/image inputs.

        Returns:
            True if vision is supported
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if the provider is available and working.

        Returns:
            True if healthy
        """
        pass


class ProviderPool:
    """
    Pool of LLM providers with smart routing.

    Routes requests to the best provider based on task type,
    with automatic fallback if a provider fails.
    """

    def __init__(self):
        self.providers: dict[str, LLMProvider] = {}
        self.routing_rules: dict[str, list[str]] = {
            # Agent type -> preferred providers in order
            "governor": ["anthropic_opus", "anthropic_sonnet", "openai_gpt4"],
            "planner": ["anthropic_opus", "anthropic_sonnet", "openai_gpt4"],
            "tool": ["anthropic_sonnet", "openai_gpt4", "ollama"],
            "critic": ["anthropic_sonnet", "openai_gpt4"],
            "memory": ["anthropic_haiku", "ollama", "openai_gpt4_mini"],
            "swarm": ["ollama", "anthropic_haiku", "openai_gpt4_mini"],
            "evolver": ["anthropic_opus", "anthropic_sonnet"],
            "default": ["anthropic_sonnet", "openai_gpt4", "ollama"],
        }
        self.logger = logger.bind(component="provider_pool")

    def register(self, key: str, provider: LLMProvider) -> None:
        """Register a provider with a key."""
        self.providers[key] = provider
        self.logger.info("Provider registered", key=key, model=provider.model)

    def get(self, key: str) -> LLMProvider | None:
        """Get a specific provider by key."""
        return self.providers.get(key)

    async def get_for_agent_type(self, agent_type: str) -> LLMProvider:
        """
        Get the best available provider for an agent type.

        Tries providers in order of preference, falling back if unavailable.

        Args:
            agent_type: Type of agent (governor, planner, tool, etc.)

        Returns:
            Available LLM provider

        Raises:
            RuntimeError: If no providers are available
        """
        preferences = self.routing_rules.get(agent_type, self.routing_rules["default"])

        for provider_key in preferences:
            provider = self.providers.get(provider_key)
            if provider is None:
                continue

            try:
                if await provider.health_check():
                    self.logger.debug(
                        "Selected provider",
                        agent_type=agent_type,
                        provider=provider_key,
                    )
                    return provider
            except Exception as e:
                self.logger.warning(
                    "Provider health check failed",
                    provider=provider_key,
                    error=str(e),
                )
                continue

        # If all preferred providers failed, try any available
        for key, provider in self.providers.items():
            try:
                if await provider.health_check():
                    self.logger.warning(
                        "Using fallback provider",
                        agent_type=agent_type,
                        provider=key,
                    )
                    return provider
            except Exception:
                continue

        raise RuntimeError(f"No available providers for agent type: {agent_type}")

    async def health_check_all(self) -> dict[str, bool]:
        """Check health of all registered providers."""
        results = {}
        for key, provider in self.providers.items():
            try:
                results[key] = await provider.health_check()
            except Exception:
                results[key] = False
        return results
