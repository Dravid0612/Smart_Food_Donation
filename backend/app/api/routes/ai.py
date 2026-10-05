from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status
from app.schemas.schemas import AIFoodAnalysisResponse
from app.services.ai_vision_service import analyze_food_image_and_metadata
from app.core.dependencies import get_current_user
from app.models.models import User

router = APIRouter(prefix="/ai", tags=["AI Vision & Decision Fusion"])

@router.post("/analyze-food", response_model=AIFoodAnalysisResponse)
async def analyze_food(
    image: Optional[UploadFile] = File(None),
    images: Optional[List[UploadFile]] = File(None),
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
    Analyzes 1 to 3 uploaded images combined with food type, storage method, history, handling,
    to assess visual condition, spoilage signs, discoloration, and calculate advisory rescue window.
    Applies conservative aggregation: spoilage on ANY image flags the rescue.
    """
    collected_files = []
    if images:
        collected_files.extend(images)
    if image and image not in collected_files:
        collected_files.append(image)

    images_data = []
    for f in collected_files:
        try:
            b = await f.read()
            images_data.append({"bytes": b, "filename": f.filename or "uploaded_food.jpg"})
        except Exception:
            pass

    prep_dt = None
    if preparation_time:
        try:
            prep_dt = datetime.fromisoformat(preparation_time)
        except Exception:
            prep_dt = None

    result = analyze_food_image_and_metadata(
        image_bytes=images_data[0]["bytes"] if images_data else None,
        filename=images_data[0]["filename"] if images_data else "",
        images_data=images_data if images_data else None,
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
