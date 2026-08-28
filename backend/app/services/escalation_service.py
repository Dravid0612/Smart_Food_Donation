from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from app.models.models import FoodDonation, NGO, User, Notification, DonationHistory
from app.services.notification_service import create_notification

def escalate_donation(db: Session, donation_id: int, reason: str = "Urgent expiry / unassigned threshold exceeded") -> FoodDonation:
    donation = db.query(FoodDonation).filter(FoodDonation.id == donation_id).first()
    if not donation:
        return None

    now = datetime.now(timezone.utc)
    donation.is_emergency = True
    donation.escalated_at = now

    # Log escalation history
    history = DonationHistory(
        donation_id=donation.id,
        old_status=donation.status,
        new_status=donation.status,
        changed_by=donation.donor_id,
        remarks=f"EMERGENCY ESCALATION: {reason}"
    )
    db.add(history)

    # 1. Alert nearby NGOs with Emergency tag
    ngos = db.query(NGO).filter(NGO.is_verified == True, NGO.is_available == True).all()
    for ngo in ngos:
        create_notification(
            db=db,
            user_id=ngo.user_id,
            title="🚨 EMERGENCY: High Priority Food Donation",
            message=f"Urgent pickup required for '{donation.food_name}' ({donation.quantity} {donation.quantity_unit}) near {donation.pickup_address}. Double reward points active!",
            type="emergency",
            related_donation_id=donation.id
        )

    # 2. Alert active Volunteers with capacity
    volunteers = db.query(User).filter(User.role == "volunteer", User.is_active == True).all()
    for vol in volunteers:
        if (vol.carrying_capacity or 50) >= donation.quantity:
            create_notification(
                db=db,
                user_id=vol.id,
                title="🚨 Emergency Volunteer Pickup Available",
                message=f"Critical pickup needed: '{donation.food_name}' at {donation.pickup_address}. Instant assignment available.",
                type="emergency",
                related_donation_id=donation.id
            )

    # 3. Alert Admins of Emergency Escalation
    admins = db.query(User).filter(User.role == "admin").all()
    for admin in admins:
        create_notification(
            db=db,
            user_id=admin.id,
            title="🚨 ADMIN ESCALATION: Emergency Food Rescue",
            message=f"Donation #{donation.id} ('{donation.food_name}') escalated to EMERGENCY: {reason}",
            type="alert",
            related_donation_id=donation.id
        )

    db.commit()
    db.refresh(donation)
    return donation

def check_and_auto_escalate(db: Session) -> list[int]:
    """
    Checks all pending and accepted donations and auto-escalates if expiry is within 2 hours or pending > 45 mins.
    """
    now = datetime.now(timezone.utc)
    escalated_ids = []
    
    active_donations = db.query(FoodDonation).filter(
        FoodDonation.status.in_(["pending", "accepted"]),
        FoodDonation.is_emergency == False
    ).all()

    for donation in active_donations:
        expiry = donation.expiry_time
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)

        time_left = (expiry - now).total_seconds() / 3600.0
        
        # If less than 2.5 hours remaining or condition is POOR, escalate
        if time_left < 2.5 or donation.ai_visual_condition == "POOR":
            escalate_donation(db, donation.id, reason=f"Critical time window: {time_left:.1f}h until expiry")
            escalated_ids.append(donation.id)

    return escalated_ids
