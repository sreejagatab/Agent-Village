"""LLM Provider abstractions for Agent Village."""

import structlog

from src.providers.base import (
    Completion,
    LLMProvider,
    Message,
    MessageRole,
    ProviderPool,
    ToolCall,
    ToolDefinition,
)
from src.providers.anthropic import AnthropicProvider, create_anthropic_providers
from src.providers.openai import OpenAIProvider, create_openai_providers
from src.providers.ollama import OllamaProvider, create_ollama_provider

logger = structlog.get_logger()

__all__ = [
    "Completion",
    "LLMProvider",
    "Message",
    "MessageRole",
    "ProviderPool",
    "ToolCall",
    "ToolDefinition",
    "AnthropicProvider",
    "OpenAIProvider",
    "OllamaProvider",
    "create_provider_pool",
]


def create_provider_pool() -> ProviderPool:
    """
    Create a fully initialized provider pool with all available providers.

    Attempts to create providers for all configured backends (Anthropic, OpenAI, Ollama).
    Providers that fail to initialize are skipped with a warning.

    Returns:
        ProviderPool with all available providers registered
    """
    pool = ProviderPool()

    # Register Anthropic providers
    try:
        anthropic_providers = create_anthropic_providers()
        for key, provider in anthropic_providers.items():
            pool.register(key, provider)
    except Exception as e:
        logger.warning("Failed to create Anthropic providers", error=str(e))

    # Register OpenAI providers
    try:
        openai_providers = create_openai_providers()
        for key, provider in openai_providers.items():
            pool.register(key, provider)
    except Exception as e:
        logger.warning("Failed to create OpenAI providers", error=str(e))

    # Register Ollama providers
    try:
        ollama_providers = create_ollama_provider()
        for key, provider in ollama_providers.items():
            pool.register(key, provider)
    except Exception as e:
        logger.warning("Failed to create Ollama provider", error=str(e))

    logger.info(
        "Provider pool initialized",
        providers=list(pool.providers.keys()),
        count=len(pool.providers),
    )

    return pool
