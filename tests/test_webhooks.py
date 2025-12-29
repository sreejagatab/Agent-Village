"""
Tests for Webhook System.

Comprehensive tests covering:
- Webhook models and data structures
- Webhook service operations
- Event publishing and delivery
- Signature verification
- Retry logic
- Routes and middleware
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
import json
import hmac
import hashlib

from src.webhooks.models import (
    WebhookEndpoint,
    WebhookEvent,
    WebhookDelivery,
    DeliveryAttempt,
    WebhookStatus,
    DeliveryStatus,
    EventType,
    EventCategory,
    WebhookConfig,
    WebhookListResponse,
    DeliveryListResponse,
    WebhookTestResult,
)

from src.webhooks.service import (
    WebhookStore,
    WebhookService,
    WebhookNotFoundError,
    WebhookDisabledError,
    WebhookLimitExceededError,
    DeliveryNotFoundError,
)

from src.webhooks.middleware import (
    WebhookCreateRequest,
    WebhookUpdateRequest,
    EventPublishRequest,
    create_webhook_routes,
    create_webhook_admin_routes,
    create_webhook_receiver_routes,
)


# =============================================================================
# Webhook Models Tests
# =============================================================================

class TestWebhookStatus:
    """Test WebhookStatus enum."""

    def test_status_values(self):
        """Test all status values."""
        assert WebhookStatus.ACTIVE == "active"
        assert WebhookStatus.PAUSED == "paused"
        assert WebhookStatus.DISABLED == "disabled"
        assert WebhookStatus.FAILED == "failed"


class TestDeliveryStatus:
    """Test DeliveryStatus enum."""

    def test_delivery_status_values(self):
        """Test all delivery status values."""
        assert DeliveryStatus.PENDING == "pending"
        assert DeliveryStatus.DELIVERED == "delivered"
        assert DeliveryStatus.FAILED == "failed"
        assert DeliveryStatus.RETRYING == "retrying"
        assert DeliveryStatus.EXPIRED == "expired"


class TestEventType:
    """Test EventType enum."""

    def test_goal_events(self):
        """Test goal event types."""
        assert EventType.GOAL_CREATED == "goal.created"
        assert EventType.GOAL_COMPLETED == "goal.completed"
        assert EventType.GOAL_FAILED == "goal.failed"

    def test_agent_events(self):
        """Test agent event types."""
        assert EventType.AGENT_SPAWNED == "agent.spawned"
        assert EventType.AGENT_COMPLETED == "agent.completed"

    def test_wildcard_event(self):
        """Test wildcard event type."""
        assert EventType.ALL == "*"


class TestWebhookEvent:
    """Test WebhookEvent dataclass."""

    def test_create_event(self):
        """Test creating an event."""
        event = WebhookEvent.create(
            event_type=EventType.GOAL_CREATED,
            data={"goal_id": "goal123", "title": "Test Goal"},
            user_id="user123",
        )

        assert event.event_id.startswith("evt_")
        assert event.event_type == EventType.GOAL_CREATED
        assert event.data["goal_id"] == "goal123"
        assert event.user_id == "user123"
        assert event.correlation_id.startswith("cor_")

    def test_event_to_dict(self):
        """Test event to dictionary conversion."""
        event = WebhookEvent.create(
            event_type=EventType.GOAL_CREATED,
            data={"goal_id": "goal123"},
        )

        result = event.to_dict()

        assert "event_id" in result
        assert result["event_type"] == "goal.created"
        assert "timestamp" in result
        assert "data" in result
        assert "metadata" in result

    def test_event_to_json(self):
        """Test event JSON serialization."""
        event = WebhookEvent.create(
            event_type=EventType.GOAL_CREATED,
            data={"goal_id": "goal123"},
        )

        json_str = event.to_json()
        parsed = json.loads(json_str)

        assert parsed["event_type"] == "goal.created"


class TestWebhookEndpoint:
    """Test WebhookEndpoint dataclass."""

    def test_create_endpoint(self):
        """Test creating a webhook endpoint."""
        endpoint, secret = WebhookEndpoint.create(
            url="https://example.com/webhook",
            owner_id="user123",
            name="Test Webhook",
            events=[EventType.GOAL_CREATED, EventType.GOAL_COMPLETED],
        )

        assert endpoint.webhook_id.startswith("whk_")
        assert endpoint.url == "https://example.com/webhook"
        assert endpoint.owner_id == "user123"
        assert endpoint.name == "Test Webhook"
        assert len(endpoint.events) == 2
        assert len(secret) >= 32

    def test_subscribes_to_specific_event(self):
        """Test event subscription check."""
        endpoint, _ = WebhookEndpoint.create(
            url="https://example.com/webhook",
            owner_id="user123",
            events=[EventType.GOAL_CREATED],
        )

        assert endpoint.subscribes_to(EventType.GOAL_CREATED) is True
        assert endpoint.subscribes_to(EventType.GOAL_COMPLETED) is False

    def test_subscribes_to_all_events(self):
        """Test wildcard subscription."""
        endpoint, _ = WebhookEndpoint.create(
            url="https://example.com/webhook",
            owner_id="user123",
            events=[EventType.ALL],
        )

        assert endpoint.subscribes_to(EventType.GOAL_CREATED) is True
        assert endpoint.subscribes_to(EventType.AGENT_SPAWNED) is True

    def test_matches_filters(self):
        """Test event filtering."""
        endpoint, _ = WebhookEndpoint.create(
            url="https://example.com/webhook",
            owner_id="user123",
            filters={"goal_id": "specific_goal"},
        )

        assert endpoint.matches_filters({"goal_id": "specific_goal"}) is True
        assert endpoint.matches_filters({"goal_id": "other_goal"}) is False
        assert endpoint.matches_filters({}) is False

    def test_matches_filters_list(self):
        """Test event filtering with list values."""
        endpoint, _ = WebhookEndpoint.create(
            url="https://example.com/webhook",
            owner_id="user123",
            filters={"status": ["active", "pending"]},
        )

        assert endpoint.matches_filters({"status": "active"}) is True
        assert endpoint.matches_filters({"status": "completed"}) is False

    def test_sign_payload(self):
        """Test payload signing."""
        endpoint, secret = WebhookEndpoint.create(
            url="https://example.com/webhook",
            owner_id="user123",
        )

        payload = '{"event": "test"}'
        timestamp = 1234567890

        signature = endpoint.sign_payload(payload, timestamp)

        assert signature.startswith("t=1234567890,v1=")

    def test_verify_signature(self):
        """Test signature verification."""
        endpoint, secret = WebhookEndpoint.create(
            url="https://example.com/webhook",
            owner_id="user123",
        )

        payload = '{"event": "test"}'
        timestamp = int(datetime.utcnow().timestamp())

        signature = endpoint.sign_payload(payload, timestamp)

        assert endpoint.verify_signature(payload, signature) is True
        assert endpoint.verify_signature("wrong_payload", signature) is False

    def test_verify_signature_expired(self):
        """Test signature verification with expired timestamp."""
        endpoint, secret = WebhookEndpoint.create(
            url="https://example.com/webhook",
            owner_id="user123",
        )

        payload = '{"event": "test"}'
        old_timestamp = int((datetime.utcnow() - timedelta(hours=1)).timestamp())

        signature = endpoint.sign_payload(payload, old_timestamp)

        assert endpoint.verify_signature(payload, signature, tolerance_seconds=300) is False

    def test_record_success(self):
        """Test recording successful delivery."""
        endpoint, _ = WebhookEndpoint.create(
            url="https://example.com/webhook",
            owner_id="user123",
        )

        endpoint.record_success()

        assert endpoint.total_deliveries == 1
        assert endpoint.successful_deliveries == 1
        assert endpoint.consecutive_failures == 0
        assert endpoint.last_triggered_at is not None

    def test_record_failure(self):
        """Test recording failed delivery."""
        endpoint, _ = WebhookEndpoint.create(
            url="https://example.com/webhook",
            owner_id="user123",
        )

        endpoint.record_failure()

        assert endpoint.total_deliveries == 1
        assert endpoint.failed_deliveries == 1
        assert endpoint.consecutive_failures == 1

    def test_auto_disable_on_failures(self):
        """Test auto-disable after too many failures."""
        endpoint, _ = WebhookEndpoint.create(
            url="https://example.com/webhook",
            owner_id="user123",
        )

        for _ in range(50):
            endpoint.record_failure()

        assert endpoint.status == WebhookStatus.FAILED

    def test_failure_rate(self):
        """Test failure rate calculation."""
        endpoint, _ = WebhookEndpoint.create(
            url="https://example.com/webhook",
            owner_id="user123",
        )

        endpoint.record_success()
        endpoint.record_success()
        endpoint.record_failure()
        endpoint.record_failure()

        assert endpoint.failure_rate == 0.5

    def test_to_dict(self):
        """Test endpoint to dictionary conversion."""
        endpoint, _ = WebhookEndpoint.create(
            url="https://example.com/webhook",
            owner_id="user123",
            name="Test Webhook",
        )

        result = endpoint.to_dict()

        assert result["webhook_id"] == endpoint.webhook_id
        assert result["url"] == "https://example.com/webhook"
        assert result["name"] == "Test Webhook"
        assert "secret" not in result

    def test_to_dict_include_secret(self):
        """Test endpoint to dictionary with secret."""
        endpoint, secret = WebhookEndpoint.create(
            url="https://example.com/webhook",
            owner_id="user123",
        )

        result = endpoint.to_dict(include_secret=True)

        assert result["secret"] == secret


class TestDeliveryAttempt:
    """Test DeliveryAttempt dataclass."""

    def test_complete_success(self):
        """Test completing a successful attempt."""
        attempt = DeliveryAttempt(
            attempt_id="att_123",
            delivery_id="dlv_123",
            webhook_id="whk_123",
            attempt_number=1,
            url="https://example.com/webhook",
        )

        attempt.complete(status_code=200, response_body='{"ok": true}')

        assert attempt.status == DeliveryStatus.DELIVERED
        assert attempt.is_successful is True
        assert attempt.duration_ms is not None

    def test_complete_failure(self):
        """Test completing a failed attempt."""
        attempt = DeliveryAttempt(
            attempt_id="att_123",
            delivery_id="dlv_123",
            webhook_id="whk_123",
            attempt_number=1,
            url="https://example.com/webhook",
        )

        attempt.complete(status_code=500)

        assert attempt.status == DeliveryStatus.FAILED
        assert attempt.is_successful is False
        assert attempt.error_message == "HTTP 500"

    def test_complete_error(self):
        """Test completing with error."""
        attempt = DeliveryAttempt(
            attempt_id="att_123",
            delivery_id="dlv_123",
            webhook_id="whk_123",
            attempt_number=1,
            url="https://example.com/webhook",
        )

        attempt.complete(None, error_message="Connection refused")

        assert attempt.status == DeliveryStatus.FAILED
        assert attempt.error_message == "Connection refused"


class TestWebhookDelivery:
    """Test WebhookDelivery dataclass."""

    def test_create_delivery(self):
        """Test creating a delivery."""
        event = WebhookEvent.create(
            event_type=EventType.GOAL_CREATED,
            data={"goal_id": "goal123"},
        )

        delivery = WebhookDelivery.create(
            webhook_id="whk_123",
            event=event,
        )

        assert delivery.delivery_id.startswith("dlv_")
        assert delivery.webhook_id == "whk_123"
        assert delivery.status == DeliveryStatus.PENDING
        assert delivery.attempt_count == 0

    def test_add_successful_attempt(self):
        """Test adding a successful attempt."""
        event = WebhookEvent.create(
            event_type=EventType.GOAL_CREATED,
            data={"goal_id": "goal123"},
        )

        delivery = WebhookDelivery.create(
            webhook_id="whk_123",
            event=event,
        )

        attempt = DeliveryAttempt(
            attempt_id="att_123",
            delivery_id=delivery.delivery_id,
            webhook_id="whk_123",
            attempt_number=1,
            url="https://example.com/webhook",
        )
        attempt.complete(status_code=200)

        delivery.add_attempt(attempt)

        assert delivery.status == DeliveryStatus.DELIVERED
        assert delivery.attempt_count == 1
        assert delivery.completed_at is not None

    def test_add_failed_attempt_with_retry(self):
        """Test adding a failed attempt with retry."""
        event = WebhookEvent.create(
            event_type=EventType.GOAL_CREATED,
            data={"goal_id": "goal123"},
        )

        delivery = WebhookDelivery.create(
            webhook_id="whk_123",
            event=event,
            max_attempts=5,
        )

        attempt = DeliveryAttempt(
            attempt_id="att_123",
            delivery_id=delivery.delivery_id,
            webhook_id="whk_123",
            attempt_number=1,
            url="https://example.com/webhook",
        )
        attempt.complete(status_code=500)

        delivery.add_attempt(attempt)

        assert delivery.status == DeliveryStatus.RETRYING
        assert delivery.can_retry is True
        assert delivery.next_attempt_at is not None

    def test_max_attempts_exceeded(self):
        """Test when max attempts are exceeded."""
        event = WebhookEvent.create(
            event_type=EventType.GOAL_CREATED,
            data={"goal_id": "goal123"},
        )

        delivery = WebhookDelivery.create(
            webhook_id="whk_123",
            event=event,
            max_attempts=2,
        )

        for i in range(2):
            attempt = DeliveryAttempt(
                attempt_id=f"att_{i}",
                delivery_id=delivery.delivery_id,
                webhook_id="whk_123",
                attempt_number=i + 1,
                url="https://example.com/webhook",
            )
            attempt.complete(status_code=500)
            delivery.add_attempt(attempt)

        assert delivery.status == DeliveryStatus.EXPIRED
        assert delivery.can_retry is False


class TestWebhookConfig:
    """Test WebhookConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        config = WebhookConfig()

        assert config.default_timeout_seconds == 30
        assert config.default_max_retries == 5
        assert config.max_webhooks_per_owner == 100
        assert config.signature_header == "X-Webhook-Signature"


