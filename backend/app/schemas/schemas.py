from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime

# Token Schemas
class Token(BaseModel):
    access_token: str
    refresh_token: str  # Long-lived refresh token for session renewal
    token_type: str = "bearer"
    user_id: int
    role: str
    name: str
    email: str

class RefreshRequest(BaseModel):
    refresh_token: str

class TokenData(BaseModel):
    user_id: Optional[int] = None
    role: Optional[str] = None

# User Schemas
class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    phone: Optional[str] = None
    role: str = "donor" # donor, ngo, volunteer, admin
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    organization_name: Optional[str] = None # Optional if registering as NGO
    description: Optional[str] = None # NGO description
    capacity: Optional[int] = 100 # NGO capacity
    vehicle_type: Optional[str] = "bike" # Volunteer vehicle type: walking, bike, car, van
    carrying_capacity: Optional[int] = 50 # Volunteer meals capacity

class UserLogin(BaseModel):
    email: str # Can be email address or registered phone number
    password: str

class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    phone: Optional[str] = None
    role: str
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    profile_image: Optional[str] = None
    vehicle_type: Optional[str] = "bike"
    carrying_capacity: Optional[int] = 50
    reliability_score: Optional[float] = 95.0
    completed_deliveries: Optional[int] = 0
    failed_deliveries: Optional[int] = 0
    preferred_language: Optional[str] = "en"
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class VolunteerProfileUpdate(BaseModel):
    vehicle_type: Optional[str] = None # walking, bike, car, van
    carrying_capacity: Optional[int] = None
    is_active: Optional[bool] = None

# NGO Schemas
class NGOCreate(BaseModel):
    organization_name: str
    description: Optional[str] = None
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    capacity: int = 100
    contact_phone: Optional[str] = None
    operating_hours: Optional[str] = None
    demand_requirements: Optional[str] = None

class NGOUpdate(BaseModel):
    organization_name: Optional[str] = None
    description: Optional[str] = None
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    capacity: Optional[int] = None
    current_capacity: Optional[int] = None
    is_available: Optional[bool] = None
    contact_phone: Optional[str] = None
    operating_hours: Optional[str] = None
    demand_requirements: Optional[str] = None

class NGOOperatingHoursUpdate(BaseModel):
    operating_hours: Any # JSON string or dict e.g. {"monday": {"open": "08:00", "close": "20:00", "closed": false}, ...}

class NGODemandUpdate(BaseModel):
    demand_requirements: Any # JSON string or dict e.g. {"Cooked Food": 80, "Bakery": 20, "Fruits": 30, "Packaged Food": 50}

class NGOResponse(BaseModel):
    id: int
    user_id: int
    organization_name: str
    description: Optional[str] = None
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    capacity: int
    current_capacity: int
    is_available: bool
    is_verified: bool
    contact_phone: Optional[str] = None
    operating_hours: Optional[str] = None
    demand_requirements: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

# AI Vision & Decision Fusion Schemas
class AIFoodAnalysisResponse(BaseModel):
    food_detected: str
    visible_spoilage: str # Not detected, Minor signs, Visible signs
    discoloration: str # Normal, Slight variation, Abnormal
    packaging_integrity: str = "GOOD" # GOOD, FAIR, POOR, Intact, Exposed, Damaged
    packaging: Optional[str] = None # Backward compatibility alias
    visual_condition: str # GOOD, FAIR, POOR
    confidence: float # e.g. 0.88
    condition_score: Optional[int] = 85 # 0-100
    observations: List[str] = []
    safety_disclaimer: str = "Visual assessment only; this does not certify food safety."
    warning: Optional[str] = None # Backward compatibility alias
    storage_assessment: Optional[str] = None
    urgency_recommendation: Optional[str] = "Normal Priority"

class FoodAnalysisCreate(BaseModel):
    food_detected: Optional[str] = None
    visible_spoilage: Optional[str] = "Not detected"
    discoloration: Optional[str] = "Normal"
    packaging_integrity: Optional[str] = "GOOD"
    visual_condition: str = "GOOD"
    confidence: float = 0.87
    observations: Optional[str] = None
    storage_assessment: Optional[str] = None
    urgency_recommendation: Optional[str] = "Normal Priority"

class FoodAnalysisResponse(BaseModel):
    id: int
    donation_id: Optional[int] = None
    food_detected: Optional[str] = None
    visible_spoilage: Optional[str] = "Not detected"
    discoloration: Optional[str] = "Normal"
    packaging_integrity: Optional[str] = "GOOD"
    visual_condition: str = "GOOD"
    confidence: float = 0.87
    observations: Optional[str] = None
    safety_disclaimer: str = "Visual assessment only; this does not certify food safety."
    storage_assessment: Optional[str] = None
    urgency_recommendation: Optional[str] = "Normal Priority"
    analyzed_at: datetime

    model_config = ConfigDict(from_attributes=True)

class RescueChecklistResponse(BaseModel):
    demand_matched: bool = True
    ngo_open: bool = True
    ngo_capacity_available: bool = True
    volunteer_available: bool = True
    volunteer_capacity_sufficient: bool = True
    deadline_valid: bool = True
    expiry_status: str = "NORMAL" # NORMAL, URGENT, EXPIRED
    rescue_opportunity_status: str = "HIGH" # HIGH, MEDIUM, ATTENTION_NEEDED
    details: Dict[str, Any] = {}

