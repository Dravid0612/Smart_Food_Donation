from typing import Optional
from pydantic import BaseModel, ConfigDict


class DonationCreate(BaseModel):
    food_name: str
    quantity: str
    preparation_time: str
    expiry_time: str
    pickup_address: str
    latitude: float = 0.0
    longitude: float = 0.0
    image_url: Optional[str] = None
    status: str = "pending"


class DonationOut(DonationCreate):
    id: int
    donor_id: int

    model_config = ConfigDict(from_attributes=True)


class DonationUpdate(DonationCreate):
    pass


class DonationStatusUpdate(BaseModel):
    status: str
