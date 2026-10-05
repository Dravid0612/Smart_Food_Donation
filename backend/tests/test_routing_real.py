"""
Comprehensive Unit & Integration Test Suite: Real Road Routing (Google Routes API & OSRM)
========================================================================================
Validates the RouteService external routing integration:
1. Google Maps Platform Routes API (REST endpoint v2:computeRoutes)
2. Open Source Routing Machine (OSRM)
3. Calibrated urban heuristic fallback policies

Required Test Proofs:
1. Google Routes API request structure (POST, X-Goog-Api-Key, X-Goog-FieldMask, travelMode=DRIVE, traffic-aware)
2. Duration extraction (string 's' parsing + vehicle overhead)
3. Distance extraction (distanceMeters -> km)
4. Provider failure handling (timeout, 500/503, empty routes)
5. Fallback identification (urban_calibrated_heuristic, is_degraded=True, never fake road ETA)
6. Feasibility integration (RematchingService window feasibility check)
7. Rematching integration (dynamic volunteer candidate evaluation)
"""

import pytest
import httpx
from unittest.mock import patch, MagicMock
from app.services.route_service import (
    RouteService,
    haversine_distance_km,
    STATUS_AVAILABLE,
    STATUS_DEGRADED,
    STATUS_UNAVAILABLE,
)
from app.services.rematching_service import RematchingService
from app.models.models import FoodDonation, User, VolunteerAssignment
from datetime import datetime, timezone, timedelta
import time


@pytest.fixture(autouse=True)
def clean_route_cache():
    RouteService.clear_cache()
    RouteService.reset_telemetry()
    yield
    RouteService.clear_cache()
    RouteService.reset_telemetry()


# Sample Google Maps Platform Routes API v2:computeRoutes mock response
MOCK_GOOGLE_ROUTES_OK_RESPONSE = {
    "routes": [
        {
            "distanceMeters": 8500,
            "duration": "1080s",
            "legs": [
                {
                    "distanceMeters": 8500,
                    "duration": "1080s"
                }
            ]
        }
    ]
}

# Sample OSRM mock response
MOCK_OSRM_OK_RESPONSE = {
    "code": "Ok",
    "routes": [
        {
            "distance": 6200.0,
            "duration": 720.0
        }
    ]
}


# ─── 1. Google Routes API Request Structure ──────────────────────────────────

def test_1_google_routes_api_request_structure():
    """
    Proves:
    - POST https://routes.googleapis.com/directions/v2:computeRoutes
    - Headers: X-Goog-Api-Key and X-Goog-FieldMask
    - Payload: travelMode = DRIVE, routingPreference = TRAFFIC_AWARE, lat/lon structure
    """
    service = RouteService(provider="google")
    service.api_key = "test-mock-api-key"

    with patch("httpx.Client.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = MOCK_GOOGLE_ROUTES_OK_RESPONSE
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        res = service.calculate_eta(12.9716, 77.5946, 13.0358, 77.5970, transport_mode="bike")

        # Verify POST method and URL
        assert mock_post.called
        call_url, call_kwargs = mock_post.call_args[0][0], mock_post.call_args[1]
        assert call_url == "https://routes.googleapis.com/directions/v2:computeRoutes"

        # Verify Headers
        headers = call_kwargs.get("headers", {})
        assert headers.get("X-Goog-Api-Key") == "test-mock-api-key"
        assert "X-Goog-FieldMask" in headers
        assert "routes.duration" in headers["X-Goog-FieldMask"]
        assert "routes.distanceMeters" in headers["X-Goog-FieldMask"]

        # Verify Payload
        payload = call_kwargs.get("json", {})
        assert payload["origin"]["location"]["latLng"]["latitude"] == 12.9716
        assert payload["origin"]["location"]["latLng"]["longitude"] == 77.5946
        assert payload["destination"]["location"]["latLng"]["latitude"] == 13.0358
        assert payload["destination"]["location"]["latLng"]["longitude"] == 77.5970
        assert payload["travelMode"] == "DRIVE"
        assert payload["routingPreference"] == "TRAFFIC_AWARE"
        assert payload["units"] == "METRIC"

        # Verify Response Mapping
        assert res["status"] == STATUS_AVAILABLE
        assert res["provider"] == "google"
        assert res["source"] == "google_routes_api"
        assert res["is_degraded"] is False


# ─── 2. Duration Extraction ──────────────────────────────────────────────────

def test_2_duration_extraction():
    """
    Proves:
    - Parses string duration with 's' suffix (e.g. '600s' = 10 min)
    - Adds transport mode dispatch overhead (e.g. car = 5 min overhead -> 15 min total)
    """
    service = RouteService(provider="google")
    service.api_key = "test-mock-api-key"

    with patch("httpx.Client.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "routes": [
                {
                    "distanceMeters": 4000,
                    "duration": "600s"  # 10 minutes road time
                }
            ]
        }
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        # car has 5 min dispatch overhead -> 10 min travel + 5 min overhead = 15 min
        res = service.calculate_eta(12.9716, 77.5946, 12.9352, 77.6245, transport_mode="car")
        assert res["eta_minutes"] == 15
        assert res["exact_minutes"] == 15.0
        assert res["overhead_minutes"] == 5.0
        assert res["transport_mode"] == "car"


