"""
Code execution sandbox for safe code running.

Provides isolated environment for executing Python code
and shell commands with resource limits and security restrictions.
"""

import ast
import asyncio
import io
import os
import shlex
import subprocess
import sys
import traceback
from contextlib import redirect_stdout, redirect_stderr
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import structlog

from src.tools.registry import Tool, ToolParameter, ToolPermission, ToolResult

logger = structlog.get_logger()


@dataclass
class SandboxConfig:
    """Configuration for sandbox execution."""

    max_execution_time: float = 30.0  # seconds
    max_output_size: int = 10000  # characters
    max_memory_mb: int = 100  # MB (advisory, not enforced in pure Python)
    allowed_imports: set[str] = field(default_factory=lambda: {
        "math", "json", "datetime", "re", "collections",
        "itertools", "functools", "operator", "string",
        "random", "statistics", "decimal", "fractions",
    })
    blocked_builtins: set[str] = field(default_factory=lambda: {
        "exec", "eval", "compile", "open", "input",
        "__import__", "globals", "locals", "vars",
        "breakpoint", "exit", "quit",
    })


class RestrictedImporter:
    """Custom importer that only allows whitelisted modules."""

    def __init__(self, allowed_modules: set[str]):
        self.allowed_modules = allowed_modules

    def find_module(self, name: str, path: Any = None) -> Any:
        if name.split(".")[0] not in self.allowed_modules:
            raise ImportError(f"Import of '{name}' is not allowed in sandbox")
        return None  # Let the default importer handle it


