"""Tests for tool implementations."""

import pytest
import pytest_asyncio
from pathlib import Path
import tempfile

from src.tools.registry import (
    Tool,
    ToolParameter,
    ToolPermission,
    ToolRegistry,
    ToolResult,
    create_default_registry,
)
from src.tools.sandbox import (
    CodeSandbox,
    SandboxConfig,
    create_sandbox_tools,
)
from src.tools.web import (
    WebRequestHandler,
    WebRequestConfig,
    create_web_tools,
)
from src.tools.file import (
    FileOperationsHandler,
    FileOperationsConfig,
    create_file_tools,
)


class TestToolRegistry:
    """Tests for ToolRegistry."""

    def test_create_default_registry(self):
        """Test creating default registry with built-in tools."""
        registry = create_default_registry()

        assert registry is not None
        assert registry.get("echo") is not None
        assert registry.get("calculate") is not None

    def test_register_tool(self):
        """Test registering a tool."""
        registry = ToolRegistry()

        async def handler(x: str) -> ToolResult:
            return ToolResult(success=True, result=x)

        tool = Tool(
            name="test_tool",
            description="Test tool",
            parameters=[
                ToolParameter(name="x", type="string", description="Input")
            ],
            handler=handler,
        )

        registry.register(tool)

        assert registry.get("test_tool") is not None

    def test_unregister_tool(self):
        """Test unregistering a tool."""
        registry = create_default_registry()
        registry.unregister("echo")

        assert registry.get("echo") is None

    def test_list_tools(self):
        """Test listing tools."""
        registry = create_default_registry()
        tools = registry.list_tools()

        assert len(tools) >= 2  # At least echo and calculate

    def test_list_tools_by_category(self):
        """Test listing tools filtered by category."""
        registry = create_default_registry()
        utility_tools = registry.list_tools(category="utility")

        assert all(t.category == "utility" for t in utility_tools)

    def test_permission_checking(self):
        """Test permission checking."""
        registry = create_default_registry()

        # Governor can use all tools
        assert registry.can_use("governor", "echo")
        assert registry.can_use("governor", "calculate")

    def test_get_tool_schemas(self):
        """Test getting JSON schemas for tools."""
        registry = create_default_registry()
        schemas = registry.get_tool_schemas()

        assert len(schemas) >= 2
        assert all("name" in s for s in schemas)
        assert all("parameters" in s for s in schemas)

    @pytest.mark.asyncio
    async def test_execute_tool(self):
        """Test executing a tool."""
        registry = create_default_registry()
        result = await registry.execute_tool("echo", "governor", message="hello")

        assert result.success
        assert result.result == "hello"

    @pytest.mark.asyncio
    async def test_execute_calculator(self):
        """Test calculator tool."""
        registry = create_default_registry()
        result = await registry.execute_tool(
            "calculate", "governor", expression="2 + 2 * 3"
        )

        assert result.success
        assert result.result == 8


