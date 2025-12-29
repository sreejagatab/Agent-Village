"""
Push Notification Providers.

Provides push delivery via:
- Firebase Cloud Messaging (FCM)
- Apple Push Notification Service (APNS)
"""

import asyncio
import json
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


class PushProvider(NotificationProvider):
    """Base class for push notification providers."""

    notification_types = [NotificationType.PUSH]

    def validate_notification(self, notification: Notification) -> None:
        """Validate push notification."""
        super().validate_notification(notification)

        if not notification.recipient.device_tokens:
            raise ProviderValidationError(
                "At least one device token is required",
                field="recipient.device_tokens",
            )

        if not notification.content.title:
            raise ProviderValidationError(
                "Push notification title is required",
                field="content.title",
            )

        if not notification.content.body:
            raise ProviderValidationError(
                "Push notification body is required",
                field="content.body",
            )


class FCMProvider(PushProvider):
    """Firebase Cloud Messaging provider."""

    provider_type = ChannelType.FCM

    async def send(self, notification: Notification) -> ProviderResult:
        """Send push notification via FCM."""
        self.validate_notification(notification)

        # Support both legacy and HTTP v1 API
        api_key = self.get_settings("api_key")  # Legacy
        service_account = self.get_settings("service_account")  # HTTP v1
        project_id = self.get_settings("project_id")

        if service_account and project_id:
            return await self._send_v1(notification, service_account, project_id)
        elif api_key:
            return await self._send_legacy(notification, api_key)
        else:
            return ProviderResult.error_result(
                error_code="CONFIG_ERROR",
                error_message="FCM credentials not configured",
                retryable=False,
            )

    async def _send_legacy(
        self,
        notification: Notification,
        api_key: str,
    ) -> ProviderResult:
        """Send using legacy FCM API."""
        # Build payload
        payload = {
            "notification": {
                "title": notification.content.title,
                "body": notification.content.body,
            },
            "data": notification.content.data,
        }

        if notification.content.image_url:
            payload["notification"]["image"] = notification.content.image_url

        if notification.content.sound:
            payload["notification"]["sound"] = notification.content.sound

        # Send to multiple tokens
        tokens = notification.recipient.device_tokens
        if len(tokens) == 1:
            payload["to"] = tokens[0]
        else:
            payload["registration_ids"] = tokens

        try:
            import aiohttp

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://fcm.googleapis.com/fcm/send",
                    json=payload,
                    headers={
                        "Authorization": f"key={api_key}",
                        "Content-Type": "application/json",
                    },
                ) as response:
                    response_data = await response.json()

                    if response.status == 200:
                        success_count = response_data.get("success", 0)
                        failure_count = response_data.get("failure", 0)

                        if success_count > 0:
                            return ProviderResult.success_result(
                                provider_message_id=str(response_data.get("multicast_id")),
                                response_data={
                                    "success_count": success_count,
                                    "failure_count": failure_count,
                                    "results": response_data.get("results", []),
                                },
                            )
                        else:
                            error_msg = "All tokens failed"
                            results = response_data.get("results", [])
                            if results:
                                error_msg = results[0].get("error", error_msg)
                            return ProviderResult.error_result(
                                error_code="DELIVERY_FAILED",
                                error_message=error_msg,
                                retryable=False,
                                response_data=response_data,
                            )
                    elif response.status == 401:
                        return ProviderResult.error_result(
                            error_code="AUTH_ERROR",
                            error_message="Invalid API key",
                            retryable=False,
                        )
                    else:
                        return ProviderResult.error_result(
                            error_code=f"HTTP_{response.status}",
                            error_message=await response.text(),
                            retryable=response.status >= 500,
                        )

        except ImportError:
            return ProviderResult.error_result(
                error_code="DEPENDENCY_ERROR",
                error_message="aiohttp is required for FCM provider",
                retryable=False,
            )
        except Exception as e:
            return ProviderResult.error_result(
                error_code="SEND_ERROR",
                error_message=str(e),
                retryable=True,
            )

    async def _send_v1(
        self,
        notification: Notification,
        service_account: Dict[str, Any],
        project_id: str,
    ) -> ProviderResult:
        """Send using FCM HTTP v1 API."""
        try:
            import aiohttp
            from google.oauth2 import service_account as sa
            from google.auth.transport.requests import Request

            # Get access token
            credentials = sa.Credentials.from_service_account_info(
                service_account,
                scopes=["https://www.googleapis.com/auth/firebase.messaging"],
            )

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: credentials.refresh(Request()),
            )

            access_token = credentials.token

            # Send to each token (HTTP v1 API doesn't support multicast)
            results = []
            for token in notification.recipient.device_tokens:
                payload = {
                    "message": {
                        "token": token,
                        "notification": {
                            "title": notification.content.title,
                            "body": notification.content.body,
                        },
                        "data": {k: str(v) for k, v in notification.content.data.items()},
                    }
                }

                if notification.content.image_url:
                    payload["message"]["notification"]["image"] = notification.content.image_url

                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        f"https://fcm.googleapis.com/v1/projects/{project_id}/messages:send",
                        json=payload,
                        headers={
                            "Authorization": f"Bearer {access_token}",
                            "Content-Type": "application/json",
                        },
                    ) as response:
                        resp_data = await response.json()
                        results.append({
                            "token": token,
                            "status": response.status,
                            "response": resp_data,
                        })

            # Check results
            successes = [r for r in results if r["status"] == 200]
            if successes:
                return ProviderResult.success_result(
                    provider_message_id=successes[0]["response"].get("name"),
                    response_data={
                        "success_count": len(successes),
                        "failure_count": len(results) - len(successes),
                        "results": results,
                    },
                )
            else:
                return ProviderResult.error_result(
                    error_code="DELIVERY_FAILED",
                    error_message="All tokens failed",
                    retryable=False,
                    response_data={"results": results},
                )

        except ImportError as e:
            missing = "google-auth" if "google" in str(e) else "aiohttp"
            return ProviderResult.error_result(
                error_code="DEPENDENCY_ERROR",
                error_message=f"{missing} is required for FCM v1 provider",
                retryable=False,
            )
        except Exception as e:
            return ProviderResult.error_result(
                error_code="SEND_ERROR",
                error_message=str(e),
                retryable=True,
            )


