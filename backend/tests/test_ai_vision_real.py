"""
AI Vision & Multimodal Analysis Test Suite — Smart Food Rescue Platform
========================================================================
Validates all 14 mandatory AI Vision requirements:
1. Filename cannot determine result
2. Hash cannot determine result
3. Actual image bytes are passed to provider
4. One image works
5. Two images work
6. Three images work
7. Unclear image yields UNCERTAIN condition
8. Conflicting images yield conservative result
9. Provider timeout yields safe degraded result
10. Provider malformed response yields safe failure
11. No synthetic numeric confidence (confidence is None, qualitative certainty HIGH/MEDIUM/LOW)
12. AI does not determine legal expiry or food safety certification
13. AI disclaimer always exists
14. Fallback is explicitly marked provider='local_fallback' and is_fallback=True
"""

import io
import json
import base64
from unittest.mock import MagicMock
import pytest
import numpy as np
from PIL import Image
from datetime import datetime, timezone, timedelta

from app.core.config import settings
from app.services.ai_vision_service import (
    analyze_food_image_and_metadata,
    FOOD_SAFETY_DISCLAIMER,
    clear_ai_cache,
    reset_ai_telemetry,
    get_ai_telemetry,
    MODEL_VERSION,
    PROMPT_VERSION,
    ANALYSIS_POLICY_VERSION,
)


@pytest.fixture(autouse=True)
def clean_ai_test_environment():
    clear_ai_cache()
    reset_ai_telemetry()
    yield
    clear_ai_cache()
    reset_ai_telemetry()


def _make_fresh_food_image_bytes() -> bytes:
    """Creates a synthetic photo-like image of warm golden-brown food."""
    arr = np.clip(np.full((128, 128, 3), [210, 160, 90]) + np.random.randint(-10, 10, (128, 128, 3)), 0, 255).astype(np.uint8)
    img = Image.fromarray(arr)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def _make_moldy_food_image_bytes() -> bytes:
    """Creates an image with realistic fungal/mold surface patches."""
    arr = np.clip(np.full((128, 128, 3), [210, 160, 90]) + np.random.randint(-10, 10, (128, 128, 3)), 0, 255).astype(np.uint8)
    # Fungal olive-green mold patch
    arr[40:70, 40:70] = [60, 110, 80]
    # Dark necrotic center
    arr[45:65, 45:65] = [35, 50, 40]
    img = Image.fromarray(arr)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def _make_blurred_image_bytes() -> bytes:
    """Creates an image with no texture / completely uniform (blurry)."""
    img = Image.new("RGB", (128, 128), (140, 140, 140))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def _make_dark_image_bytes() -> bytes:
    """Creates an underexposed dark image."""
    img = Image.new("RGB", (128, 128), (10, 10, 10))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def test_1_filename_cannot_determine_result(monkeypatch):
    """Test 1: Filename cannot determine result. Fresh food named 'moldy_rot_decay.jpg' is NOT marked spoiled."""
    monkeypatch.setattr(settings, "AI_PROVIDER", "heuristic")
    fresh_bytes = _make_fresh_food_image_bytes()
    res = analyze_food_image_and_metadata(
        image_bytes=fresh_bytes,
        filename="moldy_rot_decay_spoilage.jpg",
        storage_method="Refrigerated",
        storage_duration_hours=1.0
    )
    assert res["visual_condition"] in ["GOOD", "FAIR"]
    assert res["visible_spoilage"] == "Not detected"
    assert res["spoilage_detected"] is False

    # Conversely, moldy food named 'fresh_delicious_curry.jpg' MUST be detected as spoiled
    mold_bytes = _make_moldy_food_image_bytes()
    res_mold = analyze_food_image_and_metadata(
        image_bytes=mold_bytes,
        filename="fresh_delicious_curry.jpg",
        storage_method="Refrigerated",
        storage_duration_hours=1.0
    )
    assert res_mold["visual_condition"] == "POOR"
    assert res_mold["visible_spoilage"] == "Visible signs detected"
    assert res_mold["spoilage_detected"] is True


def test_2_hash_cannot_determine_result(monkeypatch):
    """Test 2: Hash cannot determine result. Decisions are strictly pixel/multimodal based."""
    monkeypatch.setattr(settings, "AI_PROVIDER", "heuristic")
    for i in range(5):
        arr = np.clip(np.full((128, 128, 3), [200 + i * 2, 150 + i * 2, 80 + i * 2]), 0, 255).astype(np.uint8)
        img = Image.fromarray(arr)
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        res = analyze_food_image_and_metadata(
            image_bytes=buf.getvalue(),
            storage_method="Refrigerated",
            storage_duration_hours=1.0
        )
        assert res["spoilage_detected"] is False