# Food Donation Schemas
class FoodRescueWindowResponse(BaseModel):
    assessment_status: str = "ADVISORY"
    food_type: str
    food_category: str
    rule_source: str
    rule_version: str
    rule_coverage: Optional[str] = "HIGH" # HIGH, MEDIUM, LOW
    is_custom: Optional[bool] = False
    visual_condition: str # GOOD, FAIR, CONCERNING, UNCERTAIN
    estimated_window_start: str
    estimated_window_end: str
    remaining_minutes: int
    estimated_window_display: str
    urgency_level: str # FRESH, APPROACHING, URGENT, CRITICAL
    urgency_score: float
    confidence: float
    reasons: List[str] = []
    safety_disclaimer: str = "Visual assessment only. This is an advisory estimate and does not certify food safety."
    disclaimer: Optional[str] = None

class RescueFeasibilityResponse(BaseModel):
    feasibility_status: str # RESCUE_FEASIBLE, AT_RISK, RESCUE_UNLIKELY
    feasibility_label: str
    is_feasible: bool
    estimated_pickup_minutes: float = 15.0
    estimated_travel_minutes: float = 20.0
    ngo_intake_minutes: float = 10.0
    safety_buffer_minutes: float = 15.0
    total_required_minutes: float = 60.0
    remaining_buffer_minutes: int = 0
    explanation: str

class DonationCreate(BaseModel):
    food_name: str
    food_type: Optional[str] = None
    food_source: Optional[str] = "KNOWN" # "KNOWN" vs "CUSTOM"
    custom_food_name: Optional[str] = None
    food_description: Optional[str] = None
    major_ingredients: Optional[str] = None # e.g. "rice, lentils, dairy, vegetables"
    description: Optional[str] = None
    food_category: str
    quantity: float
    quantity_unit: str = "Meals" # Meals, Portions, Kg, Grams, Litres, mL, Pieces, Packets, Boxes, Trays, Containers, Plates, Bottles, Custom
    quantity_unit_label: Optional[str] = None # Optional label when quantity_unit is 'Custom'
    estimated_meals: Optional[float] = None
    rule_coverage: Optional[str] = "HIGH"
    classification_source: Optional[str] = "rule_exact"
    classification_confidence: Optional[float] = 1.0
    preparation_time: datetime
    expiry_time: datetime
    pickup_address: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    image_url: Optional[str] = None
    storage_method: Optional[str] = "Room Temperature"
    storage_duration_hours: Optional[float] = 2.0
    storage_continuous: Optional[bool] = True
    storage_history_json: Optional[str] = None
    packaging_condition: Optional[str] = "Covered"
    previously_served: Optional[str] = "No"
    exposure_status: Optional[str] = "No"
    handling_status: Optional[str] = "No"
    pickup_deadline: Optional[datetime] = None
    ai_food_detected: Optional[str] = None
    ai_visible_spoilage: Optional[str] = None
    ai_discoloration: Optional[str] = None
    ai_packaging_intact: Optional[str] = None
    ai_visual_condition: Optional[str] = "GOOD"
    ai_confidence_score: Optional[float] = 0.88
    condition_score: Optional[int] = 85
    safety_check_answers: Optional[Dict[str, bool]] = None
    safety_check_completed: Optional[bool] = False

class DonationUpdate(BaseModel):
    food_name: Optional[str] = None
    food_type: Optional[str] = None
    food_source: Optional[str] = None
    custom_food_name: Optional[str] = None
    food_description: Optional[str] = None
    major_ingredients: Optional[str] = None
    description: Optional[str] = None
    food_category: Optional[str] = None
    quantity: Optional[float] = None
    quantity_unit: Optional[str] = None
    quantity_unit_label: Optional[str] = None
    estimated_meals: Optional[float] = None
    preparation_time: Optional[datetime] = None
    expiry_time: Optional[datetime] = None
    pickup_address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    image_url: Optional[str] = None

class DonationAcceptRequest(BaseModel):
    pickup_mode: Optional[str] = "volunteer_dispatch" # volunteer_dispatch or self_pickup
    offer_id: Optional[int] = None
    remarks: Optional[str] = None