class CodeSandbox:
    """
    Secure sandbox for executing Python code.

    Features:
    - Restricted imports (whitelist only)
    - Blocked dangerous builtins
    - Execution timeout
    - Output capture
    - AST validation
    """

    def __init__(self, config: SandboxConfig | None = None):
        self.config = config or SandboxConfig()
        self.logger = logger.bind(component="code_sandbox")

    def _create_safe_globals(self) -> dict[str, Any]:
        """Create a restricted globals dict for code execution."""
        # Start with safe subset of builtins
        safe_builtins = {}
        for name, value in __builtins__.items() if isinstance(__builtins__, dict) else vars(__builtins__).items():
            if name not in self.config.blocked_builtins:
                safe_builtins[name] = value

        # Add custom restricted __import__
        def restricted_import(name: str, *args: Any, **kwargs: Any) -> Any:
            if name.split(".")[0] not in self.config.allowed_imports:
                raise ImportError(f"Import of '{name}' is not allowed")
            return __builtins__["__import__"](name, *args, **kwargs) if isinstance(__builtins__, dict) else __import__(name, *args, **kwargs)

        safe_builtins["__import__"] = restricted_import

        return {
            "__builtins__": safe_builtins,
            "__name__": "__sandbox__",
            "__doc__": None,
        }

    def _validate_ast(self, code: str) -> tuple[bool, str | None]:
        """
        Validate code AST for potentially dangerous patterns.

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return False, f"Syntax error: {e}"

        for node in ast.walk(tree):
            # Check for dangerous attribute access
            if isinstance(node, ast.Attribute):
                if node.attr.startswith("_"):
                    return False, f"Access to private attributes ('{node.attr}') is not allowed"

            # Check for dangerous function calls
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if node.func.id in self.config.blocked_builtins:
                        return False, f"Call to '{node.func.id}' is not allowed"

            # Check for import statements
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                module_name = None
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        module_name = alias.name.split(".")[0]
                        if module_name not in self.config.allowed_imports:
                            return False, f"Import of '{alias.name}' is not allowed"
                elif isinstance(node, ast.ImportFrom) and node.module:
                    module_name = node.module.split(".")[0]
                    if module_name not in self.config.allowed_imports:
                        return False, f"Import from '{node.module}' is not allowed"

        return True, None

    async def execute(self, code: str) -> ToolResult:
        """
        Execute code in the sandbox.

        Args:
            code: Python code to execute

        Returns:
            ToolResult with execution output or error
        """
        self.logger.info("Executing code in sandbox", code_length=len(code))

        # Validate AST first
        is_valid, error = self._validate_ast(code)
        if not is_valid:
            return ToolResult(success=False, error=error)

        # Prepare execution environment
        safe_globals = self._create_safe_globals()
        safe_locals: dict[str, Any] = {}

        # Capture output
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()

        # Execute with timeout
        try:
            result = await asyncio.wait_for(
                self._execute_code(code, safe_globals, safe_locals, stdout_capture, stderr_capture),
                timeout=self.config.max_execution_time,
            )
            return result
        except asyncio.TimeoutError:
            return ToolResult(
                success=False,
                error=f"Execution timed out after {self.config.max_execution_time} seconds",
            )

    async def _execute_code(
        self,
        code: str,
        safe_globals: dict[str, Any],
        safe_locals: dict[str, Any],
        stdout: io.StringIO,
        stderr: io.StringIO,
    ) -> ToolResult:
        """Execute the code and capture results."""
        def run_code() -> tuple[Any, str, str]:
            with redirect_stdout(stdout), redirect_stderr(stderr):
                try:
                    # Try to execute as expression first (for return value)
                    try:
                        tree = ast.parse(code, mode='eval')
                        result = eval(compile(tree, '<sandbox>', 'eval'), safe_globals, safe_locals)
                        return result, stdout.getvalue(), stderr.getvalue()
                    except SyntaxError:
                        pass

                    # Execute as statements
                    exec(compile(code, '<sandbox>', 'exec'), safe_globals, safe_locals)

                    # Check for a 'result' variable
                    result = safe_locals.get('result', None)
                    return result, stdout.getvalue(), stderr.getvalue()

                except Exception as e:
                    tb = traceback.format_exc()
                    return None, stdout.getvalue(), tb

        # Run in thread pool to not block
        loop = asyncio.get_event_loop()
        result, out, err = await loop.run_in_executor(None, run_code)

        # Truncate output if needed
        if len(out) > self.config.max_output_size:
            out = out[:self.config.max_output_size] + "\n... (output truncated)"
        if len(err) > self.config.max_output_size:
            err = err[:self.config.max_output_size] + "\n... (output truncated)"

        # Determine success
        if err and not out and result is None:
            return ToolResult(
                success=False,
                error=err,
                metadata={"stdout": out},
            )

        return ToolResult(
            success=True,
            result=result,
            metadata={
                "stdout": out,
                "stderr": err,
                "variables": {k: repr(v)[:100] for k, v in safe_locals.items() if not k.startswith("_")},
            },
        )


# Singleton sandbox instance
_sandbox: CodeSandbox | None = None


def get_sandbox() -> CodeSandbox:
    """Get the global sandbox instance."""
    global _sandbox
    if _sandbox is None:
        _sandbox = CodeSandbox()
    return _sandbox


# Tool handlers

async def execute_python_handler(code: str, timeout: float = 30.0) -> ToolResult:
    """Handler for Python code execution."""
    sandbox = get_sandbox()
    # Override timeout if specified
    if timeout != 30.0:
        sandbox.config.max_execution_time = min(timeout, 60.0)  # Cap at 60s
    return await sandbox.execute(code)


async def execute_expression_handler(expression: str) -> ToolResult:
    """Handler for simple expression evaluation."""
    sandbox = get_sandbox()
    # Simple expressions get shorter timeout
    sandbox.config.max_execution_time = 5.0
    return await sandbox.execute(expression)


# Tool definitions

@dataclass
class ShellConfig:
    """Configuration for shell command execution."""

    max_execution_time: float = 60.0  # seconds
    max_output_size: int = 50000  # characters
    working_directory: Path = field(default_factory=lambda: Path.cwd() / "workspace")

    # Allowed commands (whitelist approach)
    allowed_commands: set[str] = field(default_factory=lambda: {
        # File operations
        "ls", "dir", "cat", "head", "tail", "wc", "find", "grep", "awk", "sed",
        "cp", "mv", "mkdir", "rmdir", "touch",
        # Development tools
        "git", "npm", "npx", "yarn", "pnpm", "pip", "python", "python3",
        "node", "deno", "bun", "cargo", "go", "rustc",
        # Build tools
        "make", "cmake", "gradle", "mvn",
        # Utilities
        "echo", "printf", "date", "whoami", "pwd", "env", "which", "whereis",
        "curl", "wget", "tar", "unzip", "zip", "gzip", "gunzip",
        "jq", "yq", "diff", "sort", "uniq", "cut", "tr",
    })

    # Dangerous patterns to block
    blocked_patterns: list[str] = field(default_factory=lambda: [
        "rm -rf /",
        "rm -rf ~",
        "rm -rf *",
        "rm -rf .",
        ":(){:|:&};:",  # Fork bomb
        "mkfs",
        "dd if=",
        "chmod -R 777 /",
        "> /dev/sda",
        "| sh",
        "| bash",
        "`",  # Command substitution
        "$(", # Command substitution
        "sudo",
        "su ",
        "passwd",
        "chown",
        "chmod 777",
        "/etc/passwd",
        "/etc/shadow",
        "~/.ssh",
        ".env",
        "id_rsa",
        "kill -9",
        "pkill",
        "killall",
        "shutdown",
        "reboot",
        "init ",
        "systemctl",
        "service ",
    ])

    # Environment variables to expose (whitelist)
    allowed_env_vars: set[str] = field(default_factory=lambda: {
        "PATH", "HOME", "USER", "LANG", "LC_ALL", "TERM",
        "NODE_ENV", "PYTHON_PATH", "GOPATH", "CARGO_HOME",
    })


class ShellCommandHandler:
    """
    Handler for executing shell commands with security restrictions.

    Features:
    - Command whitelist
    - Dangerous pattern blocking
    - Timeout enforcement
    - Output capture and truncation
    - Working directory isolation
    """

    def __init__(self, config: ShellConfig | None = None):
        self.config = config or ShellConfig()
        self.logger = logger.bind(component="shell_sandbox")

        # Ensure workspace exists
        self.config.working_directory.mkdir(parents=True, exist_ok=True)

    def _validate_command(self, command: str) -> tuple[bool, str | None]:
        """
        Validate command for security.

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check for blocked patterns
        command_lower = command.lower()
        for pattern in self.config.blocked_patterns:
            if pattern.lower() in command_lower:
                return False, f"Command contains blocked pattern: '{pattern}'"

        # Parse command to get the base command
        try:
            # Handle Windows vs Unix
            if sys.platform == "win32":
                parts = command.split()
            else:
                parts = shlex.split(command)

            if not parts:
                return False, "Empty command"

            base_command = parts[0]

            # Strip path from command
            base_command = os.path.basename(base_command)

            # Remove extension on Windows
            if sys.platform == "win32":
                base_command = os.path.splitext(base_command)[0]

            # Check against whitelist
            if base_command.lower() not in {c.lower() for c in self.config.allowed_commands}:
                return False, f"Command '{base_command}' is not in the allowed list"

        except ValueError as e:
            return False, f"Invalid command syntax: {e}"

        return True, None

    def _get_safe_env(self) -> dict[str, str]:
        """Get a safe subset of environment variables."""
        return {
            k: v for k, v in os.environ.items()
            if k in self.config.allowed_env_vars
        }

    async def execute(
        self,
        command: str,
        timeout: float | None = None,
        cwd: str | None = None,
    ) -> ToolResult:
        """
        Execute a shell command safely.

        Args:
            command: Shell command to execute
            timeout: Optional timeout override
            cwd: Optional working directory (relative to workspace)

        Returns:
            ToolResult with command output
        """
        self.logger.info("Executing shell command", command=command[:100])

        # Validate command
        is_valid, error = self._validate_command(command)
        if not is_valid:
            return ToolResult(success=False, error=error)

        # Determine working directory
        if cwd:
            work_dir = self.config.working_directory / cwd
            # Ensure it doesn't escape workspace
            try:
                work_dir.resolve().relative_to(self.config.working_directory.resolve())
            except ValueError:
                return ToolResult(
                    success=False,
                    error="Working directory must be within workspace"
                )
        else:
            work_dir = self.config.working_directory

        if not work_dir.exists():
            work_dir.mkdir(parents=True, exist_ok=True)

        # Set timeout
        exec_timeout = min(
            timeout or self.config.max_execution_time,
            self.config.max_execution_time
        )

        try:
            # Execute command
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(work_dir),
                env=self._get_safe_env(),
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=exec_timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                return ToolResult(
                    success=False,
                    error=f"Command timed out after {exec_timeout} seconds"
                )

            # Decode and truncate output
            stdout_str = stdout.decode("utf-8", errors="replace")
            stderr_str = stderr.decode("utf-8", errors="replace")

            if len(stdout_str) > self.config.max_output_size:
                stdout_str = stdout_str[:self.config.max_output_size] + "\n... (output truncated)"
            if len(stderr_str) > self.config.max_output_size:
                stderr_str = stderr_str[:self.config.max_output_size] + "\n... (output truncated)"

            return ToolResult(
                success=process.returncode == 0,
                result=stdout_str if stdout_str else None,
                error=stderr_str if process.returncode != 0 and stderr_str else None,
                metadata={
                    "return_code": process.returncode,
                    "stdout": stdout_str,
                    "stderr": stderr_str,
                    "cwd": str(work_dir),
                }
            )

        except Exception as e:
            self.logger.error("Shell command failed", error=str(e))
            return ToolResult(success=False, error=str(e))


