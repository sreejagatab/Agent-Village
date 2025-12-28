"""
Procedural Memory - How to do things.

Stores skills, procedures, and learned behaviors.
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
class Procedure:
    """A learned procedure or skill."""

    name: str
    description: str
    steps: list[str]
    prerequisites: list[str] = field(default_factory=list)
    success_rate: float = 1.0
    average_duration_seconds: float = 0.0
    tools_required: list[str] = field(default_factory=list)
    examples: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "steps": self.steps,
            "prerequisites": self.prerequisites,
            "success_rate": self.success_rate,
            "average_duration_seconds": self.average_duration_seconds,
            "tools_required": self.tools_required,
            "examples": self.examples,
        }


class ProceduralMemory(MemoryStore):
    """
    Procedural memory store.

    Stores and retrieves learned procedures and skills.
    """

    def __init__(self, backend: MemoryStore | None = None):
        self._backend = backend or InMemoryStore()
        self.logger = logger.bind(memory_type="procedural")

    async def store(self, entry: MemoryEntry) -> str:
        entry.memory_type = MemoryType.PROCEDURAL
        return await self._backend.store(entry)

    async def get(self, entry_id: str) -> MemoryEntry | None:
        return await self._backend.get(entry_id)

    async def query(self, query: MemoryQuery) -> MemorySearchResult:
        query.memory_types = [MemoryType.PROCEDURAL]
        return await self._backend.query(query)

    async def update(self, entry_id: str, updates: dict[str, Any]) -> bool:
        return await self._backend.update(entry_id, updates)

    async def delete(self, entry_id: str) -> bool:
        return await self._backend.delete(entry_id)

    async def store_procedure(
        self,
        procedure: Procedure,
        agent_id: str | None = None,
    ) -> str:
        """
        Store a learned procedure.

        Args:
            procedure: Procedure to store
            agent_id: Agent that learned this

        Returns:
            Memory entry ID
        """
        entry = MemoryEntry(
            memory_type=MemoryType.PROCEDURAL,
            content=procedure.to_dict(),
            summary=f"{procedure.name}: {procedure.description}",
            agent_id=agent_id,
            importance_score=procedure.success_rate,
            tags=[procedure.name] + procedure.tools_required,
            metadata={
                "avg_duration": procedure.average_duration_seconds,
                "prerequisites": procedure.prerequisites,
            },
        )

        return await self.store(entry)

    async def find_procedure(
        self,
        task_description: str,
        required_tools: list[str] | None = None,
        min_success_rate: float = 0.0,
    ) -> list[MemoryEntry]:
        """
        Find procedures that match a task.

        Args:
            task_description: What needs to be done
            required_tools: Tools that must be available
            min_success_rate: Minimum success rate

        Returns:
            Matching procedures
        """
        tags = required_tools if required_tools else None

        query = MemoryQuery(
            query_text=task_description,
            memory_types=[MemoryType.PROCEDURAL],
            tags=tags,
            min_importance=min_success_rate,
            sort_by="importance_score",
            sort_order="desc",
            limit=5,
        )

        result = await self.query(query)
        return result.entries

    async def update_success_rate(
        self,
        entry_id: str,
        success: bool,
    ) -> bool:
        """
        Update procedure success rate based on execution result.

        Uses exponential moving average to update rate.
        """
        entry = await self.get(entry_id)
        if not entry:
            return False

        current_rate = entry.importance_score
        # EMA with alpha=0.1
        new_rate = 0.9 * current_rate + 0.1 * (1.0 if success else 0.0)

        return await self.update(entry_id, {"importance_score": new_rate})

    async def get_best_procedure(
        self,
        task_type: str,
    ) -> MemoryEntry | None:
        """Get the best procedure for a task type."""
        query = MemoryQuery(
            memory_types=[MemoryType.PROCEDURAL],
            tags=[task_type],
            sort_by="importance_score",
            sort_order="desc",
            limit=1,
        )

        result = await self.query(query)
        return result.entries[0] if result.entries else None
