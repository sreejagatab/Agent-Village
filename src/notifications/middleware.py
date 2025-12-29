"""
Notification Middleware and Routes.

Provides FastAPI routes for notification management including:
- User notification endpoints
- Preference management
- Template management (admin)
- Device registration
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from functools import wraps

from pydantic import BaseModel, Field

from src.notifications.models import (
    Notification,
    NotificationType,
    NotificationStatus,
    NotificationPriority,
    NotificationCategory,
    NotificationContent,
    NotificationRecipient,
    NotificationTemplate,
    NotificationPreferences,
    ChannelPreference,
    CategoryPreference,
)
from src.notifications.service import (
    NotificationService,
    NotificationError,
    NotificationNotFoundError,
    TemplateNotFoundError,
    PreferencesBlockedError,
    RateLimitExceededError,
)


# Pydantic models for API
class NotificationContentRequest(BaseModel):
    """Request model for notification content."""
    subject: Optional[str] = None
    title: Optional[str] = None
    body: str
    html_body: Optional[str] = None
    short_body: Optional[str] = None
    image_url: Optional[str] = None
    action_url: Optional[str] = None
    action_text: Optional[str] = None
    data: Dict[str, Any] = Field(default_factory=dict)


class NotificationRecipientRequest(BaseModel):
    """Request model for notification recipient."""
    user_id: str
    email: Optional[str] = None
    phone: Optional[str] = None
    device_tokens: List[str] = Field(default_factory=list)
    name: Optional[str] = None


class SendNotificationRequest(BaseModel):
    """Request to send a notification."""
    notification_type: str
    recipient: NotificationRecipientRequest
    content: NotificationContentRequest
    category: str = "system"
    priority: str = "normal"
    scheduled_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SendToUserRequest(BaseModel):
    """Request to send notification to a user by ID."""
    user_id: str
    notification_type: str
    content: NotificationContentRequest
    category: str = "system"
    priority: str = "normal"


class SendFromTemplateRequest(BaseModel):
    """Request to send notification from a template."""
    template_id: str
    recipient: NotificationRecipientRequest
    data: Dict[str, Any] = Field(default_factory=dict)


class SendBulkRequest(BaseModel):
    """Request to send multiple notifications."""
    notifications: List[SendNotificationRequest]


class CreateTemplateRequest(BaseModel):
    """Request to create a notification template."""
    name: str
    notification_type: str
    body_template: str
    subject_template: Optional[str] = None
    title_template: Optional[str] = None
    html_body_template: Optional[str] = None
    short_body_template: Optional[str] = None
    category: str = "system"
    default_priority: str = "normal"
    description: Optional[str] = None


class UpdateTemplateRequest(BaseModel):
    """Request to update a notification template."""
    name: Optional[str] = None
    body_template: Optional[str] = None
    subject_template: Optional[str] = None
    title_template: Optional[str] = None
    html_body_template: Optional[str] = None
    default_priority: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class ChannelPreferenceRequest(BaseModel):
    """Request for channel preference."""
    enabled: bool = True
    quiet_hours_start: Optional[int] = None
    quiet_hours_end: Optional[int] = None
    max_per_hour: Optional[int] = None
    max_per_day: Optional[int] = None


class CategoryPreferenceRequest(BaseModel):
    """Request for category preference."""
    enabled: bool = True
    channels: List[str] = Field(default_factory=list)


class UpdatePreferencesRequest(BaseModel):
    """Request to update notification preferences."""
    notifications_enabled: Optional[bool] = None
    channel_preferences: Optional[Dict[str, ChannelPreferenceRequest]] = None
    category_preferences: Optional[Dict[str, CategoryPreferenceRequest]] = None
    digest_enabled: Optional[bool] = None
    digest_frequency: Optional[str] = None
    digest_time: Optional[int] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    timezone: Optional[str] = None


class RegisterDeviceRequest(BaseModel):
    """Request to register a device token."""
    device_token: str
    platform: Optional[str] = None  # ios, android, web


# Helper functions
def _parse_notification_type(type_str: str) -> NotificationType:
    """Parse notification type from string."""
    try:
        return NotificationType(type_str.lower())
    except ValueError:
        raise ValueError(f"Invalid notification type: {type_str}")


def _parse_category(cat_str: str) -> NotificationCategory:
    """Parse category from string."""
    try:
        return NotificationCategory(cat_str.lower())
    except ValueError:
        raise ValueError(f"Invalid category: {cat_str}")


def _parse_priority(priority_str: str) -> NotificationPriority:
    """Parse priority from string."""
    try:
        return NotificationPriority(priority_str.lower())
    except ValueError:
        raise ValueError(f"Invalid priority: {priority_str}")


def _parse_status(status_str: str) -> NotificationStatus:
    """Parse status from string."""
    try:
        return NotificationStatus(status_str.lower())
    except ValueError:
        raise ValueError(f"Invalid status: {status_str}")


def _build_notification(request: SendNotificationRequest) -> Notification:
    """Build a Notification from request."""
    recipient = NotificationRecipient(
        user_id=request.recipient.user_id,
        email=request.recipient.email,
        phone=request.recipient.phone,
        device_tokens=request.recipient.device_tokens,
        name=request.recipient.name,
    )

    content = NotificationContent(
        subject=request.content.subject,
        title=request.content.title,
        body=request.content.body,
        html_body=request.content.html_body,
        short_body=request.content.short_body,
        image_url=request.content.image_url,
        action_url=request.content.action_url,
        action_text=request.content.action_text,
        data=request.content.data,
    )

    return Notification(
        notification_type=_parse_notification_type(request.notification_type),
        category=_parse_category(request.category),
        priority=_parse_priority(request.priority),
        recipient=recipient,
        content=content,
        scheduled_at=request.scheduled_at,
        expires_at=request.expires_at,
        tags=request.tags,
        metadata=request.metadata,
    )


# Route factories
def create_notification_routes(service: NotificationService):
    """Create notification routes for users."""
    from fastapi import APIRouter, HTTPException, Query, Request

    router = APIRouter()

    @router.get("")
    async def list_notifications(
        request: Request,
        status: Optional[str] = None,
        offset: int = Query(0, ge=0),
        limit: int = Query(50, ge=1, le=100),
    ):
        """List notifications for the current user."""
        user_id = getattr(request.state, "user_id", None)
        if not user_id:
            raise HTTPException(status_code=401, detail="Authentication required")

        statuses = None
        if status:
            statuses = [_parse_status(status)]

        result = await service.get_user_notifications(
            user_id=user_id,
            statuses=statuses,
            offset=offset,
            limit=limit,
        )

        return result.to_dict()

    @router.get("/unread/count")
    async def get_unread_count(request: Request):
        """Get unread notification count."""
        user_id = getattr(request.state, "user_id", None)
        if not user_id:
            raise HTTPException(status_code=401, detail="Authentication required")

        count = await service.store.count_unread(user_id)
        return {"unread_count": count}

    # Preferences (must be before /{notification_id} to avoid route conflict)
    @router.get("/preferences")
    async def get_preferences(request: Request):
        """Get notification preferences."""
        user_id = getattr(request.state, "user_id", None)
        if not user_id:
            raise HTTPException(status_code=401, detail="Authentication required")

        preferences = await service.get_preferences(user_id)
        return preferences.to_dict()

    @router.get("/{notification_id}")
    async def get_notification(
        request: Request,
        notification_id: str,
    ):
        """Get a specific notification."""
        user_id = getattr(request.state, "user_id", None)
        if not user_id:
            raise HTTPException(status_code=401, detail="Authentication required")

        try:
            notification = await service.get_notification(notification_id)

            # Verify ownership
            if notification.recipient.user_id != user_id:
                raise HTTPException(status_code=404, detail="Notification not found")

            return notification.to_dict()

        except NotificationNotFoundError:
            raise HTTPException(status_code=404, detail="Notification not found")

    @router.post("/{notification_id}/read")
    async def mark_as_read(
        request: Request,
        notification_id: str,
    ):
        """Mark a notification as read."""
        user_id = getattr(request.state, "user_id", None)
        if not user_id:
            raise HTTPException(status_code=401, detail="Authentication required")

        try:
            notification = await service.mark_as_read(notification_id, user_id)
            return notification.to_dict()

        except NotificationNotFoundError:
            raise HTTPException(status_code=404, detail="Notification not found")

    @router.post("/read-all")
    async def mark_all_as_read(request: Request):
        """Mark all notifications as read."""
        user_id = getattr(request.state, "user_id", None)
        if not user_id:
            raise HTTPException(status_code=401, detail="Authentication required")

        count = await service.mark_all_as_read(user_id)
        return {"marked_as_read": count}

    @router.delete("/{notification_id}")
    async def delete_notification(
        request: Request,
        notification_id: str,
    ):
        """Delete a notification."""
        user_id = getattr(request.state, "user_id", None)
        if not user_id:
            raise HTTPException(status_code=401, detail="Authentication required")

        deleted = await service.delete_notification(notification_id, user_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Notification not found")

        return {"deleted": True}

    @router.put("/preferences")
    async def update_preferences(
        request: Request,
        data: UpdatePreferencesRequest,
    ):
        """Update notification preferences."""
        user_id = getattr(request.state, "user_id", None)
        if not user_id:
            raise HTTPException(status_code=401, detail="Authentication required")

        updates = {}

        if data.notifications_enabled is not None:
            updates["notifications_enabled"] = data.notifications_enabled

        if data.digest_enabled is not None:
            updates["digest_enabled"] = data.digest_enabled

        if data.digest_frequency:
            updates["digest_frequency"] = data.digest_frequency

        if data.digest_time is not None:
            updates["digest_time"] = data.digest_time

        if data.email:
            updates["email"] = data.email

        if data.phone:
            updates["phone"] = data.phone

        if data.timezone:
            updates["timezone"] = data.timezone

        # Handle channel preferences
        if data.channel_preferences:
            preferences = await service.get_preferences(user_id)
            for channel_str, pref_data in data.channel_preferences.items():
                try:
                    channel = _parse_notification_type(channel_str)
                    preferences.channel_preferences[channel] = ChannelPreference(
                        channel_type=channel,
                        enabled=pref_data.enabled,
                        quiet_hours_start=pref_data.quiet_hours_start,
                        quiet_hours_end=pref_data.quiet_hours_end,
                        max_per_hour=pref_data.max_per_hour,
                        max_per_day=pref_data.max_per_day,
                    )
                except ValueError:
                    pass

        # Handle category preferences
        if data.category_preferences:
            preferences = await service.get_preferences(user_id)
            for cat_str, pref_data in data.category_preferences.items():
                try:
                    category = _parse_category(cat_str)
                    channels = []
                    for ch_str in pref_data.channels:
                        try:
                            channels.append(_parse_notification_type(ch_str))
                        except ValueError:
                            pass
                    preferences.category_preferences[category] = CategoryPreference(
                        category=category,
                        enabled=pref_data.enabled,
                        channels=channels,
                    )
                except ValueError:
                    pass

        preferences = await service.update_preferences(user_id, **updates)
        return preferences.to_dict()

    # Device registration
    @router.post("/devices")
    async def register_device(
        request: Request,
        data: RegisterDeviceRequest,
    ):
        """Register a device for push notifications."""
        user_id = getattr(request.state, "user_id", None)
        if not user_id:
            raise HTTPException(status_code=401, detail="Authentication required")

        preferences = await service.register_device(user_id, data.device_token)
        return {
            "registered": True,
            "device_count": len(preferences.device_tokens),
        }

    @router.delete("/devices/{device_token}")
    async def unregister_device(
        request: Request,
        device_token: str,
    ):
        """Unregister a device."""
        user_id = getattr(request.state, "user_id", None)
        if not user_id:
            raise HTTPException(status_code=401, detail="Authentication required")

        preferences = await service.unregister_device(user_id, device_token)
        return {
            "unregistered": True,
            "device_count": len(preferences.device_tokens),
        }

    return router


def create_notification_send_routes(service: NotificationService):
    """Create routes for sending notifications (service/admin use)."""
    from fastapi import APIRouter, HTTPException, Request

    router = APIRouter()

    @router.post("/send")
    async def send_notification(
        request: Request,
        data: SendNotificationRequest,
    ):
        """Send a notification."""
        try:
            notification = _build_notification(data)
            notification = await service.send_notification(notification)
            return notification.to_dict()

        except RateLimitExceededError as e:
            raise HTTPException(status_code=429, detail=str(e))
        except PreferencesBlockedError as e:
            raise HTTPException(status_code=422, detail=str(e))
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except NotificationError as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("/send-to-user")
    async def send_to_user(
        request: Request,
        data: SendToUserRequest,
    ):
        """Send a notification to a user by ID."""
        try:
            content = NotificationContent(
                subject=data.content.subject,
                title=data.content.title,
                body=data.content.body,
                html_body=data.content.html_body,
                short_body=data.content.short_body,
                image_url=data.content.image_url,
                action_url=data.content.action_url,
                action_text=data.content.action_text,
                data=data.content.data,
            )

            notification = await service.send_to_user(
                user_id=data.user_id,
                notification_type=_parse_notification_type(data.notification_type),
                content=content,
                category=_parse_category(data.category),
                priority=_parse_priority(data.priority),
            )

            return notification.to_dict()

        except RateLimitExceededError as e:
            raise HTTPException(status_code=429, detail=str(e))
        except PreferencesBlockedError as e:
            raise HTTPException(status_code=422, detail=str(e))
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except NotificationError as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("/send-from-template")
    async def send_from_template(
        request: Request,
        data: SendFromTemplateRequest,
    ):
        """Send a notification using a template."""
        try:
            recipient = NotificationRecipient(
                user_id=data.recipient.user_id,
                email=data.recipient.email,
                phone=data.recipient.phone,
                device_tokens=data.recipient.device_tokens,
                name=data.recipient.name,
            )

            notification = await service.send_from_template(
                template_id=data.template_id,
                recipient=recipient,
                data=data.data,
            )

            return notification.to_dict()

        except TemplateNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except RateLimitExceededError as e:
            raise HTTPException(status_code=429, detail=str(e))
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except NotificationError as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("/send-bulk")
    async def send_bulk(
        request: Request,
        data: SendBulkRequest,
    ):
        """Send multiple notifications."""
        try:
            notifications = [_build_notification(n) for n in data.notifications]
            results = await service.send_bulk(notifications)

            return {
                "sent": len([n for n in results if n.status == NotificationStatus.SENT]),
                "failed": len([n for n in results if n.status == NotificationStatus.FAILED]),
                "cancelled": len([n for n in results if n.status == NotificationStatus.CANCELLED]),
                "notifications": [n.to_dict(include_attempts=False) for n in results],
            }

        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except NotificationError as e:
            raise HTTPException(status_code=500, detail=str(e))

    return router


def create_notification_admin_routes(service: NotificationService):
    """Create admin routes for notification management."""
    from fastapi import APIRouter, HTTPException, Query, Request

    router = APIRouter()

    # Template management
    @router.get("/templates")
    async def list_templates(
        request: Request,
        notification_type: Optional[str] = None,
    ):
        """List notification templates."""
        ntype = None
        if notification_type:
            try:
                ntype = _parse_notification_type(notification_type)
            except ValueError:
                pass

        templates = await service.list_templates(notification_type=ntype)
        return {
            "templates": [t.to_dict() for t in templates],
            "total": len(templates),
        }

    @router.post("/templates")
    async def create_template(
        request: Request,
        data: CreateTemplateRequest,
    ):
        """Create a notification template."""
        try:
            template = await service.create_template(
                name=data.name,
                notification_type=_parse_notification_type(data.notification_type),
                body_template=data.body_template,
                subject_template=data.subject_template,
                title_template=data.title_template,
                html_body_template=data.html_body_template,
                short_body_template=data.short_body_template,
                category=_parse_category(data.category),
                default_priority=_parse_priority(data.default_priority),
                description=data.description,
            )

            return template.to_dict()

        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.get("/templates/{template_id}")
    async def get_template(
        request: Request,
        template_id: str,
    ):
        """Get a template by ID."""
        try:
            template = await service.get_template(template_id)
            return template.to_dict()
        except TemplateNotFoundError:
            raise HTTPException(status_code=404, detail="Template not found")

    @router.put("/templates/{template_id}")
    async def update_template(
        request: Request,
        template_id: str,
        data: UpdateTemplateRequest,
    ):
        """Update a template."""
        try:
            updates = data.model_dump(exclude_unset=True)

            if "default_priority" in updates:
                updates["default_priority"] = _parse_priority(updates["default_priority"])

            template = await service.update_template(template_id, **updates)
            return template.to_dict()

        except TemplateNotFoundError:
            raise HTTPException(status_code=404, detail="Template not found")
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.delete("/templates/{template_id}")
    async def delete_template(
        request: Request,
        template_id: str,
    ):
        """Delete a template."""
        deleted = await service.delete_template(template_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Template not found")

        return {"deleted": True}

    # Statistics
    @router.get("/stats")
    async def get_stats(
        request: Request,
        user_id: Optional[str] = None,
        days: int = Query(30, ge=1, le=365),
    ):
        """Get notification statistics."""
        stats = await service.get_stats(user_id=user_id, days=days)
        return stats.to_dict()

    # Cleanup
    @router.post("/cleanup")
    async def cleanup_old(
        request: Request,
        days: int = Query(30, ge=1, le=365),
    ):
        """Clean up old notifications."""
        count = await service.cleanup_old_notifications(days)
        return {
            "deleted": count,
            "retention_days": days,
        }

    # Notification management
    @router.get("/notifications/{notification_id}")
    async def get_notification_admin(
        request: Request,
        notification_id: str,
    ):
        """Get any notification by ID (admin)."""
        try:
            notification = await service.get_notification(notification_id)
            return notification.to_dict()
        except NotificationNotFoundError:
            raise HTTPException(status_code=404, detail="Notification not found")

    @router.post("/notifications/{notification_id}/cancel")
    async def cancel_notification(
        request: Request,
        notification_id: str,
    ):
        """Cancel a pending notification."""
        try:
            notification = await service.cancel_notification(notification_id)
            return notification.to_dict()
        except NotificationNotFoundError:
            raise HTTPException(status_code=404, detail="Notification not found")
        except NotificationError as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.post("/process-pending")
    async def process_pending(
        request: Request,
        limit: int = Query(100, ge=1, le=1000),
    ):
        """Manually trigger processing of pending notifications."""
        count = await service.process_pending_notifications(limit)
        return {"processed": count}

    # User preferences (admin view)
    @router.get("/users/{user_id}/preferences")
    async def get_user_preferences(
        request: Request,
        user_id: str,
    ):
        """Get a user's notification preferences (admin)."""
        preferences = await service.get_preferences(user_id)
        return preferences.to_dict()

    @router.get("/users/{user_id}/notifications")
    async def get_user_notifications(
        request: Request,
        user_id: str,
        offset: int = Query(0, ge=0),
        limit: int = Query(50, ge=1, le=100),
    ):
        """Get a user's notifications (admin)."""
        result = await service.get_user_notifications(
            user_id=user_id,
            offset=offset,
            limit=limit,
        )
        return result.to_dict()

    return router


