"""
WebSocket endpoints for real-time updates.

Provides real-time streaming of:
- Goal progress and state changes
- Agent activity and events
- System-wide notifications
"""

import asyncio
import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

import structlog
from fastapi import WebSocket, WebSocketDisconnect

logger = structlog.get_logger()


class EventType(str, Enum):
    """Types of WebSocket events."""

    # Goal events
    GOAL_CREATED = "goal.created"
    GOAL_STARTED = "goal.started"
    GOAL_STATE_CHANGED = "goal.state_changed"
    GOAL_PROGRESS = "goal.progress"
    GOAL_COMPLETED = "goal.completed"
    GOAL_FAILED = "goal.failed"
    GOAL_CANCELLED = "goal.cancelled"
    GOAL_AWAITING_APPROVAL = "goal.awaiting_approval"

    # Agent events
    AGENT_SPAWNED = "agent.spawned"
    AGENT_STARTED = "agent.started"
    AGENT_EXECUTING = "agent.executing"
    AGENT_COMPLETED = "agent.completed"
    AGENT_FAILED = "agent.failed"
    AGENT_STOPPED = "agent.stopped"

    # Task events
    TASK_CREATED = "task.created"
    TASK_ASSIGNED = "task.assigned"
    TASK_PROGRESS = "task.progress"
    TASK_COMPLETED = "task.completed"
    TASK_FAILED = "task.failed"

    # Memory events
    MEMORY_STORED = "memory.stored"
    MEMORY_QUERIED = "memory.queried"

    # System events
    SYSTEM_INFO = "system.info"
    SYSTEM_WARNING = "system.warning"
    SYSTEM_ERROR = "system.error"

    # Connection events
    CONNECTED = "connected"
    PING = "ping"
    PONG = "pong"


@dataclass
class WebSocketEvent:
    """A WebSocket event message."""

    event_type: EventType
    data: dict[str, Any]
    goal_id: str | None = None
    agent_id: str | None = None
    task_id: str | None = None
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps({
            "event": self.event_type.value,
            "data": self.data,
            "goal_id": self.goal_id,
            "agent_id": self.agent_id,
            "task_id": self.task_id,
            "timestamp": self.timestamp.isoformat(),
        })


