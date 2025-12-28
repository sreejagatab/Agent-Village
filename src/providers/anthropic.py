"""
Anthropic (Claude) LLM Provider.

Implements the LLMProvider interface for Claude models.
"""

import json
from typing import Any, AsyncIterator

import anthropic
import structlog
import tiktoken

from src.config import get_settings
from src.providers.base import (
    Completion,
    LLMProvider,
    Message,
    MessageRole,
    ToolCall,
    ToolDefinition,
)

logger = structlog.get_logger()


class AnthropicProvider(LLMProvider):
    """
    Anthropic Claude provider implementation.

    Supports Claude Opus, Sonnet, and Haiku models.
    """

    def __init__(self, model: str | None = None):
        settings = get_settings()
        api_key = settings.llm.anthropic_api_key

        if api_key is None:
            raise ValueError("Anthropic API key not configured")

        self.client = anthropic.AsyncAnthropic(api_key=api_key.get_secret_value())

        # Default to Sonnet if no model specified
        if model is None:
            model = settings.llm.anthropic_model_sonnet

        super().__init__(name="anthropic", model=model)

        # Use cl100k_base as approximation for token counting
        self._tokenizer = tiktoken.get_encoding("cl100k_base")

    def _convert_messages(
        self, messages: list[Message]
    ) -> tuple[str | None, list[dict[str, Any]]]:
        """
        Convert messages to Anthropic format.

        Anthropic uses a separate system parameter, so we extract it.

        Returns:
            Tuple of (system_message, converted_messages)
        """
        system_message = None
        converted = []

        for msg in messages:
            if msg.role == MessageRole.SYSTEM:
                system_message = msg.content
                continue

            anthropic_msg: dict[str, Any] = {"role": msg.role.value}

            if msg.role == MessageRole.TOOL:
                # Tool results in Anthropic format
                anthropic_msg["role"] = "user"
                anthropic_msg["content"] = [
                    {
                        "type": "tool_result",
                        "tool_use_id": msg.tool_call_id,
                        "content": msg.content,
                    }
                ]
            elif msg.tool_calls:
                # Assistant message with tool calls
                content = []
                if msg.content:
                    content.append({"type": "text", "text": msg.content})
                for tc in msg.tool_calls:
                    content.append(
                        {
                            "type": "tool_use",
                            "id": tc.id,
                            "name": tc.name,
                            "input": tc.arguments,
                        }
                    )
                anthropic_msg["content"] = content
            else:
                anthropic_msg["content"] = msg.content

            converted.append(anthropic_msg)

        return system_message, converted

    def _convert_tools(self, tools: list[ToolDefinition]) -> list[dict[str, Any]]:
        """Convert tool definitions to Anthropic format."""
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.parameters,
            }
            for tool in tools
        ]

    async def complete(
        self,
        messages: list[Message],
        *,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        tools: list[ToolDefinition] | None = None,
        tool_choice: str | None = None,
        stop: list[str] | None = None,
    ) -> Completion:
        """Generate a completion using Claude."""
        system_message, converted_messages = self._convert_messages(messages)

        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": converted_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        if system_message:
            kwargs["system"] = system_message

        if tools:
            kwargs["tools"] = self._convert_tools(tools)
            if tool_choice:
                if tool_choice == "auto":
                    kwargs["tool_choice"] = {"type": "auto"}
                elif tool_choice == "none":
                    kwargs["tool_choice"] = {"type": "none"}
                else:
                    kwargs["tool_choice"] = {"type": "tool", "name": tool_choice}

        if stop:
            kwargs["stop_sequences"] = stop

        self.logger.debug("Calling Anthropic API", model=self.model)

        response = await self.client.messages.create(**kwargs)

        # Extract content and tool calls
        content_parts = []
        tool_calls = []

        for block in response.content:
            if block.type == "text":
                content_parts.append(block.text)
            elif block.type == "tool_use":
                tool_calls.append(
                    ToolCall(
                        id=block.id,
                        name=block.name,
                        arguments=block.input if isinstance(block.input, dict) else {},
                    )
                )

        return Completion(
            content="\n".join(content_parts),
            tool_calls=tool_calls,
            finish_reason=response.stop_reason or "stop",
            prompt_tokens=response.usage.input_tokens,
            completion_tokens=response.usage.output_tokens,
            total_tokens=response.usage.input_tokens + response.usage.output_tokens,
            model=self.model,
            provider="anthropic",
        )

    async def stream(
        self,
        messages: list[Message],
        *,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        stop: list[str] | None = None,
    ) -> AsyncIterator[str]:
        """Stream a completion from Claude."""
        system_message, converted_messages = self._convert_messages(messages)

        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": converted_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        if system_message:
            kwargs["system"] = system_message

        if stop:
            kwargs["stop_sequences"] = stop

        async with self.client.messages.stream(**kwargs) as stream:
            async for text in stream.text_stream:
                yield text

    def count_tokens(self, text: str) -> int:
        """Count tokens using tiktoken approximation."""
        return len(self._tokenizer.encode(text))

    def supports_function_calling(self) -> bool:
        """Claude supports function calling."""
        return True

    def supports_vision(self) -> bool:
        """Claude supports vision."""
        return True

    async def health_check(self) -> bool:
        """Check if Anthropic API is available."""
        try:
            # Simple test completion
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=10,
                messages=[{"role": "user", "content": "Hi"}],
            )
            return response.content is not None
        except Exception as e:
            self.logger.error("Anthropic health check failed", error=str(e))
            return False


def create_anthropic_providers() -> dict[str, AnthropicProvider]:
    """
    Create all Anthropic provider variants.

    Returns:
        Dictionary of provider key -> provider instance
    """
    settings = get_settings()
    providers = {}

    if settings.llm.anthropic_api_key:
        try:
            providers["anthropic_opus"] = AnthropicProvider(
                model=settings.llm.anthropic_model_opus
            )
            providers["anthropic_sonnet"] = AnthropicProvider(
                model=settings.llm.anthropic_model_sonnet
            )
            providers["anthropic_haiku"] = AnthropicProvider(
                model=settings.llm.anthropic_model_haiku
            )
            logger.info("Anthropic providers created", models=list(providers.keys()))
        except Exception as e:
            logger.error("Failed to create Anthropic providers", error=str(e))

    return providers
