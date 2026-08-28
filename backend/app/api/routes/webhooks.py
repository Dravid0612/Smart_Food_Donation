"""
SMS Delivery Webhook Route — Smart Food Rescue
================================================
Receives and processes delivery receipts from the SMS provider.

SECURITY:
  - Provider webhook signature is validated before any processing.
  - Status may only be set by this authenticated webhook endpoint.
  - No OTP data is exposed in responses.
  - Suspicious or unrecognized payloads are rejected with 400.
"""

import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.sms_service import sms_provider
from app.services.otp_service import process_sms_delivery_webhook
from app.services.notification_service import create_event_notification
from app.models.models import OtpDeliveryRecord, User, FoodDonation

logger = logging.getLogger("smart_food_rescue.webhooks")

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


@router.post("/sms-delivery")
async def sms_delivery_callback(
    request: Request,
    db: Session = Depends(get_db),
):
    """
    SMS delivery receipt webhook from provider.
    Called by the SMS provider when delivery status changes.

    Security:
    - Validates provider webhook signature before processing.
    - Only updates OtpDeliveryRecord — never exposes OTP.
    - Creates in-app notification if operationally relevant.
    """
    raw_body = await request.body()
    headers = dict(request.headers)

    # Step 1: Validate provider webhook signature
    provider = sms_provider()
    if not provider.validate_webhook_signature(raw_body, headers):
        logger.warning(
            f"[SMS Webhook] Invalid signature from {request.client.host if request.client else 'unknown'}"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Webhook signature validation failed.",
        )

    # Step 2: Parse delivery update
    try:
        payload = json.loads(raw_body.decode())
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid webhook payload format.",
        )

    update = provider.parse_delivery_webhook(payload)

    if not update.provider_message_id or update.provider_message_id == "UNKNOWN":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Webhook payload missing provider_message_id.",
        )

    # Step 3: Find and update delivery record
    delivery_record = process_sms_delivery_webhook(
        db=db,
        provider_message_id=update.provider_message_id,
        new_status=update.status,
        delivered_at=update.timestamp if update.status == "DELIVERED" else None,
        failed_at=update.timestamp if update.status == "FAILED" else None,
        failure_reason=update.failure_reason,
        raw_payload_json=json.dumps(payload),
    )

    if not delivery_record:
        # Not found — may have already been processed
        return {"status": "ignored", "reason": "No matching delivery record found."}

    # Step 4: Create in-app notification for operationally significant status changes
    if delivery_record.user_id and delivery_record.donation_id:
        user = db.query(User).filter(User.id == delivery_record.user_id).first()
        lang = (user.preferred_language if user else "en") or "en"

        if update.status == "DELIVERED":
            create_event_notification(
                db=db,
                user_id=delivery_record.user_id,
                event_type="OTP_SMS_DELIVERED",
                donation_id=delivery_record.donation_id,
                lang=lang,
            )
        elif update.status == "FAILED":
            create_event_notification(
                db=db,
                user_id=delivery_record.user_id,
                event_type="OTP_SMS_FAILED",
                donation_id=delivery_record.donation_id,
                lang=lang,
            )

    logger.info(
        f"[SMS Webhook] Processed: message_id={update.provider_message_id} "
        f"status={update.status}"
    )

    return {
        "status": "processed",
        "provider_message_id": update.provider_message_id,
        "new_status": update.status,
    }
