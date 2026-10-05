"""
RouteService — Routing & Realistic ETA Abstraction
=================================================
Provides travel distance and ETA estimation for the Time-Aware Food Rescue Network.

Routing Engine Specifications:
- Provider Support:
    1. Heuristic / Urban Calibrated (Default / Testing / Offline Fallback)
    2. OSRM (Open Source Routing Machine - Self-hosted / Open endpoints)
    3. OpenRouteService (GeoJSON Routing API)
    4. Google Maps Distance Matrix API (Optional enterprise adapter)
- Speed & Urban Transit Calibration:
    - Urban motorcycle / scooter: ~20 km/h (3.0 minutes / km) + 3 min dispatch overhead
    - Urban van / car: ~15 km/h (4.0 minutes / km) + 5 min dispatch overhead
    - Bicycle: ~12 km/h (5.0 minutes / km) + 2 min dispatch overhead
    - Walking: ~4.5 km/h (13.3 minutes / km)
- Degraded / Fallback State:
    - If GPS coordinates are missing or external routing APIs fail/timeout, returns:
      `status: "ROUTE_ESTIMATE_UNAVAILABLE"` or degraded conservative heuristic with explicit flag.
- Cost & Rate Limits:
    - Heuristic: 0 cost, infinite throughput.
    - OpenRouteService: 2,000 free requests/day (40 req/min).
    - Google Distance Matrix: $5.00 per 1,000 elements after free tier.
"""

import math
import os
import logging
import threading
import time
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)

STATUS_AVAILABLE = "ROUTE_AVAILABLE"
STATUS_DEGRADED = "ROUTE_ESTIMATE_DEGRADED"
STATUS_UNAVAILABLE = "ROUTE_ESTIMATE_UNAVAILABLE"

# In-process routing cache, singleflight request coalescing, and telemetry
_route_cache: Dict[Tuple, Dict[str, Any]] = {}
_inflight_events: Dict[Tuple, threading.Event] = {}
_inflight_results: Dict[Tuple, Dict[str, Any]] = {}
_cache_lock = threading.Lock()

_routing_telemetry: Dict[str, int] = {
    "routing_requests": 0,
    "routing_cache_hits": 0,
    "routing_cache_misses": 0,
    "routing_coalesced_hits": 0,
    "routing_fallback_count": 0,
}

# Average transit speeds in urban Indian traffic conditions (km/h)
MODE_SPEED_KMH = {
    "bike": 20.0,
    "motorcycle": 20.0,
    "scooter": 20.0,
    "car": 15.0,
    "van": 15.0,
    "bicycle": 12.0,
    "walking": 4.5,
    "default": 18.0
}

# Base dispatch & navigation overhead in minutes
MODE_OVERHEAD_MIN = {
    "bike": 3.0,
    "motorcycle": 3.0,
    "scooter": 3.0,
    "car": 5.0,
    "van": 6.0,
    "bicycle": 2.0,
    "walking": 1.0,
    "default": 3.0
}


def haversine_distance_km(
    lat1: Optional[float],
    lon1: Optional[float],
    lat2: Optional[float],
    lon2: Optional[float]
) -> Optional[float]:
    """Calculates great-circle distance between two points in kilometers."""
    if lat1 is None or lon1 is None or lat2 is None or lon2 is None:
        return None
    try:
        r = 6371.0  # Earth radius in km
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = math.sin(dlat / 2.0) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2.0) ** 2
        c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
        return round(r * c, 2)
    except Exception:
        return None


def _make_cache_key(
    provider: str,
    origin_lat: float,
    origin_lon: float,
    dest_lat: float,
    dest_lon: float,
    transport_mode: str
) -> Tuple:
    """Creates a normalized cache key with coordinates quantized to 4 decimal places (~11 meters)."""
    return (
        provider.lower(),
        round(float(origin_lat), 4),
        round(float(origin_lon), 4),
        round(float(dest_lat), 4),
        round(float(dest_lon), 4),
        transport_mode.lower().strip()
    )


from app.core.config import settings
import httpx
from datetime import datetime, timezone


