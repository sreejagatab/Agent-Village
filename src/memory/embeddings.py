"""
Embedding generation for semantic memory.

Provides vector embeddings for similarity search using multiple providers.
"""

from abc import ABC, abstractmethod
from typing import Any

import httpx
import structlog

from src.config import get_settings

logger = structlog.get_logger()


class EmbeddingProvider(ABC):
    """Abstract base class for embedding providers."""

    @abstractmethod
    async def embed(self, text: str) -> list[float]:
        """Generate embedding for a single text."""
        pass

    @abstractmethod
    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts."""
        pass

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Return the embedding dimension."""
        pass


class OpenAIEmbedding(EmbeddingProvider):
    """OpenAI embedding provider using text-embedding-3-small."""

    def __init__(self, api_key: str | None = None, model: str = "text-embedding-3-small"):
        settings = get_settings()
        self.api_key = api_key or (
            settings.llm.openai_api_key.get_secret_value()
            if settings.llm.openai_api_key
            else None
        )
        self.model = model
        self._dimension = 1536  # Default for text-embedding-3-small

        if not self.api_key:
            raise ValueError("OpenAI API key not configured")

        self.client = httpx.AsyncClient(
            base_url="https://api.openai.com/v1",
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=30.0,
        )
        self.logger = logger.bind(provider="openai_embedding")

    async def embed(self, text: str) -> list[float]:
        """Generate embedding for a single text."""
        embeddings = await self.embed_batch([text])
        return embeddings[0]

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts."""
        response = await self.client.post(
            "/embeddings",
            json={
                "input": texts,
                "model": self.model,
            },
        )
        response.raise_for_status()

        data = response.json()
        embeddings = [item["embedding"] for item in data["data"]]

        return embeddings

    @property
    def dimension(self) -> int:
        return self._dimension

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()


class OllamaEmbedding(EmbeddingProvider):
    """Ollama embedding provider for local embeddings."""

    def __init__(
        self,
        base_url: str | None = None,
        model: str = "nomic-embed-text",
    ):
        settings = get_settings()
        self.base_url = base_url or settings.llm.ollama_base_url
        self.model = model
        self._dimension = 768  # Default for nomic-embed-text

        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=60.0,
        )
        self.logger = logger.bind(provider="ollama_embedding")

    async def embed(self, text: str) -> list[float]:
        """Generate embedding for a single text."""
        response = await self.client.post(
            "/api/embeddings",
            json={
                "model": self.model,
                "prompt": text,
            },
        )
        response.raise_for_status()

        data = response.json()
        return data["embedding"]

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts."""
        # Ollama doesn't support batch, so we do it sequentially
        embeddings = []
        for text in texts:
            embedding = await self.embed(text)
            embeddings.append(embedding)
        return embeddings

    @property
    def dimension(self) -> int:
        return self._dimension

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()


class MockEmbedding(EmbeddingProvider):
    """Mock embedding provider for testing."""

    def __init__(self, dimension: int = 384):
        self._dimension = dimension

    async def embed(self, text: str) -> list[float]:
        """Generate a deterministic mock embedding based on text hash."""
        import hashlib

        # Create deterministic embedding from text hash
        text_hash = hashlib.md5(text.encode()).hexdigest()
        embedding = []

        for i in range(0, min(len(text_hash), self._dimension), 2):
            val = int(text_hash[i:i+2], 16) / 255.0 - 0.5
            embedding.append(val)

        # Pad to dimension
        while len(embedding) < self._dimension:
            embedding.append(0.0)

        return embedding[:self._dimension]

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts."""
        return [await self.embed(text) for text in texts]

    @property
    def dimension(self) -> int:
        return self._dimension


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Calculate cosine similarity between two vectors."""
    if len(a) != len(b):
        raise ValueError("Vectors must have same dimension")

    dot_product = sum(x * y for x, y in zip(a, b))
    magnitude_a = sum(x * x for x in a) ** 0.5
    magnitude_b = sum(x * x for x in b) ** 0.5

    if magnitude_a == 0 or magnitude_b == 0:
        return 0.0

    return dot_product / (magnitude_a * magnitude_b)


# Global embedding provider
_embedding_provider: EmbeddingProvider | None = None


async def get_embedding_provider() -> EmbeddingProvider:
    """Get the global embedding provider."""
    global _embedding_provider

    if _embedding_provider is None:
        settings = get_settings()

        # Try OpenAI first, then Ollama, then Mock
        if settings.llm.openai_api_key:
            try:
                _embedding_provider = OpenAIEmbedding()
                logger.info("Using OpenAI embeddings")
            except Exception as e:
                logger.warning("Failed to initialize OpenAI embeddings", error=str(e))

        if _embedding_provider is None:
            try:
                _embedding_provider = OllamaEmbedding()
                # Test if Ollama is available
                await _embedding_provider.embed("test")
                logger.info("Using Ollama embeddings")
            except Exception as e:
                logger.warning("Failed to initialize Ollama embeddings", error=str(e))
                _embedding_provider = None

        if _embedding_provider is None:
            _embedding_provider = MockEmbedding()
            logger.warning("Using mock embeddings - not suitable for production")

    return _embedding_provider