class TestCodeSandbox:
    """Tests for code sandbox."""

    @pytest.fixture
    def sandbox(self):
        return CodeSandbox()

    @pytest.mark.asyncio
    async def test_simple_expression(self, sandbox):
        """Test evaluating a simple expression."""
        result = await sandbox.execute("2 + 2")

        assert result.success
        assert result.result == 4

    @pytest.mark.asyncio
    async def test_print_statement(self, sandbox):
        """Test capturing print output."""
        result = await sandbox.execute('print("hello world")')

        assert result.success
        assert "hello world" in result.metadata.get("stdout", "")

    @pytest.mark.asyncio
    async def test_variable_assignment(self, sandbox):
        """Test variable assignment and result."""
        result = await sandbox.execute("result = 42")

        assert result.success
        assert result.result == 42

    @pytest.mark.asyncio
    async def test_allowed_import(self, sandbox):
        """Test importing allowed modules."""
        result = await sandbox.execute("import math; result = math.sqrt(16)")

        assert result.success
        assert result.result == 4.0

    @pytest.mark.asyncio
    async def test_blocked_import(self, sandbox):
        """Test blocking disallowed imports."""
        result = await sandbox.execute("import os")

        assert not result.success
        assert "not allowed" in result.error.lower()

    @pytest.mark.asyncio
    async def test_blocked_builtin(self, sandbox):
        """Test blocking dangerous builtins."""
        result = await sandbox.execute('open("test.txt")')

        assert not result.success

    @pytest.mark.asyncio
    async def test_private_attribute_access(self, sandbox):
        """Test blocking private attribute access."""
        result = await sandbox.execute('x = [].__class__.__bases__')

        assert not result.success
        assert "private" in result.error.lower()

    @pytest.mark.asyncio
    async def test_syntax_error(self, sandbox):
        """Test handling syntax errors."""
        result = await sandbox.execute("def foo(")

        assert not result.success
        assert "syntax" in result.error.lower()

    @pytest.mark.asyncio
    async def test_runtime_error(self, sandbox):
        """Test handling runtime errors."""
        result = await sandbox.execute("1/0")

        assert not result.success
        assert "ZeroDivision" in result.metadata.get("stderr", "") or "ZeroDivision" in str(result.error)

    def test_create_sandbox_tools(self):
        """Test creating sandbox tools."""
        tools = create_sandbox_tools()

        assert len(tools) == 6  # execute_python, evaluate_expression, shell_command, git, npm, pip
        assert any(t.name == "execute_python" for t in tools)
        assert any(t.name == "evaluate_expression" for t in tools)
        assert any(t.name == "shell_command" for t in tools)
        assert any(t.name == "git" for t in tools)


class TestWebRequestHandler:
    """Tests for web request handler."""

    @pytest.fixture
    def handler(self):
        return WebRequestHandler()

    def test_url_validation_valid(self, handler):
        """Test valid URL validation."""
        valid, error = handler._validate_url("https://example.com/api")
        assert valid
        assert error is None

    def test_url_validation_blocked_host(self, handler):
        """Test blocking internal hosts."""
        valid, error = handler._validate_url("http://localhost:8080")
        assert not valid
        assert "localhost" in error

    def test_url_validation_blocked_ip(self, handler):
        """Test blocking private IPs."""
        valid, error = handler._validate_url("http://192.168.1.1")
        assert not valid
        assert "private" in error.lower()

    def test_url_validation_bad_scheme(self, handler):
        """Test blocking invalid schemes."""
        valid, error = handler._validate_url("ftp://example.com")
        assert not valid
        assert "scheme" in error.lower()

    def test_create_web_tools(self):
        """Test creating web tools."""
        tools = create_web_tools()

        assert len(tools) == 4
        assert any(t.name == "http_get" for t in tools)
        assert any(t.name == "http_post" for t in tools)
        assert any(t.name == "http_request" for t in tools)
        assert any(t.name == "fetch_webpage" for t in tools)


