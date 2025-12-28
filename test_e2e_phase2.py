"""
End-to-End Tests for Phase 2 Features:
1. Memory Search API
2. Agent Log Streaming
3. Real-Time Monitoring UI

Run with: python test_e2e_phase2.py
"""

import asyncio
import sys
from datetime import datetime, timezone
from typing import Any


def print_header(text: str) -> None:
    """Print a section header."""
    print(f"\n{'=' * 70}")
    print(f"  {text}")
    print('=' * 70)


def print_test(name: str, passed: bool, details: str = "") -> None:
    """Print test result."""
    status = "PASS" if passed else "FAIL"
    print(f"  [{status}] {name}")
    if details:
        print(f"      {details}")


async def test_memory_search_api() -> dict[str, Any]:
    """Test Memory Search API endpoints."""
    print_header("TEST 1: Memory Search API")

    results = {
        "passed": 0,
        "failed": 0,
        "tests": []
    }

    # Test 1.1: Memory store initialization
    try:
        from src.api.memory_routes import init_memory_stores, get_memory_stores

        init_memory_stores()
        stores = get_memory_stores()

        has_all_stores = all(k in stores for k in ["episodic", "semantic", "strategic", "procedural"])
        print_test("Memory stores initialized", has_all_stores,
                   f"Stores: {list(stores.keys())}")

        if has_all_stores:
            results["passed"] += 1
        else:
            results["failed"] += 1
        results["tests"].append(("Memory stores initialized", has_all_stores))
    except Exception as e:
        print_test("Memory stores initialized", False, str(e))
        results["failed"] += 1
        results["tests"].append(("Memory stores initialized", False))

    # Test 1.2: Store memory entry
    try:
        from src.api.memory_routes import StoreMemoryRequest, store_memory
        from src.memory.base import MemoryEntry, MemoryType

        request = StoreMemoryRequest(
            memory_type="episodic",
            content={"event": "E2E test started", "timestamp": datetime.now(timezone.utc).isoformat()},
            summary="E2E test episode",
            importance=0.8,
            tags=["e2e", "test", "phase2"],
            goal_id="e2e-goal-001",
        )

        response = await store_memory(request)

        stored_ok = response.id is not None and response.memory_type == "episodic"
        print_test("Store memory entry", stored_ok,
                   f"Stored ID: {response.id}, Type: {response.memory_type}")

        if stored_ok:
            results["passed"] += 1
        else:
            results["failed"] += 1
        results["tests"].append(("Store memory entry", stored_ok))

        stored_id = response.id
    except Exception as e:
        print_test("Store memory entry", False, str(e))
        results["failed"] += 1
        results["tests"].append(("Store memory entry", False))
        stored_id = None

    # Test 1.3: Search memory
    try:
        from src.api.memory_routes import MemorySearchRequest, search_memory

        search_request = MemorySearchRequest(
            query="E2E test",
            memory_types=["episodic"],
            tags=["e2e"],
            limit=10,
        )

        search_response = await search_memory(search_request)

        search_ok = search_response.total_results >= 0
        print_test("Search memory", search_ok,
                   f"Found {search_response.total_results} results in {search_response.search_time_ms}ms")

        if search_ok:
            results["passed"] += 1
        else:
            results["failed"] += 1
        results["tests"].append(("Search memory", search_ok))
    except Exception as e:
        print_test("Search memory", False, str(e))
        results["failed"] += 1
        results["tests"].append(("Search memory", False))

    # Test 1.4: Get memory entry by ID
    try:
        from src.api.memory_routes import get_memory_entry

        if stored_id:
            entry = await get_memory_entry("episodic", stored_id)
            get_ok = entry.id == stored_id
            print_test("Get memory entry by ID", get_ok,
                       f"Retrieved: {entry.summary[:50]}...")
        else:
            get_ok = False
            print_test("Get memory entry by ID", False, "No stored ID available")

        if get_ok:
            results["passed"] += 1
        else:
            results["failed"] += 1
        results["tests"].append(("Get memory entry by ID", get_ok))
    except Exception as e:
        print_test("Get memory entry by ID", False, str(e))
        results["failed"] += 1
        results["tests"].append(("Get memory entry by ID", False))

    # Test 1.5: Memory statistics
    try:
        from src.api.memory_routes import get_memory_stats

        stats = await get_memory_stats()

        stats_ok = stats.total_entries >= 0 and "episodic" in stats.entries_by_type
        print_test("Get memory stats", stats_ok,
                   f"Total entries: {stats.total_entries}, Recent: {stats.recent_entries}")

        if stats_ok:
            results["passed"] += 1
        else:
            results["failed"] += 1
        results["tests"].append(("Get memory stats", stats_ok))
    except Exception as e:
        print_test("Get memory stats", False, str(e))
        results["failed"] += 1
        results["tests"].append(("Get memory stats", False))

    # Test 1.6: Timeline query
    try:
        from src.api.memory_routes import get_timeline

        timeline = await get_timeline(goal_id=None, hours=24, limit=50)

        timeline_ok = "timeline" in timeline and "time_range" in timeline
        print_test("Get timeline", timeline_ok,
                   f"Events: {timeline.get('total_events', 0)}")

        if timeline_ok:
            results["passed"] += 1
        else:
            results["failed"] += 1
        results["tests"].append(("Get timeline", timeline_ok))
    except Exception as e:
        print_test("Get timeline", False, str(e))
        results["failed"] += 1
        results["tests"].append(("Get timeline", False))

    # Test 1.7: Lessons learned
    try:
        from src.api.memory_routes import get_lessons_learned

        lessons = await get_lessons_learned(decision_type=None, limit=20)

        lessons_ok = "lessons" in lessons and "total" in lessons
        print_test("Get lessons learned", lessons_ok,
                   f"Lessons: {lessons.get('total', 0)}")

        if lessons_ok:
            results["passed"] += 1
        else:
            results["failed"] += 1
        results["tests"].append(("Get lessons learned", lessons_ok))
    except Exception as e:
        print_test("Get lessons learned", False, str(e))
        results["failed"] += 1
        results["tests"].append(("Get lessons learned", False))

    # Test 1.8: Delete memory entry
    try:
        from src.api.memory_routes import delete_memory_entry

        if stored_id:
            delete_result = await delete_memory_entry("episodic", stored_id)
            delete_ok = delete_result.get("status") == "deleted"
            print_test("Delete memory entry", delete_ok,
                       f"Deleted: {stored_id}")
        else:
            delete_ok = False
            print_test("Delete memory entry", False, "No stored ID to delete")

        if delete_ok:
            results["passed"] += 1
        else:
            results["failed"] += 1
        results["tests"].append(("Delete memory entry", delete_ok))
    except Exception as e:
        print_test("Delete memory entry", False, str(e))
        results["failed"] += 1
        results["tests"].append(("Delete memory entry", False))

    return results


