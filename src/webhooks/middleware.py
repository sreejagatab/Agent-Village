"""
Webhook Middleware and Routes.

Provides FastAPI routes and utilities for webhook management.
"""

from dataclasses import dataclass, field
from functools import wraps
from typing import Optional, Callable, List

from fastapi import FastAPI, Request, Response, HTTPException, APIRouter, Query, Body
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from src.webhooks.models import (
    WebhookEndpoint,
    WebhookEvent,
    WebhookStatus,
    DeliveryStatus,
    EventType,
    WebhookConfig,
)
from src.webhooks.service import (
    WebhookService,
    WebhookNotFoundError,
    WebhookDisabledError,
    WebhookLimitExceededError,
    DeliveryNotFoundError,
)


# ==================== Pydantic Models ====================


class WebhookCreateRequest(BaseModel):
    """Request to create a webhook."""
    url: str = Field(..., description="Webhook endpoint URL")
    name: Optional[str] = Field(None, description="Webhook name")
    description: Optional[str] = Field(None, description="Webhook description")
    events: Optional[List[str]] = Field(None, description="Event types to subscribe to")
    filters: Optional[dict] = Field(None, description="Event filters")
    custom_headers: Optional[dict] = Field(None, description="Custom HTTP headers")
    timeout_seconds: Optional[int] = Field(None, ge=1, le=120, description="Request timeout")
    max_retries: Optional[int] = Field(None, ge=0, le=10, description="Max retry attempts")


class WebhookUpdateRequest(BaseModel):
    """Request to update a webhook."""
    url: Optional[str] = Field(None, description="Webhook endpoint URL")
    name: Optional[str] = Field(None, description="Webhook name")
    description: Optional[str] = Field(None, description="Webhook description")
    events: Optional[List[str]] = Field(None, description="Event types to subscribe to")
    filters: Optional[dict] = Field(None, description="Event filters")
    custom_headers: Optional[dict] = Field(None, description="Custom HTTP headers")
    timeout_seconds: Optional[int] = Field(None, ge=1, le=120, description="Request timeout")
    max_retries: Optional[int] = Field(None, ge=0, le=10, description="Max retry attempts")
    status: Optional[str] = Field(None, description="Webhook status")


class EventPublishRequest(BaseModel):
    """Request to publish an event."""
    event_type: str = Field(..., description="Event type")
    data: dict = Field(..., description="Event data")
    user_id: Optional[str] = Field(None, description="User ID")
    correlation_id: Optional[str] = Field(None, description="Correlation ID")


class WebhookVerifyRequest(BaseModel):
    """Request to verify webhook signature."""
    payload: str = Field(..., description="Raw payload string")
    signature: str = Field(..., description="Signature header value")


# ==================== Event Publisher Decorator ====================


