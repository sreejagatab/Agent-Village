"""
FastAPI application for Agent Village.

Provides REST API and WebSocket endpoints for goal management,
agent monitoring, and memory queries.
"""

from contextlib import asynccontextmanager
from typing import Any

import structlog
from fastapi import FastAPI, HTTPException, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.agents import PlannerAgent, ToolAgent, CriticAgent
from src.agents.base import AgentType
from src.api.websocket import (
    emit_goal_created,
    emit_goal_state_changed,
    get_connection_manager,
    goal_websocket_endpoint,
    websocket_endpoint,
)
from src.config import get_settings
from src.core.governor import Governor, create_governor
from src.core.message import Goal, GoalStatus, Priority
from src.core.registry import AgentRegistry, init_registry
from src.core.safety import get_safety_gate
from src.persistence.database import init_database, close_database
from src.persistence.repositories import GoalRepository
from src.providers.anthropic import create_anthropic_providers
from src.providers.base import ProviderPool
from src.providers.ollama import create_ollama_provider
from src.providers.openai import create_openai_providers
from src.tools.registry import get_tool_registry
from src.tools.sandbox import create_sandbox_tools
from src.tools.file import create_file_tools
from src.tools.web import create_web_tools

logger = structlog.get_logger()

# Global instances
_provider_pool: ProviderPool | None = None
_registry: AgentRegistry | None = None
_governor: Governor | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global _provider_pool, _registry, _governor

    logger.info("Starting Agent Village API")

    # Initialize database
    try:
        await init_database()
        logger.info("Database initialized")
    except Exception as e:
        logger.error("Failed to initialize database", error=str(e))

    # Initialize provider pool
    _provider_pool = ProviderPool()

    # Register providers
    for key, provider in create_anthropic_providers().items():
        _provider_pool.register(key, provider)
    for key, provider in create_openai_providers().items():
        _provider_pool.register(key, provider)
    for key, provider in create_ollama_provider().items():
        _provider_pool.register(key, provider)

    # Initialize registry
    _registry = init_registry(_provider_pool)

    # Register agent factories
    _registry.register_factory(
        AgentType.TOOL,
        ToolAgent,
        default_provider_key="openai_gpt4_mini",  # Use cheaper model for tool agents
    )
    _registry.register_factory(
        AgentType.PLANNER,
        PlannerAgent,
        default_provider_key="openai_gpt4",
    )
    _registry.register_factory(
        AgentType.CRITIC,
        CriticAgent,
        default_provider_key="openai_gpt4_mini",
    )
    logger.info("Agent factories registered", count=3)

    # Register all tools
    tool_registry = get_tool_registry()
    for tool in create_sandbox_tools():
        tool_registry.register(tool)
    for tool in create_file_tools():
        tool_registry.register(tool)
    for tool in create_web_tools():
        tool_registry.register(tool)
    logger.info("Tools registered", count=len(tool_registry.list_tools()))

    # Set permissions for tool agents to use file and code tools
    from src.tools.registry import ToolPermission
    tool_registry.set_permission("tool", "write_file", ToolPermission.READ_WRITE)
    tool_registry.set_permission("tool", "read_file", ToolPermission.READ_ONLY)
    tool_registry.set_permission("tool", "delete_file", ToolPermission.READ_WRITE)
    tool_registry.set_permission("tool", "create_directory", ToolPermission.READ_WRITE)
    tool_registry.set_permission("tool", "copy_file", ToolPermission.READ_WRITE)
    tool_registry.set_permission("tool", "move_file", ToolPermission.READ_WRITE)
    tool_registry.set_permission("tool", "execute_python", ToolPermission.EXECUTE)
    tool_registry.set_permission("tool", "shell_command", ToolPermission.EXECUTE)
    logger.info("Tool permissions configured for tool agents")

    # Create governor
    try:
        governor_provider = await _provider_pool.get_for_agent_type("governor")
        _governor = await create_governor(
            governor_provider,
            _registry,
            get_safety_gate(),
        )
        logger.info("Governor initialized")
    except Exception as e:
        logger.error("Failed to initialize governor", error=str(e))

    yield

    # Shutdown
    logger.info("Shutting down Agent Village API")
    if _registry:
        await _registry.shutdown_all()
    await close_database()


# Create FastAPI app
app = FastAPI(
    title="Agent Village API",
    description="Production-grade multi-agent orchestration system",
    version="0.1.0",
    lifespan=lifespan,
)

# Configure CORS
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.api.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request/Response models
class GoalCreate(BaseModel):
    """Request to create a new goal."""

    description: str = Field(..., min_length=1, max_length=10000)
    context: dict[str, Any] = Field(default_factory=dict)
    priority: int = Field(default=2, ge=1, le=5)
    success_criteria: list[str] = Field(default_factory=list)
    async_execution: bool = Field(default=True, description="Run goal asynchronously via task queue")


class GoalResponse(BaseModel):
    """Response with goal information."""

    id: str
    description: str
    status: str
    priority: int
    created_at: str
    result: Any = None
    error: str | None = None
    task_id: str | None = None  # Celery task ID for async execution