def test_3_actual_image_bytes_are_passed_to_provider(monkeypatch):
    """Test 3: Actual image bytes are passed to multimodal provider in inline_data parts."""
    monkeypatch.setattr(settings, "AI_PROVIDER", "gemini")
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "mock-gemini-key")
    monkeypatch.setattr(settings, "GEMINI_MODEL", "gemini-2.5-flash")

    test_image = _make_fresh_food_image_bytes()
    expected_b64 = base64.b64encode(test_image).decode("utf-8")

    sent_payload = {}
    sent_url = ""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "candidates": [{
            "content": {
                "parts": [{
                    "text": json.dumps({
                        "food_detected": "Sambar & Rice",
                        "visual_condition": "GOOD",
                        "visible_spoilage": "Not detected",
                        "discoloration": "Normal",
                        "packaging_integrity": "Intact",
                        "certainty": "HIGH",
                        "observations": ["Golden color", "No surface mold"],
                        "urgency_recommendation": "Standard Priority"
                    })
                }]
            }
        }]
    }
    mock_resp.raise_for_status = MagicMock()

    def mock_post(self, url, *a, **k):
        nonlocal sent_payload, sent_url
        sent_url = str(url)
        sent_payload = k.get("json", {})
        return mock_resp

    monkeypatch.setattr("httpx.Client.post", mock_post)

    res = analyze_food_image_and_metadata(
        image_bytes=test_image,
        food_category="Cooked Food",
        storage_method="Refrigerated"
    )

    assert "models/gemini-2.5-flash:generateContent" in sent_url
    assert res["provider"] == "gemini"
    assert res["is_fallback"] is False
    assert res["certainty"] == "HIGH"
    assert res["confidence"] is None  # No synthetic numeric confidence

    # Verify actual image bytes were sent
    parts = sent_payload["contents"][0]["parts"]
    assert len(parts) >= 2
    assert parts[1]["inline_data"]["data"] == expected_b64


def test_4_one_image_works(monkeypatch):
    """Test 4: One image upload is properly routed and analyzed."""
    monkeypatch.setattr(settings, "AI_PROVIDER", "heuristic")
    img = _make_fresh_food_image_bytes()
    res = analyze_food_image_and_metadata(image_bytes=img)
    assert res["images_analyzed"] == 1
    assert res["visual_condition"] in ["GOOD", "FAIR"]


def test_5_two_images_works(monkeypatch):
    """Test 5: Two images are both accepted and reach the multimodal analysis pipeline."""
    monkeypatch.setattr(settings, "AI_PROVIDER", "gemini")
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "mock-gemini-key")

    sent_parts = []
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "candidates": [{
            "content": {
                "parts": [{
                    "text": json.dumps({
                        "food_detected": "Vegetable Curry",
                        "visual_condition": "GOOD",
                        "visible_spoilage": "Not detected",
                        "certainty": "HIGH",
                        "observations": ["Clear angles"]
                    })
                }]
            }
        }]
    }

    def mock_post(self, url, *a, **k):
        nonlocal sent_parts
        sent_parts = k.get("json", {}).get("contents", [{}])[0].get("parts", [])
        return mock_resp

    monkeypatch.setattr("httpx.Client.post", mock_post)

    images = [
        {"bytes": _make_fresh_food_image_bytes(), "filename": "angle_1.jpg"},
        {"bytes": _make_fresh_food_image_bytes(), "filename": "angle_2.jpg"},
    ]
    res = analyze_food_image_and_metadata(images_data=images)
    assert res["images_analyzed"] == 2
    # Prompt + 2 image inline_data parts = 3 parts
    assert len(sent_parts) == 3


