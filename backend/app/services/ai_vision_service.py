import io
import json
import base64
import logging
import hashlib
import time
import threading
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
import httpx
import numpy as np
from PIL import Image

from app.core.config import settings
from app.services.food_rescue_window_service import evaluate_food_rescue_window

logger = logging.getLogger("smart_food_rescue.ai_vision")

# Model, prompt, and policy versions for deterministic cache invalidation
MODEL_VERSION = getattr(settings, "GEMINI_MODEL", "gemini-flash-latest")
PROMPT_VERSION = "2026.10.v1"
ANALYSIS_POLICY_VERSION = "v1.0"

_ai_cache: Dict[str, Dict[str, Any]] = {}
_ai_cache_lock = threading.Lock()
_cooldown_until: Optional[float] = None

_ai_telemetry: Dict[str, int] = {
    "gemini_requests": 0,
    "gemini_cache_hits": 0,
    "gemini_cache_misses": 0,
    "gemini_fallback_count": 0,
    "gemini_cooldown_active": 0,
}


def get_ai_telemetry() -> Dict[str, int]:
    """Returns a snapshot of Gemini AI usage counters."""
    with _ai_cache_lock:
        return dict(_ai_telemetry)


def reset_ai_telemetry():
    """Resets Gemini AI usage counters."""
    with _ai_cache_lock:
        for k in _ai_telemetry:
            _ai_telemetry[k] = 0


def clear_ai_cache():
    """Clears the in-process Gemini AI result cache and cooldown state."""
    global _cooldown_until
    with _ai_cache_lock:
        _ai_cache.clear()
        _cooldown_until = None


FOOD_SAFETY_DISCLAIMER = (
    "Image analysis cannot guarantee food safety. Visual assessment only. "
    "This assessment is based on visual appearance only and is not a food safety or contamination certification. "
    "AI visual assessment does not certify food safety."
)

FOOD_CATEGORY_MAPPINGS = {
    "Cooked Food": ["Rice + Curry", "Cooked Meals (Dal & Rice)", "Biryani & Gravy", "Idli & Sambar Bowl", "Chapati & Vegetable Curry"],
    "Bakery": ["Assorted Breads & Buns", "Pastries & Loaves", "Sandwich Box", "Bakery Goods"],
    "Fruits": ["Fresh Fruit Medley", "Apples & Bananas Box", "Seasonal Citrus & Melons"],
    "Vegetables": ["Mixed Fresh Vegetables", "Greens & Root Vegetables", "Fresh Farm Produce"],
    "Dairy": ["Paneer & Dairy Packs", "Milk Products", "Yogurt & Curd Cups"],
    "Packaged Food": ["Sealed Canned Goods", "Packaged Snacks & Biscuits", "Assorted Tetra Paks"],
    "Other": ["Prepared Food Box", "Assorted Pantry Items"]
}


def _detect_mime_type(image_bytes: bytes) -> str:
    """Detects MIME type from magic numbers or PIL."""
    if not image_bytes:
        return "image/jpeg"
    if image_bytes.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if image_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if image_bytes.startswith(b"RIFF") and b"WEBP" in image_bytes[:16]:
        return "image/webp"
    try:
        img = Image.open(io.BytesIO(image_bytes))
        fmt = (img.format or "JPEG").lower()
        if fmt == "png":
            return "image/png"
        if fmt == "webp":
            return "image/webp"
        return "image/jpeg"
    except Exception:
        return "image/jpeg"


def _optimize_image_bytes(b: bytes) -> bytes:
    """
    Locally validates and optimizes image resolution and encoding before sending to Gemini.
    Resizes images larger than 1024x1024 and compresses to JPEG (quality=80).
    Saves bandwidth and tokens while preserving visual food quality cues.
    All preprocessing is strictly local (0 Gemini calls for preprocessing).
    """
    if not b or len(b) < 16:
        return b
    try:
        img = Image.open(io.BytesIO(b))
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        max_dim = 1024
        if img.width > max_dim or img.height > max_dim:
            img.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)
            out_buf = io.BytesIO()
            img.save(out_buf, format="JPEG", quality=80, optimize=True)
            return out_buf.getvalue()
        if len(b) > 400 * 1024:
            out_buf = io.BytesIO()
            img.save(out_buf, format="JPEG", quality=80, optimize=True)
            return out_buf.getvalue()
    except Exception as e:
        logger.debug(f"[AI Vision] Local image optimization skipped: {e}")
    return b


