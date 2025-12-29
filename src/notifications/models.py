"""
Notification System Models.

Provides data models for multi-channel notifications including:
- Email, SMS, Push, and In-App notifications
- Notification templates with variable substitution
- User notification preferences
- Delivery tracking and retry logic
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid
import json


class NotificationType(str, Enum):
    """Types of notifications."""
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    IN_APP = "in_app"


class NotificationStatus(str, Enum):
    """Notification delivery status."""
    PENDING = "pending"
    QUEUED = "queued"
    SENDING = "sending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    CANCELLED = "cancelled"
    READ = "read"


class NotificationPriority(str, Enum):
    """Notification priority levels."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class NotificationCategory(str, Enum):
    """Notification categories for grouping and preferences."""
    SYSTEM = "system"
    SECURITY = "security"
    GOAL = "goal"
    AGENT = "agent"
    TASK = "task"
    ALERT = "alert"
    MARKETING = "marketing"
    REMINDER = "reminder"
    DIGEST = "digest"


class ChannelType(str, Enum):
    """Notification channel/provider types."""
    # Email providers
    SMTP = "smtp"
    SENDGRID = "sendgrid"
    SES = "ses"
    MAILGUN = "mailgun"

    # SMS providers
    TWILIO = "twilio"
    SNS = "sns"
    NEXMO = "nexmo"

    # Push providers
    FCM = "fcm"
    APNS = "apns"
    WEB_PUSH = "web_push"

    # In-app
    INTERNAL = "internal"


@dataclass
class NotificationRecipient:
    """Recipient information for a notification."""
    user_id: str
    email: Optional[str] = None
    phone: Optional[str] = None
    device_tokens: List[str] = field(default_factory=list)
    name: Optional[str] = None
    locale: str = "en"
    timezone: str = "UTC"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "user_id": self.user_id,
            "email": self.email,
            "phone": self.phone,
            "device_tokens": self.device_tokens,
            "name": self.name,
            "locale": self.locale,
            "timezone": self.timezone,
        }


@dataclass
class NotificationContent:
    """Content for a notification."""
    subject: Optional[str] = None  # For email
    title: Optional[str] = None  # For push/in-app
    body: str = ""
    html_body: Optional[str] = None  # For email
    short_body: Optional[str] = None  # For SMS (160 char limit)

    # Rich content
    image_url: Optional[str] = None
    action_url: Optional[str] = None
    action_text: Optional[str] = None

    # Push notification specific
    badge: Optional[int] = None
    sound: Optional[str] = None
    data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "subject": self.subject,
            "title": self.title,
            "body": self.body,
            "html_body": self.html_body,
            "short_body": self.short_body,
            "image_url": self.image_url,
            "action_url": self.action_url,
            "action_text": self.action_text,
            "badge": self.badge,
            "sound": self.sound,
            "data": self.data,
        }

    def get_sms_body(self) -> str:
        """Get SMS-appropriate body (truncated if needed)."""
        text = self.short_body or self.body
        if len(text) > 160:
            return text[:157] + "..."
        return text


