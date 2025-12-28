"""
Memory Search API Routes

Provides REST endpoints for searching across all memory types:
- Episodic: Events and experiences
- Semantic: Facts and knowledge
- Strategic: Decisions and rationales
- Procedural: Procedures and workflows
"""

from datetime import datetime
from typing import Any

import structlog
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from src.memory.base import MemoryQuery, MemoryType, MemoryEntry
from src.memory.episodic import EpisodicMemory
from src.memory.semantic import SemanticMemory
from src.memory.strategic import StrategicMemory
from src.memory.procedural import ProceduralMemory

logger = structlog.get_logger()
router = APIRouter(prefix="/memory", tags=["memory"])

# Global memory instances
_episodic: EpisodicMemory | None = None
_semantic: SemanticMemory | None = None
_strategic: StrategicMemory | None = None
_procedural: ProceduralMemory | None = None


def init_memory_stores():
    """Initialize memory stores."""
    global _episodic, _semantic, _strategic, _procedural
    _episodic = EpisodicMemory()
    _semantic = SemanticMemory()
    _strategic = StrategicMemory()
    _procedural = ProceduralMemory()


def get_memory_stores() -> dict[str, Any]:
    """Get all memory store instances."""
    if not _episodic:
        init_memory_stores()
    return {
        "episodic": _episodic,
        "semantic": _semantic,
        "strategic": _strategic,
        "procedural": _procedural,
    }


# Request/Response Models

class MemorySearchRequest(BaseModel):
    """Request for memory search."""
    query: str = Field(..., min_length=1, max_length=1000, description="Search query text")
    memory_types: list[str] = Field(
        default=["episodic", "semantic", "strategic", "procedural"],
        description="Memory types to search"
    )
    goal_id: str | None = Field(default=None, description="Filter by goal ID")
    agent_id: str | None = Field(default=None, description="Filter by agent ID")
    tags: list[str] = Field(default_factory=list, description="Filter by tags")
    min_importance: float = Field(default=0.0, ge=0.0, le=1.0, description="Minimum importance score")
    limit: int = Field(default=20, ge=1, le=100, description="Maximum results per memory type")
    created_after: datetime | None = Field(default=None, description="Filter by creation date")
    created_before: datetime | None = Field(default=None, description="Filter by creation date")


class MemoryEntryResponse(BaseModel):
    """Response for a single memory entry."""
    id: str
    memory_type: str
    summary: str
    content: Any
    importance_score: float
    tags: list[str]
    goal_id: str | None = None
    task_id: str | None = None
    agent_id: str | None = None
    created_at: str
    relevance_score: float = 0.0


class MemorySearchResponse(BaseModel):
    """Response for memory search."""
    query: str
    total_results: int
    results_by_type: dict[str, int]
    results: list[MemoryEntryResponse]
    search_time_ms: float


class MemoryStatsResponse(BaseModel):
    """Response for memory statistics."""
    total_entries: int
    entries_by_type: dict[str, int]
    recent_entries: int
    top_tags: list[dict[str, Any]]


class StoreMemoryRequest(BaseModel):
    """Request to store a memory entry."""
    memory_type: str = Field(..., description="Type: episodic, semantic, strategic, procedural")
    content: dict[str, Any] = Field(..., description="Memory content")
    summary: str = Field(..., min_length=1, max_length=500, description="Brief summary")
    importance: float = Field(default=0.5, ge=0.0, le=1.0, description="Importance score")
    tags: list[str] = Field(default_factory=list, description="Tags for categorization")
    goal_id: str | None = None
    task_id: str | None = None
    agent_id: str | None = None


# Helper functions

def memory_entry_to_response(entry: MemoryEntry, relevance: float = 0.0) -> MemoryEntryResponse:
    """Convert MemoryEntry to response model."""
    return MemoryEntryResponse(
        id=entry.id,
        memory_type=entry.memory_type.value if isinstance(entry.memory_type, MemoryType) else entry.memory_type,
        summary=entry.summary,
        content=entry.content,
        importance_score=entry.importance_score,
        tags=entry.tags,
        goal_id=entry.goal_id,
        task_id=entry.task_id,
        agent_id=entry.agent_id,
        created_at=entry.created_at.isoformat() if entry.created_at else "",
        relevance_score=relevance,
    )


# Routes

