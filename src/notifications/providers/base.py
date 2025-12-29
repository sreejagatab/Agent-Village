"""
Base Notification Provider.

Provides the abstract interface for all notification providers.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
import asyncio

from src.notifications.models import (
    Notification,
    NotificationType,
    ChannelType,
    ChannelConfig,
)


class ProviderError(Exception):
    """Base exception for provider errors."""

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        retryable: bool = True,
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.retryable = retryable


class ProviderConnectionError(ProviderError):
    """Error connecting to the provider."""

    def __init__(self, message: str = "Failed to connect to provider"):
        super().__init__(message, error_code="CONNECTION_ERROR", retryable=True)


class ProviderAuthenticationError(ProviderError):
    """Authentication failed with the provider."""

    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, error_code="AUTH_ERROR", retryable=False)


class ProviderRateLimitError(ProviderError):
    """Rate limit exceeded with the provider."""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: Optional[int] = None,
    ):
        super().__init__(message, error_code="RATE_LIMIT", retryable=True)
        self.retry_after = retry_after


class ProviderValidationError(ProviderError):
    """Invalid notification data for the provider."""

    def __init__(self, message: str, field: Optional[str] = None):
        super().__init__(message, error_code="VALIDATION_ERROR", retryable=False)
        self.field = field


@dataclass
class ProviderResult:
    """Result of a notification delivery attempt."""
    success: bool
    provider_message_id: Optional[str] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    retryable: bool = True
    response_data: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)

    @classmethod
    def success_result(
        cls,
        provider_message_id: Optional[str] = None,
        response_data: Optional[Dict[str, Any]] = None,
    ) -> "ProviderResult":
        """Create a success result."""
        return cls(
            success=True,
            provider_message_id=provider_message_id,
            response_data=response_data or {},
        )

    @classmethod
    def error_result(
        cls,
        error_code: str,
        error_message: str,
        retryable: bool = True,
        response_data: Optional[Dict[str, Any]] = None,
    ) -> "ProviderResult":
        """Create an error result."""
        return cls(
            success=False,
            error_code=error_code,
            error_message=error_message,
            retryable=retryable,
            response_data=response_data or {},
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "provider_message_id": self.provider_message_id,
            "error_code": self.error_code,
            "error_message": self.error_message,
            "retryable": self.retryable,
            "timestamp": self.timestamp.isoformat(),
        }


class NotificationProvider(ABC):
    """Abstract base class for notification providers."""

    # Provider metadata
    provider_type: ChannelType
    notification_types: List[NotificationType] = []

    def __init__(self, config: Optional[ChannelConfig] = None):
        """Initialize the provider."""
        self.config = config
        self._is_initialized = False

    @property
    def name(self) -> str:
        """Get provider name."""
        return self.config.name if self.config else self.__class__.__name__

    @property
    def is_enabled(self) -> bool:
        """Check if provider is enabled."""
        return self.config.is_enabled if self.config else True

    async def initialize(self) -> None:
        """Initialize the provider (connect, authenticate, etc.)."""
        self._is_initialized = True

    async def shutdown(self) -> None:
        """Shutdown the provider (cleanup resources)."""
        self._is_initialized = False

    def validate_notification(self, notification: Notification) -> None:
        """
        Validate that the notification can be sent via this provider.

        Raises:
            ProviderValidationError: If validation fails.
        """
        if notification.notification_type not in self.notification_types:
            raise ProviderValidationError(
                f"Provider does not support {notification.notification_type.value} notifications",
                field="notification_type",
            )

    @abstractmethod
    async def send(self, notification: Notification) -> ProviderResult:
        """
        Send a notification.

        Args:
            notification: The notification to send.

        Returns:
            ProviderResult with success/failure details.
        """
        pass

    async def send_batch(
        self,
        notifications: List[Notification],
    ) -> List[ProviderResult]:
        """
        Send multiple notifications.

        Default implementation sends sequentially.
        Override for batch-optimized sending.

        Args:
            notifications: List of notifications to send.

        Returns:
            List of ProviderResults.
        """
        results = []
        for notification in notifications:
            result = await self.send(notification)
            results.append(result)
        return results

    async def check_status(
        self,
        provider_message_id: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Check the delivery status of a sent notification.

        Args:
            provider_message_id: The provider's message ID.

        Returns:
            Status information if available.
        """
        return None

    def get_settings(self, key: str, default: Any = None) -> Any:
        """Get a settings value from config."""
        if self.config and self.config.settings:
            return self.config.settings.get(key, default)
        return default

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(type={self.provider_type.value}, enabled={self.is_enabled})"
