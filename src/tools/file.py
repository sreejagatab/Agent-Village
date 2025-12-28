"""
File operations tools for Agent Village.

Provides safe file system access with sandboxing.
"""

import asyncio
import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import structlog

from src.tools.registry import Tool, ToolParameter, ToolPermission, ToolResult

logger = structlog.get_logger()


@dataclass
class FileOperationsConfig:
    """Configuration for file operations."""

    workspace_root: Path = field(default_factory=lambda: Path.cwd() / "workspace")
    max_file_size: int = 10_000_000  # 10MB
    max_read_size: int = 1_000_000  # 1MB for reading
    allowed_extensions: set[str] = field(default_factory=lambda: {
        ".txt", ".md", ".json", ".yaml", ".yml", ".xml",
        ".py", ".js", ".ts", ".html", ".css", ".sql",
        ".csv", ".log", ".sh", ".bash", ".env.example",
        ".toml", ".ini", ".cfg", ".conf",
    })
    blocked_patterns: set[str] = field(default_factory=lambda: {
        ".env", ".git", "__pycache__", "node_modules",
        ".ssh", ".aws", ".credentials", "secrets",
    })
    create_workspace: bool = True


class FileOperationsHandler:
    """Handler for safe file operations within a workspace."""

    def __init__(self, config: FileOperationsConfig | None = None):
        self.config = config or FileOperationsConfig()
        self.logger = logger.bind(component="file_operations")

        # Ensure workspace exists
        if self.config.create_workspace:
            self.config.workspace_root.mkdir(parents=True, exist_ok=True)

        # Resolve workspace root to canonical path (handles Windows short paths)
        import os
        self.config.workspace_root = Path(os.path.realpath(str(self.config.workspace_root)))

    def _resolve_path(self, path: str) -> tuple[Path | None, str | None]:
        """
        Resolve a path relative to workspace root.

        Returns:
            Tuple of (resolved_path, error_message)
        """
        try:
            # Resolve the path - use os.path.realpath for consistent path resolution on Windows
            import os
            workspace_real = Path(os.path.realpath(str(self.config.workspace_root)))
            target = Path(os.path.realpath(str(self.config.workspace_root / path)))

            # Check it's within workspace
            try:
                target.relative_to(workspace_real)
            except ValueError:
                return None, "Path escapes workspace directory"

            # Check for blocked patterns
            path_str = str(target)
            for pattern in self.config.blocked_patterns:
                if pattern in path_str:
                    return None, f"Access to '{pattern}' paths is not allowed"

            return target, None
        except Exception as e:
            return None, f"Invalid path: {e}"

    def _check_extension(self, path: Path, for_write: bool = False) -> tuple[bool, str | None]:
        """Check if file extension is allowed."""
        ext = path.suffix.lower()
        if ext and ext not in self.config.allowed_extensions:
            return False, f"File extension '{ext}' is not allowed"
        return True, None

    async def read_file(self, path: str, encoding: str = "utf-8") -> ToolResult:
        """Read a file from the workspace."""
        resolved, error = self._resolve_path(path)
        if error:
            return ToolResult(success=False, error=error)

        if not resolved.exists():
            return ToolResult(success=False, error=f"File not found: {path}")

        if not resolved.is_file():
            return ToolResult(success=False, error=f"Not a file: {path}")

        # Check size
        file_size = resolved.stat().st_size
        if file_size > self.config.max_read_size:
            return ToolResult(
                success=False,
                error=f"File too large ({file_size} bytes, max: {self.config.max_read_size})",
            )

        try:
            content = await asyncio.to_thread(resolved.read_text, encoding=encoding)
            return ToolResult(
                success=True,
                result=content,
                metadata={
                    "path": str(resolved.relative_to(self.config.workspace_root)),
                    "size": file_size,
                    "encoding": encoding,
                },
            )
        except UnicodeDecodeError:
            return ToolResult(success=False, error=f"Cannot decode file with {encoding} encoding")
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    async def write_file(
        self,
        path: str,
        content: str,
        encoding: str = "utf-8",
        overwrite: bool = False,
    ) -> ToolResult:
        """Write content to a file in the workspace."""
        resolved, error = self._resolve_path(path)
        if error:
            return ToolResult(success=False, error=error)

        # Check extension
        valid, error = self._check_extension(resolved, for_write=True)
        if not valid:
            return ToolResult(success=False, error=error)

        # Check if exists and overwrite setting
        if resolved.exists() and not overwrite:
            return ToolResult(
                success=False,
                error=f"File already exists: {path}. Set overwrite=True to replace.",
            )

        # Check content size
        if len(content.encode(encoding)) > self.config.max_file_size:
            return ToolResult(
                success=False,
                error=f"Content too large (max: {self.config.max_file_size} bytes)",
            )

        try:
            # Ensure parent directory exists
            resolved.parent.mkdir(parents=True, exist_ok=True)

            await asyncio.to_thread(resolved.write_text, content, encoding=encoding)

            self.logger.info("File written", path=str(resolved))
            return ToolResult(
                success=True,
                result=f"File written: {path}",
                metadata={
                    "path": str(resolved.relative_to(self.config.workspace_root)),
                    "size": len(content.encode(encoding)),
                },
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    async def list_directory(
        self,
        path: str = ".",
        pattern: str = "*",
        recursive: bool = False,
    ) -> ToolResult:
        """List files in a directory."""
        resolved, error = self._resolve_path(path)
        if error:
            return ToolResult(success=False, error=error)

        if not resolved.exists():
            return ToolResult(success=False, error=f"Directory not found: {path}")

        if not resolved.is_dir():
            return ToolResult(success=False, error=f"Not a directory: {path}")

        try:
            if recursive:
                files = list(resolved.rglob(pattern))
            else:
                files = list(resolved.glob(pattern))

            # Filter out blocked patterns
            result_files = []
            for f in files:
                path_str = str(f)
                if any(p in path_str for p in self.config.blocked_patterns):
                    continue
                rel_path = f.relative_to(self.config.workspace_root)
                result_files.append({
                    "path": str(rel_path),
                    "type": "file" if f.is_file() else "directory",
                    "size": f.stat().st_size if f.is_file() else None,
                })

            return ToolResult(
                success=True,
                result=result_files,
                metadata={"count": len(result_files)},
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    async def delete_file(self, path: str) -> ToolResult:
        """Delete a file from the workspace."""
        resolved, error = self._resolve_path(path)
        if error:
            return ToolResult(success=False, error=error)

        if not resolved.exists():
            return ToolResult(success=False, error=f"File not found: {path}")

        if not resolved.is_file():
            return ToolResult(success=False, error=f"Not a file: {path}")

        try:
            await asyncio.to_thread(resolved.unlink)
            self.logger.info("File deleted", path=str(resolved))
            return ToolResult(success=True, result=f"File deleted: {path}")
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    async def create_directory(self, path: str) -> ToolResult:
        """Create a directory in the workspace."""
        resolved, error = self._resolve_path(path)
        if error:
            return ToolResult(success=False, error=error)

        if resolved.exists():
            if resolved.is_dir():
                return ToolResult(success=True, result=f"Directory already exists: {path}")
            return ToolResult(success=False, error=f"Path exists but is not a directory: {path}")

        try:
            await asyncio.to_thread(resolved.mkdir, parents=True)
            self.logger.info("Directory created", path=str(resolved))
            return ToolResult(success=True, result=f"Directory created: {path}")
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    async def file_info(self, path: str) -> ToolResult:
        """Get information about a file or directory."""
        resolved, error = self._resolve_path(path)
        if error:
            return ToolResult(success=False, error=error)

        if not resolved.exists():
            return ToolResult(success=False, error=f"Path not found: {path}")

        try:
            stat = resolved.stat()
            return ToolResult(
                success=True,
                result={
                    "path": str(resolved.relative_to(self.config.workspace_root)),
                    "type": "file" if resolved.is_file() else "directory",
                    "size": stat.st_size,
                    "created": stat.st_ctime,
                    "modified": stat.st_mtime,
                    "extension": resolved.suffix if resolved.is_file() else None,
                },
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    async def search_files(
        self,
        pattern: str,
        path: str = ".",
        file_pattern: str = "*",
        max_results: int = 50,
        case_sensitive: bool = False,
    ) -> ToolResult:
        """Search for text pattern within files."""
        import re

        resolved, error = self._resolve_path(path)
        if error:
            return ToolResult(success=False, error=error)

        if not resolved.exists():
            return ToolResult(success=False, error=f"Directory not found: {path}")

        if not resolved.is_dir():
            return ToolResult(success=False, error=f"Not a directory: {path}")

        try:
            # Compile pattern
            flags = 0 if case_sensitive else re.IGNORECASE
            try:
                regex = re.compile(pattern, flags)
            except re.error as e:
                return ToolResult(success=False, error=f"Invalid regex pattern: {e}")

            results = []
            files_searched = 0

            for file_path in resolved.rglob(file_pattern):
                if not file_path.is_file():
                    continue

                # Skip blocked patterns
                path_str = str(file_path)
                if any(p in path_str for p in self.config.blocked_patterns):
                    continue

                # Skip large files
                if file_path.stat().st_size > self.config.max_read_size:
                    continue

                # Check extension
                valid, _ = self._check_extension(file_path)
                if not valid:
                    continue

                files_searched += 1

                try:
                    content = await asyncio.to_thread(file_path.read_text, encoding="utf-8")
                    lines = content.splitlines()

                    for line_num, line in enumerate(lines, 1):
                        if regex.search(line):
                            results.append({
                                "file": str(file_path.relative_to(self.config.workspace_root)),
                                "line": line_num,
                                "content": line.strip()[:200],  # Truncate long lines
                            })

                            if len(results) >= max_results:
                                break

                except (UnicodeDecodeError, PermissionError):
                    continue

                if len(results) >= max_results:
                    break

            return ToolResult(
                success=True,
                result=results,
                metadata={
                    "files_searched": files_searched,
                    "matches_found": len(results),
                    "truncated": len(results) >= max_results,
                },
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    async def copy_file(self, source: str, destination: str) -> ToolResult:
        """Copy a file within the workspace."""
        src_resolved, error = self._resolve_path(source)
        if error:
            return ToolResult(success=False, error=f"Source: {error}")

        dst_resolved, error = self._resolve_path(destination)
        if error:
            return ToolResult(success=False, error=f"Destination: {error}")

        if not src_resolved.exists():
            return ToolResult(success=False, error=f"Source not found: {source}")

        if not src_resolved.is_file():
            return ToolResult(success=False, error=f"Source is not a file: {source}")

        try:
            # Ensure parent directory exists
            dst_resolved.parent.mkdir(parents=True, exist_ok=True)

            await asyncio.to_thread(shutil.copy2, src_resolved, dst_resolved)

            self.logger.info("File copied", source=str(src_resolved), destination=str(dst_resolved))
            return ToolResult(
                success=True,
                result=f"Copied {source} to {destination}",
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    async def move_file(self, source: str, destination: str) -> ToolResult:
        """Move a file within the workspace."""
        src_resolved, error = self._resolve_path(source)
        if error:
            return ToolResult(success=False, error=f"Source: {error}")

        dst_resolved, error = self._resolve_path(destination)
        if error:
            return ToolResult(success=False, error=f"Destination: {error}")

        if not src_resolved.exists():
            return ToolResult(success=False, error=f"Source not found: {source}")

        try:
            # Ensure parent directory exists
            dst_resolved.parent.mkdir(parents=True, exist_ok=True)

            await asyncio.to_thread(shutil.move, src_resolved, dst_resolved)

            self.logger.info("File moved", source=str(src_resolved), destination=str(dst_resolved))
            return ToolResult(
                success=True,
                result=f"Moved {source} to {destination}",
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))


# Global handler instance
_handler: FileOperationsHandler | None = None


def get_file_handler() -> FileOperationsHandler:
    """Get the global file operations handler."""
    global _handler
    if _handler is None:
        _handler = FileOperationsHandler()
    return _handler


# Tool handlers

async def read_file_handler(path: str, encoding: str = "utf-8") -> ToolResult:
    """Handler for reading files."""
    handler = get_file_handler()
    return await handler.read_file(path, encoding)


async def write_file_handler(
    path: str,
    content: str,
    encoding: str = "utf-8",
    overwrite: bool = False,
) -> ToolResult:
    """Handler for writing files."""
    handler = get_file_handler()
    return await handler.write_file(path, content, encoding, overwrite)


async def list_directory_handler(
    path: str = ".",
    pattern: str = "*",
    recursive: bool = False,
) -> ToolResult:
    """Handler for listing directories."""
    handler = get_file_handler()
    return await handler.list_directory(path, pattern, recursive)


async def delete_file_handler(path: str) -> ToolResult:
    """Handler for deleting files."""
    handler = get_file_handler()
    return await handler.delete_file(path)


async def create_directory_handler(path: str) -> ToolResult:
    """Handler for creating directories."""
    handler = get_file_handler()
    return await handler.create_directory(path)


async def file_info_handler(path: str) -> ToolResult:
    """Handler for getting file info."""
    handler = get_file_handler()
    return await handler.file_info(path)


async def search_files_handler(
    pattern: str,
    path: str = ".",
    file_pattern: str = "*",
    max_results: int = 50,
    case_sensitive: bool = False,
) -> ToolResult:
    """Handler for searching files."""
    handler = get_file_handler()
    return await handler.search_files(pattern, path, file_pattern, max_results, case_sensitive)


async def copy_file_handler(source: str, destination: str) -> ToolResult:
    """Handler for copying files."""
    handler = get_file_handler()
    return await handler.copy_file(source, destination)


async def move_file_handler(source: str, destination: str) -> ToolResult:
    """Handler for moving files."""
    handler = get_file_handler()
    return await handler.move_file(source, destination)


# Tool definitions

def create_file_tools() -> list[Tool]:
    """Create file operation tools."""
    return [
        Tool(
            name="read_file",
            description="Read the contents of a file from the workspace.",
            parameters=[
                ToolParameter(
                    name="path",
                    type="string",
                    description="Path to the file relative to workspace root. Do NOT include 'workspace/' prefix - just use the path like 'myfile.txt' or 'folder/myfile.txt'",
                ),
                ToolParameter(
                    name="encoding",
                    type="string",
                    description="File encoding",
                    required=False,
                    default="utf-8",
                ),
            ],
            handler=read_file_handler,
            permission_required=ToolPermission.READ_ONLY,
            requires_approval=False,
            risk_level="low",
            category="file",
        ),
        Tool(
            name="write_file",
            description="Write content to a file in the workspace.",
            parameters=[
                ToolParameter(
                    name="path",
                    type="string",
                    description="Path to the file relative to workspace root. Do NOT include 'workspace/' prefix - just use the path like 'myfile.txt' or 'folder/myfile.txt'",
                ),
                ToolParameter(
                    name="content",
                    type="string",
                    description="Content to write",
                ),
                ToolParameter(
                    name="encoding",
                    type="string",
                    description="File encoding",
                    required=False,
                    default="utf-8",
                ),
                ToolParameter(
                    name="overwrite",
                    type="boolean",
                    description="Whether to overwrite existing files",
                    required=False,
                    default=False,
                ),
            ],
            handler=write_file_handler,
            permission_required=ToolPermission.READ_WRITE,
            requires_approval=False,
            risk_level="medium",
            category="file",
        ),
        Tool(
            name="list_directory",
            description="List files and directories in the workspace.",
            parameters=[
                ToolParameter(
                    name="path",
                    type="string",
                    description="Directory path relative to workspace root. Do NOT include 'workspace/' prefix",
                    required=False,
                    default=".",
                ),
                ToolParameter(
                    name="pattern",
                    type="string",
                    description="Glob pattern to filter files",
                    required=False,
                    default="*",
                ),
                ToolParameter(
                    name="recursive",
                    type="boolean",
                    description="Whether to search recursively",
                    required=False,
                    default=False,
                ),
            ],
            handler=list_directory_handler,
            permission_required=ToolPermission.READ_ONLY,
            requires_approval=False,
            risk_level="low",
            category="file",
        ),
        Tool(
            name="delete_file",
            description="Delete a file from the workspace.",
            parameters=[
                ToolParameter(
                    name="path",
                    type="string",
                    description="Path to the file to delete",
                ),
            ],
            handler=delete_file_handler,
            permission_required=ToolPermission.READ_WRITE,
            requires_approval=True,  # Requires approval for deletion
            risk_level="high",
            category="file",
        ),
        Tool(
            name="create_directory",
            description="Create a directory in the workspace.",
            parameters=[
                ToolParameter(
                    name="path",
                    type="string",
                    description="Path of the directory to create relative to workspace root. Do NOT include 'workspace/' prefix",
                ),
            ],
            handler=create_directory_handler,
            permission_required=ToolPermission.READ_WRITE,
            requires_approval=False,
            risk_level="low",
            category="file",
        ),
        Tool(
            name="file_info",
            description="Get information about a file or directory.",
            parameters=[
                ToolParameter(
                    name="path",
                    type="string",
                    description="Path to get info for",
                ),
            ],
            handler=file_info_handler,
            permission_required=ToolPermission.READ_ONLY,
            requires_approval=False,
            risk_level="low",
            category="file",
        ),
        Tool(
            name="search_files",
            description="Search for text patterns within files in the workspace.",
            parameters=[
                ToolParameter(
                    name="pattern",
                    type="string",
                    description="Regex pattern to search for",
                ),
                ToolParameter(
                    name="path",
                    type="string",
                    description="Directory to search in",
                    required=False,
                    default=".",
                ),
                ToolParameter(
                    name="file_pattern",
                    type="string",
                    description="Glob pattern to filter files (e.g., '*.py')",
                    required=False,
                    default="*",
                ),
                ToolParameter(
                    name="max_results",
                    type="number",
                    description="Maximum number of results to return",
                    required=False,
                    default=50,
                ),
                ToolParameter(
                    name="case_sensitive",
                    type="boolean",
                    description="Whether search is case-sensitive",
                    required=False,
                    default=False,
                ),
            ],
            handler=search_files_handler,
            permission_required=ToolPermission.READ_ONLY,
            requires_approval=False,
            risk_level="low",
            category="file",
        ),
        Tool(
            name="copy_file",
            description="Copy a file to a new location within the workspace.",
            parameters=[
                ToolParameter(
                    name="source",
                    type="string",
                    description="Source file path",
                ),
                ToolParameter(
                    name="destination",
                    type="string",
                    description="Destination file path",
                ),
            ],
            handler=copy_file_handler,
            permission_required=ToolPermission.READ_WRITE,
            requires_approval=False,
            risk_level="low",
            category="file",
        ),
        Tool(
            name="move_file",
            description="Move a file to a new location within the workspace.",
            parameters=[
                ToolParameter(
                    name="source",
                    type="string",
                    description="Source file path",
                ),
                ToolParameter(
                    name="destination",
                    type="string",
                    description="Destination file path",
                ),
            ],
            handler=move_file_handler,
            permission_required=ToolPermission.READ_WRITE,
            requires_approval=True,  # Moving can be destructive
            risk_level="medium",
            category="file",
        ),
    ]
