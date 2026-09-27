"""
LiveTrackingService — Smart Food Rescue
========================================
Real-time operational tracking, battery-conscious location telemetry ingestion,
urban-calibrated ETA calculation, privacy-filtered operational views, and
continuous feasibility monitoring.
"""

import math
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List, Tuple
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.models import (
    FoodDonation, VolunteerAssignment, User, NGO, DonationHistory, AuditLog
)
from app.services.route_service import route_service, haversine_distance_km
from app.services.food_rescue_window_service import calculate_rescue_feasibility
from app.services.security_service import log_audit_event
from app.services.notification_service import create_event_notification

logger = logging.getLogger("smart_food_rescue.live_tracking")

# Proximity threshold in km (250 meters)
PROXIMITY_ARRIVAL_KM = 0.25

# Stage keys for timeline
TRACKING_STAGES = [
    {"key": "POSTED", "title": "Donation Posted", "desc": "Food surplus listed with advisory rescue window"},
    {"key": "NGO_ACCEPTED", "title": "NGO Accepted", "desc": "Partner NGO confirmed capacity & receipt intent"},
    {"key": "VOLUNTEER_ASSIGNED", "title": "Volunteer Assigned", "desc": "Courier matched with vehicle capacity"},
    {"key": "EN_ROUTE", "title": "Volunteer On The Way", "desc": "Volunteer traveling to donor pickup location"},
    {"key": "ARRIVED_AT_DONOR", "title": "Arrived At Donor", "desc": "Volunteer reached pickup point for OTP handover"},
    {"key": "FOOD_COLLECTED", "title": "Food Collected", "desc": "OTP verified and food safely packaged for transit"},
    {"key": "IN_TRANSIT", "title": "Food In Transit", "desc": "Food being transported to receiving NGO facility"},
    {"key": "ARRIVED_AT_NGO", "title": "Arrived At NGO", "desc": "Volunteer arrived at NGO facility for delivery"},
    {"key": "DELIVERED", "title": "Delivered to NGO", "desc": "Food inspected and safely received by NGO"},
    {"key": "DISTRIBUTION", "title": "Distributed to Beneficiaries", "desc": "Meals distributed to community members"}
]


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _mask_approximate_address(full_address: Optional[str]) -> str:
    """Masks exact door/flat numbers for privacy until authorized."""
    if not full_address:
        return "Nearby Neighborhood Area"
    parts = [p.strip() for p in full_address.split(",") if p.strip()]
    if len(parts) >= 3:
        return f"{parts[-2]} Area"
    elif len(parts) == 2:
        return f"{parts[0]} Area"
    return f"{full_address} Area"


