"""
Email Notification Providers.

Provides email delivery via:
- SMTP
- SendGrid
- Amazon SES
"""

import asyncio
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Any, Dict, List, Optional
import json

from src.notifications.models import (
    Notification,
    NotificationType,
    ChannelType,
    ChannelConfig,
)
from src.notifications.providers.base import (
    NotificationProvider,
    ProviderResult,
    ProviderError,
    ProviderConnectionError,
    ProviderAuthenticationError,
    ProviderValidationError,
)


class EmailProvider(NotificationProvider):
    """Base class for email providers."""

    notification_types = [NotificationType.EMAIL]

    def validate_notification(self, notification: Notification) -> None:
        """Validate email notification."""
        super().validate_notification(notification)

        if not notification.recipient.email:
            raise ProviderValidationError(
                "Recipient email address is required",
                field="recipient.email",
            )

        if not notification.content.subject:
            raise ProviderValidationError(
                "Email subject is required",
                field="content.subject",
            )

        if not notification.content.body and not notification.content.html_body:
            raise ProviderValidationError(
                "Email body is required",
                field="content.body",
            )


class SMTPProvider(EmailProvider):
    """SMTP email provider."""

    provider_type = ChannelType.SMTP

    def __init__(self, config: Optional[ChannelConfig] = None):
        super().__init__(config)
        self._connection: Optional[smtplib.SMTP] = None

    async def initialize(self) -> None:
        """Initialize SMTP connection."""
        await super().initialize()
        # Connection is established per-send for simplicity
        # For production, consider connection pooling

    async def shutdown(self) -> None:
        """Close SMTP connection."""
        if self._connection:
            try:
                self._connection.quit()
            except Exception:
                pass
            self._connection = None
        await super().shutdown()

    def _get_connection(self) -> smtplib.SMTP:
        """Get or create SMTP connection."""
        host = self.get_settings("host", "localhost")
        port = self.get_settings("port", 587)
        use_tls = self.get_settings("use_tls", True)
        username = self.get_settings("username")
        password = self.get_settings("password")

        try:
            if use_tls:
                connection = smtplib.SMTP(host, port)
                context = ssl.create_default_context()
                connection.starttls(context=context)
            else:
                connection = smtplib.SMTP(host, port)

            if username and password:
                connection.login(username, password)

            return connection
        except smtplib.SMTPAuthenticationError as e:
            raise ProviderAuthenticationError(str(e))
        except Exception as e:
            raise ProviderConnectionError(str(e))

    async def send(self, notification: Notification) -> ProviderResult:
        """Send email via SMTP."""
        self.validate_notification(notification)

        from_email = self.get_settings("from_email", "noreply@example.com")
        from_name = self.get_settings("from_name", "Notifications")

        # Build message
        if notification.content.html_body:
            msg = MIMEMultipart("alternative")
            msg.attach(MIMEText(notification.content.body, "plain"))
            msg.attach(MIMEText(notification.content.html_body, "html"))
        else:
            msg = MIMEText(notification.content.body, "plain")

        msg["Subject"] = notification.content.subject
        msg["From"] = f"{from_name} <{from_email}>"
        msg["To"] = notification.recipient.email

        # Add reply-to if configured
        reply_to = self.get_settings("reply_to")
        if reply_to:
            msg["Reply-To"] = reply_to

        try:
            # Run SMTP in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self._send_sync,
                msg,
                from_email,
                notification.recipient.email,
            )
            return result
        except ProviderError:
            raise
        except Exception as e:
            return ProviderResult.error_result(
                error_code="SEND_ERROR",
                error_message=str(e),
                retryable=True,
            )

    def _send_sync(
        self,
        msg: MIMEText,
        from_email: str,
        to_email: str,
    ) -> ProviderResult:
        """Synchronous send (runs in thread pool)."""
        try:
            connection = self._get_connection()
            connection.sendmail(from_email, [to_email], msg.as_string())
            connection.quit()

            return ProviderResult.success_result(
                response_data={"method": "smtp"}
            )
        except ProviderError:
            raise
        except Exception as e:
            return ProviderResult.error_result(
                error_code="SEND_ERROR",
                error_message=str(e),
                retryable=True,
            )


