"""
Notification Providers Module.

Provides channel-specific delivery implementations including:
- Email providers (SMTP, SendGrid, SES)
- SMS providers (Twilio, SNS)
- Push providers (FCM, APNS)
- In-app provider
"""

from src.notifications.providers.base import (
    NotificationProvider,
    ProviderResult,
    ProviderError,
    ProviderConnectionError,
    ProviderAuthenticationError,
    ProviderRateLimitError,
    ProviderValidationError,
)

from src.notifications.providers.email import (
    EmailProvider,
    SMTPProvider,
    SendGridProvider,
    SESProvider,
)

from src.notifications.providers.sms import (
    SMSProvider,
    TwilioProvider,
    SNSSMSProvider,
)

from src.notifications.providers.push import (
    PushProvider,
    FCMProvider,
    APNSProvider,
)

from src.notifications.providers.inapp import InAppProvider

__all__ = [
    # Base
    "NotificationProvider",
    "ProviderResult",
    "ProviderError",
    "ProviderConnectionError",
    "ProviderAuthenticationError",
    "ProviderRateLimitError",
    "ProviderValidationError",
    # Email
    "EmailProvider",
    "SMTPProvider",
    "SendGridProvider",
    "SESProvider",
    # SMS
    "SMSProvider",
    "TwilioProvider",
    "SNSSMSProvider",
    # Push
    "PushProvider",
    "FCMProvider",
    "APNSProvider",
    # In-App
    "InAppProvider",
]