# ─── 3. Distance Extraction ──────────────────────────────────────────────────

def test_3_distance_extraction():
    """
    Proves:
    - Extracts distanceMeters (8500) and converts to road_distance_km (8.5 km)
    - Both calculate_distance and calculate_eta return the road distance
    """
    service = RouteService(provider="google")
    service.api_key = "test-mock-api-key"

    with patch("httpx.Client.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = MOCK_GOOGLE_ROUTES_OK_RESPONSE
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        dist_res = service.calculate_distance(12.9716, 77.5946, 13.0358, 77.5970)
        assert dist_res["distance_km"] == 8.5
        assert dist_res["status"] == STATUS_AVAILABLE
        assert dist_res["is_degraded"] is False


# ─── 4. Provider Failure Handling ────────────────────────────────────────────

def test_4_provider_failure_handling():
    """
    Proves:
    - Provider timeout degrades gracefully to calibrated heuristic without unhandled exception
    - HTTP 500/503 service error degrades gracefully
    - Empty routes response degrades gracefully
    """
    service = RouteService(provider="google")
    service.api_key = "test-mock-api-key"

    # 4a. Timeout handling
    with patch("httpx.Client.post", side_effect=httpx.TimeoutException("Routes API timeout")):
        res_timeout = service.calculate_eta(12.9716, 77.5946, 13.0358, 77.5970)
        assert res_timeout["status"] == STATUS_DEGRADED
        assert res_timeout["is_degraded"] is True
        assert res_timeout["source"] == "urban_calibrated_heuristic"
        assert res_timeout["eta_minutes"] >= 5

    # 4b. HTTP 503 Service Unavailable
    with patch("httpx.Client.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 503
        mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError("503 Service Unavailable", request=MagicMock(), response=mock_resp)
        mock_post.return_value = mock_resp

        res_503 = service.calculate_eta(12.9716, 77.5946, 13.0358, 77.5970)
        assert res_503["status"] == STATUS_DEGRADED
        assert res_503["is_degraded"] is True
        assert res_503["source"] == "urban_calibrated_heuristic"

    # 4c. Empty routes array
    with patch("httpx.Client.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"routes": []}
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        res_empty = service.calculate_eta(12.9716, 77.5946, 13.0358, 77.5970)
        assert res_empty["status"] == STATUS_DEGRADED
        assert res_empty["is_degraded"] is True
        assert "no road route found" in res_empty.get("provider_error", "").lower()


# ─── 5. Fallback Identification ──────────────────────────────────────────────

def test_5_fallback_identification():
    """
    Proves:
    - Calibrated heuristic explicitly identifies as 'urban_calibrated_heuristic'
    - Degraded responses have is_degraded=True
    - Fallback is NEVER mislabeled as 'google_routes_api' or 'real road ETA'
    """
    # Unconfigured key
    service_unconfigured = RouteService(provider="google")
    service_unconfigured.api_key = ""

    res_unconf = service_unconfigured.calculate_eta(12.9716, 77.5946, 13.0358, 77.5970)
    assert res_unconf["status"] == STATUS_DEGRADED
    assert res_unconf["is_degraded"] is True
    assert res_unconf["source"] == "urban_calibrated_heuristic"
    assert res_unconf["source"] != "google_routes_api"
    assert "not configured" in res_unconf["message"]

    # Explicit heuristic provider
    service_heuristic = RouteService(provider="heuristic")
    res_heuristic = service_heuristic.calculate_eta(12.9716, 77.5946, 13.0358, 77.5970)
    assert res_heuristic["source"] == "urban_calibrated_heuristic"
    assert res_heuristic["source"] != "google_routes_api"
    assert res_heuristic["provider"] == "heuristic"


# ─── 6. Feasibility Integration ──────────────────────────────────────────────

def test_6_feasibility_integration():
    """
    Proves:
    - RematchingService uses the road routing ETA to determine window feasibility
    - Fast ETA -> RESCUE_FEASIBLE
    - Excessive ETA exceeding window -> AT_RISK / RESCUE_UNLIKELY
    """
    now = datetime.now(timezone.utc)
    vol = MagicMock(id=1, name="Courier Hero", vehicle_type="bike", latitude=12.9500, longitude=77.5800)
    ngo = MagicMock(id=2, name="City Shelter", latitude=12.9900, longitude=77.6000)

    # 6a. Feasible assignment (90 min window, 15 min road travel)
    donation_feasible = MagicMock(
        id=10,
        food_name="Fresh Meals",
        latitude=12.9716,
        longitude=77.5946,
        estimated_window_end=now + timedelta(minutes=90),
        expiry_time=now + timedelta(minutes=90),
        remaining_minutes=90,
        status="volunteer_assigned",
        assigned_ngo=ngo
    )

    with patch("app.services.rematching_service.route_service.calculate_eta") as mock_eta:
        mock_eta.return_value = {
            "eta_minutes": 15,
            "status": STATUS_AVAILABLE,
            "provider": "google",
            "source": "google_routes_api",
            "is_degraded": False
        }

        res = RematchingService.evaluate_assignment_feasibility(
            db=MagicMock(),
            donation=donation_feasible,
            volunteer=vol,
            reference_time=now
        )
        assert res["is_feasible"] is True
        assert res["feasibility_status"] == "RESCUE_FEASIBLE"
        assert res["buffer_remaining_minutes"] > 0

    # 6b. Infeasible assignment (25 min window, 35 min road travel)
    donation_infeasible = MagicMock(
        id=11,
        food_name="Urgent Surplus",
        latitude=12.9716,
        longitude=77.5946,
        estimated_window_end=now + timedelta(minutes=25),
        expiry_time=now + timedelta(minutes=25),
        remaining_minutes=25,
        status="volunteer_assigned",
        assigned_ngo=ngo
    )

    with patch("app.services.rematching_service.route_service.calculate_eta") as mock_eta:
        mock_eta.return_value = {
            "eta_minutes": 35,
            "status": STATUS_AVAILABLE,
            "provider": "google",
            "source": "google_routes_api",
            "is_degraded": False
        }

        res_inf = RematchingService.evaluate_assignment_feasibility(
            db=MagicMock(),
            donation=donation_infeasible,
            volunteer=vol,
            reference_time=now
        )
        assert res_inf["is_feasible"] is False
        assert res_inf["feasibility_status"] in ["AT_RISK", "RESCUE_UNLIKELY"]
        assert res_inf["buffer_remaining_minutes"] < 0


# ─── 7. Rematching Integration ───────────────────────────────────────────────

def test_7_rematching_integration():
    """
    Proves:
    - Rematching workflow calls calculate_eta to evaluate volunteer candidates
    - Selected candidate uses route_service ETA
    """
    now = datetime.now(timezone.utc)
    ngo = MagicMock(id=2, name="North Shelter", latitude=13.0500, longitude=77.6000)
    donation = MagicMock(
        id=20,
        food_name="Catering Surplus",
        latitude=12.9716,
        longitude=77.5946,
        estimated_window_end=now + timedelta(minutes=60),
        expiry_time=now + timedelta(minutes=60),
        remaining_minutes=60,
        status="volunteer_assigned",
        assigned_ngo=ngo
    )
    cand_vol = MagicMock(id=5, name="Candidate Courier", latitude=12.9600, longitude=77.5900, vehicle_type="bike")

    with patch("app.services.rematching_service.route_service.calculate_eta") as mock_eta:
        mock_eta.return_value = {
            "eta_minutes": 12,
            "status": STATUS_AVAILABLE,
            "provider": "google",
            "source": "google_routes_api",
            "is_degraded": False
        }

        feas = RematchingService.evaluate_assignment_feasibility(
            db=MagicMock(),
            donation=donation,
            volunteer=cand_vol,
            reference_time=now
        )

        assert feas["is_feasible"] is True
        assert feas["eta_to_donor_minutes"] == 12.0


# ─── 8. Volunteer → Donor & Donor → NGO Google Routes Invocations ─────────────

def test_8_volunteer_to_donor_and_donor_to_ngo_eta():
    """
    Proves:
    - Volunteer -> Donor leg uses Routes API
    - Donor -> NGO leg uses Routes API
    """
    service = RouteService(provider="google")
    service.api_key = "test-mock-api-key"

    # Volunteer -> Donor
    with patch("httpx.Client.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "routes": [{"distanceMeters": 5200, "duration": "720s"}]  # 12 min
        }
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        vol_eta = service.calculate_eta(12.9279, 77.6271, 12.9716, 77.5946, transport_mode="motorcycle")
        assert vol_eta["distance_km"] == 5.2
        assert vol_eta["eta_minutes"] == 15  # 12 min + 3 min overhead

    # Donor -> NGO
    with patch("httpx.Client.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "routes": [{"distanceMeters": 9000, "duration": "1200s"}]  # 20 min
        }
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        ngo_eta = service.calculate_eta(12.9716, 77.5946, 13.0358, 77.5970, transport_mode="van")
        assert ngo_eta["distance_km"] == 9.0
        assert ngo_eta["eta_minutes"] == 26  # 20 min + 6 min overhead


# ─── 9. OSRM Routing Provider Support ────────────────────────────────────────

def test_9_osrm_routing_provider():
    """
    Proves:
    - OSRM provider remains supported as an open alternative
    - GET request to OSRM endpoint calculates real distance & duration
    """
    service = RouteService(provider="osrm")

    with patch("httpx.Client.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = MOCK_OSRM_OK_RESPONSE
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        res = service.calculate_eta(12.9716, 77.5946, 13.0358, 77.5970)
        assert res["status"] == STATUS_AVAILABLE
        assert res["provider"] == "osrm"
        assert res["source"] == "osrm_api"
        assert res["distance_km"] == 6.2
        assert res["is_degraded"] is False


# ─── 10. Haversine Distance & Proximity Filtering Still Works ────────────────

def test_10_haversine_distance_proximity_filtering():
    """
    Proves:
    - Haversine great-circle calculation remains intact for radial filtering
    - Missing coordinates safely return None
    """
    # Bengaluru MG Road to Bengaluru Airport (~28 km straight line)
    d = haversine_distance_km(12.9716, 77.5946, 13.1986, 77.7066)
    assert d is not None
    assert 25.0 <= d <= 32.0

    # Missing coordinates return None
    assert haversine_distance_km(None, 77.5946, 13.1986, 77.7066) is None
    assert haversine_distance_km(12.9716, 77.5946, None, None) is None


# ─── 11. Cache Hit Causes Zero External Calls ────────────────────────────────

def test_11_cache_hit_zero_external_calls():
    """
    Proves:
    - First call queries external provider and populates in-process cache
    - Second identical call returns cached result without making any HTTP request
    - Telemetry counts cache hits and misses accurately
    """
    service = RouteService(provider="google")
    service.api_key = "test-mock-api-key"

    with patch("httpx.Client.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = MOCK_GOOGLE_ROUTES_OK_RESPONSE
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        # 1st call: cache miss -> external call
        res1 = service.calculate_eta(12.9716, 77.5946, 13.0358, 77.5970, transport_mode="bike")
        assert mock_post.call_count == 1
        assert res1.get("cache_hit") is not True

        # 2nd call: cache hit -> 0 external calls
        res2 = service.calculate_eta(12.9716, 77.5946, 13.0358, 77.5970, transport_mode="bike")
        assert mock_post.call_count == 1  # External call count remains 1
        assert res2.get("cache_hit") is True
        assert res2["distance_km"] == res1["distance_km"]
        assert res2["eta_minutes"] == res1["eta_minutes"]

        telemetry = RouteService.get_telemetry()
        assert telemetry["routing_cache_hits"] >= 1
        assert telemetry["routing_cache_misses"] == 1
        assert telemetry["routing_requests"] == 1


# ─── 12. Request Coalescing (Singleflight) ───────────────────────────────────

def test_12_request_coalescing_single_external_call():
    """
    Proves:
    - Multiple concurrent callers for identical route result in exactly ONE external request
    - All callers receive identical correct routing results
    - routing_coalesced_hits telemetry counter increments
    """
    import threading
    service = RouteService(provider="google")
    service.api_key = "test-mock-api-key"

    call_count = 0
    def slow_post(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        time.sleep(0.05)
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = MOCK_GOOGLE_ROUTES_OK_RESPONSE
        mock_resp.raise_for_status = MagicMock()
        return mock_resp

    with patch("httpx.Client.post", side_effect=slow_post):
        results = []
        def caller():
            r = service.calculate_eta(12.9500, 77.5800, 13.0000, 77.6000, transport_mode="motorcycle")
            results.append(r)

        threads = [threading.Thread(target=caller) for _ in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Exactly 1 external call made across all 3 concurrent requests
        assert call_count == 1
        assert len(results) == 3
        for r in results:
            assert r["status"] == STATUS_AVAILABLE
            assert r["distance_km"] == 8.5
        telemetry = RouteService.get_telemetry()
        assert telemetry["routing_coalesced_hits"] >= 1


# ─── 13. Movement Below Threshold Causes Zero Recalculation ─────────────────

def test_13_movement_below_threshold_zero_recalculation():
    """
    Proves:
    - Movement below ROUTING_MIN_MOVEMENT_METERS (500m) returns False
    - Significant movement (>= 500m) returns True
    - Prevents GPS jitter from hammering external routing API
    """
    # 50 meters movement: 12.9716, 77.5946 -> 12.9720, 77.5946 (~44 meters)
    should_recalc = RouteService.should_recalculate_route(
        last_routed_lat=12.9716,
        last_routed_lon=77.5946,
        current_lat=12.9720,
        current_lon=77.5946,
        min_movement_meters=500.0
    )
    assert should_recalc is False

    # Significant movement: 12.9716 -> 12.9900 (~2000 meters)
    should_recalc_large = RouteService.should_recalculate_route(
        last_routed_lat=12.9716,
        last_routed_lon=77.5946,
        current_lat=12.9900,
        current_lon=77.5946,
        min_movement_meters=500.0
    )
    assert should_recalc_large is True


# ─── 14. Stale Route Triggers New External Request ───────────────────────────

def test_14_stale_route_triggers_new_request():
    """
    Proves:
    - Route expires after TTL and triggers exactly one fresh external request
    """
    service = RouteService(provider="google")
    service.api_key = "test-mock-api-key"

    with patch("httpx.Client.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = MOCK_GOOGLE_ROUTES_OK_RESPONSE
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        # Call with 1-second TTL
        service.calculate_eta(12.9100, 77.6000, 12.9500, 77.6200, transport_mode="car", ttl_seconds=1)
        assert mock_post.call_count == 1

        # Simulate expiration
        from app.services.route_service import _route_cache, _cache_lock
        with _cache_lock:
            for k in _route_cache:
                _route_cache[k]["expires_at"] = time.time() - 10

        # After expiration, next call must fetch a fresh route
        service.calculate_eta(12.9100, 77.6000, 12.9500, 77.6200, transport_mode="car", ttl_seconds=1)
        assert mock_post.call_count == 2


# ─── 15. Rematching Bounds Candidates to Max Limit ───────────────────────────

def test_15_rematching_bounds_candidates_to_max_limit():
    """
    Proves:
    - Rematching evaluates at most ROUTING_MAX_CANDIDATES_PER_REMATCH (5) candidates via external route calls
    - Eliminates routing storms when many volunteers are registered
    """
    from app.services.rematching_service import RematchingService
    from app.core.config import settings
    now = datetime.now(timezone.utc)

    db_mock = MagicMock()
    volunteers = []
    for i in range(15):
        v = MagicMock()
        v.id = 100 + i
        v.name = f"Candidate Vol {i}"
        v.role = "volunteer"
        v.is_active = True
        v.is_restricted = False
        v.status = "available"
        v.vehicle_type = "bike"
        v.latitude = 12.9700 + (i * 0.005)
        v.longitude = 77.5900 + (i * 0.005)
        v.carrying_capacity = 50.0
        v.reliability_score = 95.0
        volunteers.append(v)

    db_mock.query.return_value.filter.return_value.all.return_value = volunteers
    db_mock.query.return_value.filter.return_value.first.return_value = None
    db_mock.query.return_value.filter.return_value.count.return_value = 0

    ngo = MagicMock(id=99, latitude=13.0100, longitude=77.6100)
    donation = MagicMock(
        id=50,
        food_name="Bulk Rice & Curry",
        latitude=12.9716,
        longitude=77.5946,
        estimated_window_end=now + timedelta(minutes=120),
        expiry_time=now + timedelta(minutes=120),
        remaining_minutes=120,
        status="volunteer_assigned",
        assigned_ngo=ngo,
        quantity=10.0,
        quantity_kg=10.0
    )

    eta_calls = 0
    def mock_eta(*args, **kwargs):
        nonlocal eta_calls
        eta_calls += 1
        return {
            "eta_minutes": 10,
            "distance_km": 3.5,
            "status": STATUS_AVAILABLE,
            "provider": "google",
            "source": "google_routes_api",
            "is_degraded": False
        }

    with patch("app.services.rematching_service.route_service.calculate_eta", side_effect=mock_eta):
        feasible_vols = RematchingService.find_feasible_backup_volunteers(
            db=db_mock,
            donation=donation
        )
        # 1 call for donor->NGO leg + at most 5 candidate volunteer->donor calls <= 6
        assert eta_calls <= (settings.ROUTING_MAX_CANDIDATES_PER_REMATCH + 1)


# ─── 16. Provider Failure Does Not Loop ──────────────────────────────────────

def test_16_provider_failure_does_not_loop():
    """
    Proves:
    - Provider failure degrades gracefully to heuristic immediately without endless retry loops
    - Increments routing_fallback_count telemetry
    """
    service = RouteService(provider="google")
    service.api_key = "test-mock-api-key"

    with patch("httpx.Client.post", side_effect=httpx.ConnectError("Network unreachable")):
        res = service.calculate_eta(12.9716, 77.5946, 13.0358, 77.5970)
        assert res["status"] == STATUS_DEGRADED
        assert res["is_degraded"] is True
        assert res["source"] == "urban_calibrated_heuristic"
        telemetry = RouteService.get_telemetry()
        assert telemetry["routing_fallback_count"] == 1
