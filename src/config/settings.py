"""
Configuration settings for Agent Village.

Uses pydantic-settings for environment variable loading and validation.
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMProviderSettings(BaseSettings):
    """Settings for LLM providers."""

    model_config = SettingsConfigDict(env_prefix="LLM_")

    # Anthropic (Claude)
    anthropic_api_key: SecretStr | None = Field(default=None, description="Anthropic API key")
    anthropic_model_opus: str = Field(default="claude-opus-4-20250514", description="Claude Opus model")
    anthropic_model_sonnet: str = Field(default="claude-sonnet-4-20250514", description="Claude Sonnet model")
    anthropic_model_haiku: str = Field(default="claude-3-5-haiku-20241022", description="Claude Haiku model")

    # OpenAI
    openai_api_key: SecretStr | None = Field(default=None, description="OpenAI API key")
    openai_model_gpt4: str = Field(default="gpt-4o", description="GPT-4 model")
    openai_model_gpt4_mini: str = Field(default="gpt-4o-mini", description="GPT-4 mini model")

    # Ollama (local)
    ollama_base_url: str = Field(default="http://localhost:11434", description="Ollama base URL")
    ollama_model: str = Field(default="llama3.2", description="Default Ollama model")

    # Default provider
    default_provider: Literal["anthropic", "openai", "ollama"] = Field(
        default="anthropic", description="Default LLM provider"
    )


class SafetySettings(BaseSettings):
    """Safety gate settings."""

    model_config = SettingsConfigDict(env_prefix="SAFETY_")

    max_recursion_depth: int = Field(default=10, ge=1, le=50, description="Maximum recursion depth")
    max_agent_spawns: int = Field(default=50, ge=1, le=500, description="Maximum agent spawns per goal")
    max_tokens_per_task: int = Field(default=100_000, ge=1000, description="Maximum tokens per task")
    max_execution_time_seconds: int = Field(default=3600, ge=60, description="Maximum execution time")
    require_human_approval: list[str] = Field(
        default_factory=lambda: ["deploy", "delete", "payment", "admin"],
        description="Actions requiring human approval",
    )
    allowed_tools: set[str] = Field(
        default_factory=lambda: {"read_file", "write_file", "execute_code", "web_request"},
        description="Allowed tool names",
    )


class MemorySettings(BaseSettings):
    """Memory subsystem settings."""

    model_config = SettingsConfigDict(env_prefix="MEMORY_")

    # PostgreSQL
    postgres_url: str = Field(
        default="postgresql+asyncpg://village:village@localhost:5432/village",
        description="PostgreSQL connection URL",
    )

    # Qdrant (vector DB)
    qdrant_url: str = Field(default="http://localhost:6333", description="Qdrant URL")
    qdrant_collection: str = Field(default="village_memory", description="Qdrant collection name")
    embedding_dimension: int = Field(default=1536, description="Embedding vector dimension")

    # Redis
    redis_url: str = Field(default="redis://localhost:6379/0", description="Redis URL")
    redis_message_ttl: int = Field(default=86400, description="Message TTL in seconds")


class APISettings(BaseSettings):
    """API server settings."""

    model_config = SettingsConfigDict(env_prefix="API_")

    host: str = Field(default="0.0.0.0", description="API host")
    port: int = Field(default=8000, description="API port")
    workers: int = Field(default=4, description="Number of workers")
    reload: bool = Field(default=False, description="Enable auto-reload")
    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:3000"],
        description="CORS allowed origins",
    )


class Settings(BaseSettings):
    """Main application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        extra="ignore",
    )

    # Application
    app_name: str = Field(default="Agent Village", description="Application name")
    environment: Literal["development", "staging", "production"] = Field(
        default="development", description="Environment"
    )
    debug: bool = Field(default=False, description="Debug mode")
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(
        default="INFO", description="Log level"
    )

    # Sub-settings
    llm: LLMProviderSettings = Field(default_factory=LLMProviderSettings)
    safety: SafetySettings = Field(default_factory=SafetySettings)
    memory: MemorySettings = Field(default_factory=MemorySettings)
    api: APISettings = Field(default_factory=APISettings)


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
