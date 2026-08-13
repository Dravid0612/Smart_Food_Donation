from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime

# Token Schemas
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    role: str
    name: str
    email: str

class TokenData(BaseModel):
    user_id: Optional[int] = None
    role: Optional[str] = None

# User Schemas
class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    phone: Optional[str] = None
    role: str = "donor" # donor, ngo, volunteer
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    organization_name: Optional[str] = None # Optional if registering as NGO
    description: Optional[str] = None # NGO description
    capacity: Optional[int] = 100 # NGO capacity

class UserLogin(BaseModel):
    email: EmailStr
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
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

# NGO Schemas
class NGOCreate(BaseModel):
    organization_name: str
    description: Optional[str] = None
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    capacity: int = 100
    contact_phone: Optional[str] = None

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

    class Config:
        from_attributes = True

# Food Donation Schemas
class DonationCreate(BaseModel):
    food_name: str
    description: Optional[str] = None
    food_category: str
    quantity: float
    quantity_unit: str = "Meals"
    preparation_time: datetime
    expiry_time: datetime
    pickup_address: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    image_url: Optional[str] = None

class DonationUpdate(BaseModel):
    food_name: Optional[str] = None
    description: Optional[str] = None
    food_category: Optional[str] = None
    quantity: Optional[float] = None
    quantity_unit: Optional[str] = None
    preparation_time: Optional[datetime] = None
    expiry_time: Optional[datetime] = None
    pickup_address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    image_url: Optional[str] = None

class DonationHistoryResponse(BaseModel):
    id: int
    donation_id: int
    old_status: Optional[str] = None
    new_status: str
    changed_by: Optional[int] = None
    remarks: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class DonationResponse(BaseModel):
    id: int
    donor_id: int
    food_name: str
    description: Optional[str] = None
    food_category: str
    quantity: float
    quantity_unit: str
    preparation_time: datetime
    expiry_time: datetime
    pickup_address: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    image_url: Optional[str] = None
    status: str
    assigned_ngo_id: Optional[int] = None
    assigned_volunteer_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    urgency_level: Optional[str] = "Fresh" # Fresh, Use Soon, Urgent, Expired

    class Config:
        from_attributes = True

class DonationDetailResponse(DonationResponse):
    donor_name: Optional[str] = None
    donor_phone: Optional[str] = None
    ngo_name: Optional[str] = None
    volunteer_name: Optional[str] = None
    volunteer_phone: Optional[str] = None
    history: List[DonationHistoryResponse] = []

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

    class Config:
        from_attributes = True

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

    class Config:
        from_attributes = True

# Reward Schemas
class RewardResponse(BaseModel):
    id: int
    user_id: int
    points: int
    level: str
    next_level_points: int = 100
    points_to_next_level: int = 100

    class Config:
        from_attributes = True

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

class VolunteerRecommendationResponse(BaseModel):
    volunteer_id: int
    volunteer_name: str
    phone: Optional[str] = None
    distance_km: float
    score: float
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
    meals_donated: float
    unverified_ngos: int
