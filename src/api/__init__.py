"""FastAPI application for Agent Village."""

from src.api.main import app, create_app
from src.api.websocket import (
    ConnectionManager,
    WebSocketEvent,
    EventType,
    get_connection_manager,
    emit_event,
    emit_goal_created,
    emit_goal_progress,
    emit_goal_state_changed,
    emit_goal_completed,
    emit_goal_failed,
    emit_agent_spawned,
    emit_agent_executing,
)
from src.api.memory_routes import router as memory_router, init_memory_stores
from src.api.log_streaming import (
    router as logs_router,
    LogBuffer,
    LogEntry,
    LogLevel,
    LogCategory,
    emit_log,
    log_info,
    log_warning,
    log_error,
    log_debug,
    log_critical,
    get_log_buffer,
)
from src.api.monitoring import router as monitoring_router

__all__ = [
    # Main app
    "app",
    "create_app",
    # WebSocket
    "ConnectionManager",
    "WebSocketEvent",
    "EventType",
    "get_connection_manager",
    "emit_event",
    "emit_goal_created",
    "emit_goal_progress",
    "emit_goal_state_changed",
    "emit_goal_completed",
    "emit_goal_failed",
    "emit_agent_spawned",
    "emit_agent_executing",
    # Memory routes
    "memory_router",
    "init_memory_stores",
    # Log streaming
    "logs_router",
    "LogBuffer",
    "LogEntry",
    "LogLevel",
    "LogCategory",
    "emit_log",
    "log_info",
    "log_warning",
    "log_error",
    "log_debug",
    "log_critical",
    "get_log_buffer",
    # Monitoring
    "monitoring_router",
]
