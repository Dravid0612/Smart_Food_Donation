# PHASE 4 — NGO SELF-PICKUP / VOLUNTEER BRANCH
## Technical Architecture, Concurrency Design, and Verification Report

**System Version:** `2.5.0-Production-Ready`  
**Execution Date:** 2026-09-25  
**Document Identifier:** `PHASE_4_SELF_PICKUP_VOLUNTEER_BRANCH_REPORT.md`  
**Overall Status:** **✅ VERIFIED COMPLETE (100% Tests Green, Strict Concurrency & Role Isolation)**  

---

### 1. Executive Overview & Branching Architecture

Phase 4 establishes an authoritative, deterministic branch between **Direct NGO Self-Pickup** and **Community Volunteer Courier Rescue**.

```
                           FOOD DONATION CREATED
                                     │
                        ERW / FEASIBILITY EVALUATED
                                     │
                             WAITING FOR MATCH
                                     │
                        ┌────────────┴────────────┐
                        │ Can NGO Collect Direct? │
                        └────────────┬────────────┘
                                     │
                     ┌───────────────┴───────────────┐
                     ▼                               ▼
                 [ YES ]                          [ NO ]
                    │                                │
            NGO SELF-PICKUP                  VOLUNTEER RESCUE
                    │                                │
      ┌───────────────────────────┐    ┌───────────────────────────┐
      │ • pickup_mode=self_pickup │    │ • pickup_mode=vol_dispatch│
      │ • Volunteers Bypassed     │    │ • Wave 2 Courier Dispatch │
      │ • Direct OTP Verification │    │ • Volunteer Assignment    │
      │ • NGO Delivers to Shelter │    │ • Courier Delivers to NGO │
      └─────────────┬─────────────┘    └─────────────┬─────────────┘
                    │                                │
                    │   (If Breakdown / Shortage)    │
                    └───► POST /request-volunteer ───┘
```

The system prevents duplicate or unnecessary courier dispatches when a receiving NGO has its own transport resources, while maintaining an immediate fallback path (`POST /api/donations/{id}/request-volunteer`) that promotes the rescue to Wave 2 community volunteer dispatch if the NGO encounters driver shortage or vehicle breakdown.

---

### 2. Entity Representation & Relationship Integrity

In accordance with project requirements, the relationship models are strictly preserved:
- **NGO Entity:** Stored in the `ngos` table with primary key `ngos.id` and foreign key `ngos.user_id -> users.id`.
- **MatchOffer Model:** Uses `candidate_type = "ngo"` and `candidate_id = user_id` (ForeignKey to `users.id`). **No explicit `ngo_id` column is assumed on `MatchOffer`.**
- **FoodDonation Model:** Holds `assigned_ngo_id -> ngos.id` and `pickup_mode -> VARCHAR(30)` (`"self_pickup"` or `"volunteer_dispatch"`).
- **VolunteerAssignment Model:** Manages courier dispatches between `FoodDonation` and `User` (volunteer).

---

### 3. The 9-Step Authoritative NGO Acceptance Pipeline

Every acceptance call (via `POST /api/donations/{donation_id}/accept` or background services) executes the unified 9-step atomic sequence:

