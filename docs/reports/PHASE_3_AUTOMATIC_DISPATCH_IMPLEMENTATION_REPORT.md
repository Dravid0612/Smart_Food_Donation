# Phase 3 Implementation Report: Three-Wave Automatic Dispatch

## 1. Overview & Architectural Principle
In Phase 3, the food rescue system was transformed from a passive task-selection model into a **proactive, automated three-wave dispatch engine**.
All dispatch functionality strictly reuses the existing `backend/app/services/proactive_dispatch_service.py` and the `BackgroundUrgencyMonitor` background worker without creating any duplicate dispatch engines.

The platform operates under the core constraint: **Zero-cash, hyper-local, community and NGO powered**. No commercial fleets, no payment gateways, and no third-party delivery dependencies exist.

---

## 2. Three-Wave Dispatch Lifecycle

```
                   [ SURPLUS DONATION CREATED / ERW CALCULATED ]
                                        │
                                        ▼
                  Live Biological ERW Recalculation
                                        │
             ┌──────────────────────────┴──────────────────────────┐
             ▼                                                     ▼
      [ APPROACHING ]                                       [ CRITICAL ]
   (Remaining Window > 45m)                             (Remaining Window ≤ 45m)
             │                                                     │
             ▼                                                     ▼
    WAVE 1: NGO SELF-PICKUP                              WAVE 3: CRITICAL EMERGENCY
   • Nearest verified NGOs (small radius)               • Simultaneous alert to:
   • 7 Data points in advisory alert                      - Rapid-response NGOs / Shelters
   • NGO action:                                          - Eligible on-call volunteers
     - ACCEPT (self_pickup)                             • Instant Admin Escalation record
       → Status: ngo_accepted                           • Short timeout (5 mins)
       → Courier bypassed (no volunteer dispatched)
     - PASS (reject) / TIMEOUT (15 mins)
       → Cascades to Wave 2
             │
             ▼
    WAVE 2: VOLUNTEER COURIER SUPPORT
   • Triggered on Wave 1 timeout, Wave 1 passes,
     or NGO request (`pickup_mode="volunteer_dispatch"`)
   • Strict feasibility hard gates:
     1. Available (`is_active=True`, active tasks < 3)
     2. Eligible (`role="volunteer"`, not restricted)
     3. Location feasible (radius ≤ 25km)
     4. Capacity feasible (`carrying_capacity >= quantity`)
     5. Time feasible (`feasibility["is_feasible"] == True`)
   • Multi-factor ranking:
     Buffer (35%) + Distance (25%) + Reliability (25%) + Response Speed (15%)
     *Never dispatched on distance alone*
   • Volunteer action:
     - ACCEPT → Status: in_transit / assigned
     - PASS / TIMEOUT (10 mins) → Cascades to Wave 3
```

---

## 3. Detailed Component Implementation

### 3.1 Proactive Dispatch Service (`proactive_dispatch_service.py`)
- **Authoritative ERW Recalculation:** Before evaluating any wave, biological decay is recalculated using `FoodRescueWindowService.calculate_rescue_window(...)`.
- **Status & Acceptance Guards:** If a donation is already accepted (`ngo_accepted`, `in_transit`, `completed`, `cancelled`, etc.), dispatch halts immediately.
- **Active Offer Deduplication:** `MatchOffer` records with `status == "offered"` are checked. If an active unresponded offer exists, duplicate dispatches are prevented.
- **Cooldown Enforcement:** Dedicated wave cooldowns (`WAVE_COOLDOWNS = {1: 900, 2: 600, 3: 300}`) prevent candidate alert spamming.
- **Wave 1 Advisory Message:** `format_proactive_alert_message` includes all 7 mandatory data points:
  1. Food item description
  2. Food category
  3. Quantity (clean integer formatting, e.g. `35 Meals`)
  4. Distance in kilometers
  5. Authoritative remaining rescue window minutes
  6. Pickup address and coordinates
  7. Biological safety & AI inspection advisory
- **Wave 2 Feasible Volunteer Search (`find_and_rank_feasible_volunteers`):**
  - Hard capacity gate: `v.carrying_capacity >= donation.quantity`.
  - Hard time feasibility: Calculates travel time, prep buffer (10m), intake buffer (10m), ensuring volunteer arrival precedes ERW expiration.
  - Multi-attribute composite score:
    $$\text{Score} = 0.35 \times \text{BufferScore} + 0.25 \times \text{DistanceScore} + 0.25 \times \text{ReliabilityScore} + 0.15 \times \text{ResponseScore}$$
- **Wave 3 Emergency Escalation:**
  - Evaluates both rapid-response NGOs and feasible volunteers simultaneously.
  - Generates immediate admin escalation audit record and notification.
  - Expedites intake buffer (5m prep / 5m intake) to maximize survival rate.
- **Cascading Timeout Engine (`check_and_escalate_unresponsive_waves`):**
  - Identifies expired unresponded offers (`status == "offered"` and `elapsed > timeout`).
  - Marks expired offers as `status = "expired"`.
  - Automatically triggers escalation to the next wave (Wave 1 $\to$ 2 $\to$ 3 $\to$ Admin Escalation).

### 3.2 Route Integration (`donations.py` & `volunteers.py`)
- **Donation Rejection / Pass (`POST /api/donations/{id}/reject`):**
  - Permitted for NGOs and Volunteers (`require_role(["ngo", "volunteer", "admin"])`).
  - Locates candidate's active `MatchOffer`, updates `status = "rejected"`, records `responded_at` and `response_time_seconds`.
  - If all active wave candidates pass, automatically forces evaluation of the next wave.
- **Courier Request (`POST /api/donations/{id}/request-volunteer`):**
  - Switches donation `pickup_mode = "volunteer_dispatch"`.
  - Calls `dispatch_proactive_alerts(force_dispatch=True)` to alert Wave 2 volunteers immediately.
- **Volunteer Assignment & Concurrency (`volunteers.py`):**
  - Winning volunteer acceptance marks their `MatchOffer.status = "accepted"` and logs `response_time_seconds`.
  - Automatically cancels all competing volunteer offers (`MatchOffer.status = "cancelled"`).

---

## 4. Verification & Testing

### 4.1 Dedicated Phase 3 Test Suite (`test_three_wave_dispatch.py`)
1. **`test_wave1_ngo_self_pickup_dispatch`**: Verifies Wave 1 alert generation, 7 advisory fields, `MatchOffer(wave_number=1, candidate_type="ngo")`, and verified NGO acceptance without volunteer assignment.
2. **`test_wave1_pass_escalates_to_wave2_volunteer`**: Verifies Wave 1 NGO pass records `response_time_seconds` and triggers Wave 2 volunteer dispatch using capacity and buffer gating.
3. **`test_wave2_volunteer_capacity_and_buffer_gating`**: Confirms volunteers with inadequate capacity (`10 < 35`) or insufficient time buffer are rejected, proving volunteers are never dispatched on distance alone.
4. **`test_wave3_critical_emergency_dispatch`**: Confirms donations with $<45$ minutes remaining trigger simultaneous emergency NGO + volunteer dispatch and create an immediate Admin Escalation alert.
5. **`test_active_offer_deduplication_and_cooldown`**: Confirms that duplicate dispatch runs do not generate duplicate offers while active unresponded offers exist or cooldown is active.
6. **`test_unresponsive_wave_cascade`**: Confirms background urgency cascade expires unresponsive offers and advances waves automatically.
7. **`test_rescue_window_ended_blocks_dispatch`**: Confirms zero alerts are dispatched when ERW has elapsed ($\le 0$ mins).

**Result:** 7 / 7 tests passed (100% pass rate).
