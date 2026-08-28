from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from typing import List, Optional
from pydantic import BaseModel

from app.db.session import get_db
from app.models.models import Notification, User, NotificationPreference
from app.schemas.schemas import NotificationResponse
from app.core.dependencies import get_current_user
from app.services.notification_service import mark_notification_opened

router = APIRouter(prefix="/notifications", tags=["Notifications"])


# ─── Request / Response Schemas (inline for this route) ──────────────────────

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