class DonationHistoryResponse(BaseModel):
    id: int
    donation_id: int
    old_status: Optional[str] = None
    new_status: str
    changed_by: Optional[int] = None
    remarks: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class DonationResponse(BaseModel):
    id: int
    donor_id: int
    food_name: str
    food_type: Optional[str] = None
    food_source: Optional[str] = "KNOWN"
    custom_food_name: Optional[str] = None
    food_description: Optional[str] = None
    major_ingredients: Optional[str] = None
    description: Optional[str] = None
    food_category: str
    quantity: float
    quantity_unit: str
    quantity_unit_label: Optional[str] = None
    estimated_meals: Optional[float] = None
    rule_coverage: Optional[str] = "HIGH"
    classification_source: Optional[str] = "rule_exact"
    classification_confidence: Optional[float] = 1.0
    preparation_time: datetime
    expiry_time: datetime
    pickup_address: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    image_url: Optional[str] = None
    storage_method: Optional[str] = None
    storage_duration_hours: Optional[float] = None
    storage_continuous: Optional[bool] = True
    storage_history_json: Optional[str] = None
    packaging_condition: Optional[str] = None
    previously_served: Optional[str] = "No"
    exposure_status: Optional[str] = "No"
    handling_status: Optional[str] = "No"
    pickup_deadline: Optional[datetime] = None
    estimated_window_start: Optional[datetime] = None
    estimated_window_end: Optional[datetime] = None
    remaining_minutes: Optional[int] = None
    rescue_urgency_level: Optional[str] = "FRESH"
    feasibility_status: Optional[str] = "RESCUE_FEASIBLE"
    reasons_json: Optional[str] = None
    ai_food_detected: Optional[str] = None
    ai_visible_spoilage: Optional[str] = None
    ai_discoloration: Optional[str] = None
    ai_packaging_intact: Optional[str] = None
    ai_visual_condition: Optional[str] = None
    ai_confidence_score: Optional[float] = None
    ai_safety_disclaimer: Optional[str] = None
    condition_score: Optional[int] = None
    status: str
    failure_reason: Optional[str] = None
    is_emergency: Optional[bool] = False
    assigned_ngo_id: Optional[int] = None
    assigned_volunteer_id: Optional[int] = None

    # Real-Time Tracking fields
    tracking_latitude: Optional[float] = None
    tracking_longitude: Optional[float] = None
    tracking_last_updated_at: Optional[datetime] = None
    current_eta_minutes: Optional[float] = None
    current_distance_km: Optional[float] = None
    tracking_status: Optional[str] = "IDLE"

    # Dynamic Rematching fields
    rematch_count: Optional[int] = 0
    rematch_reason: Optional[str] = None
    is_rematched: Optional[bool] = False
    previous_volunteer_id: Optional[int] = None

    # Food-Safety Self-Check fields
    safety_check_completed: Optional[bool] = False
    safety_check_status: Optional[str] = "PASSED"
    safety_check_version: Optional[str] = "2026.1"

    created_at: datetime
    updated_at: datetime
    urgency_level: Optional[str] = "Fresh" # Fresh, Use Soon, Urgent, Expired
    pickup_mode: Optional[str] = "volunteer_dispatch"

    model_config = ConfigDict(from_attributes=True)

class DonationDetailResponse(DonationResponse):
    donor_name: Optional[str] = None
    donor_phone: Optional[str] = None   # Only shown to assigned volunteer after assignment
    ngo_name: Optional[str] = None
    volunteer_name: Optional[str] = None
    volunteer_phone: Optional[str] = None  # Only shown to NGO after assignment
    previous_volunteer_name: Optional[str] = None
    verification_otp: Optional[str] = None  # Only shown to donation owner (donor)
    qr_code_token: Optional[str] = None    # Only shown to donation owner (donor)
    food_analysis: Optional[FoodAnalysisResponse] = None
    rescue_checklist: Optional[RescueChecklistResponse] = None
    rescue_window: Optional[FoodRescueWindowResponse] = None
    feasibility: Optional[RescueFeasibilityResponse] = None
    history: List[DonationHistoryResponse] = []
    safety_check_answers: Optional[Dict[str, bool]] = None

# Food-Safety Self-Check Screening Schemas
class FoodSafetyCheckRequest(BaseModel):
    human_consumption: bool = True # 1. Was this food prepared for human consumption?
    hygienic_handling: bool = True # 2. Was the food handled hygienically?
    appropriate_storage: bool = True # 3. Was it stored appropriately for this type of food?
    contamination_free: bool = True # 4. Has it been kept free from contamination?
    suitable_condition: bool = True # 5. Is the food visibly suitable for donation?
    additional_notes: Optional[str] = None

class FoodSafetyCheckResponse(BaseModel):
    is_eligible: bool
    status: str # PASSED, UNSAFE_DECLARATION
    safety_check_version: str = "2026.1"
    failed_declarations: List[str] = []
    warning_message: Optional[str] = None
    disclaimer: str = "Screening declaration only. This does not certify microbiological food safety."
    guidance: Optional[str] = None

# Volunteer Location & Real-Time Tracking Schemas
class VolunteerLocationUpdateRequest(BaseModel):
    latitude: float
    longitude: float
    donation_id: Optional[int] = None
    assignment_id: Optional[int] = None
    speed_kmh: Optional[float] = None
    heading: Optional[float] = None
    battery_level: Optional[float] = None

class RescueTrackingStageItem(BaseModel):
    key: str
    title: str
    description: str
    is_completed: bool
    is_current: bool
    timestamp: Optional[str] = None

class RescueTrackingResponse(BaseModel):
    donation_id: int
    food_name: str
    quantity: float
    quantity_unit: str
    status: str
    tracking_stage: str # PENDING, NGO_ACCEPTED, VOLUNTEER_ASSIGNED, EN_ROUTE, ARRIVED_AT_DONOR, FOOD_COLLECTED, IN_TRANSIT, ARRIVED_AT_NGO, DELIVERED, COMPLETED
    tracking_stage_label: str
    
    volunteer_id: Optional[int] = None
    volunteer_name: Optional[str] = None
    volunteer_vehicle: Optional[str] = "bike"
    volunteer_status: Optional[str] = None
    volunteer_latitude: Optional[float] = None # Masked if unauthorized
    volunteer_longitude: Optional[float] = None # Masked if unauthorized
    
    pickup_address: str # Masked approximate area if unauthorized
    destination_name: Optional[str] = None
    destination_address: Optional[str] = None
    
    eta_minutes: Optional[int] = None
    eta_display: Optional[str] = None # e.g. "8 min (Estimated travel time)"
    distance_km: Optional[float] = None
    remaining_window_minutes: Optional[int] = None
    rescue_urgency_level: str = "FRESH"
    feasibility_status: str = "RESCUE_FEASIBLE" # RESCUE_FEASIBLE, AT_RISK, RESCUE_UNLIKELY
    feasibility_label: str = "Rescue Feasible"
    
    is_rematched: bool = False
    rematch_count: int = 0
    rematch_reason: Optional[str] = None
    rematch_notice: Optional[str] = None
    
    last_updated_at: Optional[datetime] = None
    next_action_prompt: str = "Awaiting next operational update."
    stages_timeline: List[RescueTrackingStageItem] = []

