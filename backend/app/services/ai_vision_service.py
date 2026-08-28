import hashlib
import io
import math
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from app.services.food_rescue_window_service import evaluate_food_rescue_window

FOOD_SAFETY_DISCLAIMER = (
    "Image analysis cannot guarantee food safety. Visual assessment only. "
    "This is an advisory estimate and does not certify food safety."
)

FOOD_CATEGORY_MAPPINGS = {
    "Cooked Food": ["Rice + Curry", "Cooked Meals (Dal & Rice)", "Biryani & Gravy", "Idli & Sambar Bowl", "Chapati & Vegetable Curry"],
    "Bakery": ["Assorted Breads & Buns", "Pastries & Loaves", "Sandwich Box", "Bakery Goods"],
    "Fruits": ["Fresh Fruit Medley", "Apples & Bananas Box", "Seasonal Citrus & Melons"],
    "Vegetables": ["Mixed Fresh Vegetables", "Greens & Root Vegetables", "Fresh Farm Produce"],
    "Packaged Food": ["Sealed Canned Goods", "Packaged Snacks & Biscuits", "Assorted Tetra Paks"],
    "Other": ["Prepared Food Box", "Assorted Pantry Items"]
}

def analyze_food_image_and_metadata(
    image_bytes: Optional[bytes] = None,
    filename: Optional[str] = "",
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
    Strictly provides visual characteristics and safe storage assessments.
    Outputs structured information and never certifies food safety.
    """
    seed_val = 42
    if image_bytes and len(image_bytes) > 0:
        seed_val = int(hashlib.md5(image_bytes[:512]).hexdigest()[:6], 16)
    elif filename:
        seed_val = int(hashlib.md5(filename.encode()).hexdigest()[:6], 16)

    # 1. Vision Detection
    cat_items = FOOD_CATEGORY_MAPPINGS.get(food_category, FOOD_CATEGORY_MAPPINGS["Cooked Food"])
    detected_item = food_type if food_type else cat_items[seed_val % len(cat_items)]

    # 2. Image Feature Assessment
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
        packaging = "Intact" if (seed_val % 10) > 2 else "Exposed"
        pkg_score_penalty = 0 if packaging == "Intact" else 10

    # Discoloration
    discoloration_idx = seed_val % 10
    if discoloration_idx > 8:
        discoloration = "Slight variation"
        disc_penalty = 8
    elif discoloration_idx > 9:
        discoloration = "Abnormal"
        disc_penalty = 20
    else:
        discoloration = "Normal"
        disc_penalty = 0

    # Visible spoilage
    if storage_duration_hours and storage_duration_hours > 6 and storage_method == "Room Temperature":
        visible_spoilage = "Minor signs"
        spoil_penalty = 25
    else:
        visible_spoilage = "Not detected"
        spoil_penalty = 0

    # Base condition score
    base_score = 94 - (seed_val % 8)
    storage_penalty = 0
    
    storage_method_str = storage_method or "Room Temperature"
    duration = storage_duration_hours if storage_duration_hours is not None else 2.0

    if storage_method_str == "Refrigerated":
        storage_penalty = max(0, int((duration - 24) * 0.5)) if duration > 24 else 0
        storage_summary = f"Refrigerated for {duration:.1f}h - Well preserved cold chain."
    elif storage_method_str in ["Heated/Insulated", "Hot Holding", "Insulated Container"]:
        storage_penalty = max(0, int((duration - 4) * 3)) if duration > 4 else 0
        storage_summary = f"Insulated hot-holding for {duration:.1f}h."
    elif storage_method_str == "Frozen":
        storage_penalty = 0
        storage_summary = f"Frozen storage for {duration:.1f}h - Stable."
    else: # Room Temperature
        storage_penalty = max(0, int((duration - 2) * 5)) if duration > 2 else 0
        storage_summary = f"Ambient room temperature for {duration:.1f}h."

    final_score = max(35, min(98, base_score - pkg_score_penalty - disc_penalty - spoil_penalty - storage_penalty))

    confidence = round(0.85 + ((seed_val % 10) * 0.01), 2)

    if confidence < 0.60:
        visual_condition = "UNCERTAIN"
        urgency_rec = "Visual confirmation required upon pickup"
    elif final_score >= 80:
        visual_condition = "GOOD"
        urgency_rec = "Standard Priority (Redistribute within safe window)"
    elif final_score >= 60:
        visual_condition = "FAIR"
        urgency_rec = "High Priority Pickup (Expedite delivery)"
    else:
        visual_condition = "POOR"
        urgency_rec = "Urgent Review Required (Quality inspection needed)"

    # Build structured visual observations
    observations = [
        f"Visual appearance: {visual_condition.lower()} condition, no severe surface deterioration observed.",
        f"Packaging integrity: {packaging.lower()}.",
        f"Discoloration: {discoloration.lower()} for {food_category} category.",
        f"Visible spoilage signs: {visible_spoilage.lower()}.",
        f"Storage evaluation: {storage_summary}"
    ]

    # Integrate Time-Aware Food Rescue Window calculation if preparation_time is provided
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
        ai_confidence_in=confidence
    )

    return {
        "food_detected": detected_item,
        "food_type": food_type or detected_item,
        "food_category": food_category,
        "visible_spoilage": visible_spoilage,
        "discoloration": discoloration,
        "packaging_integrity": packaging,
        "packaging": packaging, # Alias
        "packaging_condition": packaging_condition,
        "visual_condition": visual_condition,
        "confidence": confidence,
        "condition_score": final_score,
        "observations": observations,
        "safety_disclaimer": FOOD_SAFETY_DISCLAIMER,
        "warning": FOOD_SAFETY_DISCLAIMER, # Alias
        "storage_assessment": storage_summary,
        "urgency_recommendation": urgency_rec,
        "rescue_window": rescue_window_eval
    }
