"""Tests for WebSocket functionality."""

import json
import pytest
import pytest_asyncio

from src.api.websocket import (
    ConnectionManager,
    EventType,
    WebSocketEvent,
    WebSocketHandler,
    emit_goal_created,
    emit_goal_progress,
    emit_goal_state_changed,
)


class MockWebSocket:
    """Mock WebSocket for testing."""

    def __init__(self):
        self.accepted = False
        self.sent_messages: list[str] = []
        self.closed = False

    async def accept(self):
        self.accepted = True

    async def send_text(self, data: str):
        if self.closed:
            raise Exception("WebSocket closed")
        self.sent_messages.append(data)

    async def receive_text(self) -> str:
        return '{"action": "ping"}'

    async def close(self):
        self.closed = True


class TestWebSocketEvent:
    """Tests for WebSocketEvent."""

    def test_event_creation(self):
        """Test creating an event."""
        event = WebSocketEvent(
            event_type=EventType.GOAL_CREATED,
            data={"description": "Test goal"},
            goal_id="goal-123",
        )

        assert event.event_type == EventType.GOAL_CREATED
        assert event.data["description"] == "Test goal"
        assert event.goal_id == "goal-123"

    def test_event_to_json(self):
        """Test serializing event to JSON."""
        event = WebSocketEvent(
            event_type=EventType.GOAL_PROGRESS,
            data={"progress": 0.5, "message": "Halfway done"},
            goal_id="goal-456",
        )

        json_str = event.to_json()
        data = json.loads(json_str)

        assert data["event"] == "goal.progress"
        assert data["data"]["progress"] == 0.5
        assert data["goal_id"] == "goal-456"
        assert "timestamp" in data


class TestConnectionManager:
    """Tests for ConnectionManager."""

    @pytest.fixture
    def manager(self):
        return ConnectionManager()

    @pytest.fixture
    def mock_ws(self):
        return MockWebSocket()

    @pytest.mark.asyncio
    async def test_connect(self, manager, mock_ws):
        """Test connecting a WebSocket."""
        await manager.connect(mock_ws)

        assert mock_ws.accepted
        assert mock_ws in manager._connections
        assert len(mock_ws.sent_messages) == 1  # Connection confirmation

        # Check confirmation message
        msg = json.loads(mock_ws.sent_messages[0])
        assert msg["event"] == "connected"

    @pytest.mark.asyncio
    async def test_disconnect(self, manager, mock_ws):
        """Test disconnecting a WebSocket."""
        await manager.connect(mock_ws)
        await manager.disconnect(mock_ws)

        assert mock_ws not in manager._connections

    @pytest.mark.asyncio
    async def test_subscribe_goal(self, manager, mock_ws):
        """Test subscribing to goal updates."""
        await manager.connect(mock_ws)
        await manager.subscribe_goal(mock_ws, "goal-123")

        assert "goal-123" in manager._goal_subscriptions
        assert mock_ws in manager._goal_subscriptions["goal-123"]

    @pytest.mark.asyncio
    async def test_unsubscribe_goal(self, manager, mock_ws):
        """Test unsubscribing from goal updates."""
        await manager.connect(mock_ws)
        await manager.subscribe_goal(mock_ws, "goal-123")
        await manager.unsubscribe_goal(mock_ws, "goal-123")

        assert mock_ws not in manager._goal_subscriptions.get("goal-123", set())

    @pytest.mark.asyncio
    async def test_subscribe_agent(self, manager, mock_ws):
        """Test subscribing to agent updates."""
        await manager.connect(mock_ws)
        await manager.subscribe_agent(mock_ws, "agent-456")

        assert "agent-456" in manager._agent_subscriptions
        assert mock_ws in manager._agent_subscriptions["agent-456"]

    @pytest.mark.asyncio
    async def test_broadcast(self, manager):
        """Test broadcasting to all connections."""
        ws1 = MockWebSocket()
        ws2 = MockWebSocket()

        await manager.connect(ws1)
        await manager.connect(ws2)

        event = WebSocketEvent(
            event_type=EventType.SYSTEM_INFO,
            data={"message": "Broadcast test"},
        )

        await manager.broadcast(event)

        # Both should receive (plus connection message)
        assert len(ws1.sent_messages) == 2
        assert len(ws2.sent_messages) == 2

    @pytest.mark.asyncio
    async def test_broadcast_to_goal(self, manager):
        """Test broadcasting to goal subscribers only."""
        ws1 = MockWebSocket()
        ws2 = MockWebSocket()

        await manager.connect(ws1)
        await manager.connect(ws2)
        await manager.subscribe_goal(ws1, "goal-123")

        event = WebSocketEvent(
            event_type=EventType.GOAL_PROGRESS,
            data={"progress": 0.5},
        )

        await manager.broadcast_to_goal("goal-123", event)

        # Only ws1 subscribed to this goal (plus connection msg)
        assert len(ws1.sent_messages) == 2
        assert len(ws2.sent_messages) == 1  # Only connection msg

    @pytest.mark.asyncio
    async def test_send_personal(self, manager, mock_ws):
        """Test sending to specific connection."""
        await manager.connect(mock_ws)

        event = WebSocketEvent(
            event_type=EventType.PING,
            data={},
        )

        await manager.send_personal(mock_ws, event)

        assert len(mock_ws.sent_messages) == 2  # Connection + personal

    @pytest.mark.asyncio
    async def test_get_stats(self, manager):
        """Test getting connection stats."""
        ws1 = MockWebSocket()
        ws2 = MockWebSocket()

        await manager.connect(ws1)
        await manager.connect(ws2)
        await manager.subscribe_goal(ws1, "goal-1")
        await manager.subscribe_agent(ws2, "agent-1")

        stats = manager.get_stats()

        assert stats["total_connections"] == 2
        assert stats["goal_subscriptions"] == 1
        assert stats["agent_subscriptions"] == 1

    @pytest.mark.asyncio
    async def test_disconnect_removes_from_subscriptions(self, manager, mock_ws):
        """Test that disconnect removes from all subscriptions."""
        await manager.connect(mock_ws)
        await manager.subscribe_goal(mock_ws, "goal-1")
        await manager.subscribe_agent(mock_ws, "agent-1")

        await manager.disconnect(mock_ws)

        assert mock_ws not in manager._goal_subscriptions.get("goal-1", set())
        assert mock_ws not in manager._agent_subscriptions.get("agent-1", set())