class ConnectionManager:
    """Manages WebSocket connections and broadcasts."""

    def __init__(self):
        # All active connections
        self._connections: set[WebSocket] = set()
        # Connections subscribed to specific goals
        self._goal_subscriptions: dict[str, set[WebSocket]] = {}
        # Connections subscribed to specific agents
        self._agent_subscriptions: dict[str, set[WebSocket]] = {}
        self._lock = asyncio.Lock()
        self.logger = logger.bind(component="websocket_manager")

    async def connect(self, websocket: WebSocket) -> None:
        """Accept a new WebSocket connection."""
        await websocket.accept()
        async with self._lock:
            self._connections.add(websocket)
        self.logger.info("WebSocket connected", total_connections=len(self._connections))

        # Send connection confirmation
        await self.send_personal(
            websocket,
            WebSocketEvent(
                event_type=EventType.CONNECTED,
                data={"message": "Connected to Agent Village WebSocket"},
            ),
        )

    async def disconnect(self, websocket: WebSocket) -> None:
        """Handle WebSocket disconnection."""
        async with self._lock:
            self._connections.discard(websocket)
            # Remove from all subscriptions
            for subs in self._goal_subscriptions.values():
                subs.discard(websocket)
            for subs in self._agent_subscriptions.values():
                subs.discard(websocket)
        self.logger.info("WebSocket disconnected", total_connections=len(self._connections))

    async def subscribe_goal(self, websocket: WebSocket, goal_id: str) -> None:
        """Subscribe to updates for a specific goal."""
        async with self._lock:
            if goal_id not in self._goal_subscriptions:
                self._goal_subscriptions[goal_id] = set()
            self._goal_subscriptions[goal_id].add(websocket)
        self.logger.debug("Subscribed to goal", goal_id=goal_id)

    async def unsubscribe_goal(self, websocket: WebSocket, goal_id: str) -> None:
        """Unsubscribe from goal updates."""
        async with self._lock:
            if goal_id in self._goal_subscriptions:
                self._goal_subscriptions[goal_id].discard(websocket)

    async def subscribe_agent(self, websocket: WebSocket, agent_id: str) -> None:
        """Subscribe to updates for a specific agent."""
        async with self._lock:
            if agent_id not in self._agent_subscriptions:
                self._agent_subscriptions[agent_id] = set()
            self._agent_subscriptions[agent_id].add(websocket)
        self.logger.debug("Subscribed to agent", agent_id=agent_id)

    async def send_personal(self, websocket: WebSocket, event: WebSocketEvent) -> None:
        """Send event to a specific connection."""
        try:
            await websocket.send_text(event.to_json())
        except Exception as e:
            self.logger.warning("Failed to send to websocket", error=str(e))
            await self.disconnect(websocket)

    async def broadcast(self, event: WebSocketEvent) -> None:
        """Broadcast event to all connections."""
        disconnected = []
        async with self._lock:
            connections = list(self._connections)

        for websocket in connections:
            try:
                await websocket.send_text(event.to_json())
            except Exception:
                disconnected.append(websocket)

        # Clean up disconnected
        for ws in disconnected:
            await self.disconnect(ws)

    async def broadcast_to_goal(self, goal_id: str, event: WebSocketEvent) -> None:
        """Broadcast event to subscribers of a specific goal."""
        event.goal_id = goal_id
        disconnected = []

        async with self._lock:
            subscribers = list(self._goal_subscriptions.get(goal_id, set()))

        for websocket in subscribers:
            try:
                await websocket.send_text(event.to_json())
            except Exception:
                disconnected.append(websocket)

        for ws in disconnected:
            await self.disconnect(ws)

    async def broadcast_to_agent(self, agent_id: str, event: WebSocketEvent) -> None:
        """Broadcast event to subscribers of a specific agent."""
        event.agent_id = agent_id
        disconnected = []

        async with self._lock:
            subscribers = list(self._agent_subscriptions.get(agent_id, set()))

        for websocket in subscribers:
            try:
                await websocket.send_text(event.to_json())
            except Exception:
                disconnected.append(websocket)

        for ws in disconnected:
            await self.disconnect(ws)

    def get_stats(self) -> dict[str, Any]:
        """Get connection statistics."""
        return {
            "total_connections": len(self._connections),
            "goal_subscriptions": len(self._goal_subscriptions),
            "agent_subscriptions": len(self._agent_subscriptions),
        }


# Global connection manager
_manager: ConnectionManager | None = None


def get_connection_manager() -> ConnectionManager:
    """Get the global connection manager."""
    global _manager
    if _manager is None:
        _manager = ConnectionManager()
    return _manager


async def emit_event(event: WebSocketEvent) -> None:
    """Emit an event to appropriate subscribers."""
    manager = get_connection_manager()

    # Route to appropriate subscribers
    if event.goal_id:
        await manager.broadcast_to_goal(event.goal_id, event)
    elif event.agent_id:
        await manager.broadcast_to_agent(event.agent_id, event)
    else:
        await manager.broadcast(event)


# Convenience functions for common events
async def emit_goal_created(goal_id: str, description: str) -> None:
    """Emit goal created event."""
    await emit_event(WebSocketEvent(
        event_type=EventType.GOAL_CREATED,
        goal_id=goal_id,
        data={"description": description},
    ))


async def emit_goal_state_changed(
    goal_id: str,
    old_state: str,
    new_state: str,
    message: str = "",
) -> None:
    """Emit goal state change event."""
    await emit_event(WebSocketEvent(
        event_type=EventType.GOAL_STATE_CHANGED,
        goal_id=goal_id,
        data={
            "old_state": old_state,
            "new_state": new_state,
            "message": message,
        },
    ))


async def emit_goal_progress(
    goal_id: str,
    progress: float,
    current_task: str = "",
    message: str = "",
) -> None:
    """Emit goal progress event."""
    await emit_event(WebSocketEvent(
        event_type=EventType.GOAL_PROGRESS,
        goal_id=goal_id,
        data={
            "progress": progress,
            "current_task": current_task,
            "message": message,
        },
    ))