@router.post("/search", response_model=MemorySearchResponse)
async def search_memory(request: MemorySearchRequest):
    """
    Search across all memory types.

    Searches episodic, semantic, strategic, and procedural memory
    based on the provided query and filters.
    """
    import time
    start_time = time.time()

    stores = get_memory_stores()
    all_results: list[MemoryEntryResponse] = []
    results_by_type: dict[str, int] = {}

    # Map string types to MemoryType enum
    type_map = {
        "episodic": MemoryType.EPISODIC,
        "semantic": MemoryType.SEMANTIC,
        "strategic": MemoryType.STRATEGIC,
        "procedural": MemoryType.PROCEDURAL,
    }

    for type_name in request.memory_types:
        if type_name not in stores or type_name not in type_map:
            continue

        store = stores[type_name]
        memory_type = type_map[type_name]

        query = MemoryQuery(
            query_text=request.query,
            memory_types=[memory_type],
            goal_id=request.goal_id,
            agent_id=request.agent_id,
            tags=request.tags if request.tags else None,
            min_importance=request.min_importance,
            created_after=request.created_after,
            created_before=request.created_before,
            limit=request.limit,
            sort_by="importance_score",
            sort_order="desc",
        )

        try:
            result = await store.query(query)
            results_by_type[type_name] = len(result.entries)

            for i, entry in enumerate(result.entries):
                # Calculate a simple relevance score based on position and importance
                relevance = 1.0 - (i / max(len(result.entries), 1)) * 0.5
                relevance *= entry.importance_score
                all_results.append(memory_entry_to_response(entry, relevance))

        except Exception as e:
            logger.error(f"Error searching {type_name} memory", error=str(e))
            results_by_type[type_name] = 0

    # Sort all results by relevance
    all_results.sort(key=lambda x: x.relevance_score, reverse=True)

    search_time_ms = (time.time() - start_time) * 1000

    return MemorySearchResponse(
        query=request.query,
        total_results=len(all_results),
        results_by_type=results_by_type,
        results=all_results[:request.limit],
        search_time_ms=round(search_time_ms, 2),
    )


@router.get("/search", response_model=MemorySearchResponse)
async def search_memory_get(
    query: str = Query(..., min_length=1, description="Search query"),
    memory_types: str = Query("episodic,semantic,strategic,procedural", description="Comma-separated memory types"),
    goal_id: str | None = Query(None, description="Filter by goal ID"),
    agent_id: str | None = Query(None, description="Filter by agent ID"),
    tags: str | None = Query(None, description="Comma-separated tags"),
    min_importance: float = Query(0.0, ge=0.0, le=1.0, description="Minimum importance"),
    limit: int = Query(20, ge=1, le=100, description="Maximum results"),
):
    """Search memory via GET request with query parameters."""
    request = MemorySearchRequest(
        query=query,
        memory_types=memory_types.split(",") if memory_types else [],
        goal_id=goal_id,
        agent_id=agent_id,
        tags=tags.split(",") if tags else [],
        min_importance=min_importance,
        limit=limit,
    )
    return await search_memory(request)


@router.post("/store", response_model=MemoryEntryResponse)
async def store_memory(request: StoreMemoryRequest):
    """
    Store a new memory entry.

    Creates a new entry in the specified memory store.
    """
    stores = get_memory_stores()

    if request.memory_type not in stores:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid memory type: {request.memory_type}. Valid types: {list(stores.keys())}"
        )

    store = stores[request.memory_type]

    # Create memory entry
    type_map = {
        "episodic": MemoryType.EPISODIC,
        "semantic": MemoryType.SEMANTIC,
        "strategic": MemoryType.STRATEGIC,
        "procedural": MemoryType.PROCEDURAL,
    }

    entry = MemoryEntry(
        memory_type=type_map[request.memory_type],
        content=request.content,
        summary=request.summary,
        importance_score=request.importance,
        tags=request.tags,
        goal_id=request.goal_id,
        task_id=request.task_id,
        agent_id=request.agent_id,
    )

    try:
        entry_id = await store.store(entry)
        entry.id = entry_id

        logger.info(
            "Memory stored",
            memory_type=request.memory_type,
            entry_id=entry_id,
        )

        return memory_entry_to_response(entry)

    except Exception as e:
        logger.error("Failed to store memory", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{memory_type}/{entry_id}", response_model=MemoryEntryResponse)
async def get_memory_entry(memory_type: str, entry_id: str):
    """Get a specific memory entry by ID."""
    stores = get_memory_stores()

    if memory_type not in stores:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid memory type: {memory_type}"
        )

    store = stores[memory_type]
    entry = await store.get(entry_id)

    if not entry:
        raise HTTPException(status_code=404, detail="Memory entry not found")

    return memory_entry_to_response(entry)


