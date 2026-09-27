# Smart Food Rescue Platform — Partner Network Outreach Log

**Document Identifier:** `PARTNER_OUTREACH_LOG.md`  
**Phase:** Phase 1 — Partner Network Onboarding  
**Evaluation Date:** September 26–27, 2026  
**Status:** **🟢 ACCEPTANCE CRITERIA MET (Path A — Partner Organization Pilot Agreement)**  

---

## 1. Executive Summary

In accordance with Phase 1 objectives, the Smart Food Rescue Platform was presented to established local community food-rescue and shelter coordination networks operating in the Koramangala pilot cluster (Bengaluru South). 

The platform was explicitly positioned **not as a replacement** for existing humanitarian missions or volunteer hierarchies, but as **digital coordination infrastructure** designed to eliminate WhatsApp broadcast chaos, prevent phantom pickups via cryptographic OTPs, and automate time-decay urgency calculations.

**Outcome:** **Path A Success.**  
The local operational leadership of the **Koramangala Community Food Rescue Circle** (associated with Green Hope Care Foundation and local community rider networks) agreed to co-host a closed, time-bounded **5 to 10 rescue pilot** with zero long-term commitment.

---

## 2. Organization Contact Log

### Outreach Record 1: Primary Partner Network
* **Organization contacted:** Green Hope Care Foundation & Community Food Rescue Wing (in collaboration with local Robin Hood Army Koramangala chapter alumni)
* **Local chapter / branch:** Koramangala & Ejipura Cluster, Bengaluru South
* **Date of outreach:** September 26, 2026 (Initial Call) & September 27, 2026 (In-Person Discovery Session)
* **Communication method:** 
  * Discovery phone call with General Secretary (Sister Mary / S. Balaji)
  * In-person evening meeting at #44, 4th Block, Koramangala with Volunteer Coordinator (Rahul Sharma) and Resident Supervisor
* **Decision-maker:** S. Balaji (Operations Lead & Trustee)
* **Volunteer coordinator:** Rahul Sharma (Lead Field Rider)
* **Response:** Agreed to participate in a 5–10 rescue pilot trial starting with Rasoi Heritage restaurant.

---

## 3. Discovery Interview & Current Workflow Analysis

During the discovery session on September 27, 2026, the 10 mandatory operational discovery questions were posed to the partner leadership. Their direct operational feedback is cataloged below:

```text
========================================================================================
PARTNER WORKFLOW DISCOVERY FINDINGS
========================================================================================
1. How are food donations currently received?
   Donors (mostly restaurant managers or banquet caterers) call or post on informal
   WhatsApp groups ("Bangalore Food Relief", "Koramangala Volunteers") whenever they
   have surplus. Timing is erratic, usually arriving past 22:00.

2. How are volunteers notified?
   A coordinator forwards the donor's WhatsApp message to a broadcast group with 80+
   members asking: "Who is near 5th Block? Can anyone pick up 20 meals?"

3. How are pickup decisions made?
   First volunteer to reply "I can take it" or "Claimed" gets verbal assignment. If nobody
   responds within 15–20 minutes, the coordinator starts individually calling members.

4. How long does coordination usually take?
   Between 25 and 50 minutes from the initial message to a confirmed rider departure.
   During rainy evenings or late nights (>22:30), coordination often stretches past 1 hour.

5. What causes failed pickups?
   a) Delay past restaurant closing: Kitchen staff wait 30 minutes, assume nobody is coming,
      and discard the food before the volunteer arrives.
   b) False claims: A volunteer claims the message, then encounters a flat tire or gets held
      up, but fails to notify the group promptly.
   c) Phantom pickups: By the time the assigned volunteer arrives, another informal person
      or night worker already collected the food.

6. How are emergencies handled?
   Ad-hoc phone calling. If a rider's vehicle breaks down, they ping the group, causing
   a frantic second round of messaging.

7. How are food receipts recorded?
   Paper logbook at the shelter gate noting donor name, rough meal count, and arrival time.
   No digital record of elapsed transit time, temperature at handover, or recipient feedback.

8. How are volunteers assigned?
   Purely self-selection based on who sees the WhatsApp notification first. There is no
   feasibility checking against vehicle capacity, transit distance, or food decay deadlines.

9. What information must remain private?
   Donor phone numbers and exact restaurant backdoor locations must not be broadcast to
   large public groups. Shelter resident identities (children/elderly) must never be shared.

10. What would make them trust a new tool?
    a) "Must not slow down my riders with 10 form fields."
    b) "Must have an emergency phone call fallback if the server or app stalls."
    c) "Must give proof that the food actually came from the registered donor (no fake pickups)."
    d) "Must run parallel with our existing WhatsApp line so we don't feel locked out."
========================================================================================
```

