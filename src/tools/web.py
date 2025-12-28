"""
Web request tools for Agent Village.

Provides HTTP request capabilities with safety controls and rate limiting.
"""

import asyncio
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse

import httpx
import structlog

from src.tools.registry import Tool, ToolParameter, ToolPermission, ToolResult

logger = structlog.get_logger()


class RateLimiter:
    """
    Token bucket rate limiter for HTTP requests.

    Provides per-host rate limiting to prevent abuse.
    """

    def __init__(
        self,
        requests_per_second: float = 2.0,
        burst_size: int = 5,
    ):
        self.requests_per_second = requests_per_second
        self.burst_size = burst_size
        self._tokens: dict[str, float] = defaultdict(lambda: float(burst_size))
        self._last_update: dict[str, float] = defaultdict(time.monotonic)
        self._lock = asyncio.Lock()

    async def acquire(self, host: str) -> bool:
        """
        Acquire a token for the given host.

        Returns True if request can proceed, False if rate limited.
        """
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_update[host]
            self._last_update[host] = now

            # Add tokens based on elapsed time
            self._tokens[host] = min(
                self.burst_size,
                self._tokens[host] + elapsed * self.requests_per_second
            )

            if self._tokens[host] >= 1.0:
                self._tokens[host] -= 1.0
                return True
            return False

    async def wait_for_token(self, host: str, timeout: float = 30.0) -> bool:
        """
        Wait until a token is available for the given host.

        Returns True if token acquired, False if timeout exceeded.
        """
        start = time.monotonic()
        while True:
            if await self.acquire(host):
                return True

            if time.monotonic() - start > timeout:
                return False

            # Calculate wait time until next token
            async with self._lock:
                tokens_needed = 1.0 - self._tokens[host]
                wait_time = tokens_needed / self.requests_per_second

            await asyncio.sleep(min(wait_time, 0.5))


@dataclass
class WebRequestConfig:
    """Configuration for web request tools."""

    max_response_size: int = 1_000_000  # 1MB
    default_timeout: float = 30.0
    max_timeout: float = 60.0
    allowed_schemes: set[str] = field(default_factory=lambda: {"http", "https"})
    blocked_hosts: set[str] = field(default_factory=lambda: {
        "localhost", "127.0.0.1", "0.0.0.0", "::1",
        "169.254.169.254",  # AWS metadata
        "metadata.google.internal",  # GCP metadata
    })
    allowed_methods: set[str] = field(default_factory=lambda: {
        "GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"
    })
    user_agent: str = "AgentVillage/1.0"
    # Rate limiting
    rate_limit_enabled: bool = True
    requests_per_second: float = 2.0
    burst_size: int = 5


class WebRequestHandler:
    """Handler for making HTTP requests with security controls and rate limiting."""

    def __init__(self, config: WebRequestConfig | None = None):
        self.config = config or WebRequestConfig()
        self.logger = logger.bind(component="web_request")
        self.rate_limiter = RateLimiter(
            requests_per_second=self.config.requests_per_second,
            burst_size=self.config.burst_size,
        ) if self.config.rate_limit_enabled else None

    def _validate_url(self, url: str) -> tuple[bool, str | None]:
        """Validate URL for security."""
        try:
            parsed = urlparse(url)

            # Check scheme
            if parsed.scheme not in self.config.allowed_schemes:
                return False, f"URL scheme '{parsed.scheme}' is not allowed"

            # Check host
            host = parsed.hostname or ""
            if host in self.config.blocked_hosts:
                return False, f"Requests to '{host}' are not allowed"

            # Check for IP addresses in private ranges
            import ipaddress
            try:
                ip = ipaddress.ip_address(host)
                if ip.is_private or ip.is_loopback or ip.is_link_local:
                    return False, "Requests to private/internal IPs are not allowed"
            except ValueError:
                pass  # Not an IP address, that's fine

            return True, None
        except Exception as e:
            return False, f"Invalid URL: {e}"

    async def request(
        self,
        method: str,
        url: str,
        headers: dict[str, str] | None = None,
        body: str | dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> ToolResult:
        """Make an HTTP request with rate limiting."""
        self.logger.info("Making HTTP request", method=method, url=url)

        # Validate method
        method = method.upper()
        if method not in self.config.allowed_methods:
            return ToolResult(success=False, error=f"HTTP method '{method}' is not allowed")

        # Validate URL
        is_valid, error = self._validate_url(url)
        if not is_valid:
            return ToolResult(success=False, error=error)

        # Apply rate limiting
        if self.rate_limiter:
            parsed = urlparse(url)
            host = parsed.hostname or "unknown"
            if not await self.rate_limiter.wait_for_token(host, timeout=5.0):
                return ToolResult(
                    success=False,
                    error=f"Rate limit exceeded for {host}. Try again later.",
                )

        # Set timeout
        request_timeout = min(
            timeout or self.config.default_timeout,
            self.config.max_timeout
        )

        # Prepare headers
        request_headers = {"User-Agent": self.config.user_agent}
        if headers:
            request_headers.update(headers)

        # Prepare body
        json_body = None
        content = None
        if body:
            if isinstance(body, dict):
                json_body = body
            else:
                content = body

        try:
            async with httpx.AsyncClient(timeout=request_timeout) as client:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=request_headers,
                    json=json_body,
                    content=content,
                )

                # Check response size
                content_length = len(response.content)
                if content_length > self.config.max_response_size:
                    return ToolResult(
                        success=True,
                        result={
                            "status_code": response.status_code,
                            "headers": dict(response.headers),
                            "body": f"(Response too large: {content_length} bytes, max: {self.config.max_response_size})",
                            "truncated": True,
                        },
                    )

                # Try to parse as JSON
                try:
                    body_content = response.json()
                except Exception:
                    body_content = response.text

                return ToolResult(
                    success=True,
                    result={
                        "status_code": response.status_code,
                        "headers": dict(response.headers),
                        "body": body_content,
                        "url": str(response.url),
                    },
                    metadata={
                        "elapsed_ms": response.elapsed.total_seconds() * 1000,
                        "content_length": content_length,
                    },
                )

        except httpx.TimeoutException:
            return ToolResult(
                success=False,
                error=f"Request timed out after {request_timeout} seconds",
            )
        except httpx.ConnectError as e:
            return ToolResult(success=False, error=f"Connection error: {e}")
        except Exception as e:
            self.logger.error("HTTP request failed", error=str(e))
            return ToolResult(success=False, error=str(e))


