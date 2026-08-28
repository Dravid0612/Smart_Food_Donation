"""
FoodSafetyCheckService — Smart Food Rescue
===========================================
Pre-publish donor screening declaration & food suitability assessment.

GOAL:
  - Donor self-declaration of food suitability (Screening).
  - NOT a laboratory/chemical certification of food safety.
  - Conservative, non-punitive screening that prevents publication of visibly unsafe,
    contaminated, unhygienic, or non-human consumption food.
  - Integrates with Food Knowledge Rules and AI Visual Assessment.
"""

import json
import logging
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger("smart_food_rescue.food_safety")

SAFETY_CHECK_VERSION = "2026.1"

# Standard 5 screening declaration definitions with trilingual prompts
DECLARATION_DEFINITIONS = [
    {
        "key": "human_consumption",
        "aliases": ["prepared_for_human_consumption", "is_human_food"],
        "required_value": True,
        "title_en": "Prepared for human consumption",
        "title_ta": "மனித பயன்பாட்டிற்காக தயாரிக்கப்பட்டது",
        "title_hi": "मानव उपभोग के लिए तैयार किया गया",
        "fail_reason_en": "Food must be originally prepared and intended for human consumption.",
        "fail_reason_ta": "உணவு முதலில் மனித நுகர்வுக்காக தயாரிக்கப்பட்டதாக இருக்க வேண்டும்.",
        "fail_reason_hi": "भोजन मूल रूप से मानव उपभोग के लिए तैयार और अभिप्रेत होना चाहिए।"
    },
    {
        "key": "hygienic_handling",
        "aliases": ["handled_hygienically", "hygienic_preparation"],
        "required_value": True,
        "title_en": "Handled and prepared hygienically",
        "title_ta": "சுகாதாரமாக கையாளப்பட்டு தயாரிக்கப்பட்டது",
        "title_hi": "स्वच्छता से संभाला और तैयार किया गया",
        "fail_reason_en": "Food must have been prepared and handled using clean utensils and standard hygiene.",
        "fail_reason_ta": "சுத்தமான பாத்திரங்கள் மற்றும் சுகாதார நடைமுறைகளுடன் உணவு கையாளப்பட்டிருக்க வேண்டும்.",
        "fail_reason_hi": "भोजन को साफ बर्तनों और मानक स्वच्छता के साथ तैयार और संभाला जाना चाहिए।"
    },
    {
        "key": "appropriate_storage",
        "aliases": ["stored_appropriately", "proper_storage"],
        "required_value": True,
        "title_en": "Stored appropriately for this food type",
        "title_ta": "இந்த உணவு வகைக்கு ஏற்றவாறு சேமிக்கப்பட்டது",
        "title_hi": "इस भोजन के प्रकार के लिए उचित रूप से संग्रहीत",
        "fail_reason_en": "Food must have been maintained in suitable storage conditions (e.g. covered, temperature appropriate).",
        "fail_reason_ta": "உணவு தகுந்த சேமிப்பு நிலையில் வைக்கப்பட்டிருக்க வேண்டும் (எ.கா. மூடப்பட்டு, வெப்பநிலை பராமரிக்கப்பட்டு).",
        "fail_reason_hi": "भोजन को उपयुक्त भंडारण स्थितियों में बनाए रखा जाना चाहिए (उदा. ढका हुआ, तापमान उपयुक्त)।"
    },
    {
        "key": "contamination_free",
        "aliases": ["no_contamination", "free_from_contamination", "exposed_to_contamination_no"],
        "required_value": True,
        "title_en": "Free from known contamination or pests",
        "title_ta": "தெரிந்த மாசுபாடு அல்லது பூச்சிகள் இல்லாதது",
        "title_hi": "ज्ञात संदूषण या कीड़ों से मुक्त",
        "fail_reason_en": "Food must not have been exposed to pests, chemical contaminants, or unsafe foreign objects.",
        "fail_reason_ta": "உணவு பூச்சிகள், இரசாயனங்கள் அல்லது பாதுகாப்பற்ற வெளிப்பொருட்களுக்கு வெளிப்படுத்தப்பட்டிருக்கக்கூடாது.",
        "fail_reason_hi": "भोजन कीटों, रासायनिक संदूषकों या असुरक्षित बाहरी वस्तुओं के संपर्क में नहीं आया होना चाहिए।"
    },
    {
        "key": "suitable_condition",
        "aliases": ["visibly_suitable", "good_sensory_condition", "suitable_for_donation"],
        "required_value": True,
        "title_en": "Visibly suitable for donation based on current condition",
        "title_ta": "தற்போதைய நிலையின் அடிப்படையில் நன்கொடைக்கு ஏற்றது",
        "title_hi": "वर्तमान स्थिति के आधार पर दान के लिए उपयुक्त",
        "fail_reason_en": "Food must not show visible signs of spoilage, foul odor, abnormal discoloration, or mold.",
        "fail_reason_ta": "உணவில் கெட்டுப்போன அறிகுறிகள், துர்நாற்றம் அல்லது நிறமாற்றம் இருக்கக்கூடாது.",
        "fail_reason_hi": "भोजन में खराब होने के दृश्य लक्षण, दुर्गंध या असामान्य रंग नहीं होना चाहिए।"
    }
]