# Singleton shell handler instance
_shell_handler: ShellCommandHandler | None = None


def get_shell_handler() -> ShellCommandHandler:
    """Get the global shell command handler."""
    global _shell_handler
    if _shell_handler is None:
        _shell_handler = ShellCommandHandler()
    return _shell_handler


# Shell tool handlers

async def shell_command_handler(
    command: str,
    timeout: float = 60.0,
    cwd: str | None = None,
) -> ToolResult:
    """Handler for shell command execution."""
    handler = get_shell_handler()
    return await handler.execute(command, timeout=timeout, cwd=cwd)


async def git_command_handler(
    args: str,
    cwd: str | None = None,
) -> ToolResult:
    """Handler for git commands."""
    handler = get_shell_handler()
    command = f"git {args}"
    return await handler.execute(command, cwd=cwd)


async def npm_command_handler(
    args: str,
    cwd: str | None = None,
) -> ToolResult:
    """Handler for npm commands."""
    handler = get_shell_handler()
    command = f"npm {args}"
    return await handler.execute(command, cwd=cwd)


async def pip_command_handler(
    args: str,
    cwd: str | None = None,
) -> ToolResult:
    """Handler for pip commands."""
    handler = get_shell_handler()
    command = f"pip {args}"
    return await handler.execute(command, cwd=cwd)


