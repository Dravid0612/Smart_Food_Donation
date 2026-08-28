"""
Food Knowledge Rules & Guidance System
======================================
Provides structured, auditable food profiles, storage modes, and advisory guidelines.
Every rule contains versioning, source documentation, review dates, and explicit guidance.

Strict Food Safety Rule:
AI and rule evaluations are strictly ADVISORY decision-support tools.
They NEVER certify microbiological or consumption safety.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

@dataclass
class FoodProfile:
    food_type: str
    category: str
    supported_storage_modes: List[str]
    base_shelf_hours_room_temp: float
    base_shelf_hours_refrigerated: float
    base_shelf_hours_hot_holding: float
    applicable_guidance: str
    rule_version: str = "2026.1"
    source: str = "FSSAI Surplus Food Handling Guidance / Codex Alimentarius Advisory"
    last_reviewed: str = "2026-06-15"
    verified_data: bool = True
    notes: str = "Advisory parameters for operational rescue estimation only."

# Auditable knowledge repository for common regional and general food types
FOOD_KNOWLEDGE_PROFILES: Dict[str, FoodProfile] = {
    # Cooked Indian Staple & Rice
    "idli": FoodProfile(
        food_type="Idli",
        category="Cooked Food",
        supported_storage_modes=["Room Temperature", "Refrigerated", "Insulated Container"],
        base_shelf_hours_room_temp=4.0,
        base_shelf_hours_refrigerated=24.0,
        base_shelf_hours_hot_holding=4.0,
        applicable_guidance="Steamed rice-lentil cakes. Sensitive to room temperature humidity; best distributed promptly when ambient.",
        source="FSSAI Guidelines on Safe Handling of Cooked Foods",
        last_reviewed="2026-06-15"
    ),
    "dosa": FoodProfile(
        food_type="Dosa",
        category="Cooked Food",
        supported_storage_modes=["Room Temperature", "Insulated Container"],
        base_shelf_hours_room_temp=3.5,
        base_shelf_hours_refrigerated=12.0,
        base_shelf_hours_hot_holding=3.0,
        applicable_guidance="Fermented batter crepe. High surface area; rapid texture decay under ambient conditions.",
        source="FSSAI Guidelines on Safe Handling of Cooked Foods",
        last_reviewed="2026-06-15"
    ),
    "rice": FoodProfile(
        food_type="Rice",
        category="Cooked Food",
        supported_storage_modes=["Room Temperature", "Refrigerated", "Hot Holding", "Insulated Container"],
        base_shelf_hours_room_temp=4.0,
        base_shelf_hours_refrigerated=24.0,
        base_shelf_hours_hot_holding=5.0,
        applicable_guidance="Steamed plain rice. Rapid cooling required if refrigerated; avoid prolonged ambient exposure.",
        source="FSSAI & Codex Hygiene Practice for Cooked Meals",
        last_reviewed="2026-06-15"
    ),
    "biryani": FoodProfile(
        food_type="Biryani",
        category="Cooked Food",
        supported_storage_modes=["Hot Holding", "Refrigerated", "Insulated Container", "Room Temperature"],
        base_shelf_hours_room_temp=3.5,
        base_shelf_hours_refrigerated=24.0,
        base_shelf_hours_hot_holding=5.0,
        applicable_guidance="Spiced rice preparation with rich ingredients. Prioritize hot-holding or immediate thermal insulation.",
        source="FSSAI Catering Sector Standards",
        last_reviewed="2026-06-15"
    ),
    "sambar_rice": FoodProfile(
        food_type="Sambar Rice",
        category="Cooked Food",
        supported_storage_modes=["Hot Holding", "Insulated Container", "Room Temperature", "Refrigerated"],
        base_shelf_hours_room_temp=3.5,
        base_shelf_hours_refrigerated=20.0,
        base_shelf_hours_hot_holding=4.5,
        applicable_guidance="Lentil-vegetable-rice mixed dish. Acidic tamarind base provides minor buffering; rapid distribution advised.",
        source="FSSAI Guidelines on Safe Handling of Cooked Foods",
        last_reviewed="2026-06-15"
    ),
    "curd_rice": FoodProfile(
        food_type="Curd Rice",
        category="Cooked Food",
        supported_storage_modes=["Refrigerated", "Room Temperature", "Insulated Container"],
        base_shelf_hours_room_temp=3.0,
        base_shelf_hours_refrigerated=18.0,
        base_shelf_hours_hot_holding=0.0, # Not suitable for hot holding
        applicable_guidance="Dairy-fermented rice dish. Must not be heated. Susceptible to over-acidification at ambient temperatures.",
        source="FSSAI Dairy and Cooked Food Handling Rules",
        last_reviewed="2026-06-15"
    ),
    "chapati": FoodProfile(
        food_type="Chapati",
        category="Cooked Food",
        supported_storage_modes=["Room Temperature", "Insulated Container", "Refrigerated"],
        base_shelf_hours_room_temp=6.0,
        base_shelf_hours_refrigerated=36.0,
        base_shelf_hours_hot_holding=4.0,
        applicable_guidance="Unleavened whole wheat flatbread. Low moisture compared to curries; keep covered to prevent drying.",
        source="FSSAI Guidelines on Safe Handling of Cooked Foods",
        last_reviewed="2026-06-15"
    ),
    "roti": FoodProfile(
        food_type="Roti",
        category="Cooked Food",
        supported_storage_modes=["Room Temperature", "Insulated Container", "Refrigerated"],
        base_shelf_hours_room_temp=6.0,
        base_shelf_hours_refrigerated=36.0,
        base_shelf_hours_hot_holding=4.0,
        applicable_guidance="Wheat flatbread. Keep covered in insulated wrap.",
        source="FSSAI Guidelines on Safe Handling of Cooked Foods",
        last_reviewed="2026-06-15"
    ),
    "dal": FoodProfile(
        food_type="Dal",
        category="Cooked Food",
        supported_storage_modes=["Hot Holding", "Insulated Container", "Refrigerated", "Room Temperature"],
        base_shelf_hours_room_temp=4.0,
        base_shelf_hours_refrigerated=24.0,
        base_shelf_hours_hot_holding=5.0,
        applicable_guidance="Cooked lentil soup. High protein liquid medium; maintain hot-holding (>60C) or rapid chill.",
        source="FSSAI & Codex Hygiene Practice for Cooked Meals",
        last_reviewed="2026-06-15"
    ),
    "sambar": FoodProfile(
        food_type="Sambar",
        category="Cooked Food",
        supported_storage_modes=["Hot Holding", "Insulated Container", "Refrigerated", "Room Temperature"],
        base_shelf_hours_room_temp=4.0,
        base_shelf_hours_refrigerated=24.0,
        base_shelf_hours_hot_holding=5.0,
        applicable_guidance="Lentil-tamarind stew. Maintain covered storage.",
        source="FSSAI Guidelines on Safe Handling of Cooked Foods",
        last_reviewed="2026-06-15"
    ),
    "vegetable_curry": FoodProfile(
        food_type="Vegetable Curry",
        category="Cooked Food",
        supported_storage_modes=["Hot Holding", "Insulated Container", "Refrigerated", "Room Temperature"],
        base_shelf_hours_room_temp=4.0,
        base_shelf_hours_refrigerated=24.0,
        base_shelf_hours_hot_holding=5.0,
        applicable_guidance="Cooked vegetable preparation in spiced gravy. Ensure continuous covering.",
        source="FSSAI Guidelines on Safe Handling of Cooked Foods",
        last_reviewed="2026-06-15"
    ),
    # Bakery
    "bread": FoodProfile(
        food_type="Bread",
        category="Bakery",
        supported_storage_modes=["Room Temperature", "Frozen"],
        base_shelf_hours_room_temp=48.0,
        base_shelf_hours_refrigerated=48.0,
        base_shelf_hours_hot_holding=0.0,
        applicable_guidance="Baked leavened loaf. Keep sealed in dry environment; refrigeration may cause staling.",
        source="FSSAI Bakery Products Guidelines",
        last_reviewed="2026-06-15"
    ),
    "bun": FoodProfile(
        food_type="Bun",
        category="Bakery",
        supported_storage_modes=["Room Temperature"],
        base_shelf_hours_room_temp=48.0,
        base_shelf_hours_refrigerated=48.0,
        base_shelf_hours_hot_holding=0.0,
        applicable_guidance="Baked rolls and buns. Keep sealed against moisture.",
        source="FSSAI Bakery Products Guidelines",
        last_reviewed="2026-06-15"
    ),
    "cake": FoodProfile(
        food_type="Cake",
        category="Bakery",
        supported_storage_modes=["Refrigerated", "Room Temperature"],
        base_shelf_hours_room_temp=24.0,
        base_shelf_hours_refrigerated=72.0,
        base_shelf_hours_hot_holding=0.0,
        applicable_guidance="Confectionery cake. Cream/dairy frosted cakes require mandatory refrigeration (<5C).",
        source="FSSAI Bakery Products Guidelines",
        last_reviewed="2026-06-15"
    ),
    "pastry": FoodProfile(
        food_type="Pastry",
        category="Bakery",
        supported_storage_modes=["Refrigerated", "Room Temperature"],
        base_shelf_hours_room_temp=12.0,
        base_shelf_hours_refrigerated=48.0,
        base_shelf_hours_hot_holding=0.0,
        applicable_guidance="Filled pastry goods. High sensitivity if cream/custard filled.",
        source="FSSAI Bakery Products Guidelines",
        last_reviewed="2026-06-15"
    ),
    # Raw Produce & Generic Fallbacks
    "fruits": FoodProfile(
        food_type="Fresh Fruits",
        category="Fruits",
        supported_storage_modes=["Room Temperature", "Refrigerated"],
        base_shelf_hours_room_temp=48.0,
        base_shelf_hours_refrigerated=120.0,
        base_shelf_hours_hot_holding=0.0,
        applicable_guidance="Whole fresh fruits. Inspect for bruising or skin rupture.",
        source="Codex Alimentarius Code of Hygienic Practice for Fresh Fruits and Vegetables",
        last_reviewed="2026-06-15"
    ),
    "vegetables": FoodProfile(
        food_type="Fresh Vegetables",
        category="Vegetables",
        supported_storage_modes=["Room Temperature", "Refrigerated"],
        base_shelf_hours_room_temp=36.0,
        base_shelf_hours_refrigerated=96.0,
        base_shelf_hours_hot_holding=0.0,
        applicable_guidance="Raw vegetables. Keep dry and ventilated.",
        source="Codex Alimentarius Code of Hygienic Practice for Fresh Fruits and Vegetables",
        last_reviewed="2026-06-15"
    ),
    "packaged_food": FoodProfile(
        food_type="Packaged Food",
        category="Packaged Food",
        supported_storage_modes=["Room Temperature", "Refrigerated"],
        base_shelf_hours_room_temp=168.0,
        base_shelf_hours_refrigerated=168.0,
        base_shelf_hours_hot_holding=0.0,
        applicable_guidance="Commercially sealed packaged food. Check manufacturer printed best-before date.",
        source="FSSAI Packaging and Labelling Regulations",
        last_reviewed="2026-06-15"
    )
}

# Generic Category Fallback Profiles covering standard and regional food broad classes
GENERIC_CATEGORY_PROFILES: Dict[str, FoodProfile] = {
    "Cooked Food": FoodProfile(
        food_type="General Cooked Meal",
        category="Cooked Food",
        supported_storage_modes=["Room Temperature", "Refrigerated", "Hot Holding", "Insulated Container"],
        base_shelf_hours_room_temp=4.0,
        base_shelf_hours_refrigerated=24.0,
        base_shelf_hours_hot_holding=4.5,
        applicable_guidance="Standard cooked surplus food. Keep covered; distribute within operational rescue window.",
        source="FSSAI Surplus Food Handling Guidance",
        last_reviewed="2026-06-15"
    ),
    "cooked_rice_grain": FoodProfile(
        food_type="Cooked Rice / Grain Dish",
        category="Cooked Rice / Grain",
        supported_storage_modes=["Room Temperature", "Refrigerated", "Hot Holding", "Insulated Container"],
        base_shelf_hours_room_temp=3.5,
        base_shelf_hours_refrigerated=24.0,
        base_shelf_hours_hot_holding=4.5,
        applicable_guidance="Cooked rice, millets, quinoa, oats, or grain preparations. Prompt thermal protection recommended.",
        source="FSSAI & Codex Hygiene Practice for Cooked Meals",
        last_reviewed="2026-06-15"
    ),
    "cooked_vegetable": FoodProfile(
        food_type="Cooked Vegetable Dish",
        category="Cooked Vegetable",
        supported_storage_modes=["Room Temperature", "Refrigerated", "Hot Holding", "Insulated Container"],
        base_shelf_hours_room_temp=4.0,
        base_shelf_hours_refrigerated=24.0,
        base_shelf_hours_hot_holding=4.5,
        applicable_guidance="Cooked vegetable poriyal, sabzi, or dry vegetable preparation.",
        source="FSSAI Surplus Food Handling Guidance",
        last_reviewed="2026-06-15"
    ),
    "dal_lentil": FoodProfile(
        food_type="Dal / Lentil Dish",
        category="Dal / Lentils",
        supported_storage_modes=["Hot Holding", "Refrigerated", "Room Temperature", "Insulated Container"],
        base_shelf_hours_room_temp=4.0,
        base_shelf_hours_refrigerated=24.0,
        base_shelf_hours_hot_holding=5.0,
        applicable_guidance="Lentil, legume, or pulse preparations. Maintain hot holding (>60°C) or rapid cooling.",
        source="FSSAI Catering Sector Standards",
        last_reviewed="2026-06-15"
    ),
    "curry_gravy": FoodProfile(
        food_type="Curry / Gravy Dish",
        category="Curry / Gravy",
        supported_storage_modes=["Hot Holding", "Refrigerated", "Room Temperature", "Insulated Container"],
        base_shelf_hours_room_temp=3.5,
        base_shelf_hours_refrigerated=24.0,
        base_shelf_hours_hot_holding=5.0,
        applicable_guidance="High-moisture spiced curry or gravy. Continuous covering required.",
        source="FSSAI Surplus Food Handling Guidance",
        last_reviewed="2026-06-15"
    ),
    "dairy_based": FoodProfile(
        food_type="Dairy-Based Dish / Sweet",
        category="Dairy-Based",
        supported_storage_modes=["Refrigerated", "Room Temperature", "Insulated Container"],
        base_shelf_hours_room_temp=3.0,
        base_shelf_hours_refrigerated=18.0,
        base_shelf_hours_hot_holding=0.0,
        applicable_guidance="Milk, paneer, curd, or dairy-sweet preparations. Requires cool storage.",
        source="FSSAI Dairy Products Standards",
        last_reviewed="2026-06-15"
    ),
    "meat": FoodProfile(
        food_type="Cooked Meat / Poultry Dish",
        category="Meat",
        supported_storage_modes=["Hot Holding", "Refrigerated", "Insulated Container"],
        base_shelf_hours_room_temp=3.0,
        base_shelf_hours_refrigerated=24.0,
        base_shelf_hours_hot_holding=5.0,
        applicable_guidance="Cooked meat/poultry. Maintain thermal control at all stages.",
        source="FSSAI Meat & Poultry Handling Rules",
        last_reviewed="2026-06-15"
    ),
    "egg": FoodProfile(
        food_type="Egg-Based Dish",
        category="Egg",
        supported_storage_modes=["Refrigerated", "Room Temperature", "Hot Holding"],
        base_shelf_hours_room_temp=3.0,
        base_shelf_hours_refrigerated=24.0,
        base_shelf_hours_hot_holding=4.0,
        applicable_guidance="Boiled, scrambled, or cooked egg preparation.",
        source="FSSAI Safe Food Guidelines",
        last_reviewed="2026-06-15"
    ),
    "seafood": FoodProfile(
        food_type="Cooked Seafood Dish",
        category="Seafood",
        supported_storage_modes=["Refrigerated", "Hot Holding", "Insulated Container"],
        base_shelf_hours_room_temp=2.5,
        base_shelf_hours_refrigerated=18.0,
        base_shelf_hours_hot_holding=4.5,
        applicable_guidance="Fish or shellfish dish. Highly perishable; immediate insulated transit needed.",
        source="FSSAI Fish & Fisheries Products Guidance",
        last_reviewed="2026-06-15"
    ),
    "Bakery": FoodProfile(
        food_type="General Bakery Item",
        category="Bakery",
        supported_storage_modes=["Room Temperature", "Refrigerated"],
        base_shelf_hours_room_temp=36.0,
        base_shelf_hours_refrigerated=72.0,
        base_shelf_hours_hot_holding=0.0,
        applicable_guidance="General bakery surplus. Keep sealed in cool, dry conditions.",
        source="FSSAI Bakery Products Guidelines",
        last_reviewed="2026-06-15"
    ),
    "bakery": FoodProfile(
        food_type="General Bakery Item",
        category="Bakery",
        supported_storage_modes=["Room Temperature", "Refrigerated"],
        base_shelf_hours_room_temp=36.0,
        base_shelf_hours_refrigerated=72.0,
        base_shelf_hours_hot_holding=0.0,
        applicable_guidance="General bakery surplus. Keep sealed in cool, dry conditions.",
        source="FSSAI Bakery Products Guidelines",
        last_reviewed="2026-06-15"
    ),
    "Fruits": FoodProfile(
        food_type="General Fruits",
        category="Fruits",
        supported_storage_modes=["Room Temperature", "Refrigerated"],
        base_shelf_hours_room_temp=48.0,
        base_shelf_hours_refrigerated=120.0,
        base_shelf_hours_hot_holding=0.0,
        applicable_guidance="Fresh seasonal fruits.",
        source="Codex Fresh Produce Advisory",
        last_reviewed="2026-06-15"
    ),
    "fruit": FoodProfile(
        food_type="General Fruits",
        category="Fruits",
        supported_storage_modes=["Room Temperature", "Refrigerated"],
        base_shelf_hours_room_temp=48.0,
        base_shelf_hours_refrigerated=120.0,
        base_shelf_hours_hot_holding=0.0,
        applicable_guidance="Fresh seasonal fruits.",
        source="Codex Fresh Produce Advisory",
        last_reviewed="2026-06-15"
    ),
    "Vegetables": FoodProfile(
        food_type="General Vegetables",
        category="Vegetables",
        supported_storage_modes=["Room Temperature", "Refrigerated"],
        base_shelf_hours_room_temp=36.0,
        base_shelf_hours_refrigerated=96.0,
        base_shelf_hours_hot_holding=0.0,
        applicable_guidance="Fresh farm produce vegetables.",
        source="Codex Fresh Produce Advisory",
        last_reviewed="2026-06-15"
    ),
    "vegetable": FoodProfile(
        food_type="General Vegetables",
        category="Vegetables",
        supported_storage_modes=["Room Temperature", "Refrigerated"],
        base_shelf_hours_room_temp=36.0,
        base_shelf_hours_refrigerated=96.0,
        base_shelf_hours_hot_holding=0.0,
        applicable_guidance="Fresh farm produce vegetables.",
        source="Codex Fresh Produce Advisory",
        last_reviewed="2026-06-15"
    ),
    "snack_fried": FoodProfile(
        food_type="Snack / Fried Food",
        category="Snack / Fried",
        supported_storage_modes=["Room Temperature", "Insulated Container", "Refrigerated"],
        base_shelf_hours_room_temp=6.0,
        base_shelf_hours_refrigerated=36.0,
        base_shelf_hours_hot_holding=4.0,
        applicable_guidance="Samosas, pakoras, vada, cutlets, or dry snacks. Keep ventilated/covered.",
        source="FSSAI Street Food & Snack Handling Standards",
        last_reviewed="2026-06-15"
    ),
    "Packaged Food": FoodProfile(
        food_type="General Packaged Item",
        category="Packaged Food",
        supported_storage_modes=["Room Temperature", "Refrigerated"],
        base_shelf_hours_room_temp=168.0,
        base_shelf_hours_refrigerated=168.0,
        base_shelf_hours_hot_holding=0.0,
        applicable_guidance="Sealed packaged goods.",
        source="FSSAI Packaging Regulations",
        last_reviewed="2026-06-15"
    ),
    "packaged": FoodProfile(
        food_type="General Packaged Item",
        category="Packaged Food",
        supported_storage_modes=["Room Temperature", "Refrigerated"],
        base_shelf_hours_room_temp=168.0,
        base_shelf_hours_refrigerated=168.0,
        base_shelf_hours_hot_holding=0.0,
        applicable_guidance="Sealed packaged goods.",
        source="FSSAI Packaging Regulations",
        last_reviewed="2026-06-15"
    ),
    "frozen": FoodProfile(
        food_type="Frozen Food Item",
        category="Frozen Food",
        supported_storage_modes=["Frozen", "Refrigerated"],
        base_shelf_hours_room_temp=2.0,
        base_shelf_hours_refrigerated=24.0,
        base_shelf_hours_hot_holding=0.0,
        applicable_guidance="Pre-frozen surplus. Thaw only under controlled refrigerated conditions.",
        source="FSSAI Quick Frozen Food Regulations",
        last_reviewed="2026-06-15"
    ),
    "Other": FoodProfile(
        food_type="Unspecified Food Surplus",
        category="Other",
        supported_storage_modes=["Room Temperature", "Refrigerated", "Insulated Container"],
        base_shelf_hours_room_temp=3.5,
        base_shelf_hours_refrigerated=24.0,
        base_shelf_hours_hot_holding=4.0,
        applicable_guidance="Unspecified food type; requires visual check upon handover.",
        source="FSSAI General Food Hygiene Rules",
        last_reviewed="2026-06-15",
        verified_data=False,
        notes="Unspecified food type; parameters default to conservative cooked food values."
    ),
    "not_sure": FoodProfile(
        food_type="Unspecified Food Surplus",
        category="Not Sure",
        supported_storage_modes=["Room Temperature", "Refrigerated", "Insulated Container"],
        base_shelf_hours_room_temp=3.0,
        base_shelf_hours_refrigerated=18.0,
        base_shelf_hours_hot_holding=3.5,
        applicable_guidance="Unspecified food category. Conservative advisory window applied.",
        source="FSSAI General Food Hygiene Rules",
        last_reviewed="2026-06-15",
        verified_data=False,
        notes="Conservative fallback applied due to limited food-specific metadata."
    )
}

def normalize_category_key(raw: Optional[str]) -> str:
    if not raw:
        return "Cooked Food"
    clean = raw.strip().lower().replace(" ", "_").replace("/", "_").replace("-", "_")
    
    mapping = {
        "cooked_food": "Cooked Food",
        "cooked_rice": "cooked_rice_grain",
        "cooked_rice_grain": "cooked_rice_grain",
        "cooked_rice___grain_dish": "cooked_rice_grain",
        "grain": "cooked_rice_grain",
        "cooked_vegetable": "cooked_vegetable",
        "cooked_vegetable_dish": "cooked_vegetable",
        "dal": "dal_lentil",
        "dal_lentil": "dal_lentil",
        "dal___lentil_dish": "dal_lentil",
        "lentils": "dal_lentil",
        "curry": "curry_gravy",
        "curry_gravy": "curry_gravy",
        "curry___gravy": "curry_gravy",
        "gravy": "curry_gravy",
        "dairy": "dairy_based",
        "dairy_based": "dairy_based",
        "meat": "meat",
        "egg": "egg",
        "seafood": "seafood",
        "bakery": "Bakery",
        "fruit": "Fruits",
        "fruits": "Fruits",
        "vegetable": "Vegetables",
        "vegetables": "Vegetables",
        "snack": "snack_fried",
        "snack_fried": "snack_fried",
        "snack___fried_food": "snack_fried",
        "packaged": "Packaged Food",
        "packaged_food": "Packaged Food",
        "ready_to_eat_packaged_food": "packaged",
        "frozen": "frozen",
        "frozen_food": "frozen",
        "not_sure": "not_sure",
        "other": "Other"
    }
    return mapping.get(clean, raw)

def resolve_food_profile(food_type: Optional[str], food_category: Optional[str]) -> FoodProfile:
    """
    Resolves the most specific auditable FoodProfile for given food_type and food_category.
    Returns specific matched profile or fallback category profile.
    """
    if food_type:
        clean_key = food_type.strip().lower().replace(" ", "_").replace("-", "_")
        if clean_key in FOOD_KNOWLEDGE_PROFILES:
            return FOOD_KNOWLEDGE_PROFILES[clean_key]
        # Partial key matching (e.g. 'chicken biryani' -> 'biryani')
        for k, prof in FOOD_KNOWLEDGE_PROFILES.items():
            if k in clean_key:
                return prof

    # Category-level resolution
    norm_cat = normalize_category_key(food_category)
    if norm_cat in GENERIC_CATEGORY_PROFILES:
        return GENERIC_CATEGORY_PROFILES[norm_cat]
    
    raw_cat = food_category.strip() if food_category else "Cooked Food"
    if raw_cat in GENERIC_CATEGORY_PROFILES:
        return GENERIC_CATEGORY_PROFILES[raw_cat]
    
    return GENERIC_CATEGORY_PROFILES["Other"]

def calculate_rule_coverage(
    food_type: Optional[str],
    food_category: Optional[str],
    is_custom: bool = False
) -> str:
    """
    Calculates rule coverage rating:
    - HIGH: Specific predefined profile exists in knowledge base (e.g. Rice, Idli, Dosa, Biryani).
    - MEDIUM: Custom food with a recognized broad food category selected (e.g. Pongal -> cooked_rice_grain).
    - LOW: Completely custom / unknown food with generic / unspecified category.
    """
    if not is_custom and food_type:
        clean_key = food_type.strip().lower().replace(" ", "_")
        if clean_key in FOOD_KNOWLEDGE_PROFILES:
            return "HIGH"
        for k in FOOD_KNOWLEDGE_PROFILES.keys():
            if k in clean_key:
                return "HIGH"

    norm_cat = normalize_category_key(food_category)
    if norm_cat in ["not_sure", "Other", "other", None]:
        return "LOW"
    
    if norm_cat in GENERIC_CATEGORY_PROFILES:
        return "MEDIUM"
        
    return "LOW"

def estimate_equivalent_meals(
    quantity_value: float,
    quantity_unit: str,
    unit_label: Optional[str] = None
) -> Optional[float]:
    """
    Calculates estimated equivalent meals based on typical nutritional/portion factors:
    - Meals, Portions, Plates: 1:1
    - Kg: ~2.2 meals per kg (approx 450g per meal)
    - Grams: ~2.2 meals per 1000g
    - Litres: ~2.5 meals per litre
    - mL: ~2.5 meals per 1000 mL
    - Pieces, Packets, Boxes: 1:1 (e.g. sandwiches, samosas)
    - Trays: ~15 meals per tray
    - Containers: ~5 meals per container
    - Bottles: ~2 meals per bottle
    - Custom: None or estimated proportional to label
    """
    if quantity_value <= 0:
        return 0.0

    unit_clean = quantity_unit.strip().lower()
    
    if unit_clean in ["meals", "portions", "plates"]:
        return round(float(quantity_value), 1)
    elif unit_clean in ["kg", "kilograms"]:
        return round(float(quantity_value) * 2.22, 1)
    elif unit_clean in ["grams", "g"]:
        return round((float(quantity_value) / 1000.0) * 2.22, 1)
    elif unit_clean in ["litres", "liters", "l"]:
        return round(float(quantity_value) * 2.5, 1)
    elif unit_clean in ["ml", "millilitres", "milliliters"]:
        return round((float(quantity_value) / 1000.0) * 2.5, 1)
    elif unit_clean in ["pieces", "packets", "boxes"]:
        return round(float(quantity_value) * 1.0, 1)
    elif unit_clean in ["trays"]:
        return round(float(quantity_value) * 15.0, 1)
    elif unit_clean in ["containers"]:
        return round(float(quantity_value) * 5.0, 1)
    elif unit_clean in ["bottles"]:
        return round(float(quantity_value) * 2.0, 1)
    else:
        # Custom unit without strict standard factor
        return round(float(quantity_value), 1)