def _compute_cache_key(
    images_data: List[Dict[str, Any]],
    food_category: Optional[str],
    food_type: Optional[str],
    model_version: str,
    prompt_version: str,
    policy_version: str
) -> str:
    """
    Generates a deterministic SHA-256 cache key based on actual raw image bytes and analysis versions.
    NOTE: The hash is strictly used for deduplication/cache lookup, NEVER to infer food condition.
    """
    hasher = hashlib.sha256()
    for item in images_data:
        b = item.get("bytes") or b""
        hasher.update(hashlib.sha256(b).digest())
    meta_str = f"{food_category or ''}:{food_type or ''}:{model_version}:{prompt_version}:{policy_version}"
    hasher.update(meta_str.encode("utf-8"))
    return hasher.hexdigest()


def _call_gemini_vision(
    images_data: List[Dict[str, Any]],
    food_category: Optional[str] = "Cooked Food",
    food_type: Optional[str] = None
) -> Dict[str, Any]:
    """
    Sends actual image bytes to Google Gemini Vision REST API.
    Conservative multimodal inference across 1-3 images in ONE single request.
    Features:
      - Quota cooldown guard (no hammering when 429/rate-limited)
      - Local image resolution & token optimization
      - Bounded transient retry with backoff (max 1 retry, no 401/403 retries)
    """
    global _cooldown_until

    if not settings.GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY is not configured")

    # Check provider cooldown guard
    now_ts = time.time()
    if _cooldown_until and now_ts < _cooldown_until:
        with _ai_cache_lock:
            _ai_telemetry["gemini_cooldown_active"] += 1
        remaining_cd = int(_cooldown_until - now_ts)
        raise RuntimeError(f"Gemini API in cooldown due to rate limits ({remaining_cd}s remaining). Using local sensory fallback.")

    valid_images = [img for img in images_data if img.get("bytes") and len(img["bytes"]) >= 16][:3]
    if not valid_images:
        raise ValueError("No valid image bytes provided for Gemini Vision analysis")

    prompt = (
        "You are an advisory food visual quality analysis assistant for a food rescue donation platform. "
        "Analyze the provided food image(s) for visual appearance.\n"
        f"Declared Food Category: {food_category or 'Cooked Food'}\n"
        f"Declared Food Type: {food_type or 'Unspecified'}\n\n"
        "Guidelines:\n"
        "1. Strictly assess visual characteristics only. This is not a laboratory test or legal safety certification.\n"
        "2. If ANY image shows visible signs of mold, rot, discoloration, unnatural sheen, or severe physical degradation, "
        "mark visual_condition as 'POOR' and visible_spoilage as 'Visible signs detected'.\n"
        "3. If the image is blurry, underexposed, overexposed, ambiguous, or if conflicting images prevent a confident assessment, "
        "mark visual_condition as 'UNCERTAIN', visible_spoilage as 'Uncertain', and set certainty to 'LOW'.\n"
        "4. Otherwise, if the food visually appears normal and fresh, mark visual_condition as 'GOOD' or 'FAIR'.\n"
        "5. Set qualitative certainty to 'HIGH', 'MEDIUM', or 'LOW' based purely on image clarity and visual evidence visibility across all uploaded images. Do NOT fabricate numeric probabilities.\n"
        "Return ONLY a JSON object with this exact structure:\n"
        "{\n"
        '  "food_detected": "string (name of identified food)",\n'
        '  "visual_condition": "GOOD" | "FAIR" | "POOR" | "UNCERTAIN",\n'
        '  "visible_spoilage": "Visible signs detected" | "Not detected" | "Uncertain",\n'
        '  "discoloration": "Normal" | "Slight variation" | "Abnormal",\n'
        '  "packaging_integrity": "Intact" | "Exposed" | "Partially Covered",\n'
        '  "certainty": "HIGH" | "MEDIUM" | "LOW",\n'
        '  "observations": ["observation 1", "observation 2"],\n'
        '  "urgency_recommendation": "string guidance for volunteers/NGOs"\n'
        "}"
    )

    parts: List[Dict[str, Any]] = [{"text": prompt}]
    for img_dict in valid_images:
        b = _optimize_image_bytes(img_dict["bytes"])
        mime = _detect_mime_type(b)
        b64 = base64.b64encode(b).decode("utf-8")
        parts.append({
            "inline_data": {
                "mime_type": mime,
                "data": b64
            }
        })

    model_name = getattr(settings, "GEMINI_MODEL", "gemini-flash-latest") or "gemini-flash-latest"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={settings.GEMINI_API_KEY}"
    payload = {
        "contents": [{"parts": parts}],
        "generationConfig": {
            "temperature": 0.1,
            "responseMimeType": "application/json"
        }
    }

    timeout_sec = float(getattr(settings, "AI_TIMEOUT_SECONDS", 15.0))
    max_retries = int(getattr(settings, "AI_MAX_TRANSIENT_RETRIES", 1))

    resp = None
    for attempt in range(max_retries + 1):
        try:
            with _ai_cache_lock:
                _ai_telemetry["gemini_requests"] += 1
            with httpx.Client(timeout=timeout_sec) as client:
                resp = client.post(url, json=payload)

            # Check 429 quota rate limit
            if resp.status_code == 429:
                _cooldown_until = time.time() + float(getattr(settings, "AI_PROVIDER_COOLDOWN_SECONDS", 300))
                with _ai_cache_lock:
                    _ai_telemetry["gemini_cooldown_active"] += 1
                raise RuntimeError("Gemini API rate limit (429) reached. Entering provider cooldown.")

            resp.raise_for_status()
            data = resp.json()
            break  # Success
        except httpx.HTTPStatusError as e:
            if e.response.status_code in (401, 403):
                # Never retry permission or authentication failures
                raise
            if e.response.status_code in (500, 502, 503) and attempt < max_retries:
                time.sleep(1.0)
                continue
            raise
        except (httpx.TimeoutException, httpx.NetworkError) as e:
            if attempt < max_retries:
                time.sleep(1.0)
                continue
            raise

    candidates = data.get("candidates", [])
    if not candidates:
        raise ValueError("Gemini returned empty candidates")

    content_parts = candidates[0].get("content", {}).get("parts", [])
    if not content_parts or "text" not in content_parts[0]:
        raise ValueError("Gemini returned no text content in parts")

    raw_text = content_parts[0]["text"].strip()
    if raw_text.startswith("```"):
        lines = raw_text.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        raw_text = "\n".join(lines).strip()

    parsed = json.loads(raw_text)
    return parsed

