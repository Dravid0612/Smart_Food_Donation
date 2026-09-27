# Smart Food Rescue Platform — System Architecture & Technical Specifications

**Architecture Specification:** `v2.5`  
**Evaluation Date:** September 25, 2026  
**Document Identifier:** `ARCHITECTURE.md`  
**System Classification:** Zero-Cash, Hyper-Local Food Rescue Coordination Engine  

---

## 1. High-Level System Architecture

The **Smart Food Rescue Platform** connects four primary actor roles:
1. **Donors (Commercial/Catering):** Post surplus food with AI safety affirmations.
2. **Receiving NGOs / Shelters:** Review rescue opportunities and accept for self-pickup or courier delivery.
3. **Volunteer Couriers:** Claim feasible pickup missions and transport food to destination NGOs.
4. **Platform Administrators:** Monitor city-wide operations and intervene in disputes or critical rescues.

```mermaid
graph TD
    subgraph "Clients Layer"
        FLUTTER_APP["Flutter Mobile App (Android/iOS)<br/>Action-First UI (Donor, NGO, Volunteer)"]
        REACT_CONSOLE["React Web Operations Console<br/>Live Queue, AI Triage, Admin Overrides"]
    end

    subgraph "API & Security Gateway (FastAPI)"
        JWT_AUTH["JWT Authentication & RBAC Filter"]
        RATE_LIMITER["Sliding-Window Rate Limiter"]
        PRIVACY_GUARD["GPS Fuzzing & Neighborhood Masking"]
        HMAC_VALIDATOR["HMAC-SHA256 Webhook Validator"]
    end

    subgraph "Core Business Services"
        FSM["StateMachineService<br/>Canonical State Transitions"]
        ERW["FoodRescueWindowService<br/>Microbiological Decay Engine"]
        DISPATCH["ProactiveDispatchService<br/>3-Wave Proactive Matching"]
        FEASIBILITY["Feasibility & Rematching Engine<br/>Transit Buffers & Courier Ranking"]
        OTP_ENGINE["OtpService<br/>SHA-256 Hashing & Timing-Safe Verify"]
        NOTIFICATION_HUB["NotificationBroker & SMS Service<br/>REST Delta + SSE Live Events"]
    end

    subgraph "Storage & Audit Layer"
        SQL_DB[("Database Engine<br/>SQLite WAL Mode / PostgreSQL 15+")]
        AUDIT_STORE[("AuditLog & DonationHistory<br/>Tamper-Evident History")]
    end

    FLUTTER_APP -->|REST / SSE / Delta| JWT_AUTH
    REACT_CONSOLE -->|REST / SSE / Delta| JWT_AUTH

    JWT_AUTH --> RATE_LIMITER
    RATE_LIMITER --> PRIVACY_GUARD
    PRIVACY_GUARD --> FSM

    FSM --> ERW
    FSM --> DISPATCH
    DISPATCH --> FEASIBILITY
    FEASIBILITY --> OTP_ENGINE
    OTP_ENGINE --> NOTIFICATION_HUB

    FSM --> SQL_DB
    FSM --> AUDIT_STORE
    OTP_ENGINE --> SQL_DB
    OTP_ENGINE --> AUDIT_STORE
```

---

## 2. Backend Source of Truth & Layered Architecture

The platform strictly enforces the **Backend Source of Truth** principle:
- **Donation State:** Controlled entirely by the backend state machine. Frontends cannot force state transitions.
- **Estimated Rescue Window (ERW):** Calculated server-side using microbiological decay factors and ambient temperature multipliers.
- **Feasibility:** Couriers cannot claim assignments unless $T_{\text{transit}} + 25\text{m buffer} \le \text{ERW}$.
- **Security Decisions:** Role authorization, ownership validation, OTP verification, and rate limiting run exclusively on the server.

### 2.1 Technology Stack
- **Framework:** FastAPI 0.115+ (Python 3.13)
- **ORM & Data Layer:** SQLAlchemy 2.0 with Pydantic v2 schemas
- **Database Engine:** SQLite 3 with Write-Ahead Logging (WAL) and 30-second busy timeout (Local/Staging) / PostgreSQL 15+ with connection pooling (`pool_size=10, max_overflow=20`) (Production)
- **Live Event Transport:** In-memory asynchronous pub/sub broker (`NotificationBroker`) delivering Server-Sent Events (SSE) and REST delta polling (`/api/notifications/feed`)

---

## 3. Finite State Machine (FSM) Specification

The system manages three interrelated finite state machines with atomic row locks:

### 3.1 Donation Lifecycle FSM (`FoodDonation.status`)