class TaskStatusResponse(BaseModel):
    """Response with Celery task status."""

    task_id: str
    status: str
    result: Any = None
    error: str | None = None
    progress: float | None = None


class AgentResponse(BaseModel):
    """Response with agent information."""

    id: str
    type: str
    name: str
    state: str
    provider: str
    model: str
    metrics: dict[str, Any]


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    version: str
    agents_active: int
    providers_available: list[str]


# Health endpoint
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Check API health status."""
    providers = []
    if _provider_pool:
        health = await _provider_pool.health_check_all()
        providers = [k for k, v in health.items() if v]

    return HealthResponse(
        status="healthy",
        version="0.1.0",
        agents_active=len(_registry._agents) if _registry else 0,
        providers_available=providers,
    )


# Goals endpoints
@app.post("/goals", response_model=GoalResponse)
async def create_goal(goal_create: GoalCreate):
    """
    Create and execute a new goal.

    By default, goals are executed asynchronously via the task queue.
    Set async_execution=False to execute synchronously (blocking).
    """
    from src.persistence.database import get_async_session

    async with get_async_session() as session:
        repo = GoalRepository(session)

        goal = Goal(
            description=goal_create.description,
            context=goal_create.context,
            priority=Priority(goal_create.priority),
            success_criteria=goal_create.success_criteria,
        )

        # Persist goal
        await repo.create(goal)
        await emit_goal_created(goal.id, goal.description)

        # Async execution via Celery
        if goal_create.async_execution:
            try:
                from src.workers.tasks import execute_goal as execute_goal_task

                # Submit to task queue
                task = execute_goal_task.delay(goal.id, goal_create.context)

                logger.info(
                    "Goal submitted to task queue",
                    goal_id=goal.id,
                    task_id=task.id,
                )

                return GoalResponse(
                    id=goal.id,
                    description=goal.description,
                    status="pending",
                    priority=goal.priority.value,
                    created_at=goal.created_at.isoformat(),
                    task_id=task.id,
                )
            except Exception as e:
                logger.warning(
                    "Task queue unavailable, falling back to sync execution",
                    error=str(e),
                )
                # Fall through to sync execution

        # Synchronous execution (blocking)
        if not _governor:
            raise HTTPException(status_code=503, detail="Governor not initialized")

        from src.core.message import AgentMessage, MessageType

        message = AgentMessage(
            message_type=MessageType.GOAL_CREATED,
            sender="api",
            sender_type="api",
            recipient=_governor.id,
            recipient_type="governor",
            content={"description": goal.description, "context": goal.context},
        )

        try:
            await repo.update_status(goal.id, GoalStatus.IN_PROGRESS)
            await emit_goal_state_changed(goal.id, "pending", "in_progress")

            result = await _governor.execute(message)

            # Update with result
            if result.error:
                await repo.update_status(goal.id, GoalStatus.FAILED, error=result.error)
                await emit_goal_state_changed(goal.id, "in_progress", "failed", result.error)
            else:
                await repo.update_status(goal.id, GoalStatus.COMPLETED, result=result.result)
                await emit_goal_state_changed(goal.id, "in_progress", "completed")

            # Fetch updated goal
            updated = await repo.get(goal.id)

            return GoalResponse(
                id=goal.id,
                description=goal.description,
                status=updated.status if updated else goal.status.value,
                priority=goal.priority.value,
                created_at=goal.created_at.isoformat(),
                result=result.result,
                error=result.error,
            )
        except Exception as e:
            logger.error("Goal execution failed", error=str(e))
            await repo.update_status(goal.id, GoalStatus.FAILED, error=str(e))
            await emit_goal_state_changed(goal.id, "in_progress", "failed", str(e))
            raise HTTPException(status_code=500, detail=str(e))


@app.get("/goals/{goal_id}", response_model=GoalResponse)
async def get_goal(goal_id: str):
    """Get goal status by ID."""
    repo = GoalRepository()
    goal = await repo.get_with_tasks(goal_id)

    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")

    return GoalResponse(
        id=goal.id,
        description=goal.description,
        status=goal.status,
        priority=goal.priority,
        created_at=goal.created_at.isoformat() if goal.created_at else "",
        result=goal.result,
        error=goal.error,
    )


@app.get("/goals")
async def list_goals(
    status: str | None = None,
    limit: int = 20,
    offset: int = 0,
):
    """List goals with optional status filter."""
    repo = GoalRepository()

    status_filter = None
    if status:
        try:
            status_filter = GoalStatus(status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

    goals = await repo.list_by_status(status=status_filter, limit=limit, offset=offset)

    return {
        "goals": [g.to_dict() for g in goals],
        "total": len(goals),
        "limit": limit,
        "offset": offset,
    }


@app.delete("/goals/{goal_id}")
async def cancel_goal(goal_id: str):
    """Cancel a running goal."""
    repo = GoalRepository()
    goal = await repo.get(goal_id)

    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")

    if goal.status in (GoalStatus.COMPLETED.value, GoalStatus.FAILED.value):
        raise HTTPException(status_code=400, detail="Cannot cancel completed/failed goal")

    await repo.update_status(goal_id, GoalStatus.CANCELLED)
    await emit_goal_state_changed(goal_id, goal.status, "cancelled")

    return {"status": "cancelled", "goal_id": goal_id}


@app.post("/goals/{goal_id}/approve")
async def approve_goal(goal_id: str):
    """Approve a goal waiting for human approval."""
    repo = GoalRepository()
    goal = await repo.get(goal_id)

    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")

    if goal.status != GoalStatus.AWAITING_HUMAN.value:
        raise HTTPException(
            status_code=400,
            detail=f"Goal is not awaiting approval (status: {goal.status})"
        )

    await repo.update_status(goal_id, GoalStatus.IN_PROGRESS)
    await emit_goal_state_changed(goal_id, "awaiting_human", "in_progress", "Approved")

    return {"status": "approved", "goal_id": goal_id}


# Agents endpoints
@app.get("/agents", response_model=list[AgentResponse])
async def list_agents():
    """List all active agents."""
    if not _registry:
        return []

    agents = _registry.list_agents()
    return [
        AgentResponse(
            id=a["id"],
            type=a["type"],
            name=a["name"],
            state=a["state"],
            provider=a.get("provider", "unknown"),
            model=a.get("model", "unknown"),
            metrics=a.get("metrics", {}),
        )
        for a in agents
    ]


@app.get("/agents/{agent_id}", response_model=AgentResponse)
async def get_agent(agent_id: str):
    """Get agent details by ID."""
    if not _registry:
        raise HTTPException(status_code=503, detail="Registry not initialized")

    agent = _registry.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    data = agent.to_dict()
    return AgentResponse(
        id=data["id"],
        type=data["type"],
        name=data["name"],
        state=data["state"],
        provider=data.get("provider", "unknown"),
        model=data.get("model", "unknown"),
        metrics=data.get("metrics", {}),
    )


@app.post("/agents/{agent_id}/stop")
async def stop_agent(agent_id: str):
    """Stop an agent."""
    if not _registry:
        raise HTTPException(status_code=503, detail="Registry not initialized")

    await _registry.unregister(agent_id)
    return {"status": "stopped", "agent_id": agent_id}


# Memory endpoints
@app.get("/memory/search")
async def search_memory(
    query: str,
    memory_type: str | None = None,
    limit: int = 10,
):
    """Search across memory types."""
    # Memory search would query the memory subsystem
    return {"results": [], "message": "Memory search not fully implemented"}


# Task status endpoint
@app.get("/tasks/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    """Get the status of an async task."""
    try:
        from src.workers.celery_app import celery_app

        result = celery_app.AsyncResult(task_id)

        # Map Celery states to our status
        status_map = {
            "PENDING": "pending",
            "STARTED": "running",
            "SUCCESS": "completed",
            "FAILURE": "failed",
            "REVOKED": "cancelled",
            "RETRY": "retrying",
        }

        status = status_map.get(result.state, result.state.lower())

        response = TaskStatusResponse(
            task_id=task_id,
            status=status,
        )

        if result.ready():
            if result.successful():
                response.result = result.result
            else:
                response.error = str(result.result)

        return response

    except Exception as e:
        logger.error("Failed to get task status", task_id=task_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/tasks/{task_id}/cancel")
async def cancel_task(task_id: str):
    """Cancel a running task."""
    try:
        from src.workers.celery_app import celery_app

        celery_app.control.revoke(task_id, terminate=True)
        return {"status": "cancelled", "task_id": task_id}
    except Exception as e:
        logger.error("Failed to cancel task", task_id=task_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# Stats endpoint
@app.get("/stats")
async def get_stats():
    """Get system statistics."""
    ws_manager = get_connection_manager()
    stats = {
        "registry": _registry.get_stats() if _registry else {},
        "safety_limits": {
            "max_recursion_depth": get_safety_gate().limits.max_recursion_depth,
            "max_agent_spawns": get_safety_gate().limits.max_agent_spawns,
            "max_tokens_per_goal": get_safety_gate().limits.max_tokens_per_goal,
        },
        "websocket": ws_manager.get_stats(),
    }
    return stats


# WebSocket endpoints
@app.websocket("/ws")
async def ws_main(websocket: WebSocket):
    """Main WebSocket endpoint for all events."""
    await websocket_endpoint(websocket)


@app.websocket("/ws/goals/{goal_id}")
async def ws_goal(websocket: WebSocket, goal_id: str):
    """WebSocket endpoint for specific goal updates."""
    await goal_websocket_endpoint(websocket, goal_id)


@app.websocket("/ws/agents")
async def ws_agents(websocket: WebSocket):
    """WebSocket endpoint for agent activity."""
    manager = get_connection_manager()
    from src.api.websocket import WebSocketHandler

    handler = WebSocketHandler(manager)
    await manager.connect(websocket)

    try:
        while True:
            data = await websocket.receive_text()
            await handler.handle_message(websocket, data)
    except Exception:
        await manager.disconnect(websocket)


def create_app() -> FastAPI:
    """Create the FastAPI application."""
    return app


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "src.api.main:app",
        host=settings.api.host,
        port=settings.api.port,
        reload=settings.api.reload,
    )