class DynamicRematchRequest(BaseModel):
    reason: Optional[str] = "Estimated arrival time exceeded remaining rescue window"
    force: bool = False

class DynamicRematchResponse(BaseModel):
    donation_id: int
    status: str # REMATCHED, FEASIBLE_NO_REMATCH_NEEDED, NO_VOLUNTEER_AVAILABLE, AT_RISK_ESCALATED
    rematch_count: int
    previous_volunteer_id: Optional[int] = None
    previous_volunteer_name: Optional[str] = None
    new_volunteer_id: Optional[int] = None
    new_volunteer_name: Optional[str] = None
    rematch_reason: str
    new_eta_minutes: Optional[int] = None
    feasibility_status: str
    notifications_dispatched: List[str] = []
    message: str

# Donor Custom Food Profile ('My Foods') Schemas
class DonorCustomFoodProfileCreate(BaseModel):
    name: str
    food_category: str
    description: Optional[str] = None
    major_ingredients: Optional[str] = None
    common_storage: Optional[str] = "Room Temperature"
    default_unit: Optional[str] = "Meals"

class DonorCustomFoodProfileResponse(BaseModel):
    id: int
    donor_id: int
    name: str
    food_category: str
    description: Optional[str] = None
    major_ingredients: Optional[str] = None
    common_storage: str = "Room Temperature"
    default_unit: str = "Meals"
    usage_count: int = 1
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class CustomFoodAggregatedAdminResponse(BaseModel):
    food_name: str
    count: int
    suggested_category: str
    sample_descriptions: List[str] = []
    sample_ingredients: List[str] = []

class DonationNGOPreviewResponse(BaseModel):
    """Field-filtered view for NGOs browsing donations BEFORE acceptance.
    Does NOT expose private donor contact or exact address."""
    id: int
    food_name: str
    food_type: Optional[str] = None
    food_category: str
    quantity: float
    quantity_unit: str
    ai_visual_condition: Optional[str] = None
    ai_confidence_score: Optional[float] = None
    condition_score: Optional[int] = None
    storage_method: Optional[str] = None
    storage_duration_hours: Optional[float] = None
    packaging_condition: Optional[str] = None
    preparation_time: datetime
    expiry_time: datetime
    pickup_deadline: Optional[datetime] = None
    estimated_window_end: Optional[datetime] = None
    remaining_minutes: Optional[int] = None
    feasibility_status: Optional[str] = "RESCUE_FEASIBLE"
    # Approximate area only — no exact address before acceptance
    pickup_area: Optional[str] = None
    status: str
    urgency_level: Optional[str] = "Fresh"
    is_emergency: Optional[bool] = False

    model_config = ConfigDict(from_attributes=True)

# Verification Schemas
class VerifyOtpRequest(BaseModel):
    donation_id: int
    otp: str

class VerifyQRRequest(BaseModel):
    donation_id: int
    qr_token: str

class DonationCancelRequest(BaseModel):
    reason: str # donor_unavailable, food_expired, quantity_mismatch, other

class DonationFailureRequest(BaseModel):
    failure_type: str # pickup_failed, delivery_failed
    reason: str # donor_unavailable, volunteer_rejected, food_expired, ngo_closed, incorrect_location, vehicle_issue, other
    remarks: Optional[str] = None

# Volunteer Assignment Schemas
class VolunteerAssignmentResponse(BaseModel):
    id: int
    donation_id: int
    volunteer_id: int
    assigned_at: datetime
    accepted_at: Optional[datetime] = None
    collected_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    status: str
    failure_reason: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

# Notification Schemas
class NotificationResponse(BaseModel):
    id: int
    user_id: int
    title: str
    message: str
    type: str
    related_donation_id: Optional[int] = None
    is_read: bool
    created_at: datetime
    # Extended fields: event routing, dedup, FCM tracking
    event_type: Optional[str] = None
    deep_link_data: Optional[str] = None
    dedup_key: Optional[str] = None
    is_sent: Optional[bool] = None
    sent_at: Optional[datetime] = None
    opened_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

# Reward Schemas
class RewardResponse(BaseModel):
    id: int
    user_id: int
    points: int
    level: str
    next_level_points: int = 100
    points_to_next_level: int = 100

    model_config = ConfigDict(from_attributes=True)

# Smart Recommendations
class NGORecommendationResponse(BaseModel):
    ngo_id: int
    organization_name: str
    distance_km: float
    score: float
    reason: str
    capacity: int
    current_capacity: int
    is_available: bool
    is_open_now: bool = True
    demand_matched: bool = False
    demand_match_detail: Optional[str] = None

class VolunteerRecommendationResponse(BaseModel):
    volunteer_id: int
    volunteer_name: str
    phone: Optional[str] = None
    vehicle_type: Optional[str] = "bike"
    carrying_capacity: int = 50
    reliability_score: float = 95.0
    active_tasks: int = 0
    distance_km: float
    score: float
    score_breakdown: Optional[Dict[str, float]] = None
    reason: str