```
[ Step 1: Verify Authenticated NGO ]
       │  • Role check: current_user.role in ['ngo', 'admin']
       │  • Database check: NGO profile must exist, be verified (is_verified=True),
       │    and not restricted (admin_action_status != 'RESTRICTED').
       ▼
[ Step 2: Verify Offer Belongs to This NGO ]
       │  • If offer_id provided: verify candidate_type='ngo', candidate_id=user.id,
       │    and status in ['offered', 'accepted'].
       │  • If offer_id omitted: verify current NGO has an offer or reject with 403 if
       │    active offers are currently targeted to other shortlisted organizations.
       ▼
[ Step 3: Lock Donation Row (Concurrency Lock) ]
       │  • FoodDonation.id == donation_id with with_for_update() to serialize
       │    concurrent transactions at the database layer.
       ▼
[ Step 4: Recalculate ERW at Execution Time ]
       │  • ProactiveDispatchService.evaluate_donation_urgency(reference_time=now)
       │  • If ERW ended (remaining_minutes <= 0 or status == 'expired'):
       │    reject with HTTP 400 Bad Request.
       ▼
[ Step 5: Verify Donation Still Available ]
       │  • Enforce status == 'pending'.
       │  • If already accepted, cancelled, or expired: reject with HTTP 409 Conflict.
       ▼
[ Step 6: Accept Offer & Reserve Capacity ]
       │  • Update winning MatchOffer to status='accepted', record response_time_seconds.
       │  • Capacity check: verify NGO current_capacity >= donation.quantity.
       │  • Deduct current_capacity atomically.
       │  • Set donation.assigned_ngo_id = ngo.id and donation.pickup_mode = pickup_mode.
       ▼
[ Step 7: Cancel Competing Active Offers ]
       │  • Find all other MatchOffer rows for this donation with status='offered'.
       │  • Mark them status='cancelled' and set responded_at=now.
       ▼
[ Step 8: Create DonationHistory via Central State Machine ]
       │  • transition_donation_status(db, donation, 'accepted', changed_by, caller_role, remarks)
       │  • Automatically creates and flushes immutable DonationHistory row.
       ▼
[ Step 9: Notify Donor & Log Audit Event ]
          • Send real-time notification to donor detailing pickup mode.
          • Record security AuditLog entry with action='donation_accepted'.
```

---

### 4. Concurrency & Courier Branch Safeguards

#### 4.1 Strict Concurrency Safety
Under high concurrent traffic, two NGOs attempting to accept the exact same rescue are safely arbitrated:
1. Both requests begin a database transaction.
2. The database row lock `FoodDonation.with_for_update()` forces one transaction to proceed first.
3. The winner transitions `donation.status` from `'pending'` to `'accepted'` and commits.
4. When the second transaction unblocks, `donation.status` is checked immediately under the lock. It sees `status == 'accepted'` and immediately raises:
   ```json
   HTTP 409 Conflict: "This donation has already been accepted by another organization or is no longer available (status: 'accepted')."
   ```
5. All competing offers are cancelled, preventing stale notifications or duplicate assignments.

#### 4.2 Courier Branch Guarding
When `donation.pickup_mode == "self_pickup"`:
- `POST /api/volunteers/assignments`: Rejects assignment creation with `HTTP 400 Bad Request` ("This donation is scheduled for direct NGO self-pickup. Volunteer courier assignment is not permitted unless the NGO requests volunteer support.").
- `POST /api/volunteers/assignments/{id}/accept`: Rejects acceptance with `HTTP 400 Bad Request`.
- Wave 2 volunteer proactive alerts are strictly bypassed.

#### 4.3 Direct NGO Self-Pickup Handover Flow
An NGO conducting self-pickup operates with full first-party capability:
1. **Direct OTP Verification (`POST /api/donations/{id}/pickup-otp/verify`):** Verified NGO driver presents credentials and inputs donor's 6-digit pickup OTP. Status transitions to `'collected'`.
2. **Facility Arrival (`POST /api/donations/{id}/deliver`):** NGO reports arrival at shelter facility. Status transitions to `'delivered'`.
3. **Beneficiary Distribution (`POST /api/donations/{id}/distribution`):** NGO records meal distribution count and notes. Status transitions to `'completed'`.

---

### 5. Implementation Modifications