class RouteService:
    """
    Unified Routing & Logistics Abstraction.
    Supports real external road-routing providers (Google Maps Routes API, OSRM)
    with in-process TTL caching, singleflight request coalescing, and calibrated urban fallback.
    """

    def __init__(self, provider: Optional[str] = None):
        self.provider = (provider or os.getenv("ROUTING_PROVIDER", settings.ROUTING_PROVIDER)).lower()
        self.api_key = os.getenv("GOOGLE_MAPS_API_KEY", os.getenv("ROUTING_API_KEY", settings.GOOGLE_MAPS_API_KEY))
        self.timeout = float(os.getenv("ROUTING_TIMEOUT_SECONDS", str(settings.ROUTING_TIMEOUT_SECONDS)))

    @classmethod
    def get_telemetry(cls) -> Dict[str, int]:
        """Returns a snapshot of routing API usage counters."""
        with _cache_lock:
            return dict(_routing_telemetry)

    @classmethod
    def reset_telemetry(cls):
        """Resets routing API usage counters (used in testing)."""
        with _cache_lock:
            for k in _routing_telemetry:
                _routing_telemetry[k] = 0

    @classmethod
    def clear_cache(cls):
        """Clears the in-process route cache and pending coalescing events."""
        with _cache_lock:
            _route_cache.clear()
            _inflight_events.clear()
            _inflight_results.clear()

    @staticmethod
    def should_recalculate_route(
        last_routed_lat: Optional[float],
        last_routed_lon: Optional[float],
        current_lat: Optional[float],
        current_lon: Optional[float],
        min_movement_meters: Optional[float] = None
    ) -> bool:
        """
        Determines if volunteer movement is significant enough to warrant route recalculation.
        Suppresses redundant external API requests for stationary or minor GPS jitter.
        """
        if last_routed_lat is None or last_routed_lon is None:
            return True
        if current_lat is None or current_lon is None:
            return False

        threshold = min_movement_meters if min_movement_meters is not None else settings.ROUTING_MIN_MOVEMENT_METERS
        dist_km = haversine_distance_km(last_routed_lat, last_routed_lon, current_lat, current_lon)
        if dist_km is None:
            return True
        dist_meters = dist_km * 1000.0
        return dist_meters >= threshold

    def _call_google_routes(
        self,
        origin_lat: float,
        origin_lon: float,
        dest_lat: float,
        dest_lon: float,
        transport_mode: str
    ) -> Dict[str, Any]:
        """
        Queries Google Maps Platform Routes API (v2:computeRoutes) for real road travel distance and duration.
        Uses:
          - POST https://routes.googleapis.com/directions/v2:computeRoutes
          - Minimal Field Mask: routes.duration,routes.distanceMeters (NO unused legs/polylines/instructions)
          - travelMode = DRIVE (with TRAFFIC_AWARE)
        """
        mode_clean = transport_mode.lower().strip() if transport_mode else "bike"
        travel_mode = "DRIVE"
        routing_pref = "TRAFFIC_AWARE"

        if mode_clean in ["bicycle"]:
            travel_mode = "BICYCLE"
            routing_pref = None
        elif mode_clean in ["walking"]:
            travel_mode = "WALK"
            routing_pref = None
        else:
            travel_mode = "DRIVE"
            routing_pref = "TRAFFIC_AWARE"

        url = "https://routes.googleapis.com/directions/v2:computeRoutes"
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": "routes.duration,routes.distanceMeters",
        }
        payload = {
            "origin": {
                "location": {
                    "latLng": {
                        "latitude": float(origin_lat),
                        "longitude": float(origin_lon)
                    }
                }
            },
            "destination": {
                "location": {
                    "latLng": {
                        "latitude": float(dest_lat),
                        "longitude": float(dest_lon)
                    }
                }
            },
            "travelMode": travel_mode,
            "computeAlternativeRoutes": False,
            "routeModifiers": {
                "avoidTolls": False,
                "avoidHighways": False,
                "avoidFerries": False
            },
            "languageCode": "en-US",
            "units": "METRIC"
        }
        if routing_pref:
            payload["routingPreference"] = routing_pref

        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        routes = data.get("routes")
        if not routes:
            raise ValueError("No road route found between coordinates by Google Routes API.")

        route = routes[0]

        # Extract road distance (meters -> km)
        raw_distance = route.get("distanceMeters")
        if raw_distance is None and route.get("legs"):
            raw_distance = route["legs"][0].get("distanceMeters")
        distance_meters = float(raw_distance or 0.0)
        road_distance_km = round(distance_meters / 1000.0, 2)

        # Extract duration (string ending in 's' e.g. '1080s' or numeric)
        raw_duration = route.get("duration")
        if not raw_duration and route.get("legs"):
            raw_duration = route["legs"][0].get("duration")

        if isinstance(raw_duration, str):
            duration_seconds = float(raw_duration.rstrip("s"))
        elif isinstance(raw_duration, (int, float)):
            duration_seconds = float(raw_duration)
        else:
            duration_seconds = 0.0

        overhead = MODE_OVERHEAD_MIN.get(mode_clean, MODE_OVERHEAD_MIN["default"])
        travel_minutes = duration_seconds / 60.0
        total_eta_minutes = round(max(5.0, travel_minutes + overhead), 1)

        return {
            "distance_km": road_distance_km,
            "eta_minutes": int(round(total_eta_minutes)),
            "exact_minutes": total_eta_minutes,
            "transport_mode": mode_clean,
            "status": STATUS_AVAILABLE,
            "provider": "google",
            "source": "google_routes_api",
            "is_degraded": False,
            "overhead_minutes": overhead,
            "calculated_at": datetime.now(timezone.utc).isoformat()
        }

    # Backward compatibility alias
    _call_google_directions = _call_google_routes

    def _call_osrm_directions(
        self,
        origin_lat: float,
        origin_lon: float,
        dest_lat: float,
        dest_lon: float,
        transport_mode: str
    ) -> Dict[str, Any]:
        """
        Queries Open Source Routing Machine (OSRM) for real road distance and travel duration.
        """
        mode_clean = transport_mode.lower().strip() if transport_mode else "bike"
        url = f"http://router.project-osrm.org/route/v1/driving/{origin_lon},{origin_lat};{dest_lon},{dest_lat}?overview=false"

        with httpx.Client(timeout=self.timeout) as client:
            resp = client.get(url)
            resp.raise_for_status()
            data = resp.json()

        if data.get("code") != "Ok" or not data.get("routes"):
            raise ValueError(f"OSRM routing failed: {data.get('message', data.get('code'))}")

        route = data["routes"][0]
        road_distance_km = round(route["distance"] / 1000.0, 2)
        duration_seconds = route["duration"]
        overhead = MODE_OVERHEAD_MIN.get(mode_clean, MODE_OVERHEAD_MIN["default"])
        travel_minutes = duration_seconds / 60.0
        total_eta_minutes = round(max(5.0, travel_minutes + overhead), 1)

        return {
            "distance_km": road_distance_km,
            "eta_minutes": int(round(total_eta_minutes)),
            "exact_minutes": total_eta_minutes,
            "transport_mode": mode_clean,
            "status": STATUS_AVAILABLE,
            "provider": "osrm",
            "source": "osrm_api",
            "is_degraded": False,
            "overhead_minutes": overhead,
            "calculated_at": datetime.now(timezone.utc).isoformat()
        }

    def _calculate_heuristic(
        self,
        origin_lat: float,
        origin_lon: float,
        dest_lat: float,
        dest_lon: float,
        transport_mode: str,
        is_degraded: bool = False,
        message: Optional[str] = None,
        provider_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Calibrated urban heuristic fallback using Haversine * 1.3 road curvature.
        """
        mode_clean = transport_mode.lower().strip() if transport_mode else "bike"
        speed = MODE_SPEED_KMH.get(mode_clean, MODE_SPEED_KMH["default"])
        overhead = MODE_OVERHEAD_MIN.get(mode_clean, MODE_OVERHEAD_MIN["default"])

        straight_line = haversine_distance_km(origin_lat, origin_lon, dest_lat, dest_lon) or 5.0
        urban_road_factor = 1.3
        road_distance_km = round(straight_line * urban_road_factor, 2)

        travel_minutes = (road_distance_km / speed) * 60.0
        total_eta_minutes = round(max(5.0, travel_minutes + overhead), 1)

        prov = provider_name or self.provider
        status = STATUS_DEGRADED if is_degraded else STATUS_AVAILABLE

        return {
            "distance_km": road_distance_km,
            "straight_line_km": straight_line,
            "eta_minutes": int(round(total_eta_minutes)),
            "exact_minutes": total_eta_minutes,
            "transport_mode": mode_clean,
            "speed_kmh": speed,
            "overhead_minutes": overhead,
            "status": status,
            "provider": prov,
            "source": "urban_calibrated_heuristic",
            "is_degraded": is_degraded,
            "message": message or "Calculated via urban road network calibration.",
            "calculated_at": datetime.now(timezone.utc).isoformat()
        }

    def calculate_distance(
        self,
        origin_lat: Optional[float],
        origin_lon: Optional[float],
        dest_lat: Optional[float],
        dest_lon: Optional[float]
    ) -> Dict[str, Any]:
        """
        Calculates travel distance between origin and destination.
        Returns distance in km and status.
        """
        if origin_lat is None or origin_lon is None or dest_lat is None or dest_lon is None:
            return {
                "distance_km": 5.0,  # conservative fallback
                "status": STATUS_UNAVAILABLE,
                "provider": self.provider,
                "is_fallback": True,
                "is_degraded": True,
                "message": "GPS coordinates missing; default regional margin applied."
            }

        # If real external provider is configured, compute real distance via calculate_eta
        eta_res = self.calculate_eta(origin_lat, origin_lon, dest_lat, dest_lon)
        return {
            "distance_km": eta_res["distance_km"],
            "straight_line_km": haversine_distance_km(origin_lat, origin_lon, dest_lat, dest_lon),
            "status": eta_res["status"],
            "provider": eta_res["provider"],
            "is_fallback": eta_res.get("is_degraded", False),
            "is_degraded": eta_res.get("is_degraded", False),
            "message": eta_res.get("message", "Calculated distance.")
        }

    def _execute_provider_calculation(
        self,
        origin_lat: float,
        origin_lon: float,
        dest_lat: float,
        dest_lon: float,
        mode_clean: str
    ) -> Dict[str, Any]:
        """Executes the specific provider calculation (Google Routes API, OSRM, or calibrated heuristic)."""
        # 1. Google Maps Platform Routes Provider
        if self.provider == "google":
            if not self.api_key:
                logger.info("[RouteService] Google Maps API key not configured. Using calibrated urban heuristic fallback.")
                return self._calculate_heuristic(
                    origin_lat, origin_lon, dest_lat, dest_lon, mode_clean,
                    is_degraded=True,
                    message="Google Maps API key not configured; calibrated urban heuristic applied.",
                    provider_name="google"
                )
            try:
                return self._call_google_routes(origin_lat, origin_lon, dest_lat, dest_lon, mode_clean)
            except Exception as e:
                with _cache_lock:
                    _routing_telemetry["routing_fallback_count"] += 1
                logger.warning(f"[RouteService] Google routing request failed ({e}). Falling back to calibrated heuristic.")
                res = self._calculate_heuristic(
                    origin_lat, origin_lon, dest_lat, dest_lon, mode_clean,
                    is_degraded=True,
                    message=f"Google routing failed ({e}); calibrated urban heuristic applied.",
                    provider_name="google"
                )
                res["provider_error"] = str(e)
                return res

        # 2. Open Source Routing Machine (OSRM) Provider
        if self.provider == "osrm":
            try:
                return self._call_osrm_directions(origin_lat, origin_lon, dest_lat, dest_lon, mode_clean)
            except Exception as e:
                with _cache_lock:
                    _routing_telemetry["routing_fallback_count"] += 1
                logger.warning(f"[RouteService] OSRM routing request failed ({e}). Falling back to calibrated heuristic.")
                res = self._calculate_heuristic(
                    origin_lat, origin_lon, dest_lat, dest_lon, mode_clean,
                    is_degraded=True,
                    message=f"OSRM routing failed ({e}); calibrated urban heuristic applied.",
                    provider_name="osrm"
                )
                res["provider_error"] = str(e)
                return res

        # 3. Default Heuristic / Calibrated Mode
        return self._calculate_heuristic(
            origin_lat, origin_lon, dest_lat, dest_lon, mode_clean,
            is_degraded=False,
            message="Calculated via urban road network calibration.",
            provider_name="heuristic"
        )

    def calculate_eta(
        self,
        origin_lat: Optional[float],
        origin_lon: Optional[float],
        dest_lat: Optional[float],
        dest_lon: Optional[float],
        transport_mode: str = "bike",
        ttl_seconds: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Calculates realistic travel ETA in minutes based on real road routing or traffic calibration.
        Uses in-process caching (ROUTING_CACHE_TTL_SECONDS) and request coalescing (Singleflight).
        Uses external provider when configured (Google Maps / OSRM) with graceful degraded fallback.
        """
        mode_clean = transport_mode.lower().strip() if transport_mode else "bike"

        if origin_lat is None or origin_lon is None or dest_lat is None or dest_lon is None:
            return {
                "eta_minutes": 15,
                "exact_minutes": 15.0,
                "distance_km": 5.0,
                "transport_mode": mode_clean,
                "speed_kmh": MODE_SPEED_KMH.get(mode_clean, 18.0),
                "overhead_minutes": MODE_OVERHEAD_MIN.get(mode_clean, 3.0),
                "status": STATUS_UNAVAILABLE,
                "provider": self.provider,
                "is_degraded": True,
                "message": "GPS coordinates missing; default regional margin applied.",
                "calculated_at": datetime.now(timezone.utc).isoformat()
            }

        cache_key = _make_cache_key(self.provider, origin_lat, origin_lon, dest_lat, dest_lon, mode_clean)
        now_ts = time.time()

        # Step 1: In-process TTL Cache Check
        with _cache_lock:
            cached_entry = _route_cache.get(cache_key)
            if cached_entry and now_ts < cached_entry["expires_at"]:
                _routing_telemetry["routing_cache_hits"] += 1
                res = dict(cached_entry["data"])
                res["cache_hit"] = True
                return res

        # Step 2: Request Coalescing (Singleflight Pattern)
        is_leader = False
        event = None
        with _cache_lock:
            if cache_key in _inflight_events:
                event = _inflight_events[cache_key]
            else:
                is_leader = True
                event = threading.Event()
                _inflight_events[cache_key] = event

        if not is_leader:
            # Wait for leader thread to finish external call
            event.wait(timeout=self.timeout + 3.0)
            with _cache_lock:
                if cache_key in _inflight_results:
                    _routing_telemetry["routing_coalesced_hits"] += 1
                    res = dict(_inflight_results[cache_key])
                    res["coalesced"] = True
                    return res

        # Step 3: Provider Call (Leader Execution)
        try:
            with _cache_lock:
                _routing_telemetry["routing_cache_misses"] += 1
                _routing_telemetry["routing_requests"] += 1

            result = self._execute_provider_calculation(origin_lat, origin_lon, dest_lat, dest_lon, mode_clean)

            # Store in cache with configurable TTL (only cache successful, non-degraded routes)
            if result.get("status") == STATUS_AVAILABLE and not result.get("is_degraded"):
                ttl = ttl_seconds if ttl_seconds is not None else settings.ROUTING_CACHE_TTL_SECONDS
                with _cache_lock:
                    _route_cache[cache_key] = {
                        "data": result,
                        "timestamp": now_ts,
                        "expires_at": now_ts + ttl
                    }
            with _cache_lock:
                _inflight_results[cache_key] = result
            return result
        finally:
            if is_leader:
                with _cache_lock:
                    if cache_key in _inflight_events:
                        _inflight_events[cache_key].set()
                        del _inflight_events[cache_key]


# Global singleton instance
route_service = RouteService()