class TestWebSocketHandler:
    """Tests for WebSocketHandler."""

    @pytest.fixture
    def manager(self):
        return ConnectionManager()

    @pytest.fixture
    def handler(self, manager):
        return WebSocketHandler(manager)

    @pytest.fixture
    def mock_ws(self):
        return MockWebSocket()

    @pytest.mark.asyncio
    async def test_handle_subscribe_goal(self, manager, handler, mock_ws):
        """Test handling subscribe_goal action."""
        await manager.connect(mock_ws)

        message = json.dumps({"action": "subscribe_goal", "goal_id": "goal-123"})
        await handler.handle_message(mock_ws, message)

        assert mock_ws in manager._goal_subscriptions.get("goal-123", set())

    @pytest.mark.asyncio
    async def test_handle_subscribe_agent(self, manager, handler, mock_ws):
        """Test handling subscribe_agent action."""
        await manager.connect(mock_ws)

        message = json.dumps({"action": "subscribe_agent", "agent_id": "agent-456"})
        await handler.handle_message(mock_ws, message)

        assert mock_ws in manager._agent_subscriptions.get("agent-456", set())

    @pytest.mark.asyncio
    async def test_handle_ping(self, manager, handler, mock_ws):
        """Test handling ping action."""
        await manager.connect(mock_ws)

        message = json.dumps({"action": "ping"})
        await handler.handle_message(mock_ws, message)

        # Should receive pong
        messages = [json.loads(m) for m in mock_ws.sent_messages]
        pong_messages = [m for m in messages if m.get("event") == "pong"]
        assert len(pong_messages) == 1

    @pytest.mark.asyncio
    async def test_handle_invalid_json(self, manager, handler, mock_ws):
        """Test handling invalid JSON gracefully."""
        await manager.connect(mock_ws)

        # Should not raise
        await handler.handle_message(mock_ws, "not valid json")


class TestEventEmitters:
    """Tests for event emitter functions."""

    @pytest.mark.asyncio
    async def test_emit_goal_created(self, monkeypatch):
        """Test goal created emitter."""
        emitted_events = []

        async def mock_emit(event):
            emitted_events.append(event)

        from src.api import websocket
        monkeypatch.setattr(websocket, "emit_event", mock_emit)

        await emit_goal_created("goal-123", "Test description")

        assert len(emitted_events) == 1
        assert emitted_events[0].event_type == EventType.GOAL_CREATED
        assert emitted_events[0].goal_id == "goal-123"

    @pytest.mark.asyncio
    async def test_emit_goal_progress(self, monkeypatch):
        """Test goal progress emitter."""
        emitted_events = []

        async def mock_emit(event):
            emitted_events.append(event)

        from src.api import websocket
        monkeypatch.setattr(websocket, "emit_event", mock_emit)

        await emit_goal_progress("goal-123", 0.5, "Task 1", "Halfway")

        assert len(emitted_events) == 1
        assert emitted_events[0].event_type == EventType.GOAL_PROGRESS
        assert emitted_events[0].data["progress"] == 0.5

    @pytest.mark.asyncio
    async def test_emit_goal_state_changed(self, monkeypatch):
        """Test goal state changed emitter."""
        emitted_events = []

        async def mock_emit(event):
            emitted_events.append(event)

        from src.api import websocket
        monkeypatch.setattr(websocket, "emit_event", mock_emit)

        await emit_goal_state_changed("goal-123", "executing", "completed", "Done")

        assert len(emitted_events) == 1
        assert emitted_events[0].event_type == EventType.GOAL_STATE_CHANGED
        assert emitted_events[0].data["old_state"] == "executing"
        assert emitted_events[0].data["new_state"] == "completed"


class TestEventTypes:
    """Tests for EventType enum."""

    def test_all_event_types_defined(self):
        """Test that all expected event types are defined."""
        expected_events = [
            "GOAL_CREATED",
            "GOAL_STARTED",
            "GOAL_STATE_CHANGED",
            "GOAL_PROGRESS",
            "GOAL_COMPLETED",
            "GOAL_FAILED",
            "AGENT_SPAWNED",
            "AGENT_STARTED",
            "AGENT_EXECUTING",
            "AGENT_COMPLETED",
            "TASK_CREATED",
            "TASK_PROGRESS",
            "TASK_COMPLETED",
            "CONNECTED",
            "PING",
            "PONG",
        ]

        for event_name in expected_events:
            assert hasattr(EventType, event_name), f"Missing event type: {event_name}"

    def test_event_type_values(self):
        """Test event type string values."""
        assert EventType.GOAL_CREATED.value == "goal.created"
        assert EventType.AGENT_SPAWNED.value == "agent.spawned"
        assert EventType.TASK_PROGRESS.value == "task.progress"
