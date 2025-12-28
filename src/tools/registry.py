"""
Tool Registry for Agent Village.

Manages available tools and their permissions.
"""

import asyncio
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Awaitable

import structlog

logger = structlog.get_logger()


class ToolPermission(str, Enum):
    """Permission levels for tools."""

    NONE = "none"
    READ_ONLY = "read_only"
    READ_WRITE = "read_write"
    EXECUTE = "execute"
    ADMIN = "admin"


@dataclass
class ToolParameter:
    """Definition of a tool parameter."""

    name: str
    type: str  # string, number, boolean, array, object
    description: str
    required: bool = True
    default: Any = None
    enum: list[str] | None = None

    def to_json_schema(self) -> dict[str, Any]:
        """Convert to JSON Schema format."""
        schema: dict[str, Any] = {
            "type": self.type,
            "description": self.description,
        }
        if self.enum:
            schema["enum"] = self.enum
        if self.default is not None:
            schema["default"] = self.default
        return schema


@dataclass
class ToolResult:
    """Result of a tool execution."""

    success: bool
    result: Any = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "result": self.result,
            "error": self.error,
            "metadata": self.metadata,
        }


@dataclass
class Tool:
    """Definition of a tool that agents can use."""

    name: str
    description: str
    parameters: list[ToolParameter]
    handler: Callable[..., Awaitable[ToolResult]]
    permission_required: ToolPermission = ToolPermission.READ_ONLY
    requires_approval: bool = False
    risk_level: str = "low"
    category: str = "general"

    def to_json_schema(self) -> dict[str, Any]:
        """Convert to JSON Schema for LLM function calling."""
        properties = {}
        required = []

        for param in self.parameters:
            properties[param.name] = param.to_json_schema()
            if param.required:
                required.append(param.name)

        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        }

    async def execute(self, **kwargs: Any) -> ToolResult:
        """Execute the tool with given arguments."""
        try:
            return await self.handler(**kwargs)
        except Exception as e:
            logger.error("Tool execution failed", tool=self.name, error=str(e))
            return ToolResult(success=False, error=str(e))


