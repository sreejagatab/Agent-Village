"""
OpenAI LLM Provider.

Implements the LLMProvider interface for GPT models.
"""

import json
from typing import Any, AsyncIterator

import structlog
import tiktoken
from openai import AsyncOpenAI

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


class OpenAIProvider(LLMProvider):
    """
    OpenAI GPT provider implementation.

    Supports GPT-4o and GPT-4o-mini models.
    """

    def __init__(self, model: str | None = None):
        settings = get_settings()
        api_key = settings.llm.openai_api_key

        if api_key is None:
            raise ValueError("OpenAI API key not configured")

        self.client = AsyncOpenAI(api_key=api_key.get_secret_value())

        # Default to GPT-4o if no model specified
        if model is None:
            model = settings.llm.openai_model_gpt4

        super().__init__(name="openai", model=model)

        # Use appropriate tokenizer for the model
        try:
            self._tokenizer = tiktoken.encoding_for_model(model)
        except KeyError:
            self._tokenizer = tiktoken.get_encoding("cl100k_base")

    def _convert_messages(self, messages: list[Message]) -> list[dict[str, Any]]:
        """Convert messages to OpenAI format."""
        converted = []

        for msg in messages:
            openai_msg: dict[str, Any] = {
                "role": msg.role.value,
                "content": msg.content,
            }

            if msg.name:
                openai_msg["name"] = msg.name

            if msg.tool_call_id:
                openai_msg["tool_call_id"] = msg.tool_call_id

            if msg.tool_calls:
                openai_msg["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.name,
                            "arguments": json.dumps(tc.arguments),
                        },
                    }
                    for tc in msg.tool_calls
                ]

            converted.append(openai_msg)

        return converted

    def _convert_tools(self, tools: list[ToolDefinition]) -> list[dict[str, Any]]:
        """Convert tool definitions to OpenAI format."""
        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters,
                },
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
        """Generate a completion using GPT."""
        converted_messages = self._convert_messages(messages)

        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": converted_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        if tools:
            kwargs["tools"] = self._convert_tools(tools)
            if tool_choice:
                if tool_choice == "auto":
                    kwargs["tool_choice"] = "auto"
                elif tool_choice == "none":
                    kwargs["tool_choice"] = "none"
                else:
                    kwargs["tool_choice"] = {
                        "type": "function",
                        "function": {"name": tool_choice},
                    }

        if stop:
            kwargs["stop"] = stop

        self.logger.debug("Calling OpenAI API", model=self.model)

        response = await self.client.chat.completions.create(**kwargs)

        choice = response.choices[0]
        message = choice.message

        # Extract tool calls
        tool_calls = []
        if message.tool_calls:
            for tc in message.tool_calls:
                tool_calls.append(
                    ToolCall(
                        id=tc.id,
                        name=tc.function.name,
                        arguments=json.loads(tc.function.arguments)
                        if tc.function.arguments
                        else {},
                    )
                )

        return Completion(
            content=message.content or "",
            tool_calls=tool_calls,
            finish_reason=choice.finish_reason or "stop",
            prompt_tokens=response.usage.prompt_tokens if response.usage else 0,
            completion_tokens=response.usage.completion_tokens if response.usage else 0,
            total_tokens=response.usage.total_tokens if response.usage else 0,
            model=self.model,
            provider="openai",
        )

    async def stream(
        self,
        messages: list[Message],
        *,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        stop: list[str] | None = None,
    ) -> AsyncIterator[str]:
        """Stream a completion from GPT."""
        converted_messages = self._convert_messages(messages)

        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": converted_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": True,
        }

        if stop:
            kwargs["stop"] = stop

        stream = await self.client.chat.completions.create(**kwargs)

        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    def count_tokens(self, text: str) -> int:
        """Count tokens using tiktoken."""
        return len(self._tokenizer.encode(text))

    def supports_function_calling(self) -> bool:
        """GPT-4 supports function calling."""
        return True

    def supports_vision(self) -> bool:
        """GPT-4o supports vision."""
        return "gpt-4o" in self.model or "gpt-4-vision" in self.model

    async def health_check(self) -> bool:
        """Check if OpenAI API is available."""
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                max_tokens=10,
                messages=[{"role": "user", "content": "Hi"}],
            )
            return response.choices is not None
        except Exception as e:
            self.logger.error("OpenAI health check failed", error=str(e))
            return False


def create_openai_providers() -> dict[str, OpenAIProvider]:
    """
    Create all OpenAI provider variants.

    Returns:
        Dictionary of provider key -> provider instance
    """
    settings = get_settings()
    providers = {}

    if settings.llm.openai_api_key:
        try:
            providers["openai_gpt4"] = OpenAIProvider(
                model=settings.llm.openai_model_gpt4
            )
            providers["openai_gpt4_mini"] = OpenAIProvider(
                model=settings.llm.openai_model_gpt4_mini
            )
            logger.info("OpenAI providers created", models=list(providers.keys()))
        except Exception as e:
            logger.error("Failed to create OpenAI providers", error=str(e))

    return providers