def create_sandbox_tools() -> list[Tool]:
    """Create sandbox-related tools."""
    return [
        Tool(
            name="execute_python",
            description=(
                "Execute Python code in a secure sandbox. "
                "Limited imports available: math, json, datetime, re, collections, "
                "itertools, functools, random, statistics. "
                "No file I/O, network, or system access. "
                "Print statements will be captured. "
                "Assign results to 'result' variable to return them."
            ),
            parameters=[
                ToolParameter(
                    name="code",
                    type="string",
                    description="Python code to execute",
                ),
                ToolParameter(
                    name="timeout",
                    type="number",
                    description="Execution timeout in seconds (max 60)",
                    required=False,
                    default=30.0,
                ),
            ],
            handler=execute_python_handler,
            permission_required=ToolPermission.EXECUTE,
            requires_approval=False,
            risk_level="medium",
            category="code",
        ),
        Tool(
            name="evaluate_expression",
            description=(
                "Evaluate a simple Python expression and return the result. "
                "For simple calculations and data transformations."
            ),
            parameters=[
                ToolParameter(
                    name="expression",
                    type="string",
                    description="Python expression to evaluate",
                ),
            ],
            handler=execute_expression_handler,
            permission_required=ToolPermission.READ_ONLY,
            requires_approval=False,
            risk_level="low",
            category="code",
        ),
        Tool(
            name="shell_command",
            description=(
                "Execute a shell command in the workspace. "
                "Allowed commands include: ls, cat, grep, find, git, npm, pip, python, "
                "curl, wget, tar, zip, and common development tools. "
                "Dangerous commands like rm -rf, sudo, etc. are blocked."
            ),
            parameters=[
                ToolParameter(
                    name="command",
                    type="string",
                    description="Shell command to execute",
                ),
                ToolParameter(
                    name="timeout",
                    type="number",
                    description="Execution timeout in seconds (max 60)",
                    required=False,
                    default=60.0,
                ),
                ToolParameter(
                    name="cwd",
                    type="string",
                    description="Working directory relative to workspace",
                    required=False,
                ),
            ],
            handler=shell_command_handler,
            permission_required=ToolPermission.EXECUTE,
            requires_approval=False,
            risk_level="medium",
            category="shell",
        ),
        Tool(
            name="git",
            description="Execute git commands in the workspace.",
            parameters=[
                ToolParameter(
                    name="args",
                    type="string",
                    description="Git command arguments (e.g., 'status', 'log --oneline -5')",
                ),
                ToolParameter(
                    name="cwd",
                    type="string",
                    description="Repository directory relative to workspace",
                    required=False,
                ),
            ],
            handler=git_command_handler,
            permission_required=ToolPermission.READ_WRITE,
            requires_approval=False,
            risk_level="low",
            category="shell",
        ),
        Tool(
            name="npm",
            description="Execute npm commands in the workspace.",
            parameters=[
                ToolParameter(
                    name="args",
                    type="string",
                    description="npm command arguments (e.g., 'install', 'run build')",
                ),
                ToolParameter(
                    name="cwd",
                    type="string",
                    description="Project directory relative to workspace",
                    required=False,
                ),
            ],
            handler=npm_command_handler,
            permission_required=ToolPermission.EXECUTE,
            requires_approval=False,
            risk_level="medium",
            category="shell",
        ),
        Tool(
            name="pip",
            description="Execute pip commands in the workspace.",
            parameters=[
                ToolParameter(
                    name="args",
                    type="string",
                    description="pip command arguments (e.g., 'install requests', 'list')",
                ),
                ToolParameter(
                    name="cwd",
                    type="string",
                    description="Project directory relative to workspace",
                    required=False,
                ),
            ],
            handler=pip_command_handler,
            permission_required=ToolPermission.EXECUTE,
            requires_approval=False,
            risk_level="medium",
            category="shell",
        ),
    ]
