"""
Test Suite: Food-Safety Self-Check Screening Declarations
=========================================================
Verifies donor screening declarations, validation rules, multilingual guidance,
and integration with donation submission.
"""

import json
from datetime import datetime, timezone, timedelta
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models.models import User, FoodDonation
from app.core.security import create_access_token, hash_password
from app.services.food_safety_check_service import food_safety_check_service, DECLARATION_DEFINITIONS

client = TestClient(app)


def test_01_food_safety_service_all_passed():
    """Validates that confirming all 5 affirmative declarations passes the check."""
    valid_answers = {
        "human_consumption": True,
        "hygienic_handling": True,
        "appropriate_storage": True,
        "contamination_free": True,
        "suitable_condition": True
    }
    result = food_safety_check_service.validate_declaration(valid_answers, language="en")
    assert result["is_eligible"] is True
    assert result["status"] == "PASSED"
    assert len(result["failed_declarations"]) == 0
    assert result["warning_message"] is None


def test_02_food_safety_service_unsafe_declaration_rejection():
    """Validates that indicating contamination or unsuitable food flags ineligibility."""
    unsafe_answers = {
        "human_consumption": True,
        "hygienic_handling": True,
        "appropriate_storage": True,
        "contamination_free": False,  # Exposed to contamination
        "suitable_condition": False   # Visible spoilage
    }
    result = food_safety_check_service.validate_declaration(unsafe_answers, language="en")
    assert result["is_eligible"] is False
    assert result["status"] == "UNSAFE_DECLARATION"
    assert "contamination_free" in result["failed_declarations"]
    assert "suitable_condition" in result["failed_declarations"]
    assert "not be suitable for donation" in result["warning_message"]


def test_03_food_safety_trilingual_guidance():
    """Verifies natural trilingual guidance in English, Tamil, and Hindi."""
    answers = {
        "human_consumption": False,
        "hygienic_handling": True,
        "appropriate_storage": True,
        "contamination_free": True,
        "suitable_condition": True
    }
    # English
    en_res = food_safety_check_service.validate_declaration(answers, language="en")
    assert en_res["is_eligible"] is False
    assert "human consumption" in en_res["guidance"]

    # Tamil
    ta_res = food_safety_check_service.validate_declaration(answers, language="ta")
    assert ta_res["is_eligible"] is False
    assert "மனித நுகர்வுக்காக" in ta_res["guidance"]

    # Hindi
    hi_res = food_safety_check_service.validate_declaration(answers, language="hi")
    assert hi_res["is_eligible"] is False
    assert "मानव उपभोग" in hi_res["guidance"]


def test_04_validate_safety_check_api_endpoint(db_session: Session):
    """Verifies the standalone API endpoint POST /api/donations/validate-safety-check."""
    ts = int(datetime.now().timestamp())
    donor = User(
        name=f"Safety Donor {ts}",
        email=f"safety_donor_{ts}@test.com",
        password_hash=hash_password("Pass123!"),
        role="donor",
        preferred_language="en",
        is_active=True
    )
    db_session.add(donor)
    db_session.commit()
    token = create_access_token({"sub": str(donor.id), "role": "donor"})

    # Valid check
    resp = client.post(
        "/api/donations/validate-safety-check",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "human_consumption": True,
            "hygienic_handling": True,
            "appropriate_storage": True,
            "contamination_free": True,
            "suitable_condition": True
        }
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_eligible"] is True
    assert data["status"] == "PASSED"

    # Ineligible check
    resp2 = client.post(
        "/api/donations/validate-safety-check",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "human_consumption": True,
            "hygienic_handling": False,
            "appropriate_storage": True,
            "contamination_free": True,
            "suitable_condition": True
        }
    )
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["is_eligible"] is False
    assert "hygienic_handling" in data2["failed_declarations"]


def test_05_create_donation_with_safety_check(db_session: Session):
    """Verifies that submitting safe declaration passes donation creation and populates safety metadata."""
    ts = int(datetime.now().timestamp())
    donor = User(
        name=f"Check Donor {ts}",
        email=f"check_donor_{ts}@test.com",
        password_hash=hash_password("Pass123!"),
        role="donor",
        is_active=True
    )
    db_session.add(donor)
    db_session.commit()
    token = create_access_token({"sub": str(donor.id), "role": "donor"})

    now = datetime.now(timezone.utc)
    prep_time = (now - timedelta(hours=1)).isoformat()
    expiry_time = (now + timedelta(hours=3)).isoformat()

    payload = {
        "food_name": "Vegetable Pulao",
        "food_type": "Rice",
        "food_category": "Cooked Food",
        "quantity": 30.0,
        "quantity_unit": "Meals",
        "preparation_time": prep_time,
        "expiry_time": expiry_time,
        "pickup_address": "Indiranagar, Bangalore",
        "safety_check_answers": {
            "human_consumption": True,
            "hygienic_handling": True,
            "appropriate_storage": True,
            "contamination_free": True,
            "suitable_condition": True
        }
    }

    resp = client.post(
        "/api/donations",
        headers={"Authorization": f"Bearer {token}"},
        json=payload
    )
    assert resp.status_code == 201
    created = resp.json()
    assert created["safety_check_completed"] is True
    assert created["safety_check_status"] == "PASSED"


def test_06_create_donation_unsafe_declaration_blocked(db_session: Session):
    """Verifies that submitting an unsafe declaration rejects donation creation with 400 Bad Request."""
    ts = int(datetime.now().timestamp())
    donor = User(
        name=f"Unsafe Donor {ts}",
        email=f"unsafe_donor_{ts}@test.com",
        password_hash=hash_password("Pass123!"),
        role="donor",
        is_active=True
    )
    db_session.add(donor)
    db_session.commit()
    token = create_access_token({"sub": str(donor.id), "role": "donor"})

    now = datetime.now(timezone.utc)
    prep_time = (now - timedelta(hours=1)).isoformat()
    expiry_time = (now + timedelta(hours=3)).isoformat()

    payload = {
        "food_name": "Spoiled Dairy Curry",
        "food_category": "Cooked Food",
        "quantity": 20.0,
        "quantity_unit": "Meals",
        "preparation_time": prep_time,
        "expiry_time": expiry_time,
        "pickup_address": "Indiranagar, Bangalore",
        "safety_check_answers": {
            "human_consumption": True,
            "hygienic_handling": True,
            "appropriate_storage": False,  # Declared inappropriate storage
            "contamination_free": True,
            "suitable_condition": False    # Declared unsuitable
        }
    }

    resp = client.post(
        "/api/donations",
        headers={"Authorization": f"Bearer {token}"},
        json=payload
    )
    assert resp.status_code == 400
    assert "not be suitable for donation" in resp.json()["detail"]