def publish_webhook_event(
    event_type: EventType,
    data_extractor: Optional[Callable] = None,
):
    """
    Decorator to automatically publish webhook events.

    Usage:
        @app.post("/goals")
        @publish_webhook_event(EventType.GOAL_CREATED, lambda result: {"goal_id": result["id"]})
        async def create_goal(request: Request):
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)

            # Get webhook service from request state
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break

            if request and hasattr(request.state, "webhook_service"):
                service = request.state.webhook_service

                # Extract data
                if data_extractor:
                    data = data_extractor(result)
                elif isinstance(result, dict):
                    data = result
                else:
                    data = {"result": str(result)}

                # Get tenant and user from request
                tenant_id = getattr(request.state, "tenant_id", None)
                user_id = getattr(request.state, "user_id", None)

                try:
                    await service.publish_event(
                        event_type=event_type,
                        data=data,
                        tenant_id=tenant_id,
                        user_id=user_id,
                    )
                except Exception as e:
                    # Log but don't fail the request
                    import logging
                    logging.error(f"Failed to publish webhook event: {e}")

            return result
        return wrapper
    return decorator


# ==================== Route Handlers ====================


def create_webhook_routes(
    webhook_service: WebhookService,
    prefix: str = "",
    tags: list[str] = None,
    require_auth: bool = True,
) -> APIRouter:
    """
    Create FastAPI router with webhook management endpoints.

    Endpoints:
    - POST /webhooks - Create a webhook
    - GET /webhooks - List webhooks
    - GET /webhooks/{webhook_id} - Get webhook details
    - PATCH /webhooks/{webhook_id} - Update webhook
    - DELETE /webhooks/{webhook_id} - Delete webhook
    - POST /webhooks/{webhook_id}/test - Test webhook
    - POST /webhooks/{webhook_id}/rotate-secret - Rotate secret
    - POST /webhooks/{webhook_id}/pause - Pause webhook
    - POST /webhooks/{webhook_id}/resume - Resume webhook
    - GET /webhooks/{webhook_id}/deliveries - List deliveries
    - GET /webhooks/{webhook_id}/stats - Get statistics
    """
    router = APIRouter(prefix=prefix, tags=tags or ["Webhooks"])

    def get_owner_id(request: Request) -> str:
        """Get owner ID from request."""
        if hasattr(request.state, "user_id"):
            return request.state.user_id
        raise HTTPException(status_code=401, detail="Authentication required")

    def get_tenant_id(request: Request) -> Optional[str]:
        """Get tenant ID from request."""
        return getattr(request.state, "tenant_id", None)

    @router.post("")
    async def create_webhook(
        request: Request,
        body: WebhookCreateRequest,
    ):
        """Create a new webhook endpoint."""
        owner_id = get_owner_id(request)
        tenant_id = get_tenant_id(request)

        # Parse events
        events = None
        if body.events:
            try:
                events = [EventType(e) for e in body.events]
            except ValueError as e:
                raise HTTPException(status_code=400, detail=f"Invalid event type: {e}")

        try:
            webhook, secret = await webhook_service.create_webhook(
                url=body.url,
                owner_id=owner_id,
                events=events,
                name=body.name,
                description=body.description,
                tenant_id=tenant_id,
                filters=body.filters,
                custom_headers=body.custom_headers,
                timeout_seconds=body.timeout_seconds,
                max_retries=body.max_retries,
            )

            return JSONResponse(
                status_code=201,
                content={
                    "webhook_id": webhook.webhook_id,
                    "secret": secret,
                    "url": webhook.url,
                    "events": [e.value for e in webhook.events],
                    "message": "Store the webhook secret securely. It won't be shown again.",
                },
            )

        except WebhookLimitExceededError as e:
            raise HTTPException(status_code=429, detail=str(e))

    @router.get("")
    async def list_webhooks(
        request: Request,
        include_disabled: bool = Query(False),
        page: int = Query(1, ge=1),
        per_page: int = Query(20, ge=1, le=100),
    ):
        """List webhooks for the authenticated user."""
        owner_id = get_owner_id(request)

        result = await webhook_service.list_webhooks(
            owner_id=owner_id,
            include_disabled=include_disabled,
            page=page,
            per_page=per_page,
        )

        return {
            "webhooks": [w.to_dict() for w in result.webhooks],
            "total": result.total,
            "page": result.page,
            "per_page": result.per_page,
        }

    @router.get("/{webhook_id}")
    async def get_webhook(
        request: Request,
        webhook_id: str,
    ):
        """Get webhook details."""
        owner_id = get_owner_id(request)

        try:
            webhook = await webhook_service.get_webhook(webhook_id)

            # Verify ownership
            if webhook.owner_id != owner_id:
                raise HTTPException(status_code=403, detail="Access denied")

            return webhook.to_dict()

        except WebhookNotFoundError:
            raise HTTPException(status_code=404, detail="Webhook not found")

    @router.patch("/{webhook_id}")
    async def update_webhook(
        request: Request,
        webhook_id: str,
        body: WebhookUpdateRequest,
    ):
        """Update a webhook."""
        owner_id = get_owner_id(request)

        try:
            webhook = await webhook_service.get_webhook(webhook_id)

            if webhook.owner_id != owner_id:
                raise HTTPException(status_code=403, detail="Access denied")

            # Parse events
            events = None
            if body.events:
                try:
                    events = [EventType(e) for e in body.events]
                except ValueError as e:
                    raise HTTPException(status_code=400, detail=f"Invalid event type: {e}")

            # Parse status
            status = None
            if body.status:
                try:
                    status = WebhookStatus(body.status)
                except ValueError:
                    raise HTTPException(status_code=400, detail="Invalid status")

            webhook = await webhook_service.update_webhook(
                webhook_id=webhook_id,
                url=body.url,
                name=body.name,
                description=body.description,
                events=events,
                filters=body.filters,
                custom_headers=body.custom_headers,
                timeout_seconds=body.timeout_seconds,
                max_retries=body.max_retries,
                status=status,
            )

            return webhook.to_dict()

        except WebhookNotFoundError:
            raise HTTPException(status_code=404, detail="Webhook not found")

    @router.delete("/{webhook_id}")
    async def delete_webhook(
        request: Request,
        webhook_id: str,
    ):
        """Delete a webhook."""
        owner_id = get_owner_id(request)

        try:
            webhook = await webhook_service.get_webhook(webhook_id)

            if webhook.owner_id != owner_id:
                raise HTTPException(status_code=403, detail="Access denied")

            result = await webhook_service.delete_webhook(webhook_id)

            return {"success": result, "message": "Webhook deleted"}

        except WebhookNotFoundError:
            raise HTTPException(status_code=404, detail="Webhook not found")

    @router.post("/{webhook_id}/test")
    async def test_webhook(
        request: Request,
        webhook_id: str,
    ):
        """Send a test ping to the webhook."""
        owner_id = get_owner_id(request)

        try:
            webhook = await webhook_service.get_webhook(webhook_id)

            if webhook.owner_id != owner_id:
                raise HTTPException(status_code=403, detail="Access denied")

            result = await webhook_service.test_webhook(webhook_id)

            return result.to_dict()

        except WebhookNotFoundError:
            raise HTTPException(status_code=404, detail="Webhook not found")

    @router.post("/{webhook_id}/rotate-secret")
    async def rotate_secret(
        request: Request,
        webhook_id: str,
    ):
        """Rotate the webhook secret."""
        owner_id = get_owner_id(request)

        try:
            webhook = await webhook_service.get_webhook(webhook_id)

            if webhook.owner_id != owner_id:
                raise HTTPException(status_code=403, detail="Access denied")

            webhook, new_secret = await webhook_service.rotate_secret(webhook_id)

            return {
                "webhook_id": webhook_id,
                "secret": new_secret,
                "message": "Store the new secret securely.",
            }

        except WebhookNotFoundError:
            raise HTTPException(status_code=404, detail="Webhook not found")

    @router.post("/{webhook_id}/pause")
    async def pause_webhook(
        request: Request,
        webhook_id: str,
    ):
        """Pause webhook deliveries."""
        owner_id = get_owner_id(request)

        try:
            webhook = await webhook_service.get_webhook(webhook_id)

            if webhook.owner_id != owner_id:
                raise HTTPException(status_code=403, detail="Access denied")

            webhook = await webhook_service.pause_webhook(webhook_id)

            return {
                "success": True,
                "status": webhook.status.value,
                "message": "Webhook paused",
            }

        except WebhookNotFoundError:
            raise HTTPException(status_code=404, detail="Webhook not found")

    @router.post("/{webhook_id}/resume")
    async def resume_webhook(
        request: Request,
        webhook_id: str,
    ):
        """Resume webhook deliveries."""
        owner_id = get_owner_id(request)

        try:
            webhook = await webhook_service.get_webhook(webhook_id)

            if webhook.owner_id != owner_id:
                raise HTTPException(status_code=403, detail="Access denied")

            webhook = await webhook_service.resume_webhook(webhook_id)

            return {
                "success": True,
                "status": webhook.status.value,
                "message": "Webhook resumed",
            }

        except WebhookNotFoundError:
            raise HTTPException(status_code=404, detail="Webhook not found")

    @router.get("/{webhook_id}/deliveries")
    async def list_deliveries(
        request: Request,
        webhook_id: str,
        status: Optional[str] = Query(None),
        page: int = Query(1, ge=1),
        per_page: int = Query(20, ge=1, le=100),
    ):
        """List deliveries for a webhook."""
        owner_id = get_owner_id(request)

        try:
            webhook = await webhook_service.get_webhook(webhook_id)

            if webhook.owner_id != owner_id:
                raise HTTPException(status_code=403, detail="Access denied")

            # Parse status
            delivery_status = None
            if status:
                try:
                    delivery_status = DeliveryStatus(status)
                except ValueError:
                    raise HTTPException(status_code=400, detail="Invalid status")

            result = await webhook_service.list_deliveries(
                webhook_id=webhook_id,
                status=delivery_status,
                page=page,
                per_page=per_page,
            )

            return {
                "deliveries": [d.to_dict() for d in result.deliveries],
                "total": result.total,
                "page": result.page,
                "per_page": result.per_page,
            }

        except WebhookNotFoundError:
            raise HTTPException(status_code=404, detail="Webhook not found")

    @router.post("/{webhook_id}/deliveries/{delivery_id}/retry")
    async def retry_delivery(
        request: Request,
        webhook_id: str,
        delivery_id: str,
    ):
        """Retry a failed delivery."""
        owner_id = get_owner_id(request)

        try:
            webhook = await webhook_service.get_webhook(webhook_id)

            if webhook.owner_id != owner_id:
                raise HTTPException(status_code=403, detail="Access denied")

            delivery = await webhook_service.retry_delivery(delivery_id)

            return {
                "success": True,
                "delivery": delivery.to_dict(),
            }

        except WebhookNotFoundError:
            raise HTTPException(status_code=404, detail="Webhook not found")
        except DeliveryNotFoundError:
            raise HTTPException(status_code=404, detail="Delivery not found")

    @router.get("/{webhook_id}/stats")
    async def get_webhook_stats(
        request: Request,
        webhook_id: str,
    ):
        """Get webhook statistics."""
        owner_id = get_owner_id(request)

        try:
            webhook = await webhook_service.get_webhook(webhook_id)

            if webhook.owner_id != owner_id:
                raise HTTPException(status_code=403, detail="Access denied")

            stats = await webhook_service.get_webhook_stats(webhook_id)

            return stats

        except WebhookNotFoundError:
            raise HTTPException(status_code=404, detail="Webhook not found")

    return router


def create_webhook_admin_routes(
    webhook_service: WebhookService,
    prefix: str = "",
    tags: list[str] = None,
) -> APIRouter:
    """Create admin routes for webhook management."""
    router = APIRouter(prefix=prefix, tags=tags or ["Webhook Admin"])

    @router.post("/events/publish")
    async def publish_event(
        request: Request,
        body: EventPublishRequest,
    ):
        """Publish an event to all subscribed webhooks."""
        try:
            event_type = EventType(body.event_type)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid event type")

        tenant_id = getattr(request.state, "tenant_id", None)

        deliveries = await webhook_service.publish_event(
            event_type=event_type,
            data=body.data,
            tenant_id=tenant_id,
            user_id=body.user_id,
            correlation_id=body.correlation_id,
        )

        return {
            "success": True,
            "delivery_count": len(deliveries),
            "deliveries": [d.delivery_id for d in deliveries],
        }

    @router.get("/events/types")
    async def list_event_types():
        """List all available event types."""
        return {
            "event_types": [
                {
                    "value": e.value,
                    "name": e.name,
                }
                for e in EventType
            ],
        }

    @router.post("/cleanup")
    async def cleanup_deliveries(
        days: int = Query(30, ge=1, le=365),
    ):
        """Clean up old deliveries."""
        count = await webhook_service.cleanup_old_deliveries(days=days)

        return {
            "success": True,
            "cleaned_count": count,
        }

    @router.get("/webhooks/all")
    async def list_all_webhooks(
        tenant_id: Optional[str] = Query(None),
        page: int = Query(1, ge=1),
        per_page: int = Query(50, ge=1, le=200),
    ):
        """List all webhooks (admin only)."""
        if tenant_id:
            webhooks = await webhook_service.store.get_webhooks_by_tenant(
                tenant_id,
                include_disabled=True,
            )
        else:
            webhooks = list(webhook_service.store._webhooks.values())

        # Paginate
        start = (page - 1) * per_page
        end = start + per_page

        return {
            "webhooks": [w.to_dict() for w in webhooks[start:end]],
            "total": len(webhooks),
            "page": page,
            "per_page": per_page,
        }

    @router.post("/webhooks/{webhook_id}/disable")
    async def admin_disable_webhook(webhook_id: str):
        """Disable a webhook (admin)."""
        try:
            webhook = await webhook_service.disable_webhook(webhook_id)
            return {
                "success": True,
                "status": webhook.status.value,
            }
        except WebhookNotFoundError:
            raise HTTPException(status_code=404, detail="Webhook not found")

    return router


def create_webhook_receiver_routes(
    prefix: str = "",
    tags: list[str] = None,
) -> APIRouter:
    """
    Create routes for receiving webhooks (for testing/demo).

    This creates an endpoint that can receive webhook deliveries
    and log them for debugging purposes.
    """
    router = APIRouter(prefix=prefix, tags=tags or ["Webhook Receiver"])

    # In-memory storage for received webhooks
    received_webhooks: list[dict] = []

    @router.post("/receive")
    async def receive_webhook(request: Request):
        """Receive a webhook delivery."""
        body = await request.body()
        headers = dict(request.headers)

        received = {
            "received_at": str(__import__("datetime").datetime.utcnow().isoformat()),
            "headers": headers,
            "body": body.decode() if body else None,
            "signature": headers.get("x-webhook-signature"),
            "event_type": headers.get("x-event-type"),
            "webhook_id": headers.get("x-webhook-id"),
        }

        received_webhooks.append(received)

        # Keep only last 100
        if len(received_webhooks) > 100:
            received_webhooks.pop(0)

        return {"received": True}

    @router.get("/received")
    async def list_received_webhooks(
        limit: int = Query(20, ge=1, le=100),
    ):
        """List recently received webhooks."""
        return {
            "webhooks": received_webhooks[-limit:],
            "total": len(received_webhooks),
        }

    @router.delete("/received")
    async def clear_received_webhooks():
        """Clear received webhooks."""
        received_webhooks.clear()
        return {"success": True}

    return router
