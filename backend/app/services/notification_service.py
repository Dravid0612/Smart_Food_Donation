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

import os
import json
import logging
import asyncio
import threading
import time
from datetime import datetime, timezone
from typing import Optional, List, Dict, Set

from sqlalchemy.orm import Session

from app.models.models import Notification, NotificationPreference, User, FoodDonation
from app.core.config import settings

logger = logging.getLogger("smart_food_rescue.notifications")


_fcm_telemetry: Dict[str, int] = {
    "fcm_send_attempts": 0,
    "fcm_duplicate_prevented": 0,
    "fcm_failures": 0,
}
_fcm_lock = threading.Lock()


def get_fcm_telemetry() -> Dict[str, int]:
    """Returns a snapshot of FCM push usage counters."""
    with _fcm_lock:
        return dict(_fcm_telemetry)


def reset_fcm_telemetry():
    """Resets FCM push usage counters."""
    with _fcm_lock:
        for k in _fcm_telemetry:
            _fcm_telemetry[k] = 0


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ─────────────────────────────────────────────────────────────────────────────
# In-Memory Real-Time SSE Broadcaster (Zero Redis/Celery/Kafka Required)
# ─────────────────────────────────────────────────────────────────────────────
_user_subscribers: Dict[int, Set[asyncio.Queue]] = {}


def subscribe_user_stream(user_id: int) -> asyncio.Queue:
    """Subscribes an active SSE connection to real-time events for the specified user."""
    queue: asyncio.Queue = asyncio.Queue()
    if user_id not in _user_subscribers:
        _user_subscribers[user_id] = set()
    _user_subscribers[user_id].add(queue)
    return queue


def unsubscribe_user_stream(user_id: int, queue: asyncio.Queue):
    """Unsubscribes an SSE connection when the client disconnects."""
    if user_id in _user_subscribers:
        _user_subscribers[user_id].discard(queue)
        if not _user_subscribers[user_id]:
            del _user_subscribers[user_id]


def broadcast_user_event(user_id: int, payload: dict):
    """Pushes a live notification event payload to all active SSE queues for user_id."""
    if user_id in _user_subscribers:
        for q in list(_user_subscribers[user_id]):
            try:
                q.put_nowait(payload)
            except Exception:
                pass


