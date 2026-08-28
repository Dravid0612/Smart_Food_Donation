"""
Notification Service — Smart Food Rescue
=========================================
Full event-driven notification service supporting:
  - In-app notification creation with deduplication
  - FCM push notification abstraction (mock by default, FCM when configured)
  - Trilingual notification content (English, Tamil, Hindi)
  - Role-based recipient routing
  - Notification preference enforcement
  - Deep-link routing payload (never contains OTP, JWT, or private data)
  - Audit trail for notification lifecycle

SECURITY:
  - Notification payload NEVER contains OTP, passwords, JWT, full phone numbers.
  - Deep-link data contains only safe routing keys: type + donation_id.
  - Urgent rescue alerts bypass quiet-hour preferences (per-spec).
"""

import json
import logging
from datetime import datetime, timezone
from typing import Optional, List

from sqlalchemy.orm import Session

from app.models.models import Notification, NotificationPreference, User, FoodDonation
from app.core.config import settings

logger = logging.getLogger("smart_food_rescue.notifications")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ─────────────────────────────────────────────────────────────────────────────
# Trilingual Notification Content
# ─────────────────────────────────────────────────────────────────────────────

# Structure: event_type → {lang: {title, message}}
_NOTIFICATION_CONTENT = {
    "DONATION_CREATED": {
        "en": {"title": "Donation Submitted", "message": "Your donation has been submitted and is being reviewed."},
        "ta": {"title": "நன்கொடை சமர்ப்பிக்கப்பட்டது", "message": "உங்கள் நன்கொடை சமர்ப்பிக்கப்பட்டது, மதிப்பாய்வு நடைபெறுகிறது."},
        "hi": {"title": "दान जमा किया गया", "message": "आपका दान जमा किया गया है और समीक्षाधीन है।"},
    },
    "AI_ANALYSIS_COMPLETE": {
        "en": {"title": "Food Analysis Ready", "message": "AI visual analysis of your donation is complete. Tap to review."},
        "ta": {"title": "உணவு பகுப்பாய்வு தயார்", "message": "உங்கள் நன்கொடையின் AI பகுப்பாய்வு முடிந்தது."},
        "hi": {"title": "खाद्य विश्लेषण तैयार", "message": "आपके दान का AI दृश्य विश्लेषण पूर्ण हो गया है।"},
    },
    "DONATION_ACCEPTED": {
        "en": {"title": "Donation Accepted ✓", "message": "A partner NGO has accepted your food donation."},
        "ta": {"title": "நன்கொடை ஏற்கப்பட்டது ✓", "message": "ஒரு NGO உங்கள் நன்கொடையை ஏற்றுக்கொண்டது."},
        "hi": {"title": "दान स्वीकृत ✓", "message": "एक NGO ने आपका खाद्य दान स्वीकार कर लिया है।"},
    },
    "VOLUNTEER_ASSIGNED": {
        "en": {"title": "Volunteer Assigned", "message": "A volunteer has been assigned to collect your donation."},
        "ta": {"title": "தன்னார்வலர் நியமிக்கப்பட்டார்", "message": "ஒரு தன்னார்வலர் உங்கள் நன்கொடையை சேகரிக்க நியமிக்கப்பட்டார்."},
        "hi": {"title": "स्वयंसेवक नियुक्त", "message": "आपके दान को एकत्र करने के लिए एक स्वयंसेवक नियुक्त किया गया है।"},
    },
    "VOLUNTEER_ON_THE_WAY": {
        "en": {"title": "Volunteer On The Way 🚴", "message": "Your volunteer is on the way to collect the donation. Please be ready."},
        "ta": {"title": "தன்னார்வலர் வழியில் உள்ளார் 🚴", "message": "தன்னார்வலர் நன்கொடையை சேகரிக்க வழியில் உள்ளார். தயாராக இருங்கள்."},
        "hi": {"title": "स्वयंसेवक रास्ते में है 🚴", "message": "आपका स्वयंसेवक दान लेने के रास्ते में है। कृपया तैयार रहें।"},
    },
    "VOLUNTEER_ARRIVED": {
        "en": {"title": "Volunteer Has Arrived 📍", "message": "Your volunteer has arrived. Open the app to view your secure pickup code."},
        "ta": {"title": "தன்னார்வலர் வந்துவிட்டார் 📍", "message": "தன்னார்வலர் வந்துள்ளார். பாதுகாப்பான pickup குறியீட்டைக் காண app திறங்கள்."},
        "hi": {"title": "स्वयंसेवक पहुंच गया 📍", "message": "आपका स्वयंसेवक पहुंच गया है। सुरक्षित pickup कोड देखने के लिए app खोलें।"},
    },
    "OTP_SMS_SENT": {
        "en": {"title": "Pickup Code Sent", "message": "Your pickup code has been sent to your verified phone. Tap to view in app."},
        "ta": {"title": "Pickup குறியீடு அனுப்பப்பட்டது", "message": "Pickup குறியீடு உங்கள் சரிபார்க்கப்பட்ட தொலைபேசிக்கு அனுப்பப்பட்டது."},
        "hi": {"title": "Pickup कोड भेजा गया", "message": "आपका pickup कोड आपके सत्यापित फोन पर भेजा गया है।"},
    },
    "OTP_SMS_DELIVERED": {
        "en": {"title": "Pickup Code Delivered ✅", "message": "Your pickup code has been delivered to your phone. Show it to the volunteer."},
        "ta": {"title": "Pickup குறியீடு வழங்கப்பட்டது ✅", "message": "Pickup குறியீடு உங்கள் தொலைபேசியில் வழங்கப்பட்டது."},
        "hi": {"title": "Pickup कोड डिलीवर हुआ ✅", "message": "आपका pickup कोड आपके फोन पर डिलीवर हो गया है।"},
    },
    "OTP_SMS_FAILED": {
        "en": {"title": "⚠ SMS Delivery Failed", "message": "SMS could not be delivered. Your secure pickup code is still available in the app."},
        "ta": {"title": "⚠ SMS வழங்கல் தோல்வியடைந்தது", "message": "SMS வழங்க முடியவில்லை. Pickup குறியீடு app-ல் கிடைக்கிறது."},
        "hi": {"title": "⚠ SMS डिलीवरी विफल", "message": "SMS डिलीवर नहीं हो सका। आपका सुरक्षित pickup कोड app में उपलब्ध है।"},
    },
    "PICKUP_COMPLETED": {
        "en": {"title": "Pickup Confirmed ✓", "message": "Food pickup has been verified and confirmed."},
        "ta": {"title": "Pickup உறுதிப்படுத்தப்பட்டது ✓", "message": "உணவு சேகரிப்பு சரிபார்க்கப்பட்டு உறுதிப்படுத்தப்பட்டது."},
        "hi": {"title": "Pickup पुष्टि ✓", "message": "खाद्य pickup सत्यापित और पुष्टि हो गई है।"},
    },
    "FOOD_IN_TRANSIT": {
        "en": {"title": "Food In Transit 🚚", "message": "The food is on its way to the NGO."},
        "ta": {"title": "உணவு வழியில் உள்ளது 🚚", "message": "உணவு NGO-க்கு வழியில் உள்ளது."},
        "hi": {"title": "खाना रास्ते में है 🚚", "message": "खाना NGO की तरफ रास्ते में है।"},
    },
    "DELIVERED_TO_NGO": {
        "en": {"title": "Food Delivered to NGO ✓", "message": "The food has been delivered to the partner NGO."},
        "ta": {"title": "NGO-க்கு உணவு வழங்கப்பட்டது ✓", "message": "உணவு NGO-க்கு வழங்கப்பட்டது."},
        "hi": {"title": "NGO को खाना पहुंचा ✓", "message": "खाना NGO को डिलीवर कर दिया गया है।"},
    },
    "DISTRIBUTION_STARTED": {
        "en": {"title": "Distribution Started", "message": "The NGO has started distributing the food to beneficiaries."},
        "ta": {"title": "விநியோகம் தொடங்கியது", "message": "NGO பயனாளிகளுக்கு உணவு விநியோகிக்கத் தொடங்கியது."},
        "hi": {"title": "वितरण शुरू हुआ", "message": "NGO ने लाभार्थियों को खाना वितरित करना शुरू कर दिया है।"},
    },
    "DISTRIBUTION_COMPLETED": {
        "en": {"title": "Distribution Complete 🎉", "message": "All food has been distributed to those in need."},
        "ta": {"title": "விநியோகம் முடிந்தது 🎉", "message": "அனைத்து உணவும் தேவையானவர்களுக்கு வழங்கப்பட்டது."},
        "hi": {"title": "वितरण पूर्ण 🎉", "message": "सारा खाना जरूरतमंदों को वितरित कर दिया गया है।"},
    },
    "RESCUE_COMPLETED": {
        "en": {"title": "Rescue Complete ✓", "message": "The food rescue is complete! Please share your experience."},
        "ta": {"title": "Rescue முடிந்தது ✓", "message": "உணவு rescue வெற்றிகரமாக முடிந்தது! உங்கள் அனுபவத்தை பகிருங்கள்."},
        "hi": {"title": "Rescue पूर्ण ✓", "message": "खाद्य rescue पूर्ण हो गया! कृपया अपना अनुभव साझा करें।"},
    },
    "RESCUE_AT_RISK": {
        "en": {"title": "⚡ Rescue At Risk", "message": "This rescue is at risk. Urgent attention required."},
        "ta": {"title": "⚡ Rescue ஆபத்தில் உள்ளது", "message": "இந்த rescue ஆபத்தில் உள்ளது. உடனடி கவனம் தேவை."},
        "hi": {"title": "⚡ Rescue खतरे में", "message": "यह rescue खतरे में है। तत्काल ध्यान आवश्यक है।"},
    },
    "FALLBACK_STARTED": {
        "en": {"title": "Finding Alternative Transport", "message": "We're finding alternative transport options for your donation."},
        "ta": {"title": "மாற்று போக்குவரத்து தேடுகிறோம்", "message": "உங்கள் நன்கொடைக்கு மாற்று போக்குவரத்து விருப்பங்களை தேடுகிறோம்."},
        "hi": {"title": "वैकल्पिक परिवहन खोज रहे हैं", "message": "हम आपके दान के लिए वैकल्पिक परिवहन विकल्प खोज रहे हैं।"},
    },
    "ADMIN_ESCALATION": {
        "en": {"title": "🚨 Critical Rescue Escalation", "message": "A rescue requires immediate admin intervention."},
        "ta": {"title": "🚨 முக்கியமான Rescue அவசரம்", "message": "ஒரு rescue உடனடி நிர்வாக தலையீடு தேவைப்படுகிறது."},
        "hi": {"title": "🚨 महत्वपूर्ण Rescue एस्केलेशन", "message": "एक rescue को तत्काल प्रशासनिक हस्तक्षेप की आवश्यकता है।"},
    },
    "FEEDBACK_REMINDER": {
        "en": {"title": "Share Your Experience", "message": "Your rescue is complete. Please share your feedback."},
        "ta": {"title": "உங்கள் அனுபவத்தை பகிருங்கள்", "message": "Rescue முடிந்தது. தயவுசெய்து கருத்தை பகிருங்கள்."},
        "hi": {"title": "अपना अनुभव साझा करें", "message": "आपका rescue पूर्ण है। कृपया अपनी प्रतिक्रिया साझा करें।"},
    },
    "NEW_TASK": {
        "en": {"title": "New Rescue Task", "message": "A new food rescue task is available in your area."},
        "ta": {"title": "புதிய Rescue பணி", "message": "உங்கள் பகுதியில் புதிய உணவு rescue பணி உள்ளது."},
        "hi": {"title": "नया Rescue कार्य", "message": "आपके क्षेत्र में एक नया खाद्य rescue कार्य उपलब्ध है।"},
    },
    "TASK_CANCELLED": {
        "en": {"title": "Task Cancelled", "message": "The rescue task has been cancelled."},
        "ta": {"title": "பணி ரத்து செய்யப்பட்டது", "message": "Rescue பணி ரத்து செய்யப்பட்டது."},
        "hi": {"title": "कार्य रद्द किया गया", "message": "Rescue कार्य रद्द कर दिया गया है।"},
    },
    "RESCUE_REMATCHED_DONOR": {
        "en": {"title": "Rescue Plan Updated ⚡", "message": "Your rescue is being re-optimized with an alternative pickup courier to ensure timely collection."},
        "ta": {"title": "மீட்பு திட்டம் புதுப்பிக்கப்பட்டது ⚡", "message": "உங்கள் உணவு சரியான நேரத்தில் சேகரிக்கப்படுவதை உறுதிசெய்ய மீட்பு திட்டம் மறுசீரமைக்கப்படுகிறது."},
        "hi": {"title": "बचाव योजना अपडेट ⚡", "message": "समय पर पिकअप सुनिश्चित करने के लिए आपकी बचाव योजना को फिर से अनुकूलित किया जा रहा है।"},
    },
    "RESCUE_REMATCHED_NGO": {
        "en": {"title": "Pickup Assignment Updated", "message": "A new feasible volunteer courier has been dispatched for this donation."},
        "ta": {"title": "பிக்கப் ஒதுக்கீடு புதுப்பிக்கப்பட்டது", "message": "இந்த நன்கொடைக்காக புதிய தன்னார்வலர் நியமிக்கப்பட்டுள்ளார்."},
        "hi": {"title": "पिकअप असाइनमेंट अपडेट किया गया", "message": "इस दान के लिए एक नया स्वयंसेवक नियुक्त किया गया है।"},
    },
    "TASK_REASSIGNED_OLD_VOLUNTEER": {
        "en": {"title": "Pickup Assignment Updated", "message": "Your pickup task has been reassigned to maintain the rescue timeline."},
        "ta": {"title": "பணி ஒதுக்கீடு புதுப்பிக்கப்பட்டது", "message": "மீட்பு காலக்கெடுவை பராமரிக்க உங்கள் பணி மறுஒதுக்கீடு செய்யப்பட்டுள்ளது."},
        "hi": {"title": "कार्य असाइनमेंट अपडेट किया गया", "message": "बचाव समय सीमा बनाए रखने के लिए आपका कार्य फिर से सौंपा गया है।"},
    },
    "NEW_TASK_REMATCHED_NEW_VOLUNTEER": {
        "en": {"title": "New Rescue Task Assigned 🚴", "message": "You have been assigned an active food rescue. Tap to view pickup details."},
        "ta": {"title": "புதிய மீட்பு பணி ஒதுக்கப்பட்டுள்ளது 🚴", "message": "உங்களுக்கு உணவு மீட்பு பணி ஒதுக்கப்பட்டுள்ளது. பிக்கப் விவரங்களைக் காண தொடவும்."},
        "hi": {"title": "नया बचाव कार्य सौंपा गया 🚴", "message": "आपको एक सक्रिय खाद्य बचाव कार्य सौंपा गया है। विवरण देखने के लिए टैप करें।"},
    },
    "RESCUE_AT_RISK_ADMIN": {
        "en": {"title": "⚡ Rescue Rematched (At Risk)", "message": "A rescue route was automatically rematched to maintain feasibility."},
        "ta": {"title": "⚡ மீட்பு மறுஒதுக்கீடு செய்யப்பட்டது", "message": "சாத்தியக்கூறு ஆபத்து காரணமாக மீட்பு தானாகவே மறுஒதுக்கீடு செய்யப்பட்டது."},
        "hi": {"title": "⚡ बचाव पुनर्गठित (जोखिम में)", "message": "समय सीमा बनाए रखने के लिए बचाव मार्ग को स्वचालित रूप से फिर से असाइन किया गया।"},
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# Deep-link routing: event → screen route
# ─────────────────────────────────────────────────────────────────────────────

# SECURITY: deep-link payloads contain ONLY safe routing metadata.
# Never include OTP, password, JWT, phone number, full address.
def _build_deep_link_data(event_type: str, donation_id: Optional[int]) -> str:
    """Returns JSON string with safe routing payload only."""
    return json.dumps({
        "type": event_type,
        "donation_id": str(donation_id) if donation_id else None,
    })


# ─────────────────────────────────────────────────────────────────────────────
# FCM Push Abstraction
# ─────────────────────────────────────────────────────────────────────────────

def _send_fcm_push(notification: Notification, db: Session) -> bool:
    """
    Sends a FCM push notification. Uses mock adapter if FCM not configured.
    SECURITY: Payload never contains OTP, JWT, or private data.
    """
    if not settings.FCM_SERVER_KEY or not settings.FCM_PROJECT_ID:
        # Mock adapter — log only
        logger.info(
            f"[MockFCM] Push would be sent: user_id={notification.user_id} "
            f"event_type={notification.event_type} "
            f"title='{notification.title}' "
            f"deep_link={notification.deep_link_data} "
            f"(FCM_SERVER_KEY not configured — mock adapter)"
        )
        notification.is_sent = True
        notification.sent_at = _utcnow()
        db.commit()
        return True

    # Production FCM (requires FCM_SERVER_KEY)
    try:
        import urllib.request
        import urllib.error

        # Get FCM token for this user
        prefs = db.query(NotificationPreference).filter(
            NotificationPreference.user_id == notification.user_id
        ).first()
        if not prefs or not prefs.fcm_token:
            logger.info(f"[FCM] No FCM token for user_id={notification.user_id} — skipping push")
            return False

        payload = json.dumps({
            "to": prefs.fcm_token,
            "notification": {
                "title": notification.title,
                "body": notification.message,
                # NEVER add OTP here
            },
            "data": json.loads(notification.deep_link_data or "{}"),
            "priority": "high",
        }).encode()

        req = urllib.request.Request(
            "https://fcm.googleapis.com/fcm/send",
            data=payload,
            headers={
                "Authorization": f"key={settings.FCM_SERVER_KEY}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            result = json.loads(resp.read())
            success = result.get("success", 0) > 0
            notification.is_sent = success
            notification.sent_at = _utcnow() if success else None
            db.commit()
            logger.info(f"[FCM] Push sent: user_id={notification.user_id} success={success}")
            return success

    except Exception as e:
        logger.error(f"[FCM] Push failed for user_id={notification.user_id}: {e}")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# Notification Preference Check
# ─────────────────────────────────────────────────────────────────────────────

# Urgent events that bypass preference settings
_ALWAYS_SEND_EVENTS = {
    "VOLUNTEER_ARRIVED", "OTP_SMS_SENT", "OTP_SMS_DELIVERED", "OTP_SMS_FAILED",
    "RESCUE_AT_RISK", "ADMIN_ESCALATION", "PICKUP_COMPLETED",
    "RESCUE_REMATCHED_DONOR", "RESCUE_REMATCHED_NGO", "TASK_REASSIGNED_OLD_VOLUNTEER",
    "NEW_TASK_REMATCHED_NEW_VOLUNTEER", "RESCUE_AT_RISK_ADMIN",
}

def _should_send_notification(
    prefs: Optional[NotificationPreference],
    event_type: str,
) -> bool:
    """Check notification preferences. Urgent events always bypass preferences."""
    if event_type in _ALWAYS_SEND_EVENTS:
        return True
    if prefs is None:
        return True  # Default: send all

    event_category_map = {
        "operational_notifications": {
            "DONATION_CREATED", "AI_ANALYSIS_COMPLETE", "DONATION_ACCEPTED",
            "VOLUNTEER_ASSIGNED", "VOLUNTEER_ON_THE_WAY", "FOOD_IN_TRANSIT",
            "DELIVERED_TO_NGO", "DISTRIBUTION_STARTED", "FALLBACK_STARTED",
            "NEW_TASK", "TASK_CANCELLED", "RESCUE_REMATCHED_DONOR", "RESCUE_REMATCHED_NGO",
            "TASK_REASSIGNED_OLD_VOLUNTEER", "NEW_TASK_REMATCHED_NEW_VOLUNTEER",
        },
        "urgent_rescue_alerts": {
            "RESCUE_AT_RISK", "ADMIN_ESCALATION", "RESCUE_UNLIKELY", "RESCUE_AT_RISK_ADMIN",
        },
        "impact_updates": {
            "DISTRIBUTION_COMPLETED", "RESCUE_COMPLETED",
        },
        "feedback_reminders": {
            "FEEDBACK_REMINDER",
        },
    }

    for pref_attr, events in event_category_map.items():
        if event_type in events:
            return getattr(prefs, pref_attr, True)
    return True


# ─────────────────────────────────────────────────────────────────────────────
# Core: Create Event Notification
# ─────────────────────────────────────────────────────────────────────────────

def create_event_notification(
    db: Session,
    user_id: int,
    event_type: str,
    donation_id: Optional[int] = None,
    lang: str = "en",
    send_push: bool = True,
    extra_message: Optional[str] = None,
) -> Optional[Notification]:
    """
    Creates an in-app notification for a lifecycle event with deduplication.
    Optionally sends FCM push (mock by default).

    Args:
        user_id: Recipient user ID
        event_type: Structured event key (e.g. VOLUNTEER_ARRIVED)
        donation_id: Related donation ID for routing
        lang: Language code (en, ta, hi)
        send_push: Whether to attempt FCM push
        extra_message: Optional message override (e.g. for custom alerts)

    Returns:
        Created Notification or None if deduplicated/preference-blocked.
    """
    # Deduplication: same event for same donation within 60 seconds is suppressed
    dedup_key = f"{donation_id}:{event_type}" if donation_id else f"user:{user_id}:{event_type}"
    if donation_id:
        from datetime import timedelta
        cutoff = _utcnow() - timedelta(seconds=60)
        duplicate = (
            db.query(Notification)
            .filter(
                Notification.user_id == user_id,
                Notification.dedup_key == dedup_key,
                Notification.created_at >= cutoff,
            )
            .first()
        )
        if duplicate:
            logger.debug(f"[Notification] Deduplicated event_type={event_type} user_id={user_id}")
            return None

    # Preference check
    prefs = db.query(NotificationPreference).filter(
        NotificationPreference.user_id == user_id
    ).first()
    if not _should_send_notification(prefs, event_type):
        logger.debug(f"[Notification] Preference-blocked event_type={event_type} user_id={user_id}")
        return None

    # Get content for language (fallback to English)
    content_map = _NOTIFICATION_CONTENT.get(event_type, {})
    content = content_map.get(lang) or content_map.get("en") or {
        "title": event_type.replace("_", " ").title(),
        "message": extra_message or "",
    }

    notification = Notification(
        user_id=user_id,
        title=content["title"],
        message=extra_message or content["message"],
        type=_event_to_type(event_type),
        related_donation_id=donation_id,
        event_type=event_type,
        deep_link_data=_build_deep_link_data(event_type, donation_id),
        dedup_key=dedup_key,
        is_read=False,
        is_sent=False,
    )
    db.add(notification)
    db.commit()
    db.refresh(notification)

    # Attempt FCM push
    if send_push:
        _send_fcm_push(notification, db)

    return notification


def _event_to_type(event_type: str) -> str:
    """Maps event type to notification type category."""
    if "EMERGENCY" in event_type or "CRITICAL" in event_type or "ADMIN_ESCALATION" in event_type:
        return "emergency"
    if "RESCUE_AT_RISK" in event_type or "OTP_SMS_FAILED" in event_type or "FALLBACK" in event_type:
        return "alert"
    if "ASSIGNMENT" in event_type or "VOLUNTEER" in event_type or "PICKUP" in event_type:
        return "assignment"
    if "DONATION" in event_type or "NGO" in event_type or "DISTRIBUTION" in event_type:
        return "donation"
    return "info"


# ─────────────────────────────────────────────────────────────────────────────
# Notification Management
# ─────────────────────────────────────────────────────────────────────────────

def create_notification(
    db: Session,
    user_id: int,
    title: str,
    message: str,
    type: str = "info",
    related_donation_id: int = None,
) -> Notification:
    """
    Legacy-compatible simple notification creator.
    Kept for backward compatibility with existing callers.
    """
    notification = Notification(
        user_id=user_id,
        title=title,
        message=message,
        type=type,
        related_donation_id=related_donation_id,
    )
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return notification


def mark_notification_opened(db: Session, notification_id: int, user_id: int) -> bool:
    """Records when user taps a notification (opened_at tracking)."""
    notif = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == user_id,
    ).first()
    if not notif:
        return False
    notif.opened_at = _utcnow()
    notif.is_read = True
    db.commit()
    return True


def send_rescue_completion_feedback_reminder(
    db: Session,
    donation: FoodDonation,
    lang: str = "en",
):
    """
    Sends a single feedback reminder to all rescue participants after completion.
    Respects feedback_reminder preference.
    Deduplication prevents spam (1 per user per donation per completion).
    """
    from app.models.models import VolunteerAssignment

    participants = []

    # Donor
    if donation.donor_id:
        participants.append(("FEEDBACK_REMINDER", donation.donor_id))

    # NGO (find via assigned_ngo.user_id)
    if donation.assigned_ngo and donation.assigned_ngo.user_id:
        participants.append(("FEEDBACK_REMINDER", donation.assigned_ngo.user_id))

    # Volunteer
    if donation.assigned_volunteer_id:
        participants.append(("FEEDBACK_REMINDER", donation.assigned_volunteer_id))

    for event_type, uid in participants:
        user = db.query(User).filter(User.id == uid).first()
        user_lang = (user.preferred_language if user else lang) or "en"
        create_event_notification(
            db=db,
            user_id=uid,
            event_type=event_type,
            donation_id=donation.id,
            lang=user_lang,
        )