# =============================================================================
# Webhook Store Tests
# =============================================================================

class TestWebhookStore:
    """Test WebhookStore class."""

    @pytest.fixture
    def store(self):
        """Create a webhook store."""
        return WebhookStore()

    @pytest.mark.asyncio
    async def test_save_and_get_webhook(self, store):
        """Test saving and retrieving webhooks."""
        endpoint, _ = WebhookEndpoint.create(
            url="https://example.com/webhook",
            owner_id="user123",
        )

        await store.save_webhook(endpoint)

        retrieved = await store.get_webhook(endpoint.webhook_id)
        assert retrieved is not None
        assert retrieved.webhook_id == endpoint.webhook_id

    @pytest.mark.asyncio
    async def test_get_webhooks_by_owner(self, store):
        """Test retrieving webhooks by owner."""
        endpoint1, _ = WebhookEndpoint.create(
            url="https://example.com/webhook1",
            owner_id="user123",
        )
        endpoint2, _ = WebhookEndpoint.create(
            url="https://example.com/webhook2",
            owner_id="user123",
        )
        endpoint3, _ = WebhookEndpoint.create(
            url="https://example.com/webhook3",
            owner_id="other_user",
        )

        await store.save_webhook(endpoint1)
        await store.save_webhook(endpoint2)
        await store.save_webhook(endpoint3)

        webhooks = await store.get_webhooks_by_owner("user123")
        assert len(webhooks) == 2

    @pytest.mark.asyncio
    async def test_get_webhooks_for_event(self, store):
        """Test retrieving webhooks for an event type."""
        endpoint1, _ = WebhookEndpoint.create(
            url="https://example.com/webhook1",
            owner_id="user123",
            events=[EventType.GOAL_CREATED],
        )
        endpoint2, _ = WebhookEndpoint.create(
            url="https://example.com/webhook2",
            owner_id="user123",
            events=[EventType.AGENT_SPAWNED],
        )
        endpoint3, _ = WebhookEndpoint.create(
            url="https://example.com/webhook3",
            owner_id="user123",
            events=[EventType.ALL],
        )

        await store.save_webhook(endpoint1)
        await store.save_webhook(endpoint2)
        await store.save_webhook(endpoint3)

        webhooks = await store.get_webhooks_for_event(EventType.GOAL_CREATED)
        assert len(webhooks) == 2  # Specific + ALL

    @pytest.mark.asyncio
    async def test_delete_webhook(self, store):
        """Test deleting webhooks."""
        endpoint, _ = WebhookEndpoint.create(
            url="https://example.com/webhook",
            owner_id="user123",
        )

        await store.save_webhook(endpoint)
        result = await store.delete_webhook(endpoint.webhook_id)

        assert result is True
        assert await store.get_webhook(endpoint.webhook_id) is None

    @pytest.mark.asyncio
    async def test_count_by_owner(self, store):
        """Test counting webhooks by owner."""
        endpoint1, _ = WebhookEndpoint.create(
            url="https://example.com/webhook1",
            owner_id="user123",
        )
        endpoint2, _ = WebhookEndpoint.create(
            url="https://example.com/webhook2",
            owner_id="user123",
        )

        await store.save_webhook(endpoint1)
        await store.save_webhook(endpoint2)

        count = await store.count_by_owner("user123")
        assert count == 2

    @pytest.mark.asyncio
    async def test_save_and_get_delivery(self, store):
        """Test saving and retrieving deliveries."""
        event = WebhookEvent.create(
            event_type=EventType.GOAL_CREATED,
            data={"goal_id": "goal123"},
        )
        delivery = WebhookDelivery.create(
            webhook_id="whk_123",
            event=event,
        )

        await store.save_delivery(delivery)

        retrieved = await store.get_delivery(delivery.delivery_id)
        assert retrieved is not None
        assert retrieved.delivery_id == delivery.delivery_id

    @pytest.mark.asyncio
    async def test_get_pending_deliveries(self, store):
        """Test retrieving pending deliveries."""
        event = WebhookEvent.create(
            event_type=EventType.GOAL_CREATED,
            data={"goal_id": "goal123"},
        )

        # Pending delivery
        delivery1 = WebhookDelivery.create(
            webhook_id="whk_123",
            event=event,
        )
        delivery1.next_attempt_at = datetime.utcnow() - timedelta(minutes=1)

        # Future delivery
        delivery2 = WebhookDelivery.create(
            webhook_id="whk_123",
            event=event,
        )
        delivery2.next_attempt_at = datetime.utcnow() + timedelta(hours=1)

        await store.save_delivery(delivery1)
        await store.save_delivery(delivery2)

        pending = await store.get_pending_deliveries()
        assert len(pending) == 1