def broadcast_admin_event(payload: dict):
    """Broadcasts a live event to all connected subscribers."""
    for uid, queues in list(_user_subscribers.items()):
        for q in list(queues):
            try:
                q.put_nowait(payload)
            except Exception:
                pass


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
    # ─── Canonical Phase 9 Operational Events ────────────────────────────────
    "NEW_RESCUE": {
        "en": {"title": "New Food Rescue Listed", "message": "A new food rescue surplus has been posted."},
        "ta": {"title": "புதிய உணவு மீட்பு பதிவு", "message": "புதிய உணவு மீட்பு உபரி பதிவு செய்யப்பட்டுள்ளது."},
        "hi": {"title": "नया भोजन बचाव सूचीबद्ध", "message": "एक नया भोजन बचाव अधिशेष पोस्ट किया गया है।"},
    },
    "OFFER_RECEIVED": {
        "en": {"title": "Rescue Offer Received ⚡", "message": "You have received a new food rescue dispatch offer. Respond before the countdown ends."},
        "ta": {"title": "மீட்பு வாய்ப்பு வந்துள்ளது ⚡", "message": "உங்களுக்கு புதிய உணவு மீட்பு வாய்ப்பு வந்துள்ளது. காலக்கெடு முடிவதற்குள் பதிலளிக்கவும்."},
        "hi": {"title": "बचाव प्रस्ताव प्राप्त हुआ ⚡", "message": "आपको एक नया खाद्य बचाव प्रस्ताव मिला है। उलटी गिनती समाप्त होने से पहले प्रतिक्रिया दें।"},
    },
    "OFFER_ACCEPTED": {
        "en": {"title": "Rescue Offer Accepted ✓", "message": "A partner organization has accepted the food rescue offer."},
        "ta": {"title": "மீட்பு வாய்ப்பு ஏற்கப்பட்டது ✓", "message": "பங்காளர் அமைப்பு உணவு மீட்பு வாய்ப்பை ஏற்றுக்கொண்டது."},
        "hi": {"title": "बचाव प्रस्ताव स्वीकृत ✓", "message": "एक भागीदार संस्था ने खाद्य बचाव प्रस्ताव स्वीकार कर लिया है।"},
    },
    "WAVE_ESCALATED": {
        "en": {"title": "Dispatch Wave Escalated 🚨", "message": "The rescue dispatch has escalated to the next wave for rapid recovery."},
        "ta": {"title": "அழைப்பு அடுத்த நிலைக்கு முன்னேறியது 🚨", "message": "உணவு மீட்பு அடுத்த நிலைக்கு விரிவாக்கப்பட்டுள்ளது."},
        "hi": {"title": "डिस्पैच वेव एस्केलेट हुई 🚨", "message": "त्वरित वसूली के लिए बचाव डिस्पैच अगली लहर में बढ़ गया है।"},
    },
    "VOLUNTEER_REMATCHED": {
        "en": {"title": "Volunteer Rematched ⚡", "message": "A new volunteer courier has been rematched to maintain the rescue timeline."},
        "ta": {"title": "தன்னார்வலர் மறுஒதுக்கீடு ⚡", "message": "உணவு உரிய நேரத்தில் சேகரிக்கப்படுவதை உறுதி செய்ய புதிய தன்னார்வலர் நியமிக்கப்பட்டுள்ளார்."},
        "hi": {"title": "स्वयंसेवक पुनः नियुक्त ⚡", "message": "समय पर पिकअप सुनिश्चित करने के लिए एक नया स्वयंसेवक फिर से सौंपा गया है।"},
    },
    "VOLUNTEER_ARRIVING": {
        "en": {"title": "Volunteer Arriving 📍", "message": "Your volunteer courier is within 250 meters of the pickup location."},
        "ta": {"title": "தன்னார்வலர் வந்துவிட்டார் 📍", "message": "தன்னார்வலர் பிக்கப் இடத்திற்கு அருகில் (250 மீட்டருக்குள்) வந்துவிட்டார்."},
        "hi": {"title": "स्वयंसेवक पहुंच रहा है 📍", "message": "आपका स्वयंसेवक पिकअप स्थान के 250 मीटर के भीतर है।"},
    },
    "OTP_VERIFIED": {
        "en": {"title": "Pickup Code Verified ✅", "message": "Physical handover OTP has been cryptographically validated."},
        "ta": {"title": "OTP சரிபார்க்கப்பட்டது ✅", "message": "நேரடி ஒப்படைப்பு OTP வெற்றிகரமாக சரிபார்க்கப்பட்டது."},
        "hi": {"title": "OTP सत्यापित ✅", "message": "हैंडओवर OTP सफलतापूर्वक सत्यापित हो गया है।"},
    },
    "FOOD_RECEIVED": {
        "en": {"title": "Food Received at NGO ✓", "message": "The food rescue intake has arrived and has been received by the NGO facility."},
        "ta": {"title": "NGO-ல் உணவு பெறப்பட்டது ✓", "message": "உணவு NGO மையத்தை அடைந்து பெறப்பட்டது."},
        "hi": {"title": "NGO में खाना प्राप्त हुआ ✓", "message": "खाद्य बचाव NGO सुविधा पर पहुंच गया है और प्राप्त हो गया है।"},
    },
    "RESCUE_EXPIRED": {
        "en": {"title": "Rescue Window Expired ⚠️", "message": "The safe consumption window for this donation has ended and it is no longer available."},
        "ta": {"title": "மீட்பு காலக்கெடு முடிந்தது ⚠️", "message": "இந்த உணவின் பாதுகாப்பான பயன்பாட்டு காலக்கெடு முடிந்துவிட்டது."},
        "hi": {"title": "बचाव समय सीमा समाप्त ⚠️", "message": "इस दान के लिए सुरक्षित उपभोग का समय समाप्त हो गया है।"},
    },
    "ADMIN_INTERVENTION": {
        "en": {"title": "Admin Intervention Recorded 🛡️", "message": "An administrative intervention was executed to resolve an operational impediment."},
        "ta": {"title": "நிர்வாக தலையீடு பதிவு செய்யப்பட்டது 🛡️", "message": "செயல்பாட்டு தடையைத் தீர்க்க நிர்வாக நடவடிக்கை எடுக்கப்பட்டுள்ளது."},
        "hi": {"title": "प्रशासनिक हस्तक्षेप दर्ज 🛡️", "message": "परिचालन बाधा को हल करने के लिए प्रशासनिक हस्तक्षेप किया गया।"},
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
# FCM Push Abstraction (HTTP v1 / Firebase Admin SDK)
# ─────────────────────────────────────────────────────────────────────────────

def _get_fcm_access_token() -> Optional[str]:
    """
    Obtains an OAuth 2.0 access token for FCM HTTP v1 messaging.
    Loads service account credentials from GOOGLE_APPLICATION_CREDENTIALS
    or FIREBASE_CREDENTIALS_PATH or ADC.
    Access tokens and private keys are NEVER logged.
    """
    try:
        from google.oauth2 import service_account
        from google.auth.transport.requests import Request
        import google.auth

        scopes = ["https://www.googleapis.com/auth/firebase.messaging"]
        cred_path = getattr(settings, "GOOGLE_APPLICATION_CREDENTIALS", "") or getattr(settings, "FIREBASE_CREDENTIALS_PATH", "")

        credentials = None
        if cred_path and os.path.exists(cred_path):
            credentials = service_account.Credentials.from_service_account_file(cred_path, scopes=scopes)
        elif os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
            credentials, _ = google.auth.default(scopes=scopes)

        if credentials:
            request = Request()
            credentials.refresh(request)
            return credentials.token
    except Exception as e:
        logger.warning(f"[FCM] Failed to acquire OAuth 2.0 access token: {type(e).__name__}")
    return None


def _send_via_firebase_admin(notification: Notification, fcm_token: str, safe_data: dict, db: Session) -> Optional[bool]:
    """
    Attempts to send via Firebase Admin SDK if installed and initialized.
    Returns boolean if handled, or None if Firebase Admin SDK is not available.
    """
    try:
        import firebase_admin
        from firebase_admin import messaging

        if not firebase_admin._apps:
            cred_path = getattr(settings, "GOOGLE_APPLICATION_CREDENTIALS", "") or getattr(settings, "FIREBASE_CREDENTIALS_PATH", "")
            if cred_path and os.path.exists(cred_path):
                from firebase_admin import credentials
                cred = credentials.Certificate(cred_path)
                firebase_admin.initialize_app(cred, {"projectId": settings.FCM_PROJECT_ID} if settings.FCM_PROJECT_ID else None)
            elif settings.FCM_PROJECT_ID:
                firebase_admin.initialize_app(options={"projectId": settings.FCM_PROJECT_ID})
            else:
                return None

        msg = messaging.Message(
            token=fcm_token,
            notification=messaging.Notification(
                title=notification.title,
                body=notification.message,
            ),
            data=safe_data,
            android=messaging.AndroidConfig(
                priority="high",
                notification=messaging.AndroidNotification(
                    channel_id="smart_food_rescue_high_importance",
                    sound="default",
                ),
            ),
        )
        response = messaging.send(msg)
        notification.is_sent = True
        notification.sent_at = _utcnow()
        db.commit()
        logger.info(f"[FCM Admin SDK] Push sent successfully for user_id={notification.user_id}")
        return True
    except ImportError:
        return None
    except Exception as e:
        err_str = str(e).lower()
        if any(term in err_str for term in ["unregistered", "registration-token-not-registered", "invalid-argument", "not_found"]):
            logger.warning(f"[FCM Admin SDK] Token invalid/unregistered for user_id={notification.user_id}. Clearing token.")
            prefs = db.query(NotificationPreference).filter_by(user_id=notification.user_id).first()
            if prefs:
                prefs.fcm_token = None
                prefs.fcm_token_updated_at = _utcnow()
                db.commit()
            return False
        logger.error(f"[FCM Admin SDK] Push dispatch failed: {type(e).__name__}")
        return False


def _send_fcm_http_v1(
    notification: Notification,
    fcm_token: str,
    safe_data: dict,
    db: Session
) -> bool:
    """
    Sends push notification via current FCM HTTP v1 REST API:
    POST https://fcm.googleapis.com/v1/projects/{FCM_PROJECT_ID}/messages:send
    Using OAuth 2.0 Bearer authorization.
    Never logs access tokens or secrets.
    Clears unregistered tokens on 404 / UNREGISTERED.
    """
    import httpx
    project_id = settings.FCM_PROJECT_ID
    if not project_id:
        logger.warning("[FCM HTTP v1] FCM_PROJECT_ID not configured.")
        return False

    access_token = _get_fcm_access_token()
    if not access_token:
        logger.warning("[FCM HTTP v1] Could not acquire OAuth 2.0 access token for FCM dispatch.")
        return False

    url = f"https://fcm.googleapis.com/v1/projects/{project_id}/messages:send"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json; UTF-8",
    }

    payload = {
        "message": {
            "token": fcm_token,
            "notification": {
                "title": notification.title,
                "body": notification.message,
            },
            "data": safe_data,
            "android": {
                "priority": "HIGH",
                "notification": {
                    "channel_id": "smart_food_rescue_high_importance",
                    "sound": "default",
                }
            },
            "apns": {
                "payload": {
                    "aps": {
                        "sound": "default",
                        "badge": 1,
                    }
                }
            }
        }
    }

    with _fcm_lock:
        _fcm_telemetry["fcm_send_attempts"] += 1

    timeout_sec = 5.0
    max_retries = int(getattr(settings, "FCM_MAX_TRANSIENT_RETRIES", 1))

    resp = None
    for attempt in range(max_retries + 1):
        try:
            with httpx.Client(timeout=timeout_sec) as client:
                resp = client.post(url, json=payload, headers=headers)

            if resp.status_code == 200:
                notification.is_sent = True
                notification.sent_at = _utcnow()
                db.commit()
                logger.info(f"[FCM HTTP v1] Push sent successfully for user_id={notification.user_id}")
                return True

            # Transient errors: 429, 500, 502, 503 -> retry with backoff
            if resp.status_code in [429, 500, 502, 503] and attempt < max_retries:
                time.sleep(1.0)
                continue

            break  # Permanent or unrecoverable error
        except (httpx.TimeoutException, httpx.NetworkError) as e:
            if attempt < max_retries:
                time.sleep(1.0)
                continue
            with _fcm_lock:
                _fcm_telemetry["fcm_failures"] += 1
            logger.error(f"[FCM HTTP v1] Push network/timeout error: {e}")
            return False

    with _fcm_lock:
        _fcm_telemetry["fcm_failures"] += 1

    # Handle unregistered / invalid tokens
    is_unregistered = False
    try:
        err_data = resp.json().get("error", {})
        err_status = err_data.get("status", "")
        err_msg = err_data.get("message", "")
        err_details = err_data.get("details", [])
        for d in err_details:
            if d.get("errorCode") in ["UNREGISTERED", "INVALID_ARGUMENT"]:
                is_unregistered = True
                break
        if err_status in ["NOT_FOUND", "INVALID_ARGUMENT"] or "not a valid FCM registration token" in err_msg or "UNREGISTERED" in err_msg:
            is_unregistered = True
    except Exception:
        if resp and resp.status_code in [400, 404]:
            is_unregistered = True

    if is_unregistered:
        logger.warning(f"[FCM HTTP v1] Stale or unregistered token detected for user_id={notification.user_id}. Clearing token.")
        prefs = db.query(NotificationPreference).filter_by(user_id=notification.user_id).first()
        if prefs:
            prefs.fcm_token = None
            prefs.fcm_token_updated_at = _utcnow()
            db.commit()
        return False

    status_code = resp.status_code if resp else "None"
    logger.error(f"[FCM HTTP v1] Push request failed with HTTP {status_code}")
    return False