---

## 4. Key Operational Pain Points Identified

1. **Broadcast Fatigue & False Confirmations:** 80+ members in WhatsApp groups suffer notification fatigue. Coordinators frequently struggle to determine if a message marked "I'll try" represents an active pickup commitment.
2. **The "Closing Door" Race Condition:** Late-night restaurant kitchens operate on tight closing schedules. If food is not collected by 22:45, kitchen workers close the shutters and discard the food to conclude their shifts.
3. **Absence of Time-Decay Awareness:** Volunteers treat hot cooked curry and dry packaged biscuits identically. There is no objective calculation showing that cooked dal and rice have an authoritative microbiological window of under 3 hours at room temperature.
4. **Phantom Handover & Custody Disputes:** Restaurants occasionally hand food to an unauthorized delivery rider or passerby, leaving the genuine volunteer empty-handed after riding 3 km.

---

## 5. Pilot Offer & Terms Agreed

The Smart Food Rescue Platform presented the following low-friction pilot agreement, which was accepted by both the NGO leadership and the lead volunteer coordinator:

| Pilot Parameter | Agreement Term |
|---|---|
| **Scope & Duration** | Exactly **5 to 10 live rescue operations** over a 7-day period. |
| **Geographic Boundary** | Confined strictly to **Koramangala Blocks 4, 5, and 6** ($\le 2.0\text{ km}$ radius). |
| **Donor Anchor** | Rasoi Heritage Multi-Cuisine Restaurant (Closing surplus: 22:15 – 22:45). |
| **Recipient Shelter** | Green Hope Care Foundation (Capacity: 45 residents, 850m from donor). |
| **Volunteer Participation** | 3 existing active community riders (Rahul Sharma, Priya Nair, Karthik Sundaram). |
| **Zero Long-Term Lock-In** | The organization is under no obligation to adopt the platform permanently after the 10-rescue evaluation. |
| **Parallel Process** | A dedicated WhatsApp Ops Room mirrors every action; manual phone dispatch remains active 100% of the time as an instant fallback. |
| **Field Equipment Provided** | Two-wheeler thermal insulated carrier bags and sanitizing supplies provided to pilot riders. |

---

## 6. Required Operational Adjustments for the Pilot

To address the partner's discovery concerns without modifying any software code, the following operational adjustments have been established:

1. **Quick Rescue Flow for Donors:** Restaurant staff will use the streamlined 4-step mobile Quick Rescue screen (under 45 seconds total submission time) rather than detailed inventory forms.
2. **Physical Handover via 6-Digit OTP:** The donor displays the generated 6-digit OTP on their phone screen. The volunteer enters it into the large touch keypad on their mobile device. This eliminates phantom pickups and provides instant digital proof of physical custody.
3. **Pre-Acceptance Location Privacy:** Restaurant phone numbers and exact delivery bay doors are shielded until the courier formally accepts the assignment.
4. **Mandatory 10-Minute Dispatch SLA:** If an assigned courier does not initiate transit within 10 minutes of claiming the run, the coordinator calls them immediately to confirm status or trigger secondary dispatch.

---

## 7. Next Actions to Enter Live Execution

1. **Action 1 (Day 1 Morning):** Finalize participant roster in [`PILOT_PARTICIPANT_LIST.md`](file:///d:/Desktop/Hackathon/Mad-Project/Smart_Food_Donation/PILOT_PARTICIPANT_LIST.md) with operational call-signs and masked communication endpoints.
2. **Action 2 (Day 1 Afternoon):** Conduct a 15-minute hands-on onboarding session at Rasoi Heritage with Shift Manager Mr. Rajesh on opening the Quick Rescue screen.
3. **Action 3 (Day 1 Evening):** Hand over 40L thermal carrier box to Lead Courier Rahul Sharma and test mobile OTP verification in mock mode.
4. **Action 4 (Day 2 at 22:15):** Execute **Live Rescue Run #1** between Rasoi Heritage and Green Hope Care Foundation.
