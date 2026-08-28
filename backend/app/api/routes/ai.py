from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status
from typing import Optional
from datetime import datetime
from app.schemas.schemas import AIFoodAnalysisResponse
from app.services.ai_vision_service import analyze_food_image_and_metadata
from app.core.dependencies import get_current_user
from app.models.models import User

router = APIRouter(prefix="/ai", tags=["AI Vision & Decision Fusion"])

@router.post("/analyze-food", response_model=AIFoodAnalysisResponse)
async def analyze_food(
    image: Optional[UploadFile] = File(None),
    food_category: Optional[str] = Form("Cooked Food"),
    food_type: Optional[str] = Form(None),
    quantity: Optional[float] = Form(10.0),
    storage_method: Optional[str] = Form("Room Temperature"),
    storage_duration_hours: Optional[float] = Form(2.0),
    storage_continuous: Optional[bool] = Form(True),
    packaging_condition: Optional[str] = Form("Covered"),
    previously_served: Optional[str] = Form("No"),
    exposure_status: Optional[str] = Form("No"),
    handling_status: Optional[str] = Form("No"),
    preparation_time: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user)
):
    """
    Production-grade AI Vision & Time-Aware Decision Assessment Endpoint.
    Analyzes uploaded image features combined with food type, storage method, history, handling,
    to assess visual condition, spoilage signs, discoloration, and calculate advisory rescue window.
    """
    image_bytes = None
    filename = ""
    if image:
        image_bytes = await image.read()
        filename = image.filename or "uploaded_food.jpg"

    prep_dt = None
    if preparation_time:
        try:
            prep_dt = datetime.fromisoformat(preparation_time)
        except Exception:
            prep_dt = None

    result = analyze_food_image_and_metadata(
        image_bytes=image_bytes,
        filename=filename,
        food_category=food_category,
        food_type=food_type,
        quantity=quantity or 10.0,
        storage_method=storage_method,
        storage_duration_hours=storage_duration_hours,
        storage_continuous=storage_continuous if storage_continuous is not None else True,
        packaging_condition=packaging_condition,
        previously_served=previously_served or "No",
        exposure_status=exposure_status or "No",
        handling_status=handling_status or "No",
        preparation_time=prep_dt
    )

    return AIFoodAnalysisResponse(**result)
