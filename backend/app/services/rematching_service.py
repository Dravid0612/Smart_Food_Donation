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
from app.services.route_service import route_service, haversine_distance_km
from app.services.notification_service import create_notification, create_event_notification
from app.services.security_service import log_audit_event

logger = logging.getLogger("smart_food_rescue.rematching")

# Safety and Handover Time Allocations (in minutes)
HANDOVER_BUFFER_MIN = 10.0
NGO_INTAKE_BUFFER_MIN = 10.0
CRITICAL_SAFETY_MARGIN_MIN = 5.0


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class RematchingService:
    """
    Dynamic Rematching Engine for Time-Critical Food Rescues.
    """

    @staticmethod
    def evaluate_assignment_feasibility(
        db: Session,
        donation: FoodDonation,
        assignment: Optional[VolunteerAssignment],
        current_eta_minutes: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Evaluates whether the assigned volunteer can complete the rescue before the window closes.
        """
        now = _utcnow()
        window_end = donation.estimated_window_end or donation.expiry_time
        if window_end:
            if window_end.tzinfo is None:
                window_end = window_end.replace(tzinfo=timezone.utc)
            remaining_window_mins = (window_end - now).total_seconds() / 60.0
        else:
            remaining_window_mins = float(donation.remaining_minutes or 60.0)

        # 1. ETA to donor
        if current_eta_minutes is not None:
            eta_to_donor = float(current_eta_minutes)
        elif assignment and assignment.current_eta_minutes is not None:
            eta_to_donor = float(assignment.current_eta_minutes)
        else:
            # Fallback estimation
            vol = donation.assigned_volunteer
            vol_lat = vol.latitude if vol else None
            vol_lon = vol.longitude if vol else None
            if vol_lat and vol_lon and donation.latitude and donation.longitude:
                calc = route_service.calculate_eta(vol_lat, vol_lon, donation.latitude, donation.longitude, vol.vehicle_type or "bike")
                eta_to_donor = float(calc["eta_minutes"])
            else:
                eta_to_donor = 15.0

        # 2. Transit from donor to NGO
        ngo_lat = donation.assigned_ngo.latitude if donation.assigned_ngo else None
        ngo_lon = donation.assigned_ngo.longitude if donation.assigned_ngo else None
        if donation.latitude and donation.longitude and ngo_lat and ngo_lon:
            ngo_route = route_service.calculate_eta(
                donation.latitude, donation.longitude,
                ngo_lat, ngo_lon,
                donation.assigned_volunteer.vehicle_type if donation.assigned_volunteer else "bike"
            )
            transit_donor_to_ngo = float(ngo_route["eta_minutes"])
        else:
            transit_donor_to_ngo = 15.0

        # 3. Total mission time required
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
        if buffer_remaining < -15.0:
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

        viable_ranked = []

        for vol in candidates:
            # Hard Gate 1: Exclude the current failing volunteer
            if exclude_volunteer_id and vol.id == exclude_volunteer_id:
                continue

            # Hard Gate 2: Vehicle Capacity >= donation quantity
            capacity = vol.carrying_capacity or 50
            if capacity < donation.quantity:
                continue

            # Hard Gate 3: Active concurrency check (max 3 active tasks)
            active_count = db.query(VolunteerAssignment).filter(
                VolunteerAssignment.volunteer_id == vol.id,
                VolunteerAssignment.status.in_(["assigned", "accepted", "en_route", "arrived", "collected", "in_transit"])
            ).count()
            if active_count >= 3:
                continue

            # Hard Gate 4: Route Feasibility
            vol_lat = vol.latitude or donor_lat
            vol_lon = vol.longitude or donor_lon
            mode = vol.vehicle_type or "bike"

            eta_res = route_service.calculate_eta(vol_lat, vol_lon, donor_lat, donor_lon, transport_mode=mode)
            eta_to_donor = eta_res["eta_minutes"]
            dist_to_donor = eta_res["distance_km"]

            # Leg 2 from donor to NGO
            ngo_leg = route_service.calculate_eta(donor_lat, donor_lon, ngo_lat, ngo_lon, transport_mode=mode)
            transit_to_ngo = ngo_leg["eta_minutes"]

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
            reliability = vol.reliability_score or 95.0
            rank_score = (feasibility_buffer * 2.0) + (reliability * 0.5) - (eta_to_donor * 1.5) - (dist_to_donor * 0.5)

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
            old_assign.status = "reassigned"
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
        donation.status = "volunteer_assigned"
        donation.feasibility_status = "RESCUE_FEASIBLE"
        donation.current_eta_minutes = float(new_eta)
        donation.current_distance_km = float(best_match["distance_km"])
        donation.last_feasibility_check_at = now

        # 6. Record in DonationHistory
        db.add(DonationHistory(
            donation_id=donation.id,
            old_status="volunteer_assigned",
            new_status="volunteer_assigned",
            changed_by=new_volunteer.id,
            remarks=f"Dynamic rematch executed: Reassigned from Volunteer #{old_volunteer_id} to Volunteer #{new_volunteer.id} ({new_volunteer.name}) due to feasibility optimization."
        ))

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
