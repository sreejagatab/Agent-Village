"""
Ollama (Local) LLM Provider.

Implements the LLMProvider interface for locally-hosted models via Ollama.
"""

import json
from typing import Any, AsyncIterator

import httpx
import structlog

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


class OllamaProvider(LLMProvider):
    """
    Ollama local model provider implementation.

    Connects to a locally running Ollama server.
    """

    def __init__(self, model: str | None = None, base_url: str | None = None):
        settings = get_settings()

        self.base_url = base_url or settings.llm.ollama_base_url
        model = model or settings.llm.ollama_model

        super().__init__(name="ollama", model=model)

        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(120.0),  # Longer timeout for local models
        )

    def _convert_messages(self, messages: list[Message]) -> list[dict[str, Any]]:
        """Convert messages to Ollama format."""
        converted = []

        for msg in messages:
            ollama_msg: dict[str, Any] = {
                "role": msg.role.value,
                "content": msg.content,
            }
            converted.append(ollama_msg)

        return converted

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
        """Generate a completion using Ollama."""
        converted_messages = self._convert_messages(messages)

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": converted_messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }

        if stop:
            payload["options"]["stop"] = stop

        # Ollama tool support (experimental in some models)
        if tools and self.supports_function_calling():
            payload["tools"] = [
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

        self.logger.debug("Calling Ollama API", model=self.model)

        response = await self.client.post("/api/chat", json=payload)
        response.raise_for_status()

        data = response.json()

        # Parse tool calls if present
        tool_calls = []
        message = data.get("message", {})
        if "tool_calls" in message:
            for tc in message["tool_calls"]:
                func = tc.get("function", {})
                tool_calls.append(
                    ToolCall(
                        id=tc.get("id", f"call_{len(tool_calls)}"),
                        name=func.get("name", ""),
                        arguments=func.get("arguments", {}),
                    )
                )

        # Estimate token counts (Ollama doesn't always provide these)
        content = message.get("content", "")
        prompt_tokens = data.get("prompt_eval_count", self.count_tokens(str(messages)))
        completion_tokens = data.get("eval_count", self.count_tokens(content))

        return Completion(
            content=content,
            tool_calls=tool_calls,
            finish_reason=data.get("done_reason", "stop"),
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            model=self.model,
            provider="ollama",
        )

    async def stream(
        self,
        messages: list[Message],
        *,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        stop: list[str] | None = None,
    ) -> AsyncIterator[str]:
        """Stream a completion from Ollama."""
        converted_messages = self._convert_messages(messages)

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": converted_messages,
            "stream": True,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }

        if stop:
            payload["options"]["stop"] = stop

        async with self.client.stream("POST", "/api/chat", json=payload) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line:
                    try:
                        data = json.loads(line)
                        if "message" in data and "content" in data["message"]:
                            yield data["message"]["content"]
                    except json.JSONDecodeError:
                        continue

    def count_tokens(self, text: str) -> int:
        """
        Estimate token count.

        Ollama doesn't provide a tokenizer, so we use a rough estimate.
        """
        # Rough estimate: ~4 characters per token for English
        return len(text) // 4

    def supports_function_calling(self) -> bool:
        """
        Check if model supports function calling.

        Only some Ollama models support tools.
        """
        # Models known to support function calling
        tool_models = ["llama3.1", "llama3.2", "mistral", "mixtral", "qwen2"]
        return any(m in self.model.lower() for m in tool_models)

    def supports_vision(self) -> bool:
        """
        Check if model supports vision.

        Only some Ollama models support images.
        """
        vision_models = ["llava", "bakllava", "llama3.2-vision"]
        return any(m in self.model.lower() for m in vision_models)

    async def health_check(self) -> bool:
        """Check if Ollama server is available."""
        try:
            response = await self.client.get("/api/tags")
            if response.status_code == 200:
                # Check if our model is available
                data = response.json()
                models = [m["name"] for m in data.get("models", [])]
                # Check if model is available (with or without tag)
                model_base = self.model.split(":")[0]
                return any(model_base in m for m in models)
            return False
        except Exception as e:
            self.logger.error("Ollama health check failed", error=str(e))
            return False

    async def pull_model(self) -> bool:
        """Pull the model if not available locally."""
        try:
            self.logger.info("Pulling Ollama model", model=self.model)
            response = await self.client.post(
                "/api/pull",
                json={"name": self.model, "stream": False},
                timeout=httpx.Timeout(600.0),  # 10 minute timeout for pulls
            )
            return response.status_code == 200
        except Exception as e:
            self.logger.error("Failed to pull Ollama model", error=str(e))
            return False

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()


def create_ollama_provider() -> dict[str, OllamaProvider]:
    """
    Create Ollama provider.

    Returns:
        Dictionary of provider key -> provider instance
    """
    settings = get_settings()
    providers = {}

    try:
        providers["ollama"] = OllamaProvider(
            model=settings.llm.ollama_model,
            base_url=settings.llm.ollama_base_url,
        )
        logger.info("Ollama provider created", model=settings.llm.ollama_model)
    except Exception as e:
        logger.warning("Failed to create Ollama provider", error=str(e))

    return providers
