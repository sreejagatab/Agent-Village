"""Tests for new API features: memory routes, log streaming, monitoring."""

import pytest
import pytest_asyncio
import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from src.api.memory_routes import (
    router as memory_router,
    MemorySearchRequest,
    MemorySearchResponse,
    MemoryEntryResponse,
    StoreMemoryRequest,
    memory_entry_to_response,
    get_memory_stores,
    init_memory_stores,
)
from src.api.log_streaming import (
    LogBuffer,
    LogEntry,
    LogLevel,
    LogCategory,
    emit_log,
    log_info,
    log_error,
    get_log_buffer,
)
from src.api.monitoring import (
    router as monitoring_router,
    DASHBOARD_HTML,
)
from src.memory.base import MemoryEntry, MemoryType


class TestMemoryRoutes:
    """Tests for memory search API routes."""

    def test_memory_search_request_validation(self):
        """Test MemorySearchRequest validation."""
        request = MemorySearchRequest(
            query="test query",
            memory_types=["episodic", "semantic"],
            limit=50,
        )

        assert request.query == "test query"
        assert request.memory_types == ["episodic", "semantic"]
        assert request.limit == 50
        assert request.min_importance == 0.0

    def test_memory_search_request_defaults(self):
        """Test MemorySearchRequest default values."""
        request = MemorySearchRequest(query="test")

        assert request.memory_types == ["episodic", "semantic", "strategic", "procedural"]
        assert request.goal_id is None
        assert request.agent_id is None
        assert request.tags == []
        assert request.limit == 20

    def test_store_memory_request_validation(self):
        """Test StoreMemoryRequest validation."""
        request = StoreMemoryRequest(
            memory_type="episodic",
            content={"event": "test"},
            summary="Test event",
            importance=0.8,
            tags=["test", "unit"],
        )

        assert request.memory_type == "episodic"
        assert request.content == {"event": "test"}
        assert request.summary == "Test event"
        assert request.importance == 0.8
        assert request.tags == ["test", "unit"]

    def test_memory_entry_to_response(self):
        """Test converting MemoryEntry to response model."""
        entry = MemoryEntry(
            memory_type=MemoryType.EPISODIC,
            content={"test": "data"},
            summary="Test entry",
            importance_score=0.7,
            tags=["tag1"],
            goal_id="goal-123",
        )

        response = memory_entry_to_response(entry, relevance=0.9)

        assert response.id == entry.id
        assert response.memory_type == "episodic"
        assert response.summary == "Test entry"
        assert response.importance_score == 0.7
        assert response.relevance_score == 0.9

    def test_memory_entry_response_model(self):
        """Test MemoryEntryResponse model."""
        response = MemoryEntryResponse(
            id="mem-123",
            memory_type="semantic",
            summary="Knowledge entry",
            content={"fact": "test"},
            importance_score=0.5,
            tags=["knowledge"],
            created_at="2024-01-01T00:00:00",
        )

        assert response.id == "mem-123"
        assert response.memory_type == "semantic"
        assert response.relevance_score == 0.0

    def test_init_memory_stores(self):
        """Test memory store initialization."""
        init_memory_stores()
        stores = get_memory_stores()

        assert "episodic" in stores
        assert "semantic" in stores
        assert "strategic" in stores
        assert "procedural" in stores


