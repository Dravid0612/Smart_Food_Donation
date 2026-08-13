from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, Enum
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
    role = Column(String(50), nullable=False, default="donor") # donor, ngo, volunteer, admin
    address = Column(Text, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    profile_image = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    # Relationships
    ngo_profile = relationship("NGO", back_populates="user", uselist=False, cascade="all, delete-orphan")
    donations = relationship("FoodDonation", foreign_keys="FoodDonation.donor_id", back_populates="donor")
    volunteer_assignments = relationship("VolunteerAssignment", back_populates="volunteer")
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")
    reward = relationship("Reward", back_populates="user", uselist=False, cascade="all, delete-orphan")

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
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    # Relationships
    user = relationship("User", back_populates="ngo_profile")
    accepted_donations = relationship("FoodDonation", foreign_keys="FoodDonation.assigned_ngo_id", back_populates="assigned_ngo")

class FoodDonation(Base):
    __tablename__ = "food_donations"

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
    status = Column(String(50), nullable=False, default="pending") # pending, accepted, volunteer_assigned, collected, delivered, completed, rejected, expired, cancelled
    assigned_ngo_id = Column(Integer, ForeignKey("ngos.id", ondelete="SET NULL"), nullable=True)
    assigned_volunteer_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    # Relationships
    donor = relationship("User", foreign_keys=[donor_id], back_populates="donations")
    assigned_ngo = relationship("NGO", foreign_keys=[assigned_ngo_id], back_populates="accepted_donations")
    assigned_volunteer = relationship("User", foreign_keys=[assigned_volunteer_id])
    history = relationship("DonationHistory", back_populates="donation", cascade="all, delete-orphan")
    assignments = relationship("VolunteerAssignment", back_populates="donation", cascade="all, delete-orphan")

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

    id = Column(Integer, primary_key=True, index=True)
    donation_id = Column(Integer, ForeignKey("food_donations.id", ondelete="CASCADE"), nullable=False)
    volunteer_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    assigned_at = Column(DateTime, default=utcnow)
    accepted_at = Column(DateTime, nullable=True)
    collected_at = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)
    status = Column(String(50), nullable=False, default="assigned") # assigned, accepted, collected, delivered, cancelled

    # Relationships
    donation = relationship("FoodDonation", back_populates="assignments")
    volunteer = relationship("User", back_populates="volunteer_assignments")

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    type = Column(String(50), default="info")
    related_donation_id = Column(Integer, ForeignKey("food_donations.id", ondelete="SET NULL"), nullable=True)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=utcnow)

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