# =============================================================================
# Webhook Service Tests
# =============================================================================

class TestWebhookService:
    """Test WebhookService class."""

    @pytest.fixture
    def service(self):
        """Create a webhook service."""
        config = WebhookConfig(max_webhooks_per_owner=5)
        return WebhookService(config=config)

    @pytest.mark.asyncio
    async def test_create_webhook(self, service):
        """Test creating a webhook."""
        webhook, secret = await service.create_webhook(
            url="https://example.com/webhook",
            owner_id="user123",
            name="Test Webhook",
            events=[EventType.GOAL_CREATED],
        )

        assert webhook.webhook_id.startswith("whk_")
        assert webhook.url == "https://example.com/webhook"
        assert len(secret) >= 32

    @pytest.mark.asyncio
    async def test_create_webhook_limit(self, service):
        """Test webhook creation limit."""
        for i in range(5):
            await service.create_webhook(
                url=f"https://example.com/webhook{i}",
                owner_id="user123",
            )

        with pytest.raises(WebhookLimitExceededError):
            await service.create_webhook(
                url="https://example.com/webhook_over_limit",
                owner_id="user123",
            )

    @pytest.mark.asyncio
    async def test_get_webhook(self, service):
        """Test getting a webhook."""
        webhook, _ = await service.create_webhook(
            url="https://example.com/webhook",
            owner_id="user123",
        )

        retrieved = await service.get_webhook(webhook.webhook_id)
        assert retrieved.webhook_id == webhook.webhook_id

    @pytest.mark.asyncio
    async def test_get_webhook_not_found(self, service):
        """Test getting a non-existent webhook."""
        with pytest.raises(WebhookNotFoundError):
            await service.get_webhook("whk_nonexistent")

    @pytest.mark.asyncio
    async def test_update_webhook(self, service):
        """Test updating a webhook."""
        webhook, _ = await service.create_webhook(
            url="https://example.com/webhook",
            owner_id="user123",
            name="Original Name",
        )

        updated = await service.update_webhook(
            webhook_id=webhook.webhook_id,
            name="Updated Name",
            url="https://example.com/updated",
        )

        assert updated.name == "Updated Name"
        assert updated.url == "https://example.com/updated"

    @pytest.mark.asyncio
    async def test_delete_webhook(self, service):
        """Test deleting a webhook."""
        webhook, _ = await service.create_webhook(
            url="https://example.com/webhook",
            owner_id="user123",
        )

        result = await service.delete_webhook(webhook.webhook_id)
        assert result is True

        with pytest.raises(WebhookNotFoundError):
            await service.get_webhook(webhook.webhook_id)

    @pytest.mark.asyncio
    async def test_list_webhooks(self, service):
        """Test listing webhooks."""
        for i in range(3):
            await service.create_webhook(
                url=f"https://example.com/webhook{i}",
                owner_id="user123",
            )

        result = await service.list_webhooks("user123")
        assert result.total == 3
        assert len(result.webhooks) == 3

    @pytest.mark.asyncio
    async def test_pause_and_resume_webhook(self, service):
        """Test pausing and resuming a webhook."""
        webhook, _ = await service.create_webhook(
            url="https://example.com/webhook",
            owner_id="user123",
        )

        paused = await service.pause_webhook(webhook.webhook_id)
        assert paused.status == WebhookStatus.PAUSED

        resumed = await service.resume_webhook(webhook.webhook_id)
        assert resumed.status == WebhookStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_rotate_secret(self, service):
        """Test rotating webhook secret."""
        webhook, old_secret = await service.create_webhook(
            url="https://example.com/webhook",
            owner_id="user123",
        )

        _, new_secret = await service.rotate_secret(webhook.webhook_id)

        assert new_secret != old_secret
        assert len(new_secret) >= 32

    @pytest.mark.asyncio
    async def test_publish_event(self, service):
        """Test publishing an event."""
        webhook, _ = await service.create_webhook(
            url="https://example.com/webhook",
            owner_id="user123",
            events=[EventType.GOAL_CREATED],
        )

        # Mock the HTTP client
        with patch.object(service, '_get_session') as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.text = AsyncMock(return_value='{"ok": true}')
            mock_response.headers = {}
            mock_response.__aenter__ = AsyncMock(return_value=mock_response)
            mock_response.__aexit__ = AsyncMock(return_value=None)

            mock_client = AsyncMock()
            mock_client.post = MagicMock(return_value=mock_response)
            mock_session.return_value = mock_client

            deliveries = await service.publish_event(
                event_type=EventType.GOAL_CREATED,
                data={"goal_id": "goal123"},
            )

            assert len(deliveries) == 1

    @pytest.mark.asyncio
    async def test_publish_event_filtered(self, service):
        """Test publishing an event with filter matching."""
        webhook1, _ = await service.create_webhook(
            url="https://example.com/webhook1",
            owner_id="user123",
            events=[EventType.GOAL_CREATED],
            filters={"goal_id": "specific_goal"},
        )

        webhook2, _ = await service.create_webhook(
            url="https://example.com/webhook2",
            owner_id="user123",
            events=[EventType.GOAL_CREATED],
        )

        # Event that matches filter
        with patch.object(service, '_process_delivery'):
            deliveries = await service.publish_event(
                event_type=EventType.GOAL_CREATED,
                data={"goal_id": "specific_goal"},
            )

            assert len(deliveries) == 2

        # Event that doesn't match filter
        with patch.object(service, '_process_delivery'):
            deliveries = await service.publish_event(
                event_type=EventType.GOAL_CREATED,
                data={"goal_id": "other_goal"},
            )

            assert len(deliveries) == 1

    @pytest.mark.asyncio
    async def test_subscribe_local_handler(self, service):
        """Test subscribing a local event handler."""
        received_events = []

        async def handler(event):
            received_events.append(event)

        service.subscribe(EventType.GOAL_CREATED, handler)

        with patch.object(service, '_process_delivery'):
            await service.publish_event(
                event_type=EventType.GOAL_CREATED,
                data={"goal_id": "goal123"},
            )

        assert len(received_events) == 1
        assert received_events[0].event_type == EventType.GOAL_CREATED

    @pytest.mark.asyncio
    async def test_get_webhook_stats(self, service):
        """Test getting webhook statistics."""
        webhook, _ = await service.create_webhook(
            url="https://example.com/webhook",
            owner_id="user123",
        )

        # Simulate some deliveries
        webhook.record_success()
        webhook.record_success()
        webhook.record_failure()

        stats = await service.get_webhook_stats(webhook.webhook_id)

        assert stats["total_deliveries"] == 3
        assert stats["successful_deliveries"] == 2
        assert stats["failed_deliveries"] == 1

    @pytest.mark.asyncio
    async def test_cleanup_old_deliveries(self, service):
        """Test cleaning up old deliveries."""
        event = WebhookEvent.create(
            event_type=EventType.GOAL_CREATED,
            data={"goal_id": "goal123"},
        )

        # Create old delivery
        delivery = WebhookDelivery.create(
            webhook_id="whk_123",
            event=event,
        )
        delivery.created_at = datetime.utcnow() - timedelta(days=60)

        await service.store.save_delivery(delivery)

        count = await service.cleanup_old_deliveries(days=30)
        assert count == 1