# Lazy-loaded MobileNetV3 model for genuine visual inference
_VISION_MODEL = None
_VISION_TRANSFORMS = None

def _get_vision_model():
    """Lazily initializes PyTorch MobileNetV3 model with ImageNet pretrained weights."""
    global _VISION_MODEL, _VISION_TRANSFORMS
    if _VISION_MODEL is None:
        try:
            import torch
            import torchvision.models as models
            import torchvision.transforms as T
            
            model = models.mobilenet_v3_small(weights=models.MobileNet_V3_Small_Weights.DEFAULT)
            model.eval()
            _VISION_MODEL = model
            _VISION_TRANSFORMS = T.Compose([
                T.Resize((224, 224)),
                T.ToTensor(),
                T.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
            ])
            logger.info("MobileNetV3 vision model loaded successfully for food image inference.")
        except Exception as e:
            logger.warning(f"Could not load MobileNetV3 model: {e}. Fallback to pixel/texture analysis.")
            _VISION_MODEL = False
    return _VISION_MODEL, _VISION_TRANSFORMS


def _inspect_single_image(image_bytes: Optional[bytes]) -> Dict[str, Any]:
    """
    Performs visual feature inspection on a single image in fallback mode.
    Strictly independent of filename, paths, and cryptographic hashes.
    Evaluates:
    - PIL integrity (corrupt/truncated check)
    - Brightness & exposure levels
    - Sharpness / gradient variance (blur detection)
    - Localized fungal/mold patch detection
    Outputs qualitative certainty instead of fabricated numeric probabilities.
    """
    if not image_bytes or len(image_bytes) < 16:
        return {
            "has_spoilage": False,
            "is_unclear": False,
            "no_image": True,
            "discolored": False,
            "certainty": "LOW",
            "reason": "No image provided"
        }

    # 1. PIL Image Decoding
    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    except Exception as e:
        logger.info(f"Image decode failed: {e}")
        return {
            "has_spoilage": False,
            "is_unclear": True,
            "no_image": False,
            "discolored": False,
            "certainty": "LOW",
            "reason": "Image file is corrupt, truncated, or unreadable"
        }

    width, height = img.size
    if width < 16 or height < 16:
        return {
            "has_spoilage": False,
            "is_unclear": True,
            "no_image": False,
            "discolored": False,
            "certainty": "LOW",
            "reason": "Image resolution too low for visual assessment"
        }

    arr = np.array(img, dtype=np.float32) / 255.0
    h, w, _ = arr.shape

    # 2. Exposure & Brightness Analysis
    gray = 0.2989 * arr[:, :, 0] + 0.5870 * arr[:, :, 1] + 0.1140 * arr[:, :, 2]
    mean_brightness = float(np.mean(gray))

    if mean_brightness < 0.08:
        return {
            "has_spoilage": False,
            "is_unclear": True,
            "no_image": False,
            "discolored": False,
            "certainty": "LOW",
            "reason": "Image is too dark / underexposed"
        }
    if mean_brightness > 0.95:
        return {
            "has_spoilage": False,
            "is_unclear": True,
            "no_image": False,
            "discolored": False,
            "certainty": "LOW",
            "reason": "Image is overexposed / washed out"
        }

    # 3. Sharpness / Blur Detection via Gradient Variance
    dx = np.diff(gray, axis=1)
    dy = np.diff(gray, axis=0)
    grad_var = float(np.var(dx) + np.var(dy))
    if grad_var < 0.0001:
        return {
            "has_spoilage": False,
            "is_unclear": True,
            "no_image": False,
            "discolored": False,
            "certainty": "LOW",
            "reason": "Image is blurry or uniform without discernable texture"
        }

    # 4. Localized Color & Fungal / Mold Patch Detection
    r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
    maxc = np.maximum(np.maximum(r, g), b)
    minc = np.minimum(np.minimum(r, g), b)
    v = maxc
    deltac = maxc - minc
    s = np.zeros_like(v)
    mask = maxc > 0
    s[mask] = deltac[mask] / maxc[mask]

    h_channel = np.zeros_like(v)
    mask_r = (maxc == r) & (deltac > 0)
    mask_g = (maxc == g) & (deltac > 0)
    mask_b = (maxc == b) & (deltac > 0)
    h_channel[mask_r] = ((g[mask_r] - b[mask_r]) / deltac[mask_r]) % 6
    h_channel[mask_g] = ((b[mask_g] - r[mask_g]) / deltac[mask_g]) + 2
    h_channel[mask_b] = ((r[mask_b] - g[mask_b]) / deltac[mask_b]) + 4
    h_channel = (h_channel / 6.0) % 1.0  # Normalized hue [0.0, 1.0]

    # Typical food mold characteristics:
    # A. Fungal green/olive/blue-gray hue in [0.22, 0.55], with medium saturation and non-white value
    mold_mask_fungal = (h_channel >= 0.22) & (h_channel <= 0.55) & (s >= 0.12) & (v >= 0.15) & (v <= 0.75)
    # B. Necrotic dark decay spots contrasting strongly with warm background
    mold_mask_dark = (v < 0.22) & (mean_brightness > 0.40)
    mold_mask = mold_mask_fungal | mold_mask_dark

    mold_ratio = float(np.sum(mold_mask)) / float(h * w)
    has_spoilage = mold_ratio > 0.025
    discolored = mold_ratio > 0.008

    return {
        "has_spoilage": has_spoilage,
        "is_unclear": False,
        "no_image": False,
        "discolored": discolored,
        "certainty": "HIGH" if has_spoilage else "MEDIUM",
        "reason": "Potential visual spoilage detected" if has_spoilage else "Normal visual appearance"
    }


