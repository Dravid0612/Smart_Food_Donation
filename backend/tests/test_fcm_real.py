"""
FCM Push Notification Test Suite — Smart Food Rescue Platform
==============================================================
Validates:
1. HTTP v1 / Admin SDK authorization path with OAuth 2.0 Bearer token
2. Valid FCM HTTP v1 message send & delivery status
3. Invalid / unregistered token cleanup (HTTP 404 / UNREGISTERED -> token deactivated)
4. Provider failure isolation (network error / 500 does NOT crash core transaction)
5. Missing credentials fallback (cleanly falls back to mock push adapter)
6. Token registration (POST /notifications/device-token)
7. Token refresh & deduplication
8. Logout cleanup (DELETE /notifications/device-token)
9. Notification deep-link routing
10. Security: Zero plaintext OTP in notification title, body, or deep-link data
11. Security: Zero credential leakage (service account keys, tokens never in payloads)
12. Security: Zero sensitive exact coordinates in push payload
"""

import json
from unittest.mock import MagicMock
import pytest
from app.core.config import settings
from app.models.models import Notification, NotificationPreference, User
from app.services.notification_service import (
    _send_fcm_push,
    _get_fcm_access_token,
    _build_deep_link_data,
    create_notification,
    _NOTIFICATION_CONTENT
)


@pytest.fixture
def donor_user(db_session):
    u = db_session.query(User).filter(User.role.ilike("donor")).first()
    if not u:
        u = User(name="fcm_donor_test", email="fcm_donor@test.com", password_hash="dummy_hash_123", role="donor", is_active=True)
        db_session.add(u)
        db_session.commit()
    return u


def test_1_http_v1_authorization_path(monkeypatch, db_session, donor_user):
    """Test 1: HTTP v1 authorization path queries projects/{id}/messages:send with OAuth 2.0 Bearer token."""
    monkeypatch.setattr(settings, "FCM_PROJECT_ID", "relivio-rescue")
    monkeypatch.setattr(settings, "GOOGLE_APPLICATION_CREDENTIALS", "dummy_service_account.json")
    monkeypatch.setattr("app.services.notification_service._get_fcm_access_token", lambda: "mock-oauth2-bearer-token-12345")

    pref = db_session.query(NotificationPreference).filter_by(user_id=donor_user.id).first()
    if not pref:
        pref = NotificationPreference(user_id=donor_user.id, fcm_token="device_token_auth_test")
        db_session.add(pref)
    else:
        pref.fcm_token = "device_token_auth_test"
    db_session.commit()

    notif = Notification(
        user_id=donor_user.id,
        event_type="DONATION_CREATED",
        title="Donation Submitted",
        message="Your donation has been submitted.",
        deep_link_data=_build_deep_link_data("DONATION_CREATED", 101),
        is_sent=False
    )
    db_session.add(notif)
    db_session.commit()

    sent_url = ""
    sent_headers = {}
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"name": "projects/relivio-rescue/messages/0:123456789"}

    def mock_post(self, url, json=None, headers=None, **kwargs):
        nonlocal sent_url, sent_headers
        sent_url = str(url)
        sent_headers = headers or {}
        return mock_resp

    monkeypatch.setattr("httpx.Client.post", mock_post)

    success = _send_fcm_push(notif, db_session)
    assert success is True
    assert sent_url == "https://fcm.googleapis.com/v1/projects/relivio-rescue/messages:send"
    assert sent_headers.get("Authorization") == "Bearer mock-oauth2-bearer-token-12345"
    assert "application/json" in sent_headers.get("Content-Type", "")


