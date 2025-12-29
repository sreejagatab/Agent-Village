"""
In-App Notification Provider.

Provides in-app notifications that are stored and delivered
within the application (no external service).
"""

from typing import Any, Dict, List, Optional
from datetime import datetime

from src.notifications.models import (
    Notification,
    NotificationType,
    ChannelType,
    ChannelConfig,
)
from src.notifications.providers.base import (
    NotificationProvider,
    ProviderResult,
    ProviderValidationError,
)


class InAppProvider(NotificationProvider):
    """In-app notification provider (internal storage)."""

    provider_type = ChannelType.INTERNAL
    notification_types = [NotificationType.IN_APP]

    async def send(self, notification: Notification) -> ProviderResult:
        """
        'Send' an in-app notification.

        For in-app notifications, 'sending' means marking the notification
        as ready for delivery. The actual delivery happens when the user
        fetches their notifications.
        """
        self.validate_notification(notification)

        # In-app notifications are immediately 'sent' since they're stored internally
        # The notification service handles the actual storage

        return ProviderResult.success_result(
            provider_message_id=notification.notification_id,
            response_data={
                "delivery_method": "in_app",
                "user_id": notification.recipient.user_id,
            },
        )

    def validate_notification(self, notification: Notification) -> None:
        """Validate in-app notification."""
        super().validate_notification(notification)

        if not notification.recipient.user_id:
            raise ProviderValidationError(
                "Recipient user_id is required for in-app notifications",
                field="recipient.user_id",
            )

        if not notification.content.title and not notification.content.body:
            raise ProviderValidationError(
                "Either title or body is required for in-app notifications",
                field="content",
            )

    async def send_batch(
        self,
        notifications: List[Notification],
    ) -> List[ProviderResult]:
        """
        Send multiple in-app notifications.

        In-app notifications can be processed very quickly since there's
        no external service to call.
        """
        results = []
        for notification in notifications:
            try:
                result = await self.send(notification)
                results.append(result)
            except ProviderValidationError as e:
                results.append(ProviderResult.error_result(
                    error_code="VALIDATION_ERROR",
                    error_message=str(e),
                    retryable=False,
                ))
        return results