def test_6_three_images_works(monkeypatch):
    """Test 6: Three images (max allowed) all reach the multimodal provider request."""
    monkeypatch.setattr(settings, "AI_PROVIDER", "gemini")
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "mock-gemini-key")

    sent_parts = []
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "candidates": [{
            "content": {
                "parts": [{
                    "text": json.dumps({
                        "food_detected": "Curry Box",
                        "visual_condition": "GOOD",
                        "visible_spoilage": "Not detected",
                        "certainty": "HIGH"
                    })
                }]
            }
        }]
    }

    def mock_post(self, url, *a, **k):
        nonlocal sent_parts
        sent_parts = k.get("json", {}).get("contents", [{}])[0].get("parts", [])
        return mock_resp

    monkeypatch.setattr("httpx.Client.post", mock_post)

    images = [
        {"bytes": _make_fresh_food_image_bytes(), "filename": "angle_top.jpg"},
        {"bytes": _make_fresh_food_image_bytes(), "filename": "angle_side.jpg"},
        {"bytes": _make_fresh_food_image_bytes(), "filename": "angle_close.jpg"},
    ]
    res = analyze_food_image_and_metadata(images_data=images)
    assert res["images_analyzed"] == 3
    # Prompt + 3 images = 4 parts
    assert len(sent_parts) == 4


def test_7_unclear_image_yields_uncertain(monkeypatch):
    """Test 7: Unclear, blurry, or underexposed image yields UNCERTAIN with LOW certainty."""
    monkeypatch.setattr(settings, "AI_PROVIDER", "heuristic")
    blur_bytes = _make_blurred_image_bytes()
    res_blur = analyze_food_image_and_metadata(image_bytes=blur_bytes)
    assert res_blur["visual_condition"] == "UNCERTAIN"
    assert res_blur["certainty"] == "LOW"
    assert res_blur["confidence"] is None

    dark_bytes = _make_dark_image_bytes()
    res_dark = analyze_food_image_and_metadata(image_bytes=dark_bytes)
    assert res_dark["visual_condition"] == "UNCERTAIN"
    assert res_dark["certainty"] == "LOW"
    assert res_dark["confidence"] is None


def test_8_conflicting_images_conservative_result(monkeypatch):
    """Test 8: Conflicting images (2 good + 1 moldy) conservatively evaluate to POOR and visible spoilage."""
    monkeypatch.setattr(settings, "AI_PROVIDER", "heuristic")
    images = [
        {"bytes": _make_fresh_food_image_bytes(), "filename": "fresh_1.jpg"},
        {"bytes": _make_moldy_food_image_bytes(), "filename": "mold_angle.jpg"},
        {"bytes": _make_fresh_food_image_bytes(), "filename": "fresh_2.jpg"},
    ]
    res = analyze_food_image_and_metadata(images_data=images)
    assert res["images_analyzed"] == 3
    assert res["visual_condition"] == "POOR"
    assert res["spoilage_detected"] is True
    assert res["visible_spoilage"] == "Visible signs detected"
    assert res["confidence"] is None


def test_9_provider_timeout_safe_degraded_result(monkeypatch):
    """Test 9: Provider timeout safely degrades to local_fallback with is_fallback=True."""
    import httpx

    monkeypatch.setattr(settings, "AI_PROVIDER", "gemini")
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "mock-gemini-key")

    def mock_timeout(*a, **k):
        raise httpx.TimeoutException("Gemini vision timed out after 10s")

    monkeypatch.setattr("httpx.Client.post", mock_timeout)

    test_image = _make_fresh_food_image_bytes()
    res = analyze_food_image_and_metadata(image_bytes=test_image)

    assert res["provider"] == "local_fallback"
    assert res["is_fallback"] is True
    assert res["confidence"] is None
    assert "local fallback" in res["observations"][0].lower()


def test_10_provider_malformed_response_safe_failure(monkeypatch):
    """Test 10: Provider malformed non-JSON response safely falls back without crashing."""
    monkeypatch.setattr(settings, "AI_PROVIDER", "gemini")
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "mock-gemini-key")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "candidates": [{"content": {"parts": [{"text": "Sorry, cannot analyze this format properly."}]}}]
    }
    mock_resp.raise_for_status = MagicMock()

    monkeypatch.setattr("httpx.Client.post", lambda *a, **k: mock_resp)

    test_image = _make_fresh_food_image_bytes()
    res = analyze_food_image_and_metadata(image_bytes=test_image)

    assert res["provider"] == "local_fallback"
    assert res["is_fallback"] is True
    assert res["confidence"] is None


def test_11_no_synthetic_numeric_confidence(monkeypatch):
    """Test 11: No synthetic numeric confidence. Confidence is None and certainty is qualitative HIGH/MEDIUM/LOW."""
    monkeypatch.setattr(settings, "AI_PROVIDER", "heuristic")
    img = _make_fresh_food_image_bytes()
    res = analyze_food_image_and_metadata(image_bytes=img)

    # Strictly verify NO fabricated numeric float is returned
    assert res["confidence"] is None
    assert res["certainty"] in ["HIGH", "MEDIUM", "LOW"]


