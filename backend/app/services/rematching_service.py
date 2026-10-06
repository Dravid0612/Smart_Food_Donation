"""
RematchingService — Smart Food Rescue
======================================
Continuous logistics feasibility evaluation, automated dynamic re-matching,
atomic reassignment locking, hard-gated candidate selection, and trilingual
non-blaming notifications.
"""

import math
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List, Tuple

from sqlalchemy.orm import Session
from sqlalchemy import text

from app.models.models import (
    FoodDonation, VolunteerAssignment, User, NGO, DonationHistory, AuditLog, Notification
)
from app.core.config import settings
from app.services.route_service import route_service, haversine_distance_km
from app.services.notification_service import create_notification, create_event_notification
from app.services.security_service import log_audit_event, log_rescue_operation
from app.services.state_machine_service import (
    transition_donation_state,
    transition_donation_status,
    transition_assignment_status,
)

logger = logging.getLogger("smart_food_rescue.rematching")

# Safety and Handover Time Allocations (in minutes)
HANDOVER_BUFFER_MIN = 10.0
NGO_INTAKE_BUFFER_MIN = 10.0
CRITICAL_SAFETY_MARGIN_MIN = 5.0


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


TELEMETRY_STALE_MINUTES = 15.0


class RematchingService:
    """
    Dynamic Rematching Engine for Time-Critical Food Rescues.
    """

    @staticmethod
    def evaluate_assignment_feasibility(
        db: Session,
        donation: FoodDonation,
        assignment: Optional[VolunteerAssignment] = None,
        current_eta_minutes: Optional[float] = None,
        volunteer: Optional[User] = None,
        reference_time: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Evaluates whether the assigned or candidate volunteer can complete the rescue before the window closes.
        Formula:
          mission_time = courier_to_donor_eta + pickup_buffer + donor_to_ngo_eta + intake_buffer + traffic_contingency
          is_feasible = (mission_time <= remaining_ERW)
        """
        now = reference_time or _utcnow()
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        window_end = donation.estimated_window_end or donation.expiry_time
        if window_end:
            if window_end.tzinfo is None:
                window_end = window_end.replace(tzinfo=timezone.utc)
            remaining_window_mins = max(0.0, (window_end - now).total_seconds() / 60.0)
        else:
            remaining_window_mins = float(donation.remaining_minutes or 60.0)

        # 1. Resolve active or candidate volunteer
        vol = volunteer or donation.assigned_volunteer
        if not vol and assignment and assignment.volunteer_id:
            vol = db.query(User).filter(User.id == assignment.volunteer_id).first()

        # 2. ETA to donor
        if current_eta_minutes is not None:
            eta_to_donor = float(current_eta_minutes)
        elif assignment and assignment.current_eta_minutes is not None:
            eta_to_donor = float(assignment.current_eta_minutes)
        else:
            # Fallback estimation based on volunteer coordinates
            vol_lat = vol.latitude if vol else None
            vol_lon = vol.longitude if vol else None
            if vol_lat and vol_lon and donation.latitude and donation.longitude:
                calc = route_service.calculate_eta(
                    vol_lat, vol_lon,
                    donation.latitude, donation.longitude,
                    vol.vehicle_type or "bike"
                )
                eta_to_donor = float(calc["eta_minutes"])
            else:
                eta_to_donor = 15.0

        # 3. Transit from donor to receiving NGO
        ngo_lat = donation.assigned_ngo.latitude if donation.assigned_ngo else None
        ngo_lon = donation.assigned_ngo.longitude if donation.assigned_ngo else None
        if donation.latitude and donation.longitude and ngo_lat and ngo_lon:
            ngo_route = route_service.calculate_eta(
                donation.latitude, donation.longitude,
                ngo_lat, ngo_lon,
                vol.vehicle_type if vol else "bike"
            )
            transit_donor_to_ngo = float(ngo_route["eta_minutes"])
        else:
            transit_donor_to_ngo = 15.0

        # 4. Total mission time required
        stage = donation.status.lower()
        if stage in ["collected", "in_transit"]:
            # Only remaining leg to NGO
            total_required_mins = eta_to_donor + NGO_INTAKE_BUFFER_MIN + CRITICAL_SAFETY_MARGIN_MIN
        else:
            total_required_mins = (
                eta_to_donor +
                HANDOVER_BUFFER_MIN +
                transit_donor_to_ngo +
                NGO_INTAKE_BUFFER_MIN +
                CRITICAL_SAFETY_MARGIN_MIN
            )

        buffer_remaining = remaining_window_mins - total_required_mins
        is_feasible = buffer_remaining >= 0

        feasibility_status = "RESCUE_FEASIBLE" if is_feasible else "AT_RISK"
        if buffer_remaining < -15.0 or remaining_window_mins <= 0:
            feasibility_status = "RESCUE_UNLIKELY"

        return {
            "is_feasible": is_feasible,
            "feasibility_status": feasibility_status,
            "remaining_window_minutes": round(remaining_window_mins, 1),
            "eta_to_donor_minutes": round(eta_to_donor, 1),
            "transit_to_ngo_minutes": round(transit_donor_to_ngo, 1),
            "total_required_minutes": round(total_required_mins, 1),
            "buffer_remaining_minutes": round(buffer_remaining, 1)
        }

    @staticmethod
    def check_assignment_telemetry_freshness(
        assignment: VolunteerAssignment,
        reference_time: Optional[datetime] = None,
        max_stale_minutes: float = TELEMETRY_STALE_MINUTES
    ) -> Dict[str, Any]:
        """
        Evaluates whether the assigned volunteer's location telemetry is fresh.
        IMPORTANT: Does NOT infer staleness from current_eta_minutes alone (e.g. current_eta_minutes=95 is NOT proof of stale GPS).
        Strictly inspects actual timestamps: assignment.last_location_update.
        """
        now = reference_time or _utcnow()
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        last_update = assignment.last_location_update
        if last_update is not None:
            if last_update.tzinfo is None:
                last_update = last_update.replace(tzinfo=timezone.utc)
            age_seconds = (now - last_update).total_seconds()
            age_minutes = max(0.0, age_seconds / 60.0)
            is_stale = age_minutes > max_stale_minutes
            return {
                "has_telemetry": True,
                "last_location_update": last_update.isoformat(),
                "telemetry_age_minutes": round(age_minutes, 1),
                "is_stale": is_stale,
                "reason": (
                    f"Telemetry is stale: last GPS ping was {age_minutes:.1f} minutes ago (threshold: {max_stale_minutes}m)."
                    if is_stale else "Telemetry is fresh."
                )
            }
        else:
            # Check elapsed time since assignment was accepted or created
            assigned_at = assignment.accepted_at or assignment.assigned_at
            if assigned_at:
                if assigned_at.tzinfo is None:
                    assigned_at = assigned_at.replace(tzinfo=timezone.utc)
                age_minutes = max(0.0, (now - assigned_at).total_seconds() / 60.0)
                is_stale = age_minutes > max_stale_minutes
            else:
                age_minutes = 0.0
                is_stale = False

            return {
                "has_telemetry": False,
                "last_location_update": None,
                "telemetry_age_minutes": round(age_minutes, 1),
                "is_stale": is_stale,
                "reason": (
                    f"No telemetry received since assignment ({age_minutes:.1f}m elapsed, threshold: {max_stale_minutes}m)."
                    if is_stale else "Assignment newly created; initial telemetry pending."
                )
            }

    @staticmethod
    def verify_active_assignment_health(
        db: Session,
        donation: FoodDonation,
        assignment: Optional[VolunteerAssignment] = None,
        reference_time: Optional[datetime] = None,
        max_stale_minutes: float = TELEMETRY_STALE_MINUTES
    ) -> Dict[str, Any]:
        """
        Comprehensive operational check across:
        1. Courier cancellation / failure status
        2. Vehicle problem / breakdown
        3. ETA logistics feasibility (mission_time <= ERW)
        4. Location telemetry freshness (actual timestamp check)
        5. Courier appropriateness (role, status, capacity)
        """
        now = reference_time or _utcnow()
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        if not assignment and donation.assigned_volunteer_id:
            assignment = db.query(VolunteerAssignment).filter(
                VolunteerAssignment.donation_id == donation.id,
                VolunteerAssignment.volunteer_id == donation.assigned_volunteer_id,
                VolunteerAssignment.status.in_(["assigned", "accepted", "en_route", "arrived", "collected", "in_transit"])
            ).first()

        if not assignment:
            return {
                "healthy": True,
                "requires_rematch": False,
                "trigger": "NO_ACTIVE_ASSIGNMENT",
                "reason": "No active volunteer assignment to evaluate.",
                "feasibility": None,
                "telemetry": None
            }

        vol = db.query(User).filter(User.id == assignment.volunteer_id).first()

        # Check 1: Courier cancellation or failed state
        if assignment.status in ["failed", "cancelled"] or donation.status in ["pickup_failed", "delivery_failed"]:
            fail_reason = assignment.failure_reason or donation.failure_reason or "Courier cancelled or reported task failure"
            trigger = (
                "VEHICLE_BREAKDOWN"
                if any(w in fail_reason.lower() for w in ["vehicle", "breakdown", "tyre", "puncture", "engine", "flat"])
                else "COURIER_CANCELLED"
            )
            is_post_coll = (donation.status in ["collected", "in_transit", "delivery_failed"]) or (assignment.status in ["collected", "in_transit", "delivery_failed"])
            return {
                "healthy": False,
                "requires_rematch": not is_post_coll,
                "trigger": trigger,
                "reason": fail_reason,
                "feasibility": None,
                "telemetry": None
            }

        # Check 2: Courier appropriateness (admin restriction or deactivation)
        if vol:
            if vol.admin_action_status == "RESTRICTED":
                return {
                    "healthy": False,
                    "requires_rematch": True,
                    "trigger": "COURIER_INAPPROPRIATE",
                    "reason": "Assigned courier account has been restricted by administrator.",
                    "feasibility": None,
                    "telemetry": None
                }
            if not vol.is_active:
                return {
                    "healthy": False,
                    "requires_rematch": True,
                    "trigger": "COURIER_INAPPROPRIATE",
                    "reason": "Assigned courier is no longer active on the platform.",
                    "feasibility": None,
                    "telemetry": None
                }
            if (vol.carrying_capacity or 50) < donation.quantity:
                return {
                    "healthy": False,
                    "requires_rematch": True,
                    "trigger": "COURIER_INAPPROPRIATE",
                    "reason": f"Courier carrying capacity ({vol.carrying_capacity} meals) insufficient for donation batch ({donation.quantity} meals).",
                    "feasibility": None,
                    "telemetry": None
                }

        # Check 3: Telemetry freshness (using actual timestamp, NOT inferred from ETA value)
        telemetry_eval = RematchingService.check_assignment_telemetry_freshness(
            assignment=assignment,
            reference_time=now,
            max_stale_minutes=max_stale_minutes
        )
        is_post_coll = (donation.status in ["collected", "in_transit"]) or (assignment.status in ["collected", "in_transit"])
        if assignment.status in ["assigned", "accepted", "en_route", "arrived", "collected", "in_transit"] and telemetry_eval["is_stale"]:
            if is_post_coll:
                donation.feasibility_status = "AT_RISK"
                return {
                    "healthy": False,
                    "requires_rematch": False,
                    "trigger": "STALE_TELEMETRY",
                    "reason": f"In-transit telemetry stale ({telemetry_eval['reason']}). Food already collected; courier update or admin check needed.",
                    "feasibility": None,
                    "telemetry": telemetry_eval
                }
            return {
                "healthy": False,
                "requires_rematch": True,
                "trigger": "STALE_TELEMETRY",
                "reason": telemetry_eval["reason"],
                "feasibility": None,
                "telemetry": telemetry_eval
            }

        # Check 4: Logistics feasibility (mission_time <= remaining ERW)
        feasibility_eval = RematchingService.evaluate_assignment_feasibility(
            db=db,
            donation=donation,
            assignment=assignment,
            volunteer=vol,
            reference_time=now
        )
        if not feasibility_eval["is_feasible"]:
            if is_post_coll:
                donation.feasibility_status = "AT_RISK"
                return {
                    "healthy": False,
                    "requires_rematch": False,
                    "trigger": "ETA_EXCEEDED_WINDOW",
                    "reason": f"In-transit mission time ({feasibility_eval['total_required_minutes']}m) exceeds remaining rescue window ({feasibility_eval['remaining_window_minutes']}m). Food already collected; escalated to NGO/admin.",
                    "feasibility": feasibility_eval,
                    "telemetry": telemetry_eval
                }
            return {
                "healthy": False,
                "requires_rematch": True,
                "trigger": "ETA_EXCEEDED_WINDOW",
                "reason": f"Total required mission time ({feasibility_eval['total_required_minutes']}m) exceeds remaining rescue window ({feasibility_eval['remaining_window_minutes']}m).",
                "feasibility": feasibility_eval,
                "telemetry": telemetry_eval
            }

        return {
            "healthy": True,
            "requires_rematch": False,
            "trigger": "NONE",
            "reason": "Assignment is healthy, feasible, and telemetry is fresh.",
            "feasibility": feasibility_eval,
            "telemetry": telemetry_eval
        }

    @staticmethod
    def find_feasible_backup_volunteers(
        db: Session,
        donation: FoodDonation,
        exclude_volunteer_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Hard-gated and ranked query for feasible backup volunteer couriers.
        """
        now = _utcnow()
        window_end = donation.estimated_window_end or donation.expiry_time
        if window_end:
            if window_end.tzinfo is None:
                window_end = window_end.replace(tzinfo=timezone.utc)
            remaining_window_mins = (window_end - now).total_seconds() / 60.0
        else:
            remaining_window_mins = float(donation.remaining_minutes or 60.0)

        # Donor & NGO coords
        donor_lat = donation.latitude or 12.9716
        donor_lon = donation.longitude or 77.5946
        ngo_lat = donation.assigned_ngo.latitude if donation.assigned_ngo else donor_lat
        ngo_lon = donation.assigned_ngo.longitude if donation.assigned_ngo else donor_lon

        candidates = db.query(User).filter(
            User.role == "volunteer",
            User.is_active == True,
            User.admin_action_status != "RESTRICTED"
        ).all()

        # Pre-filter 1: Cheap local filters (Role, Active, Restriction, Exclude failing, Capacity, Concurrency)
        filtered_candidates = []
        for vol in candidates:
            if exclude_volunteer_id and vol.id == exclude_volunteer_id:
                continue
            try:
                cap_val = float(vol.carrying_capacity) if getattr(vol, "carrying_capacity", None) is not None else 50.0
            except (ValueError, TypeError):
                cap_val = 50.0
            try:
                raw_qty = getattr(donation, "quantity", None) or getattr(donation, "quantity_kg", None) or 1.0
                qty_val = float(raw_qty)
            except (ValueError, TypeError):
                qty_val = 1.0
            if cap_val < qty_val:
                continue
            active_count = db.query(VolunteerAssignment).filter(
                VolunteerAssignment.volunteer_id == vol.id,
                VolunteerAssignment.status.in_(["assigned", "accepted", "en_route", "arrived", "collected", "in_transit"])
            ).count()
            if active_count >= 3:
                continue

            vol_lat = vol.latitude or donor_lat
            vol_lon = vol.longitude or donor_lon
            # Cheap straight-line proximity for initial bounding
            proximity_km = haversine_distance_km(vol_lat, vol_lon, donor_lat, donor_lon) or 999.0
            filtered_candidates.append((proximity_km, vol))

        # Sort by proximity and bound to top candidates to prevent external routing storms
        max_routed_candidates = getattr(settings, "ROUTING_MAX_CANDIDATES_PER_REMATCH", 5)
        filtered_candidates.sort(key=lambda x: x[0])
        bounded_candidates = [vol for _, vol in filtered_candidates[:max_routed_candidates]]

        # Compute Donor -> NGO leg once per transport mode (avoids redundant calls)
        donor_ngo_legs: Dict[str, Dict[str, Any]] = {}

        viable_ranked = []
        for vol in bounded_candidates:
            vol_lat = vol.latitude or donor_lat
            vol_lon = vol.longitude or donor_lon
            mode = vol.vehicle_type or "bike"

            # Route Leg 1: Volunteer -> Donor
            eta_res = route_service.calculate_eta(vol_lat, vol_lon, donor_lat, donor_lon, transport_mode=mode)
            eta_to_donor = eta_res.get("eta_minutes", 15)
            dist_to_donor = eta_res.get("distance_km", 5.0)

            # Route Leg 2: Donor -> NGO (computed once per mode or retrieved from cache)
            if mode not in donor_ngo_legs:
                donor_ngo_legs[mode] = route_service.calculate_eta(donor_lat, donor_lon, ngo_lat, ngo_lon, transport_mode=mode)
            ngo_leg = donor_ngo_legs[mode]
            transit_to_ngo = ngo_leg.get("eta_minutes", 20)

            total_mission_time = (
                eta_to_donor +
                HANDOVER_BUFFER_MIN +
                transit_to_ngo +
                NGO_INTAKE_BUFFER_MIN +
                CRITICAL_SAFETY_MARGIN_MIN
            )

            if total_mission_time > remaining_window_mins:
                # Infeasible: cannot complete mission before food rescue window closes
                continue

            # Ranking Formula:
            # Score = (Feasibility Buffer * 0.4) + (Reliability Score * 0.3) - (ETA * 0.2) - (Distance * 0.1)
            feasibility_buffer = remaining_window_mins - total_mission_time
            try:
                reliability = float(vol.reliability_score) if getattr(vol, "reliability_score", None) is not None else 95.0
            except (ValueError, TypeError):
                reliability = 95.0
            rank_score = (float(feasibility_buffer) * 2.0) + (reliability * 0.5) - (float(eta_to_donor) * 1.5) - (float(dist_to_donor) * 0.5)

            viable_ranked.append({
                "volunteer": vol,
                "volunteer_id": vol.id,
                "name": vol.name,
                "eta_minutes": eta_to_donor,
                "distance_km": dist_to_donor,
                "total_mission_time": total_mission_time,
                "feasibility_buffer": feasibility_buffer,
                "reliability_score": reliability,
                "rank_score": round(rank_score, 2)
            })

        # Sort descending by rank_score
        viable_ranked.sort(key=lambda x: x["rank_score"], reverse=True)
        return viable_ranked

    @staticmethod
    def attempt_dynamic_rematch(
        db: Session,
        donation: FoodDonation,
        trigger: str = "ETA_EXCEEDED_WINDOW",
        reason: str = "Estimated arrival time exceeded remaining rescue window"
    ) -> Dict[str, Any]:
        """
        Executes atomic dynamic rematching:
        - Locks donation row
        - Safely retires previous assignment
        - Dispatches top feasible backup volunteer
        - Dispatches trilingual non-blaming notifications
        """
        now = _utcnow()
        old_volunteer_id = donation.assigned_volunteer_id

        # Guard: Check donation eligibility for dynamic donor pickup rematch
        if donation.status in ["collected", "in_transit"]:
            logger.warning(
                f"[Dynamic Rematch] Donation #{donation.id} is already in '{donation.status}' state "
                f"(food collected from donor). Dynamic donor rematch is not applicable post-collection."
            )
            donation.feasibility_status = "AT_RISK"
            db.commit()
            return {
                "donation_id": donation.id,
                "status": "NOT_APPLICABLE_POST_COLLECTION",
                "rematch_count": donation.rematch_count or 0,
                "rematch_reason": reason,
                "feasibility_status": "AT_RISK",
                "message": f"Donation #{donation.id} is already '{donation.status}' (food already collected from donor). Automatic donor rematch cannot be executed post-collection."
            }

        if donation.status in ["delivered", "partially_distributed", "completed", "cancelled", "expired", "delivery_failed"]:
            logger.warning(
                f"[Dynamic Rematch] Donation #{donation.id} is in non-rematchable state '{donation.status}'."
            )
            return {
                "donation_id": donation.id,
                "status": "INELIGIBLE_STATE",
                "rematch_count": donation.rematch_count or 0,
                "rematch_reason": reason,
                "feasibility_status": donation.feasibility_status or "TERMINAL",
                "message": f"Donation #{donation.id} is in state '{donation.status}'. Dynamic rematch is only applicable for pre-collection active rescues."
            }

        # 1. Look for backup volunteers
        viable_candidates = RematchingService.find_feasible_backup_volunteers(
            db=db,
            donation=donation,
            exclude_volunteer_id=old_volunteer_id
        )

        if not viable_candidates:
            # No viable candidate found — mark at risk and escalate to admin
            donation.feasibility_status = "AT_RISK"
            log_audit_event(
                db=db,
                action="rematch_failed_no_candidates",
                user_id=old_volunteer_id,
                resource_type="donation",
                resource_id=donation.id,
                status_code="failed",
                details=f"Dynamic rematch attempted for donation {donation.id} but no feasible volunteer found. Reason: {reason}"
            )
            # Notify Admin
            admin_users = db.query(User).filter(User.role == "admin").all()
            for admin in admin_users:
                create_notification(
                    db=db,
                    user_id=admin.id,
                    title="🚨 Urgent: Rescue Rematch Infeasible",
                    message=f"Donation #{donation.id} ('{donation.food_name}') route is at risk with no feasible backup volunteers. Manual intervention required.",
                    type="emergency",
                    related_donation_id=donation.id
                )
            db.commit()
            return {
                "donation_id": donation.id,
                "status": "NO_VOLUNTEER_AVAILABLE",
                "rematch_count": donation.rematch_count or 0,
                "rematch_reason": reason,
                "feasibility_status": "AT_RISK",
                "notifications_dispatched": ["admin_escalation"],
                "message": "No feasible backup volunteer found with sufficient time and capacity. Escalated to Administrator."
            }

        # 2. Select top ranked candidate
        best_match = viable_candidates[0]
        new_volunteer = best_match["volunteer"]
        new_eta = best_match["eta_minutes"]

        # 3. Safely transition existing active assignments
        existing_assignments = db.query(VolunteerAssignment).filter(
            VolunteerAssignment.donation_id == donation.id,
            VolunteerAssignment.status.in_(["assigned", "accepted", "en_route", "arrived"])
        ).all()

        for old_assign in existing_assignments:
            transition_assignment_status(
                db, old_assign, "reassigned",
                changed_by_user_id=new_volunteer.id,
                caller_role="system",
                remarks=f"Reassigned: {reason}"
            )
            old_assign.is_reassigned = True
            old_assign.reassign_reason = reason
            old_assign.reassigned_at = now

        # 4. Create new assignment for backup volunteer
        new_assignment = VolunteerAssignment(
            donation_id=donation.id,
            volunteer_id=new_volunteer.id,
            status="assigned",
            assigned_at=now,
            current_eta_minutes=float(new_eta),
            current_distance_km=float(best_match["distance_km"])
        )
        db.add(new_assignment)

        # 5. Update donation record
        donation.previous_volunteer_id = old_volunteer_id
        donation.assigned_volunteer_id = new_volunteer.id
        donation.rematch_count = (donation.rematch_count or 0) + 1
        donation.rematch_reason = reason
        donation.is_rematched = True
        donation.feasibility_status = "RESCUE_FEASIBLE"
        donation.current_eta_minutes = float(new_eta)
        donation.current_distance_km = float(best_match["distance_km"])
        donation.last_feasibility_check_at = now

        transition_donation_status(
            db, donation, "volunteer_assigned",
            changed_by_user_id=new_volunteer.id,
            caller_role="system",
            remarks=f"Dynamic rematch executed: Reassigned from Volunteer #{old_volunteer_id} to Volunteer #{new_volunteer.id} ({new_volunteer.name}) due to feasibility optimization."
        )

        # 7. Audit log
        log_audit_event(
            db=db,
            action="dynamic_rematch_executed",
            user_id=new_volunteer.id,
            resource_type="donation",
            resource_id=donation.id,
            status_code="success",
            details=f"Donation #{donation.id} rematched: Old Vol #{old_volunteer_id} -> New Vol #{new_volunteer.id} (ETA: {new_eta}m, Trigger: {trigger})"
        )
        log_rescue_operation(
            db=db,
            action="reassigned",
            donation_id=donation.id,
            user_id=new_volunteer.id,
            old_status="volunteer_assigned",
            new_status="volunteer_assigned",
            remarks=f"Reassigned from Volunteer #{old_volunteer_id} to Volunteer #{new_volunteer.id}",
            details=f"Dynamic rematch reassigned to Volunteer #{new_volunteer.id}. Trigger: {trigger}"
        )

        # 8. Dispatch Trilingual Notifications (Non-blaming & Privacy safe)
        notifications_sent = []

        # A. Donor Notification
        donor = donation.donor
        donor_lang = (donor.preferred_language if donor else "en") or "en"
        donor_msg = (
            "Your food rescue is being re-optimized. We found another feasible pickup partner to ensure timely collection."
            if donor_lang == "en" else
            "உங்கள் உணவு மீட்பு திட்டம் மறுசீரமைக்கப்படுகிறது. சரியான நேரத்தில் சேகரிக்க மாற்று தன்னார்வலர் நியமிக்கப்பட்டுள்ளார்."
            if donor_lang == "ta" else
            "आपका भोजन बचाव पुनर्गठित किया जा रहा है। समय पर संग्रहण सुनिश्चित करने के लिए एक वैकल्पिक साथी नियुक्त किया गया है।"
        )
        create_event_notification(
            db=db,
            user_id=donation.donor_id,
            event_type="RESCUE_REMATCHED_DONOR",
            donation_id=donation.id,
            lang=donor_lang,
            extra_message=donor_msg
        )
        notifications_sent.append("donor")

        # B. NGO Notification
        if donation.assigned_ngo and donation.assigned_ngo.user_id:
            ngo_user = donation.assigned_ngo.user
            ngo_lang = (ngo_user.preferred_language if ngo_user else "en") or "en"
            ngo_msg = (
                f"Pickup plan updated for '{donation.food_name}'. New volunteer assigned (ETA: ~{new_eta} min)."
                if ngo_lang == "en" else
                f"'{donation.food_name}' பிக்கப் திட்டம் புதுப்பிக்கப்பட்டது. புதிய தன்னார்வலர் நியமிக்கப்பட்டார் (ETA: ~{new_eta} நிமி)."
                if ngo_lang == "ta" else
                f"'{donation.food_name}' के लिए पिकअप योजना अपडेट की गई। नया स्वयंसेवक नियुक्त किया गया (ETA: ~{new_eta} मिनट)।"
            )
            create_event_notification(
                db=db,
                user_id=donation.assigned_ngo.user_id,
                event_type="RESCUE_REMATCHED_NGO",
                donation_id=donation.id,
                lang=ngo_lang,
                extra_message=ngo_msg
            )
            notifications_sent.append("ngo")

        # C. New Volunteer Notification
        new_vol_lang = (new_volunteer.preferred_language or "en").lower()
        new_vol_msg = (
            f"New rescue task assigned: '{donation.food_name}' ({int(donation.quantity)} {donation.quantity_unit}). Tap to view pickup."
            if new_vol_lang == "en" else
            f"புதிய மீட்பு பணி: '{donation.food_name}' ({int(donation.quantity)} {donation.quantity_unit}). பிக்கப் விவரங்களைக் காண தொடவும்."
            if new_vol_lang == "ta" else
            f"नया बचाव कार्य: '{donation.food_name}' ({int(donation.quantity)} {donation.quantity_unit})। पिकअप देखने के लिए टैप करें।"
        )
        create_event_notification(
            db=db,
            user_id=new_volunteer.id,
            event_type="NEW_TASK_REMATCHED_NEW_VOLUNTEER",
            donation_id=donation.id,
            lang=new_vol_lang,
            extra_message=new_vol_msg
        )
        notifications_sent.append("new_volunteer")

        # D. Old Volunteer Notification
        if old_volunteer_id:
            old_vol = db.query(User).filter(User.id == old_volunteer_id).first()
            old_vol_lang = (old_vol.preferred_language if old_vol else "en") or "en"
            old_vol_msg = (
                f"Your pickup assignment for '{donation.food_name}' has been updated and reassigned to maintain rescue timeline."
                if old_vol_lang == "en" else
                f"'{donation.food_name}' பிக்கப் பணி காலக்கெடுவை பராமரிக்க மாற்றியமைக்கப்பட்டுள்ளது."
                if old_vol_lang == "ta" else
                f"'{donation.food_name}' के लिए आपका पिकअप कार्य समय सीमा बनाए रखने के लिए फिर से असाइन किया गया है।"
            )
            create_event_notification(
                db=db,
                user_id=old_volunteer_id,
                event_type="TASK_REASSIGNED_OLD_VOLUNTEER",
                donation_id=donation.id,
                lang=old_vol_lang,
                extra_message=old_vol_msg
            )
            notifications_sent.append("old_volunteer")

        # E. Admin Notification
        admin_users = db.query(User).filter(User.role == "admin").all()
        for admin in admin_users:
            create_event_notification(
                db=db,
                user_id=admin.id,
                event_type="RESCUE_AT_RISK_ADMIN",
                donation_id=donation.id,
                lang=(admin.preferred_language or "en"),
                extra_message=f"Donation #{donation.id} automatically rematched: Vol #{old_volunteer_id} -> Vol #{new_volunteer.id} ({new_volunteer.name}, ETA {new_eta}m)."
            )
        notifications_sent.append("admin")

        db.commit()
        db.refresh(donation)

        return {
            "donation_id": donation.id,
            "status": "REMATCHED",
            "rematch_count": donation.rematch_count,
            "previous_volunteer_id": old_volunteer_id,
            "previous_volunteer_name": old_vol.name if (old_volunteer_id and 'old_vol' in locals() and old_vol) else None,
            "new_volunteer_id": new_volunteer.id,
            "new_volunteer_name": new_volunteer.name,
            "rematch_reason": reason,
            "new_eta_minutes": new_eta,
            "feasibility_status": "RESCUE_FEASIBLE",
            "notifications_dispatched": notifications_sent,
            "message": f"Successfully rematched rescue to Volunteer '{new_volunteer.name}' with feasible ETA (~{new_eta} min)."
        }


rematching_service = RematchingService()