@dataclass
class DeliveryAttempt:
    """Record of a delivery attempt."""
    attempt_id: str = field(default_factory=lambda: f"att_{uuid.uuid4().hex[:12]}")
    attempt_number: int = 1
    channel_type: ChannelType = ChannelType.INTERNAL
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

    # Result
    success: bool = False
    error_code: Optional[str] = None
    error_message: Optional[str] = None

    # Provider response
    provider_message_id: Optional[str] = None
    provider_response: Optional[Dict[str, Any]] = None

    @property
    def duration_ms(self) -> Optional[int]:
        """Get duration in milliseconds."""
        if self.completed_at:
            delta = self.completed_at - self.started_at
            return int(delta.total_seconds() * 1000)
        return None

    def complete(
        self,
        success: bool,
        error_code: Optional[str] = None,
        error_message: Optional[str] = None,
        provider_message_id: Optional[str] = None,
        provider_response: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Mark the attempt as complete."""
        self.completed_at = datetime.utcnow()
        self.success = success
        self.error_code = error_code
        self.error_message = error_message
        self.provider_message_id = provider_message_id
        self.provider_response = provider_response

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "attempt_id": self.attempt_id,
            "attempt_number": self.attempt_number,
            "channel_type": self.channel_type.value,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_ms": self.duration_ms,
            "success": self.success,
            "error_code": self.error_code,
            "error_message": self.error_message,
            "provider_message_id": self.provider_message_id,
        }


@dataclass
class Notification:
    """Core notification model."""
    notification_id: str = field(default_factory=lambda: f"ntf_{uuid.uuid4().hex[:16]}")

    # Type and category
    notification_type: NotificationType = NotificationType.IN_APP
    category: NotificationCategory = NotificationCategory.SYSTEM
    priority: NotificationPriority = NotificationPriority.NORMAL

    # Recipient
    recipient: NotificationRecipient = field(default_factory=lambda: NotificationRecipient(user_id=""))

    # Content
    content: NotificationContent = field(default_factory=NotificationContent)

    # Template (if used)
    template_id: Optional[str] = None
    template_data: Dict[str, Any] = field(default_factory=dict)

    # Status and tracking
    status: NotificationStatus = NotificationStatus.PENDING
    attempts: List[DeliveryAttempt] = field(default_factory=list)
    max_attempts: int = 3

    # Scheduling
    scheduled_at: Optional[datetime] = None
    send_after: Optional[datetime] = None
    expires_at: Optional[datetime] = None

    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    read_at: Optional[datetime] = None

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)

    # Multi-tenancy
    tenant_id: Optional[str] = None

    # Grouping
    group_id: Optional[str] = None  # For notification grouping
    thread_id: Optional[str] = None  # For conversation threading

    @property
    def attempt_count(self) -> int:
        """Get number of delivery attempts."""
        return len(self.attempts)

    @property
    def can_retry(self) -> bool:
        """Check if notification can be retried."""
        return (
            self.status in (NotificationStatus.FAILED, NotificationStatus.PENDING)
            and self.attempt_count < self.max_attempts
            and (self.expires_at is None or datetime.utcnow() < self.expires_at)
        )

    @property
    def is_expired(self) -> bool:
        """Check if notification has expired."""
        if self.expires_at:
            return datetime.utcnow() > self.expires_at
        return False

    @property
    def is_scheduled(self) -> bool:
        """Check if notification is scheduled for later."""
        if self.scheduled_at:
            return datetime.utcnow() < self.scheduled_at
        if self.send_after:
            return datetime.utcnow() < self.send_after
        return False

    @property
    def last_attempt(self) -> Optional[DeliveryAttempt]:
        """Get the last delivery attempt."""
        return self.attempts[-1] if self.attempts else None

    def add_attempt(self, attempt: DeliveryAttempt) -> None:
        """Add a delivery attempt and update status."""
        self.attempts.append(attempt)
        self.updated_at = datetime.utcnow()

        if attempt.success:
            self.status = NotificationStatus.SENT
            self.sent_at = datetime.utcnow()
        elif self.can_retry:
            self.status = NotificationStatus.PENDING
        else:
            self.status = NotificationStatus.FAILED

    def mark_delivered(self) -> None:
        """Mark notification as delivered."""
        self.status = NotificationStatus.DELIVERED
        self.delivered_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

    def mark_read(self) -> None:
        """Mark notification as read."""
        self.status = NotificationStatus.READ
        self.read_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

    def cancel(self) -> bool:
        """Cancel the notification if possible."""
        if self.status in (NotificationStatus.PENDING, NotificationStatus.QUEUED):
            self.status = NotificationStatus.CANCELLED
            self.updated_at = datetime.utcnow()
            return True
        return False

    def to_dict(self, include_attempts: bool = True) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {
            "notification_id": self.notification_id,
            "notification_type": self.notification_type.value,
            "category": self.category.value,
            "priority": self.priority.value,
            "recipient": self.recipient.to_dict(),
            "content": self.content.to_dict(),
            "template_id": self.template_id,
            "status": self.status.value,
            "attempt_count": self.attempt_count,
            "max_attempts": self.max_attempts,
            "scheduled_at": self.scheduled_at.isoformat() if self.scheduled_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "created_at": self.created_at.isoformat(),
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
            "delivered_at": self.delivered_at.isoformat() if self.delivered_at else None,
            "read_at": self.read_at.isoformat() if self.read_at else None,
            "tags": self.tags,
            "group_id": self.group_id,
            "tenant_id": self.tenant_id,
        }

        if include_attempts:
            result["attempts"] = [a.to_dict() for a in self.attempts]

        return result

    @classmethod
    def create_email(
        cls,
        recipient: NotificationRecipient,
        subject: str,
        body: str,
        html_body: Optional[str] = None,
        **kwargs,
    ) -> "Notification":
        """Create an email notification."""
        return cls(
            notification_type=NotificationType.EMAIL,
            recipient=recipient,
            content=NotificationContent(
                subject=subject,
                body=body,
                html_body=html_body,
            ),
            **kwargs,
        )

    @classmethod
    def create_sms(
        cls,
        recipient: NotificationRecipient,
        body: str,
        **kwargs,
    ) -> "Notification":
        """Create an SMS notification."""
        return cls(
            notification_type=NotificationType.SMS,
            recipient=recipient,
            content=NotificationContent(body=body),
            **kwargs,
        )

    @classmethod
    def create_push(
        cls,
        recipient: NotificationRecipient,
        title: str,
        body: str,
        data: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> "Notification":
        """Create a push notification."""
        return cls(
            notification_type=NotificationType.PUSH,
            recipient=recipient,
            content=NotificationContent(
                title=title,
                body=body,
                data=data or {},
            ),
            **kwargs,
        )

    @classmethod
    def create_in_app(
        cls,
        recipient: NotificationRecipient,
        title: str,
        body: str,
        action_url: Optional[str] = None,
        **kwargs,
    ) -> "Notification":
        """Create an in-app notification."""
        return cls(
            notification_type=NotificationType.IN_APP,
            recipient=recipient,
            content=NotificationContent(
                title=title,
                body=body,
                action_url=action_url,
            ),
            **kwargs,
        )


@dataclass
class NotificationTemplate:
    """Reusable notification template with variable substitution."""
    template_id: str = field(default_factory=lambda: f"tpl_{uuid.uuid4().hex[:12]}")
    name: str = ""
    description: Optional[str] = None

    # Template type
    notification_type: NotificationType = NotificationType.EMAIL
    category: NotificationCategory = NotificationCategory.SYSTEM

    # Content templates (use {{variable}} syntax)
    subject_template: Optional[str] = None
    title_template: Optional[str] = None
    body_template: str = ""
    html_body_template: Optional[str] = None
    short_body_template: Optional[str] = None

    # Default settings
    default_priority: NotificationPriority = NotificationPriority.NORMAL

    # Metadata
    locale: str = "en"
    version: int = 1
    is_active: bool = True

    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    # Multi-tenancy
    tenant_id: Optional[str] = None

    def render(self, data: Dict[str, Any]) -> NotificationContent:
        """Render the template with provided data."""
        def substitute(template: Optional[str]) -> Optional[str]:
            if not template:
                return None
            result = template
            for key, value in data.items():
                result = result.replace(f"{{{{{key}}}}}", str(value))
            return result

        return NotificationContent(
            subject=substitute(self.subject_template),
            title=substitute(self.title_template),
            body=substitute(self.body_template) or "",
            html_body=substitute(self.html_body_template),
            short_body=substitute(self.short_body_template),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "template_id": self.template_id,
            "name": self.name,
            "description": self.description,
            "notification_type": self.notification_type.value,
            "category": self.category.value,
            "subject_template": self.subject_template,
            "title_template": self.title_template,
            "body_template": self.body_template,
            "html_body_template": self.html_body_template,
            "default_priority": self.default_priority.value,
            "locale": self.locale,
            "version": self.version,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "tenant_id": self.tenant_id,
        }


@dataclass
class ChannelPreference:
    """User preference for a notification channel."""
    channel_type: NotificationType
    enabled: bool = True

    # Quiet hours
    quiet_hours_start: Optional[int] = None  # Hour (0-23)
    quiet_hours_end: Optional[int] = None

    # Frequency limits
    max_per_hour: Optional[int] = None
    max_per_day: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "channel_type": self.channel_type.value,
            "enabled": self.enabled,
            "quiet_hours_start": self.quiet_hours_start,
            "quiet_hours_end": self.quiet_hours_end,
            "max_per_hour": self.max_per_hour,
            "max_per_day": self.max_per_day,
        }


@dataclass
class CategoryPreference:
    """User preference for a notification category."""
    category: NotificationCategory
    enabled: bool = True
    channels: List[NotificationType] = field(default_factory=list)  # Empty = all channels

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "category": self.category.value,
            "enabled": self.enabled,
            "channels": [c.value for c in self.channels],
        }


@dataclass
class NotificationPreferences:
    """User notification preferences."""
    user_id: str

    # Global settings
    notifications_enabled: bool = True

    # Channel preferences
    channel_preferences: Dict[NotificationType, ChannelPreference] = field(
        default_factory=lambda: {
            NotificationType.EMAIL: ChannelPreference(NotificationType.EMAIL),
            NotificationType.SMS: ChannelPreference(NotificationType.SMS),
            NotificationType.PUSH: ChannelPreference(NotificationType.PUSH),
            NotificationType.IN_APP: ChannelPreference(NotificationType.IN_APP),
        }
    )

    # Category preferences
    category_preferences: Dict[NotificationCategory, CategoryPreference] = field(
        default_factory=dict
    )

    # Digest settings
    digest_enabled: bool = False
    digest_frequency: str = "daily"  # daily, weekly
    digest_time: int = 9  # Hour (0-23)

    # Contact info
    email: Optional[str] = None
    phone: Optional[str] = None
    device_tokens: List[str] = field(default_factory=list)

    # Timezone
    timezone: str = "UTC"

    # Timestamps
    updated_at: datetime = field(default_factory=datetime.utcnow)

    # Multi-tenancy
    tenant_id: Optional[str] = None

    def is_channel_enabled(self, channel: NotificationType) -> bool:
        """Check if a channel is enabled."""
        if not self.notifications_enabled:
            return False
        pref = self.channel_preferences.get(channel)
        return pref.enabled if pref else True

    def is_category_enabled(
        self,
        category: NotificationCategory,
        channel: Optional[NotificationType] = None,
    ) -> bool:
        """Check if a category is enabled (optionally for a specific channel)."""
        if not self.notifications_enabled:
            return False

        pref = self.category_preferences.get(category)
        if not pref:
            return True  # Default enabled

        if not pref.enabled:
            return False

        if channel and pref.channels:
            return channel in pref.channels

        return True

    def is_in_quiet_hours(self, channel: NotificationType) -> bool:
        """Check if currently in quiet hours for a channel."""
        pref = self.channel_preferences.get(channel)
        if not pref or pref.quiet_hours_start is None or pref.quiet_hours_end is None:
            return False

        # Get current hour in user's timezone
        from datetime import timezone as tz
        import pytz
        try:
            user_tz = pytz.timezone(self.timezone)
            current_hour = datetime.now(user_tz).hour
        except Exception:
            current_hour = datetime.utcnow().hour

        start = pref.quiet_hours_start
        end = pref.quiet_hours_end

        if start <= end:
            return start <= current_hour < end
        else:
            # Quiet hours span midnight
            return current_hour >= start or current_hour < end

    def should_send(
        self,
        notification_type: NotificationType,
        category: NotificationCategory,
        priority: NotificationPriority = NotificationPriority.NORMAL,
    ) -> bool:
        """Determine if a notification should be sent based on preferences."""
        # Urgent notifications bypass most preferences
        if priority == NotificationPriority.URGENT:
            return self.notifications_enabled

        if not self.is_channel_enabled(notification_type):
            return False

        if not self.is_category_enabled(category, notification_type):
            return False

        # High priority bypasses quiet hours
        if priority != NotificationPriority.HIGH and self.is_in_quiet_hours(notification_type):
            return False

        return True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "user_id": self.user_id,
            "notifications_enabled": self.notifications_enabled,
            "channel_preferences": {
                k.value: v.to_dict() for k, v in self.channel_preferences.items()
            },
            "category_preferences": {
                k.value: v.to_dict() for k, v in self.category_preferences.items()
            },
            "digest_enabled": self.digest_enabled,
            "digest_frequency": self.digest_frequency,
            "digest_time": self.digest_time,
            "email": self.email,
            "phone": self.phone,
            "device_tokens": self.device_tokens,
            "timezone": self.timezone,
            "updated_at": self.updated_at.isoformat(),
            "tenant_id": self.tenant_id,
        }


@dataclass
class ChannelConfig:
    """Configuration for a notification channel/provider."""
    channel_type: ChannelType
    name: str = ""
    is_enabled: bool = True
    is_default: bool = False

    # Provider settings
    settings: Dict[str, Any] = field(default_factory=dict)

    # Rate limits
    rate_limit_per_second: Optional[float] = None
    rate_limit_per_minute: Optional[int] = None

    # Retry settings
    max_retries: int = 3
    retry_delay_seconds: int = 60

    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    # Multi-tenancy
    tenant_id: Optional[str] = None

    def to_dict(self, include_secrets: bool = False) -> Dict[str, Any]:
        """Convert to dictionary."""
        settings = self.settings.copy()
        if not include_secrets:
            # Mask sensitive settings
            for key in ["api_key", "secret", "password", "token"]:
                if key in settings:
                    settings[key] = "***"

        return {
            "channel_type": self.channel_type.value,
            "name": self.name,
            "is_enabled": self.is_enabled,
            "is_default": self.is_default,
            "settings": settings,
            "rate_limit_per_second": self.rate_limit_per_second,
            "rate_limit_per_minute": self.rate_limit_per_minute,
            "max_retries": self.max_retries,
            "retry_delay_seconds": self.retry_delay_seconds,
            "created_at": self.created_at.isoformat(),
            "tenant_id": self.tenant_id,
        }


@dataclass
class NotificationConfig:
    """Global notification system configuration."""
    # Default settings
    default_max_attempts: int = 3
    default_retry_delay_seconds: int = 60
    default_expiry_hours: int = 72

    # Rate limits
    max_notifications_per_user_per_hour: int = 100
    max_notifications_per_user_per_day: int = 500

    # Batch settings
    batch_size: int = 100
    batch_delay_ms: int = 100

    # Cleanup
    retention_days: int = 30

    # Feature flags
    digest_enabled: bool = True
    template_caching: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "default_max_attempts": self.default_max_attempts,
            "default_retry_delay_seconds": self.default_retry_delay_seconds,
            "default_expiry_hours": self.default_expiry_hours,
            "max_notifications_per_user_per_hour": self.max_notifications_per_user_per_hour,
            "max_notifications_per_user_per_day": self.max_notifications_per_user_per_day,
            "batch_size": self.batch_size,
            "batch_delay_ms": self.batch_delay_ms,
            "retention_days": self.retention_days,
            "digest_enabled": self.digest_enabled,
            "template_caching": self.template_caching,
        }


@dataclass
class NotificationListResponse:
    """Paginated list of notifications."""
    notifications: List[Notification]
    total: int
    offset: int
    limit: int
    unread_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "notifications": [n.to_dict(include_attempts=False) for n in self.notifications],
            "total": self.total,
            "offset": self.offset,
            "limit": self.limit,
            "unread_count": self.unread_count,
        }


@dataclass
class NotificationStats:
    """Statistics for notifications."""
    total_sent: int = 0
    total_delivered: int = 0
    total_failed: int = 0
    total_read: int = 0

    # By type
    by_type: Dict[str, int] = field(default_factory=dict)

    # By category
    by_category: Dict[str, int] = field(default_factory=dict)

    # Delivery rate
    delivery_rate: float = 0.0
    read_rate: float = 0.0

    # Time period
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_sent": self.total_sent,
            "total_delivered": self.total_delivered,
            "total_failed": self.total_failed,
            "total_read": self.total_read,
            "by_type": self.by_type,
            "by_category": self.by_category,
            "delivery_rate": self.delivery_rate,
            "read_rate": self.read_rate,
            "period_start": self.period_start.isoformat() if self.period_start else None,
            "period_end": self.period_end.isoformat() if self.period_end else None,
        }
