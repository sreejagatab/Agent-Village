"""
Webhook Service Layer.

Provides webhook management and delivery services including:
- Webhook endpoint CRUD operations
- Event publishing and delivery
- Retry logic with exponential backoff
- Signature generation and verification
- Delivery tracking and statistics
"""

import asyncio
import aiohttp
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, Callable, Any
import logging
import uuid

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


logger = logging.getLogger(__name__)


class WebhookError(Exception):
    """Base webhook error."""
    pass


class WebhookNotFoundError(WebhookError):
    """Webhook not found."""
    pass


class WebhookDisabledError(WebhookError):
    """Webhook is disabled."""
    pass


class WebhookLimitExceededError(WebhookError):
    """Webhook limit exceeded."""
    pass


class DeliveryNotFoundError(WebhookError):
    """Delivery not found."""
    pass


class InvalidEventError(WebhookError):
    """Invalid event."""
    pass


class WebhookStore:
    """In-memory webhook storage."""

    def __init__(self):
        self._webhooks: dict[str, WebhookEndpoint] = {}
        self._deliveries: dict[str, WebhookDelivery] = {}
        self._by_owner: dict[str, set[str]] = {}
        self._by_tenant: dict[str, set[str]] = {}
        self._by_event: dict[EventType, set[str]] = {}

    async def save_webhook(self, webhook: WebhookEndpoint) -> None:
        """Save a webhook endpoint."""
        self._webhooks[webhook.webhook_id] = webhook

        # Index by owner
        if webhook.owner_id not in self._by_owner:
            self._by_owner[webhook.owner_id] = set()
        self._by_owner[webhook.owner_id].add(webhook.webhook_id)

        # Index by tenant
        if webhook.tenant_id:
            if webhook.tenant_id not in self._by_tenant:
                self._by_tenant[webhook.tenant_id] = set()
            self._by_tenant[webhook.tenant_id].add(webhook.webhook_id)

        # Index by event
        for event in webhook.events:
            if event not in self._by_event:
                self._by_event[event] = set()
            self._by_event[event].add(webhook.webhook_id)

    async def get_webhook(self, webhook_id: str) -> Optional[WebhookEndpoint]:
        """Get a webhook by ID."""
        return self._webhooks.get(webhook_id)

    async def get_webhooks_by_owner(
        self,
        owner_id: str,
        include_disabled: bool = False,
    ) -> list[WebhookEndpoint]:
        """Get all webhooks for an owner."""
        webhook_ids = self._by_owner.get(owner_id, set())
        webhooks = [self._webhooks[wid] for wid in webhook_ids if wid in self._webhooks]

        if not include_disabled:
            webhooks = [w for w in webhooks if w.status != WebhookStatus.DISABLED]

        return webhooks

    async def get_webhooks_by_tenant(
        self,
        tenant_id: str,
        include_disabled: bool = False,
    ) -> list[WebhookEndpoint]:
        """Get all webhooks for a tenant."""
        webhook_ids = self._by_tenant.get(tenant_id, set())
        webhooks = [self._webhooks[wid] for wid in webhook_ids if wid in self._webhooks]

        if not include_disabled:
            webhooks = [w for w in webhooks if w.status != WebhookStatus.DISABLED]

        return webhooks

    async def get_webhooks_for_event(
        self,
        event_type: EventType,
        tenant_id: Optional[str] = None,
    ) -> list[WebhookEndpoint]:
        """Get all active webhooks subscribed to an event type."""
        # Get webhooks subscribed to specific event or ALL
        webhook_ids = set()
        webhook_ids.update(self._by_event.get(event_type, set()))
        webhook_ids.update(self._by_event.get(EventType.ALL, set()))

        webhooks = []
        for wid in webhook_ids:
            webhook = self._webhooks.get(wid)
            if webhook and webhook.status == WebhookStatus.ACTIVE:
                # Filter by tenant if specified
                if tenant_id is None or webhook.tenant_id == tenant_id:
                    webhooks.append(webhook)

        return webhooks

    async def delete_webhook(self, webhook_id: str) -> bool:
        """Delete a webhook."""
        webhook = self._webhooks.pop(webhook_id, None)
        if not webhook:
            return False

        # Remove from owner index
        if webhook.owner_id in self._by_owner:
            self._by_owner[webhook.owner_id].discard(webhook_id)

        # Remove from tenant index
        if webhook.tenant_id and webhook.tenant_id in self._by_tenant:
            self._by_tenant[webhook.tenant_id].discard(webhook_id)

        # Remove from event indexes
        for event in webhook.events:
            if event in self._by_event:
                self._by_event[event].discard(webhook_id)

        return True

    async def count_by_owner(self, owner_id: str) -> int:
        """Count webhooks by owner."""
        return len(self._by_owner.get(owner_id, set()))

    async def save_delivery(self, delivery: WebhookDelivery) -> None:
        """Save a delivery."""
        self._deliveries[delivery.delivery_id] = delivery

    async def get_delivery(self, delivery_id: str) -> Optional[WebhookDelivery]:
        """Get a delivery by ID."""
        return self._deliveries.get(delivery_id)

    async def get_deliveries_by_webhook(
        self,
        webhook_id: str,
        status: Optional[DeliveryStatus] = None,
        limit: int = 100,
    ) -> list[WebhookDelivery]:
        """Get deliveries for a webhook."""
        deliveries = [
            d for d in self._deliveries.values()
            if d.webhook_id == webhook_id
        ]

        if status:
            deliveries = [d for d in deliveries if d.status == status]

        # Sort by created_at descending
        deliveries.sort(key=lambda d: d.created_at, reverse=True)

        return deliveries[:limit]

    async def get_pending_deliveries(
        self,
        before: Optional[datetime] = None,
        limit: int = 100,
    ) -> list[WebhookDelivery]:
        """Get pending deliveries ready for retry."""
        now = before or datetime.utcnow()
        pending = [
            d for d in self._deliveries.values()
            if d.status in (DeliveryStatus.PENDING, DeliveryStatus.RETRYING)
            and d.next_attempt_at
            and d.next_attempt_at <= now
        ]

        # Sort by next_attempt_at ascending
        pending.sort(key=lambda d: d.next_attempt_at)

        return pending[:limit]

    async def cleanup_old_deliveries(self, before: datetime) -> int:
        """Delete deliveries older than specified date."""
        to_delete = [
            did for did, d in self._deliveries.items()
            if d.created_at < before
        ]

        for did in to_delete:
            del self._deliveries[did]

        return len(to_delete)