# Admin Stats
class AdminStatsResponse(BaseModel):
    total_users: int
    total_donors: int
    total_ngos: int
    total_volunteers: int
    total_donations: int
    completed_donations: int
    pending_donations: int
    emergency_donations: int = 0
    failed_donations: int = 0
    meals_donated: float
    unverified_ngos: int

# Recurring Donation Schemas
class RecurringDonationCreate(BaseModel):
    template_name: str
    food_name: str
    food_category: str
    typical_quantity: float = 50.0
    quantity_unit: str = "Meals"
    frequency: str = "Daily"
    preferred_pickup_time: str = "20:30"
    pickup_address: str
    storage_method: Optional[str] = "Heated/Insulated"
    packaging_condition: Optional[str] = "Sealed / Covered"

class RecurringDonationResponse(BaseModel):
    id: int
    donor_id: int
    template_name: str
    food_name: str
    food_category: str
    typical_quantity: float
    quantity_unit: str
    frequency: str
    preferred_pickup_time: str
    pickup_address: str
    storage_method: Optional[str] = None
    packaging_condition: Optional[str] = None
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

# Kitchen Profile Schemas (Frequent Business Donors)
class KitchenProfileCreate(BaseModel):
    name: str  # e.g. "Main Kitchen", "Banquet Hall"
    location_address: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    typical_food_types: Optional[str] = "Rice, Curry, Idli, Dosa"
    default_storage_method: Optional[str] = "Refrigerated"
    contact_person: Optional[str] = None
    contact_phone: Optional[str] = None

class KitchenProfileResponse(BaseModel):
    id: int
    donor_id: int
    name: str
    location_address: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    typical_food_types: Optional[str] = None
    default_storage_method: Optional[str] = "Refrigerated"
    contact_person: Optional[str] = None
    contact_phone: Optional[str] = None
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

# Quick Repeat Donation Prefill Response
class RepeatDonationPrefillResponse(BaseModel):
    previous_donation_id: int
    food_name: str
    food_category: str
    food_type: Optional[str] = None
    typical_quantity: float
    quantity_unit: str
    pickup_address: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    default_storage_method: Optional[str] = "Room Temperature"
    packaging_condition: Optional[str] = "Covered"
    reconfirmation_required: List[str] = [
        "Current Quantity",
        "Preparation Timestamp",
        "Current Storage Condition",
        "Current Photo & Visual Assessment"
    ]

# Rating Schemas
class RatingCreate(BaseModel):
    donation_id: int
    to_user_id: int
    role_to: str
    rating_score: int = Field(ge=1, le=5)
    feedback: Optional[str] = None
    tags: Optional[str] = None

class RatingResponse(BaseModel):
    id: int
    donation_id: int
    from_user_id: int
    to_user_id: int
    role_from: str
    role_to: str
    rating_score: int
    feedback: Optional[str] = None
    tags: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

# Match Offer Schemas
class MatchOfferResponse(BaseModel):
    id: int
    donation_id: int
    candidate_id: int
    candidate_type: str
    score: float
    status: str
    offered_at: datetime
    expires_at: Optional[datetime] = None
    responded_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

# Certificate & CSR Impact Schemas
class CertificateResponse(BaseModel):
    certificate_id: str
    donation_id: int
    donor_name: str
    organization_type: str
    food_name: str
    quantity: float
    quantity_unit: str
    receiving_ngo: str
    completed_at: str
    verification_hash: str
    co2_saved_kg: float
    water_saved_liters: float
    title: str = "Certificate of Participation in Food Donation"
    disclaimer: str = "Issued for voluntary surplus food redistribution and community hunger relief."

class CSRImpactSummaryResponse(BaseModel):
    donor_id: int
    donor_name: str
    total_donations: int
    total_meals_donated: float
    total_co2_avoided_kg: float
    total_water_conserved_liters: float
    estimated_disposal_cost_avoided_inr: float
    verified_ngo_partners_count: int
    trust_score: float
    is_verified_donor: bool

class DonorMonthlyImpactItem(BaseModel):
    month: str
    donations_count: int
    meals_donated: float
    meals_rescued: float
    meals_distributed: float
    waste_diverted_kg: float
    successful_rescues: int
    partner_ngos_count: int

class DonorImpactSummaryResponse(BaseModel):
    donor_id: int
    donor_name: str
    total_donations_count: int
    successful_rescues_count: int
    active_rescues_count: int = 0
    pending_rescues_count: int = 0
    meals_donated: float
    meals_rescued: float
    meals_distributed: float
    estimated_waste_diverted_kg: float
    estimated_value_preserved_inr: float
    partner_ngos_count: int
    recognition_level: str
    completion_rate_percent: float
    rescue_success_rate_percent: float = 98.0
    conversion_factor_note: str
    monthly_breakdown: List[DonorMonthlyImpactItem]

# Distribution Schemas
class DonationDistributionRequest(BaseModel):
    distributed_quantity: Optional[float] = None
    received_quantity: Optional[float] = None
    remaining_quantity: Optional[float] = None
    beneficiaries_served: Optional[int] = None
    beneficiary_count: Optional[int] = None  # Backward compatibility alias
    remarks: Optional[str] = None
    beneficiary_notes: Optional[str] = None  # Backward compatibility alias
    distribution_timestamp: Optional[datetime] = None

