import asyncio
import json
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from typing import List, Optional
from pydantic import BaseModel

from app.db.session import get_db
from app.models.models import Notification, User, NotificationPreference
from app.schemas.schemas import NotificationResponse
from app.core.dependencies import get_current_user
from app.services.notification_service import (
    mark_notification_opened,
    subscribe_user_stream,
    unsubscribe_user_stream,
)

router = APIRouter(prefix="/notifications", tags=["Notifications"])


# ─── Request / Response Schemas (inline for this route) ──────────────────────

class NotificationFeedResponse(BaseModel):
    notifications: List[NotificationResponse]
    unread_count: int
    server_time: str
    has_more: bool

class NotificationPreferenceUpdate(BaseModel):
    operational_notifications: Optional[bool] = None
    urgent_rescue_alerts: Optional[bool] = None
    impact_updates: Optional[bool] = None
    feedback_reminders: Optional[bool] = None
    fcm_token: Optional[str] = None  # Firebase device token


class NotificationPreferenceResponse(BaseModel):
    user_id: int
    operational_notifications: bool
    urgent_rescue_alerts: bool
    impact_updates: bool
    feedback_reminders: bool
    fcm_token_registered: bool  # True if FCM token present (never return the actual token)

    class Config:
        from_attributes = True


# ─── Notification List ────────────────────────────────────────────────────────

@router.get("", response_model=List[NotificationResponse])
def get_user_notifications(
    unread_only: bool = False,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Returns the current user's notifications, newest first."""
    query = db.query(Notification).filter(Notification.user_id == current_user.id)
    if unread_only:
        query = query.filter(Notification.is_read == False)
    notifications = query.order_by(Notification.created_at.desc()).offset(offset).limit(limit).all()
    return notifications


@router.get("/unread-count")
def get_unread_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Returns count of unread notifications."""
    count = db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False,
    ).count()
    return {"unread_count": count}


@router.get("/feed", response_model=NotificationFeedResponse)
def get_notification_feed(
    since: Optional[str] = None,
    unread_only: bool = False,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    High-efficiency delta polling endpoint for real-time mobile and web clients.
    If 'since' is provided, returns only notifications created after that timestamp.
    Also returns the current unread count and authoritative server_time for synchronizing next poll.
    """
    query = db.query(Notification).filter(Notification.user_id == current_user.id)
    if since:
        try:
            # URL decoding often turns '+' into ' '; handle gracefully
            clean_since = since.strip().replace(" ", "+")
            since_dt = datetime.fromisoformat(clean_since)
            if since_dt.tzinfo is None:
                since_dt = since_dt.replace(tzinfo=timezone.utc)
            query = query.filter(Notification.created_at > since_dt)
        except Exception:
            pass
    if unread_only:
        query = query.filter(Notification.is_read == False)

    total_new = query.count()
    items = query.order_by(Notification.created_at.desc()).limit(limit).all()

    unread_count = db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False,
    ).count()

    return NotificationFeedResponse(
        notifications=items,
        unread_count=unread_count,
        server_time=datetime.now(timezone.utc).isoformat(),
        has_more=total_new > limit,
    )


@router.get("/stream")
async def stream_notifications(
    current_user: User = Depends(get_current_user),
):
    """
    Server-Sent Events (SSE) live streaming endpoint.
    Establishes a persistent text/event-stream connection.
    Pushes canonical lifecycle notifications immediately as they occur.
    Transmits keepalive ': ping\n\n' every 15 seconds to prevent client timeout.
    """
    queue = subscribe_user_stream(current_user.id)

    async def event_generator():
        try:
            connected_payload = json.dumps({
                "type": "connected",
                "user_id": current_user.id,
                "server_time": datetime.now(timezone.utc).isoformat(),
            })
            yield f"event: connect\ndata: {connected_payload}\n\n"

            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=15.0)
                    yield f"event: notification\ndata: {json.dumps(event)}\n\n"
                except asyncio.TimeoutError:
                    yield ": ping\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            unsubscribe_user_stream(current_user.id, queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ─── Mark Read ────────────────────────────────────────────────────────────────

@router.put("/{notification_id}/read", response_model=NotificationResponse)
def mark_notification_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Marks a single notification as read."""
    notif = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == current_user.id,
    ).first()
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found.")
    notif.is_read = True
    db.commit()
    db.refresh(notif)
    return notif


@router.put("/read-all", status_code=status.HTTP_200_OK)
def mark_all_notifications_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Marks all of the current user's notifications as read."""
    db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False,
    ).update({"is_read": True})
    db.commit()
    return {"message": "All notifications marked as read."}


# ─── Opened Tracking ──────────────────────────────────────────────────────────

@router.post("/{notification_id}/opened")
def record_notification_opened(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Records when the user taps/opens a notification.
    Used for notification lifecycle tracking (created → sent → opened).
    """
    success = mark_notification_opened(db, notification_id, current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Notification not found.")
    return {"message": "Notification marked as opened."}


# ─── Notification Preferences ─────────────────────────────────────────────────

@router.get("/preferences", response_model=NotificationPreferenceResponse)
def get_notification_preferences(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Returns the current user's notification preferences."""
    prefs = db.query(NotificationPreference).filter(
        NotificationPreference.user_id == current_user.id
    ).first()
    if not prefs:
        # Return defaults if not yet configured
        return NotificationPreferenceResponse(
            user_id=current_user.id,
            operational_notifications=True,
            urgent_rescue_alerts=True,
            impact_updates=True,
            feedback_reminders=True,
            fcm_token_registered=False,
        )
    return NotificationPreferenceResponse(
        user_id=current_user.id,
        operational_notifications=prefs.operational_notifications,
        urgent_rescue_alerts=prefs.urgent_rescue_alerts,
        impact_updates=prefs.impact_updates,
        feedback_reminders=prefs.feedback_reminders,
        fcm_token_registered=bool(prefs.fcm_token),
    )


@router.put("/preferences", response_model=NotificationPreferenceResponse)
def update_notification_preferences(
    update: NotificationPreferenceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Updates the current user's notification preferences and/or registers an FCM token.

    Note: urgent_rescue_alerts=False is accepted for the preference record,
    but the system will still deliver mandatory security notifications
    (OTP, VOLUNTEER_ARRIVED) regardless of this setting.
    """
    prefs = db.query(NotificationPreference).filter(
        NotificationPreference.user_id == current_user.id
    ).first()

    if not prefs:
        prefs = NotificationPreference(user_id=current_user.id)
        db.add(prefs)
        db.flush()

    if update.operational_notifications is not None:
        prefs.operational_notifications = update.operational_notifications
    if update.urgent_rescue_alerts is not None:
        prefs.urgent_rescue_alerts = update.urgent_rescue_alerts
    if update.impact_updates is not None:
        prefs.impact_updates = update.impact_updates
    if update.feedback_reminders is not None:
        prefs.feedback_reminders = update.feedback_reminders
    if update.fcm_token is not None:
        prefs.fcm_token = update.fcm_token
        prefs.fcm_token_updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(prefs)

    return NotificationPreferenceResponse(
        user_id=current_user.id,
        operational_notifications=prefs.operational_notifications,
        urgent_rescue_alerts=prefs.urgent_rescue_alerts,
        impact_updates=prefs.impact_updates,
        feedback_reminders=prefs.feedback_reminders,
        fcm_token_registered=bool(prefs.fcm_token),
    )