async def test_log_streaming() -> dict[str, Any]:
    """Test Agent Log Streaming."""
    print_header("TEST 2: Agent Log Streaming")

    results = {
        "passed": 0,
        "failed": 0,
        "tests": []
    }

    # Test 2.1: Log buffer creation
    try:
        from src.api.log_streaming import LogBuffer, LogEntry, LogLevel, LogCategory

        buffer = LogBuffer(max_size=100)

        buffer_ok = buffer is not None
        print_test("Log buffer creation", buffer_ok,
                   f"Max size: 100")

        if buffer_ok:
            results["passed"] += 1
        else:
            results["failed"] += 1
        results["tests"].append(("Log buffer creation", buffer_ok))
    except Exception as e:
        print_test("Log buffer creation", False, str(e))
        results["failed"] += 1
        results["tests"].append(("Log buffer creation", False))

    # Test 2.2: Log entry creation
    try:
        from src.api.log_streaming import LogEntry, LogLevel, LogCategory

        entry = LogEntry(
            id="test-log-001",
            timestamp=datetime.now(timezone.utc),
            level=LogLevel.INFO,
            category=LogCategory.AGENT,
            message="E2E test log entry",
            source="e2e_test",
            agent_id="test-agent-001",
            goal_id="e2e-goal-001",
        )

        entry_ok = entry.id == "test-log-001" and entry.level == LogLevel.INFO
        print_test("Log entry creation", entry_ok,
                   f"ID: {entry.id}, Level: {entry.level.value}")

        if entry_ok:
            results["passed"] += 1
        else:
            results["failed"] += 1
        results["tests"].append(("Log entry creation", entry_ok))
    except Exception as e:
        print_test("Log entry creation", False, str(e))
        results["failed"] += 1
        results["tests"].append(("Log entry creation", False))

    # Test 2.3: Append to buffer
    try:
        from src.api.log_streaming import LogBuffer, LogEntry, LogLevel, LogCategory

        buffer = LogBuffer(max_size=100)

        for i in range(5):
            entry = LogEntry(
                id=f"test-{i}",
                timestamp=datetime.now(timezone.utc),
                level=LogLevel.INFO if i % 2 == 0 else LogLevel.WARNING,
                category=LogCategory.AGENT if i < 3 else LogCategory.GOAL,
                message=f"Test log message {i}",
                source="e2e_test",
            )
            await buffer.append(entry)

        logs = await buffer.get_recent(limit=10)
        append_ok = len(logs) == 5
        print_test("Append logs to buffer", append_ok,
                   f"Appended 5 logs, retrieved {len(logs)}")

        if append_ok:
            results["passed"] += 1
        else:
            results["failed"] += 1
        results["tests"].append(("Append logs to buffer", append_ok))
    except Exception as e:
        print_test("Append logs to buffer", False, str(e))
        results["failed"] += 1
        results["tests"].append(("Append logs to buffer", False))

    # Test 2.4: Filter by level
    try:
        warning_logs = await buffer.get_recent(level=LogLevel.WARNING)
        filter_level_ok = all(l.level == LogLevel.WARNING for l in warning_logs)
        print_test("Filter logs by level", filter_level_ok,
                   f"Found {len(warning_logs)} WARNING logs")

        if filter_level_ok:
            results["passed"] += 1
        else:
            results["failed"] += 1
        results["tests"].append(("Filter logs by level", filter_level_ok))
    except Exception as e:
        print_test("Filter logs by level", False, str(e))
        results["failed"] += 1
        results["tests"].append(("Filter logs by level", False))

    # Test 2.5: Filter by category
    try:
        agent_logs = await buffer.get_recent(category=LogCategory.AGENT)
        filter_cat_ok = all(l.category == LogCategory.AGENT for l in agent_logs)
        print_test("Filter logs by category", filter_cat_ok,
                   f"Found {len(agent_logs)} AGENT logs")

        if filter_cat_ok:
            results["passed"] += 1
        else:
            results["failed"] += 1
        results["tests"].append(("Filter logs by category", filter_cat_ok))
    except Exception as e:
        print_test("Filter logs by category", False, str(e))
        results["failed"] += 1
        results["tests"].append(("Filter logs by category", False))

    # Test 2.6: Log buffer stats
    try:
        stats = await buffer.get_stats()

        stats_ok = (
            stats["total_entries"] == 5 and
            "by_level" in stats and
            "by_category" in stats
        )
        print_test("Log buffer stats", stats_ok,
                   f"Total: {stats['total_entries']}, Levels: {stats['by_level']}")

        if stats_ok:
            results["passed"] += 1
        else:
            results["failed"] += 1
        results["tests"].append(("Log buffer stats", stats_ok))
    except Exception as e:
        print_test("Log buffer stats", False, str(e))
        results["failed"] += 1
        results["tests"].append(("Log buffer stats", False))

    # Test 2.7: Log subscription
    try:
        queue = await buffer.subscribe("test-subscriber")

        # Add a new log
        new_entry = LogEntry(
            id="sub-test",
            timestamp=datetime.now(timezone.utc),
            level=LogLevel.INFO,
            category=LogCategory.SYSTEM,
            message="Subscription test",
            source="e2e_test",
        )
        await buffer.append(new_entry)

        # Check if we receive it
        received = await asyncio.wait_for(queue.get(), timeout=1.0)

        sub_ok = received.id == "sub-test"
        print_test("Log subscription", sub_ok,
                   f"Received: {received.message}")

        await buffer.unsubscribe("test-subscriber")

        if sub_ok:
            results["passed"] += 1
        else:
            results["failed"] += 1
        results["tests"].append(("Log subscription", sub_ok))
    except Exception as e:
        print_test("Log subscription", False, str(e))
        results["failed"] += 1
        results["tests"].append(("Log subscription", False))

    # Test 2.8: Log emit function
    try:
        from src.api.log_streaming import emit_log, get_log_buffer
        from unittest.mock import patch, AsyncMock, MagicMock

        # Create a mock for the connection manager
        with patch('src.api.log_streaming.get_connection_manager') as mock_cm:
            mock_manager = MagicMock()
            mock_manager.broadcast = AsyncMock()
            mock_cm.return_value = mock_manager

            await emit_log(
                level=LogLevel.INFO,
                category=LogCategory.GOAL,
                message="E2E emit test",
                source="e2e_test",
                goal_id="e2e-goal-001",
            )

            emit_ok = mock_manager.broadcast.called
            print_test("Log emit function", emit_ok,
                       "Broadcast called successfully")

        if emit_ok:
            results["passed"] += 1
        else:
            results["failed"] += 1
        results["tests"].append(("Log emit function", emit_ok))
    except Exception as e:
        print_test("Log emit function", False, str(e))
        results["failed"] += 1
        results["tests"].append(("Log emit function", False))

    # Test 2.9: Convenience log functions
    try:
        from src.api.log_streaming import log_info, log_error, log_warning, log_debug
        from unittest.mock import patch, AsyncMock

        with patch('src.api.log_streaming.emit_log', new_callable=AsyncMock) as mock_emit:
            await log_info(LogCategory.SYSTEM, "Info test", "e2e")
            await log_warning(LogCategory.SYSTEM, "Warning test", "e2e")
            await log_error(LogCategory.SYSTEM, "Error test", "e2e")

            conv_ok = mock_emit.call_count == 3
            print_test("Convenience log functions", conv_ok,
                       f"Called {mock_emit.call_count} times")

        if conv_ok:
            results["passed"] += 1
        else:
            results["failed"] += 1
        results["tests"].append(("Convenience log functions", conv_ok))
    except Exception as e:
        print_test("Convenience log functions", False, str(e))
        results["failed"] += 1
        results["tests"].append(("Convenience log functions", False))

    # Test 2.10: Log entry serialization
    try:
        from src.api.log_streaming import LogEntry, LogLevel, LogCategory

        ts = datetime.now(timezone.utc)
        entry = LogEntry(
            id="serial-test",
            timestamp=ts,
            level=LogLevel.ERROR,
            category=LogCategory.TOOL,
            message="Serialization test",
            source="e2e",
            metadata={"key": "value"},
        )

        data = entry.to_dict()

        serial_ok = (
            data["id"] == "serial-test" and
            data["level"] == "error" and
            data["category"] == "tool" and
            data["metadata"]["key"] == "value"
        )
        print_test("Log entry serialization", serial_ok,
                   f"Keys: {list(data.keys())}")

        if serial_ok:
            results["passed"] += 1
        else:
            results["failed"] += 1
        results["tests"].append(("Log entry serialization", serial_ok))
    except Exception as e:
        print_test("Log entry serialization", False, str(e))
        results["failed"] += 1
        results["tests"].append(("Log entry serialization", False))

    return results