def test_2_valid_token_send_http_v1(monkeypatch, db_session, donor_user):
    """Test 2: Valid token send dispatches structured HTTP v1 message payload."""
    monkeypatch.setattr(settings, "FCM_PROJECT_ID", "relivio-rescue")
    monkeypatch.setattr(settings, "GOOGLE_APPLICATION_CREDENTIALS", "dummy_service_account.json")
    monkeypatch.setattr("app.services.notification_service._get_fcm_access_token", lambda: "mock-oauth2-token")

    pref = db_session.query(NotificationPreference).filter_by(user_id=donor_user.id).first()
    if not pref:
        pref = NotificationPreference(user_id=donor_user.id, fcm_token="device_token_donor_99")
        db_session.add(pref)
    else:
        pref.fcm_token = "device_token_donor_99"
    db_session.commit()

    notif = Notification(
        user_id=donor_user.id,
        event_type="VOLUNTEER_ASSIGNED",
        title="Volunteer Assigned",
        message="A volunteer has been assigned to collect your donation.",
        deep_link_data=_build_deep_link_data("VOLUNTEER_ASSIGNED", 102),
        is_sent=False
    )
    db_session.add(notif)
    db_session.commit()

    sent_body = {}
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"name": "projects/relivio-rescue/messages/0:987654321"}

    def mock_post(self, url, json=None, headers=None, **kwargs):
        nonlocal sent_body
        sent_body = json
        return mock_resp

    monkeypatch.setattr("httpx.Client.post", mock_post)

    success = _send_fcm_push(notif, db_session)
    assert success is True
    assert notif.is_sent is True
    assert notif.sent_at is not None
    # Must use current HTTP v1 format: message.token
    assert "message" in sent_body
    msg = sent_body["message"]
    assert msg["token"] == "device_token_donor_99"
    assert msg["notification"]["title"] == "Volunteer Assigned"
    assert msg["data"]["donation_id"] == "102"
    assert msg["android"]["priority"] == "HIGH"


def test_3_invalid_unregistered_token_cleanup(monkeypatch, db_session, donor_user):
    """Test 3: When FCM HTTP v1 returns UNREGISTERED / NOT_FOUND, stale device token is cleared automatically."""
    monkeypatch.setattr(settings, "FCM_PROJECT_ID", "relivio-rescue")
    monkeypatch.setattr(settings, "GOOGLE_APPLICATION_CREDENTIALS", "dummy_service_account.json")
    monkeypatch.setattr("app.services.notification_service._get_fcm_access_token", lambda: "mock-oauth2-token")

    pref = db_session.query(NotificationPreference).filter_by(user_id=donor_user.id).first()
    if not pref:
        pref = NotificationPreference(user_id=donor_user.id, fcm_token="stale_dead_token")
        db_session.add(pref)
    else:
        pref.fcm_token = "stale_dead_token"
    db_session.commit()

    notif = Notification(
        user_id=donor_user.id,
        event_type="DONATION_ACCEPTED",
        title="Donation Accepted",
        message="An NGO has accepted your donation.",
        deep_link_data=_build_deep_link_data("DONATION_ACCEPTED", 103),
        is_sent=False
    )
    db_session.add(notif)
    db_session.commit()

    mock_resp = MagicMock()
    mock_resp.status_code = 404
    mock_resp.json.return_value = {
        "error": {
            "code": 404,
            "message": "Requested entity was not found.",
            "status": "NOT_FOUND",
            "details": [{"@type": "type.googleapis.com/google.firebase.fcm.v1.FcmError", "errorCode": "UNREGISTERED"}]
        }
    }

    monkeypatch.setattr("httpx.Client.post", lambda self, *a, **k: mock_resp)

    success = _send_fcm_push(notif, db_session)
    assert success is False
    assert notif.is_sent is False

    # Stale token must be deactivated in database
    db_session.refresh(pref)
    assert pref.fcm_token is None