class FoodSafetyCheckService:
    """
    Validates pre-publish donor declarations and computes holistic advisory suitability.
    """

    @staticmethod
    def normalize_answers(raw_answers: Optional[Dict[str, Any]]) -> Dict[str, bool]:
        """
        Normalizes various answer dictionary key formats into canonical boolean declaration mapping.
        """
        if not raw_answers:
            return {}

        normalized = {}
        for decl in DECLARATION_DEFINITIONS:
            canonical_key = decl["key"]
            all_keys = [canonical_key] + decl.get("aliases", [])

            val = None
            for k in all_keys:
                if k in raw_answers:
                    raw_val = raw_answers[k]
                    if isinstance(raw_val, bool):
                        val = raw_val
                    elif isinstance(raw_val, str):
                        val = raw_val.strip().lower() in ["true", "yes", "1", "passed", "y"]
                    elif isinstance(raw_val, (int, float)):
                        val = bool(raw_val)
                    break

            if val is not None:
                normalized[canonical_key] = val

        return normalized

    @staticmethod
    def validate_declaration(
        raw_answers: Optional[Dict[str, Any]],
        language: str = "en"
    ) -> Dict[str, Any]:
        """
        Evaluates donor safety checklist answers against standard suitability criteria.

        Returns:
            Dict with:
                - is_eligible: bool
                - status: "PASSED" or "UNSAFE_DECLARATION"
                - failed_declarations: List[str]
                - warning_message: Optional[str]
                - guidance: Optional[str]
                - safety_check_version: str
                - disclaimer: str
        """
        lang = (language or "en").lower()
        if not raw_answers:
            # If no answers provided, return failure requiring completion
            return {
                "is_eligible": False,
                "status": "UNSAFE_DECLARATION",
                "safety_check_version": SAFETY_CHECK_VERSION,
                "failed_declarations": [d["key"] for d in DECLARATION_DEFINITIONS],
                "warning_message": (
                    "Please complete the food safety self-check before publishing your donation."
                    if lang == "en" else
                    "நன்கொடையை வெளியிடுவதற்கு முன் உணவு பாதுகாப்பு சுய சரிபார்ப்பை பூர்த்தி செய்யவும்."
                    if lang == "ta" else
                    "दान प्रकाशित करने से पहले कृपया खाद्य सुरक्षा स्व-जांच पूरी करें।"
                ),
                "guidance": "All 5 declarations must be confirmed affirmative before publishing.",
                "disclaimer": "Screening declaration only. This does not certify microbiological food safety."
            }

        normalized = FoodSafetyCheckService.normalize_answers(raw_answers)
        failed_keys = []
        fail_reasons = []

        for decl in DECLARATION_DEFINITIONS:
            key = decl["key"]
            expected = decl["required_value"]
            actual = normalized.get(key)

            if actual != expected:
                failed_keys.append(key)
                if lang == "ta":
                    fail_reasons.append(decl.get("fail_reason_ta", decl["fail_reason_en"]))
                elif lang == "hi":
                    fail_reasons.append(decl.get("fail_reason_hi", decl["fail_reason_en"]))
                else:
                    fail_reasons.append(decl["fail_reason_en"])

        is_eligible = len(failed_keys) == 0

        if not is_eligible:
            warning_msg = (
                "This food may not be suitable for donation based on the information provided."
                if lang == "en" else
                "வழங்கப்பட்ட தகவலின் அடிப்படையில் இந்த உணவு நன்கொடைக்கு ஏற்றதாக இருக்காது."
                if lang == "ta" else
                "दी गई जानकारी के आधार पर यह भोजन दान के लिए उपयुक्त नहीं हो सकता है।"
            )
            guidance = (
                f"Issues flagged: {'; '.join(fail_reasons)}"
                if lang == "en" else
                f"கண்டறியப்பட்ட காரணங்கள்: {'; '.join(fail_reasons)}"
                if lang == "ta" else
                f"पहचानी गई समस्याएं: {'; '.join(fail_reasons)}"
            )
            return {
                "is_eligible": False,
                "status": "UNSAFE_DECLARATION",
                "safety_check_version": SAFETY_CHECK_VERSION,
                "failed_declarations": failed_keys,
                "warning_message": warning_msg,
                "guidance": guidance,
                "disclaimer": "Screening declaration only. This does not certify microbiological food safety."
            }

        return {
            "is_eligible": True,
            "status": "PASSED",
            "safety_check_version": SAFETY_CHECK_VERSION,
            "failed_declarations": [],
            "warning_message": None,
            "guidance": "Donor declaration confirms initial food suitability for rescue matching.",
            "disclaimer": "Screening declaration only. This does not certify microbiological food safety."
        }


food_safety_check_service = FoodSafetyCheckService()
