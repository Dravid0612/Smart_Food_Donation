from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, Enum, Index
)
from sqlalchemy.orm import relationship
from app.db.base import Base

def utcnow():
    return datetime.now(timezone.utc)

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    phone = Column(String(50), nullable=True)
    phone_verified = Column(Boolean, default=False)  # True only after OTP-verified
    phone_country_code = Column(String(10), nullable=True, default="+91")  # e.g. "+91"
    phone_normalized = Column(String(20), nullable=True)  # E.164 e.g. +919876543210
    role = Column(String(50), nullable=False, default="donor") # donor, ngo, volunteer, admin
    address = Column(Text, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    profile_image = Column(Text, nullable=True)
    preferred_language = Column(String(10), default="en") # en, ta, hi
    
    # Donor & Volunteer trust & CSR metrics
    donor_trust_score = Column(Float, default=98.0)
    is_verified_donor = Column(Boolean, default=True)
    total_meals_donated = Column(Float, default=0.0)
    
    # Volunteer logistics attributes
    vehicle_type = Column(String(50), nullable=True, default="bike") # walking, bike, car, van
    carrying_capacity = Column(Integer, default=50) # max meals capacity
    reliability_score = Column(Float, default=95.0) # success rate %
    completed_deliveries = Column(Integer, default=0)
    failed_deliveries = Column(Integer, default=0)

    # Operational Performance & Admin Management
    performance_status = Column(String(50), default="ESTABLISHED") # NEW, LIMITED_HISTORY, ESTABLISHED, RELIABLE, NEEDS_REVIEW
    admin_action_status = Column(String(50), default="NORMAL") # NORMAL, MONITORED, DEPRIORITIZED, CONFIRMATION_REQUIRED, RESTRICTED
    admin_action_notes = Column(Text, nullable=True)
    avg_response_time_seconds = Column(Float, nullable=True, default=180.0)

    is_active = Column(Boolean, default=True)
    refresh_token_hash = Column(String(255), nullable=True)  # Hashed refresh token for revocation
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    # Relationships
    ngo_profile = relationship("NGO", back_populates="user", uselist=False, cascade="all, delete-orphan")
    donations = relationship("FoodDonation", foreign_keys="FoodDonation.donor_id", back_populates="donor")
    volunteer_assignments = relationship("VolunteerAssignment", back_populates="volunteer")
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")
    reward = relationship("Reward", back_populates="user", uselist=False, cascade="all, delete-orphan")
    recurring_donations = relationship("RecurringDonation", back_populates="donor", cascade="all, delete-orphan")
    kitchen_profiles = relationship("KitchenProfile", back_populates="donor", cascade="all, delete-orphan")
    given_ratings = relationship("Rating", foreign_keys="Rating.from_user_id", back_populates="from_user")
    received_ratings = relationship("Rating", foreign_keys="Rating.to_user_id", back_populates="to_user")
    submitted_feedbacks = relationship("RescueFeedback", foreign_keys="RescueFeedback.author_id", back_populates="author", cascade="all, delete-orphan")
    reported_issues = relationship("RescueIssueReport", foreign_keys="RescueIssueReport.reporter_id", back_populates="reporter", cascade="all, delete-orphan")
    otp_records = relationship("PickupOtpRecord", foreign_keys="PickupOtpRecord.donor_id", back_populates="donor", cascade="all, delete-orphan")
    notification_preference = relationship("NotificationPreference", back_populates="user", uselist=False, cascade="all, delete-orphan")

class NGO(Base):
    __tablename__ = "ngos"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    organization_name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    address = Column(Text, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    capacity = Column(Integer, default=100) # total meals capacity
    current_capacity = Column(Integer, default=100) # remaining capacity
    is_available = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    contact_phone = Column(String(50), nullable=True)
    trust_score = Column(Float, default=96.0) # NGO reliability score %
    total_distributed_meals = Column(Float, default=0.0)
    
    # Operating hours & dynamic beneficiary demand (JSON string or serialized dict)
    # e.g. {"monday": {"open": "08:00", "close": "20:00", "closed": false}, ...}
    operating_hours = Column(Text, nullable=True)
    # e.g. {"Cooked Food": 80, "Bakery": 20, "Fruits": 30, "Packaged Food": 50}
    demand_requirements = Column(Text, nullable=True)

    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    # Operational Performance & Admin Management
    performance_status = Column(String(50), default="ESTABLISHED") # NEW, LIMITED_HISTORY, ESTABLISHED, RELIABLE, NEEDS_REVIEW
    admin_action_status = Column(String(50), default="NORMAL") # NORMAL, MONITORED, DEPRIORITIZED, CONFIRMATION_REQUIRED, RESTRICTED
    admin_action_notes = Column(Text, nullable=True)

    # Relationships
    user = relationship("User", back_populates="ngo_profile")
    accepted_donations = relationship("FoodDonation", foreign_keys="FoodDonation.assigned_ngo_id", back_populates="assigned_ngo")

class FoodDonation(Base):
    __tablename__ = "food_donations"
    __table_args__ = (
        Index("ix_donations_status_created", "status", "created_at"),
        Index("ix_donations_donor_created", "donor_id", "created_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    donor_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    food_name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    food_category = Column(String(100), nullable=False) # Cooked Food, Bakery, Fruits, Vegetables, Packaged Food, Other
    quantity = Column(Float, nullable=False)
    quantity_unit = Column(String(50), nullable=False, default="Meals") # Meals, Kg, Litres, Packets
    preparation_time = Column(DateTime, nullable=False)
    expiry_time = Column(DateTime, nullable=False)
    pickup_address = Column(Text, nullable=False)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    image_url = Column(Text, nullable=True)

    # Donor metadata
    food_type = Column(String(100), nullable=True) # e.g. Idli, Biryani, Chapati, Rice
    food_source = Column(String(50), default="KNOWN") # "KNOWN" vs "CUSTOM"
    custom_food_name = Column(String(255), nullable=True) # User-entered custom food name (e.g. Pongal, Kurma, Samosa)
    food_description = Column(Text, nullable=True) # Additional description for custom food
    major_ingredients = Column(Text, nullable=True) # e.g. "rice, lentils, spices, dairy"
    quantity_unit_label = Column(String(100), nullable=True) # Optional label for custom units (e.g. "large containers")
    estimated_meals = Column(Float, nullable=True) # Calculated approximate equivalent meals
    rule_coverage = Column(String(50), default="HIGH") # "HIGH" (known profile), "MEDIUM" (category match), "LOW" (unspecified)
    classification_source = Column(String(50), default="rule_exact") # "rule_exact", "donor_specified", "ai_assisted", "generic_category"
    classification_confidence = Column(Float, default=1.0)
    storage_method = Column(String(100), nullable=True, default="Room Temperature") # Refrigerated, Room Temperature, Heated/Insulated, Frozen
    storage_duration_hours = Column(Float, nullable=True, default=2.0)
    storage_continuous = Column(Boolean, default=True) # Continuous single storage mode vs mixed
    storage_history_json = Column(Text, nullable=True) # Structured history transitions
    packaging_condition = Column(String(100), nullable=True, default="Sealed / Covered") # Sealed, Covered, Partially Covered, Open, Unknown
    previously_served = Column(String(20), nullable=True, default="No") # Yes, No, Unknown
    exposure_status = Column(String(20), nullable=True, default="No") # Yes, No, Unknown
    handling_status = Column(String(20), nullable=True, default="No") # Yes, No, Unknown
    pickup_deadline = Column(DateTime, nullable=True)

    # Time-Aware Food Rescue Window & Feasibility
    estimated_window_start = Column(DateTime, nullable=True)
    estimated_window_end = Column(DateTime, nullable=True)
    remaining_minutes = Column(Integer, nullable=True)
    rescue_urgency_level = Column(String(50), nullable=True, default="FRESH") # FRESH, APPROACHING, URGENT, CRITICAL
    feasibility_status = Column(String(50), nullable=True, default="RESCUE_FEASIBLE") # RESCUE_FEASIBLE, AT_RISK, RESCUE_UNLIKELY
    reasons_json = Column(Text, nullable=True)

    # AI Vision & Decision Assessment
    ai_food_detected = Column(String(255), nullable=True)
    ai_visible_spoilage = Column(String(100), nullable=True) # Not detected, Minor signs, Visible signs
    ai_discoloration = Column(String(100), nullable=True) # Normal, Slight variation, Abnormal
    ai_packaging_intact = Column(String(100), nullable=True) # Intact, Exposed, Damaged
    ai_visual_condition = Column(String(50), nullable=True, default="GOOD") # GOOD, FAIR, POOR, UNCERTAIN
    ai_confidence_score = Column(Float, nullable=True, default=0.88)
    ai_safety_disclaimer = Column(Text, nullable=True, default="Image analysis cannot guarantee food safety. Visual assessment only. Microbiological safety cannot be determined from visual characteristics alone.")
    condition_score = Column(Integer, nullable=True, default=85)

    # Verification OTP & QR token — with expiry and single-use replay protection
    verification_otp = Column(String(10), nullable=True)
    otp_expiry = Column(DateTime, nullable=True)       # OTP valid until this timestamp
    otp_used_at = Column(DateTime, nullable=True)      # Set when OTP is consumed (replay guard)
    qr_code_token = Column(String(255), nullable=True)
    qr_expiry = Column(DateTime, nullable=True)        # QR valid until this timestamp
    qr_used_at = Column(DateTime, nullable=True)       # Set when QR is consumed (replay guard)

    # Impact & Distribution metrics
    cost_avoided_inr = Column(Float, default=0.0) # Estimated waste disposal cost avoided in INR
    beneficiaries_served = Column(Integer, default=0)
    received_quantity = Column(Float, nullable=True)
    distributed_quantity = Column(Float, nullable=True)
    remaining_quantity = Column(Float, nullable=True)
    distribution_timestamp = Column(DateTime, nullable=True)
    distribution_remarks = Column(Text, nullable=True)

    # Status & Emergency Lifecycle
    status = Column(String(50), nullable=False, default="pending") # pending, accepted, volunteer_assigned, collected, delivered, completed, cancelled, pickup_failed, delivery_failed, expired
    failure_reason = Column(String(255), nullable=True)
    is_emergency = Column(Boolean, default=False)
    escalated_at = Column(DateTime, nullable=True)

    # Proactive Time-Critical Dispatch & Alert Wave Tracking
    last_alerted_urgency = Column(String(50), nullable=True)
    last_alerted_at = Column(DateTime, nullable=True)
    current_alert_wave = Column(Integer, default=0)
    wave_timeout_at = Column(DateTime, nullable=True)
    alert_history_json = Column(Text, nullable=True)

    # Real-Time Rescue Tracking
    tracking_latitude = Column(Float, nullable=True)
    tracking_longitude = Column(Float, nullable=True)
    tracking_last_updated_at = Column(DateTime, nullable=True)
    current_eta_minutes = Column(Float, nullable=True)
    current_distance_km = Column(Float, nullable=True)
    tracking_status = Column(String(50), default="IDLE") # IDLE, EN_ROUTE, NEARBY, ARRIVED_AT_DONOR, IN_TRANSIT, ARRIVED_AT_NGO, COMPLETED

    # Dynamic Rematching & Reassignment Audit
    rematch_count = Column(Integer, default=0)
    rematch_reason = Column(Text, nullable=True)
    is_rematched = Column(Boolean, default=False)
    last_feasibility_check_at = Column(DateTime, nullable=True)
    previous_volunteer_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Food-Safety Self-Check Screening Declaration
    safety_check_completed = Column(Boolean, default=False)
    safety_check_answers_json = Column(Text, nullable=True)
    safety_check_status = Column(String(50), default="PASSED") # PASSED, FAILED, EXEMPT
    safety_check_version = Column(String(50), default="2026.1")

    assigned_ngo_id = Column(Integer, ForeignKey("ngos.id", ondelete="SET NULL"), nullable=True)
    assigned_volunteer_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    # Relationships
    donor = relationship("User", foreign_keys=[donor_id], back_populates="donations")
    assigned_ngo = relationship("NGO", foreign_keys=[assigned_ngo_id], back_populates="accepted_donations")
    assigned_volunteer = relationship("User", foreign_keys=[assigned_volunteer_id])
    previous_volunteer = relationship("User", foreign_keys=[previous_volunteer_id])
    history = relationship("DonationHistory", back_populates="donation", cascade="all, delete-orphan")
    assignments = relationship("VolunteerAssignment", back_populates="donation", cascade="all, delete-orphan")
    offers = relationship("MatchOffer", back_populates="donation", cascade="all, delete-orphan")
    ratings = relationship("Rating", back_populates="donation", cascade="all, delete-orphan")
    feedbacks = relationship("RescueFeedback", back_populates="donation", cascade="all, delete-orphan")
    issue_reports = relationship("RescueIssueReport", back_populates="donation", cascade="all, delete-orphan")
    food_analysis = relationship("FoodAnalysis", back_populates="donation", uselist=False, cascade="all, delete-orphan")
    disputes = relationship("Dispute", back_populates="donation", cascade="all, delete-orphan")

class RecurringDonation(Base):
    __tablename__ = "recurring_donations"

    id = Column(Integer, primary_key=True, index=True)
    donor_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    template_name = Column(String(255), nullable=False) # e.g. "Dinner Buffet Surplus", "Daily Lunch Service"
    food_name = Column(String(255), nullable=False)
    food_category = Column(String(100), nullable=False)
    typical_quantity = Column(Float, nullable=False, default=50.0)
    quantity_unit = Column(String(50), default="Meals")
    frequency = Column(String(50), default="Daily") # Daily, Weekdays, Weekly, Custom
    preferred_pickup_time = Column(String(50), default="20:30") # e.g. "20:30"
    pickup_address = Column(Text, nullable=False)
    storage_method = Column(String(100), default="Heated/Insulated")
    packaging_condition = Column(String(100), default="Sealed / Covered")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    # Relationships
    donor = relationship("User", back_populates="recurring_donations")

class KitchenProfile(Base):
    __tablename__ = "kitchen_profiles"

    id = Column(Integer, primary_key=True, index=True)
    donor_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)  # e.g. "Main Kitchen", "Terrace Banquet"
    location_address = Column(Text, nullable=False)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    typical_food_types = Column(Text, nullable=True)  # JSON or comma-separated
    default_storage_method = Column(String(100), default="Refrigerated")
    contact_person = Column(String(100), nullable=True)
    contact_phone = Column(String(50), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    # Relationships
    donor = relationship("User", back_populates="kitchen_profiles")

class MatchOffer(Base):
    __tablename__ = "match_offers"

    id = Column(Integer, primary_key=True, index=True)
    donation_id = Column(Integer, ForeignKey("food_donations.id", ondelete="CASCADE"), nullable=False)
    candidate_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    candidate_type = Column(String(50), nullable=False) # "ngo" or "volunteer"
    score = Column(Float, nullable=False, default=90.0)
    status = Column(String(50), nullable=False, default="offered") # offered, accepted, rejected, expired, cancelled
    wave_number = Column(Integer, default=1)
    offered_at = Column(DateTime, default=utcnow)
    expires_at = Column(DateTime, nullable=True)
    first_viewed_at = Column(DateTime, nullable=True)
    responded_at = Column(DateTime, nullable=True)
    response_time_seconds = Column(Float, nullable=True)

    # Relationships
    donation = relationship("FoodDonation", back_populates="offers")
    candidate = relationship("User")

class Rating(Base):
    __tablename__ = "ratings"

    id = Column(Integer, primary_key=True, index=True)
    donation_id = Column(Integer, ForeignKey("food_donations.id", ondelete="CASCADE"), nullable=False)
    from_user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    to_user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role_from = Column(String(50), nullable=False) # donor, ngo, volunteer
    role_to = Column(String(50), nullable=False) # donor, ngo, volunteer
    rating_score = Column(Integer, nullable=False) # 1 to 5 stars
    feedback = Column(Text, nullable=True)
    tags = Column(String(255), nullable=True) # "On time", "Excellent packaging", "Quick handover"
    created_at = Column(DateTime, default=utcnow)

    # Relationships
    donation = relationship("FoodDonation", back_populates="ratings")
    from_user = relationship("User", foreign_keys=[from_user_id], back_populates="given_ratings")
    to_user = relationship("User", foreign_keys=[to_user_id], back_populates="received_ratings")

class DonationHistory(Base):
    __tablename__ = "donation_history"

    id = Column(Integer, primary_key=True, index=True)
    donation_id = Column(Integer, ForeignKey("food_donations.id", ondelete="CASCADE"), nullable=False)
    old_status = Column(String(50), nullable=True)
    new_status = Column(String(50), nullable=False)
    changed_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    remarks = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utcnow)

    # Relationships
    donation = relationship("FoodDonation", back_populates="history")
    user = relationship("User", foreign_keys=[changed_by])

class VolunteerAssignment(Base):
    __tablename__ = "volunteer_assignments"
    __table_args__ = (
        Index("ix_vol_assign_vol_status", "volunteer_id", "status", "assigned_at"),
        Index("ix_vol_assign_donation", "donation_id", "status"),
    )

    id = Column(Integer, primary_key=True, index=True)
    donation_id = Column(Integer, ForeignKey("food_donations.id", ondelete="CASCADE"), nullable=False)
    volunteer_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    assigned_at = Column(DateTime, default=utcnow)
    accepted_at = Column(DateTime, nullable=True)
    collected_at = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)
    status = Column(String(50), nullable=False, default="assigned") # assigned, accepted, en_route, arrived, collected, in_transit, delivered, cancelled, reassigned, failed
    failure_reason = Column(String(255), nullable=True)

    # Real-time Location & Telemetry Tracking
    last_known_lat = Column(Float, nullable=True)
    last_known_lon = Column(Float, nullable=True)
    last_location_update = Column(DateTime, nullable=True)
    current_eta_minutes = Column(Float, nullable=True)
    current_distance_km = Column(Float, nullable=True)

    # Dynamic Rematching Reassignment fields
    is_reassigned = Column(Boolean, default=False)
    reassign_reason = Column(Text, nullable=True)
    reassigned_at = Column(DateTime, nullable=True)

    # Relationships
    donation = relationship("FoodDonation", back_populates="assignments")
    volunteer = relationship("User", back_populates="volunteer_assignments")

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    type = Column(String(50), default="info")  # info, donation, assignment, emergency, alert
    related_donation_id = Column(Integer, ForeignKey("food_donations.id", ondelete="SET NULL"), nullable=True)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=utcnow)

    # Extended fields: structured event routing, deduplication, FCM tracking
    event_type = Column(String(100), nullable=True)   # e.g. VOLUNTEER_ARRIVED, RESCUE_COMPLETED
    deep_link_data = Column(Text, nullable=True)       # Safe JSON routing payload — no OTP/JWT
    dedup_key = Column(String(255), nullable=True)     # donation_id:event_type — prevents duplicate events
    is_sent = Column(Boolean, default=False)           # FCM push attempted
    sent_at = Column(DateTime, nullable=True)          # When FCM push was sent
    opened_at = Column(DateTime, nullable=True)        # When user tapped notification

    # Relationships
    user = relationship("User", back_populates="notifications")
    related_donation = relationship("FoodDonation", foreign_keys=[related_donation_id])

class Reward(Base):
    __tablename__ = "rewards"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    points = Column(Integer, default=0)
    level = Column(String(50), default="Bronze") # Bronze, Silver, Gold, Platinum
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    # Relationships
    user = relationship("User", back_populates="reward")

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action = Column(String(100), nullable=False) # login_success, login_failed, unauthorized_access, etc.
    resource_type = Column(String(50), nullable=True) # donation, ngo, volunteer_assignment, user
    resource_id = Column(Integer, nullable=True)
    ip_address = Column(String(100), nullable=True)
    status = Column(String(50), nullable=False, default="success") # success, failed, blocked
    details = Column(Text, nullable=True) # JSON or string description (no credentials/tokens)
    created_at = Column(DateTime, default=utcnow)

    # Relationships
    user = relationship("User")

class FoodAnalysis(Base):
    __tablename__ = "food_analyses"

    id = Column(Integer, primary_key=True, index=True)
    donation_id = Column(Integer, ForeignKey("food_donations.id", ondelete="CASCADE"), nullable=True)
    food_detected = Column(String(255), nullable=True)
    visible_spoilage = Column(String(100), nullable=True, default="Not detected")
    discoloration = Column(String(100), nullable=True, default="Normal")
    packaging_integrity = Column(String(100), nullable=True, default="GOOD")
    visual_condition = Column(String(50), nullable=False, default="GOOD") # GOOD, FAIR, POOR
    confidence = Column(Float, nullable=False, default=0.87)
    observations = Column(Text, nullable=True) # JSON list of strings
    safety_disclaimer = Column(
        Text,
        nullable=False,
        default="Visual assessment only; this does not certify food safety."
    )
    storage_assessment = Column(Text, nullable=True)
    urgency_recommendation = Column(String(100), nullable=True, default="Normal Priority")
    model_version = Column(String(50), nullable=True, default="SmartDonor-Vision-v2")
    analyzed_at = Column(DateTime, default=utcnow)

    # Relationships
    donation = relationship("FoodDonation", back_populates="food_analysis")

class Dispute(Base):
    __tablename__ = "disputes"

    id = Column(Integer, primary_key=True, index=True)
    donation_id = Column(Integer, ForeignKey("food_donations.id", ondelete="CASCADE"), nullable=False)
    reporter_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(50), nullable=False) # donor, ngo, volunteer, admin
    issue_type = Column(String(100), nullable=False) # food_condition_mismatch, volunteer_no_show, donor_unavailable, ngo_unavailable, other
    description = Column(Text, nullable=False)
    status = Column(String(50), nullable=False, default="open") # open, under_review, resolved, dismissed
    admin_notes = Column(Text, nullable=True)
    resolved_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    trust_score_penalty = Column(Float, default=0.0)
    created_at = Column(DateTime, default=utcnow)
    resolved_at = Column(DateTime, nullable=True)

    # Relationships
    donation = relationship("FoodDonation", back_populates="disputes")
    reporter = relationship("User", foreign_keys=[reporter_id])
    resolver = relationship("User", foreign_keys=[resolved_by])

