"""
Test Suite: Real-Time Rescue Tracking & Battery-Conscious Telemetry
===================================================================
Verifies location ingestion security, honest ETA calculation, proximity arrival
detection, and role-based privacy filters.
"""

import json
from datetime import datetime, timezone, timedelta
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models.models import User, NGO, FoodDonation, VolunteerAssignment
from app.core.security import create_access_token, hash_password
from app.services.route_service import route_service

client = TestClient(app)


def test_01_volunteer_location_update_authorization(db_session: Session):
    """Verifies that an assigned volunteer can update their rescue location, while unassigned cannot."""
    ts = int(datetime.now().timestamp())

    # Donor
    donor = User(
        name=f"Track Donor {ts}",
        email=f"donor_{ts}@test.com",
        password_hash=hash_password("Pass123!"),
        role="donor",
        is_active=True
    )
    db_session.add(donor)

    # Assigned Volunteer
    vol_assigned = User(
        name=f"Assigned Vol {ts}",
        email=f"vol_assigned_{ts}@test.com",
        password_hash=hash_password("Pass123!"),
        role="volunteer",
        vehicle_type="bike",
        carrying_capacity=50,
        is_active=True
    )
    db_session.add(vol_assigned)

    # Unassigned Volunteer
    vol_unassigned = User(
        name=f"Unassigned Vol {ts}",
        email=f"vol_unassigned_{ts}@test.com",
        password_hash=hash_password("Pass123!"),
        role="volunteer",
        vehicle_type="bike",
        carrying_capacity=50,
        is_active=True
    )
    db_session.add(vol_unassigned)

    # NGO
    ngo_user = User(
        name=f"NGO User {ts}",
        email=f"ngo_{ts}@test.com",
        password_hash=hash_password("Pass123!"),
        role="ngo",
        is_active=True
    )
    db_session.add(ngo_user)
    db_session.flush()

    ngo = NGO(
        user_id=ngo_user.id,
        organization_name="Care Shelter",
        capacity=100,
        current_capacity=80,
        is_available=True,
        is_verified=True,
        latitude=12.9780,
        longitude=77.6000
    )
    db_session.add(ngo)

    now = datetime.now(timezone.utc)
    donation = FoodDonation(
        donor_id=donor.id,
        food_name="Curd Rice Meals",
        food_category="Cooked Food",
        quantity=25.0,
        quantity_unit="Meals",
        preparation_time=now - timedelta(minutes=30),
        expiry_time=now + timedelta(hours=3),
        pickup_address="123, 5th Cross, Koramangala 4th Block, Bangalore",
        latitude=12.9716,
        longitude=77.5946,
        status="volunteer_assigned",
        assigned_ngo_id=ngo.id,
        assigned_volunteer_id=vol_assigned.id
    )
    db_session.add(donation)
    db_session.flush()

    assignment = VolunteerAssignment(
        donation_id=donation.id,
        volunteer_id=vol_assigned.id,
        status="en_route",
        assigned_at=now
    )
    db_session.add(assignment)
    db_session.commit()

    token_assigned = create_access_token({"sub": str(vol_assigned.id), "role": "volunteer"})
    token_unassigned = create_access_token({"sub": str(vol_unassigned.id), "role": "volunteer"})

    # 1. Assigned volunteer transmits location -> Succeeds
    resp = client.post(
        "/api/volunteers/location",
        headers={"Authorization": f"Bearer {token_assigned}"},
        json={
            "latitude": 12.9650,
            "longitude": 77.5900,
            "donation_id": donation.id,
            "speed_kmh": 22.5,
            "heading": 45.0,
            "battery_level": 88.0
        }
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["success"] is True
    assert data["eta_minutes"] >= 5
    assert data["tracking_status"] == "EN_ROUTE"

    # 2. Unassigned volunteer attempts to update -> 404 (No active assignment for this volunteer)
    resp2 = client.post(
        "/api/volunteers/location",
        headers={"Authorization": f"Bearer {token_unassigned}"},
        json={
            "latitude": 12.9650,
            "longitude": 77.5900,
            "donation_id": donation.id
        }
    )
    assert resp2.status_code == 404


def test_02_honest_eta_and_proximity_arrival(db_session: Session):
    """Verifies that moving close to donor location (< 250m) auto-detects arrival proximity."""
    ts = int(datetime.now().timestamp())
    donor = User(name=f"D {ts}", email=f"d_{ts}@test.com", password_hash=hash_password("Pass123!"), role="donor", is_active=True)
    vol = User(name=f"V {ts}", email=f"v_{ts}@test.com", password_hash=hash_password("Pass123!"), role="volunteer", is_active=True)
    db_session.add_all([donor, vol])
    db_session.flush()

    now = datetime.now(timezone.utc)
    donation = FoodDonation(
        donor_id=donor.id,
        food_name="Sambar Rice",
        food_category="Cooked Food",
        quantity=30.0,
        quantity_unit="Meals",
        preparation_time=now - timedelta(minutes=45),
        expiry_time=now + timedelta(hours=3),
        pickup_address="MG Road, Bangalore",
        latitude=12.9716,
        longitude=77.5946,
        status="pickup_en_route",
        assigned_volunteer_id=vol.id
    )
    db_session.add(donation)
    db_session.flush()

    assignment = VolunteerAssignment(
        donation_id=donation.id,
        volunteer_id=vol.id,
        status="en_route",
        assigned_at=now
    )
    db_session.add(assignment)
    db_session.commit()

    token = create_access_token({"sub": str(vol.id), "role": "volunteer"})

    # Volunteer transmits coordinates very close to donor (< 100 meters: 12.9717, 77.5947)
    resp = client.post(
        "/api/volunteers/location",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "latitude": 12.9717,
            "longitude": 77.5947,
            "donation_id": donation.id
        }
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["tracking_status"] == "ARRIVED_AT_DONOR"


def test_03_tracking_endpoint_role_privacy_filtering(db_session: Session):
    """Verifies that GET /api/donations/{id}/tracking delivers role-specific filtered views."""
    ts = int(datetime.now().timestamp())
    donor = User(name=f"Donor Priv {ts}", email=f"don_priv_{ts}@test.com", password_hash=hash_password("Pass123!"), role="donor", is_active=True)
    vol = User(name=f"Arun Courier {ts}", email=f"vol_priv_{ts}@test.com", password_hash=hash_password("Pass123!"), role="volunteer", is_active=True)
    ngo_u = User(name=f"NGO Priv {ts}", email=f"ngo_priv_{ts}@test.com", password_hash=hash_password("Pass123!"), role="ngo", is_active=True)
    admin_u = User(name=f"Admin Priv {ts}", email=f"adm_priv_{ts}@test.com", password_hash=hash_password("Pass123!"), role="admin", is_active=True)
    db_session.add_all([donor, vol, ngo_u, admin_u])
    db_session.flush()

    ngo = NGO(
        user_id=ngo_u.id,
        organization_name="Hope Shelter",
        capacity=100,
        is_verified=True,
        address="789, 80ft Road, Indiranagar, Bangalore",
        latitude=12.9780,
        longitude=77.6000
    )
    db_session.add(ngo)
    db_session.flush()

    now = datetime.now(timezone.utc)
    donation = FoodDonation(
        donor_id=donor.id,
        food_name="Rice & Lentils",
        food_category="Cooked Food",
        quantity=50.0,
        quantity_unit="Meals",
        preparation_time=now - timedelta(minutes=40),
        expiry_time=now + timedelta(hours=2),
        pickup_address="456, 12th Main, Koramangala 4th Block, Bangalore",
        latitude=12.9716,
        longitude=77.5946,
        status="en_route",
        assigned_ngo_id=ngo.id,
        assigned_volunteer_id=vol.id,
        tracking_latitude=12.9680,
        tracking_longitude=77.5910,
        current_eta_minutes=8.0,
        current_distance_km=2.1,
        feasibility_status="RESCUE_FEASIBLE"
    )
    db_session.add(donation)
    db_session.flush()

    assign = VolunteerAssignment(
        donation_id=donation.id,
        volunteer_id=vol.id,
        status="en_route",
        assigned_at=now
    )
    db_session.add(assign)
    db_session.commit()

    donor_tok = create_access_token({"sub": str(donor.id), "role": "donor"})
    ngo_tok = create_access_token({"sub": str(ngo_u.id), "role": "ngo"})
    vol_tok = create_access_token({"sub": str(vol.id), "role": "volunteer"})
    adm_tok = create_access_token({"sub": str(admin_u.id), "role": "admin"})

    # 1. Donor View
    resp_don = client.get(f"/api/donations/{donation.id}/tracking", headers={"Authorization": f"Bearer {donor_tok}"})
    assert resp_don.status_code == 200
    don_data = resp_don.json()
    assert don_data["food_name"] == "Rice & Lentils"
    assert don_data["volunteer_name"] == vol.name
    assert don_data["eta_minutes"] == 8
    assert "Estimated travel time" in don_data["eta_display"]
    assert len(don_data["stages_timeline"]) > 0

    # 2. NGO View
    resp_ngo = client.get(f"/api/donations/{donation.id}/tracking", headers={"Authorization": f"Bearer {ngo_tok}"})
    assert resp_ngo.status_code == 200
    ngo_data = resp_ngo.json()
    assert ngo_data["volunteer_name"] == vol.name
    assert ngo_data["feasibility_status"] == "RESCUE_FEASIBLE"

    # 3. Volunteer View
    resp_vol = client.get(f"/api/donations/{donation.id}/tracking", headers={"Authorization": f"Bearer {vol_tok}"})
    assert resp_vol.status_code == 200
    vol_data = resp_vol.json()
    assert vol_data["pickup_address"] == donation.pickup_address  # Exact address for assigned volunteer

    # 4. Admin View
    resp_adm = client.get(f"/api/donations/{donation.id}/tracking", headers={"Authorization": f"Bearer {adm_tok}"})
    assert resp_adm.status_code == 200
    adm_data = resp_adm.json()
    assert adm_data["donation_id"] == donation.id


def test_04_eta_endpoint_breakdown(db_session: Session):
    """Verifies GET /api/donations/{id}/eta returns calibrated routing metrics."""
    ts = int(datetime.now().timestamp())
    donor = User(name=f"ETA Donor {ts}", email=f"eta_{ts}@test.com", password_hash=hash_password("Pass123!"), role="donor", is_active=True)
    db_session.add(donor)
    db_session.commit()

    now = datetime.now(timezone.utc)
    donation = FoodDonation(
        donor_id=donor.id,
        food_name="Idli Platter",
        food_category="Cooked Food",
        quantity=40.0,
        quantity_unit="Meals",
        preparation_time=now - timedelta(minutes=20),
        expiry_time=now + timedelta(hours=3),
        pickup_address="Indiranagar, Bangalore",
        latitude=12.9716,
        longitude=77.5946,
        current_eta_minutes=11.0,
        current_distance_km=3.2,
        status="volunteer_assigned"
    )
    db_session.add(donation)
    db_session.commit()

    donor_tok = create_access_token({"sub": str(donor.id), "role": "donor"})
    resp = client.get(f"/api/donations/{donation.id}/eta", headers={"Authorization": f"Bearer {donor_tok}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["donation_id"] == donation.id
    assert data["eta_label"] == "Estimated travel time"
    assert data["eta_minutes"] >= 5
    assert data["distance_km"] > 0