class TestLogBuffer:
    """Tests for log buffer functionality."""

    @pytest.fixture
    def log_buffer(self):
        """Create a fresh log buffer."""
        return LogBuffer(max_size=100)

    @pytest.mark.asyncio
    async def test_append_log(self, log_buffer):
        """Test appending log entries."""
        entry = LogEntry(
            id="log-1",
            timestamp=datetime.now(timezone.utc),
            level=LogLevel.INFO,
            category=LogCategory.AGENT,
            message="Test log message",
            source="test_agent",
        )

        await log_buffer.append(entry)
        logs = await log_buffer.get_recent(limit=10)

        assert len(logs) == 1
        assert logs[0].message == "Test log message"

    @pytest.mark.asyncio
    async def test_log_buffer_limit(self, log_buffer):
        """Test log buffer respects max size."""
        for i in range(150):
            entry = LogEntry(
                id=f"log-{i}",
                timestamp=datetime.now(timezone.utc),
                level=LogLevel.INFO,
                category=LogCategory.SYSTEM,
                message=f"Log {i}",
                source="test",
            )
            await log_buffer.append(entry)

        logs = await log_buffer.get_recent(limit=200)
        assert len(logs) <= 100  # Buffer max size

    @pytest.mark.asyncio
    async def test_log_filter_by_level(self, log_buffer):
        """Test filtering logs by level."""
        await log_buffer.append(LogEntry(
            id="1", timestamp=datetime.now(timezone.utc),
            level=LogLevel.DEBUG, category=LogCategory.SYSTEM,
            message="Debug", source="test"
        ))
        await log_buffer.append(LogEntry(
            id="2", timestamp=datetime.now(timezone.utc),
            level=LogLevel.ERROR, category=LogCategory.SYSTEM,
            message="Error", source="test"
        ))
        await log_buffer.append(LogEntry(
            id="3", timestamp=datetime.now(timezone.utc),
            level=LogLevel.INFO, category=LogCategory.SYSTEM,
            message="Info", source="test"
        ))

        error_logs = await log_buffer.get_recent(level=LogLevel.ERROR)
        assert len(error_logs) == 1
        assert error_logs[0].message == "Error"

    @pytest.mark.asyncio
    async def test_log_filter_by_category(self, log_buffer):
        """Test filtering logs by category."""
        await log_buffer.append(LogEntry(
            id="1", timestamp=datetime.now(timezone.utc),
            level=LogLevel.INFO, category=LogCategory.AGENT,
            message="Agent log", source="test"
        ))
        await log_buffer.append(LogEntry(
            id="2", timestamp=datetime.now(timezone.utc),
            level=LogLevel.INFO, category=LogCategory.GOAL,
            message="Goal log", source="test"
        ))

        agent_logs = await log_buffer.get_recent(category=LogCategory.AGENT)
        assert len(agent_logs) == 1
        assert agent_logs[0].category == LogCategory.AGENT

    @pytest.mark.asyncio
    async def test_log_filter_by_agent_id(self, log_buffer):
        """Test filtering logs by agent ID."""
        await log_buffer.append(LogEntry(
            id="1", timestamp=datetime.now(timezone.utc),
            level=LogLevel.INFO, category=LogCategory.AGENT,
            message="Agent 1 log", source="agent1",
            agent_id="agent-1"
        ))
        await log_buffer.append(LogEntry(
            id="2", timestamp=datetime.now(timezone.utc),
            level=LogLevel.INFO, category=LogCategory.AGENT,
            message="Agent 2 log", source="agent2",
            agent_id="agent-2"
        ))

        logs = await log_buffer.get_recent(agent_id="agent-1")
        assert len(logs) == 1
        assert logs[0].agent_id == "agent-1"

    @pytest.mark.asyncio
    async def test_log_stats(self, log_buffer):
        """Test getting log buffer statistics."""
        await log_buffer.append(LogEntry(
            id="1", timestamp=datetime.now(timezone.utc),
            level=LogLevel.INFO, category=LogCategory.AGENT,
            message="Info", source="test"
        ))
        await log_buffer.append(LogEntry(
            id="2", timestamp=datetime.now(timezone.utc),
            level=LogLevel.ERROR, category=LogCategory.SYSTEM,
            message="Error", source="test"
        ))

        stats = await log_buffer.get_stats()

        assert stats["total_entries"] == 2
        assert stats["by_level"]["info"] == 1
        assert stats["by_level"]["error"] == 1
        assert stats["by_category"]["agent"] == 1
        assert stats["by_category"]["system"] == 1

    @pytest.mark.asyncio
    async def test_log_subscription(self, log_buffer):
        """Test subscribing to log updates."""
        queue = await log_buffer.subscribe("test-subscriber")

        entry = LogEntry(
            id="1", timestamp=datetime.now(timezone.utc),
            level=LogLevel.INFO, category=LogCategory.SYSTEM,
            message="Test", source="test"
        )
        await log_buffer.append(entry)

        # Should receive the log
        received = await asyncio.wait_for(queue.get(), timeout=1.0)
        assert received.message == "Test"

        await log_buffer.unsubscribe("test-subscriber")