class DonationDistributionResponse(BaseModel):
    donation_id: int
    received_quantity: float
    distributed_quantity: float
    remaining_quantity: float
    distribution_timestamp: Optional[datetime] = None
    distribution_status: str = "distributed"
    beneficiaries_served: int
    remarks: Optional[str] = None

# Dispute & Issue Reporting Schemas
class DisputeCreateRequest(BaseModel):
    donation_id: int
    issue_type: str # food_condition_mismatch, volunteer_no_show, donor_unavailable, ngo_unavailable, other
    description: str

class DisputeResolveRequest(BaseModel):
    status: str # resolved, dismissed
    admin_notes: Optional[str] = None
    trust_score_penalty: Optional[float] = 0.0

class DisputeResponse(BaseModel):
    id: int
    donation_id: int
    reporter_id: int
    role: str
    issue_type: str
    description: str
    status: str
    admin_notes: Optional[str] = None
    resolved_by: Optional[int] = None
    trust_score_penalty: Optional[float] = 0.0
    created_at: datetime
    resolved_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

# Comprehensive Metrics Summary Schema
class DonationMetricsSummary(BaseModel):
    meals_donated: float # Total meals created in system
    meals_rescued: float # Total meals delivered/completed
    meals_distributed: float # Total meals recorded as served to beneficiaries
    total_donations_count: int
    completed_rescues_count: int
    estimated_disposal_cost_avoided_inr: float

# Admin Operational Intervention Schemas
class AdminInterventionItem(BaseModel):
    donation_id: int
    food_name: str
    food_category: str
    quantity: float
    quantity_unit: str
    status: str
    is_emergency: bool
    intervention_type: str # URGENT_NO_NGO, URGENT_NO_VOLUNTEER, NGO_TIMEOUT, VOLUNTEER_TIMEOUT, PICKUP_FAILED, DELIVERY_FAILED, DEADLINE_APPROACHING
    reason: str
    time_remaining_hours: float
    food_at_risk_meals: float
    suggested_action: str
    created_at: datetime
    pickup_area: Optional[str] = None

class AdminInterventionsResponse(BaseModel):
    total_interventions_needed: int
    total_food_at_risk_meals: float
    urgent_count: int
    items: List[AdminInterventionItem]

# ── Rescue Feedback Schemas ──────────────────────────────────────────────────
class RescueFeedbackCreate(BaseModel):
    overall_rating: int = Field(ge=1, le=5, description="Overall experience rating 1-5")
    # Donor dimensions
    pickup_timeliness: Optional[str] = None  # on_time, slight_delay, late
    handover_experience: Optional[str] = None  # smooth, acceptable, difficult
    communication_quality: Optional[str] = None  # clear, acceptable, poor
    app_experience: Optional[str] = None  # helpful, acceptable, needs_improvement
    # NGO dimensions
    food_condition_rating: Optional[str] = None  # good, acceptable, poor
    quantity_accuracy: Optional[str] = None  # accurate, minor_diff, major_diff
    packaging_quality: Optional[str] = None  # good, damaged
    volunteer_punctuality: Optional[str] = None  # on_time, slightly_late, very_late
    volunteer_professionalism: Optional[str] = None  # professional, acceptable, unprofessional
    # Volunteer dimensions
    donor_readiness: Optional[str] = None  # ready, partially_ready, not_ready
    pickup_location_clarity: Optional[str] = None  # easy_to_find, some_difficulty, hard_to_find
    packaging_readiness: Optional[str] = None  # well_packaged, partially_prepared, poorly_packaged
    ngo_receiving_readiness: Optional[str] = None  # ready_to_receive, minor_wait, unprepared
    comment: Optional[str] = Field(default=None, max_length=500)

class RescueFeedbackResponse(BaseModel):
    id: int
    donation_id: int
    author_id: int
    author_role: str
    author_name: Optional[str] = None
    target_user_id: Optional[int] = None
    target_ngo_id: Optional[int] = None
    overall_rating: int
    pickup_timeliness: Optional[str] = None
    handover_experience: Optional[str] = None
    communication_quality: Optional[str] = None
    app_experience: Optional[str] = None
    food_condition_rating: Optional[str] = None
    quantity_accuracy: Optional[str] = None
    packaging_quality: Optional[str] = None
    volunteer_punctuality: Optional[str] = None
    volunteer_professionalism: Optional[str] = None
    donor_readiness: Optional[str] = None
    pickup_location_clarity: Optional[str] = None
    packaging_readiness: Optional[str] = None
    ngo_receiving_readiness: Optional[str] = None
    comment: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

# ── Rescue Issue Report Schemas ──────────────────────────────────────────────
class RescueIssueReportCreate(BaseModel):
    category: str = Field(..., description="Issue category: pickup_not_happened, volunteer_no_show, volunteer_late, donor_unavailable, ngo_unavailable, quantity_mismatch, packaging_damaged, food_condition_concern, location_issue, communication_issue, otp_issue, delivery_issue, distribution_issue, other")
    description: str = Field(..., min_length=3, max_length=1000)
    is_food_safety_incident: bool = False
    food_safety_details: Optional[str] = None  # spoilage, damaged_packaging, unexpected_temperature, contamination_concern, other
    evidence_url: Optional[str] = None

class RescueIssueResolveRequest(BaseModel):
    status: str = Field(..., description="RESOLVED or DISMISSED")
    admin_notes: Optional[str] = Field(default=None, max_length=1000)
    reliability_penalty: Optional[float] = Field(default=0.0, ge=0.0, le=20.0)

