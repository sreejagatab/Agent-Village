"""
Episodic Memory - What happened.

Stores events, experiences, and their temporal relationships.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
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
class Episode:
    """An episode in the agent's experience."""

    event_type: str  # goal_started, task_completed, error_occurred, etc.
    description: str
    actors: list[str] = field(default_factory=list)  # Agent IDs involved
    outcome: str = ""  # success, failure, partial
    context: dict[str, Any] = field(default_factory=dict)
    duration_seconds: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_type": self.event_type,
            "description": self.description,
            "actors": self.actors,
            "outcome": self.outcome,
            "context": self.context,
            "duration_seconds": self.duration_seconds,
            "timestamp": self.timestamp.isoformat(),
        }


class EpisodicMemory(MemoryStore):
    """
    Episodic memory store.

    Optimized for temporal queries and event sequences.
    """

    def __init__(self, backend: MemoryStore | None = None):
        self._backend = backend or InMemoryStore()
        self.logger = logger.bind(memory_type="episodic")

    async def store(self, entry: MemoryEntry) -> str:
        """Store an episodic memory."""
        entry.memory_type = MemoryType.EPISODIC
        return await self._backend.store(entry)

    async def get(self, entry_id: str) -> MemoryEntry | None:
        return await self._backend.get(entry_id)

    async def query(self, query: MemoryQuery) -> MemorySearchResult:
        # Force episodic type
        query.memory_types = [MemoryType.EPISODIC]
        return await self._backend.query(query)

    async def update(self, entry_id: str, updates: dict[str, Any]) -> bool:
        return await self._backend.update(entry_id, updates)

    async def delete(self, entry_id: str) -> bool:
        return await self._backend.delete(entry_id)

    async def record_episode(
        self,
        episode: Episode,
        goal_id: str | None = None,
        task_id: str | None = None,
        agent_id: str | None = None,
        importance: float = 0.5,
    ) -> str:
        """
        Record an episode to memory.

        Args:
            episode: The episode to record
            goal_id: Associated goal ID
            task_id: Associated task ID
            agent_id: Agent that experienced this
            importance: Importance score (0-1)

        Returns:
            Memory entry ID
        """
        entry = MemoryEntry(
            memory_type=MemoryType.EPISODIC,
            content=episode.to_dict(),
            summary=f"{episode.event_type}: {episode.description}",
            goal_id=goal_id,
            task_id=task_id,
            agent_id=agent_id,
            importance_score=importance,
            tags=[episode.event_type, episode.outcome] if episode.outcome else [episode.event_type],
        )

        return await self.store(entry)

    async def get_timeline(
        self,
        goal_id: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 100,
    ) -> list[MemoryEntry]:
        """
        Get a timeline of episodes.

        Args:
            goal_id: Filter by goal
            start_time: Start of time range
            end_time: End of time range
            limit: Maximum episodes to return

        Returns:
            List of episodes in chronological order
        """
        query = MemoryQuery(
            memory_types=[MemoryType.EPISODIC],
            goal_id=goal_id,
            created_after=start_time,
            created_before=end_time,
            limit=limit,
            sort_by="created_at",
            sort_order="asc",
        )

        result = await self.query(query)
        return result.entries

    async def get_similar_experiences(
        self,
        event_type: str,
        outcome: str | None = None,
        limit: int = 5,
    ) -> list[MemoryEntry]:
        """
        Find similar past experiences.

        Args:
            event_type: Type of event to find
            outcome: Filter by outcome
            limit: Maximum results

        Returns:
            Similar past episodes
        """
        tags = [event_type]
        if outcome:
            tags.append(outcome)

        query = MemoryQuery(
            memory_types=[MemoryType.EPISODIC],
            tags=tags,
            limit=limit,
            sort_by="importance_score",
            sort_order="desc",
        )

        result = await self.query(query)
        return result.entries
