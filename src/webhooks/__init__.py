"""
Webhook System Module.

Provides comprehensive webhook management including:
- Webhook endpoint registration and configuration
- Event publishing to subscribed endpoints
- Retry logic with exponential backoff
- Signature generation and verification (HMAC-SHA256)
- Delivery tracking and statistics
- Background delivery processing
"""

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
    WebhookError,
    WebhookNotFoundError,
    WebhookDisabledError,
    WebhookLimitExceededError,
    DeliveryNotFoundError,
    InvalidEventError,
)

from src.webhooks.middleware import (
    WebhookCreateRequest,
    WebhookUpdateRequest,
    EventPublishRequest,
    publish_webhook_event,
    create_webhook_routes,
    create_webhook_admin_routes,
    create_webhook_receiver_routes,
)

__all__ = [
    # Models
    "WebhookEndpoint",
    "WebhookEvent",
    "WebhookDelivery",
    "DeliveryAttempt",
    "WebhookStatus",
    "DeliveryStatus",
    "EventType",
    "EventCategory",
    "WebhookConfig",
    "WebhookListResponse",
    "DeliveryListResponse",
    "WebhookTestResult",
    # Service
    "WebhookStore",
    "WebhookService",
    "WebhookError",
    "WebhookNotFoundError",
    "WebhookDisabledError",
    "WebhookLimitExceededError",
    "DeliveryNotFoundError",
    "InvalidEventError",
    # Middleware
    "WebhookCreateRequest",
    "WebhookUpdateRequest",
    "EventPublishRequest",
    "publish_webhook_event",
    "create_webhook_routes",
    "create_webhook_admin_routes",
    "create_webhook_receiver_routes",
]