class APNSProvider(PushProvider):
    """Apple Push Notification Service provider."""

    provider_type = ChannelType.APNS

    async def send(self, notification: Notification) -> ProviderResult:
        """Send push notification via APNS."""
        self.validate_notification(notification)

        # APNS can use either JWT or certificate authentication
        key_id = self.get_settings("key_id")
        team_id = self.get_settings("team_id")
        private_key = self.get_settings("private_key")
        bundle_id = self.get_settings("bundle_id")
        use_sandbox = self.get_settings("use_sandbox", False)

        if not all([key_id, team_id, private_key, bundle_id]):
            return ProviderResult.error_result(
                error_code="CONFIG_ERROR",
                error_message="APNS credentials not configured",
                retryable=False,
            )

        # Build APNS payload
        aps = {
            "alert": {
                "title": notification.content.title,
                "body": notification.content.body,
            },
        }

        if notification.content.badge is not None:
            aps["badge"] = notification.content.badge

        if notification.content.sound:
            aps["sound"] = notification.content.sound

        payload = {
            "aps": aps,
            **notification.content.data,
        }

        try:
            import jwt
            import aiohttp
            import time

            # Generate JWT token
            token = jwt.encode(
                {
                    "iss": team_id,
                    "iat": int(time.time()),
                },
                private_key,
                algorithm="ES256",
                headers={
                    "alg": "ES256",
                    "kid": key_id,
                },
            )

            # Determine environment
            if use_sandbox:
                host = "api.sandbox.push.apple.com"
            else:
                host = "api.push.apple.com"

            # Send to each device token
            results = []
            for device_token in notification.recipient.device_tokens:
                url = f"https://{host}/3/device/{device_token}"

                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        url,
                        json=payload,
                        headers={
                            "Authorization": f"bearer {token}",
                            "apns-topic": bundle_id,
                            "apns-push-type": "alert",
                        },
                    ) as response:
                        if response.status == 200:
                            apns_id = response.headers.get("apns-id")
                            results.append({
                                "token": device_token,
                                "success": True,
                                "apns_id": apns_id,
                            })
                        else:
                            resp_data = await response.json()
                            results.append({
                                "token": device_token,
                                "success": False,
                                "error": resp_data.get("reason"),
                            })

            # Check results
            successes = [r for r in results if r.get("success")]
            if successes:
                return ProviderResult.success_result(
                    provider_message_id=successes[0].get("apns_id"),
                    response_data={
                        "success_count": len(successes),
                        "failure_count": len(results) - len(successes),
                        "results": results,
                    },
                )
            else:
                error_msg = results[0].get("error", "Unknown error") if results else "No results"
                return ProviderResult.error_result(
                    error_code="DELIVERY_FAILED",
                    error_message=error_msg,
                    retryable=False,
                    response_data={"results": results},
                )

        except ImportError as e:
            missing = "PyJWT" if "jwt" in str(e) else "aiohttp"
            return ProviderResult.error_result(
                error_code="DEPENDENCY_ERROR",
                error_message=f"{missing} is required for APNS provider",
                retryable=False,
            )
        except Exception as e:
            return ProviderResult.error_result(
                error_code="SEND_ERROR",
                error_message=str(e),
                retryable=True,
            )