# Decorator for sending notifications on events
def notify_on_event(
    service: NotificationService,
    notification_type: NotificationType,
    template_id: Optional[str] = None,
    recipient_extractor: Optional[callable] = None,
    data_extractor: Optional[callable] = None,
    category: NotificationCategory = NotificationCategory.SYSTEM,
    priority: NotificationPriority = NotificationPriority.NORMAL,
):
    """
    Decorator to send notifications when a function is called.

    Args:
        service: NotificationService instance.
        notification_type: Type of notification to send.
        template_id: Template ID to use (optional).
        recipient_extractor: Function to extract recipient from request/response.
        data_extractor: Function to extract template data from request/response.
        category: Notification category.
        priority: Notification priority.

    Example:
        @app.post("/users")
        @notify_on_event(
            service=notification_service,
            notification_type=NotificationType.EMAIL,
            template_id="welcome_email",
            recipient_extractor=lambda req, resp: NotificationRecipient(
                user_id=resp["id"],
                email=resp["email"],
            ),
            data_extractor=lambda req, resp: {"name": resp["name"]},
        )
        async def create_user(request: Request):
            return {"id": "user123", "email": "user@example.com", "name": "John"}
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Execute the original function
            result = await func(*args, **kwargs)

            # Extract recipient
            request = kwargs.get("request") or (args[0] if args else None)
            recipient = None

            if recipient_extractor:
                try:
                    recipient = recipient_extractor(request, result)
                except Exception:
                    return result

            if not recipient:
                return result

            # Send notification
            try:
                if template_id:
                    data = {}
                    if data_extractor:
                        data = data_extractor(request, result)

                    await service.send_from_template(
                        template_id=template_id,
                        recipient=recipient,
                        data=data,
                    )
                else:
                    content = NotificationContent(
                        title="Notification",
                        body="Event occurred",
                    )
                    if data_extractor:
                        data = data_extractor(request, result)
                        content = NotificationContent(**data)

                    notification = Notification(
                        notification_type=notification_type,
                        category=category,
                        priority=priority,
                        recipient=recipient,
                        content=content,
                    )
                    await service.send_notification(notification)

            except Exception:
                # Don't fail the request if notification fails
                pass

            return result

        return wrapper
    return decorator
