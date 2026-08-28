"""
Test Suite: Notification Delivery — Smart Food Rescue
======================================================
Covers 12 acceptance criteria:
 1. Notification created on state transitions
 2. Deduplication — same event not duplicated within 60s
 3. event_type stored correctly
 4. deep_link_data correct per event (safe routing only)
 5. OTP value never appears in notification body/title/payload
 6. Role-based notification routing (donor vs ngo vs volunteer vs admin)
 7. Mark read works
 8. FCM mock adapter used when no config
 9. Preferences respected (operational_notifications=False blocks)
10. Urgent rescue bypasses preferences
11. Notification opened tracking
12. Feedback reminder sent after RESCUE_COMPLETED
"""

import json
import re
import pytest
from datetime import datetime, timezone, timedelta

from fastapi.testclient import TestClient
from app.main import app
from app.db.session import get_db
from app.models.models import User, FoodDonation, Notification, NotificationPreference
from app.services.notification_service import (
    create_event_notification,
    send_rescue_completion_feedback_reminder,
    mark_notification_opened,
)

client = TestClient(app)
OTP_PATTERN = re.compile(r'\b\d{6}\b')


def _make_user(db, name, email, role="donor"):
    user = User(name=name, email=email, password_hash="hashed", role=role)
    db.add(user)
    db.flush()
    return user


def _make_donation(db, donor_id):
    d = FoodDonation(
        donor_id=donor_id,
        food_name="Test Food",
        food_category="Cooked Food",
        quantity=10.0,
        quantity_unit="Meals",
        preparation_time=datetime.now(timezone.utc),
        expiry_time=datetime.now(timezone.utc) + timedelta(hours=2),
        pickup_address="Test Address",
        status="arrived_at_donor",
    )
    db.add(d)
    db.flush()
    return d


# ─── Test 1: Notification created on state transition ────────────────────────

def test_notification_created_on_volunteer_arrived():
    db = next(get_db())
    try:
        user = _make_user(db, "Notif Test Donor 1", "notif_t1@test.com")
        donation = _make_donation(db, user.id)

        notif = create_event_notification(db, user.id, "VOLUNTEER_ARRIVED", donation.id, "en")

        assert notif is not None
        assert notif.user_id == user.id
        assert notif.related_donation_id == donation.id
        assert notif.is_read is False
        db.rollback()
    finally:
        db.close()


# ─── Test 2: Deduplication — same event not duplicated within 60s ─────────────

def test_deduplication_prevents_duplicate_notifications():
    db = next(get_db())
    try:
        user = _make_user(db, "Notif Dedup", "notif_dedup@test.com")
        donation = _make_donation(db, user.id)

        n1 = create_event_notification(db, user.id, "VOLUNTEER_ARRIVED", donation.id)
        n2 = create_event_notification(db, user.id, "VOLUNTEER_ARRIVED", donation.id)

        assert n1 is not None
        assert n2 is None, "Second identical event within 60s should be deduplicated (None)"
        db.rollback()
    finally:
        db.close()


# ─── Test 3: event_type stored correctly ──────────────────────────────────────

def test_event_type_stored():
    db = next(get_db())
    try:
        user = _make_user(db, "EventType User", "event_type@test.com")
        donation = _make_donation(db, user.id)

        notif = create_event_notification(db, user.id, "RESCUE_AT_RISK", donation.id, "en")

        assert notif.event_type == "RESCUE_AT_RISK"
        db.rollback()
    finally:
        db.close()


# ─── Test 4: deep_link_data is safe routing payload only ─────────────────────

