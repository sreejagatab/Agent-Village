"""
Strategic Memory - Why decisions were made.

Stores decision rationales, strategies, and their outcomes.
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
class Decision:
    """A recorded decision and its context."""

    decision_type: str  # pattern_selection, agent_assignment, replanning, etc.
    description: str
    rationale: str
    alternatives_considered: list[str] = field(default_factory=list)
    constraints: dict[str, Any] = field(default_factory=dict)
    outcome: str = ""  # success, failure, partial, pending
    outcome_score: float = 0.0  # 0-1 how well the decision worked
    lessons: list[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision_type": self.decision_type,
            "description": self.description,
            "rationale": self.rationale,
            "alternatives_considered": self.alternatives_considered,
            "constraints": self.constraints,
            "outcome": self.outcome,
            "outcome_score": self.outcome_score,
            "lessons": self.lessons,
            "timestamp": self.timestamp.isoformat(),
        }


class StrategicMemory(MemoryStore):
    """
    Strategic memory store.

    Stores decision rationales and learns from outcomes.
    """

    def __init__(self, backend: MemoryStore | None = None):
        self._backend = backend or InMemoryStore()
        self.logger = logger.bind(memory_type="strategic")

    async def store(self, entry: MemoryEntry) -> str:
        entry.memory_type = MemoryType.STRATEGIC
        return await self._backend.store(entry)

    async def get(self, entry_id: str) -> MemoryEntry | None:
        return await self._backend.get(entry_id)

    async def query(self, query: MemoryQuery) -> MemorySearchResult:
        query.memory_types = [MemoryType.STRATEGIC]
        return await self._backend.query(query)

    async def update(self, entry_id: str, updates: dict[str, Any]) -> bool:
        return await self._backend.update(entry_id, updates)

    async def delete(self, entry_id: str) -> bool:
        return await self._backend.delete(entry_id)

    async def record_decision(
        self,
        decision: Decision,
        goal_id: str | None = None,
        task_id: str | None = None,
        agent_id: str | None = None,
    ) -> str:
        """
        Record a decision.

        Args:
            decision: Decision to record
            goal_id: Associated goal
            task_id: Associated task
            agent_id: Agent that made the decision

        Returns:
            Memory entry ID
        """
        entry = MemoryEntry(
            memory_type=MemoryType.STRATEGIC,
            content=decision.to_dict(),
            summary=f"{decision.decision_type}: {decision.description}",
            goal_id=goal_id,
            task_id=task_id,
            agent_id=agent_id,
            importance_score=decision.outcome_score if decision.outcome else 0.5,
            tags=[decision.decision_type, decision.outcome] if decision.outcome else [decision.decision_type],
            metadata={"rationale": decision.rationale},
        )

        return await self.store(entry)

    async def record_outcome(
        self,
        entry_id: str,
        outcome: str,
        outcome_score: float,
        lessons: list[str],
    ) -> bool:
        """
        Record the outcome of a decision.

        Args:
            entry_id: Decision entry ID
            outcome: Outcome description
            outcome_score: How well it worked (0-1)
            lessons: Lessons learned

        Returns:
            True if updated successfully
        """
        entry = await self.get(entry_id)
        if not entry:
            return False

        content = entry.content
        if isinstance(content, dict):
            content["outcome"] = outcome
            content["outcome_score"] = outcome_score
            content["lessons"] = lessons

        return await self.update(
            entry_id,
            {
                "content": content,
                "importance_score": outcome_score,
                "tags": entry.tags + [outcome] if outcome not in entry.tags else entry.tags,
            },
        )

    async def find_similar_decisions(
        self,
        decision_type: str,
        context_description: str,
        min_outcome_score: float = 0.0,
        limit: int = 5,
    ) -> list[MemoryEntry]:
        """
        Find past decisions in similar contexts.

        Args:
            decision_type: Type of decision
            context_description: Current context
            min_outcome_score: Minimum outcome score to consider
            limit: Maximum results

        Returns:
            Similar past decisions
        """
        query = MemoryQuery(
            query_text=context_description,
            memory_types=[MemoryType.STRATEGIC],
            tags=[decision_type],
            min_importance=min_outcome_score,
            sort_by="importance_score",
            sort_order="desc",
            limit=limit,
        )

        result = await self.query(query)
        return result.entries

    async def get_best_strategy(
        self,
        decision_type: str,
    ) -> MemoryEntry | None:
        """
        Get the best performing strategy for a decision type.

        Args:
            decision_type: Type of decision

        Returns:
            Best performing decision or None
        """
        query = MemoryQuery(
            memory_types=[MemoryType.STRATEGIC],
            tags=[decision_type, "success"],
            sort_by="importance_score",
            sort_order="desc",
            limit=1,
        )

        result = await self.query(query)
        return result.entries[0] if result.entries else None

    async def get_lessons_learned(
        self,
        decision_type: str | None = None,
        limit: int = 10,
    ) -> list[str]:
        """
        Aggregate lessons learned from past decisions.

        Args:
            decision_type: Optional filter by type
            limit: Maximum decisions to consider

        Returns:
            List of lessons learned
        """
        tags = [decision_type] if decision_type else None

        query = MemoryQuery(
            memory_types=[MemoryType.STRATEGIC],
            tags=tags,
            sort_by="importance_score",
            sort_order="desc",
            limit=limit,
        )

        result = await self.query(query)

        lessons = []
        for entry in result.entries:
            content = entry.content
            if isinstance(content, dict):
                lessons.extend(content.get("lessons", []))

        return lessons