async def emit_goal_completed(goal_id: str, result: Any = None) -> None:
    """Emit goal completed event."""
    await emit_event(WebSocketEvent(
        event_type=EventType.GOAL_COMPLETED,
        goal_id=goal_id,
        data={"result": result},
    ))


async def emit_goal_failed(goal_id: str, error: str) -> None:
    """Emit goal failed event."""
    await emit_event(WebSocketEvent(
        event_type=EventType.GOAL_FAILED,
        goal_id=goal_id,
        data={"error": error},
    ))


async def emit_agent_spawned(agent_id: str, agent_type: str, name: str) -> None:
    """Emit agent spawned event."""
    await emit_event(WebSocketEvent(
        event_type=EventType.AGENT_SPAWNED,
        agent_id=agent_id,
        data={"agent_type": agent_type, "name": name},
    ))


async def emit_agent_executing(agent_id: str, task: str, goal_id: str | None = None) -> None:
    """Emit agent executing event."""
    await emit_event(WebSocketEvent(
        event_type=EventType.AGENT_EXECUTING,
        agent_id=agent_id,
        goal_id=goal_id,
        data={"task": task},
    ))


async def emit_task_progress(
    task_id: str,
    goal_id: str,
    progress: float,
    message: str = "",
) -> None:
    """Emit task progress event."""
    await emit_event(WebSocketEvent(
        event_type=EventType.TASK_PROGRESS,
        task_id=task_id,
        goal_id=goal_id,
        data={"progress": progress, "message": message},
    ))


class WebSocketHandler:
    """Handler for WebSocket message processing."""

    def __init__(self, manager: ConnectionManager):
        self.manager = manager
        self.logger = logger.bind(component="websocket_handler")

    async def handle_message(self, websocket: WebSocket, data: str) -> None:
        """Process incoming WebSocket message."""
        try:
            message = json.loads(data)
            action = message.get("action")

            if action == "subscribe_goal":
                goal_id = message.get("goal_id")
                if goal_id:
                    await self.manager.subscribe_goal(websocket, goal_id)
                    await self.manager.send_personal(
                        websocket,
                        WebSocketEvent(
                            event_type=EventType.SYSTEM_INFO,
                            data={"message": f"Subscribed to goal {goal_id}"},
                        ),
                    )

            elif action == "unsubscribe_goal":
                goal_id = message.get("goal_id")
                if goal_id:
                    await self.manager.unsubscribe_goal(websocket, goal_id)

            elif action == "subscribe_agent":
                agent_id = message.get("agent_id")
                if agent_id:
                    await self.manager.subscribe_agent(websocket, agent_id)
                    await self.manager.send_personal(
                        websocket,
                        WebSocketEvent(
                            event_type=EventType.SYSTEM_INFO,
                            data={"message": f"Subscribed to agent {agent_id}"},
                        ),
                    )

            elif action == "ping":
                await self.manager.send_personal(
                    websocket,
                    WebSocketEvent(event_type=EventType.PONG, data={}),
                )

            else:
                self.logger.warning("Unknown WebSocket action", action=action)

        except json.JSONDecodeError:
            self.logger.warning("Invalid JSON in WebSocket message")
        except Exception as e:
            self.logger.error("Error handling WebSocket message", error=str(e))


async def websocket_endpoint(websocket: WebSocket) -> None:
    """Main WebSocket endpoint handler."""
    manager = get_connection_manager()
    handler = WebSocketHandler(manager)

    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await handler.handle_message(websocket, data)
    except WebSocketDisconnect:
        await manager.disconnect(websocket)


async def goal_websocket_endpoint(websocket: WebSocket, goal_id: str) -> None:
    """WebSocket endpoint for a specific goal."""
    manager = get_connection_manager()
    handler = WebSocketHandler(manager)

    await manager.connect(websocket)
    await manager.subscribe_goal(websocket, goal_id)

    try:
        while True:
            data = await websocket.receive_text()
            await handler.handle_message(websocket, data)
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