def test_12_ai_does_not_determine_expiry(monkeypatch):
    """Test 12: AI vision does NOT determine legal expiry, contamination certification, or edibility."""
    monkeypatch.setattr(settings, "AI_PROVIDER", "heuristic")
    res = analyze_food_image_and_metadata(image_bytes=_make_fresh_food_image_bytes())
    assert "safe_to_eat" not in res
    assert "is_safe" not in res
    assert "contamination_certified" not in res
    # Authoritative window remains evaluated by food rescue window service
    assert "rescue_window" in res
    assert "remaining_minutes" in res["rescue_window"]


def test_13_ai_disclaimer_always_exists(monkeypatch):
    """Test 13: Mandatory safety disclaimer is always returned in safety_disclaimer."""
    monkeypatch.setattr(settings, "AI_PROVIDER", "heuristic")
    res = analyze_food_image_and_metadata(image_bytes=_make_fresh_food_image_bytes())
    assert "safety_disclaimer" in res
    assert "does not certify food safety" in res["safety_disclaimer"]
    assert FOOD_SAFETY_DISCLAIMER in res["safety_disclaimer"]


def test_14_fallback_is_explicitly_marked_fallback(monkeypatch):
    """Test 14: Fallback is explicitly marked provider='local_fallback' and is_fallback=True."""
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "")

    res = analyze_food_image_and_metadata(image_bytes=_make_fresh_food_image_bytes())
    assert res["provider"] == "local_fallback"
    assert res["is_fallback"] is True
    assert res["confidence"] is None
    assert any("local fallback" in obs.lower() for obs in res["observations"])


# ─── 15. Identical Image Set Uses Cached Result ─────────────────────────────

def test_15_identical_image_set_uses_cached_result(monkeypatch):
    """
    Proves:
    - 1st call executes external Gemini multimodal request
    - 2nd call with identical image bytes returns cached result with 0 external API calls
    - Telemetry counts cache hits and misses accurately
    """
    monkeypatch.setattr(settings, "AI_PROVIDER", "gemini")
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "mock-gemini-key")
    monkeypatch.setattr(settings, "GEMINI_MODEL", "gemini-flash-latest")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "candidates": [{"content": {"parts": [{"text": json.dumps({
            "food_detected": "Curry Meals",
            "visual_condition": "GOOD",
            "visible_spoilage": "Not detected",
            "certainty": "HIGH"
        })}]}}]
    }
    mock_resp.raise_for_status = MagicMock()

    call_count = 0
    def mock_post(self, *a, **k):
        nonlocal call_count
        call_count += 1
        return mock_resp

    monkeypatch.setattr("httpx.Client.post", mock_post)

    test_img = _make_fresh_food_image_bytes()

    # 1st call: queries provider
    res1 = analyze_food_image_and_metadata(image_bytes=test_img, food_category="Cooked Food")
    assert call_count == 1
    assert res1.get("cache_hit") is not True

    # 2nd call: identical image bytes -> cache hit, zero external calls
    res2 = analyze_food_image_and_metadata(image_bytes=test_img, food_category="Cooked Food")
    assert call_count == 1
    assert res2.get("cache_hit") is True
    assert res2["visual_condition"] == res1["visual_condition"]

    telemetry = get_ai_telemetry()
    assert telemetry["gemini_cache_hits"] >= 1
    assert telemetry["gemini_cache_misses"] == 1
    assert telemetry["gemini_requests"] == 1


# ─── 16. Same Donation Does Not Re-call Gemini ──────────────────────────────

def test_16_same_donation_image_set_does_not_recall_gemini(monkeypatch):
    """
    Proves:
    - Multi-photo donation image set is analyzed once
    - Re-evaluating the donation reuses existing verified result
    """
    monkeypatch.setattr(settings, "AI_PROVIDER", "gemini")
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "mock-gemini-key")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "candidates": [{"content": {"parts": [{"text": json.dumps({
            "food_detected": "Idli Box",
            "visual_condition": "GOOD",
            "visible_spoilage": "Not detected",
            "certainty": "HIGH"
        })}]}}]
    }
    mock_resp.raise_for_status = MagicMock()

    call_count = 0
    def mock_post(self, *a, **k):
        nonlocal call_count
        call_count += 1
        return mock_resp

    monkeypatch.setattr("httpx.Client.post", mock_post)

    images = [
        {"bytes": _make_fresh_food_image_bytes(), "filename": "idli_top.jpg"},
        {"bytes": _make_fresh_food_image_bytes(), "filename": "idli_side.jpg"}
    ]

    res1 = analyze_food_image_and_metadata(images_data=images, food_category="Cooked Food")
    assert call_count == 1

    # Viewing donation details / screens later with same image set
    res2 = analyze_food_image_and_metadata(images_data=images, food_category="Cooked Food")
    assert call_count == 1
    assert res2.get("cache_hit") is True