@router.delete("/{memory_type}/{entry_id}")
async def delete_memory_entry(memory_type: str, entry_id: str):
    """Delete a memory entry."""
    stores = get_memory_stores()

    if memory_type not in stores:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid memory type: {memory_type}"
        )

    store = stores[memory_type]
    success = await store.delete(entry_id)

    if not success:
        raise HTTPException(status_code=404, detail="Memory entry not found")

    return {"status": "deleted", "entry_id": entry_id}


@router.get("/stats", response_model=MemoryStatsResponse)
async def get_memory_stats():
    """Get statistics about memory usage."""
    stores = get_memory_stores()
    entries_by_type: dict[str, int] = {}
    total_entries = 0
    tag_counts: dict[str, int] = {}
    recent_count = 0

    for type_name, store in stores.items():
        try:
            # Query all entries for this type
            query = MemoryQuery(limit=1000)
            result = await store.query(query)

            count = len(result.entries)
            entries_by_type[type_name] = count
            total_entries += count

            # Count tags and recent entries
            from datetime import timedelta, timezone
            now = datetime.now(timezone.utc)
            recent_threshold = now - timedelta(hours=24)

            for entry in result.entries:
                for tag in entry.tags:
                    tag_counts[tag] = tag_counts.get(tag, 0) + 1
                if entry.created_at and entry.created_at > recent_threshold:
                    recent_count += 1

        except Exception as e:
            logger.error(f"Error getting stats for {type_name}", error=str(e))
            entries_by_type[type_name] = 0

    # Get top 10 tags
    top_tags = sorted(
        [{"tag": k, "count": v} for k, v in tag_counts.items()],
        key=lambda x: x["count"],
        reverse=True,
    )[:10]

    return MemoryStatsResponse(
        total_entries=total_entries,
        entries_by_type=entries_by_type,
        recent_entries=recent_count,
        top_tags=top_tags,
    )


@router.get("/timeline")
async def get_timeline(
    goal_id: str | None = Query(None, description="Filter by goal ID"),
    hours: int = Query(24, ge=1, le=168, description="Hours to look back"),
    limit: int = Query(50, ge=1, le=200, description="Maximum events"),
):
    """
    Get a timeline of recent memory events.

    Returns episodic and strategic memories in chronological order.
    """
    stores = get_memory_stores()

    from datetime import timedelta, timezone
    now = datetime.now(timezone.utc)
    start_time = now - timedelta(hours=hours)

    timeline_entries: list[MemoryEntryResponse] = []

    # Query episodic memory
    if stores["episodic"]:
        entries = await stores["episodic"].get_timeline(
            goal_id=goal_id,
            start_time=start_time,
            limit=limit,
        )
        for entry in entries:
            timeline_entries.append(memory_entry_to_response(entry))

    # Query strategic memory for decisions
    if stores["strategic"]:
        query = MemoryQuery(
            memory_types=[MemoryType.STRATEGIC],
            goal_id=goal_id,
            created_after=start_time,
            limit=limit,
            sort_by="created_at",
            sort_order="asc",
        )
        result = await stores["strategic"].query(query)
        for entry in result.entries:
            timeline_entries.append(memory_entry_to_response(entry))

    # Sort by creation time
    timeline_entries.sort(
        key=lambda x: x.created_at if x.created_at else "",
        reverse=True,
    )

    return {
        "timeline": timeline_entries[:limit],
        "total_events": len(timeline_entries),
        "time_range": {
            "start": start_time.isoformat(),
            "end": now.isoformat(),
        },
    }


@router.get("/lessons")
async def get_lessons_learned(
    decision_type: str | None = Query(None, description="Filter by decision type"),
    limit: int = Query(20, ge=1, le=100, description="Maximum lessons"),
):
    """Get aggregated lessons learned from strategic memory."""
    stores = get_memory_stores()

    if not stores["strategic"]:
        return {"lessons": [], "total": 0}

    lessons = await stores["strategic"].get_lessons_learned(
        decision_type=decision_type,
        limit=limit,
    )

    return {
        "lessons": lessons,
        "total": len(lessons),
        "decision_type": decision_type,
    }
