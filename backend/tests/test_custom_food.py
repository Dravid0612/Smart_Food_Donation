import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from app.main import app
from app.services.food_knowledge_rules import (
    calculate_rule_coverage,
    estimate_equivalent_meals,
    resolve_food_profile,
    normalize_category_key
)
from app.services.food_rescue_window_service import evaluate_food_rescue_window

client = TestClient(app)

@pytest.fixture
def donor_auth_token():
    # Login as donor
    res = client.post("/api/auth/login", json={"email": "donor1@hotel.com", "password": "pass123"})
    assert res.status_code == 200
    return res.json()["access_token"]

@pytest.fixture
def ngo_auth_token():
    res = client.post("/api/auth/login", json={"email": "ngo1@greenhope.org", "password": "pass123"})
    assert res.status_code == 200
    return res.json()["access_token"]

@pytest.fixture
def admin_auth_token():
    res = client.post("/api/auth/login", json={"email": "admin@fooddonation.org", "password": "admin123"})
    assert res.status_code == 200
    return res.json()["access_token"]

def test_01_known_food_rule_coverage():
    assert calculate_rule_coverage("Rice", "Cooked Food", is_custom=False) == "HIGH"
    assert calculate_rule_coverage("Biryani", "Cooked Food", is_custom=False) == "HIGH"
    assert calculate_rule_coverage("Idli", "Cooked Food", is_custom=False) == "HIGH"

def test_02_custom_food_rule_coverage_medium():
    assert calculate_rule_coverage("Vegetable Pongal", "cooked_rice_grain", is_custom=True) == "MEDIUM"
    assert calculate_rule_coverage("Grandma's Curry", "curry_gravy", is_custom=True) == "MEDIUM"
    assert calculate_rule_coverage("Samosas", "snack_fried", is_custom=True) == "MEDIUM"

def test_03_custom_food_rule_coverage_low():
    assert calculate_rule_coverage("Mystery Dish", "not_sure", is_custom=True) == "LOW"
    assert calculate_rule_coverage("Special Mix", "Other", is_custom=True) == "LOW"

def test_04_equivalent_meals_estimation():
    # 1:1 units
    assert estimate_equivalent_meals(50, "Meals") == 50.0
    assert estimate_equivalent_meals(20, "Portions") == 20.0
    assert estimate_equivalent_meals(15, "Plates") == 15.0

    # Weight
    assert estimate_equivalent_meals(5.0, "Kg") == 11.1
    assert estimate_equivalent_meals(500, "Grams") == 1.1

    # Volume
    assert estimate_equivalent_meals(10.0, "Litres") == 25.0
    assert estimate_equivalent_meals(1000, "mL") == 2.5

    # Discrete / Containers
    assert estimate_equivalent_meals(3, "Trays") == 45.0
    assert estimate_equivalent_meals(5, "Containers") == 25.0
    assert estimate_equivalent_meals(4, "Bottles") == 8.0
    assert estimate_equivalent_meals(20, "Pieces") == 20.0

def test_05_custom_food_rescue_window_evaluation():
    now = datetime.now(timezone.utc)
    prep_time = now - timedelta(hours=3) # Prepared 3 hours ago

    # Pongal (cooked rice grain category)
    eval_res = evaluate_food_rescue_window(
        food_type="Vegetable Pongal",
        food_category="cooked_rice_grain",
        prepared_at=prep_time,
        storage_method="Room Temperature",
        is_custom=True,
        current_time=now
    )
    assert eval_res["is_custom"] is True
    assert eval_res["rule_coverage"] == "MEDIUM"
    assert eval_res["visual_condition"] == "GOOD"
    assert eval_res["urgency_level"] in ["URGENT", "CRITICAL"] # 3h elapsed of 3.5h base -> ~30m left
    assert "Custom food evaluated" in " ".join(eval_res["reasons"])

def test_06_create_custom_food_donation_api(donor_auth_token):
    now = datetime.now(timezone.utc)
    prep_time = now - timedelta(hours=2)
    expiry = now + timedelta(hours=4)

    payload = {
        "food_name": "Vegetable Pongal",
        "food_source": "CUSTOM",
        "custom_food_name": "Vegetable Pongal",
        "food_description": "South Indian rice and yellow lentil dish with mild pepper and cashews",
        "major_ingredients": "rice, moong dal, pepper, ghee, cashews",
        "food_category": "cooked_rice_grain",
        "quantity": 5.0,
        "quantity_unit": "Containers",
        "quantity_unit_label": "Large Hot-Packs",
        "preparation_time": prep_time.isoformat(),
        "expiry_time": expiry.isoformat(),
        "pickup_address": "Indiranagar 100ft Road, Bengaluru",
        "storage_method": "Room Temperature",
        "storage_duration_hours": 2.0,
        "packaging_condition": "Covered",
        "previously_served": "No",
        "exposure_status": "No",
        "handling_status": "No"
    }

    res = client.post(
        "/api/donations",
        json=payload,
        headers={"Authorization": f"Bearer {donor_auth_token}"}
    )
    assert res.status_code == 201
    data = res.json()
    assert data["food_source"] == "CUSTOM"
    assert data["custom_food_name"] == "Vegetable Pongal"
    assert data["food_description"] == "South Indian rice and yellow lentil dish with mild pepper and cashews"
    assert data["quantity_unit"] == "Containers"
    assert data["quantity_unit_label"] == "Large Hot-Packs"
    assert data["estimated_meals"] == 25.0 # 5 containers * 5 meals
    assert data["rule_coverage"] == "MEDIUM"
    assert data["rescue_urgency_level"] in ["APPROACHING", "URGENT", "CRITICAL"]