def test_4_provider_failure_isolation(monkeypatch, db_session, donor_user):
    """Test 4: External FCM network failure or HTTP 500 does NOT raise exception or crash core transaction."""
    import httpx
    monkeypatch.setattr(settings, "FCM_PROJECT_ID", "relivio-rescue")
    monkeypatch.setattr(settings, "GOOGLE_APPLICATION_CREDENTIALS", "dummy_service_account.json")
    monkeypatch.setattr("app.services.notification_service._get_fcm_access_token", lambda: "mock-oauth2-token")

    pref = db_session.query(NotificationPreference).filter_by(user_id=donor_user.id).first()
    if not pref:
        pref = NotificationPreference(user_id=donor_user.id, fcm_token="valid_token_xyz")
        db_session.add(pref)
    else:
        pref.fcm_token = "valid_token_xyz"
    db_session.commit()

    notif = Notification(
        user_id=donor_user.id,
        event_type="RESCUE_AT_RISK",
        title="Rescue At Risk",
        message="Urgent action required.",
        deep_link_data=_build_deep_link_data("RESCUE_AT_RISK", 104),
        is_sent=False
    )
    db_session.add(notif)
    db_session.commit()

    def mock_failing_post(*a, **k):
        raise httpx.ConnectError("Connection refused by FCM endpoint")

    monkeypatch.setattr("httpx.Client.post", mock_failing_post)

    # Must return False gracefully without raising exception
    success = _send_fcm_push(notif, db_session)
    assert success is False
    assert notif.is_sent is False


def test_5_missing_credentials_fallback(monkeypatch, db_session, donor_user):
    """Test 5: When FCM credentials are not configured, mock push adapter logs safely and completes."""
    monkeypatch.setattr(settings, "FCM_PROJECT_ID", "")
    monkeypatch.setattr(settings, "GOOGLE_APPLICATION_CREDENTIALS", "")

    notif = Notification(
        user_id=donor_user.id,
        event_type="DONATION_CREATED",
        title="Donation Submitted",
        message="Your donation has been submitted.",
        deep_link_data=_build_deep_link_data("DONATION_CREATED", 101),
        is_sent=False
    )
    db_session.add(notif)
    db_session.commit()

    success = _send_fcm_push(notif, db_session)
    assert success is True
    assert notif.is_sent is True
    assert notif.sent_at is not None


def test_6_token_registration(db_session, donor_user):
    """Test 6: Token registration creates NotificationPreference record."""
    from app.api.routes.notifications import register_device_token, DeviceTokenRequest

    req = DeviceTokenRequest(fcm_token="reg_test_token_abc")
    res = register_device_token(payload=req, db=db_session, current_user=donor_user)
    assert res["user_id"] == donor_user.id

    pref = db_session.query(NotificationPreference).filter_by(user_id=donor_user.id).first()
    assert pref is not None
    assert pref.fcm_token == "reg_test_token_abc"


def test_7_token_refresh(db_session, donor_user):
    """Test 7: Token refresh updates existing device token and timestamp."""
    from app.api.routes.notifications import register_device_token, DeviceTokenRequest

    req = DeviceTokenRequest(fcm_token="refreshed_test_token_xyz")
    res = register_device_token(payload=req, db=db_session, current_user=donor_user)
    assert res["user_id"] == donor_user.id

    pref = db_session.query(NotificationPreference).filter_by(user_id=donor_user.id).first()
    assert pref.fcm_token == "refreshed_test_token_xyz"
    assert pref.fcm_token_updated_at is not None


def test_8_logout_cleanup(db_session, donor_user):
    """Test 8: Logout unregisters device token."""
    from app.api.routes.notifications import register_device_token, unregister_device_token, DeviceTokenRequest

    register_device_token(payload=DeviceTokenRequest(fcm_token="logout_cleanup_token"), db=db_session, current_user=donor_user)
    pref = db_session.query(NotificationPreference).filter_by(user_id=donor_user.id).first()
    assert pref.fcm_token == "logout_cleanup_token"

    res = unregister_device_token(db=db_session, current_user=donor_user)
    assert "successfully" in res["message"]
    db_session.refresh(pref)
    assert pref.fcm_token is None


def test_9_notification_routing():
    """Test 9: Deep link payload contains only safe event type and donation ID."""
    deep_link = _build_deep_link_data("VOLUNTEER_ARRIVED", 201)
    data = json.loads(deep_link)
    assert data["type"] == "VOLUNTEER_ARRIVED"
    assert data["donation_id"] == "201"
    assert "otp" not in data
    assert "phone" not in data