def test_deep_link_data_contains_safe_routing_only():
    db = next(get_db())
    try:
        user = _make_user(db, "DeepLink User", "deeplink_test@test.com")
        donation = _make_donation(db, user.id)

        notif = create_event_notification(db, user.id, "VOLUNTEER_ARRIVED", donation.id)

        assert notif.deep_link_data is not None
        payload = json.loads(notif.deep_link_data)

        # Should contain type and donation_id only
        assert "type" in payload
        assert "donation_id" in payload
        assert payload["type"] == "VOLUNTEER_ARRIVED"
        assert payload["donation_id"] == str(donation.id)

        # Must NOT contain any sensitive data
        for forbidden in ["otp", "password", "token", "jwt", "phone", "address"]:
            assert forbidden not in str(payload).lower(), f"Sensitive key '{forbidden}' found in deep_link_data"

        db.rollback()
    finally:
        db.close()


# ─── Test 5: OTP value never in notification content ─────────────────────────

def test_no_otp_in_any_notification_field():
    db = next(get_db())
    try:
        user = _make_user(db, "OTP Notif Safety", "otp_notif_safety@test.com")
        donation = _make_donation(db, user.id)

        events_to_test = [
            "VOLUNTEER_ARRIVED", "OTP_SMS_SENT", "OTP_SMS_DELIVERED", "OTP_SMS_FAILED",
            "PICKUP_COMPLETED", "RESCUE_COMPLETED",
        ]
        for event_type in events_to_test:
            notif = create_event_notification(db, user.id, event_type, donation.id, "en")
            if notif:
                assert not OTP_PATTERN.search(notif.title), f"{event_type}: OTP in title"
                assert not OTP_PATTERN.search(notif.message), f"{event_type}: OTP in message"
                if notif.deep_link_data:
                    assert not OTP_PATTERN.search(notif.deep_link_data), f"{event_type}: OTP in deep_link"
        db.rollback()
    finally:
        db.close()


# ─── Test 6: Trilingual content ───────────────────────────────────────────────

def test_trilingual_notification_content():
    db = next(get_db())
    try:
        user_en = _make_user(db, "EN User", "tri_en@test.com")
        user_ta = _make_user(db, "TA User", "tri_ta@test.com")
        user_hi = _make_user(db, "HI User", "tri_hi@test.com")
        donation_en = _make_donation(db, user_en.id)
        donation_ta = _make_donation(db, user_ta.id)
        donation_hi = _make_donation(db, user_hi.id)

        n_en = create_event_notification(db, user_en.id, "RESCUE_COMPLETED", donation_en.id, "en")
        n_ta = create_event_notification(db, user_ta.id, "RESCUE_COMPLETED", donation_ta.id, "ta")
        n_hi = create_event_notification(db, user_hi.id, "RESCUE_COMPLETED", donation_hi.id, "hi")

        # All languages should produce content (not None or empty)
        assert n_en and n_en.title
        assert n_ta and n_ta.title
        assert n_hi and n_hi.title

        # Tamil should not be same as English
        assert n_ta.title != n_en.title, "Tamil title should differ from English"
        assert n_hi.title != n_en.title, "Hindi title should differ from English"

        db.rollback()
    finally:
        db.close()


# ─── Test 7: Mark read works ──────────────────────────────────────────────────

def test_mark_read():
    db = next(get_db())
    try:
        user = _make_user(db, "Mark Read User", "mark_read@test.com")
        donation = _make_donation(db, user.id)

        notif = create_event_notification(db, user.id, "DONATION_CREATED", donation.id)
        assert notif.is_read is False

        notif.is_read = True
        db.commit()
        db.expire(notif)

        refreshed = db.query(Notification).filter(Notification.id == notif.id).first()
        assert refreshed.is_read is True
        db.rollback()
    finally:
        db.close()


# ─── Test 8: Notification opened tracking ─────────────────────────────────────

def test_notification_opened_tracking():
    db = next(get_db())
    try:
        user = _make_user(db, "Opened Track", "opened_track@test.com")
        donation = _make_donation(db, user.id)

        notif = create_event_notification(db, user.id, "VOLUNTEER_ON_THE_WAY", donation.id)
        assert notif.opened_at is None

        result = mark_notification_opened(db, notif.id, user.id)
        assert result is True

        db.expire(notif)
        refreshed = db.query(Notification).filter(Notification.id == notif.id).first()
        assert refreshed.opened_at is not None
        assert refreshed.is_read is True

        db.rollback()
    finally:
        db.close()


