from sqlalchemy.orm import Session
from app.models.models import Notification

def create_notification(
    db: Session,
    user_id: int,
    title: str,
    message: str,
    type: str = "info",
    related_donation_id: int = None
) -> Notification:
    notification = Notification(
        user_id=user_id,
        title=title,
        message=message,
        type=type,
        related_donation_id=related_donation_id
    )
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return notification
