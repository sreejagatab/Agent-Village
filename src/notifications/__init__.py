"""
Notification System Module.

Provides comprehensive multi-channel notification management including:
- Email notifications (SMTP, SendGrid, SES)
- SMS notifications (Twilio, SNS)
- Push notifications (FCM, APNS)
- In-app notifications
- Notification templates with variable substitution
- User notification preferences
- Delivery tracking and retry logic
"""

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
    NotificationStats,
    NotificationListResponse,
)

from src.notifications.service import (
    NotificationStore,
    NotificationService,
    NotificationError,
    NotificationNotFoundError,
    TemplateNotFoundError,
    ProviderNotConfiguredError,
    PreferencesBlockedError,
    RateLimitExceededError,
)

from src.notifications.middleware import (
    SendNotificationRequest,
    SendToUserRequest,
    SendFromTemplateRequest,
    SendBulkRequest,
    CreateTemplateRequest,
    UpdateTemplateRequest,
    UpdatePreferencesRequest,
    RegisterDeviceRequest,
    create_notification_routes,
    create_notification_send_routes,
    create_notification_admin_routes,
    notify_on_event,
)

from src.notifications.providers import (
    NotificationProvider,
    ProviderResult,
    ProviderError,
    ProviderConnectionError,
    ProviderAuthenticationError,
    ProviderRateLimitError,
    ProviderValidationError,
    # Email
    EmailProvider,
    SMTPProvider,
    SendGridProvider,
    SESProvider,
    # SMS
    SMSProvider,
    TwilioProvider,
    SNSSMSProvider,
    # Push
    PushProvider,
    FCMProvider,
    APNSProvider,
    # In-App
    InAppProvider,
)

__all__ = [
    # Models - Types
    "NotificationType",
    "NotificationStatus",
    "NotificationPriority",
    "NotificationCategory",
    "ChannelType",
    # Models - Data classes
    "NotificationRecipient",
    "NotificationContent",
    "DeliveryAttempt",
    "Notification",
    "NotificationTemplate",
    "NotificationPreferences",
    "ChannelPreference",
    "CategoryPreference",
    "ChannelConfig",
    "NotificationConfig",
    "NotificationStats",
    "NotificationListResponse",
    # Service
    "NotificationStore",
    "NotificationService",
    "NotificationError",
    "NotificationNotFoundError",
    "TemplateNotFoundError",
    "ProviderNotConfiguredError",
    "PreferencesBlockedError",
    "RateLimitExceededError",
    # Middleware
    "SendNotificationRequest",
    "SendToUserRequest",
    "SendFromTemplateRequest",
    "SendBulkRequest",
    "CreateTemplateRequest",
    "UpdateTemplateRequest",
    "UpdatePreferencesRequest",
    "RegisterDeviceRequest",
    "create_notification_routes",
    "create_notification_send_routes",
    "create_notification_admin_routes",
    "notify_on_event",
    # Providers - Base
    "NotificationProvider",
    "ProviderResult",
    "ProviderError",
    "ProviderConnectionError",
    "ProviderAuthenticationError",
    "ProviderRateLimitError",
    "ProviderValidationError",
    # Providers - Email
    "EmailProvider",
    "SMTPProvider",
    "SendGridProvider",
    "SESProvider",
    # Providers - SMS
    "SMSProvider",
    "TwilioProvider",
    "SNSSMSProvider",
    # Providers - Push
    "PushProvider",
    "FCMProvider",
    "APNSProvider",
    # Providers - In-App
    "InAppProvider",
]
