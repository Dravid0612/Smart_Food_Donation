# Proactive Time-Critical Food Rescue Alert & NGO Dispatch System
## Final Implementation & Verification Report

---

### 1. Executive Summary & Core Philosophy

The **Smart Food Rescue** platform has been enhanced beyond passive advisory window display. Rather than merely presenting `"Your food is about to expire"`, the system now **proactively coordinates, alerts, and dispatches feasible nearby rescue partners** the moment surplus food approaches time-critical operational thresholds.

> **Operational Distinction**: The platform does **not** certify absolute food safety or predict microbiological expiry. Instead, it computes an **Advisory Rescue Window** ($\text{Food Rules} + \text{Preparation Time} + \text{Storage History} + \text{AI Visual Condition}$) and triggers **Proactive Response Actions** before the window closes.

---

### 2. Time-Critical Operational Urgency Matrix

| Urgency State | Remaining Advisory Window | Platform Behavior & Partner Outreach |
| :--- | :--- | :--- |
| **`FRESH`** | $> 180$ min ($> 3$ hours) | **Normal Operations**: Visible in normal browse feed. No emergency push notifications. |
| **`APPROACHING`** | $120 - 180$ min ($2 - 3$ hours) | **Awareness State**: Donor dashboard displays progress reassurance; system pre-evaluates eligible NGO matching pools. |
| **`URGENT`** | $45 - 120$ min ($45\text{m} - 2\text{h}$) | **Proactive Targeted Dispatch**: Wave 1 match offers sent to top 3 feasible NGOs. Donor reassured that partners are being contacted. |
| **`CRITICAL`** | $1 - 45$ min ($< 45\text{m}$) | **Emergency Shortlist Dispatch**: Wave 2 alerts sent to next 5 feasible NGOs with shortened 5-minute response timeouts. |
| **`RESCUE_WINDOW_ENDED`** | $\le 0$ min | **Halt Dispatch**: Proactive dispatch stops immediately. Pending match offers cancelled. Food marked `expired`. |

---

### 3. Hard Feasibility Over Proximity Guarantee

A fundamental architectural rule implemented in `ProactiveDispatchService.find_and_rank_feasible_ngos()` is that **Feasibility strictly overrides Proximity**:

$$\text{Estimated Transit Time} = \max\left(8\text{ min}, \text{Distance (km)} \times 3.0\right)$$
$$\text{Total Required Rescue Time} = \text{Pickup Time (15m)} + \text{Transit Time} + \text{NGO Intake Time (10m)}$$

$$\text{Feasibility Condition}: \quad \text{Total Required Rescue Time} \le \text{Remaining Rescue Window}$$

An NGO located 1.2 km away requiring 33 minutes cannot rescue food with only 25 minutes remaining; whereas an eligible partner capable of completing within the window is prioritized.

#### Hard Gates Enforced:
1. **Verification Gate**: `ngo.is_verified == True`
2. **Operational Hours Gate**: NGO must be currently open based on daily schedule (`is_ngo_open_now`).
3. **Capacity Gate**: `ngo.capacity_meals - current_daily_intake >= donation.quantity`
4. **Demand Match Gate**: NGO must accept the food category or broad cooked meals.
5. **Time Feasibility Gate**: $\text{Remaining Buffer} \ge 0$.

---

### 4. Controlled Wave Dispatch & Anti-Spam Safeguards

To prevent community fatigue and notification chaos, broadcasts to every NGO in the city are prohibited:

1. **Wave 1 (Top 3 Feasible NGOs)**:
   - Initial targeted dispatch upon entering `URGENT` or `CRITICAL`.
   - Timeout: 10 minutes (Urgent) or 5 minutes (Critical).
2. **Wave 2 (Next 5 Feasible NGOs)**:
   - Automatically triggered if Wave 1 times out with no acceptance.
3. **Wave 3 (Admin Critical Intervention)**:
   - If Wave 2 times out or zero feasible NGOs remain for critical surplus, the system escalates directly to administrators with a `RescueIssueReport` (`category="other"`, `severity="CRITICAL"`).
4. **Deduplication & Cooldown**:
   - Event Key: `(donation_id, urgency_state)`.
   - Cooldown period: 15 minutes between alerts for unchanged urgency states.
   - Immediate dispatch override when urgency state increases (`FRESH` $\rightarrow$ `URGENT` $\rightarrow$ `CRITICAL`).

---

### 5. Atomic Acceptance & 409 Conflict Handling

To eliminate race conditions when multiple NGOs attempt to claim the same time-critical surplus simultaneously:

