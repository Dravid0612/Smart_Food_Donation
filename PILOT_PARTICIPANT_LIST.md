# Smart Food Rescue Platform — Pilot Participant Operational Roster

**Document Identifier:** `PILOT_PARTICIPANT_LIST.md`  
**Phase:** Phase 1 — Partner Network Onboarding  
**Operating Area:** Koramangala (Blocks 4, 5, 6), Bengaluru, Karnataka  
**Privacy Status:** Redacted Minimal Operational Information (Zero unnecessary personal data)  

---

## 1. Operational Roster Summary

```text
========================================================================================
PILOT PHASE 0/1 PARTICIPANT DIRECTORY
========================================================================================
Operational Cluster:       Koramangala 4th, 5th, and 6th Blocks, Bengaluru
Active Operating Window:   21:30 – 23:30 IST
Central Dispatch Desk:     Field Coordinator (+91 98*** **210 / WhatsApp Ops Room)
Maximum Nodes Transit:     <10 minutes (All nodes within 1.5 km of 80ft Road Junction)
========================================================================================
```

---

## 2. Participant Node Directory

### 2.1 Donor Nodes (Commercial Food Providers)

| Role / Call-Sign | Entity Name | General Location | Contact Channel (Masked) | Key Operating Contact | Operating Window | Typical Surplus Profile |
|---|---|---|---|---|---|---|
| **DONOR-01 (Primary Anchor)** | Rasoi Heritage Restaurant | 5th Block, 80 Feet Road | `+91 98*** **301` / WhatsApp | Shift Floor Manager | 22:15 – 22:45 | 15–25 meals (Curries, Dal, Rice, Rotis) |
| **DONOR-02 (Backup Anchor)** | Annapoorna Grand Thali | 4th Block, 100 Feet Road | `+91 98*** **412` / Direct Call | Kitchen Supervisor | 22:00 – 22:30 | 20–35 meals (Sambar, Rice, Chapati) |

---

### 2.2 Recipient Nodes (Shelters & Welfare Homes)

| Role / Call-Sign | Organization Name | Node Location | Contact Channel (Masked) | Receiving Coordinator | Operating Hours | Intake Capacity & Facilities |
|---|---|---|---|---|---|---|
| **NGO-01 (Primary Shelter)** | Green Hope Care Foundation | 4th Block, 6th Cross (*850m from DONOR-01*) | `+91 98*** **444` / WhatsApp Ops | Sister Mary / S. Balaji | 07:00 – 23:30 | 45 resident children/elders; commercial re-heating & cold holding |
| **NGO-02 (Backup Shelter)** | Karunai Community Night Shelter | 6th Block, 12th Main (*1.4km from DONOR-01*) | `+91 98*** **555` / Direct Call | Mr. Rajesh Gowda | 18:00 – 06:00 | 30–40 overnight workers; immediate warm meal distribution |

---

### 2.3 Volunteer Courier Pool (Logistics Responders)

| Role / Call-Sign | Rider Name | Operating Zone | Vehicle & Gear Profile | Contact Channel (Masked) | Availability Window | Max Rescue Radius |
|---|---|---|---|---|---|---|
| **RIDER-01 (Primary Lead)** | Rahul Sharma | 5th Block Corridor | Motorcycle + 40L Thermal Insulated Box | `+91 98*** **777` / WhatsApp | 21:30 – 23:30 (Mon–Fri) | $\le 3.0\text{ km}$ ($\le 1.5\text{ km}$ preferred) |
| **RIDER-02 (Backup Lead)** | Priya Nair | 4th Block & ST Bed | Electric Scooter + 25L Insulated Bag | `+91 98*** **888` / WhatsApp | 21:00 – 23:00 (Tue, Thu, Sat, Sun) | $\le 2.5\text{ km}$ |
| **RIDER-03 (Hyper-Local Reserve)** | Karthik Sundaram | 5th Block Core | Geared Bicycle / Foot courier | `+91 98*** **122` / Direct Call | 22:00 – 23:00 (Daily on-call) | $\le 1.5\text{ km}$ |

---

### 2.4 Program Coordination & Arbitration Desk

| Role | Designation | Responsibilities | Operational Contact |
|---|---|---|---|
| **COORDINATOR-01** | Lead Operations Coordinator | Real-time monitoring via Web Console, WhatsApp Ops triage, manual phone escalation, handover dispute arbitration | `+91 98*** **210` (Central Helpline) |

---

## 3. Escalation & Fallback Dispatch Sequence

If a disruption occurs during a live rescue run, participants follow this strict fallback sequence:

```text
Step 1 (T+0m to T+5m):
  - Donor declares food surplus on Mobile App at 22:15.
  - Automated Push Notification dispatches to RIDER-01 (Rahul).
  - Mirror alert posted to "Koramangala Food Rescue Pilot" WhatsApp group.

Step 2 (T+5m to T+8m):
  - If RIDER-01 does not acknowledge or accept within 5 minutes:
    Coordinator calls RIDER-01 directly.
  - If RIDER-01 is unreachable or delayed:
    Task is immediately assigned to RIDER-02 (Priya).

Step 3 (T+8m to T+12m):
  - If both primary riders are held up:
    Coordinator pings RIDER-03 (Karthik) or notifies NGO-01 (Green Hope)
    for direct 850-meter self-pickup by their resident staff.

Step 4 (T+15m):
  - Handover occurs at Donor back gate.
  - Donor displays 6-digit OTP on phone screen.
  - Rider enters OTP into touch keypad -> Status confirmed as 'collected'.
  - Rider delivers to NGO-01 within 10 minutes.
```

---

## 4. Privacy & Data Protection Compliance

1. **No Sensitive PII Persisted:** Personal home addresses, individual national IDs (Aadhaar/PAN), and personal bank/financial information are strictly excluded from this repository and project logs.
2. **Phone Number Masking:** In all public documentation and courier-facing screens, donor and volunteer phone numbers are masked in accordance with platform security protocols (`+91 98*** **301`).
3. **Beneficiary Protection:** The identities, photographs, and records of minor shelter residents and vulnerable individuals are protected under strict non-disclosure; only aggregated meal counts are published.
4. **Zero-Knowledge Handover:** The donor never receives the volunteer's private data, and the volunteer never sees donor private contact data post-delivery confirmation.
