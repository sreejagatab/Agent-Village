"""
Vector store implementation using Qdrant.

Provides semantic search capabilities for memory entries.
"""

from dataclasses import dataclass
from typing import Any

import structlog

from src.config import get_settings
from src.memory.base import MemoryEntry, MemoryQuery, MemorySearchResult, MemoryStore, MemoryType
from src.memory.embeddings import EmbeddingProvider, cosine_similarity, get_embedding_provider

logger = structlog.get_logger()


@dataclass
class VectorSearchResult:
    """Result of a vector similarity search."""

    entry: MemoryEntry
    score: float  # Similarity score (0-1)


class QdrantVectorStore(MemoryStore):
    """
    Vector store using Qdrant for semantic search.

    Combines vector similarity with metadata filtering.
    """

    def __init__(
        self,
        collection_name: str | None = None,
        url: str | None = None,
        embedding_provider: EmbeddingProvider | None = None,
    ):
        settings = get_settings()
        self.url = url or settings.memory.qdrant_url
        self.collection_name = collection_name or settings.memory.qdrant_collection
        self._embedding_provider = embedding_provider
        self._client = None
        self.logger = logger.bind(component="qdrant_store")

    async def _get_client(self):
        """Get or create Qdrant client."""
        if self._client is None:
            try:
                from qdrant_client import AsyncQdrantClient
                from qdrant_client.models import Distance, VectorParams

                self._client = AsyncQdrantClient(url=self.url)

                # Ensure collection exists
                collections = await self._client.get_collections()
                collection_names = [c.name for c in collections.collections]

                if self.collection_name not in collection_names:
                    embedding = await self._get_embedding_provider()
                    await self._client.create_collection(
                        collection_name=self.collection_name,
                        vectors_config=VectorParams(
                            size=embedding.dimension,
                            distance=Distance.COSINE,
                        ),
                    )
                    self.logger.info(
                        "Created Qdrant collection",
                        collection=self.collection_name,
                        dimension=embedding.dimension,
                    )

            except ImportError:
                self.logger.warning("Qdrant client not installed, using in-memory fallback")
                self._client = None
            except Exception as e:
                self.logger.error("Failed to connect to Qdrant", error=str(e))
                self._client = None

        return self._client

    async def _get_embedding_provider(self) -> EmbeddingProvider:
        """Get embedding provider."""
        if self._embedding_provider is None:
            self._embedding_provider = await get_embedding_provider()
        return self._embedding_provider

    async def store(self, entry: MemoryEntry) -> str:
        """Store a memory entry with vector embedding."""
        client = await self._get_client()

        # Generate embedding if not present
        if entry.embedding is None:
            embedding = await self._get_embedding_provider()
            text_to_embed = entry.summary or str(entry.content)
            entry.embedding = await embedding.embed(text_to_embed)

        if client:
            try:
                from qdrant_client.models import PointStruct

                await client.upsert(
                    collection_name=self.collection_name,
                    points=[
                        PointStruct(
                            id=entry.id,
                            vector=entry.embedding,
                            payload={
                                "memory_type": entry.memory_type.value,
                                "content": entry.content,
                                "summary": entry.summary,
                                "goal_id": entry.goal_id,
                                "task_id": entry.task_id,
                                "agent_id": entry.agent_id,
                                "tags": entry.tags,
                                "importance_score": entry.importance_score,
                                "created_at": entry.created_at.isoformat(),
                            },
                        )
                    ],
                )
            except Exception as e:
                self.logger.error("Failed to store in Qdrant", error=str(e))

        return entry.id

    async def get(self, entry_id: str) -> MemoryEntry | None:
        """Get a memory entry by ID."""
        client = await self._get_client()

        if client:
            try:
                results = await client.retrieve(
                    collection_name=self.collection_name,
                    ids=[entry_id],
                    with_vectors=True,
                )

                if results:
                    point = results[0]
                    return self._point_to_entry(point)
            except Exception as e:
                self.logger.error("Failed to get from Qdrant", error=str(e))

        return None

    async def query(self, query: MemoryQuery) -> MemorySearchResult:
        """Query memories using vector similarity and filters."""
        import time

        start_time = time.time()
        client = await self._get_client()
        entries = []

        if client and (query.query_text or query.query_embedding):
            try:
                # Generate query embedding if text provided
                query_vector = query.query_embedding
                if query_vector is None and query.query_text:
                    embedding = await self._get_embedding_provider()
                    query_vector = await embedding.embed(query.query_text)

                # Build filter
                filter_conditions = []

                if query.memory_types:
                    filter_conditions.append({
                        "key": "memory_type",
                        "match": {"any": [t.value for t in query.memory_types]},
                    })

                if query.goal_id:
                    filter_conditions.append({
                        "key": "goal_id",
                        "match": {"value": query.goal_id},
                    })

                if query.tags:
                    filter_conditions.append({
                        "key": "tags",
                        "match": {"any": query.tags},
                    })

                if query.min_importance > 0:
                    filter_conditions.append({
                        "key": "importance_score",
                        "range": {"gte": query.min_importance},
                    })

                from qdrant_client.models import Filter, FieldCondition, MatchAny, MatchValue, Range

                qdrant_filter = None
                if filter_conditions:
                    conditions = []
                    for cond in filter_conditions:
                        if "match" in cond:
                            if "any" in cond["match"]:
                                conditions.append(
                                    FieldCondition(
                                        key=cond["key"],
                                        match=MatchAny(any=cond["match"]["any"]),
                                    )
                                )
                            else:
                                conditions.append(
                                    FieldCondition(
                                        key=cond["key"],
                                        match=MatchValue(value=cond["match"]["value"]),
                                    )
                                )
                        elif "range" in cond:
                            conditions.append(
                                FieldCondition(
                                    key=cond["key"],
                                    range=Range(**cond["range"]),
                                )
                            )

                    qdrant_filter = Filter(must=conditions)

                # Search
                results = await client.search(
                    collection_name=self.collection_name,
                    query_vector=query_vector,
                    query_filter=qdrant_filter,
                    limit=query.limit,
                    offset=query.offset,
                    with_vectors=True,
                )

                entries = [self._point_to_entry(r) for r in results]

            except Exception as e:
                self.logger.error("Qdrant search failed", error=str(e))

        query_time = (time.time() - start_time) * 1000

        return MemorySearchResult(
            entries=entries,
            total_count=len(entries),
            query_time_ms=query_time,
        )

    async def update(self, entry_id: str, updates: dict[str, Any]) -> bool:
        """Update a memory entry."""
        client = await self._get_client()

        if client:
            try:
                await client.set_payload(
                    collection_name=self.collection_name,
                    payload=updates,
                    points=[entry_id],
                )
                return True
            except Exception as e:
                self.logger.error("Failed to update in Qdrant", error=str(e))

        return False

    async def delete(self, entry_id: str) -> bool:
        """Delete a memory entry."""
        client = await self._get_client()

        if client:
            try:
                await client.delete(
                    collection_name=self.collection_name,
                    points_selector=[entry_id],
                )
                return True
            except Exception as e:
                self.logger.error("Failed to delete from Qdrant", error=str(e))

        return False

    async def semantic_search(
        self,
        query_text: str,
        memory_type: MemoryType | None = None,
        limit: int = 10,
        min_score: float = 0.5,
    ) -> list[VectorSearchResult]:
        """
        Perform semantic similarity search.

        Args:
            query_text: Text to search for
            memory_type: Optional filter by type
            limit: Maximum results
            min_score: Minimum similarity score

        Returns:
            List of results with similarity scores
        """
        embedding = await self._get_embedding_provider()
        query_vector = await embedding.embed(query_text)

        query = MemoryQuery(
            query_embedding=query_vector,
            memory_types=[memory_type] if memory_type else None,
            limit=limit,
        )

        result = await self.query(query)

        # Filter by score and add scores
        # Note: In production, Qdrant returns scores with results
        vector_results = []
        for entry in result.entries:
            if entry.embedding:
                score = cosine_similarity(query_vector, entry.embedding)
                if score >= min_score:
                    vector_results.append(VectorSearchResult(entry=entry, score=score))

        # Sort by score
        vector_results.sort(key=lambda x: x.score, reverse=True)

        return vector_results[:limit]

    def _point_to_entry(self, point: Any) -> MemoryEntry:
        """Convert Qdrant point to MemoryEntry."""
        from datetime import datetime

        payload = point.payload or {}

        return MemoryEntry(
            id=str(point.id),
            memory_type=MemoryType(payload.get("memory_type", "semantic")),
            content=payload.get("content"),
            summary=payload.get("summary", ""),
            goal_id=payload.get("goal_id"),
            task_id=payload.get("task_id"),
            agent_id=payload.get("agent_id"),
            tags=payload.get("tags", []),
            importance_score=payload.get("importance_score", 0.5),
            embedding=point.vector if hasattr(point, "vector") else None,
        )

    async def close(self) -> None:
        """Close the client connection."""
        if self._client:
            await self._client.close()
            self._client = None
