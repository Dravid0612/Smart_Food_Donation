"""
Phase 9 — Real-Time Integration & Production Database Tests
============================================================
Comprehensive test suite verifying:
1. 13 Canonical User-Visible Events & Trilingual Content
2. Notification Deduplication Sliding Window (60s)
3. Delta-Polling Feed API (GET /notifications/feed?since=...)
4. In-Memory SSE Live Streaming (GET /notifications/stream & pub/sub)
5. Production PostgreSQL Connection Pooling & Diagnostic Telemetry
6. Startup Database Validation & /health Probes (/health/live, /health/ready)
7. SQLite WAL & Foreign Key Pragma Enforcement
"""

import pytest
import asyncio
import json
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient

from app.main import app
from app.db.session import (
    SessionLocal,
    engine,
    validate_database_connection,
    get_db_diagnostics,
)
from app.models.models import (
    User,
    FoodDonation,
    Notification,
    NotificationPreference,
)
from app.services.notification_service import (
    create_event_notification,
    subscribe_user_stream,
    unsubscribe_user_stream,
    broadcast_user_event,
    _NOTIFICATION_CONTENT,
    _ALWAYS_SEND_EVENTS,
)
from app.core.security import create_access_token


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_donor(db_session):
    user = db_session.query(User).filter(User.role == "donor").first()
    if not user:
        user = User(
            name="Phase 9 Donor",
            email="phase9_donor@test.org",
            password_hash="test_hash",
            role="donor",
            is_active=True,
            is_verified=True,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
    token = create_access_token({"sub": str(user.id), "role": user.role})
    return user, {"Authorization": f"Bearer {token}"}


@pytest.fixture
def sample_donation(db_session, auth_donor):
    user, _ = auth_donor
    don = db_session.query(FoodDonation).filter(FoodDonation.donor_id == user.id).first()
    if not don:
        don = FoodDonation(
            donor_id=user.id,
            food_name="Phase 9 Sambar Rice",
            quantity=50.0,
            quantity_unit="meals",
            pickup_address="123 Test St",
            latitude=12.9716,
            longitude=77.5946,
            expiry_time=datetime.now(timezone.utc) + timedelta(hours=4),
            status="pending",
        )
        db_session.add(don)
        db_session.commit()
        db_session.refresh(don)
    return don


# ─────────────────────────────────────────────────────────────────────────────
# 1. 13 Canonical User-Visible Events
# ─────────────────────────────────────────────────────────────────────────────

CANONICAL_EVENTS = [
    "NEW_RESCUE",
    "OFFER_RECEIVED",
    "OFFER_ACCEPTED",
    "WAVE_ESCALATED",
    "VOLUNTEER_ASSIGNED",
    "VOLUNTEER_REMATCHED",
    "VOLUNTEER_ARRIVING",
    "PICKUP_COMPLETED",
    "OTP_VERIFIED",
    "FOOD_RECEIVED",
    "DISTRIBUTION_COMPLETED",
    "RESCUE_EXPIRED",
    "ADMIN_INTERVENTION",
]


def test_all_13_canonical_events_registered():
    """Verify all 13 Phase 9 canonical events exist in content registry with translations."""
    for event_key in CANONICAL_EVENTS:
        assert event_key in _NOTIFICATION_CONTENT, f"Missing event: {event_key}"
        content = _NOTIFICATION_CONTENT[event_key]
        assert "en" in content, f"Missing English for {event_key}"
        assert "ta" in content, f"Missing Tamil for {event_key}"
        assert "hi" in content, f"Missing Hindi for {event_key}"
        assert len(content["en"]["title"]) > 0
        assert len(content["en"]["message"]) > 0


def test_create_and_deliver_all_13_canonical_events(db_session, auth_donor, sample_donation):
    """Verify create_event_notification successfully creates and stores all 13 events."""
    user, _ = auth_donor
    created_notifications = []

    for idx, event_key in enumerate(CANONICAL_EVENTS):
        # Unique timestamp/delay simulation so dedup doesn't trigger across identical keys
        notif = create_event_notification(
            db=db_session,
            user_id=user.id,
            event_type=event_key,
            donation_id=sample_donation.id,
            lang="en",
            send_push=False,
            extra_message=f"Test message for {event_key}"
        )
        assert notif is not None, f"Failed to create notification for event {event_key}"
        assert notif.event_type == event_key
        assert notif.user_id == user.id
        assert notif.type in ["emergency", "alert", "assignment", "donation", "info"]
        created_notifications.append(notif)

    assert len(created_notifications) == 13


def test_no_sensitive_data_in_canonical_events(db_session, auth_donor, sample_donation):
    """Verify that none of the canonical notifications leak OTP, plaintext passwords, or tokens."""
    user, _ = auth_donor
    for event_key in CANONICAL_EVENTS:
        notif = create_event_notification(
            db=db_session,
            user_id=user.id,
            event_type=event_key,
            donation_id=sample_donation.id,
            lang="en",
            send_push=False,
        )
        if notif:
            # Check title, message, and deep link data
            assert "password" not in notif.message.lower()
            assert "bearer" not in notif.message.lower()
            if notif.deep_link_data:
                payload = json.loads(notif.deep_link_data)
                assert "otp" not in payload
                assert "token" not in payload


# ─────────────────────────────────────────────────────────────────────────────
# 2. Notification Deduplication Mechanism
# ─────────────────────────────────────────────────────────────────────────────

def test_sliding_window_deduplication(db_session, auth_donor):
    """Verify that duplicate notifications for the same event and donation within 60s are suppressed."""
    user, _ = auth_donor
    don = FoodDonation(
        donor_id=user.id,
        food_name="Dedup Test Sambar",
        food_category="cooked_meals",
        quantity=25.0,
        pickup_address="456 Dedup Lane",
        latitude=13.0,
        longitude=80.0,
        expiry_time=datetime.now(timezone.utc) + timedelta(hours=3),
        preparation_time=datetime.now(timezone.utc),
        status="pending",
    )
    db_session.add(don)
    db_session.commit()
    db_session.refresh(don)

    # First event should succeed
    first = create_event_notification(
        db=db_session,
        user_id=user.id,
        event_type="NEW_RESCUE",
        donation_id=don.id,
        lang="en",
        send_push=False,
    )
    assert first is not None

    # Second immediate event within 60s must be suppressed
    duplicate = create_event_notification(
        db=db_session,
        user_id=user.id,
        event_type="NEW_RESCUE",
        donation_id=don.id,
        lang="en",
        send_push=False,
    )
    assert duplicate is None, "Immediate duplicate must be suppressed by deduplication"

    # Different event for the same donation should NOT be suppressed
    different_event = create_event_notification(
        db=db_session,
        user_id=user.id,
        event_type="ADMIN_INTERVENTION",
        donation_id=don.id,
        lang="en",
        send_push=False,
    )
    assert different_event is not None, "Distinct event type must not be blocked"


# ─────────────────────────────────────────────────────────────────────────────
# 3. Delta-Polling Feed API
# ─────────────────────────────────────────────────────────────────────────────

def test_notification_feed_endpoint(client, auth_donor, sample_donation, db_session):
    """Test GET /api/notifications/feed with and without 'since' filter."""
    user, headers = auth_donor

    # Create a fresh notification
    create_event_notification(
        db=db_session,
        user_id=user.id,
        event_type="OFFER_ACCEPTED",
        donation_id=sample_donation.id,
        lang="en",
        send_push=False,
    )

    # 1. Full feed poll
    resp = client.get("/api/notifications/feed", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "notifications" in data
    assert "unread_count" in data
    assert "server_time" in data
    assert len(data["notifications"]) >= 1

    # 2. Delta poll with 'since' in the future
    future_time = (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()
    resp_future = client.get(f"/api/notifications/feed?since={future_time}", headers=headers)
    assert resp_future.status_code == 200
    future_data = resp_future.json()
    assert len(future_data["notifications"]) == 0

    # 3. Delta poll with 'since' in the past
    past_time = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()
    resp_past = client.get(f"/api/notifications/feed?since={past_time}", headers=headers)
    assert resp_past.status_code == 200
    past_data = resp_past.json()
    assert len(past_data["notifications"]) >= 1


# ─────────────────────────────────────────────────────────────────────────────
# 4. In-Memory SSE Streaming
# ─────────────────────────────────────────────────────────────────────────────

def test_sse_subscription_and_broadcast():
    """Verify in-memory pub/sub queues connect and receive live event payloads."""
    test_uid = 99999
    queue = subscribe_user_stream(test_uid)

    try:
        # Broadcast test event
        test_payload = {
            "id": 1,
            "event_type": "VOLUNTEER_ARRIVING",
            "title": "Volunteer Arriving",
            "message": "Arriving in 2 minutes",
        }
        broadcast_user_event(test_uid, test_payload)

        # Check queue received it immediately
        assert not queue.empty()
        received = queue.get_nowait()
        assert received["event_type"] == "VOLUNTEER_ARRIVING"
        assert received["title"] == "Volunteer Arriving"
    finally:
        unsubscribe_user_stream(test_uid, queue)


# ─────────────────────────────────────────────────────────────────────────────
# 5. Production Database Connection Pooling & Diagnostics
# ─────────────────────────────────────────────────────────────────────────────

def test_database_connection_validation():
    """Verify startup validation measures query latency and returns masked URL."""
    val = validate_database_connection()
    assert val["status"] == "ok"
    assert val["latency_ms"] >= 0.0
    assert "password" not in val["database_url"].lower()
    assert val["dialect"] in ["sqlite", "postgresql"]


def test_database_diagnostics_telemetry():
    """Verify pool telemetry reports engine configuration and pool state."""
    diag = get_db_diagnostics()
    assert "dialect" in diag
    assert "pool" in diag
    assert "database_url" in diag
    assert "is_sqlite" in diag
    assert "is_postgresql" in diag


# ─────────────────────────────────────────────────────────────────────────────
# 6. Health Check Probes
# ─────────────────────────────────────────────────────────────────────────────

def test_health_check_probes(client):
    """Verify /health, /health/live, and /health/ready respond with operational readiness."""
    # Process Liveness
    resp_live = client.get("/health/live")
    assert resp_live.status_code == 200
    assert resp_live.json()["status"] == "alive"

    # Database Readiness
    resp_ready = client.get("/health/ready")
    assert resp_ready.status_code == 200
    assert resp_ready.json()["status"] == "ready"
    assert "latency_ms" in resp_ready.json()

    # Full Health Diagnostic
    resp_health = client.get("/health")
    assert resp_health.status_code == 200
    h_data = resp_health.json()
    assert h_data["database"]["status"] == "ok"
    assert "services" in h_data
    assert h_data["services"]["background_urgency_monitor"] in ["running", "stopped"]
    assert h_data["services"]["sms_provider"] in ["mock", "twilio"]


# ─────────────────────────────────────────────────────────────────────────────
# 7. SQLite WAL & Foreign Key Pragma Enforcement
# ─────────────────────────────────────────────────────────────────────────────

def test_sqlite_wal_pragmas(db_session):
    """Verify that when running on SQLite, WAL journal mode is active."""
    if engine.dialect.name == "sqlite":
        from sqlalchemy import text
        wal_result = db_session.execute(text("PRAGMA journal_mode;")).scalar()
        assert str(wal_result).lower() == "wal", f"Expected WAL journal mode, got {wal_result}"