def test_07_zero_and_negative_quantity_rejected(donor_auth_token):
    now = datetime.now(timezone.utc)
    prep_time = now - timedelta(hours=1)
    expiry = now + timedelta(hours=4)

    payload_zero = {
        "food_name": "Samosas",
        "food_category": "snack_fried",
        "quantity": 0,
        "quantity_unit": "Pieces",
        "preparation_time": prep_time.isoformat(),
        "expiry_time": expiry.isoformat(),
        "pickup_address": "MG Road, Bengaluru"
    }
    res = client.post(
        "/api/donations",
        json=payload_zero,
        headers={"Authorization": f"Bearer {donor_auth_token}"}
    )
    assert res.status_code == 400

    payload_neg = dict(payload_zero, quantity=-10)
    res_neg = client.post(
        "/api/donations",
        json=payload_neg,
        headers={"Authorization": f"Bearer {donor_auth_token}"}
    )
    assert res_neg.status_code == 400

def test_08_decimal_quantities_accepted(donor_auth_token):
    now = datetime.now(timezone.utc)
    prep_time = now - timedelta(hours=1)
    expiry = now + timedelta(hours=4)

    payload_decimal = {
        "food_name": "Tomato Dal",
        "food_source": "CUSTOM",
        "custom_food_name": "Tomato Dal",
        "food_category": "dal_lentil",
        "quantity": 3.5,
        "quantity_unit": "Litres",
        "preparation_time": prep_time.isoformat(),
        "expiry_time": expiry.isoformat(),
        "pickup_address": "Jayanagar 4th Block, Bengaluru"
    }
    res = client.post(
        "/api/donations",
        json=payload_decimal,
        headers={"Authorization": f"Bearer {donor_auth_token}"}
    )
    assert res.status_code == 201
    data = res.json()
    assert data["quantity"] == 3.5
    assert data["quantity_unit"] == "Litres"
    assert data["estimated_meals"] == 8.8 # 3.5 * 2.5

def test_09_donor_my_foods_personal_library(donor_auth_token):
    # Retrieve donor's my-foods list
    res = client.get(
        "/api/donations/my-foods",
        headers={"Authorization": f"Bearer {donor_auth_token}"}
    )
    assert res.status_code == 200
    my_foods = res.json()
    assert isinstance(my_foods, list)
    # The previously created custom donation (Vegetable Pongal or Tomato Dal) should be recorded
    names = [f["name"].lower() for f in my_foods]
    assert any("pongal" in n or "dal" in n for n in names)

    # Manually add a custom food to library
    add_payload = {
        "name": "Lemon Rice Deluxe",
        "food_category": "cooked_rice_grain",
        "description": "Turmeric-infused rice with roasted peanuts and curry leaves",
        "major_ingredients": "rice, lemon juice, peanuts, spices",
        "common_storage": "Room Temperature",
        "default_unit": "Portions"
    }
    create_res = client.post(
        "/api/donations/my-foods",
        json=add_payload,
        headers={"Authorization": f"Bearer {donor_auth_token}"}
    )
    assert create_res.status_code == 201
    created_item = create_res.json()
    assert created_item["name"] == "Lemon Rice Deluxe"
    assert created_item["default_unit"] == "Portions"

    # Delete custom food from library
    del_res = client.delete(
        f"/api/donations/my-foods/{created_item['id']}",
        headers={"Authorization": f"Bearer {donor_auth_token}"}
    )
    assert del_res.status_code == 200

def test_10_admin_custom_foods_queue(admin_auth_token):
    res = client.get(
        "/api/donations/admin/custom-foods-queue",
        headers={"Authorization": f"Bearer {admin_auth_token}"}
    )
    assert res.status_code == 200
    queue = res.json()
    assert isinstance(queue, list)
    # Each entry in queue should have food_name, count, suggested_category
    for item in queue:
        assert "food_name" in item
        assert "count" in item
        assert "suggested_category" in item