class DonorCustomFoodProfile(Base):
    """
    Donor Personal Food Library ('My Foods').
    Saves frequently donated custom food items for 1-click reuse without altering global food rules.
    """
    __tablename__ = "donor_custom_food_profiles"

    id = Column(Integer, primary_key=True, index=True)
    donor_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    food_category = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    major_ingredients = Column(Text, nullable=True)
    common_storage = Column(String(100), default="Room Temperature")
    default_unit = Column(String(50), default="Meals")
    usage_count = Column(Integer, default=1)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    # Relationships
    donor = relationship("User", backref="custom_food_profiles")


class RescueFeedback(Base):
    __tablename__ = "rescue_feedbacks"
    __table_args__ = (
        Index("ix_feedback_target_user_created", "target_user_id", "created_at"),
        Index("ix_feedback_target_ngo_created", "target_ngo_id", "created_at"),
        Index("ix_feedback_author_created", "author_id", "created_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    donation_id = Column(Integer, ForeignKey("food_donations.id", ondelete="CASCADE"), nullable=False, index=True)
    author_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    author_role = Column(String(50), nullable=False)  # donor, ngo, volunteer
    target_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    target_ngo_id = Column(Integer, ForeignKey("ngos.id", ondelete="SET NULL"), nullable=True)
    overall_rating = Column(Integer, nullable=False)  # 1 to 5 stars

    # Structured dimensions - Donor
    pickup_timeliness = Column(String(50), nullable=True)  # on_time, slight_delay, late
    handover_experience = Column(String(50), nullable=True)  # smooth, acceptable, difficult
    communication_quality = Column(String(50), nullable=True)  # clear, acceptable, poor
    app_experience = Column(String(50), nullable=True)  # helpful, acceptable, needs_improvement

    # Structured dimensions - NGO
    food_condition_rating = Column(String(50), nullable=True)  # good, acceptable, poor
    quantity_accuracy = Column(String(50), nullable=True)  # accurate, minor_diff, major_diff
    packaging_quality = Column(String(50), nullable=True)  # good, damaged
    volunteer_punctuality = Column(String(50), nullable=True)  # on_time, slightly_late, very_late
    volunteer_professionalism = Column(String(50), nullable=True)  # professional, acceptable, unprofessional

    # Structured dimensions - Volunteer
    donor_readiness = Column(String(50), nullable=True)  # ready, partially_ready, not_ready
    pickup_location_clarity = Column(String(50), nullable=True)  # easy_to_find, some_difficulty, hard_to_find
    packaging_readiness = Column(String(50), nullable=True)  # well_packaged, partially_prepared, poorly_packaged
    ngo_receiving_readiness = Column(String(50), nullable=True)  # ready_to_receive, minor_wait, unprepared

    comment = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    # Relationships
    donation = relationship("FoodDonation", back_populates="feedbacks")
    author = relationship("User", foreign_keys=[author_id], back_populates="submitted_feedbacks")
    target_user = relationship("User", foreign_keys=[target_user_id])
    target_ngo = relationship("NGO", foreign_keys=[target_ngo_id])


class RescueIssueReport(Base):
    __tablename__ = "rescue_issue_reports"
    __table_args__ = (
        Index("ix_issues_severity_status_created", "severity", "status", "created_at"),
        Index("ix_issues_reported_user_created", "reported_user_id", "created_at"),
        Index("ix_issues_reported_ngo_created", "reported_ngo_id", "created_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    donation_id = Column(Integer, ForeignKey("food_donations.id", ondelete="CASCADE"), nullable=False, index=True)
    reporter_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    reporter_role = Column(String(50), nullable=False)  # donor, ngo, volunteer, admin
    reported_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reported_ngo_id = Column(Integer, ForeignKey("ngos.id", ondelete="SET NULL"), nullable=True)
    category = Column(String(100), nullable=False)  # pickup_not_happened, volunteer_no_show, volunteer_late, donor_unavailable, ngo_unavailable, quantity_mismatch, packaging_damaged, food_condition_concern, location_issue, communication_issue, otp_issue, delivery_issue, distribution_issue, other
    severity = Column(String(50), nullable=False, default="LOW")  # LOW, MEDIUM, HIGH, CRITICAL
    is_food_safety_incident = Column(Boolean, default=False)
    food_safety_details = Column(Text, nullable=True)
    description = Column(Text, nullable=False)
    evidence_url = Column(Text, nullable=True)
    status = Column(String(50), nullable=False, default="OPEN")  # OPEN, UNDER_REVIEW, ACTION_REQUIRED, RESOLVED, DISMISSED
    admin_notes = Column(Text, nullable=True)
    resolved_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)
    resolved_at = Column(DateTime, nullable=True)

    # Relationships
    donation = relationship("FoodDonation", back_populates="issue_reports")
    reporter = relationship("User", foreign_keys=[reporter_id], back_populates="reported_issues")
    reported_user = relationship("User", foreign_keys=[reported_user_id])
    reported_ngo = relationship("NGO", foreign_keys=[reported_ngo_id])
    resolver = relationship("User", foreign_keys=[resolved_by])


# ─────────────────────────────────────────────────────────────────────────────
# OTP & SMS Delivery Models
# ─────────────────────────────────────────────────────────────────────────────

class PickupOtpRecord(Base):
    """
    Single authoritative OTP record per donation per purpose.
    Stores only a SHA-256 hash — never the plaintext OTP.
    Plaintext is returned once in the API response for the donor and SMS channel only.
    """
    __tablename__ = "pickup_otp_records"
    __table_args__ = (
        Index("ix_otp_donation_purpose_active", "donation_id", "purpose", "is_active"),
    )

    id = Column(Integer, primary_key=True, index=True)
    donation_id = Column(Integer, ForeignKey("food_donations.id", ondelete="CASCADE"), nullable=False, index=True)
    donor_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    volunteer_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    purpose = Column(String(50), nullable=False, default="PICKUP_VERIFICATION_OTP")
    # Purpose enum: PICKUP_VERIFICATION_OTP | PHONE_VERIFICATION_OTP
    otp_hash = Column(String(64), nullable=False)   # SHA-256 hex digest — NEVER plaintext
    created_at = Column(DateTime, default=utcnow)
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime, nullable=True)        # Set on verified use — replay guard
    is_active = Column(Boolean, default=True)        # False after regeneration or expiry
    delivery_status = Column(String(50), default="QUEUED")
    # Delivery status: QUEUED | SENT | DELIVERED | FAILED | EXPIRED | UNKNOWN
    provider_message_id = Column(String(255), nullable=True)  # SMS provider reference ID

    # Relationships
    donation = relationship("FoodDonation", foreign_keys=[donation_id])
    donor = relationship("User", foreign_keys=[donor_id], back_populates="otp_records")
    volunteer = relationship("User", foreign_keys=[volunteer_id])
    delivery_records = relationship("OtpDeliveryRecord", back_populates="otp_record", cascade="all, delete-orphan")


class OtpDeliveryRecord(Base):
    """
    Tracks each individual SMS send attempt and provider delivery status updates.
    Only backend/webhook may update status — never client-side.
    Never stores plaintext OTP.
    """
    __tablename__ = "otp_delivery_records"

    id = Column(Integer, primary_key=True, index=True)
    otp_record_id = Column(Integer, ForeignKey("pickup_otp_records.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    donation_id = Column(Integer, ForeignKey("food_donations.id", ondelete="SET NULL"), nullable=True)
    purpose = Column(String(50), nullable=False)
    phone_number_masked = Column(String(20), nullable=False)  # e.g. ****3210 — NEVER full number
    provider = Column(String(50), nullable=False, default="mock")  # mock | twilio | msg91 | exotel
    provider_message_id = Column(String(255), nullable=True)
    status = Column(String(50), nullable=False, default="QUEUED")
    # QUEUED | SENT | DELIVERED | FAILED | EXPIRED | UNKNOWN
    created_at = Column(DateTime, default=utcnow)
    sent_at = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)
    failed_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    failure_reason = Column(String(255), nullable=True)
    provider_payload_json = Column(Text, nullable=True)  # Raw webhook payload reference

    # Relationships
    otp_record = relationship("PickupOtpRecord", back_populates="delivery_records")
    user = relationship("User", foreign_keys=[user_id])


class NotificationPreference(Base):
    """Per-user notification preference settings and FCM device token."""
    __tablename__ = "notification_preferences"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    operational_notifications = Column(Boolean, default=True)   # Rescue lifecycle events
    urgent_rescue_alerts = Column(Boolean, default=True)         # Cannot be disabled for critical events
    impact_updates = Column(Boolean, default=True)               # Distribution, completion events
    feedback_reminders = Column(Boolean, default=True)           # Post-rescue feedback prompt
    fcm_token = Column(String(512), nullable=True)               # Firebase Cloud Messaging device token
    fcm_token_updated_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    # Relationships
    user = relationship("User", back_populates="notification_preference")