def analyze_food_image_and_metadata(
    image_bytes: Optional[bytes] = None,
    filename: Optional[str] = "",
    images_data: Optional[List[Dict[str, Any]]] = None,
    food_category: Optional[str] = "Cooked Food",
    food_type: Optional[str] = None,
    quantity: float = 10.0,
    storage_method: Optional[str] = "Room Temperature",
    storage_duration_hours: Optional[float] = 2.0,
    storage_continuous: bool = True,
    storage_history: Optional[List[Dict[str, Any]]] = None,
    packaging_condition: Optional[str] = "Sealed / Covered",
    previously_served: str = "No",
    exposure_status: str = "No",
    handling_status: str = "No",
    preparation_time: Optional[datetime] = None
) -> Dict[str, Any]:
    """
    Performs visual condition analysis and decision fusion combining image features with donor metadata.
    Supports 1 to 3 images with conservative aggregation:
    If ANY image shows visible mold, fuzzy growth, or degradation, visual condition cannot be 'GOOD'.
    Strictly provides visual characteristics and safe storage assessments.
    Outputs structured information and never certifies food safety.
    """
    # 1. Build list of image payloads
    image_items: List[Dict[str, Any]] = []
    if images_data and len(images_data) > 0:
        image_items = images_data
    elif image_bytes:
        image_items = [{"bytes": image_bytes, "filename": filename or ""}]

    num_images = max(1, len(image_items)) if image_items else 1

    # In-Process SHA-256 Image Cache Check (Deduplication across identical image sets)
    has_valid_images = bool(image_items and any(img.get("bytes") and len(img["bytes"]) >= 16 for img in image_items))
    cache_key = None
    now_ts = time.time()
    if has_valid_images:
        model_ver = getattr(settings, "GEMINI_MODEL", "gemini-flash-latest")
        cache_key = _compute_cache_key(
            image_items, food_category, food_type, model_ver, PROMPT_VERSION, ANALYSIS_POLICY_VERSION
        )
        with _ai_cache_lock:
            cached = _ai_cache.get(cache_key)
            if cached and now_ts < cached["expires_at"]:
                _ai_telemetry["gemini_cache_hits"] += 1
                res = dict(cached["data"])
                res["cache_hit"] = True
                return res
            _ai_telemetry["gemini_cache_misses"] += 1

    # 2. Food Identification Defaults
    cat_items = FOOD_CATEGORY_MAPPINGS.get(food_category or "Cooked Food", FOOD_CATEGORY_MAPPINGS["Cooked Food"])
    detected_item = food_type if food_type else cat_items[0]

    # 3. Packaging Assessment
    if packaging_condition and "Open" in packaging_condition:
        packaging = "Exposed"
        pkg_score_penalty = 15
    elif packaging_condition and "Sealed" in packaging_condition:
        packaging = "Intact"
        pkg_score_penalty = 0
    elif packaging_condition and "Partially" in packaging_condition:
        packaging = "Partially Covered"
        pkg_score_penalty = 5
    else:
        packaging = "Intact"
        pkg_score_penalty = 0

    storage_method_str = storage_method or "Room Temperature"
    duration = storage_duration_hours if storage_duration_hours is not None else 2.0

    # Storage penalty calculation
    storage_penalty = 0
    if storage_method_str == "Refrigerated":
        storage_penalty = max(0, int((duration - 24) * 0.5)) if duration > 24 else 0
        storage_summary = f"Refrigerated for {duration:.1f}h - Well preserved cold chain."
    elif storage_method_str in ["Heated/Insulated", "Hot Holding", "Insulated Container"]:
        storage_penalty = max(0, int((duration - 4) * 3)) if duration > 4 else 0
        storage_summary = f"Insulated hot-holding for {duration:.1f}h."
    elif storage_method_str == "Frozen":
        storage_penalty = 0
        storage_summary = f"Frozen storage for {duration:.1f}h - Stable."
    else:  # Room Temperature
        storage_penalty = max(0, int((duration - 2) * 5)) if duration > 2 else 0
        storage_summary = f"Ambient room temperature for {duration:.1f}h."

    # 4. Attempt External Gemini Vision if configured
    provider = "local_fallback"
    is_fallback = True
    gemini_result = None

    if getattr(settings, "AI_PROVIDER", "gemini").lower() == "gemini" and settings.GEMINI_API_KEY:
        if image_items and any(img.get("bytes") and len(img["bytes"]) >= 16 for img in image_items):
            try:
                gemini_result = _call_gemini_vision(
                    images_data=image_items,
                    food_category=food_category,
                    food_type=food_type
                )
                provider = "gemini"
                is_fallback = False
                logger.info(f"Gemini Vision inference completed successfully with {num_images} image(s).")
            except Exception as e:
                logger.warning(f"External Gemini Vision call failed: {e}. Falling back to local sensory inference.")
                provider = "local_fallback"
                is_fallback = True

    if gemini_result:
        # Process External Gemini Result
        detected_item = gemini_result.get("food_detected") or detected_item
        v_cond_str = str(gemini_result.get("visual_condition", "GOOD")).upper()
        visual_condition = v_cond_str if v_cond_str in ["GOOD", "FAIR", "POOR", "UNCERTAIN"] else "UNCERTAIN"
        visible_spoilage = gemini_result.get("visible_spoilage", "Not detected")
        discoloration = gemini_result.get("discoloration", "Normal")
        
        any_spoilage = (visual_condition == "POOR") or ("visible" in visible_spoilage.lower())
        if any_spoilage:
            visual_condition = "POOR"
            visible_spoilage = "Visible signs detected"
            discoloration = "Abnormal"
            disc_penalty = 30
            spoil_penalty = 40
        else:
            disc_penalty = 8 if "slight" in discoloration.lower() else 0
            spoil_penalty = 0

        # Qualitative certainty representation: HIGH, MEDIUM, LOW (no synthetic numeric confidence)
        raw_certainty = str(gemini_result.get("certainty", "MEDIUM")).upper()
        certainty = raw_certainty if raw_certainty in ["HIGH", "MEDIUM", "LOW"] else ("LOW" if visual_condition == "UNCERTAIN" else "MEDIUM")
        confidence = None  # Explicitly null: no fabricated numeric confidence

        base_score = 92
        final_score = max(25, min(98, base_score - pkg_score_penalty - disc_penalty - spoil_penalty - storage_penalty))
        if any_spoilage:
            final_score = min(final_score, 38)
        elif visual_condition == "UNCERTAIN":
            final_score = min(final_score, 55)

        urgency_rec = gemini_result.get("urgency_recommendation") or (
            "Potential visual spoilage detected. Do not proceed without appropriate food-safety review." if any_spoilage
            else ("Visual confirmation required upon pickup." if visual_condition == "UNCERTAIN"
                  else "Standard Priority (Redistribute within safe window)")
        )

        observations = gemini_result.get("observations") or [
            f"Gemini multimodal analysis completed for {num_images} photo(s).",
            f"Visual condition: {visual_condition}.",
            f"Visible spoilage: {visible_spoilage}.",
            f"Qualitative certainty: {certainty}.",
            f"Storage assessment: {storage_summary}"
        ]
    else:
        with _ai_cache_lock:
            _ai_telemetry["gemini_fallback_count"] += 1
        # 5. Local Sensory Feature Analysis (Explicitly Degraded Fallback)
        single_evaluations = [_inspect_single_image(img.get("bytes")) for img in image_items] if image_items else [
            {"has_spoilage": False, "is_unclear": False, "no_image": True, "discolored": False, "certainty": "LOW", "reason": "No image provided"}
        ]

        any_spoilage = any(e["has_spoilage"] for e in single_evaluations)
        any_unclear = any(e["is_unclear"] for e in single_evaluations)
        any_discolored = any(e["discolored"] for e in single_evaluations)
        all_no_image = all(e.get("no_image", False) for e in single_evaluations)

        # Ambient room temperature exposure threshold contributes to visible degradation risk
        if duration > 6 and storage_method_str == "Room Temperature":
            any_spoilage = True

        if any_spoilage:
            visible_spoilage = "Visible signs detected"
            discoloration = "Abnormal"
            disc_penalty = 30
            spoil_penalty = 40
        elif any_discolored:
            visible_spoilage = "Not detected"
            discoloration = "Slight variation"
            disc_penalty = 8
            spoil_penalty = 0
        else:
            visible_spoilage = "Not detected"
            discoloration = "Normal"
            disc_penalty = 0
            spoil_penalty = 0

        base_score = 92
        final_score = max(25, min(98, base_score - pkg_score_penalty - disc_penalty - spoil_penalty - storage_penalty))
        if any_spoilage:
            final_score = min(final_score, 38)

        # No synthetic numeric confidence; use qualitative certainty
        confidence = None

        if any_spoilage:
            visual_condition = "POOR"
            certainty = "HIGH"
            urgency_rec = "Potential visual spoilage detected. Do not proceed without appropriate food-safety review."
        elif any_unclear:
            visual_condition = "UNCERTAIN"
            certainty = "LOW"
            urgency_rec = "Unclear / Low quality image. Visual confirmation required upon pickup."
        elif all_no_image:
            visual_condition = "GOOD" if final_score >= 80 else ("FAIR" if final_score >= 60 else "POOR")
            certainty = "LOW"
            urgency_rec = "Visual assessment based on metadata fusion (no photos uploaded)."
        elif final_score >= 80:
            visual_condition = "GOOD"
            certainty = "MEDIUM"
            urgency_rec = "Standard Priority (Redistribute within safe window)"
        elif final_score >= 60:
            visual_condition = "FAIR"
            certainty = "LOW"
            urgency_rec = "High Priority Pickup (Expedite delivery)"
        else:
            visual_condition = "POOR"
            certainty = "MEDIUM"
            urgency_rec = "Urgent Review Required (Quality inspection needed)"

        # Build structured observations
        observations = [
            f"Analyzed {num_images} food photo{'s' if num_images > 1 else ''} via local fallback." if not all_no_image else "Visual assessment based on metadata fusion (no photos uploaded).",
            f"Visual appearance: {visual_condition.lower()} condition.",
            f"Packaging integrity: {packaging.lower()}.",
            f"Discoloration: {discoloration.lower()}.",
            f"Visible spoilage signs: {visible_spoilage.lower()}.",
            f"Qualitative certainty: {certainty}.",
            f"Storage evaluation: {storage_summary}",
        ]

        if any_spoilage:
            observations.insert(0, "CRITICAL: Surface deterioration or potential visual spoilage pattern detected on image analysis.")
        elif any_unclear:
            unclear_reasons = [e.get("reason", "Low quality") for e in single_evaluations if e.get("is_unclear")]
            observations.insert(0, f"ADVISORY: Image quality constraint ({unclear_reasons[0]}); secondary visual review recommended upon pickup.")
        else:
            observations.insert(0, "ADVISORY: Processed via local fallback (AI provider unavailable). Secondary visual review recommended upon pickup.")

    # Time-Aware Food Rescue Window calculation (Authoritative: uses prep time & storage)
    prep_time_to_use = preparation_time or datetime.now(timezone.utc)
    rescue_window_eval = evaluate_food_rescue_window(
        food_type=food_type or detected_item,
        food_category=food_category or "Cooked Food",
        prepared_at=prep_time_to_use,
        storage_method=storage_method_str,
        storage_continuous=storage_continuous,
        storage_history=storage_history,
        packaging_status=packaging_condition or "Covered",
        previously_served=previously_served,
        exposure_status=exposure_status,
        handling_status=handling_status,
        visual_condition_in=visual_condition,
        visible_spoilage_in=visible_spoilage,
        ai_confidence_in=None
    )

    result = {
        "food_detected": detected_item,
        "food_type": food_type or detected_item,
        "food_category": food_category,
        "visible_spoilage": visible_spoilage,
        "discoloration": discoloration,
        "packaging_integrity": packaging,
        "packaging": packaging,
        "packaging_condition": packaging_condition,
        "visual_condition": visual_condition,
        "confidence": confidence,
        "certainty": certainty,
        "condition_score": final_score,
        "observations": observations,
        "safety_disclaimer": FOOD_SAFETY_DISCLAIMER,
        "warning": FOOD_SAFETY_DISCLAIMER,
        "storage_assessment": storage_summary,
        "urgency_recommendation": urgency_rec,
        "images_analyzed": num_images,
        "spoilage_detected": any_spoilage,
        "rescue_window": rescue_window_eval,
        "provider": provider,
        "is_fallback": is_fallback
    }

    # Store in in-process cache for subsequent deduplication
    if cache_key and has_valid_images:
        ttl = int(getattr(settings, "AI_IMAGE_CACHE_TTL_SECONDS", 86400))
        with _ai_cache_lock:
            _ai_cache[cache_key] = {
                "data": result,
                "timestamp": now_ts,
                "expires_at": now_ts + ttl
            }

    return result
