# Smart Food Rescue Platform — REST API Reference Manual

**API Version:** `v1`  
**Base Path:** `/api`  
**Authentication Scheme:** `Bearer <JWT_ACCESS_TOKEN>`  
**Evaluation Date:** September 25, 2026  
**Document Identifier:** `API.md`  

---

## 1. Global Standards & Status Codes

All responses use JSON format. Protected endpoints require the standard `Authorization: Bearer <token>` header.

### 1.1 HTTP Status Code Conventions
- `200 OK`: Request succeeded; returns resource data.
- `201 Created`: Resource created successfully.
- `400 Bad Request`: Validation failure or business logic violation.
- `401 Unauthorized`: Missing, invalid, or expired JWT access token.
- `403 Forbidden`: Authenticated user lacks the required role or does not own the resource.
- `404 Not Found`: Resource does not exist (or unauthorized ID enumeration protection).
- `409 Conflict`: State machine violation, double-claim attempt, or OTP replay.
- `410 Gone`: Expired resource (e.g. OTP code TTL elapsed).
- `422 Unprocessable Content`: Pydantic schema validation error (malformed fields/bounds).
- `429 Too Many Requests`: Rate limiter triggered (e.g. brute-force login lockout).

---

## 2. Authentication & Identity Endpoints (`/api/auth`)

### 2.1 Register User
- **Method:** `POST /api/auth/register`
- **Access:** Public
- **Request Body:**
  ```json
  {
    "name": "Arun Kumar",
    "email": "donor@example.com",
    "password": "Password123!",
    "role": "donor",
    "phone": "+919876543210"
  }
  ```
- **Response `200 OK`:** User object with ID, role, and registered timestamp.

### 2.2 User Login
- **Method:** `POST /api/auth/login`
- **Access:** Public (Rate limited to `MAX_FAILED_LOGIN_ATTEMPTS`)
- **Request Body:**
  ```json
  {
    "email": "donor@example.com",
    "password": "Password123!"
  }
  ```
- **Response `200 OK`:**
  ```json
  {
    "access_token": "eyJhbGciOiJIUzI1Ni...",
    "refresh_token": "eyJhbGciOiJIUzI1Ni...",
    "token_type": "bearer",
    "user": { "id": 1, "name": "Arun Kumar", "role": "donor" }
  }
  ```

### 2.3 Send Phone Verification OTP
- **Method:** `POST /api/auth/verify-phone/request`
- **Access:** Authenticated (Any role)
- **Request Body:**
  ```json
  { "phone": "+919876543210" }
  ```
- **Response `200 OK`:**
  ```json
  {
    "message": "Verification code sent to +91 ****3210.",
    "phone_masked": "+91 ****3210"
  }
  ```

### 2.4 Confirm Phone Verification OTP
- **Method:** `POST /api/auth/verify-phone/confirm`
- **Access:** Authenticated (Any role)
- **Request Body:**
  ```json
  { "phone": "+919876543210", "otp": "654321" }
  ```
- **Response `200 OK`:** `{ "verified": true, "phone": "+919876543210" }`

---

## 3. Food Donations API (`/api/donations`)

### 3.1 Create Food Donation (Quick Rescue)
- **Method:** `POST /api/donations/`
- **Access:** `donor`
- **Request Body:**
  ```json
  {
    "food_name": "Paneer Biryani & Dal Makhani",
    "food_category": "Cooked Food",
    "quantity": 40.0,
    "quantity_unit": "Meals",
    "pickup_address": "Door 12, 1st Cross, Anna Nagar, Chennai",
    "latitude": 13.0827,
    "longitude": 80.2707,
    "storage_method": "Room Temperature",
    "packaging_condition": "Sealed / Covered",
    "safety_affirmation": true
  }
  ```
- **Response `201 Created`:** Full donation object with computed ERW, urgency level, and generated OTP hash.

### 3.2 List Active Rescue Feed
- **Method:** `GET /api/donations/`
- **Access:** Authenticated (Filtered by caller role)
- **Query Parameters:** `status`, `urgency`, `limit`, `offset`
- **Privacy Rules:** For unaccepted donations viewed by non-donors:
  - `pickup_address` displays coarse neighborhood area only.
  - `latitude` and `longitude` are rounded to 2 decimal places (~1.1km fuzzing).

### 3.3 Get Donation Detail View
- **Method:** `GET /api/donations/{donation_id}`
- **Access:** Authenticated (Role & ownership guarded)
- **Response `200 OK`:**
  - `verification_otp`: Exclusively provided if caller is donation owner or admin. Set to `null` for couriers and NGOs.
  - `history`: Sequential lifecycle entries with timestamps and actors.

### 3.4 Accept Rescue Mission (NGO Self-Pickup or Request Volunteer)
- **Method:** `POST /api/donations/{donation_id}/accept`
- **Access:** Verified `ngo`
- **Request Body:**
  ```json
  {
    "pickup_mode": "self_pickup"
  }
  ```
  *(Options: `self_pickup` | `volunteer_dispatch`)*
- **Response `200 OK`:** Updated donation status (`accepted` or `collected`).

---

## 4. Proactive Dispatch & Offers API (`/api/donations`)

### 4.1 Get Pending Match Offers for NGO
- **Method:** `GET /api/ngos/me/offers`
- **Access:** Verified `ngo`
- **Response `200 OK`:** List of active Wave 1 dispatch invitations with countdown timeouts.