```python
# Atomic row-level lock in ProactiveDispatchService.process_atomic_ngo_acceptance
locked_donation = db.query(FoodDonation).filter(
    FoodDonation.id == donation_id
).with_for_update().first()

if locked_donation.status != "pending":
    raise HTTPException(
        status_code=409,
        detail="Donation has already been accepted by another rescue partner."
    )
```
- The first NGO acquires the lock, updates status to `accepted`, and records exact response time (`response_time_seconds`).
- All other active match offers for that donation are atomically marked `cancelled`.
- Secondary accept attempts instantly receive HTTP `409 Conflict`.

---

### 6. Trilingual Proactive Notification Localization

Authoritative localized notifications are provided across English, Tamil (`தமிழ்`), and Hindi (`हिन्दी`):

| Role | Language | Sample Alert Format |
| :--- | :--- | :--- |
| **Donor** | **EN** | `🕒 Rescue Update: Your donation 'Cooked Biryani' is becoming time-critical (~90 min rescue window remaining). We are actively contacting feasible nearby rescue partners.` |
| **Donor** | **TA** | `🕒 மீட்பு புதுப்பிப்பு: உங்கள் 'Cooked Biryani' நன்கொடைக்கான மீட்பு நேரம் குறைகிறது (~90 நிமிடம் மீதமுள்ளது). அருகிலுள்ள தகுதியான மீட்பு அமைப்புகளை தீவிரமாக தொடர்பு கொள்கிறோம்.` |
| **Donor** | **HI** | `🕒 बचाव अपडेट: आपके दान 'Cooked Biryani' के लिए बचाव समय कम हो रहा है (~90 मिनट शेष)। हम निकटतम व्यवहार्य बचाव भागीदारों से संपर्क कर रहे हैं।` |
| **NGO** | **EN** | `⚡ Urgent Rescue Opportunity: 50 Meals of Cooked Food in Indiranagar (~90 min rescue window). Can your organization accept?` |
| **NGO** | **TA** | `⚡ அவசர உணவு மீட்பு வாய்ப்பு: Indiranagar பகுதியில் 50 உணவுகள் (~90 நிமிடம் மீட்பு நேரம்). உங்கள் தொண்டு நிறுவனம் ஏற்க முடியுமா?` |
| **NGO** | **HI** | `⚡ तत्काल भोजन बचाव अवसर: Indiranagar में 50 भोजन (~90 मिनट बचाव समय)। क्या आपका संगठन स्वीकार कर सकता है?` |

---

### 7. Verification & Test Evidence

#### Automated Pytest Suite (`backend/tests/test_proactive_dispatch.py`):
```text
tests/test_proactive_dispatch.py::test_01_fresh_donation_normal_operations PASSED
tests/test_proactive_dispatch.py::test_02_approaching_urgency_awareness_alert PASSED
tests/test_proactive_dispatch.py::test_03_urgent_transition_targeted_feasible_ngo_dispatch PASSED
tests/test_proactive_dispatch.py::test_04_critical_transition_emergency_shortlist_alert PASSED
tests/test_proactive_dispatch.py::test_05_rescue_window_ended_stops_dispatch_and_inactivates PASSED
tests/test_proactive_dispatch.py::test_06_alert_deduplication_and_cooldown PASSED
tests/test_proactive_dispatch.py::test_07_feasibility_hard_gate_overrides_closer_infeasible_ngo PASSED
tests/test_proactive_dispatch.py::test_08_capacity_and_closed_hard_gates_filter_ineligible_ngos PASSED
tests/test_proactive_dispatch.py::test_09_multi_wave_escalation_on_timeout PASSED
tests/test_proactive_dispatch.py::test_10_atomic_ngo_acceptance_lock_and_409_conflict PASSED
tests/test_proactive_dispatch.py::test_11_privacy_safe_location_masking PASSED
tests/test_proactive_dispatch.py::test_12_trilingual_proactive_alert_formatting PASSED
tests/test_proactive_dispatch.py::test_13_custom_food_conservative_proactive_rescue PASSED
tests/test_proactive_dispatch.py::test_14_api_monitor_urgency_and_dispatch_status_endpoints PASSED
============================== 14 passed in 3.78s ==============================
```

#### Flutter Mobile Test Suite (`mobile/test/proactive_rescue_alert_test.dart`):
```text
Proactive Time-Critical Rescue Alerts - Localization & Text Tests:
  ✓ English translations for proactive alert reassurance are present and non-empty
  ✓ Tamil translations for proactive alerts are natural and complete
  ✓ Hindi translations for proactive alerts are accurate and clear
Proactive Rescue Model & Filtering Tests:
  ✓ urgent and critical criteria correctly filter pending donations
All 4 tests passed!
```

#### Full Mobile Suite (`flutter test`):
```text
67 tests passed!
```

#### Code Quality Analysis (`flutter analyze`):
```text
Analyzing mobile...
No issues found! (ran in 3.0s)
```
