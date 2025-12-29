"""
Webhook System Models.

Provides data models for webhook management including:
- Webhook endpoints and subscriptions
- Event types and payloads
- Delivery attempts and status tracking
- Signature verification
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, Any
import secrets
import hashlib
import hmac
import json
import uuid


class WebhookStatus(str, Enum):
    """Webhook endpoint status."""
    ACTIVE = "active"
    PAUSED = "paused"
    DISABLED = "disabled"
    FAILED = "failed"  # Too many failures


class DeliveryStatus(str, Enum):
    """Webhook delivery status."""
    PENDING = "pending"
    DELIVERED = "delivered"
    FAILED = "failed"
    RETRYING = "retrying"
    EXPIRED = "expired"  # Max retries exceeded


class EventCategory(str, Enum):
    """Event categories for webhooks."""
    GOAL = "goal"
    AGENT = "agent"
    TASK = "task"
    MEMORY = "memory"
    SAFETY = "safety"
    SYSTEM = "system"
    USER = "user"
    SESSION = "session"
    AUTH = "auth"


class EventType(str, Enum):
    """Webhook event types."""
    # Goal events
    GOAL_CREATED = "goal.created"
    GOAL_STARTED = "goal.started"
    GOAL_COMPLETED = "goal.completed"
    GOAL_FAILED = "goal.failed"
    GOAL_CANCELLED = "goal.cancelled"
    GOAL_PAUSED = "goal.paused"
    GOAL_RESUMED = "goal.resumed"

    # Agent events
    AGENT_SPAWNED = "agent.spawned"
    AGENT_COMPLETED = "agent.completed"
    AGENT_FAILED = "agent.failed"
    AGENT_BLOCKED = "agent.blocked"

    # Task events
    TASK_CREATED = "task.created"
    TASK_STARTED = "task.started"
    TASK_COMPLETED = "task.completed"
    TASK_FAILED = "task.failed"

    # Memory events
    MEMORY_STORED = "memory.stored"
    MEMORY_RETRIEVED = "memory.retrieved"
    MEMORY_UPDATED = "memory.updated"

    # Safety events
    SAFETY_VIOLATION = "safety.violation"
    SAFETY_APPROVAL_REQUIRED = "safety.approval_required"
    SAFETY_APPROVAL_GRANTED = "safety.approval_granted"
    SAFETY_APPROVAL_DENIED = "safety.approval_denied"

    # System events
    SYSTEM_HEALTH = "system.health"
    SYSTEM_ERROR = "system.error"
    SYSTEM_WARNING = "system.warning"

    # User events
    USER_CREATED = "user.created"
    USER_UPDATED = "user.updated"
    USER_DELETED = "user.deleted"
    USER_LOGIN = "user.login"
    USER_LOGOUT = "user.logout"

    # Session events
    SESSION_CREATED = "session.created"
    SESSION_EXPIRED = "session.expired"
    SESSION_REVOKED = "session.revoked"

    # Auth events
    AUTH_MFA_ENABLED = "auth.mfa_enabled"
    AUTH_MFA_DISABLED = "auth.mfa_disabled"
    AUTH_API_KEY_CREATED = "auth.api_key_created"
    AUTH_API_KEY_REVOKED = "auth.api_key_revoked"

    # Wildcard
    ALL = "*"


@dataclass
class WebhookEvent:
    """Webhook event payload."""
    event_id: str
    event_type: EventType
    timestamp: datetime
    data: dict

    # Metadata
    source: str = "agent-village"
    version: str = "1.0"
    tenant_id: Optional[str] = None
    user_id: Optional[str] = None
    correlation_id: Optional[str] = None

    @classmethod
    def create(
        cls,
        event_type: EventType,
        data: dict,
        tenant_id: Optional[str] = None,
        user_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> "WebhookEvent":
        """Create a new webhook event."""
        return cls(
            event_id=f"evt_{uuid.uuid4().hex}",
            event_type=event_type,
            timestamp=datetime.utcnow(),
            data=data,
            tenant_id=tenant_id,
            user_id=user_id,
            correlation_id=correlation_id or f"cor_{uuid.uuid4().hex[:12]}",
        )

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
            "version": self.version,
            "data": self.data,
            "metadata": {
                "tenant_id": self.tenant_id,
                "user_id": self.user_id,
                "correlation_id": self.correlation_id,
            },
        }

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), default=str)


@dataclass
class WebhookEndpoint:
    """Webhook endpoint configuration."""
    webhook_id: str
    url: str
    secret: str  # For signing payloads

    # Owner
    owner_id: str
    tenant_id: Optional[str] = None

    # Configuration
    name: Optional[str] = None
    description: Optional[str] = None
    status: WebhookStatus = WebhookStatus.ACTIVE

    # Event subscriptions
    events: list[EventType] = field(default_factory=lambda: [EventType.ALL])

    # Filtering
    filters: dict = field(default_factory=dict)  # e.g., {"goal_id": "specific_id"}

    # Delivery settings
    timeout_seconds: int = 30
    max_retries: int = 5
    retry_delay_seconds: int = 60

    # Headers
    custom_headers: dict = field(default_factory=dict)

    # Rate limiting
    rate_limit_per_minute: Optional[int] = None

    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    last_triggered_at: Optional[datetime] = None

    # Statistics
    total_deliveries: int = 0
    successful_deliveries: int = 0
    failed_deliveries: int = 0
    consecutive_failures: int = 0

    @property
    def failure_rate(self) -> float:
        """Calculate failure rate."""
        if self.total_deliveries == 0:
            return 0.0
        return self.failed_deliveries / self.total_deliveries

    @property
    def is_healthy(self) -> bool:
        """Check if webhook is healthy (not too many failures)."""
        return self.consecutive_failures < 10 and self.status == WebhookStatus.ACTIVE

    def subscribes_to(self, event_type: EventType) -> bool:
        """Check if endpoint subscribes to event type."""
        if EventType.ALL in self.events:
            return True
        return event_type in self.events

    def matches_filters(self, event_data: dict) -> bool:
        """Check if event data matches filters."""
        if not self.filters:
            return True

        for key, value in self.filters.items():
            if key not in event_data:
                return False
            if isinstance(value, list):
                if event_data[key] not in value:
                    return False
            elif event_data[key] != value:
                return False

        return True

    def record_success(self) -> None:
        """Record successful delivery."""
        self.total_deliveries += 1
        self.successful_deliveries += 1
        self.consecutive_failures = 0
        self.last_triggered_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

    def record_failure(self) -> None:
        """Record failed delivery."""
        self.total_deliveries += 1
        self.failed_deliveries += 1
        self.consecutive_failures += 1
        self.updated_at = datetime.utcnow()

        # Auto-disable after too many failures
        if self.consecutive_failures >= 50:
            self.status = WebhookStatus.FAILED

    @classmethod
    def create(
        cls,
        url: str,
        owner_id: str,
        events: list[EventType] = None,
        name: Optional[str] = None,
        description: Optional[str] = None,
        tenant_id: Optional[str] = None,
        filters: Optional[dict] = None,
        custom_headers: Optional[dict] = None,
        timeout_seconds: int = 30,
        max_retries: int = 5,
    ) -> tuple["WebhookEndpoint", str]:
        """
        Create a new webhook endpoint.
        Returns (endpoint, plaintext_secret).
        """
        webhook_id = f"whk_{uuid.uuid4().hex[:16]}"
        secret = secrets.token_urlsafe(32)

        endpoint = cls(
            webhook_id=webhook_id,
            url=url,
            secret=secret,
            owner_id=owner_id,
            tenant_id=tenant_id,
            name=name,
            description=description,
            events=events or [EventType.ALL],
            filters=filters or {},
            custom_headers=custom_headers or {},
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
        )

        return endpoint, secret

    def sign_payload(self, payload: str, timestamp: int) -> str:
        """Generate HMAC signature for payload."""
        message = f"{timestamp}.{payload}"
        signature = hmac.new(
            self.secret.encode(),
            message.encode(),
            hashlib.sha256,
        ).hexdigest()
        return f"t={timestamp},v1={signature}"

    def verify_signature(
        self,
        payload: str,
        signature: str,
        tolerance_seconds: int = 300,
    ) -> bool:
        """Verify webhook signature."""
        try:
            parts = dict(p.split("=") for p in signature.split(","))
            timestamp = int(parts["t"])
            expected_sig = parts["v1"]

            # Check timestamp tolerance
            now = int(datetime.utcnow().timestamp())
            if abs(now - timestamp) > tolerance_seconds:
                return False

            # Verify signature
            message = f"{timestamp}.{payload}"
            computed = hmac.new(
                self.secret.encode(),
                message.encode(),
                hashlib.sha256,
            ).hexdigest()

            return hmac.compare_digest(computed, expected_sig)
        except (KeyError, ValueError):
            return False

    def to_dict(self, include_secret: bool = False) -> dict:
        """Convert to dictionary."""
        result = {
            "webhook_id": self.webhook_id,
            "url": self.url,
            "owner_id": self.owner_id,
            "tenant_id": self.tenant_id,
            "name": self.name,
            "description": self.description,
            "status": self.status.value,
            "events": [e.value for e in self.events],
            "filters": self.filters,
            "timeout_seconds": self.timeout_seconds,
            "max_retries": self.max_retries,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "last_triggered_at": self.last_triggered_at.isoformat() if self.last_triggered_at else None,
            "statistics": {
                "total_deliveries": self.total_deliveries,
                "successful_deliveries": self.successful_deliveries,
                "failed_deliveries": self.failed_deliveries,
                "failure_rate": round(self.failure_rate, 4),
                "consecutive_failures": self.consecutive_failures,
            },
        }

        if include_secret:
            result["secret"] = self.secret

        return result


@dataclass
class DeliveryAttempt:
    """Record of a webhook delivery attempt."""
    attempt_id: str
    delivery_id: str
    webhook_id: str
    attempt_number: int

    # Request details
    url: str
    method: str = "POST"
    headers: dict = field(default_factory=dict)
    payload: str = ""

    # Response details
    status_code: Optional[int] = None
    response_body: Optional[str] = None
    response_headers: dict = field(default_factory=dict)

    # Timing
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None

    # Status
    status: DeliveryStatus = DeliveryStatus.PENDING
    error_message: Optional[str] = None

    @property
    def is_successful(self) -> bool:
        """Check if attempt was successful (2xx status)."""
        return self.status_code is not None and 200 <= self.status_code < 300

    def complete(
        self,
        status_code: Optional[int],
        response_body: Optional[str] = None,
        response_headers: Optional[dict] = None,
        error_message: Optional[str] = None,
    ) -> None:
        """Mark attempt as complete."""
        self.completed_at = datetime.utcnow()
        self.duration_ms = int((self.completed_at - self.started_at).total_seconds() * 1000)
        self.status_code = status_code
        self.response_body = response_body
        self.response_headers = response_headers or {}

        if error_message:
            self.status = DeliveryStatus.FAILED
            self.error_message = error_message
        elif self.is_successful:
            self.status = DeliveryStatus.DELIVERED
        else:
            self.status = DeliveryStatus.FAILED
            self.error_message = f"HTTP {status_code}"

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "attempt_id": self.attempt_id,
            "delivery_id": self.delivery_id,
            "webhook_id": self.webhook_id,
            "attempt_number": self.attempt_number,
            "url": self.url,
            "status_code": self.status_code,
            "status": self.status.value,
            "duration_ms": self.duration_ms,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error_message": self.error_message,
        }


@dataclass
class WebhookDelivery:
    """Webhook delivery record."""
    delivery_id: str
    webhook_id: str
    event: WebhookEvent

    # Status
    status: DeliveryStatus = DeliveryStatus.PENDING

    # Attempts
    attempts: list[DeliveryAttempt] = field(default_factory=list)
    max_attempts: int = 5

    # Scheduling
    created_at: datetime = field(default_factory=datetime.utcnow)
    next_attempt_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Metadata
    tenant_id: Optional[str] = None

    @property
    def attempt_count(self) -> int:
        """Number of delivery attempts."""
        return len(self.attempts)

    @property
    def can_retry(self) -> bool:
        """Check if delivery can be retried."""
        return (
            self.status in (DeliveryStatus.FAILED, DeliveryStatus.RETRYING)
            and self.attempt_count < self.max_attempts
        )

    @property
    def last_attempt(self) -> Optional[DeliveryAttempt]:
        """Get the last delivery attempt."""
        return self.attempts[-1] if self.attempts else None

    def add_attempt(self, attempt: DeliveryAttempt) -> None:
        """Add a delivery attempt."""
        self.attempts.append(attempt)

        if attempt.is_successful:
            self.status = DeliveryStatus.DELIVERED
            self.completed_at = datetime.utcnow()
        elif self.attempt_count < self.max_attempts:
            self.status = DeliveryStatus.RETRYING
            # Exponential backoff: 1min, 2min, 4min, 8min, 16min
            delay = 60 * (2 ** (self.attempt_count - 1))
            self.next_attempt_at = datetime.utcnow() + timedelta(seconds=delay)
        else:
            self.status = DeliveryStatus.EXPIRED
            self.completed_at = datetime.utcnow()

    @classmethod
    def create(
        cls,
        webhook_id: str,
        event: WebhookEvent,
        max_attempts: int = 5,
        tenant_id: Optional[str] = None,
    ) -> "WebhookDelivery":
        """Create a new delivery."""
        return cls(
            delivery_id=f"dlv_{uuid.uuid4().hex[:16]}",
            webhook_id=webhook_id,
            event=event,
            max_attempts=max_attempts,
            next_attempt_at=datetime.utcnow(),
            tenant_id=tenant_id,
        )

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "delivery_id": self.delivery_id,
            "webhook_id": self.webhook_id,
            "event_id": self.event.event_id,
            "event_type": self.event.event_type.value,
            "status": self.status.value,
            "attempt_count": self.attempt_count,
            "max_attempts": self.max_attempts,
            "created_at": self.created_at.isoformat(),
            "next_attempt_at": self.next_attempt_at.isoformat() if self.next_attempt_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "attempts": [a.to_dict() for a in self.attempts],
        }


@dataclass
class WebhookConfig:
    """Webhook system configuration."""
    # Delivery settings
    default_timeout_seconds: int = 30
    default_max_retries: int = 5
    max_payload_size_bytes: int = 1024 * 1024  # 1MB

    # Rate limiting
    max_deliveries_per_minute: int = 1000
    max_webhooks_per_owner: int = 100

    # Retry settings
    initial_retry_delay_seconds: int = 60
    max_retry_delay_seconds: int = 3600  # 1 hour
    retry_backoff_multiplier: float = 2.0

    # Health settings
    max_consecutive_failures: int = 50
    auto_disable_on_failures: bool = True

    # Signature settings
    signature_header: str = "X-Webhook-Signature"
    timestamp_header: str = "X-Webhook-Timestamp"
    signature_tolerance_seconds: int = 300

    # Cleanup settings
    delivery_retention_days: int = 30
    attempt_retention_days: int = 7


@dataclass
class WebhookListResponse:
    """Response for listing webhooks."""
    webhooks: list[WebhookEndpoint]
    total: int
    page: int = 1
    per_page: int = 20


@dataclass
class DeliveryListResponse:
    """Response for listing deliveries."""
    deliveries: list[WebhookDelivery]
    total: int
    page: int = 1
    per_page: int = 20


@dataclass
class WebhookTestResult:
    """Result of webhook test ping."""
    webhook_id: str
    success: bool
    status_code: Optional[int] = None
    response_time_ms: Optional[int] = None
    error_message: Optional[str] = None
    tested_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "webhook_id": self.webhook_id,
            "success": self.success,
            "status_code": self.status_code,
            "response_time_ms": self.response_time_ms,
            "error_message": self.error_message,
            "tested_at": self.tested_at.isoformat(),
        }