class ToolRegistry:
    """
    Central registry for all available tools.

    Manages tool discovery, permissions, and execution.
    """

    def __init__(self):
        self._tools: dict[str, Tool] = {}
        self._permissions: dict[str, dict[str, ToolPermission]] = {}
        self.logger = logger.bind(component="tool_registry")

    def register(self, tool: Tool) -> None:
        """Register a tool."""
        self._tools[tool.name] = tool
        self.logger.info(
            "Tool registered",
            name=tool.name,
            category=tool.category,
            permission=tool.permission_required.value,
        )

    def unregister(self, name: str) -> None:
        """Unregister a tool."""
        if name in self._tools:
            del self._tools[name]
            self.logger.info("Tool unregistered", name=name)

    def get(self, name: str) -> Tool | None:
        """Get a tool by name."""
        return self._tools.get(name)

    def list_tools(self, category: str | None = None) -> list[Tool]:
        """List all registered tools, optionally filtered by category."""
        tools = list(self._tools.values())
        if category:
            tools = [t for t in tools if t.category == category]
        return tools

    def get_tools_for_agent(
        self, agent_type: str, agent_id: str | None = None
    ) -> list[Tool]:
        """
        Get tools available to an agent based on permissions.

        Args:
            agent_type: Type of agent
            agent_id: Optional specific agent ID

        Returns:
            List of tools the agent can use
        """
        available = []

        # Get agent-level permissions
        agent_perms = self._permissions.get(agent_type, {})
        if agent_id:
            agent_perms = {**agent_perms, **self._permissions.get(agent_id, {})}

        for tool in self._tools.values():
            # Check if agent has required permission
            agent_perm = agent_perms.get(tool.name)

            if agent_perm is None:
                # Use default based on agent type
                if agent_type == "governor":
                    available.append(tool)
                elif agent_type == "tool" and tool.permission_required != ToolPermission.ADMIN:
                    available.append(tool)
                elif tool.permission_required in [ToolPermission.READ_ONLY, ToolPermission.NONE]:
                    available.append(tool)
            else:
                # Check if agent permission meets tool requirement
                if self._permission_meets_requirement(agent_perm, tool.permission_required):
                    available.append(tool)

        return available

    def set_permission(
        self,
        agent_key: str,  # agent_type or agent_id
        tool_name: str,
        permission: ToolPermission,
    ) -> None:
        """Set a specific permission for an agent on a tool."""
        if agent_key not in self._permissions:
            self._permissions[agent_key] = {}
        self._permissions[agent_key][tool_name] = permission

    def can_use(
        self, agent_type: str, tool_name: str, action: str = ""
    ) -> bool:
        """Check if an agent can use a tool."""
        tool = self._tools.get(tool_name)
        if tool is None:
            return False

        agent_perm = self._permissions.get(agent_type, {}).get(tool_name)

        if agent_perm is None:
            # Default permissions
            if agent_type == "governor":
                return True
            return tool.permission_required in [ToolPermission.READ_ONLY, ToolPermission.NONE]

        return self._permission_meets_requirement(agent_perm, tool.permission_required)

    def _permission_meets_requirement(
        self, agent_perm: ToolPermission, required: ToolPermission
    ) -> bool:
        """Check if agent permission meets tool requirement."""
        permission_order = [
            ToolPermission.NONE,
            ToolPermission.READ_ONLY,
            ToolPermission.READ_WRITE,
            ToolPermission.EXECUTE,
            ToolPermission.ADMIN,
        ]
        return permission_order.index(agent_perm) >= permission_order.index(required)

    async def execute_tool(
        self,
        tool_name: str,
        agent_type: str,
        **kwargs: Any,
    ) -> ToolResult:
        """
        Execute a tool with permission checking.

        Args:
            tool_name: Name of tool to execute
            agent_type: Type of agent executing
            **kwargs: Tool arguments

        Returns:
            ToolResult with execution outcome
        """
        tool = self._tools.get(tool_name)
        if tool is None:
            return ToolResult(success=False, error=f"Tool not found: {tool_name}")

        if not self.can_use(agent_type, tool_name):
            return ToolResult(
                success=False,
                error=f"Agent {agent_type} does not have permission to use {tool_name}",
            )

        return await tool.execute(**kwargs)

    def get_tool_schemas(self, tools: list[Tool] | None = None) -> list[dict[str, Any]]:
        """Get JSON schemas for tools (for LLM function calling)."""
        if tools is None:
            tools = list(self._tools.values())
        return [t.to_json_schema() for t in tools]


# Built-in tools

async def _echo_handler(message: str) -> ToolResult:
    """Simple echo tool for testing."""
    return ToolResult(success=True, result=message)


async def _calculate_handler(expression: str) -> ToolResult:
    """Safe calculator tool."""
    try:
        # Only allow safe operations
        allowed_chars = set("0123456789+-*/().% ")
        if not all(c in allowed_chars for c in expression):
            return ToolResult(success=False, error="Invalid characters in expression")

        result = eval(expression, {"__builtins__": {}}, {})
        return ToolResult(success=True, result=result)
    except Exception as e:
        return ToolResult(success=False, error=str(e))


def create_default_registry() -> ToolRegistry:
    """Create a registry with default tools."""
    registry = ToolRegistry()

    # Register built-in tools
    registry.register(
        Tool(
            name="echo",
            description="Echo back a message (for testing)",
            parameters=[
                ToolParameter(
                    name="message",
                    type="string",
                    description="Message to echo",
                )
            ],
            handler=_echo_handler,
            permission_required=ToolPermission.NONE,
            category="utility",
        )
    )

    registry.register(
        Tool(
            name="calculate",
            description="Evaluate a mathematical expression",
            parameters=[
                ToolParameter(
                    name="expression",
                    type="string",
                    description="Mathematical expression to evaluate",
                )
            ],
            handler=_calculate_handler,
            permission_required=ToolPermission.READ_ONLY,
            category="utility",
        )
    )

    return registry


# Global registry instance
_registry: ToolRegistry | None = None


def get_tool_registry() -> ToolRegistry:
    """Get the global tool registry."""
    global _registry
    if _registry is None:
        _registry = create_default_registry()
    return _registry