# =============================================================================
# Webhook Routes Tests
# =============================================================================

class TestWebhookRoutes:
    """Test webhook API routes."""

    @pytest.fixture
    def service(self):
        """Create a webhook service."""
        return WebhookService()

    @pytest.fixture
    def app(self, service):
        """Create FastAPI app with routes."""
        from fastapi import FastAPI

        app = FastAPI()
        router = create_webhook_routes(service, prefix="")
        app.include_router(router, prefix="/webhooks")

        # Add middleware to set user_id
        @app.middleware("http")
        async def add_user_id(request, call_next):
            request.state.user_id = "user123"
            return await call_next(request)

        return app

    @pytest.mark.asyncio
    async def test_create_webhook_route(self, app, service):
        """Test POST /webhooks endpoint."""
        from fastapi.testclient import TestClient

        client = TestClient(app)
        response = client.post(
            "/webhooks",
            json={
                "url": "https://example.com/webhook",
                "name": "Test Webhook",
                "events": ["goal.created"],
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert "webhook_id" in data
        assert "secret" in data

    @pytest.mark.asyncio
    async def test_list_webhooks_route(self, app, service):
        """Test GET /webhooks endpoint."""
        from fastapi.testclient import TestClient

        # Create webhooks
        await service.create_webhook(
            url="https://example.com/webhook1",
            owner_id="user123",
        )
        await service.create_webhook(
            url="https://example.com/webhook2",
            owner_id="user123",
        )

        client = TestClient(app)
        response = client.get("/webhooks")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2

    @pytest.mark.asyncio
    async def test_get_webhook_route(self, app, service):
        """Test GET /webhooks/{webhook_id} endpoint."""
        from fastapi.testclient import TestClient

        webhook, _ = await service.create_webhook(
            url="https://example.com/webhook",
            owner_id="user123",
        )

        client = TestClient(app)
        response = client.get(f"/webhooks/{webhook.webhook_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["webhook_id"] == webhook.webhook_id

    @pytest.mark.asyncio
    async def test_update_webhook_route(self, app, service):
        """Test PATCH /webhooks/{webhook_id} endpoint."""
        from fastapi.testclient import TestClient

        webhook, _ = await service.create_webhook(
            url="https://example.com/webhook",
            owner_id="user123",
            name="Original",
        )

        client = TestClient(app)
        response = client.patch(
            f"/webhooks/{webhook.webhook_id}",
            json={"name": "Updated"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated"

    @pytest.mark.asyncio
    async def test_delete_webhook_route(self, app, service):
        """Test DELETE /webhooks/{webhook_id} endpoint."""
        from fastapi.testclient import TestClient

        webhook, _ = await service.create_webhook(
            url="https://example.com/webhook",
            owner_id="user123",
        )

        client = TestClient(app)
        response = client.delete(f"/webhooks/{webhook.webhook_id}")

        assert response.status_code == 200
        assert response.json()["success"] is True

    @pytest.mark.asyncio
    async def test_pause_webhook_route(self, app, service):
        """Test POST /webhooks/{webhook_id}/pause endpoint."""
        from fastapi.testclient import TestClient

        webhook, _ = await service.create_webhook(
            url="https://example.com/webhook",
            owner_id="user123",
        )

        client = TestClient(app)
        response = client.post(f"/webhooks/{webhook.webhook_id}/pause")

        assert response.status_code == 200
        assert response.json()["status"] == "paused"

    @pytest.mark.asyncio
    async def test_resume_webhook_route(self, app, service):
        """Test POST /webhooks/{webhook_id}/resume endpoint."""
        from fastapi.testclient import TestClient

        webhook, _ = await service.create_webhook(
            url="https://example.com/webhook",
            owner_id="user123",
        )
        await service.pause_webhook(webhook.webhook_id)

        client = TestClient(app)
        response = client.post(f"/webhooks/{webhook.webhook_id}/resume")

        assert response.status_code == 200
        assert response.json()["status"] == "active"

    @pytest.mark.asyncio
    async def test_rotate_secret_route(self, app, service):
        """Test POST /webhooks/{webhook_id}/rotate-secret endpoint."""
        from fastapi.testclient import TestClient

        webhook, old_secret = await service.create_webhook(
            url="https://example.com/webhook",
            owner_id="user123",
        )

        client = TestClient(app)
        response = client.post(f"/webhooks/{webhook.webhook_id}/rotate-secret")

        assert response.status_code == 200
        data = response.json()
        assert "secret" in data
        assert data["secret"] != old_secret

    @pytest.mark.asyncio
    async def test_get_stats_route(self, app, service):
        """Test GET /webhooks/{webhook_id}/stats endpoint."""
        from fastapi.testclient import TestClient

        webhook, _ = await service.create_webhook(
            url="https://example.com/webhook",
            owner_id="user123",
        )

        client = TestClient(app)
        response = client.get(f"/webhooks/{webhook.webhook_id}/stats")

        assert response.status_code == 200
        data = response.json()
        assert "total_deliveries" in data


class TestWebhookAdminRoutes:
    """Test webhook admin routes."""

    @pytest.fixture
    def service(self):
        """Create a webhook service."""
        return WebhookService()

    @pytest.fixture
    def app(self, service):
        """Create FastAPI app with admin routes."""
        from fastapi import FastAPI

        app = FastAPI()
        router = create_webhook_admin_routes(service, prefix="")
        app.include_router(router, prefix="/admin/webhooks")
        return app

    @pytest.mark.asyncio
    async def test_list_event_types(self, app, service):
        """Test GET /admin/webhooks/events/types endpoint."""
        from fastapi.testclient import TestClient

        client = TestClient(app)
        response = client.get("/admin/webhooks/events/types")

        assert response.status_code == 200
        data = response.json()
        assert "event_types" in data
        assert len(data["event_types"]) > 0

    @pytest.mark.asyncio
    async def test_cleanup_deliveries(self, app, service):
        """Test POST /admin/webhooks/cleanup endpoint."""
        from fastapi.testclient import TestClient

        client = TestClient(app)
        response = client.post("/admin/webhooks/cleanup")

        assert response.status_code == 200
        assert "cleaned_count" in response.json()


class TestWebhookReceiverRoutes:
    """Test webhook receiver routes."""

    @pytest.fixture
    def app(self):
        """Create FastAPI app with receiver routes."""
        from fastapi import FastAPI

        app = FastAPI()
        router = create_webhook_receiver_routes(prefix="")
        app.include_router(router, prefix="/receiver")
        return app

    @pytest.mark.asyncio
    async def test_receive_webhook(self, app):
        """Test POST /receiver/receive endpoint."""
        from fastapi.testclient import TestClient

        client = TestClient(app)
        response = client.post(
            "/receiver/receive",
            json={"event": "test"},
            headers={"X-Event-Type": "test.event"},
        )

        assert response.status_code == 200
        assert response.json()["received"] is True

    @pytest.mark.asyncio
    async def test_list_received_webhooks(self, app):
        """Test GET /receiver/received endpoint."""
        from fastapi.testclient import TestClient

        client = TestClient(app)

        # Send a webhook first
        client.post("/receiver/receive", json={"event": "test"})

        response = client.get("/receiver/received")

        assert response.status_code == 200
        data = response.json()
        assert "webhooks" in data

    @pytest.mark.asyncio
    async def test_clear_received_webhooks(self, app):
        """Test DELETE /receiver/received endpoint."""
        from fastapi.testclient import TestClient

        client = TestClient(app)

        # Send a webhook first
        client.post("/receiver/receive", json={"event": "test"})

        response = client.delete("/receiver/received")

        assert response.status_code == 200
        assert response.json()["success"] is True


# =============================================================================
# Integration Tests
# =============================================================================

class TestWebhookIntegration:
    """Integration tests for webhook system."""

    @pytest.fixture
    def service(self):
        """Create a webhook service."""
        return WebhookService()

    @pytest.mark.asyncio
    async def test_full_webhook_lifecycle(self, service):
        """Test complete webhook lifecycle."""
        # Create webhook
        webhook, secret = await service.create_webhook(
            url="https://example.com/webhook",
            owner_id="user123",
            name="Test Webhook",
            events=[EventType.GOAL_CREATED, EventType.GOAL_COMPLETED],
        )

        assert webhook.status == WebhookStatus.ACTIVE

        # Update webhook
        webhook = await service.update_webhook(
            webhook_id=webhook.webhook_id,
            name="Updated Webhook",
        )
        assert webhook.name == "Updated Webhook"

        # Pause webhook
        webhook = await service.pause_webhook(webhook.webhook_id)
        assert webhook.status == WebhookStatus.PAUSED

        # Resume webhook
        webhook = await service.resume_webhook(webhook.webhook_id)
        assert webhook.status == WebhookStatus.ACTIVE

        # Rotate secret
        webhook, new_secret = await service.rotate_secret(webhook.webhook_id)
        assert new_secret != secret

        # Delete webhook
        result = await service.delete_webhook(webhook.webhook_id)
        assert result is True

    @pytest.mark.asyncio
    async def test_event_filtering(self, service):
        """Test event filtering with multiple webhooks."""
        # Webhook for all goal events
        webhook1, _ = await service.create_webhook(
            url="https://example.com/webhook1",
            owner_id="user123",
            events=[EventType.GOAL_CREATED, EventType.GOAL_COMPLETED],
        )

        # Webhook for specific goal
        webhook2, _ = await service.create_webhook(
            url="https://example.com/webhook2",
            owner_id="user123",
            events=[EventType.GOAL_CREATED],
            filters={"goal_id": "important_goal"},
        )

        # Webhook for all events
        webhook3, _ = await service.create_webhook(
            url="https://example.com/webhook3",
            owner_id="user123",
            events=[EventType.ALL],
        )

        # Publish event for important_goal
        with patch.object(service, '_process_delivery'):
            deliveries = await service.publish_event(
                event_type=EventType.GOAL_CREATED,
                data={"goal_id": "important_goal"},
            )
            # webhook1, webhook2, webhook3 all match
            assert len(deliveries) == 3

        # Publish event for regular goal
        with patch.object(service, '_process_delivery'):
            deliveries = await service.publish_event(
                event_type=EventType.GOAL_CREATED,
                data={"goal_id": "regular_goal"},
            )
            # Only webhook1 and webhook3 match (webhook2 has filter)
            assert len(deliveries) == 2

    @pytest.mark.asyncio
    async def test_signature_verification_flow(self, service):
        """Test signature generation and verification."""
        webhook, secret = await service.create_webhook(
            url="https://example.com/webhook",
            owner_id="user123",
        )

        # Create event
        event = WebhookEvent.create(
            event_type=EventType.GOAL_CREATED,
            data={"goal_id": "goal123"},
        )

        payload = event.to_json()
        timestamp = int(datetime.utcnow().timestamp())

        # Sign payload
        signature = webhook.sign_payload(payload, timestamp)

        # Verify signature
        assert webhook.verify_signature(payload, signature) is True

        # Tampered payload should fail
        assert webhook.verify_signature('{"tampered": true}', signature) is False