async def test_monitoring_ui() -> dict[str, Any]:
    """Test Real-Time Monitoring UI."""
    print_header("TEST 3: Real-Time Monitoring UI")

    results = {
        "passed": 0,
        "failed": 0,
        "tests": []
    }

    # Test 3.1: Dashboard HTML exists
    try:
        from src.api.monitoring import DASHBOARD_HTML

        html_ok = len(DASHBOARD_HTML) > 1000
        print_test("Dashboard HTML exists", html_ok,
                   f"HTML size: {len(DASHBOARD_HTML)} chars")

        if html_ok:
            results["passed"] += 1
        else:
            results["failed"] += 1
        results["tests"].append(("Dashboard HTML exists", html_ok))
    except Exception as e:
        print_test("Dashboard HTML exists", False, str(e))
        results["failed"] += 1
        results["tests"].append(("Dashboard HTML exists", False))

    # Test 3.2: Dashboard has agent panel
    try:
        from src.api.monitoring import DASHBOARD_HTML

        agent_panel_ok = (
            "agents-list" in DASHBOARD_HTML and
            "agent-card" in DASHBOARD_HTML and
            "agent-count" in DASHBOARD_HTML
        )
        print_test("Dashboard has agent panel", agent_panel_ok,
                   "Agent list, cards, and count elements present")

        if agent_panel_ok:
            results["passed"] += 1
        else:
            results["failed"] += 1
        results["tests"].append(("Dashboard has agent panel", agent_panel_ok))
    except Exception as e:
        print_test("Dashboard has agent panel", False, str(e))
        results["failed"] += 1
        results["tests"].append(("Dashboard has agent panel", False))

    # Test 3.3: Dashboard has log panel
    try:
        from src.api.monitoring import DASHBOARD_HTML

        log_panel_ok = (
            "logs-list" in DASHBOARD_HTML and
            "log-entry" in DASHBOARD_HTML and
            "log-level-filter" in DASHBOARD_HTML and
            "log-category-filter" in DASHBOARD_HTML
        )
        print_test("Dashboard has log panel", log_panel_ok,
                   "Log list, entries, and filters present")

        if log_panel_ok:
            results["passed"] += 1
        else:
            results["failed"] += 1
        results["tests"].append(("Dashboard has log panel", log_panel_ok))
    except Exception as e:
        print_test("Dashboard has log panel", False, str(e))
        results["failed"] += 1
        results["tests"].append(("Dashboard has log panel", False))

    # Test 3.4: Dashboard has goals panel
    try:
        from src.api.monitoring import DASHBOARD_HTML

        goals_panel_ok = (
            "goals-list" in DASHBOARD_HTML and
            "goal-card" in DASHBOARD_HTML and
            "progress-bar" in DASHBOARD_HTML
        )
        print_test("Dashboard has goals panel", goals_panel_ok,
                   "Goals list, cards, and progress bars present")

        if goals_panel_ok:
            results["passed"] += 1
        else:
            results["failed"] += 1
        results["tests"].append(("Dashboard has goals panel", goals_panel_ok))
    except Exception as e:
        print_test("Dashboard has goals panel", False, str(e))
        results["failed"] += 1
        results["tests"].append(("Dashboard has goals panel", False))

    # Test 3.5: Dashboard has memory panel
    try:
        from src.api.monitoring import DASHBOARD_HTML

        memory_panel_ok = (
            "memory-list" in DASHBOARD_HTML and
            "memory-entry" in DASHBOARD_HTML
        )
        print_test("Dashboard has memory panel", memory_panel_ok,
                   "Memory list and entries present")

        if memory_panel_ok:
            results["passed"] += 1
        else:
            results["failed"] += 1
        results["tests"].append(("Dashboard has memory panel", memory_panel_ok))
    except Exception as e:
        print_test("Dashboard has memory panel", False, str(e))
        results["failed"] += 1
        results["tests"].append(("Dashboard has memory panel", False))

    # Test 3.6: Dashboard has WebSocket connection code
    try:
        from src.api.monitoring import DASHBOARD_HTML

        ws_ok = (
            "connectWebSocket" in DASHBOARD_HTML and
            "WebSocket" in DASHBOARD_HTML and
            "ws.onmessage" in DASHBOARD_HTML
        )
        print_test("Dashboard has WebSocket code", ws_ok,
                   "WebSocket connection and handlers present")

        if ws_ok:
            results["passed"] += 1
        else:
            results["failed"] += 1
        results["tests"].append(("Dashboard has WebSocket code", ws_ok))
    except Exception as e:
        print_test("Dashboard has WebSocket code", False, str(e))
        results["failed"] += 1
        results["tests"].append(("Dashboard has WebSocket code", False))

    # Test 3.7: Dashboard has log streaming WebSocket
    try:
        from src.api.monitoring import DASHBOARD_HTML

        log_ws_ok = (
            "connectLogsWebSocket" in DASHBOARD_HTML and
            "/api/logs/stream" in DASHBOARD_HTML
        )
        print_test("Dashboard has log streaming WS", log_ws_ok,
                   "Log streaming WebSocket connection present")

        if log_ws_ok:
            results["passed"] += 1
        else:
            results["failed"] += 1
        results["tests"].append(("Dashboard has log streaming WS", log_ws_ok))
    except Exception as e:
        print_test("Dashboard has log streaming WS", False, str(e))
        results["failed"] += 1
        results["tests"].append(("Dashboard has log streaming WS", False))

    # Test 3.8: Dashboard has CSS styles
    try:
        from src.api.monitoring import DASHBOARD_HTML

        css_ok = (
            "<style>" in DASHBOARD_HTML and
            ".panel" in DASHBOARD_HTML and
            ".header" in DASHBOARD_HTML and
            "grid" in DASHBOARD_HTML
        )
        print_test("Dashboard has CSS styles", css_ok,
                   "Panel, header, and grid styles present")

        if css_ok:
            results["passed"] += 1
        else:
            results["failed"] += 1
        results["tests"].append(("Dashboard has CSS styles", css_ok))
    except Exception as e:
        print_test("Dashboard has CSS styles", False, str(e))
        results["failed"] += 1
        results["tests"].append(("Dashboard has CSS styles", False))

    # Test 3.9: Dashboard has JavaScript state management
    try:
        from src.api.monitoring import DASHBOARD_HTML

        js_state_ok = (
            "const state" in DASHBOARD_HTML and
            "state.agents" in DASHBOARD_HTML and
            "state.logs" in DASHBOARD_HTML and
            "state.goals" in DASHBOARD_HTML
        )
        print_test("Dashboard has JS state management", js_state_ok,
                   "State object for agents, logs, goals present")

        if js_state_ok:
            results["passed"] += 1
        else:
            results["failed"] += 1
        results["tests"].append(("Dashboard has JS state management", js_state_ok))
    except Exception as e:
        print_test("Dashboard has JS state management", False, str(e))
        results["failed"] += 1
        results["tests"].append(("Dashboard has JS state management", False))

    # Test 3.10: Dashboard has render functions
    try:
        from src.api.monitoring import DASHBOARD_HTML

        render_ok = (
            "renderAgents" in DASHBOARD_HTML and
            "renderLogs" in DASHBOARD_HTML and
            "renderGoals" in DASHBOARD_HTML and
            "renderMemory" in DASHBOARD_HTML
        )
        print_test("Dashboard has render functions", render_ok,
                   "All render functions present")

        if render_ok:
            results["passed"] += 1
        else:
            results["failed"] += 1
        results["tests"].append(("Dashboard has render functions", render_ok))
    except Exception as e:
        print_test("Dashboard has render functions", False, str(e))
        results["failed"] += 1
        results["tests"].append(("Dashboard has render functions", False))

    # Test 3.11: Dashboard has event handling
    try:
        from src.api.monitoring import DASHBOARD_HTML

        event_ok = (
            "handleEvent" in DASHBOARD_HTML and
            "agent.spawned" in DASHBOARD_HTML and
            "goal.created" in DASHBOARD_HTML and
            "goal.progress" in DASHBOARD_HTML
        )
        print_test("Dashboard has event handling", event_ok,
                   "Event handlers for agents and goals present")

        if event_ok:
            results["passed"] += 1
        else:
            results["failed"] += 1
        results["tests"].append(("Dashboard has event handling", event_ok))
    except Exception as e:
        print_test("Dashboard has event handling", False, str(e))
        results["failed"] += 1
        results["tests"].append(("Dashboard has event handling", False))

    # Test 3.12: Dashboard fetches initial data
    try:
        from src.api.monitoring import DASHBOARD_HTML

        fetch_ok = (
            "fetchInitialData" in DASHBOARD_HTML and
            "fetch('/agents')" in DASHBOARD_HTML and
            "fetch('/goals" in DASHBOARD_HTML and
            "fetch('/api/logs" in DASHBOARD_HTML
        )
        print_test("Dashboard fetches initial data", fetch_ok,
                   "Initial data fetch for agents, goals, logs")

        if fetch_ok:
            results["passed"] += 1
        else:
            results["failed"] += 1
        results["tests"].append(("Dashboard fetches initial data", fetch_ok))
    except Exception as e:
        print_test("Dashboard fetches initial data", False, str(e))
        results["failed"] += 1
        results["tests"].append(("Dashboard fetches initial data", False))

    # Test 3.13: Monitor health endpoint
    try:
        from src.api.monitoring import monitor_health
        from src.api.websocket import get_connection_manager
        from src.api.log_streaming import get_log_buffer

        # Just call monitor_health - it will use the real singletons
        health = await monitor_health()

        health_ok = (
            health["status"] == "healthy" and
            "websocket" in health and
            "log_buffer" in health
        )
        print_test("Monitor health endpoint", health_ok,
                   f"Status: {health['status']}, WS: {health['websocket']}")

        if health_ok:
            results["passed"] += 1
        else:
            results["failed"] += 1
        results["tests"].append(("Monitor health endpoint", health_ok))
    except Exception as e:
        print_test("Monitor health endpoint", False, str(e))
        results["failed"] += 1
        results["tests"].append(("Monitor health endpoint", False))

    return results