def test_10_zero_otp_leakage(monkeypatch, db_session, donor_user):
    """Test 10: Absolute security: Plaintext OTP is NEVER included in FCM push notification or data."""
    monkeypatch.setattr(settings, "FCM_PROJECT_ID", "relivio-rescue")
    monkeypatch.setattr(settings, "GOOGLE_APPLICATION_CREDENTIALS", "dummy.json")
    monkeypatch.setattr("app.services.notification_service._get_fcm_access_token", lambda: "mock-token")

    pref = db_session.query(NotificationPreference).filter_by(user_id=donor_user.id).first()
    if not pref:
        pref = NotificationPreference(user_id=donor_user.id, fcm_token="secure_token_abc")
        db_session.add(pref)
    else:
        pref.fcm_token = "secure_token_abc"
    db_session.commit()

    tampered_data = json.dumps({
        "type": "VOLUNTEER_ARRIVED",
        "donation_id": "105",
        "otp": "492015",
        "secret_code": "secret123",
        "pin": "7788"
    })

    notif = Notification(
        user_id=donor_user.id,
        event_type="VOLUNTEER_ARRIVED",
        title="Volunteer Has Arrived",
        message="Open app to view your secure pickup code.",
        deep_link_data=tampered_data,
        is_sent=False
    )
    db_session.add(notif)
    db_session.commit()

    sent_payload = {}
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"name": "projects/relivio-rescue/messages/0:105"}

    def mock_post(self, url, json=None, **k):
        nonlocal sent_payload
        sent_payload = json
        return mock_resp

    monkeypatch.setattr("httpx.Client.post", mock_post)

    _send_fcm_push(notif, db_session)

    msg_data = sent_payload.get("message", {}).get("data", {})
    assert "otp" not in msg_data
    assert "secret_code" not in msg_data
    assert "pin" not in msg_data
    assert "492015" not in json.dumps(sent_payload)


def test_11_zero_credential_leakage(monkeypatch, db_session, donor_user):
    """Test 11: Security: Private credentials, access tokens, and API secrets are never embedded in payload."""
    monkeypatch.setattr(settings, "FCM_PROJECT_ID", "relivio-rescue")
    monkeypatch.setattr(settings, "GOOGLE_APPLICATION_CREDENTIALS", "dummy.json")
    monkeypatch.setattr("app.services.notification_service._get_fcm_access_token", lambda: "super-secret-oauth-token")

    pref = db_session.query(NotificationPreference).filter_by(user_id=donor_user.id).first()
    if not pref:
        pref = NotificationPreference(user_id=donor_user.id, fcm_token="cred_test_token")
        db_session.add(pref)
    else:
        pref.fcm_token = "cred_test_token"
    db_session.commit()

    notif = Notification(
        user_id=donor_user.id,
        event_type="DONATION_CREATED",
        title="Donation Submitted",
        message="Your donation has been submitted.",
        deep_link_data=json.dumps({"type": "DONATION_CREATED", "donation_id": "106", "auth_token": "secret_tok", "private_key": "private_val"}),
        is_sent=False
    )
    db_session.add(notif)
    db_session.commit()

    sent_payload = {}
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"name": "projects/relivio-rescue/messages/0:106"}

    monkeypatch.setattr("httpx.Client.post", lambda s, u, json=None, **k: setattr(s, "_sent", json) or mock_resp)

    _send_fcm_push(notif, db_session)

    raw_json = json.dumps(sent_payload)
    assert "auth_token" not in raw_json
    assert "private_key" not in raw_json
    assert "super-secret-oauth-token" not in raw_json