```mermaid
stateDiagram-v2
    [*] --> pending: Donor creates donation
    pending --> accepted: NGO accepts (Wave 1)
    pending --> cancelled: Donor cancels
    pending --> expired: ERW window expires

    accepted --> collected: NGO self-pickup
    accepted --> volunteer_assigned: Dispatched to courier (Wave 2)
    accepted --> cancelled: NGO / Donor cancels
    accepted --> expired: ERW window expires

    volunteer_assigned --> pickup_en_route: Courier departs
    volunteer_assigned --> arrived_at_donor: Courier arrives (<250m)
    volunteer_assigned --> accepted: Rematch on vehicle breakdown
    volunteer_assigned --> pickup_failed: Pickup impossible

    pickup_en_route --> arrived_at_donor: Courier arrives
    pickup_en_route --> accepted: Rematch on transit delay
    pickup_en_route --> pickup_failed: Courier failure

    arrived_at_donor --> collected: Valid OTP submitted by courier
    arrived_at_donor --> pickup_failed: Donor unavailable / food spoiled

    collected --> in_transit: Transport to NGO shelter
    collected --> delivered: Courier arrives at NGO
    collected --> delivery_failed: NGO premises closed

    in_transit --> delivered: Food received at NGO
    in_transit --> delivery_failed: Delivery failure

    delivered --> partially_distributed: NGO begins distribution
    delivered --> completed: 100% meals distributed

    partially_distributed --> partially_distributed: Additional batches
    partially_distributed --> completed: All meals distributed

    completed --> [*]: Terminal
    cancelled --> [*]: Terminal
    expired --> [*]: Terminal
```

### 3.2 State Transition Matrix & Role Gates

| Current State | Target State | Authorized Roles | Preconditions / Rules |
|---|---|---|---|
| `pending` | `accepted` | `ngo`, `admin` | Verified NGO; locks `MatchOffer` |
| `pending` | `cancelled` | `donor`, `admin` | Donor can cancel before acceptance |
| `pending` | `expired` | System Watchdog | $\text{Remaining Minutes} \le 0$ |
| `accepted` | `collected` | `ngo`, `admin` | Only valid when `pickup_mode="self_pickup"` |
| `accepted` | `volunteer_assigned`| `volunteer`, `admin` | Courier satisfies feasibility equation |
| `volunteer_assigned`| `pickup_en_route` | `volunteer`, `admin` | Courier starts transit |
| `volunteer_assigned`| `arrived_at_donor` | `volunteer`, `admin` | Courier GPS within 250m geofence |
| `volunteer_assigned`| `accepted` | `volunteer`, `admin` | Dynamic rematching triggered |
| `arrived_at_donor` | `collected` | `volunteer`, `admin`, `ngo` | Cryptographic OTP verified successfully |
| `collected` | `delivered` | `volunteer`, `admin` | Courier physically arrives at NGO shelter |
| `delivered` | `partially_distributed`| `ngo`, `admin` | NGO logs partial distribution intake |
| `delivered` | `completed` | `ngo`, `admin` | All meals distributed; impact computed |

---

## 4. Estimated Rescue Window (ERW) Decay Model

The backend evaluates food safety dynamically based on microbiological decay rules:

$$\text{ERW}_{\text{total}} = \text{BaseWindow}(\text{Category}) \times M_{\text{storage}} \times M_{\text{packaging}} - T_{\text{elapsed}}$$

$$\text{Remaining Minutes} = \max\left(0, \left\lfloor \frac{\text{Deadline} - \text{Now}}{60} \right\rfloor\right)$$

### 4.1 Decay Parameters by Food Category
- **Cooked Rice / Lentils / Gravy:** Base 4.0 hours, High risk, Conservative buffer: 30 minutes
- **Bakery & Bread:** Base 12.0 hours, Low risk, Conservative buffer: 60 minutes
- **Fresh Cut Fruits & Salads:** Base 3.0 hours, High risk, Conservative buffer: 20 minutes
- **Packaged Dry Goods:** Base 24.0 hours, Low risk, Conservative buffer: 120 minutes

### 4.2 Storage & Packaging Multipliers
- **Refrigerated (<4°C):** Multiplier $1.5\times$
- **Room Temperature (20°C–30°C):** Multiplier $1.0\times$
- **Warm / Insulated (>60°C):** Multiplier $1.2\times$
- **Sealed / Airtight Container:** Multiplier $1.1\times$
- **Open / Exposed:** Multiplier $0.7\times$

---

## 5. Three-Wave Proactive Dispatch Engine

Dispatch progresses automatically through 3 successive waves until claimed:

```mermaid
sequenceDiagram
    participant D as Food Donation
    participant W1 as Wave 1: NGO Self-Pickup
    participant W2 as Wave 2: Volunteer Dispatch
    participant W3 as Wave 3: Critical Broadcast
    participant A as Admin Intervention

    D->>W1: Donation Created (status=pending)
    Note over W1: Find nearest verified NGO<br/>Check vehicle capacity & operating hours
    W1-->>D: Proactive Offer Created (timeout=10m)

    alt NGO Accepts (Self-Pickup)
        W1->>D: NGO Accepts (pickup_mode=self_pickup)
        Note over D: Transitions to 'accepted'<br/>Direct collection enabled
    else NGO Passes or 10m Timeout Elapses
        W1->>W2: Cascade to Wave 2
        Note over W2: Query available couriers<br/>Filter: Transit + 25m <= ERW<br/>Rank by capacity & reliability
        W2-->>D: Volunteer Offers Dispatched (timeout=8m)
        alt Volunteer Accepts
            W2->>D: Courier Claims Assignment
            Note over D: Transitions to 'volunteer_assigned'<br/>OTP generated for donor
        else Timeout Elapses & ERW <= 60m
            W2->>W3: Escalate to Wave 3 (Critical)
            Note over W3: Broadcast to all couriers & NGOs<br/>within 15km radius
            W3->>A: Trigger Admin Control Alert
            Note over A: Admin can reassign, extend, or force-dispatch
        end
    end
```

---

## 6. Security Perimeter & Privacy Architecture

The platform maintains 6 strict defensive layers:

1. **Authentication:** JWT tokens (15-minute access, 7-day refresh) signed with `JWT_SECRET`. Tokens re-verify user active state on every database query.
2. **RBAC & Ownership:** Role validation guards routes (`require_role(["donor", "volunteer", "ngo", "admin"])`). Donors can only inspect their own donations; couriers can only view their active assignment.
3. **One-Way OTP Hashing:** OTPs are stored exclusively as 64-character SHA-256 hex digests (`PickupOtpRecord.otp_hash`). Plaintext OTP is never stored in persistent storage. Comparisons execute in constant time via `secrets.compare_digest`.
4. **Replay & Concurrency Defense:** Single-use tokens flag `used_at = now` and `is_active = False`. Repeated submissions return `HTTP 409 Conflict`. Simultaneous requests are serialized using database row-level locking.
5. **GPS Privacy Fuzzing:** Unaccepted donations round latitude and longitude to 2 decimal places (~1.1km precision) and mask the street address with `"(Exact address revealed upon acceptance)"`. Full coordinates and address are only revealed to the assigned courier or NGO once accepted.
6. **HMAC Webhook Validation:** Inbound SMS delivery receipts on `/api/webhooks/sms-delivery` validate cryptographic `HMAC-SHA256` signatures (`X-Hub-Signature-256`, `X-SFR-Webhook-Signature`) using constant-time evaluation against `SMS_WEBHOOK_SECRET`.

---

## 7. Mobile & Web Client Architectures

### 7.1 Flutter Mobile Architecture (`mobile/`)
- **UI Pattern:** Material 3 Action-First design system. Focuses on field efficiency: large buttons, high contrast, minimal typing.
- **State Management:** Provider-based reactive architecture (`DonationProvider`, `AuthProvider`, `LanguageProvider`).
- **Urgency Visualization:** Curated 5-tier color system:
  - `FRESH`: Emerald Green
  - `APPROACHING`: Amber
  - `URGENT`: Orange
  - `CRITICAL`: Crimson Red
  - `ENDED`: Muted Slate Gray
- **Localization:** 100% key parity across English (`en`), Tamil (`ta`), and Hindi (`hi`).

### 7.2 React Web Operations Console (`web/`)
- **UI Pattern:** SPA dashboard engineered for live intervention and triage.
- **Key Modules:**
  - Active Food Receiving Feed with urgent countdown timers
  - AI Vision Condition Inspection Drawer
  - Force State Transition Modal with required audit remarks
  - Spatial Grid Clustering of city-wide rescue activity
- **Real-Time Integration:** REST delta polling with fallback to SSE stream. Zero third-party broker dependencies (no Redis/Kafka needed).

---

## 8. Data Storage Architecture

### 8.1 SQLite Write-Ahead Logging (WAL) Mode
In development, testing, and staging environments, the backend configures SQLite with:
```sql
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA foreign_keys = ON;
PRAGMA busy_timeout = 30000;
```
This guarantees concurrent read-while-write transactions without database locked errors.

### 8.2 Production PostgreSQL Compatibility
The ORM and Alembic migrations are written for PostgreSQL 15+:
- Connection pool with pre-ping validation (`pool_size=10, max_overflow=20`)
- Standardized `TIMESTAMP WITH TIME ZONE` columns
- Explicit database indices on frequently queried fields (`ix_donations_status_created`, `ix_donations_donor_created`)