# Global handler instance
_handler: WebRequestHandler | None = None


def get_web_handler() -> WebRequestHandler:
    """Get the global web request handler."""
    global _handler
    if _handler is None:
        _handler = WebRequestHandler()
    return _handler


# Tool handlers

async def http_get_handler(
    url: str,
    headers: dict[str, str] | None = None,
    timeout: float = 30.0,
) -> ToolResult:
    """Handler for HTTP GET requests."""
    handler = get_web_handler()
    return await handler.request("GET", url, headers=headers, timeout=timeout)


async def http_post_handler(
    url: str,
    body: str | dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: float = 30.0,
) -> ToolResult:
    """Handler for HTTP POST requests."""
    handler = get_web_handler()
    return await handler.request("POST", url, headers=headers, body=body, timeout=timeout)


async def http_request_handler(
    method: str,
    url: str,
    body: str | dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: float = 30.0,
) -> ToolResult:
    """Handler for generic HTTP requests."""
    handler = get_web_handler()
    return await handler.request(method, url, headers=headers, body=body, timeout=timeout)


async def fetch_webpage_handler(
    url: str,
    extract_text: bool = True,
) -> ToolResult:
    """Fetch a webpage and optionally extract text content."""
    handler = get_web_handler()
    result = await handler.request("GET", url)

    if not result.success:
        return result

    if extract_text and result.result:
        body = result.result.get("body", "")
        if isinstance(body, str) and "<" in body:
            # Simple HTML to text conversion
            import re
            # Remove script and style
            text = re.sub(r'<script[^>]*>.*?</script>', '', body, flags=re.DOTALL | re.IGNORECASE)
            text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
            # Remove tags
            text = re.sub(r'<[^>]+>', ' ', text)
            # Clean whitespace
            text = re.sub(r'\s+', ' ', text).strip()
            # Truncate if too long
            if len(text) > 10000:
                text = text[:10000] + "... (truncated)"
            result.result["text_content"] = text

    return result


# Tool definitions

def create_web_tools() -> list[Tool]:
    """Create web-related tools."""
    return [
        Tool(
            name="http_get",
            description="Make an HTTP GET request to a URL and return the response.",
            parameters=[
                ToolParameter(
                    name="url",
                    type="string",
                    description="The URL to request",
                ),
                ToolParameter(
                    name="headers",
                    type="object",
                    description="Optional HTTP headers",
                    required=False,
                ),
                ToolParameter(
                    name="timeout",
                    type="number",
                    description="Request timeout in seconds (max 60)",
                    required=False,
                    default=30.0,
                ),
            ],
            handler=http_get_handler,
            permission_required=ToolPermission.READ_ONLY,
            requires_approval=False,
            risk_level="low",
            category="web",
        ),
        Tool(
            name="http_post",
            description="Make an HTTP POST request with optional body.",
            parameters=[
                ToolParameter(
                    name="url",
                    type="string",
                    description="The URL to request",
                ),
                ToolParameter(
                    name="body",
                    type="object",
                    description="Request body (JSON or string)",
                    required=False,
                ),
                ToolParameter(
                    name="headers",
                    type="object",
                    description="Optional HTTP headers",
                    required=False,
                ),
                ToolParameter(
                    name="timeout",
                    type="number",
                    description="Request timeout in seconds (max 60)",
                    required=False,
                    default=30.0,
                ),
            ],
            handler=http_post_handler,
            permission_required=ToolPermission.READ_WRITE,
            requires_approval=False,
            risk_level="medium",
            category="web",
        ),
        Tool(
            name="http_request",
            description="Make a generic HTTP request with any method.",
            parameters=[
                ToolParameter(
                    name="method",
                    type="string",
                    description="HTTP method (GET, POST, PUT, PATCH, DELETE)",
                    enum=["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"],
                ),
                ToolParameter(
                    name="url",
                    type="string",
                    description="The URL to request",
                ),
                ToolParameter(
                    name="body",
                    type="object",
                    description="Request body (JSON or string)",
                    required=False,
                ),
                ToolParameter(
                    name="headers",
                    type="object",
                    description="Optional HTTP headers",
                    required=False,
                ),
                ToolParameter(
                    name="timeout",
                    type="number",
                    description="Request timeout in seconds (max 60)",
                    required=False,
                    default=30.0,
                ),
            ],
            handler=http_request_handler,
            permission_required=ToolPermission.READ_WRITE,
            requires_approval=False,
            risk_level="medium",
            category="web",
        ),
        Tool(
            name="fetch_webpage",
            description="Fetch a webpage and extract its text content.",
            parameters=[
                ToolParameter(
                    name="url",
                    type="string",
                    description="The URL of the webpage to fetch",
                ),
                ToolParameter(
                    name="extract_text",
                    type="boolean",
                    description="Whether to extract plain text from HTML",
                    required=False,
                    default=True,
                ),
            ],
            handler=fetch_webpage_handler,
            permission_required=ToolPermission.READ_ONLY,
            requires_approval=False,
            risk_level="low",
            category="web",
        ),
    ]