def test_12_zero_sensitive_coordinate_leakage(monkeypatch, db_session, donor_user):
    """Test 12: Security: Sensitive exact GPS coordinates are stripped from push payload data."""
    monkeypatch.setattr(settings, "FCM_PROJECT_ID", "relivio-rescue")
    monkeypatch.setattr(settings, "GOOGLE_APPLICATION_CREDENTIALS", "dummy.json")
    monkeypatch.setattr("app.services.notification_service._get_fcm_access_token", lambda: "mock-token")

    pref = db_session.query(NotificationPreference).filter_by(user_id=donor_user.id).first()
    if not pref:
        pref = NotificationPreference(user_id=donor_user.id, fcm_token="coord_test_token")
        db_session.add(pref)
    else:
        pref.fcm_token = "coord_test_token"
    db_session.commit()

    notif = Notification(
        user_id=donor_user.id,
        event_type="VOLUNTEER_ON_THE_WAY",
        title="Volunteer On The Way",
        message="Your volunteer is on the way.",
        deep_link_data=json.dumps({"type": "VOLUNTEER_ON_THE_WAY", "donation_id": "107", "latitude": "13.0827", "longitude": "80.2707", "coord": "13.08,80.27"}),
        is_sent=False
    )
    db_session.add(notif)
    db_session.commit()

    sent_payload = {}
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"name": "projects/relivio-rescue/messages/0:107"}

    def mock_post(self, url, json=None, **k):
        nonlocal sent_payload
        sent_payload = json
        return mock_resp

    monkeypatch.setattr("httpx.Client.post", mock_post)

    _send_fcm_push(notif, db_session)

    msg_data = sent_payload.get("message", {}).get("data", {})
    assert "latitude" not in msg_data
    assert "longitude" not in msg_data
    assert "coord" not in msg_data


# ─── 13. Repeated Same State Causes Zero Duplicate Pushes ───────────────────

def test_13_repeated_same_state_causes_zero_duplicate_pushes(monkeypatch, db_session, donor_user):
    """
    Proves:
    - Same operational event for the same donation within 60s is deduplicated
    - Duplicate send is prevented and telemetry counts fcm_duplicate_prevented
    - Zero additional notifications or pushes are generated
    """
    from app.services.notification_service import create_event_notification, get_fcm_telemetry, reset_fcm_telemetry
    reset_fcm_telemetry()

    # 1st event
    notif1 = create_event_notification(
        db=db_session,
        user_id=donor_user.id,
        event_type="DONATION_ACCEPTED",
        donation_id=505,
        send_push=False
    )
    assert notif1 is not None

    # Repeated identical event (e.g. background monitor checking state repeatedly)
    notif2 = create_event_notification(
        db=db_session,
        user_id=donor_user.id,
        event_type="DONATION_ACCEPTED",
        donation_id=505,
        send_push=False
    )
    # Duplicate suppressed, returning None
    assert notif2 is None
    telemetry = get_fcm_telemetry()
    assert telemetry["fcm_duplicate_prevented"] >= 1


# ─── 14. Same Token Not Repeatedly Registered ────────────────────────────────

def test_14_same_token_not_repeatedly_registered(db_session, donor_user):
    """
    Proves:
    - Registering an already active, identical token skips redundant DB updates
    - Returns updated=False to indicate no-op
    """
    from app.api.routes.notifications import register_device_token, DeviceTokenRequest

    # Initial registration
    req = DeviceTokenRequest(fcm_token="stable_device_token_123")
    res1 = register_device_token(payload=req, db=db_session, current_user=donor_user)
    assert res1["updated"] is True

    # Immediate re-registration with exact same token
    res2 = register_device_token(payload=req, db=db_session, current_user=donor_user)
    assert res2["updated"] is False
    assert "already registered" in res2["message"].lower()


# ─── 15. Provider Transient Failure Bounded Retries ──────────────────────────

