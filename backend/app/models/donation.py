from sqlalchemy import Column, Integer, String, Float, DateTime, Text
from sqlalchemy.sql import func
from app.db.base import Base


class FoodDonation(Base):
    __tablename__ = "food_donations"

    id = Column(Integer, primary_key=True, index=True)
    food_name = Column(String(255), nullable=False)
    quantity = Column(String(100), nullable=False)
    preparation_time = Column(String(100), nullable=False)
    expiry_time = Column(String(100), nullable=False)
    pickup_address = Column(Text, nullable=False)
    latitude = Column(Float, nullable=False, default=0.0)
    longitude = Column(Float, nullable=False, default=0.0)
    image_url = Column(String(500), nullable=True)
    status = Column(String(50), nullable=False, default="pending")
    donor_id = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