class LiveTrackingService:
    """
    Core engine for real-time tracking, ETA updates, and feasibility monitoring.
    """

    @staticmethod
    def update_volunteer_location(
        db: Session,
        volunteer_user: User,
        latitude: float,
        longitude: float,
        donation_id: Optional[int] = None,
        assignment_id: Optional[int] = None,
        speed_kmh: Optional[float] = None,
        heading: Optional[float] = None,
        battery_level: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Updates volunteer coordinates, recalculates realistic ETA, detects arrival proximity,
        and rechecks rescue feasibility.
        """
        now = _utcnow()

        # 1. Resolve active assignment
        query = db.query(VolunteerAssignment).filter(
            VolunteerAssignment.volunteer_id == volunteer_user.id,
            VolunteerAssignment.status.in_(["assigned", "accepted", "en_route", "arrived", "collected", "in_transit"])
        )
        if assignment_id:
            query = query.filter(VolunteerAssignment.id == assignment_id)
        elif donation_id:
            query = query.filter(VolunteerAssignment.donation_id == donation_id)

        assignment = query.first()
        if not assignment:
            # Check if admin is updating
            if volunteer_user.role == "admin" and donation_id:
                assignment = db.query(VolunteerAssignment).filter(
                    VolunteerAssignment.donation_id == donation_id,
                    VolunteerAssignment.status.in_(["assigned", "accepted", "en_route", "arrived", "collected", "in_transit"])
                ).first()
            if not assignment:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="No active rescue assignment found for this volunteer."
                )

        donation = db.query(FoodDonation).filter(FoodDonation.id == assignment.donation_id).first()
        if not donation:
            raise HTTPException(status_code=404, detail="Donation not found.")

        # 2. Update volunteer user and assignment location
        volunteer_user.latitude = latitude
        volunteer_user.longitude = longitude
        assignment.last_known_lat = latitude
        assignment.last_known_lon = longitude
        assignment.last_location_update = now

        # 3. Calculate destination coordinates & ETA
        transport_mode = volunteer_user.vehicle_type or "bike"
        target_lat = donation.latitude
        target_lon = donation.longitude
        stage = donation.status.lower()

        # If already collected, destination is the NGO
        if stage in ["collected", "in_transit"]:
            if donation.assigned_ngo:
                target_lat = donation.assigned_ngo.latitude or target_lat
                target_lon = donation.assigned_ngo.longitude or target_lon

        eta_calc = route_service.calculate_eta(
            origin_lat=latitude,
            origin_lon=longitude,
            dest_lat=target_lat,
            dest_lon=target_lon,
            transport_mode=transport_mode
        )

        eta_minutes = eta_calc["eta_minutes"]
        distance_km = eta_calc["distance_km"]

        # Update assignment and donation tracking fields
        assignment.current_eta_minutes = float(eta_minutes)
        assignment.current_distance_km = float(distance_km)

        donation.tracking_latitude = latitude
        donation.tracking_longitude = longitude
        donation.tracking_last_updated_at = now
        donation.current_eta_minutes = float(eta_minutes)
        donation.current_distance_km = float(distance_km)

        # 4. Proximity Arrival Detection
        straight_dist = haversine_distance_km(latitude, longitude, target_lat, target_lon)
        if straight_dist is not None and straight_dist <= PROXIMITY_ARRIVAL_KM:
            if stage in ["volunteer_assigned", "assigned", "accepted", "en_route", "pickup_en_route"]:
                donation.tracking_status = "ARRIVED_AT_DONOR"
                create_event_notification(
                    db=db,
                    user_id=donation.donor_id,
                    event_type="VOLUNTEER_ARRIVING",
                    donation_id=donation.id,
                )
            elif stage in ["in_transit", "collected"]:
                donation.tracking_status = "ARRIVED_AT_NGO"
        else:
            if stage in ["volunteer_assigned", "assigned", "accepted", "en_route", "pickup_en_route"]:
                donation.tracking_status = "EN_ROUTE"
            elif stage in ["in_transit", "collected"]:
                donation.tracking_status = "IN_TRANSIT"

        # 5. Continuous Feasibility Re-check
        from app.services.rematching_service import rematching_service

        feasibility_result = rematching_service.evaluate_assignment_feasibility(
            db=db,
            donation=donation,
            assignment=assignment,
            current_eta_minutes=eta_minutes
        )

        rematch_triggered = False
        rematch_info = None

        if feasibility_result["feasibility_status"] in ["AT_RISK", "RESCUE_UNLIKELY"]:
            donation.feasibility_status = "AT_RISK"
            # Trigger automatic dynamic rematching
            rematch_response = rematching_service.attempt_dynamic_rematch(
                db=db,
                donation=donation,
                trigger="ETA_EXCEEDED_WINDOW",
                reason=f"Volunteer ETA ({eta_minutes} min) exceeded remaining rescue window"
            )
            rematch_triggered = rematch_response.get("status") == "REMATCHED"
            rematch_info = rematch_response

        db.commit()
        db.refresh(donation)
        db.refresh(assignment)

        return {
            "success": True,
            "donation_id": donation.id,
            "assignment_id": assignment.id,
            "tracking_status": donation.tracking_status,
            "eta_minutes": eta_minutes,
            "distance_km": distance_km,
            "feasibility_status": donation.feasibility_status,
            "is_at_risk": donation.feasibility_status == "AT_RISK",
            "rematch_triggered": rematch_triggered,
            "rematch_info": rematch_info,
            "updated_at": now.isoformat()
        }

    @staticmethod
    def get_tracking_data(
        db: Session,
        donation_id: int,
        current_user: User
    ) -> Dict[str, Any]:
        """
        Builds role-based, privacy-filtered real-time tracking representation.
        """
        donation = db.query(FoodDonation).filter(FoodDonation.id == donation_id).first()
        if not donation:
            raise HTTPException(status_code=404, detail="Donation not found.")

        # RBAC and Visibility Verification
        role = current_user.role
        is_owner_donor = (role == "donor" and donation.donor_id == current_user.id)
        is_assigned_ngo = (role == "ngo" and donation.assigned_ngo and donation.assigned_ngo.user_id == current_user.id)
        is_assigned_vol = (role == "volunteer" and donation.assigned_volunteer_id == current_user.id)
        is_admin = (role == "admin")

        if not (is_owner_donor or is_assigned_ngo or is_assigned_vol or is_admin):
            # Check if unassigned volunteer viewing before accepting
            if role != "volunteer":
                raise HTTPException(status_code=403, detail="Not authorized to access tracking for this rescue.")

        # Resolve active volunteer & assignment
        vol_user = donation.assigned_volunteer
        active_assignment = db.query(VolunteerAssignment).filter(
            VolunteerAssignment.donation_id == donation.id,
            VolunteerAssignment.status.in_(["assigned", "accepted", "en_route", "arrived", "collected", "in_transit", "delivered"])
        ).order_by(VolunteerAssignment.id.desc()).first()

        # Compute remaining rescue window
        now = _utcnow()
        window_end = donation.estimated_window_end or donation.expiry_time
        if window_end:
            if window_end.tzinfo is None:
                window_end = window_end.replace(tzinfo=timezone.utc)
            remaining_mins = max(0, int((window_end - now).total_seconds() / 60))
        else:
            remaining_mins = donation.remaining_minutes or 60

        # Determine tracking stage & labels
        raw_st = donation.status.lower()
        tracking_stage = "PENDING"
        stage_label = "Pending NGO Acceptance"
        next_prompt = "Awaiting nearby NGO review."

        if raw_st == "accepted":
            tracking_stage = "NGO_ACCEPTED"
            stage_label = "NGO Accepted ✓"
            next_prompt = "Matching available volunteer with appropriate transport."
        elif raw_st in ["volunteer_assigned"]:
            tracking_stage = "VOLUNTEER_ASSIGNED"
            stage_label = "Volunteer Assigned"
            next_prompt = "Volunteer is preparing to start navigation."
        elif raw_st in ["pickup_en_route", "en_route"]:
            tracking_stage = "EN_ROUTE"
            stage_label = "Volunteer On The Way 🚴"
            next_prompt = "Volunteer is traveling to pickup location. Please keep food packaged."
        elif raw_st in ["arrived_at_donor", "arrived"]:
            tracking_stage = "ARRIVED_AT_DONOR"
            stage_label = "Volunteer Arrived 📍"
            next_prompt = "Volunteer has arrived. Share the 6-digit pickup OTP to verify handover."
        elif raw_st in ["collected"]:
            tracking_stage = "FOOD_COLLECTED"
            stage_label = "Food Collected ✓"
            next_prompt = "Food collected securely. Transport to NGO starting."
        elif raw_st in ["in_transit", "transit"]:
            tracking_stage = "IN_TRANSIT"
            stage_label = "Food In Transit 🚚"
            next_prompt = "Food is on its way to the partner NGO facility."
        elif raw_st in ["arrived_at_ngo"]:
            tracking_stage = "ARRIVED_AT_NGO"
            stage_label = "Arrived At NGO 📍"
            next_prompt = "Volunteer arrived at NGO facility. Intake inspection in progress."
        elif raw_st in ["delivered"]:
            tracking_stage = "DELIVERED"
            stage_label = "Delivered to NGO ✓"
            next_prompt = "Food safely received. NGO will record distribution to beneficiaries."
        elif raw_st in ["completed"]:
            tracking_stage = "COMPLETED"
            stage_label = "Rescue Complete 🎉"
            next_prompt = "All meals distributed! Thank you for reducing food waste."
        elif raw_st in ["cancelled", "pickup_failed", "delivery_failed", "expired"]:
            tracking_stage = raw_st.upper()
            stage_label = raw_st.replace("_", " ").title()
            next_prompt = f"Status: {donation.failure_reason or 'Task concluded.'}"

        # Privacy rules for coordinates and addresses
        vol_lat = None
        vol_lon = None
        pickup_addr = _mask_approximate_address(donation.pickup_address)
        dest_name = donation.assigned_ngo.organization_name if donation.assigned_ngo else "Partner NGO"
        dest_addr = _mask_approximate_address(donation.assigned_ngo.address if donation.assigned_ngo else "")

        if is_admin or is_assigned_vol:
            pickup_addr = donation.pickup_address
            if donation.assigned_ngo and donation.assigned_ngo.address:
                dest_addr = donation.assigned_ngo.address

        if is_owner_donor and donation.status not in ["pending"]:
            pickup_addr = donation.pickup_address

        if is_admin or is_assigned_vol or is_owner_donor or is_assigned_ngo:
            vol_lat = donation.tracking_latitude or (vol_user.latitude if vol_user else None)
            vol_lon = donation.tracking_longitude or (vol_user.longitude if vol_user else None)

        # ETA Display formatting
        current_eta = donation.current_eta_minutes
        if current_eta is None and vol_lat and vol_lon and donation.latitude and donation.longitude:
            eta_res = route_service.calculate_eta(vol_lat, vol_lon, donation.latitude, donation.longitude)
            current_eta = eta_res["eta_minutes"]

        eta_int = int(current_eta) if current_eta is not None else None
        eta_display = f"{eta_int} min (Estimated travel time)" if eta_int is not None else None

        # Build Stage Timeline
        stages_order = [
            ("POSTED", ["pending", "accepted", "volunteer_assigned", "en_route", "pickup_en_route", "arrived_at_donor", "arrived", "collected", "in_transit", "delivered", "completed"]),
            ("NGO_ACCEPTED", ["accepted", "volunteer_assigned", "en_route", "pickup_en_route", "arrived_at_donor", "arrived", "collected", "in_transit", "delivered", "completed"]),
            ("VOLUNTEER_ASSIGNED", ["volunteer_assigned", "en_route", "pickup_en_route", "arrived_at_donor", "arrived", "collected", "in_transit", "delivered", "completed"]),
            ("EN_ROUTE", ["en_route", "pickup_en_route", "arrived_at_donor", "arrived", "collected", "in_transit", "delivered", "completed"]),
            ("ARRIVED_AT_DONOR", ["arrived_at_donor", "arrived", "collected", "in_transit", "delivered", "completed"]),
            ("FOOD_COLLECTED", ["collected", "in_transit", "delivered", "completed"]),
            ("IN_TRANSIT", ["in_transit", "delivered", "completed"]),
            ("DELIVERED", ["delivered", "completed"]),
            ("DISTRIBUTION", ["completed"])
        ]

        timeline_items = []
        for stage_k, passed_statuses in stages_order:
            meta = next((s for s in TRACKING_STAGES if s["key"] == stage_k), None)
            if not meta:
                continue
            is_comp = raw_st in passed_statuses and raw_st != "pending"
            is_curr = (tracking_stage == stage_k)
            timeline_items.append({
                "key": stage_k,
                "title": meta["title"],
                "description": meta["desc"],
                "is_completed": is_comp,
                "is_current": is_curr,
                "timestamp": now.isoformat() if is_curr else None
            })

        # Rematch Notice copy (friendly, non-blaming)
        rematch_notice = None
        if donation.is_rematched or (donation.rematch_count or 0) > 0:
            if role == "donor":
                rematch_notice = "Your rescue is being re-optimized. Your previous pickup route became delayed, and we found another feasible rescue partner."
            elif role == "ngo":
                rematch_notice = "Pickup assignment updated. A newly available volunteer has been dispatched."
            elif role == "volunteer":
                rematch_notice = "Pickup assignment updated."
            else:
                rematch_notice = f"Donation rematched ({donation.rematch_count}x). Reason: {donation.rematch_reason or 'Feasibility risk'}"

        return {
            "donation_id": donation.id,
            "food_name": donation.food_name,
            "quantity": donation.quantity,
            "quantity_unit": donation.quantity_unit,
            "status": donation.status,
            "tracking_stage": tracking_stage,
            "tracking_stage_label": stage_label,
            "volunteer_id": vol_user.id if vol_user else None,
            "volunteer_name": vol_user.name if vol_user else None,
            "volunteer_vehicle": vol_user.vehicle_type if vol_user else "bike",
            "volunteer_status": active_assignment.status if active_assignment else None,
            "volunteer_latitude": vol_lat,
            "volunteer_longitude": vol_lon,
            "pickup_address": pickup_addr,
            "destination_name": dest_name,
            "destination_address": dest_addr,
            "eta_minutes": eta_int,
            "eta_display": eta_display,
            "distance_km": donation.current_distance_km,
            "remaining_window_minutes": remaining_mins,
            "rescue_urgency_level": donation.rescue_urgency_level or "FRESH",
            "feasibility_status": donation.feasibility_status or "RESCUE_FEASIBLE",
            "feasibility_label": "Rescue Feasible" if donation.feasibility_status == "RESCUE_FEASIBLE" else "Rescue At Risk ⚠️",
            "is_rematched": bool(donation.is_rematched),
            "rematch_count": donation.rematch_count or 0,
            "rematch_reason": donation.rematch_reason,
            "rematch_notice": rematch_notice,
            "last_updated_at": donation.tracking_last_updated_at or now,
            "next_action_prompt": next_prompt,
            "stages_timeline": timeline_items
        }


live_tracking_service = LiveTrackingService()