# ─── 17. Changing Filename Does Not Trigger New Analysis ────────────────────

def test_17_changing_filename_does_not_trigger_unnecessary_analysis(monkeypatch):
    """
    Proves:
    - Cache key is strictly derived from raw image bytes SHA-256 digest
    - Changing filename from 'original.jpg' to 'renamed.jpg' reuses cached result
    """
    monkeypatch.setattr(settings, "AI_PROVIDER", "gemini")
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "mock-gemini-key")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "candidates": [{"content": {"parts": [{"text": json.dumps({
            "food_detected": "Rice",
            "visual_condition": "GOOD",
            "visible_spoilage": "Not detected",
            "certainty": "HIGH"
        })}]}}]
    }
    mock_resp.raise_for_status = MagicMock()

    call_count = 0
    def mock_post(self, *a, **k):
        nonlocal call_count
        call_count += 1
        return mock_resp

    monkeypatch.setattr("httpx.Client.post", mock_post)

    raw_bytes = _make_fresh_food_image_bytes()
    # Call 1 with filename A
    analyze_food_image_and_metadata(images_data=[{"bytes": raw_bytes, "filename": "original_upload.jpg"}])
    assert call_count == 1

    # Call 2 with identical bytes but different filename B -> must hit cache without external API call
    res_b = analyze_food_image_and_metadata(images_data=[{"bytes": raw_bytes, "filename": "renamed_download_copy.jpg"}])
    assert call_count == 1
    assert res_b.get("cache_hit") is True


# ─── 18. Changed Bytes Generate New Cache Key ────────────────────────────────

def test_18_changed_bytes_generate_new_cache_key(monkeypatch):
    """
    Proves:
    - Different images produce different cache keys and trigger fresh external analysis
    """
    monkeypatch.setattr(settings, "AI_PROVIDER", "gemini")
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "mock-gemini-key")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "candidates": [{"content": {"parts": [{"text": json.dumps({
            "food_detected": "Food Item",
            "visual_condition": "GOOD",
            "visible_spoilage": "Not detected",
            "certainty": "HIGH"
        })}]}}]
    }
    mock_resp.raise_for_status = MagicMock()

    call_count = 0
    def mock_post(self, *a, **k):
        nonlocal call_count
        call_count += 1
        return mock_resp

    monkeypatch.setattr("httpx.Client.post", mock_post)

    img_a = _make_fresh_food_image_bytes()
    img_b = _make_moldy_food_image_bytes()

    analyze_food_image_and_metadata(image_bytes=img_a)
    assert call_count == 1

    analyze_food_image_and_metadata(image_bytes=img_b)
    assert call_count == 2


# ─── 19. Changed Prompt/Model Version Invalidates Cache ─────────────────────

def test_19_changed_prompt_or_model_version_invalidates_cache(monkeypatch):
    """
    Proves:
    - Updating model version invalidates existing cache and triggers re-analysis
    """
    monkeypatch.setattr(settings, "AI_PROVIDER", "gemini")
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "mock-gemini-key")
    monkeypatch.setattr(settings, "GEMINI_MODEL", "gemini-flash-latest")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "candidates": [{"content": {"parts": [{"text": json.dumps({
            "food_detected": "Sample",
            "visual_condition": "GOOD",
            "visible_spoilage": "Not detected",
            "certainty": "HIGH"
        })}]}}]
    }
    mock_resp.raise_for_status = MagicMock()

    call_count = 0
    def mock_post(self, *a, **k):
        nonlocal call_count
        call_count += 1
        return mock_resp

    monkeypatch.setattr("httpx.Client.post", mock_post)

    test_img = _make_fresh_food_image_bytes()
    analyze_food_image_and_metadata(image_bytes=test_img)
    assert call_count == 1

    # Invalidate by bumping model version
    monkeypatch.setattr(settings, "GEMINI_MODEL", "gemini-2.5-pro")
    analyze_food_image_and_metadata(image_bytes=test_img)
    assert call_count == 2