class TestLogEntry:
    """Tests for LogEntry dataclass."""

    def test_log_entry_creation(self):
        """Test creating a log entry."""
        entry = LogEntry(
            id="log-123",
            timestamp=datetime.now(timezone.utc),
            level=LogLevel.WARNING,
            category=LogCategory.TOOL,
            message="Tool execution warning",
            source="tool_agent",
            goal_id="goal-1",
            task_id="task-1",
            metadata={"duration_ms": 100},
        )

        assert entry.id == "log-123"
        assert entry.level == LogLevel.WARNING
        assert entry.category == LogCategory.TOOL
        assert entry.goal_id == "goal-1"
        assert entry.metadata["duration_ms"] == 100

    def test_log_entry_to_dict(self):
        """Test converting log entry to dict."""
        ts = datetime.now(timezone.utc)
        entry = LogEntry(
            id="log-1",
            timestamp=ts,
            level=LogLevel.INFO,
            category=LogCategory.AGENT,
            message="Test",
            source="test",
        )

        data = entry.to_dict()

        assert data["id"] == "log-1"
        assert data["level"] == "info"
        assert data["category"] == "agent"
        assert data["timestamp"] == ts.isoformat()


class TestLogEmitters:
    """Tests for log emitter functions."""

    @pytest.mark.asyncio
    async def test_emit_log(self):
        """Test emit_log function."""
        with patch('src.api.log_streaming.get_log_buffer') as mock_buffer, \
             patch('src.api.log_streaming.get_connection_manager') as mock_manager:

            mock_buffer_instance = MagicMock()
            mock_buffer_instance.append = AsyncMock()
            mock_buffer.return_value = mock_buffer_instance

            mock_manager_instance = MagicMock()
            mock_manager_instance.broadcast = AsyncMock()
            mock_manager.return_value = mock_manager_instance

            await emit_log(
                level=LogLevel.INFO,
                category=LogCategory.AGENT,
                message="Test log",
                source="test",
                agent_id="agent-1",
            )

            mock_buffer_instance.append.assert_called_once()
            mock_manager_instance.broadcast.assert_called_once()

    @pytest.mark.asyncio
    async def test_log_info_convenience(self):
        """Test log_info convenience function."""
        with patch('src.api.log_streaming.emit_log') as mock_emit:
            mock_emit.return_value = None

            await log_info(
                LogCategory.SYSTEM,
                "Info message",
                "test_source",
            )

            mock_emit.assert_called_once()
            args = mock_emit.call_args
            assert args[0][0] == LogLevel.INFO
            assert args[0][1] == LogCategory.SYSTEM


class TestMonitoringDashboard:
    """Tests for monitoring dashboard."""

    def test_dashboard_html_exists(self):
        """Test dashboard HTML is defined."""
        assert DASHBOARD_HTML is not None
        assert len(DASHBOARD_HTML) > 0

    def test_dashboard_contains_key_elements(self):
        """Test dashboard contains required elements."""
        assert "Agent Village Monitor" in DASHBOARD_HTML
        assert "agents-list" in DASHBOARD_HTML
        assert "logs-list" in DASHBOARD_HTML
        assert "goals-list" in DASHBOARD_HTML
        assert "WebSocket" in DASHBOARD_HTML

    def test_dashboard_has_styles(self):
        """Test dashboard has CSS styles."""
        assert "<style>" in DASHBOARD_HTML
        assert ".agent-card" in DASHBOARD_HTML
        assert ".log-entry" in DASHBOARD_HTML
        assert ".goal-card" in DASHBOARD_HTML

    def test_dashboard_has_javascript(self):
        """Test dashboard has JavaScript."""
        assert "<script>" in DASHBOARD_HTML
        assert "connectWebSocket" in DASHBOARD_HTML
        assert "fetchInitialData" in DASHBOARD_HTML


class TestLogLevel:
    """Tests for LogLevel enum."""

    def test_all_levels_defined(self):
        """Test all log levels are defined."""
        assert LogLevel.DEBUG.value == "debug"
        assert LogLevel.INFO.value == "info"
        assert LogLevel.WARNING.value == "warning"
        assert LogLevel.ERROR.value == "error"
        assert LogLevel.CRITICAL.value == "critical"


class TestLogCategory:
    """Tests for LogCategory enum."""

    def test_all_categories_defined(self):
        """Test all log categories are defined."""
        assert LogCategory.AGENT.value == "agent"
        assert LogCategory.GOAL.value == "goal"
        assert LogCategory.TASK.value == "task"
        assert LogCategory.TOOL.value == "tool"
        assert LogCategory.MEMORY.value == "memory"
        assert LogCategory.SYSTEM.value == "system"
        assert LogCategory.GOVERNOR.value == "governor"
        assert LogCategory.PROVIDER.value == "provider"