### 4.2 Respond to Dispatch Offer (Pass / Decline)
- **Method:** `POST /api/donations/{donation_id}/reject`
- **Access:** `ngo`, `volunteer`
- **Request Body:**
  ```json
  {
    "reason": "Capacity full for evening service",
    "rejection_category": "insufficient_capacity"
  }
  ```
- **Response `200 OK`:** Offer marked `declined`; dispatch engine immediately escalates to Wave 2 or next candidate.

---

## 5. Volunteer Courier Operations (`/api/volunteers`)

### 5.1 Claim Feasible Volunteer Assignment
- **Method:** `POST /api/volunteers/assignments/{assignment_id}/accept`
- **Access:** `volunteer`
- **Preconditions:** Server validates $T_{\text{transit}} + 25\text{m buffer} \le \text{ERW}$.
- **Response `200 OK`:** Status set to `volunteer_assigned`.

### 5.2 Update Courier Telemetry & Geofence Arrival
- **Method:** `POST /api/donations/{donation_id}/telemetry`
- **Access:** Assigned `volunteer`
- **Request Body:**
  ```json
  {
    "latitude": 13.0830,
    "longitude": 80.2710,
    "speed_kmh": 28.5
  }
  ```
- **Behavior:** If distance to donor < 250m, automatically transitions to `arrived_at_donor`.

### 5.3 Report Courier Delay / Breakdown (Dynamic Rematch)
- **Method:** `POST /api/volunteers/assignments/{assignment_id}/report-issue`
- **Access:** Assigned `volunteer`, `admin`
- **Request Body:**
  ```json
  {
    "issue_type": "vehicle_breakdown",
    "remarks": "Flat tyre on transit route, cannot complete pickup"
  }
  ```
- **Response `200 OK`:** Triggers dynamic rematching; releases courier and finds backup without deleting audit records.

---

## 6. Pickup Verification & OTP API (`/api/donations` & `/api/volunteers`)

### 6.1 Retrieve Pickup OTP (Donor Only)
- **Method:** `GET /api/donations/{donation_id}/pickup-otp`
- **Access:** `donor` (owner only), `admin`
- **Response `200 OK`:**
  ```json
  {
    "donation_id": 42,
    "verification_otp": "782104",
    "expires_at": "2026-09-25T22:30:00Z",
    "phone_masked": "+91 ****3210"
  }
  ```
- **Security:** Returns `403 Forbidden` if invoked by volunteer or unauthorized user.

### 6.2 Verify Handover OTP (Courier Submission)
- **Method:** `POST /api/volunteers/verify-otp`
- **Access:** Assigned `volunteer`, `admin`, assigned `ngo`
- **Request Body:**
  ```json
  {
    "donation_id": 42,
    "otp": "782104"
  }
  ```
- **Validation Rules:**
  - Evaluates `secrets.compare_digest(hash(otp), record.otp_hash)` (constant time).
  - Rejects with `409 Conflict` if already consumed (replay defense).
  - Rejects with `410 Gone` if expired.
  - Rejects with `403 Forbidden` if submitted by donor (self-verification prevented).
- **Response `200 OK`:** `{ "verified": true, "status": "collected" }`

---

## 7. Live Notifications & Events API (`/api/notifications`)

### 7.1 Real-Time Server-Sent Events (SSE) Stream
- **Method:** `GET /api/notifications/stream`
- **Access:** Authenticated
- **Headers:** `Accept: text/event-stream`
- **Stream Events Delivered:**
  - `RESCUE_NEW_OFFER`: Notification of incoming rescue opportunity.
  - `RESCUE_CLAIMED`: Offer locked by an actor.
  - `COURIER_ARRIVED`: Volunteer reached donor pickup address.
  - `HANDOVER_COMPLETED`: OTP verified; food collected.
  - `RESCUE_CRITICAL`: Wave 3 emergency escalation.

### 7.2 REST Delta Polling Feed
- **Method:** `GET /api/notifications/feed`
- **Access:** Authenticated
- **Query Parameters:** `since_timestamp`
- **Response `200 OK`:** List of notifications created since requested timestamp.

---

## 8. Admin Intervention & Audit Operations (`/api/admin`)

### 8.1 Force State Transition Override
- **Method:** `POST /api/admin/rescues/{donation_id}/force-transition`
- **Access:** `admin`
- **Request Body:**
  ```json
  {
    "target_status": "collected",
    "reason": "Courier phone battery died at donor venue; physical collection confirmed via phone call.",
    "bypass_otp": true
  }
  ```
- **Response `200 OK`:** Status updated; immutable `AuditLog` entry created with required reason.

### 8.2 Retrieve Security Audit Trail
- **Method:** `GET /api/admin/audit-logs`
- **Access:** `admin`
- **Query Parameters:** `resource_type`, `user_id`, `limit`
- **Response `200 OK`:** Paginated immutable audit trail with sanitized details.

---

## 9. Provider Webhooks (`/api/webhooks`)

### 9.1 SMS Delivery Receipt Callback
- **Method:** `POST /api/webhooks/sms-delivery`
- **Access:** Provider Webhook Gateway
- **Headers:** `X-Hub-Signature-256: sha256=<HMAC_HEX>` or `X-SFR-Webhook-Secret: <SECRET>`
- **Request Body:**
  ```json
  {
    "provider_message_id": "MSG-981247",
    "status": "DELIVERED",
    "timestamp": "2026-09-25T21:15:00Z"
  }
  ```
- **Security:** Validates cryptographic HMAC signature with constant-time comparison. Returns `401 Unauthorized` on tampered or unsigned requests.
- **Response `200 OK`:** `{ "status": "processed", "provider_message_id": "MSG-981247" }`