def _send_fcm_push(notification: Notification, db: Session) -> bool:
    """
    Sends an FCM push notification using current FCM HTTP v1 or Firebase Admin SDK.
    Uses mock adapter if FCM HTTP v1 is not configured.
    SECURITY:
      - Primary transport is FCM HTTP v1 / Firebase Admin SDK with OAuth 2.0 authorization.
      - Legacy FCM server keys are NOT used for primary push delivery.
      - Access tokens, service account keys, and private credentials are NEVER logged.
      - Payload NEVER contains OTP, password, JWT, or private coordinates.
      - Automatically clears stale/unregistered device tokens on FCM failure.
      - FCM failures are isolated and never crash the core transaction.
    """
    has_credentials = bool(
        settings.GOOGLE_APPLICATION_CREDENTIALS or 
        getattr(settings, "FIREBASE_CREDENTIALS_PATH", "") or 
        os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    )
    if not settings.FCM_PROJECT_ID or not has_credentials:
        # Mock/degraded adapter — log only
        logger.info(
            f"[MockFCM] Push recorded: user_id={notification.user_id} "
            f"event_type={notification.event_type} "
            f"title='{notification.title}' "
            f"deep_link={notification.deep_link_data} "
            f"(FCM HTTP v1 credentials not configured — mock adapter)"
        )
        notification.is_sent = True
        notification.sent_at = _utcnow()
        try:
            db.commit()
        except Exception:
            db.rollback()
        return True

    try:
        # Get FCM token for this user
        prefs = db.query(NotificationPreference).filter(
            NotificationPreference.user_id == notification.user_id
        ).first()
        if not prefs or not prefs.fcm_token:
            logger.info(f"[FCM] No registered FCM token for user_id={notification.user_id} — skipping push")
            return False

        # Parse deep link data and strictly sanitize to ensure NO OTP, tokens, or coordinates leak
        raw_data = json.loads(notification.deep_link_data or "{}")
        sensitive_patterns = ["otp", "pass", "token", "secret", "auth", "key", "cred", "pin", "latitude", "longitude", "coord"]
        safe_data = {
            k: str(v) for k, v in raw_data.items()
            if not any(pat in k.lower() for pat in sensitive_patterns)
        }

        # First try Firebase Admin SDK if available
        admin_result = _send_via_firebase_admin(notification, prefs.fcm_token, safe_data, db)
        if admin_result is not None:
            return admin_result

        # Otherwise use FCM HTTP v1 REST API
        return _send_fcm_http_v1(notification, prefs.fcm_token, safe_data, db)

    except Exception as e:
        logger.error(f"[FCM] Push dispatch error for user_id={notification.user_id}: {type(e).__name__}")
        # Failure isolation: never bubble push errors to caller
        return False


