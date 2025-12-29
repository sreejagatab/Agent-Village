"""
Tests for the Notification System.

Tests cover:
- Notification models and enums
- Notification templates
- User preferences
- Notification service
- Provider system
- FastAPI routes
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.notifications.models import (
    NotificationType,
    NotificationStatus,
    NotificationPriority,
    NotificationCategory,
    ChannelType,
    NotificationRecipient,
    NotificationContent,
    DeliveryAttempt,
    Notification,
    NotificationTemplate,
    NotificationPreferences,
    ChannelPreference,
    CategoryPreference,
    ChannelConfig,
    NotificationConfig,
)
from src.notifications.service import (
    NotificationStore,
    NotificationService,
    NotificationNotFoundError,
    TemplateNotFoundError,
    RateLimitExceededError,
    PreferencesBlockedError,
)
from src.notifications.providers.base import (
    NotificationProvider,
    ProviderResult,
    ProviderError,
    ProviderValidationError,
)
from src.notifications.providers.inapp import InAppProvider
from src.notifications.middleware import (
    create_notification_routes,
    create_notification_send_routes,
    create_notification_admin_routes,
)


# ============================================================================
# Model Tests
# ============================================================================

class TestNotificationType:
    """Tests for NotificationType enum."""

    def test_notification_types(self):
        """Test notification type values."""
        assert NotificationType.EMAIL.value == "email"
        assert NotificationType.SMS.value == "sms"
        assert NotificationType.PUSH.value == "push"
        assert NotificationType.IN_APP.value == "in_app"


class TestNotificationStatus:
    """Tests for NotificationStatus enum."""

    def test_status_values(self):
        """Test status values."""
        assert NotificationStatus.PENDING.value == "pending"
        assert NotificationStatus.SENT.value == "sent"
        assert NotificationStatus.DELIVERED.value == "delivered"
        assert NotificationStatus.FAILED.value == "failed"
        assert NotificationStatus.READ.value == "read"


class TestNotificationPriority:
    """Tests for NotificationPriority enum."""

    def test_priority_values(self):
        """Test priority values."""
        assert NotificationPriority.LOW.value == "low"
        assert NotificationPriority.NORMAL.value == "normal"
        assert NotificationPriority.HIGH.value == "high"
        assert NotificationPriority.URGENT.value == "urgent"


class TestNotificationRecipient:
    """Tests for NotificationRecipient."""

    def test_create_recipient(self):
        """Test creating a recipient."""
        recipient = NotificationRecipient(
            user_id="user123",
            email="user@example.com",
            phone="+1234567890",
            device_tokens=["token1", "token2"],
            name="John Doe",
        )

        assert recipient.user_id == "user123"
        assert recipient.email == "user@example.com"
        assert recipient.phone == "+1234567890"
        assert len(recipient.device_tokens) == 2
        assert recipient.name == "John Doe"

    def test_recipient_to_dict(self):
        """Test converting recipient to dict."""
        recipient = NotificationRecipient(
            user_id="user123",
            email="user@example.com",
        )

        data = recipient.to_dict()
        assert data["user_id"] == "user123"
        assert data["email"] == "user@example.com"


class TestNotificationContent:
    """Tests for NotificationContent."""

    def test_create_content(self):
        """Test creating notification content."""
        content = NotificationContent(
            subject="Test Subject",
            title="Test Title",
            body="Test body message",
            html_body="<p>Test body</p>",
            action_url="https://example.com",
        )

        assert content.subject == "Test Subject"
        assert content.title == "Test Title"
        assert content.body == "Test body message"
        assert content.html_body == "<p>Test body</p>"

    def test_get_sms_body_short(self):
        """Test SMS body under limit."""
        content = NotificationContent(body="Short message")
        assert content.get_sms_body() == "Short message"

    def test_get_sms_body_truncated(self):
        """Test SMS body truncation."""
        long_body = "A" * 200
        content = NotificationContent(body=long_body)
        sms_body = content.get_sms_body()

        assert len(sms_body) == 160
        assert sms_body.endswith("...")

    def test_get_sms_body_prefers_short(self):
        """Test SMS body uses short_body when available."""
        content = NotificationContent(
            body="Long body message here",
            short_body="Short",
        )
        assert content.get_sms_body() == "Short"


class TestDeliveryAttempt:
    """Tests for DeliveryAttempt."""

    def test_create_attempt(self):
        """Test creating a delivery attempt."""
        attempt = DeliveryAttempt(
            attempt_number=1,
            channel_type=ChannelType.SMTP,
        )

        assert attempt.attempt_number == 1
        assert attempt.channel_type == ChannelType.SMTP
        assert not attempt.success
        assert attempt.completed_at is None

    def test_complete_success(self):
        """Test completing a successful attempt."""
        attempt = DeliveryAttempt()
        attempt.complete(
            success=True,
            provider_message_id="msg_123",
        )

        assert attempt.success
        assert attempt.completed_at is not None
        assert attempt.provider_message_id == "msg_123"
        assert attempt.duration_ms is not None

    def test_complete_failure(self):
        """Test completing a failed attempt."""
        attempt = DeliveryAttempt()
        attempt.complete(
            success=False,
            error_code="SEND_ERROR",
            error_message="Connection failed",
        )

        assert not attempt.success
        assert attempt.error_code == "SEND_ERROR"
        assert attempt.error_message == "Connection failed"


class TestNotification:
    """Tests for Notification."""

    def test_create_notification(self):
        """Test creating a notification."""
        recipient = NotificationRecipient(user_id="user123")
        content = NotificationContent(title="Test", body="Body")

        notification = Notification(
            notification_type=NotificationType.IN_APP,
            recipient=recipient,
            content=content,
        )

        assert notification.notification_id.startswith("ntf_")
        assert notification.notification_type == NotificationType.IN_APP
        assert notification.status == NotificationStatus.PENDING

    def test_create_email(self):
        """Test factory method for email."""
        recipient = NotificationRecipient(
            user_id="user123",
            email="user@example.com",
        )

        notification = Notification.create_email(
            recipient=recipient,
            subject="Welcome",
            body="Welcome to our service!",
            html_body="<h1>Welcome!</h1>",
        )

        assert notification.notification_type == NotificationType.EMAIL
        assert notification.content.subject == "Welcome"

    def test_create_sms(self):
        """Test factory method for SMS."""
        recipient = NotificationRecipient(
            user_id="user123",
            phone="+1234567890",
        )

        notification = Notification.create_sms(
            recipient=recipient,
            body="Your code is 123456",
        )

        assert notification.notification_type == NotificationType.SMS
        assert notification.content.body == "Your code is 123456"

    def test_create_push(self):
        """Test factory method for push notification."""
        recipient = NotificationRecipient(
            user_id="user123",
            device_tokens=["token1"],
        )

        notification = Notification.create_push(
            recipient=recipient,
            title="New Message",
            body="You have a new message",
            data={"message_id": "msg123"},
        )

        assert notification.notification_type == NotificationType.PUSH
        assert notification.content.title == "New Message"
        assert notification.content.data["message_id"] == "msg123"

    def test_add_successful_attempt(self):
        """Test adding a successful delivery attempt."""
        notification = Notification(
            notification_type=NotificationType.IN_APP,
            recipient=NotificationRecipient(user_id="user123"),
            content=NotificationContent(body="Test"),
        )

        attempt = DeliveryAttempt()
        attempt.complete(success=True)
        notification.add_attempt(attempt)

        assert notification.status == NotificationStatus.SENT
        assert notification.attempt_count == 1
        assert notification.sent_at is not None

    def test_add_failed_attempt_with_retry(self):
        """Test adding a failed attempt when retries available."""
        notification = Notification(
            notification_type=NotificationType.IN_APP,
            recipient=NotificationRecipient(user_id="user123"),
            content=NotificationContent(body="Test"),
            max_attempts=3,
        )

        attempt = DeliveryAttempt()
        attempt.complete(success=False, error_code="ERROR")
        notification.add_attempt(attempt)

        assert notification.status == NotificationStatus.PENDING
        assert notification.can_retry

    def test_add_failed_attempt_exhausted(self):
        """Test adding a failed attempt when retries exhausted."""
        notification = Notification(
            notification_type=NotificationType.IN_APP,
            recipient=NotificationRecipient(user_id="user123"),
            content=NotificationContent(body="Test"),
            max_attempts=1,
        )

        attempt = DeliveryAttempt()
        attempt.complete(success=False, error_code="ERROR")
        notification.add_attempt(attempt)

        assert notification.status == NotificationStatus.FAILED
        assert not notification.can_retry

    def test_mark_delivered(self):
        """Test marking notification as delivered."""
        notification = Notification(
            notification_type=NotificationType.IN_APP,
            recipient=NotificationRecipient(user_id="user123"),
            content=NotificationContent(body="Test"),
        )

        notification.mark_delivered()

        assert notification.status == NotificationStatus.DELIVERED
        assert notification.delivered_at is not None

    def test_mark_read(self):
        """Test marking notification as read."""
        notification = Notification(
            notification_type=NotificationType.IN_APP,
            recipient=NotificationRecipient(user_id="user123"),
            content=NotificationContent(body="Test"),
        )

        notification.mark_read()

        assert notification.status == NotificationStatus.READ
        assert notification.read_at is not None

    def test_cancel_pending(self):
        """Test cancelling a pending notification."""
        notification = Notification(
            notification_type=NotificationType.IN_APP,
            recipient=NotificationRecipient(user_id="user123"),
            content=NotificationContent(body="Test"),
        )

        result = notification.cancel()

        assert result is True
        assert notification.status == NotificationStatus.CANCELLED

    def test_cancel_sent_fails(self):
        """Test cancelling a sent notification fails."""
        notification = Notification(
            notification_type=NotificationType.IN_APP,
            recipient=NotificationRecipient(user_id="user123"),
            content=NotificationContent(body="Test"),
            status=NotificationStatus.SENT,
        )

        result = notification.cancel()

        assert result is False
        assert notification.status == NotificationStatus.SENT

    def test_is_scheduled(self):
        """Test scheduled notification check."""
        notification = Notification(
            notification_type=NotificationType.IN_APP,
            recipient=NotificationRecipient(user_id="user123"),
            content=NotificationContent(body="Test"),
            scheduled_at=datetime.utcnow() + timedelta(hours=1),
        )

        assert notification.is_scheduled

    def test_is_expired(self):
        """Test expired notification check."""
        notification = Notification(
            notification_type=NotificationType.IN_APP,
            recipient=NotificationRecipient(user_id="user123"),
            content=NotificationContent(body="Test"),
            expires_at=datetime.utcnow() - timedelta(hours=1),
        )

        assert notification.is_expired


class TestNotificationTemplate:
    """Tests for NotificationTemplate."""

    def test_create_template(self):
        """Test creating a template."""
        template = NotificationTemplate(
            name="Welcome Email",
            notification_type=NotificationType.EMAIL,
            subject_template="Welcome, {{name}}!",
            body_template="Hello {{name}}, welcome to {{service}}!",
        )

        assert template.template_id.startswith("tpl_")
        assert template.name == "Welcome Email"
        assert template.notification_type == NotificationType.EMAIL

    def test_render_template(self):
        """Test rendering a template with data."""
        template = NotificationTemplate(
            name="Welcome",
            notification_type=NotificationType.EMAIL,
            subject_template="Welcome, {{name}}!",
            body_template="Hello {{name}}, welcome to {{service}}!",
        )

        content = template.render({
            "name": "John",
            "service": "Agent Village",
        })

        assert content.subject == "Welcome, John!"
        assert content.body == "Hello John, welcome to Agent Village!"


class TestNotificationPreferences:
    """Tests for NotificationPreferences."""

    def test_create_preferences(self):
        """Test creating preferences."""
        preferences = NotificationPreferences(
            user_id="user123",
            email="user@example.com",
            phone="+1234567890",
        )

        assert preferences.user_id == "user123"
        assert preferences.notifications_enabled
        assert len(preferences.channel_preferences) == 4

    def test_is_channel_enabled(self):
        """Test checking if channel is enabled."""
        preferences = NotificationPreferences(user_id="user123")

        assert preferences.is_channel_enabled(NotificationType.EMAIL)

        # Disable email
        preferences.channel_preferences[NotificationType.EMAIL].enabled = False
        assert not preferences.is_channel_enabled(NotificationType.EMAIL)

    def test_is_category_enabled(self):
        """Test checking if category is enabled."""
        preferences = NotificationPreferences(user_id="user123")

        # By default, all categories are enabled
        assert preferences.is_category_enabled(NotificationCategory.SYSTEM)

        # Disable a category
        preferences.category_preferences[NotificationCategory.MARKETING] = CategoryPreference(
            category=NotificationCategory.MARKETING,
            enabled=False,
        )
        assert not preferences.is_category_enabled(NotificationCategory.MARKETING)

    def test_should_send_respects_global(self):
        """Test should_send respects global setting."""
        preferences = NotificationPreferences(
            user_id="user123",
            notifications_enabled=False,
        )

        assert not preferences.should_send(
            NotificationType.EMAIL,
            NotificationCategory.SYSTEM,
        )

    def test_should_send_urgent_bypasses_most(self):
        """Test urgent priority bypasses most preferences."""
        preferences = NotificationPreferences(
            user_id="user123",
            notifications_enabled=True,
        )
        preferences.channel_preferences[NotificationType.EMAIL].enabled = False

        # Normal priority blocked
        assert not preferences.should_send(
            NotificationType.EMAIL,
            NotificationCategory.SYSTEM,
            NotificationPriority.NORMAL,
        )

        # Urgent bypasses channel preference
        assert preferences.should_send(
            NotificationType.EMAIL,
            NotificationCategory.SYSTEM,
            NotificationPriority.URGENT,
        )


# ============================================================================
# Store Tests
# ============================================================================

class TestNotificationStore:
    """Tests for NotificationStore."""

    @pytest.fixture
    def store(self):
        """Create a test store."""
        return NotificationStore()

    @pytest.fixture
    def sample_notification(self):
        """Create a sample notification."""
        return Notification(
            notification_type=NotificationType.IN_APP,
            recipient=NotificationRecipient(user_id="user123"),
            content=NotificationContent(title="Test", body="Body"),
        )

    @pytest.mark.asyncio
    async def test_save_and_get_notification(self, store, sample_notification):
        """Test saving and retrieving a notification."""
        await store.save_notification(sample_notification)

        retrieved = await store.get_notification(sample_notification.notification_id)

        assert retrieved is not None
        assert retrieved.notification_id == sample_notification.notification_id

    @pytest.mark.asyncio
    async def test_get_notifications_by_user(self, store):
        """Test getting notifications by user."""
        # Create notifications for two users
        n1 = Notification(
            notification_type=NotificationType.IN_APP,
            recipient=NotificationRecipient(user_id="user123"),
            content=NotificationContent(body="Test 1"),
        )
        n2 = Notification(
            notification_type=NotificationType.IN_APP,
            recipient=NotificationRecipient(user_id="user123"),
            content=NotificationContent(body="Test 2"),
        )
        n3 = Notification(
            notification_type=NotificationType.IN_APP,
            recipient=NotificationRecipient(user_id="user456"),
            content=NotificationContent(body="Test 3"),
        )

        await store.save_notification(n1)
        await store.save_notification(n2)
        await store.save_notification(n3)

        user_notifications = await store.get_notifications_by_user("user123")

        assert len(user_notifications) == 2

    @pytest.mark.asyncio
    async def test_get_pending_notifications(self, store):
        """Test getting pending notifications."""
        n1 = Notification(
            notification_type=NotificationType.IN_APP,
            recipient=NotificationRecipient(user_id="user123"),
            content=NotificationContent(body="Test"),
            status=NotificationStatus.PENDING,
        )
        n2 = Notification(
            notification_type=NotificationType.IN_APP,
            recipient=NotificationRecipient(user_id="user123"),
            content=NotificationContent(body="Test"),
            status=NotificationStatus.SENT,
        )

        await store.save_notification(n1)
        await store.save_notification(n2)

        pending = await store.get_pending_notifications()

        assert len(pending) == 1
        assert pending[0].notification_id == n1.notification_id

    @pytest.mark.asyncio
    async def test_delete_notification(self, store, sample_notification):
        """Test deleting a notification."""
        await store.save_notification(sample_notification)

        deleted = await store.delete_notification(sample_notification.notification_id)

        assert deleted
        assert await store.get_notification(sample_notification.notification_id) is None

    @pytest.mark.asyncio
    async def test_count_unread(self, store):
        """Test counting unread notifications."""
        for i in range(5):
            n = Notification(
                notification_type=NotificationType.IN_APP,
                recipient=NotificationRecipient(user_id="user123"),
                content=NotificationContent(body=f"Test {i}"),
            )
            if i < 2:
                n.mark_read()
            await store.save_notification(n)

        unread = await store.count_unread("user123")
        assert unread == 3

    @pytest.mark.asyncio
    async def test_template_operations(self, store):
        """Test template CRUD operations."""
        template = NotificationTemplate(
            name="Test Template",
            notification_type=NotificationType.EMAIL,
            body_template="Hello {{name}}",
        )

        await store.save_template(template)

        retrieved = await store.get_template(template.template_id)
        assert retrieved is not None
        assert retrieved.name == "Test Template"

        templates = await store.get_templates(NotificationType.EMAIL)
        assert len(templates) == 1

        deleted = await store.delete_template(template.template_id)
        assert deleted

    @pytest.mark.asyncio
    async def test_preferences_operations(self, store):
        """Test preferences CRUD operations."""
        preferences = NotificationPreferences(
            user_id="user123",
            email="user@example.com",
        )

        await store.save_preferences(preferences)

        retrieved = await store.get_preferences("user123")
        assert retrieved is not None
        assert retrieved.email == "user@example.com"

        deleted = await store.delete_preferences("user123")
        assert deleted

    @pytest.mark.asyncio
    async def test_rate_limiting(self, store):
        """Test rate limit checking."""
        # Within limits
        assert await store.check_rate_limit("user123", 10, 100)

        # Increment
        for _ in range(10):
            await store.increment_rate_limit("user123")

        # Now at limit
        assert not await store.check_rate_limit("user123", 10, 100)


# ============================================================================
# Service Tests
# ============================================================================

class TestNotificationService:
    """Tests for NotificationService."""

    @pytest.fixture
    def store(self):
        """Create a test store."""
        return NotificationStore()

    @pytest.fixture
    def service(self, store):
        """Create a test service."""
        svc = NotificationService(store)
        # Register in-app provider
        svc.register_provider(InAppProvider())
        return svc

    @pytest.fixture
    def sample_notification(self):
        """Create a sample notification."""
        return Notification(
            notification_type=NotificationType.IN_APP,
            recipient=NotificationRecipient(user_id="user123"),
            content=NotificationContent(title="Test", body="Body"),
        )

    @pytest.mark.asyncio
    async def test_send_notification(self, service, sample_notification):
        """Test sending a notification."""
        result = await service.send_notification(sample_notification)

        assert result.status == NotificationStatus.SENT
        assert result.attempt_count == 1

    @pytest.mark.asyncio
    async def test_send_notification_respects_preferences(self, service):
        """Test that sending respects user preferences."""
        # Set up preferences that block notifications
        preferences = NotificationPreferences(
            user_id="user123",
            notifications_enabled=False,
        )
        await service.store.save_preferences(preferences)

        notification = Notification(
            notification_type=NotificationType.IN_APP,
            recipient=NotificationRecipient(user_id="user123"),
            content=NotificationContent(body="Test"),
        )

        with pytest.raises(PreferencesBlockedError):
            await service.send_notification(notification)

    @pytest.mark.asyncio
    async def test_send_to_user(self, service):
        """Test sending notification to a user by ID."""
        # Set up user preferences with contact info
        preferences = NotificationPreferences(
            user_id="user123",
            email="user@example.com",
        )
        await service.store.save_preferences(preferences)

        notification = await service.send_to_user(
            user_id="user123",
            notification_type=NotificationType.IN_APP,
            content=NotificationContent(title="Hello", body="World"),
        )

        assert notification.status == NotificationStatus.SENT

    @pytest.mark.asyncio
    async def test_send_from_template(self, service):
        """Test sending notification from a template."""
        # Create template
        template = await service.create_template(
            name="Welcome",
            notification_type=NotificationType.IN_APP,
            body_template="Welcome, {{name}}!",
            title_template="Hello {{name}}",
        )

        recipient = NotificationRecipient(user_id="user123")

        notification = await service.send_from_template(
            template_id=template.template_id,
            recipient=recipient,
            data={"name": "John"},
        )

        assert notification.status == NotificationStatus.SENT
        assert notification.content.body == "Welcome, John!"

    @pytest.mark.asyncio
    async def test_send_from_template_not_found(self, service):
        """Test error when template not found."""
        recipient = NotificationRecipient(user_id="user123")

        with pytest.raises(TemplateNotFoundError):
            await service.send_from_template(
                template_id="nonexistent",
                recipient=recipient,
                data={},
            )

    @pytest.mark.asyncio
    async def test_get_user_notifications(self, service):
        """Test getting user notifications."""
        # Send some notifications
        for i in range(5):
            n = Notification(
                notification_type=NotificationType.IN_APP,
                recipient=NotificationRecipient(user_id="user123"),
                content=NotificationContent(body=f"Test {i}"),
            )
            await service.send_notification(n)

        result = await service.get_user_notifications(
            user_id="user123",
            limit=3,
        )

        assert len(result.notifications) == 3
        assert result.total == 5

    @pytest.mark.asyncio
    async def test_mark_as_read(self, service, sample_notification):
        """Test marking a notification as read."""
        await service.send_notification(sample_notification)

        result = await service.mark_as_read(
            sample_notification.notification_id,
            user_id="user123",
        )

        assert result.status == NotificationStatus.READ

    @pytest.mark.asyncio
    async def test_mark_all_as_read(self, service):
        """Test marking all notifications as read."""
        for i in range(3):
            n = Notification(
                notification_type=NotificationType.IN_APP,
                recipient=NotificationRecipient(user_id="user123"),
                content=NotificationContent(body=f"Test {i}"),
            )
            await service.send_notification(n)

        count = await service.mark_all_as_read("user123")

        assert count == 3

    @pytest.mark.asyncio
    async def test_cancel_notification(self, service):
        """Test cancelling a notification."""
        notification = Notification(
            notification_type=NotificationType.IN_APP,
            recipient=NotificationRecipient(user_id="user123"),
            content=NotificationContent(body="Test"),
            scheduled_at=datetime.utcnow() + timedelta(hours=1),
        )
        await service.store.save_notification(notification)

        result = await service.cancel_notification(notification.notification_id)

        assert result.status == NotificationStatus.CANCELLED

    @pytest.mark.asyncio
    async def test_template_crud(self, service):
        """Test template CRUD operations."""
        # Create
        template = await service.create_template(
            name="Test",
            notification_type=NotificationType.EMAIL,
            body_template="Hello",
            subject_template="Subject",
        )
        assert template.template_id is not None

        # Read
        retrieved = await service.get_template(template.template_id)
        assert retrieved.name == "Test"

        # Update
        updated = await service.update_template(
            template.template_id,
            name="Updated Name",
        )
        assert updated.name == "Updated Name"
        assert updated.version == 2

        # List
        templates = await service.list_templates()
        assert len(templates) == 1

        # Delete
        deleted = await service.delete_template(template.template_id)
        assert deleted

    @pytest.mark.asyncio
    async def test_preferences_management(self, service):
        """Test preferences management."""
        # Get (creates default)
        preferences = await service.get_preferences("user123")
        assert preferences.notifications_enabled

        # Update
        updated = await service.update_preferences(
            "user123",
            notifications_enabled=False,
            email="new@example.com",
        )
        assert not updated.notifications_enabled
        assert updated.email == "new@example.com"

    @pytest.mark.asyncio
    async def test_device_registration(self, service):
        """Test device token registration."""
        # Register
        prefs = await service.register_device("user123", "device_token_1")
        assert "device_token_1" in prefs.device_tokens

        # Register another
        prefs = await service.register_device("user123", "device_token_2")
        assert len(prefs.device_tokens) == 2

        # Unregister
        prefs = await service.unregister_device("user123", "device_token_1")
        assert len(prefs.device_tokens) == 1
        assert "device_token_1" not in prefs.device_tokens

    @pytest.mark.asyncio
    async def test_get_stats(self, service):
        """Test getting notification statistics."""
        # Send some notifications
        for i in range(5):
            n = Notification(
                notification_type=NotificationType.IN_APP,
                recipient=NotificationRecipient(user_id="user123"),
                content=NotificationContent(body=f"Test {i}"),
            )
            await service.send_notification(n)

        stats = await service.get_stats(user_id="user123")

        assert stats.total_sent == 5
        assert stats.by_type.get("in_app") == 5

    @pytest.mark.asyncio
    async def test_cleanup_old_notifications(self, service):
        """Test cleaning up old notifications."""
        # Create old notification
        old_notification = Notification(
            notification_type=NotificationType.IN_APP,
            recipient=NotificationRecipient(user_id="user123"),
            content=NotificationContent(body="Old"),
        )
        old_notification.created_at = datetime.utcnow() - timedelta(days=60)
        await service.store.save_notification(old_notification)

        # Create recent notification
        recent = Notification(
            notification_type=NotificationType.IN_APP,
            recipient=NotificationRecipient(user_id="user123"),
            content=NotificationContent(body="Recent"),
        )
        await service.store.save_notification(recent)

        count = await service.cleanup_old_notifications(days=30)

        assert count == 1

    @pytest.mark.asyncio
    async def test_rate_limiting(self, service):
        """Test rate limiting."""
        # Set low limits
        service.config.max_notifications_per_user_per_hour = 2

        # Send up to limit
        for i in range(2):
            n = Notification(
                notification_type=NotificationType.IN_APP,
                recipient=NotificationRecipient(user_id="user123"),
                content=NotificationContent(body=f"Test {i}"),
            )
            await service.send_notification(n)

        # Next should fail
        n = Notification(
            notification_type=NotificationType.IN_APP,
            recipient=NotificationRecipient(user_id="user123"),
            content=NotificationContent(body="Over limit"),
        )

        with pytest.raises(RateLimitExceededError):
            await service.send_notification(n)


# ============================================================================
# Provider Tests
# ============================================================================

class TestInAppProvider:
    """Tests for InAppProvider."""

    @pytest.fixture
    def provider(self):
        """Create a test provider."""
        return InAppProvider()

    @pytest.mark.asyncio
    async def test_send_success(self, provider):
        """Test successful in-app send."""
        notification = Notification(
            notification_type=NotificationType.IN_APP,
            recipient=NotificationRecipient(user_id="user123"),
            content=NotificationContent(title="Test", body="Body"),
        )

        result = await provider.send(notification)

        assert result.success
        assert result.provider_message_id == notification.notification_id

    @pytest.mark.asyncio
    async def test_validation_error(self, provider):
        """Test validation error for missing user_id."""
        notification = Notification(
            notification_type=NotificationType.IN_APP,
            recipient=NotificationRecipient(user_id=""),
            content=NotificationContent(body="Test"),
        )

        with pytest.raises(ProviderValidationError):
            await provider.send(notification)


# ============================================================================
# Route Tests
# ============================================================================

class TestNotificationRoutes:
    """Tests for notification routes."""

    @pytest.fixture
    def app(self):
        """Create a test app."""
        from fastapi import FastAPI

        store = NotificationStore()
        service = NotificationService(store)
        service.register_provider(InAppProvider())

        app = FastAPI()
        app.include_router(
            create_notification_routes(service),
            prefix="/notifications",
        )
        app.include_router(
            create_notification_send_routes(service),
            prefix="/notifications",
        )
        app.include_router(
            create_notification_admin_routes(service),
            prefix="/admin/notifications",
        )

        # Add mock auth
        @app.middleware("http")
        async def add_user(request, call_next):
            request.state.user_id = "user123"
            return await call_next(request)

        return app

    @pytest.fixture
    def client(self, app):
        """Create a test client."""
        return TestClient(app)

    def test_list_notifications(self, client):
        """Test listing notifications."""
        response = client.get("/notifications")

        assert response.status_code == 200
        data = response.json()
        assert "notifications" in data
        assert "total" in data

    def test_send_notification(self, client):
        """Test sending a notification."""
        response = client.post("/notifications/send", json={
            "notification_type": "in_app",
            "recipient": {
                "user_id": "user123",
            },
            "content": {
                "title": "Test",
                "body": "Test body",
            },
        })

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "sent"

    def test_get_preferences(self, client):
        """Test getting preferences."""
        response = client.get("/notifications/preferences")

        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == "user123"

    def test_update_preferences(self, client):
        """Test updating preferences."""
        response = client.put("/notifications/preferences", json={
            "notifications_enabled": False,
            "email": "new@example.com",
        })

        assert response.status_code == 200
        data = response.json()
        assert data["notifications_enabled"] is False
        assert data["email"] == "new@example.com"

    def test_register_device(self, client):
        """Test registering a device."""
        response = client.post("/notifications/devices", json={
            "device_token": "test_token_123",
        })

        assert response.status_code == 200
        data = response.json()
        assert data["registered"] is True

    def test_mark_as_read(self, client):
        """Test marking notification as read."""
        # First send a notification
        send_response = client.post("/notifications/send", json={
            "notification_type": "in_app",
            "recipient": {"user_id": "user123"},
            "content": {"body": "Test"},
        })
        notification_id = send_response.json()["notification_id"]

        # Mark as read
        response = client.post(f"/notifications/{notification_id}/read")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "read"

    def test_mark_all_as_read(self, client):
        """Test marking all as read."""
        # Send some notifications
        for i in range(3):
            client.post("/notifications/send", json={
                "notification_type": "in_app",
                "recipient": {"user_id": "user123"},
                "content": {"body": f"Test {i}"},
            })

        response = client.post("/notifications/read-all")

        assert response.status_code == 200
        data = response.json()
        assert data["marked_as_read"] == 3

    def test_get_unread_count(self, client):
        """Test getting unread count."""
        response = client.get("/notifications/unread/count")

        assert response.status_code == 200
        data = response.json()
        assert "unread_count" in data


class TestNotificationAdminRoutes:
    """Tests for admin routes."""

    @pytest.fixture
    def app(self):
        """Create a test app."""
        from fastapi import FastAPI

        store = NotificationStore()
        service = NotificationService(store)
        service.register_provider(InAppProvider())

        app = FastAPI()
        app.include_router(
            create_notification_admin_routes(service),
            prefix="/admin/notifications",
        )

        return app

    @pytest.fixture
    def client(self, app):
        """Create a test client."""
        return TestClient(app)

    def test_create_template(self, client):
        """Test creating a template."""
        response = client.post("/admin/notifications/templates", json={
            "name": "Welcome Email",
            "notification_type": "email",
            "body_template": "Hello {{name}}!",
            "subject_template": "Welcome",
        })

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Welcome Email"
        assert data["template_id"].startswith("tpl_")

    def test_list_templates(self, client):
        """Test listing templates."""
        # Create a template first
        client.post("/admin/notifications/templates", json={
            "name": "Test",
            "notification_type": "in_app",
            "body_template": "Test",
        })

        response = client.get("/admin/notifications/templates")

        assert response.status_code == 200
        data = response.json()
        assert "templates" in data
        assert len(data["templates"]) >= 1

    def test_get_stats(self, client):
        """Test getting stats."""
        response = client.get("/admin/notifications/stats")

        assert response.status_code == 200
        data = response.json()
        assert "total_sent" in data
        assert "delivery_rate" in data

    def test_cleanup(self, client):
        """Test cleanup endpoint."""
        response = client.post("/admin/notifications/cleanup?days=30")

        assert response.status_code == 200
        data = response.json()
        assert "deleted" in data


# ============================================================================
# Integration Tests
# ============================================================================

class TestNotificationIntegration:
    """Integration tests for the notification system."""

    @pytest.mark.asyncio
    async def test_full_notification_lifecycle(self):
        """Test full notification lifecycle."""
        store = NotificationStore()
        service = NotificationService(store)
        service.register_provider(InAppProvider())

        # Set up user preferences
        await service.update_preferences(
            "user123",
            email="user@example.com",
        )

        # Create a template
        template = await service.create_template(
            name="Welcome",
            notification_type=NotificationType.IN_APP,
            title_template="Welcome {{name}}",
            body_template="Hello {{name}}, you have {{count}} new messages!",
        )

        # Send from template
        notification = await service.send_from_template(
            template_id=template.template_id,
            recipient=NotificationRecipient(user_id="user123"),
            data={"name": "John", "count": "5"},
        )

        assert notification.status == NotificationStatus.SENT
        assert notification.content.title == "Welcome John"
        assert "5 new messages" in notification.content.body

        # Get user notifications
        result = await service.get_user_notifications("user123")
        assert result.total == 1
        assert result.unread_count == 1

        # Mark as read
        await service.mark_as_read(notification.notification_id)

        # Check unread count
        result = await service.get_user_notifications("user123")
        assert result.unread_count == 0

    @pytest.mark.asyncio
    async def test_multi_channel_notification(self):
        """Test sending to multiple channels."""
        store = NotificationStore()
        service = NotificationService(store)
        service.register_provider(InAppProvider())

        recipient = NotificationRecipient(
            user_id="user123",
            email="user@example.com",
            phone="+1234567890",
            device_tokens=["token1"],
        )

        # Send in-app (only registered provider)
        notification = Notification.create_in_app(
            recipient=recipient,
            title="Multi-channel",
            body="This is a test",
        )
        result = await service.send_notification(notification)

        assert result.status == NotificationStatus.SENT

    @pytest.mark.asyncio
    async def test_preference_blocking(self):
        """Test that preferences correctly block notifications."""
        store = NotificationStore()
        service = NotificationService(store)
        service.register_provider(InAppProvider())

        # Disable marketing category
        preferences = await service.get_preferences("user123")
        preferences.category_preferences[NotificationCategory.MARKETING] = CategoryPreference(
            category=NotificationCategory.MARKETING,
            enabled=False,
        )
        await service.store.save_preferences(preferences)

        # Try to send marketing notification
        notification = Notification(
            notification_type=NotificationType.IN_APP,
            category=NotificationCategory.MARKETING,
            recipient=NotificationRecipient(user_id="user123"),
            content=NotificationContent(body="Buy now!"),
        )

        with pytest.raises(PreferencesBlockedError):
            await service.send_notification(notification)

        # System notifications should still work
        system_notification = Notification(
            notification_type=NotificationType.IN_APP,
            category=NotificationCategory.SYSTEM,
            recipient=NotificationRecipient(user_id="user123"),
            content=NotificationContent(body="System update"),
        )
        result = await service.send_notification(system_notification)
        assert result.status == NotificationStatus.SENT