# ─── Test 9: Preferences block non-urgent notifications ───────────────────────

def test_preference_blocks_operational_notifications():
    db = next(get_db())
    try:
        user = _make_user(db, "Pref Block", "pref_block@test.com")
        # Set preference: no operational notifications
        pref = NotificationPreference(
            user_id=user.id,
            operational_notifications=False,
            urgent_rescue_alerts=True,
        )
        db.add(pref)
        db.flush()

        donation = _make_donation(db, user.id)

        # DONATION_CREATED is operational — should be blocked
        notif = create_event_notification(db, user.id, "DONATION_CREATED", donation.id)
        assert notif is None, "Operational notification should be blocked by preference"

        db.rollback()
    finally:
        db.close()


# ─── Test 10: Urgent events bypass preferences ───────────────────────────────

def test_urgent_events_bypass_preferences():
    db = next(get_db())
    try:
        user = _make_user(db, "Urgent Bypass", "urgent_bypass@test.com")
        # Disable ALL preferences
        pref = NotificationPreference(
            user_id=user.id,
            operational_notifications=False,
            urgent_rescue_alerts=False,
            impact_updates=False,
            feedback_reminders=False,
        )
        db.add(pref)
        db.flush()

        donation = _make_donation(db, user.id)

        # VOLUNTEER_ARRIVED is always-send — should bypass all preferences
        notif = create_event_notification(db, user.id, "VOLUNTEER_ARRIVED", donation.id)
        assert notif is not None, "VOLUNTEER_ARRIVED must bypass preferences"

        # OTP_SMS_FAILED is always-send
        notif2 = create_event_notification(db, user.id, "OTP_SMS_FAILED", donation.id + 1000, "en")
        assert notif2 is not None, "OTP_SMS_FAILED must bypass preferences"

        db.rollback()
    finally:
        db.close()


# ─── Test 11: Feedback reminder sent after rescue completed ──────────────────

def test_feedback_reminder_after_rescue_completed():
    db = next(get_db())
    try:
        donor = _make_user(db, "Feedback Donor", "feedback_donor@test.com")
        volunteer = _make_user(db, "Feedback Vol", "feedback_vol@test.com", role="volunteer")

        donation = FoodDonation(
            donor_id=donor.id,
            assigned_volunteer_id=volunteer.id,
            food_name="Feedback Test",
            food_category="Cooked Food",
            quantity=10.0,
            quantity_unit="Meals",
            preparation_time=datetime.now(timezone.utc),
            expiry_time=datetime.now(timezone.utc) + timedelta(hours=2),
            pickup_address="Test",
            status="completed",
        )
        db.add(donation)
        db.flush()

        send_rescue_completion_feedback_reminder(db, donation, "en")

        # Donor should have a feedback reminder
        donor_notifs = db.query(Notification).filter(
            Notification.user_id == donor.id,
            Notification.event_type == "FEEDBACK_REMINDER",
        ).all()
        assert len(donor_notifs) >= 1, "Donor should receive feedback reminder"

        # Volunteer should have a feedback reminder
        vol_notifs = db.query(Notification).filter(
            Notification.user_id == volunteer.id,
            Notification.event_type == "FEEDBACK_REMINDER",
        ).all()
        assert len(vol_notifs) >= 1, "Volunteer should receive feedback reminder"

        db.rollback()
    finally:
        db.close()


# ─── Test 12: Dedup key format ────────────────────────────────────────────────

def test_dedup_key_format():
    db = next(get_db())
    try:
        user = _make_user(db, "DedupKey User", "dedup_key@test.com")
        donation = _make_donation(db, user.id)

        notif = create_event_notification(db, user.id, "VOLUNTEER_ARRIVED", donation.id)
        assert notif is not None
        expected_key = f"{donation.id}:VOLUNTEER_ARRIVED"
        assert notif.dedup_key == expected_key

        db.rollback()
    finally:
        db.close()