class TestFileOperationsHandler:
    """Tests for file operations handler."""

    @pytest.fixture
    def temp_workspace(self):
        """Create a temporary workspace."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def handler(self, temp_workspace):
        config = FileOperationsConfig(workspace_root=temp_workspace)
        return FileOperationsHandler(config)

    def test_resolve_path_valid(self, handler):
        """Test resolving valid paths."""
        resolved, error = handler._resolve_path("test/file.txt")
        assert error is None
        assert resolved is not None

    def test_resolve_path_escape(self, handler):
        """Test blocking path traversal."""
        resolved, error = handler._resolve_path("../../../etc/passwd")
        assert resolved is None
        assert "escape" in error.lower()

    def test_resolve_path_blocked_pattern(self, handler):
        """Test blocking sensitive paths."""
        resolved, error = handler._resolve_path(".git/config")
        assert resolved is None
        assert ".git" in error

    @pytest.mark.asyncio
    async def test_write_and_read_file(self, handler, temp_workspace):
        """Test writing and reading a file."""
        # Write
        write_result = await handler.write_file("test.txt", "Hello, World!")
        assert write_result.success

        # Read
        read_result = await handler.read_file("test.txt")
        assert read_result.success
        assert read_result.result == "Hello, World!"

    @pytest.mark.asyncio
    async def test_list_directory(self, handler, temp_workspace):
        """Test listing directory contents."""
        # Create some files
        (temp_workspace / "file1.txt").write_text("content1")
        (temp_workspace / "file2.txt").write_text("content2")

        result = await handler.list_directory()
        assert result.success
        assert len(result.result) >= 2

    @pytest.mark.asyncio
    async def test_create_directory(self, handler):
        """Test creating a directory."""
        result = await handler.create_directory("new_dir")
        assert result.success

    @pytest.mark.asyncio
    async def test_file_info(self, handler, temp_workspace):
        """Test getting file info."""
        # Create a file
        (temp_workspace / "info_test.txt").write_text("test content")

        result = await handler.file_info("info_test.txt")
        assert result.success
        assert result.result["type"] == "file"
        assert result.result["size"] > 0

    @pytest.mark.asyncio
    async def test_delete_file(self, handler, temp_workspace):
        """Test deleting a file."""
        # Create a file
        (temp_workspace / "to_delete.txt").write_text("delete me")

        result = await handler.delete_file("to_delete.txt")
        assert result.success
        assert not (temp_workspace / "to_delete.txt").exists()

    @pytest.mark.asyncio
    async def test_read_nonexistent_file(self, handler):
        """Test reading a file that doesn't exist."""
        result = await handler.read_file("nonexistent.txt")
        assert not result.success
        assert "not found" in result.error.lower()

    @pytest.mark.asyncio
    async def test_write_blocked_extension(self, handler):
        """Test writing to a blocked extension."""
        result = await handler.write_file("script.exe", "content")
        assert not result.success
        assert "extension" in result.error.lower()

    def test_create_file_tools(self):
        """Test creating file tools."""
        tools = create_file_tools()

        assert len(tools) == 9  # read, write, list, delete, create_dir, file_info, search, copy, move
        assert any(t.name == "read_file" for t in tools)
        assert any(t.name == "write_file" for t in tools)
        assert any(t.name == "list_directory" for t in tools)
        assert any(t.name == "delete_file" for t in tools)
        assert any(t.name == "search_files" for t in tools)
        assert any(t.name == "copy_file" for t in tools)
        assert any(t.name == "move_file" for t in tools)


class TestToolParameter:
    """Tests for ToolParameter."""

    def test_to_json_schema_basic(self):
        """Test basic JSON schema conversion."""
        param = ToolParameter(
            name="test",
            type="string",
            description="A test parameter",
        )

        schema = param.to_json_schema()

        assert schema["type"] == "string"
        assert schema["description"] == "A test parameter"

    def test_to_json_schema_with_enum(self):
        """Test JSON schema with enum values."""
        param = ToolParameter(
            name="method",
            type="string",
            description="HTTP method",
            enum=["GET", "POST", "PUT"],
        )

        schema = param.to_json_schema()

        assert "enum" in schema
        assert schema["enum"] == ["GET", "POST", "PUT"]

    def test_to_json_schema_with_default(self):
        """Test JSON schema with default value."""
        param = ToolParameter(
            name="timeout",
            type="number",
            description="Timeout in seconds",
            default=30.0,
            required=False,
        )

        schema = param.to_json_schema()

        assert schema["default"] == 30.0


class TestToolResult:
    """Tests for ToolResult."""

    def test_success_result(self):
        """Test successful result."""
        result = ToolResult(success=True, result={"key": "value"})

        assert result.success
        assert result.result == {"key": "value"}
        assert result.error is None

    def test_error_result(self):
        """Test error result."""
        result = ToolResult(success=False, error="Something went wrong")

        assert not result.success
        assert result.error == "Something went wrong"

    def test_to_dict(self):
        """Test converting to dictionary."""
        result = ToolResult(
            success=True,
            result="output",
            metadata={"time_ms": 100},
        )

        data = result.to_dict()

        assert data["success"]
        assert data["result"] == "output"
        assert data["metadata"]["time_ms"] == 100