class RescueIssueReportResponse(BaseModel):
    id: int
    donation_id: int
    food_name: Optional[str] = None
    reporter_id: int
    reporter_name: Optional[str] = None
    reporter_role: str
    reported_user_id: Optional[int] = None
    reported_user_name: Optional[str] = None
    reported_ngo_id: Optional[int] = None
    reported_ngo_name: Optional[str] = None
    category: str
    severity: str  # LOW, MEDIUM, HIGH, CRITICAL
    is_food_safety_incident: bool
    food_safety_details: Optional[str] = None
    description: str
    evidence_url: Optional[str] = None
    status: str  # OPEN, UNDER_REVIEW, ACTION_REQUIRED, RESOLVED, DISMISSED
    admin_notes: Optional[str] = None
    resolved_by: Optional[int] = None
    resolver_name: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    reporter_history_count: Optional[int] = 0

    model_config = ConfigDict(from_attributes=True)

# ── Participant Reliability & Trust Schemas ──────────────────────────────────
class ReliabilityDimension(BaseModel):
    name: str
    score: float
    weight: float
    description: str

class ParticipantReliabilityResponse(BaseModel):
    user_id: int
    name: str
    role: str
    total_completed_rescues: int
    total_accepted_rescues: int
    cancellations_count: int
    no_shows_count: int
    on_time_rate_percent: float
    completion_rate_percent: float
    average_service_rating: float
    overall_reliability_score: float  # 0.0 to 100.0
    trust_tier: str  # New Participant, Verified Partner, Highly Reliable, Needs Review
    trust_badges: List[str]
    has_sufficient_history: bool
    sample_size_threshold: int = 3
    recency_window_rescues: int = 10
    dimensions: List[ReliabilityDimension]

# ── Admin Feedback & Issues Dashboard Schemas ────────────────────────────────
class AdminFeedbackOverviewResponse(BaseModel):
    total_feedback_count: int
    average_experience_rating: float
    open_issues_count: int
    critical_issues_count: int
    high_severity_count: int
    volunteer_reliability_alerts_count: int
    ngo_reliability_alerts_count: int
    donor_readiness_alerts_count: int
    recent_issues: List[RescueIssueReportResponse]

# ── Operational Performance & Matching Optimization Schemas ───────────────────
class RawOperationalMetrics(BaseModel):
    total_tasks_assigned: int
    total_tasks_accepted: int
    total_completed: int
    total_cancelled: int
    total_no_shows: int
    total_on_time: int
    total_delayed: int
    total_feedbacks_received: int
    average_response_time_seconds: float

class DerivedReliabilityMetrics(BaseModel):
    completion_rate_percent: float
    on_time_rate_percent: float
    cancellation_rate_percent: float
    no_show_rate_percent: float
    service_quality_score_percent: float
    response_speed_score_percent: float

class MatchReasonItem(BaseModel):
    code: str
    label: str
    is_positive: bool = True
    detail: Optional[str] = None

class PerformanceProfileResponse(BaseModel):
    user_id: int
    name: str
    role: str
    performance_status: str  # NEW, LIMITED_HISTORY, ESTABLISHED, RELIABLE, NEEDS_REVIEW
    admin_action_status: str  # NORMAL, MONITORED, DEPRIORITIZED, CONFIRMATION_REQUIRED, RESTRICTED
    admin_action_notes: Optional[str] = None
    overall_reliability_score: float
    trust_tier: str
    trust_badges: List[str]
    recent_trend: str  # improving, steady, declining, new
    trend_description: str
    raw_metrics: RawOperationalMetrics
    derived_metrics: DerivedReliabilityMetrics
    dimensions: List[ReliabilityDimension]
    sample_size_threshold: int = 3
    recency_window_size: int = 10
    has_sufficient_history: bool

class AdminPerformanceOverviewResponse(BaseModel):
    total_active_volunteers: int
    total_verified_ngos: int
    average_pickup_time_minutes: float
    average_volunteer_response_time_seconds: float
    volunteer_acceptance_rate_percent: float
    network_on_time_rate_percent: float
    network_completion_rate_percent: float
    overall_rescue_success_rate_percent: float
    fallback_escalation_rate_percent: float
    needs_review_count: int
    critical_alerts_count: int

class FailureReasonStat(BaseModel):
    reason_code: str
    reason_label: str
    count: int
    percentage: float
    trend: str  # increasing, decreasing, stable

class RescueFailureAnalyticsResponse(BaseModel):
    total_rescue_attempts: int
    total_completed_rescues: int
    total_failed_or_cancelled: int
    rescue_success_rate_percent: float
    failure_reasons: List[FailureReasonStat]
    period: str = "all_time"

class NeedsReviewParticipantResponse(BaseModel):
    user_id: int
    name: str
    role: str
    performance_status: str
    admin_action_status: str
    overall_reliability_score: float
    trigger_reason: str
    no_show_rate_percent: float
    completion_rate_percent: float
    cancellation_rate_percent: float
    critical_issues_count: int
    total_completed: int
    total_assigned: int
    admin_notes: Optional[str] = None
    last_active_at: Optional[datetime] = None

class SuspiciousFeedbackAlertResponse(BaseModel):
    feedback_id: int
    donation_id: int
    author_id: int
    author_name: str
    author_role: str
    target_user_id: Optional[int] = None
    target_name: Optional[str] = None
    rating: int
    comment: Optional[str] = None
    suspicion_reason: str  # repetitive_comment, rating_burst, retaliatory_pattern, identical_score_cluster
    severity: str
    created_at: datetime

