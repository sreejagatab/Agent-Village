"""
Agent Log Streaming API.

Provides real-time log streaming for agents via WebSocket
and a ring buffer for recent log retrieval via REST.
"""

import asyncio
import json
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, AsyncIterator

import structlog
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from pydantic import BaseModel, Field

from src.api.websocket import get_connection_manager, EventType, WebSocketEvent

logger = structlog.get_logger()
router = APIRouter(prefix="/logs", tags=["logs"])


class LogLevel(str, Enum):
    """Log severity levels."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class LogCategory(str, Enum):
    """Log categories for filtering."""
    AGENT = "agent"
    GOAL = "goal"
    TASK = "task"
    TOOL = "tool"
    MEMORY = "memory"
    SYSTEM = "system"
    GOVERNOR = "governor"
    PROVIDER = "provider"


@dataclass
class LogEntry:
    """A single log entry."""
    id: str
    timestamp: datetime
    level: LogLevel
    category: LogCategory
    message: str
    source: str  # agent_id or component name
    goal_id: str | None = None
    task_id: str | None = None
    agent_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "level": self.level.value,
            "category": self.category.value,
            "message": self.message,
            "source": self.source,
            "goal_id": self.goal_id,
            "task_id": self.task_id,
            "agent_id": self.agent_id,
            "metadata": self.metadata,
        }


class LogBuffer:
    """
    Ring buffer for storing recent logs.

    Thread-safe buffer that keeps the most recent N log entries.
    """

    def __init__(self, max_size: int = 10000):
        self._buffer: deque[LogEntry] = deque(maxlen=max_size)
        self._lock = asyncio.Lock()
        self._subscribers: dict[str, asyncio.Queue] = {}
        self._log_counter = 0
        self.logger = logger.bind(component="log_buffer")

    async def append(self, entry: LogEntry) -> None:
        """Add a log entry to the buffer."""
        async with self._lock:
            self._log_counter += 1
            if not entry.id:
                entry.id = f"log_{self._log_counter}"
            self._buffer.append(entry)

        # Notify subscribers
        await self._notify_subscribers(entry)

    async def _notify_subscribers(self, entry: LogEntry) -> None:
        """Notify all subscribers of new log entry."""
        for queue in self._subscribers.values():
            try:
                queue.put_nowait(entry)
            except asyncio.QueueFull:
                # Drop oldest if queue is full
                try:
                    queue.get_nowait()
                    queue.put_nowait(entry)
                except asyncio.QueueEmpty:
                    pass

    async def subscribe(self, subscriber_id: str) -> asyncio.Queue:
        """Subscribe to log updates."""
        queue: asyncio.Queue = asyncio.Queue(maxsize=1000)
        async with self._lock:
            self._subscribers[subscriber_id] = queue
        return queue

    async def unsubscribe(self, subscriber_id: str) -> None:
        """Unsubscribe from log updates."""
        async with self._lock:
            self._subscribers.pop(subscriber_id, None)

    async def get_recent(
        self,
        limit: int = 100,
        level: LogLevel | None = None,
        category: LogCategory | None = None,
        agent_id: str | None = None,
        goal_id: str | None = None,
        since: datetime | None = None,
    ) -> list[LogEntry]:
        """Get recent log entries with optional filtering."""
        async with self._lock:
            entries = list(self._buffer)

        # Apply filters
        if level:
            level_order = [LogLevel.DEBUG, LogLevel.INFO, LogLevel.WARNING, LogLevel.ERROR, LogLevel.CRITICAL]
            min_level_idx = level_order.index(level)
            entries = [e for e in entries if level_order.index(e.level) >= min_level_idx]

        if category:
            entries = [e for e in entries if e.category == category]

        if agent_id:
            entries = [e for e in entries if e.agent_id == agent_id]

        if goal_id:
            entries = [e for e in entries if e.goal_id == goal_id]

        if since:
            entries = [e for e in entries if e.timestamp >= since]

        # Return most recent, limited
        return entries[-limit:]

    async def get_stats(self) -> dict[str, Any]:
        """Get buffer statistics."""
        async with self._lock:
            entries = list(self._buffer)

        level_counts = {}
        category_counts = {}

        for entry in entries:
            level_counts[entry.level.value] = level_counts.get(entry.level.value, 0) + 1
            category_counts[entry.category.value] = category_counts.get(entry.category.value, 0) + 1

        return {
            "total_entries": len(entries),
            "buffer_size": self._buffer.maxlen,
            "subscribers": len(self._subscribers),
            "by_level": level_counts,
            "by_category": category_counts,
        }


# Global log buffer
_log_buffer: LogBuffer | None = None


def get_log_buffer() -> LogBuffer:
    """Get the global log buffer."""
    global _log_buffer
    if _log_buffer is None:
        _log_buffer = LogBuffer()
    return _log_buffer


async def emit_log(
    level: LogLevel,
    category: LogCategory,
    message: str,
    source: str,
    goal_id: str | None = None,
    task_id: str | None = None,
    agent_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    """
    Emit a log entry to the buffer and WebSocket subscribers.

    This is the main function to be called from other parts of the system.
    """
    entry = LogEntry(
        id="",  # Will be assigned by buffer
        timestamp=datetime.now(timezone.utc),
        level=level,
        category=category,
        message=message,
        source=source,
        goal_id=goal_id,
        task_id=task_id,
        agent_id=agent_id,
        metadata=metadata or {},
    )

    buffer = get_log_buffer()
    await buffer.append(entry)

    # Also emit via WebSocket for real-time streaming
    manager = get_connection_manager()
    await manager.broadcast(WebSocketEvent(
        event_type=EventType.SYSTEM_INFO,
        goal_id=goal_id,
        agent_id=agent_id,
        task_id=task_id,
        data={
            "log_entry": entry.to_dict(),
        },
    ))


# Convenience functions for different log levels
async def log_debug(category: LogCategory, message: str, source: str, **kwargs) -> None:
    await emit_log(LogLevel.DEBUG, category, message, source, **kwargs)


async def log_info(category: LogCategory, message: str, source: str, **kwargs) -> None:
    await emit_log(LogLevel.INFO, category, message, source, **kwargs)


async def log_warning(category: LogCategory, message: str, source: str, **kwargs) -> None:
    await emit_log(LogLevel.WARNING, category, message, source, **kwargs)


async def log_error(category: LogCategory, message: str, source: str, **kwargs) -> None:
    await emit_log(LogLevel.ERROR, category, message, source, **kwargs)


async def log_critical(category: LogCategory, message: str, source: str, **kwargs) -> None:
    await emit_log(LogLevel.CRITICAL, category, message, source, **kwargs)


# Response Models
class LogEntryResponse(BaseModel):
    """Response for a single log entry."""
    id: str
    timestamp: str
    level: str
    category: str
    message: str
    source: str
    goal_id: str | None = None
    task_id: str | None = None
    agent_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class LogsResponse(BaseModel):
    """Response for log queries."""
    logs: list[LogEntryResponse]
    total: int
    has_more: bool


class LogStatsResponse(BaseModel):
    """Response for log statistics."""
    total_entries: int
    buffer_size: int
    subscribers: int
    by_level: dict[str, int]
    by_category: dict[str, int]


# REST Endpoints

@router.get("", response_model=LogsResponse)
async def get_logs(
    limit: int = Query(100, ge=1, le=1000, description="Maximum logs to return"),
    level: str | None = Query(None, description="Minimum log level"),
    category: str | None = Query(None, description="Filter by category"),
    agent_id: str | None = Query(None, description="Filter by agent ID"),
    goal_id: str | None = Query(None, description="Filter by goal ID"),
):
    """
    Get recent logs from the buffer.

    Returns the most recent log entries matching the specified filters.
    """
    buffer = get_log_buffer()

    level_filter = LogLevel(level) if level else None
    category_filter = LogCategory(category) if category else None

    entries = await buffer.get_recent(
        limit=limit + 1,  # Get one extra to check has_more
        level=level_filter,
        category=category_filter,
        agent_id=agent_id,
        goal_id=goal_id,
    )

    has_more = len(entries) > limit
    entries = entries[:limit]

    return LogsResponse(
        logs=[LogEntryResponse(**e.to_dict()) for e in entries],
        total=len(entries),
        has_more=has_more,
    )


@router.get("/stats", response_model=LogStatsResponse)
async def get_log_stats():
    """Get log buffer statistics."""
    buffer = get_log_buffer()
    stats = await buffer.get_stats()
    return LogStatsResponse(**stats)


@router.get("/agent/{agent_id}", response_model=LogsResponse)
async def get_agent_logs(
    agent_id: str,
    limit: int = Query(100, ge=1, le=1000),
    level: str | None = Query(None),
):
    """Get logs for a specific agent."""
    buffer = get_log_buffer()

    level_filter = LogLevel(level) if level else None

    entries = await buffer.get_recent(
        limit=limit,
        level=level_filter,
        agent_id=agent_id,
    )

    return LogsResponse(
        logs=[LogEntryResponse(**e.to_dict()) for e in entries],
        total=len(entries),
        has_more=False,
    )


@router.get("/goal/{goal_id}", response_model=LogsResponse)
async def get_goal_logs(
    goal_id: str,
    limit: int = Query(100, ge=1, le=1000),
    level: str | None = Query(None),
):
    """Get logs for a specific goal."""
    buffer = get_log_buffer()

    level_filter = LogLevel(level) if level else None

    entries = await buffer.get_recent(
        limit=limit,
        level=level_filter,
        goal_id=goal_id,
    )

    return LogsResponse(
        logs=[LogEntryResponse(**e.to_dict()) for e in entries],
        total=len(entries),
        has_more=False,
    )


# WebSocket endpoint for streaming
@router.websocket("/stream")
async def stream_logs(
    websocket: WebSocket,
    level: str | None = None,
    category: str | None = None,
    agent_id: str | None = None,
    goal_id: str | None = None,
):
    """
    WebSocket endpoint for real-time log streaming.

    Clients can filter logs by level, category, agent, or goal.
    The connection will receive log entries as they are emitted.
    """
    import uuid

    await websocket.accept()
    subscriber_id = str(uuid.uuid4())
    buffer = get_log_buffer()

    # Parse filters
    level_filter = LogLevel(level) if level else None
    category_filter = LogCategory(category) if category else None
    level_order = [LogLevel.DEBUG, LogLevel.INFO, LogLevel.WARNING, LogLevel.ERROR, LogLevel.CRITICAL]
    min_level_idx = level_order.index(level_filter) if level_filter else 0

    queue = await buffer.subscribe(subscriber_id)

    try:
        # Send initial connection message
        await websocket.send_json({
            "type": "connected",
            "subscriber_id": subscriber_id,
            "filters": {
                "level": level,
                "category": category,
                "agent_id": agent_id,
                "goal_id": goal_id,
            },
        })

        # Stream logs
        while True:
            try:
                entry = await asyncio.wait_for(queue.get(), timeout=30.0)

                # Apply filters
                if level_filter and level_order.index(entry.level) < min_level_idx:
                    continue
                if category_filter and entry.category != category_filter:
                    continue
                if agent_id and entry.agent_id != agent_id:
                    continue
                if goal_id and entry.goal_id != goal_id:
                    continue

                await websocket.send_json({
                    "type": "log",
                    "entry": entry.to_dict(),
                })

            except asyncio.TimeoutError:
                # Send heartbeat
                await websocket.send_json({"type": "heartbeat"})

    except WebSocketDisconnect:
        pass
    finally:
        await buffer.unsubscribe(subscriber_id)
