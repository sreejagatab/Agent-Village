"""
Semantic Memory - What is known.

Stores facts, knowledge, and conceptual relationships.
Uses vector embeddings for similarity search.
"""

from dataclasses import dataclass, field
from typing import Any

import structlog

from src.memory.base import (
    InMemoryStore,
    MemoryEntry,
    MemoryQuery,
    MemorySearchResult,
    MemoryStore,
    MemoryType,
)

logger = structlog.get_logger()


@dataclass
class KnowledgeItem:
    """A piece of knowledge."""

    fact: str
    domain: str = "general"  # Domain/category of knowledge
    confidence: float = 1.0  # How confident we are in this fact
    source: str = ""  # Where this knowledge came from
    related_concepts: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "fact": self.fact,
            "domain": self.domain,
            "confidence": self.confidence,
            "source": self.source,
            "related_concepts": self.related_concepts,
        }


class SemanticMemory(MemoryStore):
    """
    Semantic memory store.

    Optimized for knowledge retrieval and similarity search.
    Supports both in-memory and Qdrant vector backends.
    """

    def __init__(
        self,
        backend: MemoryStore | None = None,
        use_vector_store: bool = False,
    ):
        if use_vector_store:
            from src.memory.vector_store import QdrantVectorStore
            self._backend = backend or QdrantVectorStore()
            self._use_vectors = True
        else:
            self._backend = backend or InMemoryStore()
            self._use_vectors = False
        self.logger = logger.bind(memory_type="semantic")

    async def store(self, entry: MemoryEntry) -> str:
        """Store a semantic memory."""
        entry.memory_type = MemoryType.SEMANTIC
        return await self._backend.store(entry)

    async def get(self, entry_id: str) -> MemoryEntry | None:
        return await self._backend.get(entry_id)

    async def query(self, query: MemoryQuery) -> MemorySearchResult:
        query.memory_types = [MemoryType.SEMANTIC]
        return await self._backend.query(query)

    async def update(self, entry_id: str, updates: dict[str, Any]) -> bool:
        return await self._backend.update(entry_id, updates)

    async def delete(self, entry_id: str) -> bool:
        return await self._backend.delete(entry_id)

    async def store_knowledge(
        self,
        item: KnowledgeItem,
        goal_id: str | None = None,
        agent_id: str | None = None,
    ) -> str:
        """
        Store a knowledge item.

        Args:
            item: Knowledge to store
            goal_id: Associated goal
            agent_id: Agent that learned this

        Returns:
            Memory entry ID
        """
        entry = MemoryEntry(
            memory_type=MemoryType.SEMANTIC,
            content=item.to_dict(),
            summary=item.fact,
            goal_id=goal_id,
            agent_id=agent_id,
            importance_score=item.confidence,
            tags=[item.domain] + item.related_concepts,
            metadata={"source": item.source},
        )

        return await self.store(entry)

    async def search_knowledge(
        self,
        query_text: str,
        domain: str | None = None,
        min_confidence: float = 0.0,
        limit: int = 10,
    ) -> list[MemoryEntry]:
        """
        Search for relevant knowledge.

        Args:
            query_text: Search query
            domain: Filter by domain
            min_confidence: Minimum confidence threshold
            limit: Maximum results

        Returns:
            Relevant knowledge entries
        """
        tags = [domain] if domain else None

        query = MemoryQuery(
            query_text=query_text,
            memory_types=[MemoryType.SEMANTIC],
            tags=tags,
            min_importance=min_confidence,
            limit=limit,
            sort_by="importance_score",
            sort_order="desc",
        )

        result = await self.query(query)
        return result.entries

    async def get_related_concepts(
        self,
        concept: str,
        limit: int = 10,
    ) -> list[MemoryEntry]:
        """
        Get knowledge related to a concept.

        Args:
            concept: Concept to find relations for
            limit: Maximum results

        Returns:
            Related knowledge entries
        """
        query = MemoryQuery(
            memory_types=[MemoryType.SEMANTIC],
            tags=[concept],
            limit=limit,
        )

        result = await self.query(query)
        return result.entries

    async def update_confidence(
        self,
        entry_id: str,
        new_confidence: float,
    ) -> bool:
        """Update confidence in a knowledge item."""
        return await self.update(
            entry_id,
            {"importance_score": new_confidence},
        )

    async def semantic_search(
        self,
        query_text: str,
        limit: int = 10,
        min_score: float = 0.5,
    ) -> list[tuple[MemoryEntry, float]]:
        """
        Perform semantic similarity search using vector embeddings.

        Args:
            query_text: Text to search for
            limit: Maximum results
            min_score: Minimum similarity score (0-1)

        Returns:
            List of (entry, score) tuples sorted by relevance
        """
        if self._use_vectors:
            from src.memory.vector_store import QdrantVectorStore

            if isinstance(self._backend, QdrantVectorStore):
                results = await self._backend.semantic_search(
                    query_text=query_text,
                    memory_type=MemoryType.SEMANTIC,
                    limit=limit,
                    min_score=min_score,
                )
                return [(r.entry, r.score) for r in results]

        # Fallback to text search
        entries = await self.search_knowledge(query_text, limit=limit)
        return [(e, 0.5) for e in entries]


async def create_semantic_memory(use_vectors: bool = True) -> SemanticMemory:
    """
    Factory function to create semantic memory with proper initialization.

    Args:
        use_vectors: Whether to use vector embeddings (requires Qdrant)

    Returns:
        Initialized SemanticMemory instance
    """
    return SemanticMemory(use_vector_store=use_vectors)