# ─────────────────────────────────────────────────────────────────────────────
# Notification Preference Check
# ─────────────────────────────────────────────────────────────────────────────

# Urgent events that bypass preference settings
_ALWAYS_SEND_EVENTS = {
    "VOLUNTEER_ARRIVED", "VOLUNTEER_ARRIVING", "OTP_SMS_SENT", "OTP_SMS_DELIVERED", "OTP_SMS_FAILED",
    "RESCUE_AT_RISK", "ADMIN_ESCALATION", "ADMIN_INTERVENTION", "PICKUP_COMPLETED", "OTP_VERIFIED",
    "RESCUE_REMATCHED_DONOR", "RESCUE_REMATCHED_NGO", "TASK_REASSIGNED_OLD_VOLUNTEER",
    "NEW_TASK_REMATCHED_NEW_VOLUNTEER", "RESCUE_AT_RISK_ADMIN", "VOLUNTEER_REMATCHED",
    "WAVE_ESCALATED", "RESCUE_EXPIRED", "OFFER_RECEIVED", "OFFER_ACCEPTED",
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
            "DONATION_CREATED", "NEW_RESCUE", "AI_ANALYSIS_COMPLETE", "DONATION_ACCEPTED", "OFFER_ACCEPTED",
            "VOLUNTEER_ASSIGNED", "VOLUNTEER_ON_THE_WAY", "FOOD_IN_TRANSIT",
            "DELIVERED_TO_NGO", "FOOD_RECEIVED", "DISTRIBUTION_STARTED", "FALLBACK_STARTED",
            "NEW_TASK", "TASK_CANCELLED", "RESCUE_REMATCHED_DONOR", "RESCUE_REMATCHED_NGO",
            "TASK_REASSIGNED_OLD_VOLUNTEER", "NEW_TASK_REMATCHED_NEW_VOLUNTEER",
            "VOLUNTEER_REMATCHED", "OFFER_RECEIVED",
        },
        "urgent_rescue_alerts": {
            "RESCUE_AT_RISK", "ADMIN_ESCALATION", "ADMIN_INTERVENTION", "RESCUE_UNLIKELY",
            "RESCUE_AT_RISK_ADMIN", "WAVE_ESCALATED", "RESCUE_EXPIRED",
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
    extra_title: Optional[str] = None,
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
        extra_title: Optional title override (e.g. for dynamic urgency titles)

    Returns:
        Created Notification or None if deduplicated/preference-blocked.
    """
    # Deduplication: same event for same user/donation within 60 seconds is suppressed
    from datetime import timedelta
    dedup_key = f"{donation_id}:{event_type}" if donation_id else f"user:{user_id}:{event_type}"
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
        with _fcm_lock:
            _fcm_telemetry["fcm_duplicate_prevented"] += 1
        logger.info(f"[Notification] Deduplicated event_type={event_type} user_id={user_id} dedup_key={dedup_key}")
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

    # Validate related_donation_id existence to prevent foreign key violations on PostgreSQL/SQLite
    valid_donation_id = donation_id
    if donation_id is not None:
        exists = db.query(FoodDonation.id).filter(FoodDonation.id == donation_id).first()
        if not exists:
            valid_donation_id = None

    notification = Notification(
        user_id=user_id,
        title=extra_title or content["title"],
        message=extra_message or content["message"],
        type=_event_to_type(event_type),
        related_donation_id=valid_donation_id,
        event_type=event_type,
        deep_link_data=_build_deep_link_data(event_type, donation_id),
        dedup_key=dedup_key,
        is_read=False,
        is_sent=False,
    )
    db.add(notification)
    db.commit()
    db.refresh(notification)

    # Broadcast to active SSE listeners
    broadcast_user_event(user_id, {
        "id": notification.id,
        "title": notification.title,
        "message": notification.message,
        "type": notification.type,
        "event_type": notification.event_type,
        "related_donation_id": notification.related_donation_id,
        "created_at": notification.created_at.isoformat() if notification.created_at else None,
        "deep_link_data": notification.deep_link_data,
        "is_read": notification.is_read,
    })

    # Attempt FCM push
    if send_push:
        _send_fcm_push(notification, db)

    return notification


def _event_to_type(event_type: str) -> str:
    """Maps event type to notification type category."""
    if "EMERGENCY" in event_type or "CRITICAL" in event_type or "ADMIN_ESCALATION" in event_type or "WAVE_ESCALATED" in event_type:
        return "emergency"
    if "RESCUE_AT_RISK" in event_type or "OTP_SMS_FAILED" in event_type or "FALLBACK" in event_type or "EXPIRED" in event_type or "INTERVENTION" in event_type:
        return "alert"
    if "ASSIGNMENT" in event_type or "VOLUNTEER" in event_type or "PICKUP" in event_type or "OTP" in event_type or "TASK" in event_type:
        return "assignment"
    if "DONATION" in event_type or "NGO" in event_type or "DISTRIBUTION" in event_type or "OFFER" in event_type or "RESCUE" in event_type or "FOOD" in event_type:
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

    # Broadcast to active SSE listeners
    broadcast_user_event(user_id, {
        "id": notification.id,
        "title": notification.title,
        "message": notification.message,
        "type": notification.type,
        "event_type": getattr(notification, "event_type", None),
        "related_donation_id": notification.related_donation_id,
        "created_at": notification.created_at.isoformat() if notification.created_at else None,
        "is_read": notification.is_read,
    })

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