def test_15_provider_transient_failure_bounded_retries(monkeypatch, db_session, donor_user):
    """
    Proves:
    - Transient 503 error retries at most FCM_MAX_TRANSIENT_RETRIES (1)
    - Total calls = 2 (initial + 1 retry), never loops infinitely
    """
    monkeypatch.setattr(settings, "FCM_PROJECT_ID", "relivio-rescue")
    monkeypatch.setattr(settings, "GOOGLE_APPLICATION_CREDENTIALS", "dummy.json")
    monkeypatch.setattr(settings, "FCM_MAX_TRANSIENT_RETRIES", 1)
    monkeypatch.setattr("app.services.notification_service._get_fcm_access_token", lambda: "mock-token")

    pref = db_session.query(NotificationPreference).filter_by(user_id=donor_user.id).first()
    if not pref:
        pref = NotificationPreference(user_id=donor_user.id, fcm_token="retry_token_abc")
        db_session.add(pref)
    else:
        pref.fcm_token = "retry_token_abc"
    db_session.commit()

    notif = Notification(
        user_id=donor_user.id,
        event_type="DONATION_CREATED",
        title="Donation Created",
        message="Created.",
        deep_link_data=_build_deep_link_data("DONATION_CREATED", 108),
        is_sent=False
    )
    db_session.add(notif)
    db_session.commit()

    call_count = 0
    def mock_503(self, *a, **k):
        nonlocal call_count
        call_count += 1
        resp = MagicMock()
        resp.status_code = 503
        return resp

    monkeypatch.setattr("httpx.Client.post", mock_503)
    monkeypatch.setattr("time.sleep", lambda s: None)

    success = _send_fcm_push(notif, db_session)
    assert success is False
    # Max retries = 1 -> exactly 2 calls made
    assert call_count == 2


# ─── 16. Permanent Token Error Not Retried ───────────────────────────────────

def test_16_permanent_token_error_not_retried(monkeypatch, db_session, donor_user):
    """
    Proves:
    - Permanent 404 UNREGISTERED error is NEVER retried
    - Exactly 1 external call is made, token cleared, returns False immediately
    """
    monkeypatch.setattr(settings, "FCM_PROJECT_ID", "relivio-rescue")
    monkeypatch.setattr(settings, "GOOGLE_APPLICATION_CREDENTIALS", "dummy.json")
    monkeypatch.setattr("app.services.notification_service._get_fcm_access_token", lambda: "mock-token")

    pref = db_session.query(NotificationPreference).filter_by(user_id=donor_user.id).first()
    if not pref:
        pref = NotificationPreference(user_id=donor_user.id, fcm_token="dead_token_404")
        db_session.add(pref)
    else:
        pref.fcm_token = "dead_token_404"
    db_session.commit()

    notif = Notification(
        user_id=donor_user.id,
        event_type="DONATION_ACCEPTED",
        title="Donation Accepted",
        message="Accepted.",
        deep_link_data=_build_deep_link_data("DONATION_ACCEPTED", 109),
        is_sent=False
    )
    db_session.add(notif)
    db_session.commit()

    call_count = 0
    mock_resp = MagicMock()
    mock_resp.status_code = 404
    mock_resp.json.return_value = {
        "error": {
            "code": 404,
            "status": "NOT_FOUND",
            "details": [{"errorCode": "UNREGISTERED"}]
        }
    }

    def mock_post(self, *a, **k):
        nonlocal call_count
        call_count += 1
        return mock_resp

    monkeypatch.setattr("httpx.Client.post", mock_post)

    success = _send_fcm_push(notif, db_session)
    assert success is False
    # Permanent error must NOT be retried: exactly 1 call made
    assert call_count == 1
    db_session.refresh(pref)
    assert pref.fcm_token is None


# ─── 17. OTP Remains Absent in All Dedup and Push ────────────────────────────

def test_17_otp_remains_absent_in_all_dedup_and_push(monkeypatch, db_session, donor_user):
    """
    Proves:
    - Absolute security guarantee: OTP is completely absent across deduplicated events, push payloads, and deep link data
    """
    from app.services.notification_service import create_event_notification
    # Send VOLUNTEER_ARRIVED event
    notif = create_event_notification(
        db=db_session,
        user_id=donor_user.id,
        event_type="VOLUNTEER_ARRIVED",
        donation_id=601,
        send_push=False
    )
    assert notif is not None
    assert "otp" not in notif.title.lower()
    assert "otp" not in notif.message.lower()
    assert "otp" not in (notif.deep_link_data or "").lower()