# ─── 20. Provider 429 Enters Cooldown ────────────────────────────────────────

def test_20_provider_429_enters_cooldown(monkeypatch):
    """
    Proves:
    - When Gemini returns HTTP 429, service activates provider cooldown
    - Subsequent calls during cooldown immediately return local fallback WITHOUT calling external API
    """
    monkeypatch.setattr(settings, "AI_PROVIDER", "gemini")
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "mock-gemini-key")

    mock_resp_429 = MagicMock()
    mock_resp_429.status_code = 429
    mock_resp_429.text = "Quota exceeded"

    call_count = 0
    def mock_post(self, *a, **k):
        nonlocal call_count
        call_count += 1
        return mock_resp_429

    monkeypatch.setattr("httpx.Client.post", mock_post)

    test_img = _make_fresh_food_image_bytes()
    res1 = analyze_food_image_and_metadata(image_bytes=test_img)
    assert res1["provider"] == "local_fallback"
    assert res1["is_fallback"] is True
    assert call_count == 1

    telemetry = get_ai_telemetry()
    assert telemetry["gemini_cooldown_active"] >= 1

    # Second call while in cooldown must NOT call external API at all
    res2 = analyze_food_image_and_metadata(image_bytes=_make_moldy_food_image_bytes())
    assert res2["provider"] == "local_fallback"
    assert call_count == 1  # Still 1, zero calls during cooldown!


# ─── 21. Transient Failure Bounded Retry ─────────────────────────────────────

def test_21_transient_failure_bounded_retry(monkeypatch):
    """
    Proves:
    - Transient server error (503) retries at most AI_MAX_TRANSIENT_RETRIES (1)
    - Total calls = 2 (initial + 1 retry), never infinite loops
    - Degrades safely to local fallback
    """
    import httpx
    monkeypatch.setattr(settings, "AI_PROVIDER", "gemini")
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "mock-gemini-key")
    monkeypatch.setattr(settings, "AI_MAX_TRANSIENT_RETRIES", 1)

    call_count = 0
    def mock_server_error(self, *a, **k):
        nonlocal call_count
        call_count += 1
        resp = MagicMock()
        resp.status_code = 503
        raise httpx.HTTPStatusError("503 Service Unavailable", request=MagicMock(), response=resp)

    monkeypatch.setattr("httpx.Client.post", mock_server_error)
    monkeypatch.setattr("time.sleep", lambda s: None)

    res = analyze_food_image_and_metadata(image_bytes=_make_fresh_food_image_bytes())
    assert call_count == 2
    assert res["provider"] == "local_fallback"
    assert res["is_fallback"] is True


# ─── 22. Local Image Optimization Downsamples Resolution ────────────────────

def test_22_local_image_optimization_downsamples_excessive_resolution(monkeypatch):
    """
    Proves:
    - High-resolution images are downsampled to <= 1024x1024 before transmission
    - Optimization is purely local (zero Gemini calls for preprocessing)
    - Conserves bandwidth and token budget
    """
    monkeypatch.setattr(settings, "AI_PROVIDER", "gemini")
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "mock-gemini-key")

    sent_b64 = ""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "candidates": [{"content": {"parts": [{"text": json.dumps({
            "food_detected": "High-Res Food",
            "visual_condition": "GOOD",
            "visible_spoilage": "Not detected",
            "certainty": "HIGH"
        })}]}}]
    }
    mock_resp.raise_for_status = MagicMock()

    def mock_post(self, url, json=None, *a, **k):
        nonlocal sent_b64
        parts = json.get("contents", [{}])[0].get("parts", [])
        if len(parts) > 1:
            sent_b64 = parts[1]["inline_data"]["data"]
        return mock_resp

    monkeypatch.setattr("httpx.Client.post", mock_post)

    # Create large 2048x2048 image
    large_img = Image.new("RGB", (2048, 2048), (210, 160, 90))
    buf = io.BytesIO()
    large_img.save(buf, format="JPEG")
    large_bytes = buf.getvalue()

    analyze_food_image_and_metadata(image_bytes=large_bytes)

    # Decode what was actually transmitted to Gemini
    assert sent_b64 != ""
    sent_bytes = base64.b64decode(sent_b64)
    received_img = Image.open(io.BytesIO(sent_bytes))

    # Must be downsampled to max 1024x1024 locally before transmission
    assert received_img.width <= 1024
    assert received_img.height <= 1024