| Component | File Path | Core Modifications |
|---|---|---|
| **Proactive Dispatch Service** | [`backend/app/services/proactive_dispatch_service.py`](file:///backend/app/services/proactive_dispatch_service.py) | • Hardened `process_atomic_ngo_acceptance` with 9-step pipeline.<br>• Added candidate verification matching `candidate_type="ngo"` and `candidate_id=user_id`.<br>• Added offer ownership check (403 if offer belongs to another NGO).<br>• Implemented competing offer cancellation and audit logging. |
| **Donations Route** | [`backend/app/api/routes/donations.py`](file:///backend/app/api/routes/donations.py) | • In `accept_donation`, replaced inline logic with delegation to canonical `process_atomic_ngo_acceptance`.<br>• In `collect_food` and `deliver_food`, added support for authenticated NGO role during self-pickup. |
| **Volunteers Route** | [`backend/app/api/routes/volunteers.py`](file:///backend/app/api/routes/volunteers.py) | • In `create_volunteer_assignment`, added guard rejecting assignments on `pickup_mode == "self_pickup"`.<br>• In `accept_volunteer_assignment`, added matching guard rejecting volunteer acceptance on self-pickup rescues. |
| **NGOs Route** | [`backend/app/api/routes/ngos.py`](file:///backend/app/api/routes/ngos.py) | • Added `GET /ngos/me/offers` returning `List[MatchOfferResponse]`.<br>• Added `GET /ngos/me/self-pickups` returning `List[DonationResponse]` for direct self-pickups. |
| **Schemas** | [`backend/app/schemas/schemas.py`](file:///backend/app/schemas/schemas.py) | • Ensured `DonationAcceptRequest` has `pickup_mode: Optional[str] = "volunteer_dispatch"` and `offer_id: Optional[int] = None`. |
| **Phase 4 Test Suite** | [`backend/tests/test_phase4_self_pickup_branch.py`](file:///backend/tests/test_phase4_self_pickup_branch.py) | • Created 7 dedicated tests covering self-pickup acceptance, offer lifecycle, courier blocking, mode switching, concurrency, uninvited rejection, and end-to-end OTP handover. |

---

### 6. Automated Test Verification Results

#### 6.1 Phase 4 Test Suite (`test_phase4_self_pickup_branch.py`)
```
tests/test_phase4_self_pickup_branch.py::test_01_ngo_self_pickup_clean_branch_acceptance PASSED [ 14%]
tests/test_phase4_self_pickup_branch.py::test_02_volunteer_assignment_blocked_on_self_pickup_donation PASSED [ 28%]
tests/test_phase4_self_pickup_branch.py::test_03_request_volunteer_switches_mode_and_triggers_wave2_dispatch PASSED [ 42%]
tests/test_phase4_self_pickup_branch.py::test_04_concurrency_two_ngos_simultaneous_acceptance_conflict_409 PASSED [ 57%]
tests/test_phase4_self_pickup_branch.py::test_05_uninvited_ngo_or_foreign_offer_id_rejected PASSED [ 71%]
tests/test_phase4_self_pickup_branch.py::test_06_direct_ngo_self_pickup_otp_verification_delivery_and_distribution PASSED [ 85%]
tests/test_phase4_self_pickup_branch.py::test_07_ngo_me_offers_and_me_self_pickups_endpoints PASSED [100%]

============================= 7 passed in 83.74s =============================
```

#### 6.2 Combined Regression Suite (Phase 4 + Three-Wave Dispatch + Proactive Dispatch)
```
tests/test_phase4_self_pickup_branch.py (7 passed)
tests/test_three_wave_dispatch.py (7 passed)
tests/test_proactive_dispatch.py (14 passed)

============================ 28 passed in 14.18s ============================
```

#### 6.3 Cross-Platform Validation
- **Mobile Flutter Suite:** 97 / 97 unit and widget tests passed (`flutter test`).
- **Web React Vite Build:** 1,471 modules transformed; production bundle built cleanly in 1.67s (`npm run build`).

---

### 7. Conclusion

Phase 4 is fully implemented, verified, and integrated into the Smart Food Rescue platform. The branch between direct NGO self-pickup and volunteer courier rescue operates cleanly, deterministically, and with bulletproof concurrency protection.
