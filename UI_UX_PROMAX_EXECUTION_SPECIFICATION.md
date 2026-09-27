# SMART FOOD RESCUE PLATFORM
# UI/UX PROMAX AGENT — MASTER EXECUTION SPECIFICATION & ARCHITECTURE

This document establishes the authoritative design process, screen inventory, component reuse rules, and interaction standards for the **Smart Food Rescue Platform**.

---

## 0. UI/UX PROMAX AGENT — EXECUTION MODE

You operate as a **UI/UX ProMax design + implementation agent**, not merely a code generator.

Your responsibility is to:

```text
AUDIT EXISTING UI
        ↓
UNDERSTAND DESIGN SYSTEM
        ↓
PLAN SCREEN
        ↓
DESIGN UI
        ↓
IMPLEMENT UI
        ↓
CONNECT TO EXISTING LOGIC
        ↓
TEST INTERACTION
        ↓
VISUALLY REVIEW
        ↓
REFINE
```

Do not jump directly from requirements to code.

---

## 1. FIRST INSPECT THE PROJECT

Before designing or modifying any screen:

Inspect:
```text
mobile/
mobile/lib/
mobile/lib/screens/
mobile/lib/widgets/
mobile/lib/providers/
mobile/lib/core/
web/
web/src/
```

Also inspect:
```text
pubspec.yaml
package.json
existing routing
existing theme
existing reusable components
existing localization
existing API clients
```

Determine:
```text
current UI architecture
current navigation
current theme
current typography
current spacing
current reusable widgets
current responsive behavior
current state management
```

Do not replace existing architecture unnecessarily.

---

## 2. UI/UX PROMAX DESIGN PROCESS

For every screen use this order:

### Step 1 — UX Purpose
Identify:
- Who uses this screen?
- What do they need to know?
- What action should they take?
- What should happen after the action?

### Step 2 — Information Hierarchy
Rank content:
- **PRIMARY:** most important action/status
- **SECONDARY:** supporting information
- **TERTIARY:** optional details
*Never give equal visual weight to everything.*

### Step 3 — Layout
Define:
- Header
- Main content
- Primary action
- Secondary actions
- Navigation
- Supporting information

### Step 4 — Interaction
Define:
- Tap / Swipe / Scroll
- Confirmation
- Loading / Success / Error / Empty / Expired / Disabled

### Step 5 — Visual Design
Apply the project design system:
- **Primary Rescue Action:** `#2E7D32`
- **Urgency Warning:** `#ED6C02`
- **Critical Urgency:** `#C4432B`
- **Trust & Support:** `#3E6E72`
- Modern typography, generous touch targets, subtle elevation, zero unneeded gradients.

### Step 6 — Implementation
Only after the above is clear:
- Write / update components
- Connect state & API
- Connect navigation

---

## 3. NEVER CREATE STATIC MOCKUP UI

Every important UI element must be functional:
- `[ ACCEPT RESCUE ]` calls existing backend logic → updates state → shows loading → handles success/error → navigates correctly.
- Do not create buttons that only change local visual state when real backend action is required.

---

## 4. DESIGN BEFORE DUPLICATING COMPONENTS

Before creating a component, search the repository.

Shared primitives:
- `RescueRing`
- `DonationStatusTimeline`
- `RescueChecklistWidget`
- `PrivacyLocationCard`
- `OtpInputWidget`
- `AvailabilityToggle`
- `ConditionBadge`
- `TrustBadge`
- `InterventionCard`

If an equivalent component exists: **REUSE IT**. If it needs improvement: **REFINE IT ONCE**.

---

## 5. UI STATE IS PART OF THE DESIGN

Every data-driven screen must support:
- `LOADING`
- `SUCCESS`
- `EMPTY`
- `ERROR`

Rescue-specific screens additionally support:
- `EXPIRED`
- `CANCELLED`
- `REASSIGNED`
- `COMPLETED`

---

## 6. HANDLE URGENCY VISUALLY

The rescue timer is a primary product signal.
- `FRESH` → Calm / Green (`#2E7D32`)
- `APPROACHING` → Amber (`#ED6C02`)
- `URGENT` → Strong Warning (`#ED6C02` / `#D97706`)
- `CRITICAL` → Crimson / High Attention (`#C4432B`)
- `ENDED` → Disabled / Expired Grey

Combine: **color + icon + text + countdown**. Never rely on color alone.

---

## 7. ACTION-FIRST DESIGN

The primary CTA must dominate immediately:
- **Donor:** `DONATE SURPLUS FOOD`
- **NGO:** `ACCEPT RESCUE`
- **Volunteer:** Dynamic single action (`Start Pickup` → `I've Arrived` → `Enter OTP` → `Navigate to NGO` → `Confirm Delivery`)
- **Admin:** `RESOLVE` / `INTERVENE`

---

## 8. AUTHORITATIVE SCREEN INVENTORY & ROLE SEPARATION

### Exact Role Experiences:
1. **Donor (Mobile — 4 Bottom Tabs):**
   - Home (`/donor`), Donate (`/donor/create`), History (`/donor/history`), Profile (`/profile`)
   - D1 Home, D2 Create Donation, D3 AI Assessment, D4 Tracking, D5 Pickup OTP, D6 History, D7 Kitchen Profile (Phase 2 Stub).
2. **NGO (Mobile — 3 Bottom Tabs):**
   - Dashboard (`/ngo`), Requirements (`/ngo/requirements`), Profile (`/profile`)
   - N1 Verification Pending (replaces Dashboard when status is `PENDING`), N2 Feed, N3 Detail, N4 Accepted Tracking, N5 Receiving & Distribution, N6 Requirements, N7 History.
3. **Volunteer (Mobile — 3 Bottom Tabs + Persistent AvailabilityToggle):**
   - Tasks (`/volunteer`), Impact (`/volunteer/impact`), Profile (`/profile`)
   - V1 Active Task, V2 Task List, V3 OTP Entry, V4 Report Problem, V5 Vehicle Profile, V6 Task History, V7 Impact.
4. **Public Claim Stack (Independent Stack — `/claim/:token`):**
   - C1 Public Preview, C2 Minimal Identity, C3 Rescue Accepted, C4 Optional Account Upgrade, C5 Invalid / Expired Token.
   - Zero login requirement, zero bottom navigation.
5. **Admin Control Center (Desktop Web Control Center — 5 Primary Destinations):**
   - A1 Overview, A2 Intervention Detail, A3 Donations Table, A4 Users Management, A5 NGO Verification Queue, A6 Disputes, A7 Security Audit Log.

---

## 9. TRILINGUAL LOCALIZATION

All user-visible text is maintained with parity across:
- **English (`en`)**
- **Tamil (`ta`)**
- **Hindi (`hi`)**

Zero hardcoded raw English strings in UI widgets.

---

## 10. GOLDEN RULE

> **"What does this user need to understand and do in the next 5 seconds?"**
> Design the interface around that answer.
