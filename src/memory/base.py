"""
Base memory interfaces for Agent Village.

Defines the abstract interfaces for all memory types:
- Episodic: What happened
- Semantic: What is known
- Procedural: How to do things
- Strategic: Why decisions were made
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from src.core.message import generate_id


class MemoryType(str, Enum):
    """Types of memory in the system."""

    EPISODIC = "episodic"  # Events, experiences
    SEMANTIC = "semantic"  # Facts, knowledge
    PROCEDURAL = "procedural"  # Skills, procedures
    STRATEGIC = "strategic"  # Decisions, reasoning


@dataclass
class MemoryEntry:
    """A single memory entry."""

    id: str = field(default_factory=generate_id)
    memory_type: MemoryType = MemoryType.SEMANTIC
    content: Any = None
    summary: str = ""

    # Context
    goal_id: str | None = None
    task_id: str | None = None
    agent_id: str | None = None

    # Metadata
    metadata: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)

    # Importance and relevance
    importance_score: float = 0.5  # 0-1
    access_count: int = 0
    last_accessed: datetime | None = None

    # Embedding for vector search
    embedding: list[float] | None = None

    # Timestamps
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "memory_type": self.memory_type.value,
            "content": self.content,
            "summary": self.summary,
            "goal_id": self.goal_id,
            "task_id": self.task_id,
            "agent_id": self.agent_id,
            "metadata": self.metadata,
            "tags": self.tags,
            "importance_score": self.importance_score,
            "access_count": self.access_count,
            "last_accessed": self.last_accessed.isoformat() if self.last_accessed else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MemoryEntry":
        """Create from dictionary."""
        return cls(
            id=data.get("id", generate_id()),
            memory_type=MemoryType(data.get("memory_type", "semantic")),
            content=data.get("content"),
            summary=data.get("summary", ""),
            goal_id=data.get("goal_id"),
            task_id=data.get("task_id"),
            agent_id=data.get("agent_id"),
            metadata=data.get("metadata", {}),
            tags=data.get("tags", []),
            importance_score=data.get("importance_score", 0.5),
            access_count=data.get("access_count", 0),
        )


@dataclass
class MemoryQuery:
    """Query for searching memories."""

    # Text search
    query_text: str | None = None
    query_embedding: list[float] | None = None

    # Filters
    memory_types: list[MemoryType] | None = None
    goal_id: str | None = None
    task_id: str | None = None
    agent_id: str | None = None
    tags: list[str] | None = None

    # Time range
    created_after: datetime | None = None
    created_before: datetime | None = None

    # Importance
    min_importance: float = 0.0

    # Pagination
    limit: int = 10
    offset: int = 0

    # Sorting
    sort_by: str = "created_at"  # created_at, importance_score, access_count
    sort_order: str = "desc"  # asc, desc


@dataclass
class MemorySearchResult:
    """Result of a memory search."""

    entries: list[MemoryEntry]
    total_count: int
    query_time_ms: float = 0.0


class MemoryStore(ABC):
    """
    Abstract base class for memory storage.

    All memory type implementations inherit from this.
    """

    @abstractmethod
    async def store(self, entry: MemoryEntry) -> str:
        """
        Store a memory entry.

        Args:
            entry: Memory entry to store

        Returns:
            ID of stored entry
        """
        pass

    @abstractmethod
    async def get(self, entry_id: str) -> MemoryEntry | None:
        """
        Get a memory entry by ID.

        Args:
            entry_id: ID of entry to retrieve

        Returns:
            Memory entry or None if not found
        """
        pass

    @abstractmethod
    async def query(self, query: MemoryQuery) -> MemorySearchResult:
        """
        Query memories.

        Args:
            query: Query parameters

        Returns:
            Search results
        """
        pass

    @abstractmethod
    async def update(self, entry_id: str, updates: dict[str, Any]) -> bool:
        """
        Update a memory entry.

        Args:
            entry_id: ID of entry to update
            updates: Fields to update

        Returns:
            True if updated successfully
        """
        pass

    @abstractmethod
    async def delete(self, entry_id: str) -> bool:
        """
        Delete a memory entry.

        Args:
            entry_id: ID of entry to delete

        Returns:
            True if deleted successfully
        """
        pass

    async def record_access(self, entry_id: str) -> None:
        """Record that a memory was accessed."""
        await self.update(
            entry_id,
            {
                "access_count": "+1",
                "last_accessed": datetime.now(timezone.utc),
            },
        )


class InMemoryStore(MemoryStore):
    """Simple in-memory implementation for testing."""

    def __init__(self):
        self._entries: dict[str, MemoryEntry] = {}

    async def store(self, entry: MemoryEntry) -> str:
        self._entries[entry.id] = entry
        return entry.id

    async def get(self, entry_id: str) -> MemoryEntry | None:
        return self._entries.get(entry_id)

    async def query(self, query: MemoryQuery) -> MemorySearchResult:
        results = []

        for entry in self._entries.values():
            # Apply filters
            if query.memory_types and entry.memory_type not in query.memory_types:
                continue
            if query.goal_id and entry.goal_id != query.goal_id:
                continue
            if query.task_id and entry.task_id != query.task_id:
                continue
            if query.agent_id and entry.agent_id != query.agent_id:
                continue
            if query.min_importance and entry.importance_score < query.min_importance:
                continue
            if query.tags and not any(t in entry.tags for t in query.tags):
                continue

            # Text search (simple substring match)
            if query.query_text:
                text_lower = query.query_text.lower()
                content_str = str(entry.content).lower()
                summary_lower = entry.summary.lower()
                if text_lower not in content_str and text_lower not in summary_lower:
                    continue

            results.append(entry)

        # Sort
        reverse = query.sort_order == "desc"
        if query.sort_by == "importance_score":
            results.sort(key=lambda e: e.importance_score, reverse=reverse)
        elif query.sort_by == "access_count":
            results.sort(key=lambda e: e.access_count, reverse=reverse)
        else:
            results.sort(key=lambda e: e.created_at, reverse=reverse)

        # Paginate
        total = len(results)
        results = results[query.offset : query.offset + query.limit]

        return MemorySearchResult(entries=results, total_count=total)

    async def update(self, entry_id: str, updates: dict[str, Any]) -> bool:
        entry = self._entries.get(entry_id)
        if not entry:
            return False

        for key, value in updates.items():
            if key == "access_count" and value == "+1":
                entry.access_count += 1
            elif hasattr(entry, key):
                setattr(entry, key, value)

        entry.updated_at = datetime.now(timezone.utc)
        return True

    async def delete(self, entry_id: str) -> bool:
        if entry_id in self._entries:
            del self._entries[entry_id]
            return True
        return False
