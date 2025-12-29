"""
Notification Service Layer.

Provides notification management including:
- Notification creation and storage
- Provider management and routing
- Delivery processing and retry logic
- User preferences management
- Template management
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Set, Type
import asyncio
import logging

from src.notifications.models import (
    Notification,
    NotificationStatus,
    NotificationType,
    NotificationPriority,
    NotificationCategory,
    NotificationContent,
    NotificationRecipient,
    NotificationTemplate,
    NotificationPreferences,
    NotificationConfig,
    NotificationStats,
    NotificationListResponse,
    DeliveryAttempt,
    ChannelType,
    ChannelConfig,
)
from src.notifications.providers.base import (
    NotificationProvider,
    ProviderResult,
    ProviderError,
)

logger = logging.getLogger(__name__)


# Exceptions
class NotificationError(Exception):
    """Base exception for notification errors."""
    pass


class NotificationNotFoundError(NotificationError):
    """Notification not found."""
    pass


class TemplateNotFoundError(NotificationError):
    """Template not found."""
    pass


class ProviderNotConfiguredError(NotificationError):
    """No provider configured for notification type."""
    pass


class PreferencesBlockedError(NotificationError):
    """User preferences block this notification."""
    pass


class RateLimitExceededError(NotificationError):
    """Rate limit exceeded for user."""
    pass


@dataclass
class NotificationStore:
    """In-memory notification storage with indexing."""

    # Primary storage
    _notifications: Dict[str, Notification] = field(default_factory=dict)

    # Templates
    _templates: Dict[str, NotificationTemplate] = field(default_factory=dict)

    # User preferences
    _preferences: Dict[str, NotificationPreferences] = field(default_factory=dict)

    # Indexes
    _by_user: Dict[str, Set[str]] = field(default_factory=lambda: {})
    _by_status: Dict[NotificationStatus, Set[str]] = field(default_factory=lambda: {})
    _by_tenant: Dict[str, Set[str]] = field(default_factory=lambda: {})
    _pending_queue: List[str] = field(default_factory=list)

    # Rate limiting
    _user_counts: Dict[str, Dict[str, int]] = field(default_factory=dict)

    # Notifications
    async def save_notification(self, notification: Notification) -> None:
        """Save a notification."""
        self._notifications[notification.notification_id] = notification

        # Update indexes
        user_id = notification.recipient.user_id
        if user_id not in self._by_user:
            self._by_user[user_id] = set()
        self._by_user[user_id].add(notification.notification_id)

        if notification.status not in self._by_status:
            self._by_status[notification.status] = set()
        self._by_status[notification.status].add(notification.notification_id)

        if notification.tenant_id:
            if notification.tenant_id not in self._by_tenant:
                self._by_tenant[notification.tenant_id] = set()
            self._by_tenant[notification.tenant_id].add(notification.notification_id)

        # Add to pending queue if pending
        if notification.status == NotificationStatus.PENDING:
            if notification.notification_id not in self._pending_queue:
                self._pending_queue.append(notification.notification_id)

    async def get_notification(self, notification_id: str) -> Optional[Notification]:
        """Get a notification by ID."""
        return self._notifications.get(notification_id)

    async def get_notifications_by_user(
        self,
        user_id: str,
        statuses: Optional[List[NotificationStatus]] = None,
        offset: int = 0,
        limit: int = 50,
    ) -> List[Notification]:
        """Get notifications for a user."""
        notification_ids = self._by_user.get(user_id, set())
        notifications = []

        for nid in notification_ids:
            notification = self._notifications.get(nid)
            if notification:
                if statuses is None or notification.status in statuses:
                    notifications.append(notification)

        # Sort by created_at descending
        notifications.sort(key=lambda n: n.created_at, reverse=True)

        return notifications[offset:offset + limit]

    async def get_pending_notifications(
        self,
        limit: int = 100,
        before: Optional[datetime] = None,
    ) -> List[Notification]:
        """Get notifications pending delivery."""
        now = before or datetime.utcnow()
        pending = []

        for notification_id in list(self._pending_queue):
            if len(pending) >= limit:
                break

            notification = self._notifications.get(notification_id)
            if not notification:
                self._pending_queue.remove(notification_id)
                continue

            # Skip if scheduled for later
            if notification.is_scheduled:
                continue

            # Skip if expired
            if notification.is_expired:
                notification.status = NotificationStatus.CANCELLED
                self._pending_queue.remove(notification_id)
                continue

            pending.append(notification)

        return pending

    async def update_notification_status(
        self,
        notification_id: str,
        old_status: NotificationStatus,
        new_status: NotificationStatus,
    ) -> None:
        """Update notification status and indexes."""
        notification = self._notifications.get(notification_id)
        if not notification:
            return

        # Update status index
        if old_status in self._by_status:
            self._by_status[old_status].discard(notification_id)
        if new_status not in self._by_status:
            self._by_status[new_status] = set()
        self._by_status[new_status].add(notification_id)

        # Remove from pending queue if no longer pending
        if new_status != NotificationStatus.PENDING:
            if notification_id in self._pending_queue:
                self._pending_queue.remove(notification_id)

    async def delete_notification(self, notification_id: str) -> bool:
        """Delete a notification."""
        notification = self._notifications.pop(notification_id, None)
        if not notification:
            return False

        # Clean up indexes
        user_id = notification.recipient.user_id
        if user_id in self._by_user:
            self._by_user[user_id].discard(notification_id)

        if notification.status in self._by_status:
            self._by_status[notification.status].discard(notification_id)

        if notification.tenant_id and notification.tenant_id in self._by_tenant:
            self._by_tenant[notification.tenant_id].discard(notification_id)

        if notification_id in self._pending_queue:
            self._pending_queue.remove(notification_id)

        return True

    async def count_unread(self, user_id: str) -> int:
        """Count unread notifications for a user."""
        notification_ids = self._by_user.get(user_id, set())
        count = 0

        for nid in notification_ids:
            notification = self._notifications.get(nid)
            if notification and notification.status not in (
                NotificationStatus.READ,
                NotificationStatus.CANCELLED,
            ):
                count += 1

        return count

    # Templates
    async def save_template(self, template: NotificationTemplate) -> None:
        """Save a notification template."""
        self._templates[template.template_id] = template

    async def get_template(self, template_id: str) -> Optional[NotificationTemplate]:
        """Get a template by ID."""
        return self._templates.get(template_id)

    async def get_templates(
        self,
        notification_type: Optional[NotificationType] = None,
        tenant_id: Optional[str] = None,
    ) -> List[NotificationTemplate]:
        """Get templates with optional filtering."""
        templates = []

        for template in self._templates.values():
            if notification_type and template.notification_type != notification_type:
                continue
            if tenant_id and template.tenant_id != tenant_id:
                continue
            if template.is_active:
                templates.append(template)

        return templates

    async def delete_template(self, template_id: str) -> bool:
        """Delete a template."""
        return self._templates.pop(template_id, None) is not None

    # Preferences
    async def save_preferences(self, preferences: NotificationPreferences) -> None:
        """Save user notification preferences."""
        self._preferences[preferences.user_id] = preferences

    async def get_preferences(self, user_id: str) -> Optional[NotificationPreferences]:
        """Get user notification preferences."""
        return self._preferences.get(user_id)

    async def delete_preferences(self, user_id: str) -> bool:
        """Delete user preferences."""
        return self._preferences.pop(user_id, None) is not None

    # Rate limiting
    async def check_rate_limit(
        self,
        user_id: str,
        max_per_hour: int,
        max_per_day: int,
    ) -> bool:
        """Check if user is within rate limits."""
        now = datetime.utcnow()
        hour_key = now.strftime("%Y%m%d%H")
        day_key = now.strftime("%Y%m%d")

        if user_id not in self._user_counts:
            self._user_counts[user_id] = {}

        counts = self._user_counts[user_id]

        hour_count = counts.get(hour_key, 0)
        day_count = counts.get(day_key, 0)

        return hour_count < max_per_hour and day_count < max_per_day

    async def increment_rate_limit(self, user_id: str) -> None:
        """Increment rate limit counters for a user."""
        now = datetime.utcnow()
        hour_key = now.strftime("%Y%m%d%H")
        day_key = now.strftime("%Y%m%d")

        if user_id not in self._user_counts:
            self._user_counts[user_id] = {}

        counts = self._user_counts[user_id]
        counts[hour_key] = counts.get(hour_key, 0) + 1
        counts[day_key] = counts.get(day_key, 0) + 1

        # Clean old keys
        old_keys = [k for k in counts.keys() if k < (now - timedelta(days=2)).strftime("%Y%m%d")]
        for key in old_keys:
            del counts[key]

    # Cleanup
    async def cleanup_old_notifications(self, days: int = 30) -> int:
        """Delete notifications older than specified days."""
        cutoff = datetime.utcnow() - timedelta(days=days)
        to_delete = []

        for notification_id, notification in self._notifications.items():
            if notification.created_at < cutoff:
                to_delete.append(notification_id)

        for notification_id in to_delete:
            await self.delete_notification(notification_id)

        return len(to_delete)


class NotificationService:
    """Main notification service."""

    def __init__(
        self,
        store: NotificationStore,
        config: Optional[NotificationConfig] = None,
    ):
        self.store = store
        self.config = config or NotificationConfig()

        # Provider registry
        self._providers: Dict[NotificationType, List[NotificationProvider]] = {
            NotificationType.EMAIL: [],
            NotificationType.SMS: [],
            NotificationType.PUSH: [],
            NotificationType.IN_APP: [],
        }

        # Event handlers (for webhooks integration)
        self._event_handlers: Dict[str, List[Callable]] = {}

        # Background task handle
        self._processor_task: Optional[asyncio.Task] = None

    # Provider management
    def register_provider(
        self,
        provider: NotificationProvider,
        notification_type: Optional[NotificationType] = None,
    ) -> None:
        """Register a notification provider."""
        types = [notification_type] if notification_type else provider.notification_types

        for ntype in types:
            if ntype in self._providers:
                self._providers[ntype].append(provider)
                logger.info(f"Registered provider {provider.name} for {ntype.value}")

    def get_provider(
        self,
        notification_type: NotificationType,
    ) -> Optional[NotificationProvider]:
        """Get the default provider for a notification type."""
        providers = self._providers.get(notification_type, [])

        # Find enabled provider
        for provider in providers:
            if provider.is_enabled:
                return provider

        return None

    # Core notification methods
    async def send_notification(
        self,
        notification: Notification,
        check_preferences: bool = True,
    ) -> Notification:
        """
        Send a notification.

        Args:
            notification: The notification to send.
            check_preferences: Whether to check user preferences.

        Returns:
            The notification with updated status.
        """
        # Check rate limits
        user_id = notification.recipient.user_id
        if not await self.store.check_rate_limit(
            user_id,
            self.config.max_notifications_per_user_per_hour,
            self.config.max_notifications_per_user_per_day,
        ):
            raise RateLimitExceededError(f"Rate limit exceeded for user {user_id}")

        # Check user preferences
        if check_preferences:
            preferences = await self.store.get_preferences(user_id)
            if preferences and not preferences.should_send(
                notification.notification_type,
                notification.category,
                notification.priority,
            ):
                raise PreferencesBlockedError("User preferences block this notification")

        # Save notification
        await self.store.save_notification(notification)
        await self.store.increment_rate_limit(user_id)

        # If scheduled, just save and return
        if notification.is_scheduled:
            logger.info(f"Notification {notification.notification_id} scheduled for later")
            return notification

        # Get provider
        provider = self.get_provider(notification.notification_type)
        if not provider:
            notification.status = NotificationStatus.FAILED
            await self.store.save_notification(notification)
            raise ProviderNotConfiguredError(
                f"No provider configured for {notification.notification_type.value}"
            )

        # Send via provider
        result = await self._deliver_notification(notification, provider)

        # Emit event
        await self._emit_event("notification.sent", {
            "notification_id": notification.notification_id,
            "user_id": user_id,
            "type": notification.notification_type.value,
            "status": notification.status.value,
        })

        return notification

    async def send_to_user(
        self,
        user_id: str,
        notification_type: NotificationType,
        content: NotificationContent,
        category: NotificationCategory = NotificationCategory.SYSTEM,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        **kwargs,
    ) -> Notification:
        """Send a notification to a user by ID."""
        # Get user preferences for contact info
        preferences = await self.store.get_preferences(user_id)

        recipient = NotificationRecipient(
            user_id=user_id,
            email=preferences.email if preferences else None,
            phone=preferences.phone if preferences else None,
            device_tokens=preferences.device_tokens if preferences else [],
        )

        notification = Notification(
            notification_type=notification_type,
            category=category,
            priority=priority,
            recipient=recipient,
            content=content,
            **kwargs,
        )

        return await self.send_notification(notification)

    async def send_from_template(
        self,
        template_id: str,
        recipient: NotificationRecipient,
        data: Dict[str, Any],
        **kwargs,
    ) -> Notification:
        """Send a notification using a template."""
        template = await self.store.get_template(template_id)
        if not template:
            raise TemplateNotFoundError(f"Template {template_id} not found")

        # Render template
        content = template.render(data)

        notification = Notification(
            notification_type=template.notification_type,
            category=template.category,
            priority=template.default_priority,
            recipient=recipient,
            content=content,
            template_id=template_id,
            template_data=data,
            **kwargs,
        )

        return await self.send_notification(notification)

    async def send_bulk(
        self,
        notifications: List[Notification],
        check_preferences: bool = True,
    ) -> List[Notification]:
        """Send multiple notifications."""
        results = []

        # Group by type for batch processing
        by_type: Dict[NotificationType, List[Notification]] = {}
        for notification in notifications:
            ntype = notification.notification_type
            if ntype not in by_type:
                by_type[ntype] = []
            by_type[ntype].append(notification)

        # Process each type
        for ntype, type_notifications in by_type.items():
            provider = self.get_provider(ntype)
            if not provider:
                for notification in type_notifications:
                    notification.status = NotificationStatus.FAILED
                    results.append(notification)
                continue

            # Process in batches
            for i in range(0, len(type_notifications), self.config.batch_size):
                batch = type_notifications[i:i + self.config.batch_size]

                for notification in batch:
                    try:
                        if check_preferences:
                            preferences = await self.store.get_preferences(
                                notification.recipient.user_id
                            )
                            if preferences and not preferences.should_send(
                                notification.notification_type,
                                notification.category,
                                notification.priority,
                            ):
                                notification.status = NotificationStatus.CANCELLED
                                results.append(notification)
                                continue

                        await self.store.save_notification(notification)
                        await self._deliver_notification(notification, provider)
                        results.append(notification)

                    except Exception as e:
                        notification.status = NotificationStatus.FAILED
                        results.append(notification)
                        logger.error(f"Failed to send notification: {e}")

                # Small delay between batches
                if i + self.config.batch_size < len(type_notifications):
                    await asyncio.sleep(self.config.batch_delay_ms / 1000)

        return results

    async def _deliver_notification(
        self,
        notification: Notification,
        provider: NotificationProvider,
    ) -> ProviderResult:
        """Deliver a notification via a provider."""
        notification.status = NotificationStatus.SENDING
        old_status = notification.status

        attempt = DeliveryAttempt(
            attempt_number=notification.attempt_count + 1,
            channel_type=provider.provider_type,
        )

        try:
            result = await provider.send(notification)

            attempt.complete(
                success=result.success,
                error_code=result.error_code,
                error_message=result.error_message,
                provider_message_id=result.provider_message_id,
                provider_response=result.response_data,
            )

            notification.add_attempt(attempt)

        except ProviderError as e:
            attempt.complete(
                success=False,
                error_code=e.error_code,
                error_message=str(e),
            )
            notification.add_attempt(attempt)
            result = ProviderResult.error_result(
                error_code=e.error_code or "PROVIDER_ERROR",
                error_message=str(e),
                retryable=e.retryable,
            )

        except Exception as e:
            attempt.complete(
                success=False,
                error_code="UNKNOWN_ERROR",
                error_message=str(e),
            )
            notification.add_attempt(attempt)
            result = ProviderResult.error_result(
                error_code="UNKNOWN_ERROR",
                error_message=str(e),
                retryable=True,
            )

        # Update status in store
        await self.store.update_notification_status(
            notification.notification_id,
            old_status,
            notification.status,
        )
        await self.store.save_notification(notification)

        return result

    # Notification management
    async def get_notification(self, notification_id: str) -> Notification:
        """Get a notification by ID."""
        notification = await self.store.get_notification(notification_id)
        if not notification:
            raise NotificationNotFoundError(f"Notification {notification_id} not found")
        return notification

    async def get_user_notifications(
        self,
        user_id: str,
        statuses: Optional[List[NotificationStatus]] = None,
        offset: int = 0,
        limit: int = 50,
    ) -> NotificationListResponse:
        """Get notifications for a user."""
        notifications = await self.store.get_notifications_by_user(
            user_id,
            statuses=statuses,
            offset=offset,
            limit=limit,
        )

        # Get total count
        all_notifications = await self.store.get_notifications_by_user(user_id)
        total = len(all_notifications)

        unread = await self.store.count_unread(user_id)

        return NotificationListResponse(
            notifications=notifications,
            total=total,
            offset=offset,
            limit=limit,
            unread_count=unread,
        )

    async def mark_as_read(
        self,
        notification_id: str,
        user_id: Optional[str] = None,
    ) -> Notification:
        """Mark a notification as read."""
        notification = await self.get_notification(notification_id)

        # Verify ownership if user_id provided
        if user_id and notification.recipient.user_id != user_id:
            raise NotificationNotFoundError("Notification not found")

        old_status = notification.status
        notification.mark_read()

        await self.store.update_notification_status(
            notification_id,
            old_status,
            notification.status,
        )
        await self.store.save_notification(notification)

        return notification

    async def mark_all_as_read(self, user_id: str) -> int:
        """Mark all notifications as read for a user."""
        notifications = await self.store.get_notifications_by_user(user_id)
        count = 0

        for notification in notifications:
            if notification.status not in (
                NotificationStatus.READ,
                NotificationStatus.CANCELLED,
            ):
                old_status = notification.status
                notification.mark_read()
                await self.store.update_notification_status(
                    notification.notification_id,
                    old_status,
                    notification.status,
                )
                await self.store.save_notification(notification)
                count += 1

        return count

    async def cancel_notification(self, notification_id: str) -> Notification:
        """Cancel a pending notification."""
        notification = await self.get_notification(notification_id)

        old_status = notification.status
        if not notification.cancel():
            raise NotificationError(
                f"Cannot cancel notification in {notification.status.value} status"
            )

        await self.store.update_notification_status(
            notification_id,
            old_status,
            notification.status,
        )
        await self.store.save_notification(notification)

        return notification

    async def delete_notification(
        self,
        notification_id: str,
        user_id: Optional[str] = None,
    ) -> bool:
        """Delete a notification."""
        notification = await self.store.get_notification(notification_id)
        if not notification:
            return False

        # Verify ownership if user_id provided
        if user_id and notification.recipient.user_id != user_id:
            return False

        return await self.store.delete_notification(notification_id)

    # Template management
    async def create_template(
        self,
        name: str,
        notification_type: NotificationType,
        body_template: str,
        subject_template: Optional[str] = None,
        title_template: Optional[str] = None,
        **kwargs,
    ) -> NotificationTemplate:
        """Create a notification template."""
        template = NotificationTemplate(
            name=name,
            notification_type=notification_type,
            body_template=body_template,
            subject_template=subject_template,
            title_template=title_template,
            **kwargs,
        )

        await self.store.save_template(template)
        return template

    async def get_template(self, template_id: str) -> NotificationTemplate:
        """Get a template by ID."""
        template = await self.store.get_template(template_id)
        if not template:
            raise TemplateNotFoundError(f"Template {template_id} not found")
        return template

    async def update_template(
        self,
        template_id: str,
        **updates,
    ) -> NotificationTemplate:
        """Update a template."""
        template = await self.get_template(template_id)

        for key, value in updates.items():
            if hasattr(template, key):
                setattr(template, key, value)

        template.updated_at = datetime.utcnow()
        template.version += 1

        await self.store.save_template(template)
        return template

    async def delete_template(self, template_id: str) -> bool:
        """Delete a template."""
        return await self.store.delete_template(template_id)

    async def list_templates(
        self,
        notification_type: Optional[NotificationType] = None,
        tenant_id: Optional[str] = None,
    ) -> List[NotificationTemplate]:
        """List templates."""
        return await self.store.get_templates(notification_type, tenant_id)

    # Preferences management
    async def get_preferences(self, user_id: str) -> NotificationPreferences:
        """Get user preferences (creates default if not exists)."""
        preferences = await self.store.get_preferences(user_id)
        if not preferences:
            preferences = NotificationPreferences(user_id=user_id)
            await self.store.save_preferences(preferences)
        return preferences

    async def update_preferences(
        self,
        user_id: str,
        **updates,
    ) -> NotificationPreferences:
        """Update user preferences."""
        preferences = await self.get_preferences(user_id)

        for key, value in updates.items():
            if hasattr(preferences, key):
                setattr(preferences, key, value)

        preferences.updated_at = datetime.utcnow()
        await self.store.save_preferences(preferences)

        return preferences

    async def register_device(
        self,
        user_id: str,
        device_token: str,
    ) -> NotificationPreferences:
        """Register a device token for push notifications."""
        preferences = await self.get_preferences(user_id)

        if device_token not in preferences.device_tokens:
            preferences.device_tokens.append(device_token)
            preferences.updated_at = datetime.utcnow()
            await self.store.save_preferences(preferences)

        return preferences

    async def unregister_device(
        self,
        user_id: str,
        device_token: str,
    ) -> NotificationPreferences:
        """Unregister a device token."""
        preferences = await self.get_preferences(user_id)

        if device_token in preferences.device_tokens:
            preferences.device_tokens.remove(device_token)
            preferences.updated_at = datetime.utcnow()
            await self.store.save_preferences(preferences)

        return preferences

    # Background processing
    async def process_pending_notifications(self, limit: int = 100) -> int:
        """Process pending notifications."""
        notifications = await self.store.get_pending_notifications(limit=limit)
        processed = 0

        for notification in notifications:
            try:
                provider = self.get_provider(notification.notification_type)
                if provider:
                    await self._deliver_notification(notification, provider)
                    processed += 1
            except Exception as e:
                logger.error(f"Failed to process notification {notification.notification_id}: {e}")

        return processed

    async def start_background_processor(
        self,
        interval_seconds: int = 60,
    ) -> None:
        """Start the background notification processor."""
        async def processor():
            while True:
                try:
                    await self.process_pending_notifications()
                except Exception as e:
                    logger.error(f"Background processor error: {e}")
                await asyncio.sleep(interval_seconds)

        self._processor_task = asyncio.create_task(processor())
        logger.info("Started background notification processor")

    async def stop_background_processor(self) -> None:
        """Stop the background processor."""
        if self._processor_task:
            self._processor_task.cancel()
            try:
                await self._processor_task
            except asyncio.CancelledError:
                pass
            self._processor_task = None
            logger.info("Stopped background notification processor")

    # Statistics
    async def get_stats(
        self,
        user_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        days: int = 30,
    ) -> NotificationStats:
        """Get notification statistics."""
        stats = NotificationStats(
            period_start=datetime.utcnow() - timedelta(days=days),
            period_end=datetime.utcnow(),
        )

        # Get notifications
        if user_id:
            notifications = await self.store.get_notifications_by_user(user_id)
        else:
            notifications = list(self.store._notifications.values())

        # Filter by tenant if specified
        if tenant_id:
            notifications = [n for n in notifications if n.tenant_id == tenant_id]

        # Filter by date
        cutoff = datetime.utcnow() - timedelta(days=days)
        notifications = [n for n in notifications if n.created_at >= cutoff]

        # Calculate stats
        for notification in notifications:
            if notification.status in (NotificationStatus.SENT, NotificationStatus.DELIVERED, NotificationStatus.READ):
                stats.total_sent += 1

            if notification.status == NotificationStatus.DELIVERED:
                stats.total_delivered += 1

            if notification.status == NotificationStatus.FAILED:
                stats.total_failed += 1

            if notification.status == NotificationStatus.READ:
                stats.total_read += 1

            # By type
            type_key = notification.notification_type.value
            stats.by_type[type_key] = stats.by_type.get(type_key, 0) + 1

            # By category
            cat_key = notification.category.value
            stats.by_category[cat_key] = stats.by_category.get(cat_key, 0) + 1

        # Calculate rates
        if stats.total_sent > 0:
            stats.delivery_rate = stats.total_delivered / stats.total_sent
            stats.read_rate = stats.total_read / stats.total_sent

        return stats

    # Cleanup
    async def cleanup_old_notifications(self, days: int = 30) -> int:
        """Clean up old notifications."""
        count = await self.store.cleanup_old_notifications(days)
        logger.info(f"Cleaned up {count} old notifications")
        return count

    # Event handling
    def subscribe(
        self,
        event_type: str,
        handler: Callable,
    ) -> None:
        """Subscribe to notification events."""
        if event_type not in self._event_handlers:
            self._event_handlers[event_type] = []
        self._event_handlers[event_type].append(handler)

    async def _emit_event(
        self,
        event_type: str,
        data: Dict[str, Any],
    ) -> None:
        """Emit an event to subscribers."""
        handlers = self._event_handlers.get(event_type, [])
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event_type, data)
                else:
                    handler(event_type, data)
            except Exception as e:
                logger.error(f"Event handler error: {e}")