@dataclass
class WebhookService:
    """Webhook management service."""

    config: WebhookConfig = field(default_factory=WebhookConfig)
    store: WebhookStore = field(default_factory=WebhookStore)

    # Event handlers for local subscriptions
    _event_handlers: dict[EventType, list[Callable]] = field(default_factory=dict)

    # HTTP client session
    _session: Optional[aiohttp.ClientSession] = None

    # Background task for delivery processing
    _delivery_task: Optional[asyncio.Task] = None
    _running: bool = False

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP client session."""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self.config.default_timeout_seconds)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session

    async def close(self) -> None:
        """Close the service and cleanup resources."""
        self._running = False
        if self._delivery_task:
            self._delivery_task.cancel()
            try:
                await self._delivery_task
            except asyncio.CancelledError:
                pass

        if self._session and not self._session.closed:
            await self._session.close()

    # ==================== Webhook CRUD ====================

    async def create_webhook(
        self,
        url: str,
        owner_id: str,
        events: list[EventType] = None,
        name: Optional[str] = None,
        description: Optional[str] = None,
        tenant_id: Optional[str] = None,
        filters: Optional[dict] = None,
        custom_headers: Optional[dict] = None,
        timeout_seconds: Optional[int] = None,
        max_retries: Optional[int] = None,
    ) -> tuple[WebhookEndpoint, str]:
        """
        Create a new webhook endpoint.
        Returns (webhook, plaintext_secret).
        """
        # Check webhook limit
        count = await self.store.count_by_owner(owner_id)
        if count >= self.config.max_webhooks_per_owner:
            raise WebhookLimitExceededError(
                f"Maximum webhooks ({self.config.max_webhooks_per_owner}) exceeded"
            )

        webhook, secret = WebhookEndpoint.create(
            url=url,
            owner_id=owner_id,
            events=events,
            name=name,
            description=description,
            tenant_id=tenant_id,
            filters=filters,
            custom_headers=custom_headers,
            timeout_seconds=timeout_seconds or self.config.default_timeout_seconds,
            max_retries=max_retries or self.config.default_max_retries,
        )

        await self.store.save_webhook(webhook)
        logger.info(f"Created webhook {webhook.webhook_id} for owner {owner_id}")

        return webhook, secret

    async def get_webhook(self, webhook_id: str) -> WebhookEndpoint:
        """Get a webhook by ID."""
        webhook = await self.store.get_webhook(webhook_id)
        if not webhook:
            raise WebhookNotFoundError(f"Webhook {webhook_id} not found")
        return webhook

    async def update_webhook(
        self,
        webhook_id: str,
        url: Optional[str] = None,
        name: Optional[str] = None,
        description: Optional[str] = None,
        events: Optional[list[EventType]] = None,
        filters: Optional[dict] = None,
        custom_headers: Optional[dict] = None,
        timeout_seconds: Optional[int] = None,
        max_retries: Optional[int] = None,
        status: Optional[WebhookStatus] = None,
    ) -> WebhookEndpoint:
        """Update a webhook."""
        webhook = await self.get_webhook(webhook_id)

        if url is not None:
            webhook.url = url
        if name is not None:
            webhook.name = name
        if description is not None:
            webhook.description = description
        if events is not None:
            webhook.events = events
        if filters is not None:
            webhook.filters = filters
        if custom_headers is not None:
            webhook.custom_headers = custom_headers
        if timeout_seconds is not None:
            webhook.timeout_seconds = timeout_seconds
        if max_retries is not None:
            webhook.max_retries = max_retries
        if status is not None:
            webhook.status = status
            # Reset failures if re-enabling
            if status == WebhookStatus.ACTIVE:
                webhook.consecutive_failures = 0

        webhook.updated_at = datetime.utcnow()
        await self.store.save_webhook(webhook)

        logger.info(f"Updated webhook {webhook_id}")
        return webhook

    async def delete_webhook(self, webhook_id: str) -> bool:
        """Delete a webhook."""
        result = await self.store.delete_webhook(webhook_id)
        if result:
            logger.info(f"Deleted webhook {webhook_id}")
        return result

    async def list_webhooks(
        self,
        owner_id: str,
        include_disabled: bool = False,
        page: int = 1,
        per_page: int = 20,
    ) -> WebhookListResponse:
        """List webhooks for an owner."""
        webhooks = await self.store.get_webhooks_by_owner(owner_id, include_disabled)

        # Paginate
        start = (page - 1) * per_page
        end = start + per_page

        return WebhookListResponse(
            webhooks=webhooks[start:end],
            total=len(webhooks),
            page=page,
            per_page=per_page,
        )

    async def pause_webhook(self, webhook_id: str) -> WebhookEndpoint:
        """Pause a webhook."""
        return await self.update_webhook(webhook_id, status=WebhookStatus.PAUSED)

    async def resume_webhook(self, webhook_id: str) -> WebhookEndpoint:
        """Resume a paused webhook."""
        return await self.update_webhook(webhook_id, status=WebhookStatus.ACTIVE)

    async def disable_webhook(self, webhook_id: str) -> WebhookEndpoint:
        """Disable a webhook."""
        return await self.update_webhook(webhook_id, status=WebhookStatus.DISABLED)

    async def rotate_secret(self, webhook_id: str) -> tuple[WebhookEndpoint, str]:
        """Rotate webhook secret."""
        webhook = await self.get_webhook(webhook_id)

        import secrets
        new_secret = secrets.token_urlsafe(32)
        webhook.secret = new_secret
        webhook.updated_at = datetime.utcnow()

        await self.store.save_webhook(webhook)
        logger.info(f"Rotated secret for webhook {webhook_id}")

        return webhook, new_secret

    # ==================== Event Publishing ====================

    async def publish_event(
        self,
        event_type: EventType,
        data: dict,
        tenant_id: Optional[str] = None,
        user_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> list[WebhookDelivery]:
        """
        Publish an event to all subscribed webhooks.
        Returns list of created deliveries.
        """
        event = WebhookEvent.create(
            event_type=event_type,
            data=data,
            tenant_id=tenant_id,
            user_id=user_id,
            correlation_id=correlation_id,
        )

        # Get subscribed webhooks
        webhooks = await self.store.get_webhooks_for_event(event_type, tenant_id)

        deliveries = []
        for webhook in webhooks:
            # Check if event matches filters
            if not webhook.matches_filters(data):
                continue

            # Create delivery
            delivery = WebhookDelivery.create(
                webhook_id=webhook.webhook_id,
                event=event,
                max_attempts=webhook.max_retries,
                tenant_id=tenant_id,
            )

            await self.store.save_delivery(delivery)
            deliveries.append(delivery)

        # Trigger local handlers
        await self._trigger_local_handlers(event)

        logger.info(
            f"Published event {event.event_type.value} to {len(deliveries)} webhooks"
        )

        # Process deliveries immediately if not running background task
        if not self._running:
            for delivery in deliveries:
                await self._process_delivery(delivery)

        return deliveries

    async def _trigger_local_handlers(self, event: WebhookEvent) -> None:
        """Trigger local event handlers."""
        handlers = self._event_handlers.get(event.event_type, [])
        handlers.extend(self._event_handlers.get(EventType.ALL, []))

        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as e:
                logger.error(f"Error in event handler: {e}")

    def subscribe(self, event_type: EventType, handler: Callable) -> None:
        """Subscribe a local handler to an event type."""
        if event_type not in self._event_handlers:
            self._event_handlers[event_type] = []
        self._event_handlers[event_type].append(handler)

    def unsubscribe(self, event_type: EventType, handler: Callable) -> None:
        """Unsubscribe a local handler."""
        if event_type in self._event_handlers:
            self._event_handlers[event_type] = [
                h for h in self._event_handlers[event_type]
                if h != handler
            ]

    # ==================== Delivery Processing ====================

    async def _process_delivery(self, delivery: WebhookDelivery) -> DeliveryAttempt:
        """Process a single delivery."""
        webhook = await self.store.get_webhook(delivery.webhook_id)
        if not webhook or webhook.status != WebhookStatus.ACTIVE:
            delivery.status = DeliveryStatus.EXPIRED
            await self.store.save_delivery(delivery)
            return None

        # Create attempt
        attempt = DeliveryAttempt(
            attempt_id=f"att_{uuid.uuid4().hex[:16]}",
            delivery_id=delivery.delivery_id,
            webhook_id=webhook.webhook_id,
            attempt_number=delivery.attempt_count + 1,
            url=webhook.url,
        )

        # Prepare payload
        payload = delivery.event.to_json()
        timestamp = int(datetime.utcnow().timestamp())

        # Prepare headers
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "AgentVillage-Webhooks/1.0",
            self.config.signature_header: webhook.sign_payload(payload, timestamp),
            self.config.timestamp_header: str(timestamp),
            "X-Webhook-ID": webhook.webhook_id,
            "X-Event-ID": delivery.event.event_id,
            "X-Event-Type": delivery.event.event_type.value,
            "X-Delivery-ID": delivery.delivery_id,
            "X-Attempt-Number": str(attempt.attempt_number),
        }
        headers.update(webhook.custom_headers)

        attempt.headers = headers
        attempt.payload = payload

        # Send request
        try:
            session = await self._get_session()
            timeout = aiohttp.ClientTimeout(total=webhook.timeout_seconds)

            async with session.post(
                webhook.url,
                data=payload,
                headers=headers,
                timeout=timeout,
            ) as response:
                response_body = await response.text()
                attempt.complete(
                    status_code=response.status,
                    response_body=response_body[:1000],  # Truncate
                    response_headers=dict(response.headers),
                )

        except asyncio.TimeoutError:
            attempt.complete(None, error_message="Request timeout")
        except aiohttp.ClientError as e:
            attempt.complete(None, error_message=str(e))
        except Exception as e:
            attempt.complete(None, error_message=f"Unexpected error: {e}")

        # Update delivery and webhook stats
        delivery.add_attempt(attempt)
        await self.store.save_delivery(delivery)

        if attempt.is_successful:
            webhook.record_success()
        else:
            webhook.record_failure()

        await self.store.save_webhook(webhook)

        logger.info(
            f"Delivery {delivery.delivery_id} attempt {attempt.attempt_number}: "
            f"{'success' if attempt.is_successful else 'failed'}"
        )

        return attempt

    async def retry_delivery(self, delivery_id: str) -> WebhookDelivery:
        """Manually retry a failed delivery."""
        delivery = await self.store.get_delivery(delivery_id)
        if not delivery:
            raise DeliveryNotFoundError(f"Delivery {delivery_id} not found")

        if delivery.status == DeliveryStatus.DELIVERED:
            raise WebhookError("Cannot retry successful delivery")

        # Reset for retry
        delivery.status = DeliveryStatus.RETRYING
        delivery.next_attempt_at = datetime.utcnow()

        await self.store.save_delivery(delivery)
        await self._process_delivery(delivery)

        return delivery

    async def get_delivery(self, delivery_id: str) -> WebhookDelivery:
        """Get a delivery by ID."""
        delivery = await self.store.get_delivery(delivery_id)
        if not delivery:
            raise DeliveryNotFoundError(f"Delivery {delivery_id} not found")
        return delivery

    async def list_deliveries(
        self,
        webhook_id: str,
        status: Optional[DeliveryStatus] = None,
        page: int = 1,
        per_page: int = 20,
    ) -> DeliveryListResponse:
        """List deliveries for a webhook."""
        deliveries = await self.store.get_deliveries_by_webhook(
            webhook_id,
            status=status,
            limit=1000,
        )

        # Paginate
        start = (page - 1) * per_page
        end = start + per_page

        return DeliveryListResponse(
            deliveries=deliveries[start:end],
            total=len(deliveries),
            page=page,
            per_page=per_page,
        )

    # ==================== Testing ====================

    async def test_webhook(self, webhook_id: str) -> WebhookTestResult:
        """Send a test ping to a webhook."""
        webhook = await self.get_webhook(webhook_id)

        # Create test event
        test_event = WebhookEvent.create(
            event_type=EventType.SYSTEM_HEALTH,
            data={
                "type": "test",
                "message": "This is a test webhook delivery",
                "webhook_id": webhook_id,
            },
        )

        payload = test_event.to_json()
        timestamp = int(datetime.utcnow().timestamp())

        headers = {
            "Content-Type": "application/json",
            "User-Agent": "AgentVillage-Webhooks/1.0",
            self.config.signature_header: webhook.sign_payload(payload, timestamp),
            self.config.timestamp_header: str(timestamp),
            "X-Webhook-Test": "true",
        }
        headers.update(webhook.custom_headers)

        start_time = datetime.utcnow()

        try:
            session = await self._get_session()
            timeout = aiohttp.ClientTimeout(total=webhook.timeout_seconds)

            async with session.post(
                webhook.url,
                data=payload,
                headers=headers,
                timeout=timeout,
            ) as response:
                duration = int((datetime.utcnow() - start_time).total_seconds() * 1000)
                return WebhookTestResult(
                    webhook_id=webhook_id,
                    success=200 <= response.status < 300,
                    status_code=response.status,
                    response_time_ms=duration,
                )

        except asyncio.TimeoutError:
            return WebhookTestResult(
                webhook_id=webhook_id,
                success=False,
                error_message="Request timeout",
            )
        except aiohttp.ClientError as e:
            return WebhookTestResult(
                webhook_id=webhook_id,
                success=False,
                error_message=str(e),
            )
        except Exception as e:
            return WebhookTestResult(
                webhook_id=webhook_id,
                success=False,
                error_message=f"Unexpected error: {e}",
            )

    # ==================== Background Processing ====================

    async def start_delivery_processor(self, interval_seconds: int = 10) -> None:
        """Start background delivery processor."""
        self._running = True
        self._delivery_task = asyncio.create_task(
            self._delivery_loop(interval_seconds)
        )
        logger.info("Started webhook delivery processor")

    async def _delivery_loop(self, interval: int) -> None:
        """Background loop for processing pending deliveries."""
        while self._running:
            try:
                pending = await self.store.get_pending_deliveries(limit=50)

                for delivery in pending:
                    if not self._running:
                        break
                    await self._process_delivery(delivery)

            except Exception as e:
                logger.error(f"Error in delivery loop: {e}")

            await asyncio.sleep(interval)

    # ==================== Cleanup ====================

    async def cleanup_old_deliveries(self, days: Optional[int] = None) -> int:
        """Clean up old deliveries."""
        days = days or self.config.delivery_retention_days
        before = datetime.utcnow() - timedelta(days=days)

        count = await self.store.cleanup_old_deliveries(before)
        logger.info(f"Cleaned up {count} old deliveries")

        return count

    # ==================== Statistics ====================

    async def get_webhook_stats(self, webhook_id: str) -> dict:
        """Get statistics for a webhook."""
        webhook = await self.get_webhook(webhook_id)

        return {
            "webhook_id": webhook_id,
            "status": webhook.status.value,
            "total_deliveries": webhook.total_deliveries,
            "successful_deliveries": webhook.successful_deliveries,
            "failed_deliveries": webhook.failed_deliveries,
            "failure_rate": round(webhook.failure_rate, 4),
            "consecutive_failures": webhook.consecutive_failures,
            "last_triggered_at": webhook.last_triggered_at.isoformat() if webhook.last_triggered_at else None,
            "is_healthy": webhook.is_healthy,
        }
