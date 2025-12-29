"""
SMS Notification Providers.

Provides SMS delivery via:
- Twilio
- Amazon SNS
"""

import asyncio
from typing import Any, Dict, List, Optional

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
    ProviderValidationError,
)


class SMSProvider(NotificationProvider):
    """Base class for SMS providers."""

    notification_types = [NotificationType.SMS]

    def validate_notification(self, notification: Notification) -> None:
        """Validate SMS notification."""
        super().validate_notification(notification)

        if not notification.recipient.phone:
            raise ProviderValidationError(
                "Recipient phone number is required",
                field="recipient.phone",
            )

        if not notification.content.body:
            raise ProviderValidationError(
                "SMS body is required",
                field="content.body",
            )


class TwilioProvider(SMSProvider):
    """Twilio SMS provider."""

    provider_type = ChannelType.TWILIO

    async def send(self, notification: Notification) -> ProviderResult:
        """Send SMS via Twilio."""
        self.validate_notification(notification)

        account_sid = self.get_settings("account_sid")
        auth_token = self.get_settings("auth_token")
        from_number = self.get_settings("from_number")

        if not all([account_sid, auth_token, from_number]):
            return ProviderResult.error_result(
                error_code="CONFIG_ERROR",
                error_message="Twilio credentials not configured",
                retryable=False,
            )

        body = notification.content.get_sms_body()

        try:
            import aiohttp
            from aiohttp import BasicAuth

            url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    data={
                        "To": notification.recipient.phone,
                        "From": from_number,
                        "Body": body,
                    },
                    auth=BasicAuth(account_sid, auth_token),
                ) as response:
                    response_data = await response.json()

                    if response.status == 201:
                        return ProviderResult.success_result(
                            provider_message_id=response_data.get("sid"),
                            response_data=response_data,
                        )
                    elif response.status == 401:
                        return ProviderResult.error_result(
                            error_code="AUTH_ERROR",
                            error_message="Invalid credentials",
                            retryable=False,
                        )
                    elif response.status == 429:
                        return ProviderResult.error_result(
                            error_code="RATE_LIMIT",
                            error_message="Rate limit exceeded",
                            retryable=True,
                        )
                    else:
                        error_msg = response_data.get("message", "Unknown error")
                        error_code = response_data.get("code", response.status)
                        return ProviderResult.error_result(
                            error_code=str(error_code),
                            error_message=error_msg,
                            retryable=response.status >= 500,
                            response_data=response_data,
                        )

        except ImportError:
            return ProviderResult.error_result(
                error_code="DEPENDENCY_ERROR",
                error_message="aiohttp is required for Twilio provider",
                retryable=False,
            )
        except Exception as e:
            return ProviderResult.error_result(
                error_code="SEND_ERROR",
                error_message=str(e),
                retryable=True,
            )

    async def check_status(
        self,
        provider_message_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Check SMS delivery status."""
        account_sid = self.get_settings("account_sid")
        auth_token = self.get_settings("auth_token")

        if not account_sid or not auth_token:
            return None

        try:
            import aiohttp
            from aiohttp import BasicAuth

            url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages/{provider_message_id}.json"

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    auth=BasicAuth(account_sid, auth_token),
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    return None

        except Exception:
            return None


class SNSSMSProvider(SMSProvider):
    """Amazon SNS SMS provider."""

    provider_type = ChannelType.SNS

    async def send(self, notification: Notification) -> ProviderResult:
        """Send SMS via Amazon SNS."""
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

        body = notification.content.get_sms_body()
        sender_id = self.get_settings("sender_id")

        try:
            import boto3
            from botocore.exceptions import ClientError

            # Create SNS client
            client = boto3.client(
                "sns",
                region_name=region,
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
            )

            # Build message attributes
            attributes = {}

            if sender_id:
                attributes["AWS.SNS.SMS.SenderID"] = {
                    "DataType": "String",
                    "StringValue": sender_id,
                }

            # Set SMS type based on priority
            sms_type = "Transactional"  # or "Promotional"
            if notification.category.value == "marketing":
                sms_type = "Promotional"

            attributes["AWS.SNS.SMS.SMSType"] = {
                "DataType": "String",
                "StringValue": sms_type,
            }

            # Run in thread pool
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: client.publish(
                    PhoneNumber=notification.recipient.phone,
                    Message=body,
                    MessageAttributes=attributes,
                ),
            )

            return ProviderResult.success_result(
                provider_message_id=response.get("MessageId"),
                response_data={"response": response},
            )

        except ImportError:
            return ProviderResult.error_result(
                error_code="DEPENDENCY_ERROR",
                error_message="boto3 is required for SNS provider",
                retryable=False,
            )
        except Exception as e:
            error_code = "SEND_ERROR"
            retryable = True

            if "InvalidParameter" in str(e):
                error_code = "VALIDATION_ERROR"
                retryable = False
            elif "AuthorizationError" in str(e):
                error_code = "AUTH_ERROR"
                retryable = False
            elif "Throttling" in str(e):
                error_code = "RATE_LIMIT"
                retryable = True

            return ProviderResult.error_result(
                error_code=error_code,
                error_message=str(e),
                retryable=retryable,
            )
