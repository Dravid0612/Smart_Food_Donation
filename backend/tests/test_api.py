import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db.session import SessionLocal

client = TestClient(app)

def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert "Smart Food Donation" in response.json()["message"]

def test_login_donor():
    response = client.post("/api/auth/login", json={
        "email": "donor1@hotel.com",
        "password": "pass123"
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["role"] == "donor"
    assert data["name"] == "Taj Hotel Restaurant"

def test_login_ngo():
    response = client.post("/api/auth/login", json={
        "email": "ngo1@greenhope.org",
        "password": "pass123"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["role"] == "ngo"

def test_login_volunteer():
    response = client.post("/api/auth/login", json={
        "email": "vol1@volunteer.org",
        "password": "pass123"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["role"] == "volunteer"

def test_login_admin():
    response = client.post("/api/auth/login", json={
        "email": "admin@fooddonation.org",
        "password": "admin123"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["role"] == "admin"

def test_get_donations_unauthorized():
    response = client.get("/api/donations")
    assert response.status_code == 401

def test_get_donations_authorized():
    login_res = client.post("/api/auth/login", json={
        "email": "donor1@hotel.com",
        "password": "pass123"
    })
    token = login_res.json()["access_token"]
    
    response = client.get("/api/donations", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    donations = response.json()
    assert isinstance(donations, list)
    assert len(donations) > 0

def test_recommendation_algorithm():
    login_res = client.post("/api/auth/login", json={
        "email": "donor1@hotel.com",
        "password": "pass123"
    })
    token = login_res.json()["access_token"]
    
    donations = client.get("/api/donations", headers={"Authorization": f"Bearer {token}"}).json()
    donation_id = donations[0]["id"]

    rec_res = client.get(f"/api/donations/{donation_id}/recommend-ngo", headers={"Authorization": f"Bearer {token}"})
    assert rec_res.status_code == 200
    recommendations = rec_res.json()
    assert isinstance(recommendations, list)
    if len(recommendations) > 0:
        assert "score" in recommendations[0]
        assert "reason" in recommendations[0]
