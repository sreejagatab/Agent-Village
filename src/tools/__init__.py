"""Tool system for Agent Village."""

from src.tools.registry import (
    Tool,
    ToolParameter,
    ToolPermission,
    ToolRegistry,
    ToolResult,
    create_default_registry,
    get_tool_registry,
)
from src.tools.sandbox import (
    CodeSandbox,
    SandboxConfig,
    create_sandbox_tools,
    get_sandbox,
)
from src.tools.web import (
    WebRequestConfig,
    WebRequestHandler,
    create_web_tools,
    get_web_handler,
)
from src.tools.file import (
    FileOperationsConfig,
    FileOperationsHandler,
    create_file_tools,
    get_file_handler,
)

__all__ = [
    # Registry
    "Tool",
    "ToolParameter",
    "ToolPermission",
    "ToolRegistry",
    "ToolResult",
    "create_default_registry",
    "get_tool_registry",
    # Sandbox
    "CodeSandbox",
    "SandboxConfig",
    "create_sandbox_tools",
    "get_sandbox",
    # Web
    "WebRequestConfig",
    "WebRequestHandler",
    "create_web_tools",
    "get_web_handler",
    # File
    "FileOperationsConfig",
    "FileOperationsHandler",
    "create_file_tools",
    "get_file_handler",
]


def register_all_tools(registry: ToolRegistry | None = None) -> ToolRegistry:
    """Register all built-in tools with the registry."""
    if registry is None:
        registry = get_tool_registry()

    # Register sandbox tools
    for tool in create_sandbox_tools():
        registry.register(tool)

    # Register web tools
    for tool in create_web_tools():
        registry.register(tool)

    # Register file tools
    for tool in create_file_tools():
        registry.register(tool)

    return registry