class SendGridProvider(EmailProvider):
    """SendGrid email provider."""

    provider_type = ChannelType.SENDGRID

    async def send(self, notification: Notification) -> ProviderResult:
        """Send email via SendGrid API."""
        self.validate_notification(notification)

        api_key = self.get_settings("api_key")
        if not api_key:
            return ProviderResult.error_result(
                error_code="CONFIG_ERROR",
                error_message="SendGrid API key not configured",
                retryable=False,
            )

        from_email = self.get_settings("from_email", "noreply@example.com")
        from_name = self.get_settings("from_name", "Notifications")

        # Build request payload
        payload = {
            "personalizations": [{
                "to": [{"email": notification.recipient.email}],
                "subject": notification.content.subject,
            }],
            "from": {
                "email": from_email,
                "name": from_name,
            },
            "content": [],
        }

        if notification.content.body:
            payload["content"].append({
                "type": "text/plain",
                "value": notification.content.body,
            })

        if notification.content.html_body:
            payload["content"].append({
                "type": "text/html",
                "value": notification.content.html_body,
            })

        try:
            import aiohttp

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://api.sendgrid.com/v3/mail/send",
                    json=payload,
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                ) as response:
                    if response.status == 202:
                        message_id = response.headers.get("X-Message-Id")
                        return ProviderResult.success_result(
                            provider_message_id=message_id,
                            response_data={"status": response.status},
                        )
                    elif response.status == 401:
                        return ProviderResult.error_result(
                            error_code="AUTH_ERROR",
                            error_message="Invalid API key",
                            retryable=False,
                        )
                    elif response.status == 429:
                        return ProviderResult.error_result(
                            error_code="RATE_LIMIT",
                            error_message="Rate limit exceeded",
                            retryable=True,
                        )
                    else:
                        body = await response.text()
                        return ProviderResult.error_result(
                            error_code=f"HTTP_{response.status}",
                            error_message=body,
                            retryable=response.status >= 500,
                        )

        except ImportError:
            return ProviderResult.error_result(
                error_code="DEPENDENCY_ERROR",
                error_message="aiohttp is required for SendGrid provider",
                retryable=False,
            )
        except Exception as e:
            return ProviderResult.error_result(
                error_code="SEND_ERROR",
                error_message=str(e),
                retryable=True,
            )


class SESProvider(EmailProvider):
    """Amazon SES email provider."""

    provider_type = ChannelType.SES

    async def send(self, notification: Notification) -> ProviderResult:
        """Send email via Amazon SES."""
        self.validate_notification(notification)

        region = self.get_settings("region", "us-east-1")
        access_key = self.get_settings("access_key")
        secret_key = self.get_settings("secret_key")

        if not access_key or not secret_key:
            return ProviderResult.error_result(
                error_code="CONFIG_ERROR",
                error_message="AWS credentials not configured",
                retryable=False,
            )

        from_email = self.get_settings("from_email", "noreply@example.com")

        try:
            import boto3
            from botocore.exceptions import ClientError

            # Create SES client
            client = boto3.client(
                "ses",
                region_name=region,
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
            )

            # Build email
            body = {}
            if notification.content.body:
                body["Text"] = {"Data": notification.content.body}
            if notification.content.html_body:
                body["Html"] = {"Data": notification.content.html_body}

            # Run in thread pool
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: client.send_email(
                    Source=from_email,
                    Destination={"ToAddresses": [notification.recipient.email]},
                    Message={
                        "Subject": {"Data": notification.content.subject},
                        "Body": body,
                    },
                ),
            )

            return ProviderResult.success_result(
                provider_message_id=response.get("MessageId"),
                response_data={"response": response},
            )

        except ImportError:
            return ProviderResult.error_result(
                error_code="DEPENDENCY_ERROR",
                error_message="boto3 is required for SES provider",
                retryable=False,
            )
        except Exception as e:
            error_code = "SEND_ERROR"
            retryable = True

            if "InvalidParameterValue" in str(e):
                error_code = "VALIDATION_ERROR"
                retryable = False
            elif "AccessDenied" in str(e):
                error_code = "AUTH_ERROR"
                retryable = False

            return ProviderResult.error_result(
                error_code=error_code,
                error_message=str(e),
                retryable=retryable,
            )