class AdminPerformanceActionRequest(BaseModel):
    action: str = Field(..., description="MONITOR, CONTACT, TEMPORARILY_DEPRIORITIZE, REQUIRE_CONFIRMATION, DISABLE_AVAILABILITY, RESTORE")
    notes: Optional[str] = Field(default=None, max_length=1000)
    deprioritize_factor: Optional[float] = Field(default=0.7, ge=0.1, le=1.0)

class AdminPerformanceActionResponse(BaseModel):
    user_id: int
    action_taken: str
    admin_action_status: str
    message: str
    audit_log_id: Optional[int] = None

# ── Admin Food Rescue Control Center Schemas ─────────────────────────────────

class AdminReceivingSummaryResponse(BaseModel):
    active_rescues: int
    urgent_rescues: int
    critical_rescues: int
    in_transit: int
    received_today: float
    distributed_today: float
    remaining_today: float
    issues_open: int
    food_at_risk_meals: float
    completed_today: int

class AdminReceivingItemResponse(BaseModel):
    id: int
    food_name: str
    food_category: str
    quantity: float
    quantity_unit: str
    donor_id: int
    donor_name: Optional[str] = None
    donor_phone: Optional[str] = None
    assigned_ngo_id: Optional[int] = None
    ngo_name: Optional[str] = None
    assigned_volunteer_id: Optional[int] = None
    volunteer_name: Optional[str] = None
    volunteer_phone: Optional[str] = None
    status: str
    rescue_urgency_level: str
    remaining_minutes: Optional[int] = None
    ai_visual_condition: Optional[str] = "GOOD"
    storage_method: Optional[str] = None
    packaging_condition: Optional[str] = None
    eta_minutes: Optional[float] = None
    expected_quantity: float
    received_quantity: Optional[float] = None
    has_quantity_mismatch: bool = False
    discrepancy_amount: Optional[float] = None
    discrepancy_reason: Optional[str] = None
    distributed_quantity: Optional[float] = None
    remaining_quantity: Optional[float] = None
    issue_count: int = 0
    pickup_address: str
    created_at: datetime
    accepted_at: Optional[datetime] = None
    collected_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class AdminReceivingListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[AdminReceivingItemResponse]

class AdminRescueAuditTimelineItem(BaseModel):
    stage: str
    label: str
    timestamp: Optional[datetime] = None
    is_completed: bool
    is_current: bool
    actor_name: Optional[str] = None
    details: Optional[str] = None

class AdminRescueDetailResponse(AdminReceivingItemResponse):
    timeline: List[AdminRescueAuditTimelineItem] = []
    ngo_capacity_available: Optional[bool] = True
    ngo_current_capacity: Optional[float] = None
    ngo_max_capacity: Optional[float] = None
    recent_issues: List[RescueIssueReportResponse] = []

class AdminInterventionCreate(BaseModel):
    donation_id: int
    reason_code: str = Field(..., description="no_volunteer_available, ngo_unavailable, pickup_delayed, delivery_delayed, food_condition_concern, quantity_mismatch, transport_failure, other")
    notes: Optional[str] = Field(default=None, max_length=1000)
    action_type: Optional[str] = "INTERVENTION_RECORDED"
    target_status: Optional[str] = Field(default=None, description="Optional target status for donation state transition")

class AdminInterventionActionResponse(BaseModel):
    success: bool
    donation_id: int
    message: str
    audit_log_id: Optional[int] = None

class NGOCapacityItemResponse(BaseModel):
    id: int
    organization_name: str
    address: str
    current_capacity: float
    max_capacity: float
    remaining_capacity: float
    utilization_percent: float
    is_verified: bool
    is_open: bool
    status_color: str  # GREEN, AMBER, RED

class AdminCategoryBreakdownItem(BaseModel):
    category: str
    count: int
    total_meals: float
    percentage: float

class AdminCategoryBreakdownResponse(BaseModel):
    total_meals: float
    categories: List[AdminCategoryBreakdownItem]


# ─── Frictionless First-Time Volunteer Claim Schemas ─────────────────────────

class RescueClaimTokenResponse(BaseModel):
    claim_token: str
    claim_url: str
    donation_id: int
    expires_at: datetime
    remaining_minutes: int
    urgency_level: str

    model_config = ConfigDict(from_attributes=True)


class RescueClaimPreviewResponse(BaseModel):
    claim_token: str
    donation_id: int
    food_name: str
    food_category: str
    quantity: float
    quantity_unit: str
    pickup_neighborhood: str
    approx_latitude: Optional[float] = None
    approx_longitude: Optional[float] = None
    remaining_minutes: int
    urgency_level: str
    is_feasible: bool
    expires_at: datetime
    status: str
    dietary_type: Optional[str] = None


class RescueClaimAcceptRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    phone: str = Field(..., min_length=7, max_length=20)
    vehicle_type: Optional[str] = "bike"
    carrying_capacity: Optional[int] = 50
    current_lat: Optional[float] = None
    current_lon: Optional[float] = None


class RescueClaimAcceptResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
    assignment_id: int
    donation_id: int
    status: str
    pickup_address: str
    current_eta_minutes: Optional[float] = None
    remaining_minutes: int
    urgency_level: str
    message: str


class VolunteerAccountUpgradeRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)
    preferred_language: Optional[str] = "en"