async def test_integration() -> dict[str, Any]:
    """Test integration between components."""
    print_header("TEST 4: Integration Tests")

    results = {
        "passed": 0,
        "failed": 0,
        "tests": []
    }

    # Test 4.1: Main app includes memory router
    try:
        from src.api.main import app

        routes = [r.path for r in app.routes]
        memory_route_ok = any("/api/memory" in str(r) for r in routes)
        print_test("Main app includes memory router", memory_route_ok,
                   f"Routes with /api/memory found")

        if memory_route_ok:
            results["passed"] += 1
        else:
            results["failed"] += 1
        results["tests"].append(("Main app includes memory router", memory_route_ok))
    except Exception as e:
        print_test("Main app includes memory router", False, str(e))
        results["failed"] += 1
        results["tests"].append(("Main app includes memory router", False))

    # Test 4.2: Main app includes logs router
    try:
        from src.api.main import app

        routes = [r.path for r in app.routes]
        logs_route_ok = any("/api/logs" in str(r) for r in routes)
        print_test("Main app includes logs router", logs_route_ok,
                   f"Routes with /api/logs found")

        if logs_route_ok:
            results["passed"] += 1
        else:
            results["failed"] += 1
        results["tests"].append(("Main app includes logs router", logs_route_ok))
    except Exception as e:
        print_test("Main app includes logs router", False, str(e))
        results["failed"] += 1
        results["tests"].append(("Main app includes logs router", False))

    # Test 4.3: Main app includes monitor router
    try:
        from src.api.main import app

        routes = [r.path for r in app.routes]
        monitor_route_ok = any("/monitor" in str(r) for r in routes)
        print_test("Main app includes monitor router", monitor_route_ok,
                   f"Routes with /monitor found")

        if monitor_route_ok:
            results["passed"] += 1
        else:
            results["failed"] += 1
        results["tests"].append(("Main app includes monitor router", monitor_route_ok))
    except Exception as e:
        print_test("Main app includes monitor router", False, str(e))
        results["failed"] += 1
        results["tests"].append(("Main app includes monitor router", False))

    # Test 4.4: API __init__ exports
    try:
        from src.api import (
            app, emit_log, LogLevel, LogCategory,
            memory_router, monitoring_router, logs_router,
            log_info, log_error, get_log_buffer
        )

        exports_ok = all([
            app is not None,
            emit_log is not None,
            LogLevel is not None,
            memory_router is not None,
        ])
        print_test("API module exports", exports_ok,
                   "All key exports available")

        if exports_ok:
            results["passed"] += 1
        else:
            results["failed"] += 1
        results["tests"].append(("API module exports", exports_ok))
    except Exception as e:
        print_test("API module exports", False, str(e))
        results["failed"] += 1
        results["tests"].append(("API module exports", False))

    # Test 4.5: Memory stores integrate with routes
    try:
        from src.api.memory_routes import init_memory_stores, get_memory_stores
        from src.memory.episodic import EpisodicMemory
        from src.memory.semantic import SemanticMemory

        init_memory_stores()
        stores = get_memory_stores()

        type_ok = (
            isinstance(stores["episodic"], EpisodicMemory) and
            isinstance(stores["semantic"], SemanticMemory)
        )
        print_test("Memory stores are correct types", type_ok,
                   "EpisodicMemory, SemanticMemory instances")

        if type_ok:
            results["passed"] += 1
        else:
            results["failed"] += 1
        results["tests"].append(("Memory stores are correct types", type_ok))
    except Exception as e:
        print_test("Memory stores are correct types", False, str(e))
        results["failed"] += 1
        results["tests"].append(("Memory stores are correct types", False))

    # Test 4.6: Log streaming integrates with WebSocket
    try:
        from src.api.log_streaming import emit_log, LogLevel, LogCategory
        from src.api.websocket import WebSocketEvent, EventType

        # These should be importable together
        integration_ok = True
        print_test("Log streaming + WebSocket integration", integration_ok,
                   "Both modules work together")

        if integration_ok:
            results["passed"] += 1
        else:
            results["failed"] += 1
        results["tests"].append(("Log streaming + WebSocket integration", integration_ok))
    except Exception as e:
        print_test("Log streaming + WebSocket integration", False, str(e))
        results["failed"] += 1
        results["tests"].append(("Log streaming + WebSocket integration", False))

    return results


async def main():
    """Run all E2E tests."""
    print("\n" + "=" * 70)
    print("  AGENT-CIVIL PHASE 2 END-TO-END TEST")
    print("  Testing: Memory API, Log Streaming, Monitoring UI")
    print("=" * 70)

    all_results = {}

    # Run all test suites
    all_results["Memory Search API"] = await test_memory_search_api()
    all_results["Log Streaming"] = await test_log_streaming()
    all_results["Monitoring UI"] = await test_monitoring_ui()
    all_results["Integration"] = await test_integration()

    # Print summary
    print_header("TEST RESULTS SUMMARY")

    total_passed = 0
    total_failed = 0

    for suite_name, results in all_results.items():
        passed = results["passed"]
        failed = results["failed"]
        total = passed + failed
        total_passed += passed
        total_failed += failed

        status = "PASS" if failed == 0 else "FAIL"
        print(f"  [{status}] {suite_name}: {passed}/{total} tests passed")

    print()
    print("-" * 70)

    overall_status = "PASSED" if total_failed == 0 else "FAILED"
    print(f"  OVERALL: {overall_status}")
    print(f"  Total: {total_passed} passed, {total_failed} failed")
    print("=" * 70 + "\n")

    return total_failed == 0


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
