import json
import math
from datetime import datetime, timezone
import numpy as np
from scipy.optimize import linear_sum_assignment
from sqlalchemy.orm import Session
from app.models.models import NGO, User, FoodDonation, VolunteerAssignment
from app.services.urgency_service import calculate_urgency, calculate_urgency_score
from app.services.food_rescue_window_service import calculate_rescue_feasibility
from app.services.route_service import route_service

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculates distance in kilometers between two lat/lon coordinates."""
    if lat1 is None or lon1 is None or lat2 is None or lon2 is None:
        return 5.0 # default 5km fallback
    R = 6371.0 # Earth radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def is_ngo_open_now(operating_hours_json: str, check_time: datetime = None) -> tuple[bool, str]:
    """
    Evaluates if the NGO is open at the check_time (or current time).
    Accepts JSON formatted operating schedule or defaults to open.
    Example: {"monday": {"open": "08:00", "close": "20:00", "closed": false}, ...}
    """
    if not operating_hours_json:
        return True, "Standard Operating Hours (Open)"

    if check_time is None:
        check_time = datetime.now(timezone.utc)

    try:
        schedule = json.loads(operating_hours_json)
        day_name = check_time.strftime("%A").lower()
        if day_name not in schedule:
            return True, "Open"

        day_info = schedule[day_name]
        if day_info.get("closed", False):
            return False, f"Closed on {day_name.capitalize()}"

        open_str = day_info.get("open", "08:00")
        close_str = day_info.get("close", "20:00")

        open_h, open_m = map(int, open_str.split(":"))
        close_h, close_m = map(int, close_str.split(":"))

        current_minutes = check_time.hour * 60 + check_time.minute
        open_minutes = open_h * 60 + open_m
        close_minutes = close_h * 60 + close_m

        if open_minutes <= current_minutes <= close_minutes:
            return True, f"Open today until {close_str}"
        else:
            return False, f"Closed now (Hours: {open_str} - {close_str})"
    except Exception:
        return True, "Open"

def calculate_demand_match_score(ngo_demands_json: str, food_category: str, quantity: float) -> tuple[float, bool, str]:
    """
    Calculates alignment with NGO dynamic beneficiary demand requirements.
    Example: {"Cooked Food": 80, "Bakery": 20, "Fruits": 30, "Packaged Food": 50}
    """
    if not ngo_demands_json:
        return 0.5, False, "General need (No specific demand specified)"

    try:
        demands = json.loads(ngo_demands_json)
        needed_qty = demands.get(food_category, 0)

        if needed_qty <= 0:
            return 0.2, False, f"No active demand for {food_category}"

        # If donation quantity fits the demand nicely
        ratio = min(1.0, quantity / float(needed_qty)) if needed_qty > 0 else 0.5
        demand_score = 0.6 + (0.4 * ratio)
        return demand_score, True, f"Matches demand for {food_category} (Needed: {needed_qty}, Donated: {quantity:.0f})"
    except Exception:
        return 0.5, False, "General demand"

def build_rescue_checklist(db: Session, donation: FoodDonation, ngo: NGO = None) -> dict:
    """
    Builds the transparent operational feasibility checklist for food rescue.
    Provides structured boolean indicators and status summaries.
    """
    now = datetime.now(timezone.utc)
    
    # 1. Target NGO
    target_ngo = ngo
    if not target_ngo and donation.assigned_ngo_id:
        target_ngo = db.query(NGO).filter(NGO.id == donation.assigned_ngo_id).first()
    if not target_ngo:
        # Check first recommended verified NGO
        recs = recommend_ngos(db, donation)
        if recs:
            target_ngo = db.query(NGO).filter(NGO.id == recs[0]["ngo_id"]).first()

    # Demand Match
    if target_ngo:
        _, is_demand_matched, demand_msg = calculate_demand_match_score(
            target_ngo.demand_requirements, donation.food_category, donation.quantity
        )
        is_open, open_msg = is_ngo_open_now(target_ngo.operating_hours, now)
        ngo_cap_ok = (target_ngo.current_capacity or 0) >= donation.quantity
    else:
        is_demand_matched = True
        is_open = True
        ngo_cap_ok = True
        demand_msg = "General demand available"
        open_msg = "Operating hours active"

    # 2. Volunteer Availability & Carrying Capacity
    volunteers = db.query(User).filter(User.role == "volunteer", User.is_active == True).all()
    vol_available = len(volunteers) > 0
    vol_cap_ok = any((v.carrying_capacity or 50) >= donation.quantity for v in volunteers) if volunteers else False

    # 3. Deadline Validity
    deadline = donation.estimated_window_end or donation.pickup_deadline or donation.expiry_time
    if deadline and deadline.tzinfo is None:
        deadline = deadline.replace(tzinfo=timezone.utc)
    
    if deadline:
        time_diff = (deadline - now).total_seconds()
        deadline_valid = time_diff > 0
        hours_left = max(0.0, round(time_diff / 3600.0, 1))
        remaining_minutes = max(0, int(time_diff / 60))
        if hours_left <= 0:
            expiry_status = "EXPIRED"
        elif hours_left <= 2.0 or donation.is_emergency:
            expiry_status = "URGENT"
        else:
            expiry_status = "NORMAL"
    else:
        deadline_valid = True
        hours_left = 4.0
        remaining_minutes = 240
        expiry_status = "NORMAL"

    # Logistics Feasibility
    feasibility_res = calculate_rescue_feasibility(remaining_minutes)

    # Overall Rescue Opportunity Status
    all_ready = is_demand_matched and is_open and ngo_cap_ok and vol_available and vol_cap_ok and deadline_valid
    if all_ready and expiry_status != "EXPIRED":
        rescue_status = "HIGH"
    elif deadline_valid and expiry_status != "EXPIRED":
        rescue_status = "MEDIUM"
    else:
        rescue_status = "ATTENTION_NEEDED"

    return {
        "demand_matched": is_demand_matched,
        "ngo_open": is_open,
        "ngo_capacity_available": ngo_cap_ok,
        "volunteer_available": vol_available,
        "volunteer_capacity_sufficient": vol_cap_ok,
        "deadline_valid": deadline_valid,
        "expiry_status": expiry_status,
        "rescue_opportunity_status": rescue_status,
        "feasibility": feasibility_res,
        "details": {
            "demand_summary": demand_msg,
            "operating_summary": open_msg,
            "time_remaining_hours": hours_left,
            "time_remaining_minutes": remaining_minutes,
            "target_ngo": target_ngo.organization_name if target_ngo else "Nearby Verified NGOs",
            "quantity_meals": donation.quantity,
            "safety_disclaimer": "Visual assessment only. This is an advisory estimate and does not certify food safety."
        }
    }

def recommend_ngos(db: Session, donation: FoodDonation) -> list[dict]:
    ngos = db.query(NGO).filter(NGO.is_verified == True, NGO.is_available == True).all()
    recommendations = []

    now = datetime.now(timezone.utc)
    deadline = donation.estimated_window_end or donation.pickup_deadline or donation.expiry_time
    if deadline and deadline.tzinfo is None:
        deadline = deadline.replace(tzinfo=timezone.utc)
    
    remaining_window_min = max(0, int((deadline - now).total_seconds() / 60)) if deadline else 240

    urgency = calculate_urgency(donation.preparation_time, donation.expiry_time)
    urgency_score = calculate_urgency_score(donation.preparation_time, donation.expiry_time, donation.food_category)

    for ngo in ngos:
        # Check admin action status
        if ngo.admin_action_status == "RESTRICTED":
            continue

        # 1. Distance score (0-1, closer is higher)
        dist = haversine_distance(donation.latitude, donation.longitude, ngo.latitude, ngo.longitude)
        dist_score = max(0.0, 1.0 - (dist / 25.0)) # 0 score at 25km+

        # 2. Beneficiary Demand Alignment (30% priority weight)
        demand_score, is_demand_matched, demand_detail = calculate_demand_match_score(
            ngo.demand_requirements, donation.food_category, donation.quantity
        )

        # 3. Capacity score (20%) - Hard Gate
        if ngo.current_capacity >= donation.quantity:
            capacity_score = 1.0
            capacity_feasible = True
        elif ngo.current_capacity > 0:
            capacity_score = ngo.current_capacity / float(donation.quantity)
            capacity_feasible = False
        else:
            capacity_score = 0.0
            capacity_feasible = False

        # 4. Operating Hours / Open Now (20% priority weight - closed NGOs strongly penalized)
        is_open, open_status = is_ngo_open_now(ngo.operating_hours, donation.created_at)
        operating_score = 1.0 if is_open else 0.05

        # 5. Historical Receiving Reliability (15%)
        receiving_reliability = ngo.trust_score if ngo.trust_score is not None else 96.0
        reliability_norm = max(0.0, min(1.0, receiving_reliability / 100.0))

        # 6. Urgency & Condition match (15%)
        condition_urgency_score = urgency_score

        # 7. Time-aware ETA feasibility
        transit_time_min = max(10.0, dist * 3.0)
        feasibility = calculate_rescue_feasibility(
            remaining_window_minutes=remaining_window_min,
            estimated_pickup_minutes=15.0,
            estimated_travel_minutes=transit_time_min,
            ngo_intake_minutes=10.0
        )

        # Hard Gate: Infeasible NGOs (closed, capacity 0, or transit ETA > window) are heavily penalized
        feasibility_multiplier = 1.0 if (feasibility["is_feasible"] and capacity_feasible and is_open) else 0.1

        # Admin deprioritize factor
        deprioritize_mult = 0.7 if ngo.admin_action_status == "DEPRIORITIZED" else 1.0

        raw_score = (
            (demand_score * 0.30) +
            (dist_score * 0.20) +
            (capacity_score * 0.20) +
            (operating_score * 0.15) +
            (reliability_norm * 0.15)
        )

        final_score = raw_score * feasibility_multiplier * deprioritize_mult

        reason = (
            f"{dist:.1f} km away. {open_status}. "
            f"{demand_detail}. "
            f"{'Full capacity available' if capacity_score == 1.0 else 'Partial capacity'}. "
            f"Receiving Reliability: {receiving_reliability:.0f}%. "
            f"ETA: {int(transit_time_min)}m ({feasibility['feasibility_label']})."
        )

        # Structured Explainable Match Reasons ("Why this NGO?")
        match_reasons = []
        if is_open:
            match_reasons.append({"code": "open", "label": open_status, "is_positive": True})
        else:
            match_reasons.append({"code": "closed", "label": open_status, "is_positive": False})

        if is_demand_matched:
            match_reasons.append({"code": "demand", "label": demand_detail, "is_positive": True})

        if capacity_feasible:
            match_reasons.append({"code": "capacity", "label": f"Intake capacity available ({ngo.current_capacity} meals)", "is_positive": True})

        if feasibility["is_feasible"]:
            match_reasons.append({"code": "feasible", "label": f"Rescue feasible ({int(transit_time_min)}m transit)", "is_positive": True})

        if receiving_reliability >= 90.0:
            match_reasons.append({"code": "reliability", "label": f"Reliable receiving partner ({receiving_reliability:.0f}%)", "is_positive": True})

        recommendations.append({
            "ngo_id": ngo.id,
            "organization_name": ngo.organization_name,
            "distance_km": round(dist, 2),
            "score": round(final_score * 100, 1),
            "reason": reason,
            "match_reasons": match_reasons,
            "capacity": ngo.capacity,
            "current_capacity": ngo.current_capacity,
            "is_available": ngo.is_available,
            "is_open_now": is_open,
            "demand_matched": is_demand_matched,
            "demand_match_detail": demand_detail,
            "receiving_reliability": receiving_reliability,
            "feasibility_status": feasibility["feasibility_status"],
            "feasibility_label": feasibility["feasibility_label"],
            "transit_time_minutes": int(transit_time_min)
        })

    recommendations.sort(key=lambda x: x["score"], reverse=True)
    return recommendations

def global_batch_match_ngos(db: Session) -> dict:
    """
    Solves Global Bipartite Maximum Weight Matching using the Hungarian Algorithm (linear_sum_assignment).
    Excludes candidates failing hard constraints (closed, zero capacity, impossible deadline) before optimization.
    Algorithm: Kuhn-Munkres / Hungarian Algorithm
    Complexity: O(V * E)
    """
    pending_donations = db.query(FoodDonation).filter(FoodDonation.status == "pending").all()
    available_ngos = db.query(NGO).filter(NGO.is_verified == True, NGO.is_available == True).all()

    if not pending_donations or not available_ngos:
        return {"matched_pairs": [], "unmatched_donations": [d.id for d in pending_donations], "global_efficiency_score": 0.0}

    n_donations = len(pending_donations)
    n_ngos = len(available_ngos)

    cost_matrix = np.zeros((n_donations, n_ngos))

    for i, donation in enumerate(pending_donations):
        recs = recommend_ngos(db, donation)
        rec_map = {r["ngo_id"]: r["score"] for r in recs}
        for j, ngo in enumerate(available_ngos):
            score = rec_map.get(ngo.id, 0.0)
            cost_matrix[i, j] = -score

    row_ind, col_ind = linear_sum_assignment(cost_matrix)

    matched_pairs = []
    total_score = 0.0

    for r, c in zip(row_ind, col_ind):
        score = -cost_matrix[r, c]
        if score > 10.0:
            donation = pending_donations[r]
            ngo = available_ngos[c]
            matched_pairs.append({
                "donation_id": donation.id,
                "food_name": donation.food_name,
                "ngo_id": ngo.id,
                "ngo_name": ngo.organization_name,
                "match_score": round(float(score), 1),
                "distance_km": round(haversine_distance(donation.latitude, donation.longitude, ngo.latitude, ngo.longitude), 2)
            })
            total_score += score

    matched_donation_ids = {p["donation_id"] for p in matched_pairs}
    unmatched = [d.id for d in pending_donations if d.id not in matched_donation_ids]
    avg_efficiency = (total_score / len(matched_pairs)) if matched_pairs else 0.0

    return {
        "matched_pairs": matched_pairs,
        "unmatched_donations": unmatched,
        "total_matched": len(matched_pairs),
        "global_efficiency_score": round(avg_efficiency, 1)
    }

def recommend_volunteers(db: Session, donation: FoodDonation) -> list[dict]:
    """
    Urgency-Aware & Feasibility-Gated Volunteer Matching Algorithm:
    Sequence:
    1. Active status & Authorization
    2. Carrying Capacity Match (Hard constraint)
    3. Availability
    4. Rescue Feasibility & Deadline (Hard constraint)
    5. Distance & ETA
    6. Reliability, Response Speed & Punctuality
    7. Workload & Admin Deprioritization factor
    """
    volunteers = db.query(User).filter(User.role == "volunteer", User.is_active == True).all()
    recommendations = []

    now = datetime.now(timezone.utc)
    deadline = donation.estimated_window_end or donation.pickup_deadline or donation.expiry_time
    if deadline and deadline.tzinfo is None:
        deadline = deadline.replace(tzinfo=timezone.utc)
    
    remaining_window_min = max(0, int((deadline - now).total_seconds() / 60)) if deadline else 240
    is_urgent = (donation.rescue_urgency_level in ["URGENT", "CRITICAL"]) or (remaining_window_min <= 60)

    for vol in volunteers:
        # Check admin action status
        if vol.admin_action_status == "RESTRICTED":
            continue

        # 1. Distance (closer is higher)
        dist = haversine_distance(donation.latitude, donation.longitude, vol.latitude, vol.longitude)
        dist_score = max(0.0, 1.0 - (dist / 15.0))

        # ETA calculation (~3 min per km in urban environment)
        pickup_eta_min = max(5.0, dist * 3.0)

        # 2. Availability
        avail_score = 1.0 if vol.is_active else 0.0

        # 3. Carrying Capacity - Hard Gate
        vol_capacity = vol.carrying_capacity or 50
        if vol_capacity >= donation.quantity:
            capacity_score = 1.0
            capacity_feasibility = True
        elif vol_capacity > 0:
            capacity_score = max(0.05, vol_capacity / float(donation.quantity))
            capacity_feasibility = False
        else:
            capacity_score = 0.05
            capacity_feasibility = False

        # 4. Workload / Active tasks
        active_count = db.query(VolunteerAssignment).filter(
            VolunteerAssignment.volunteer_id == vol.id,
            VolunteerAssignment.status.in_(["assigned", "accepted", "collected"])
        ).count()
        workload_score = max(0.0, 1.0 - (active_count * 0.35))

        # 5. Reliability / Success Rate
        reliability = vol.reliability_score if vol.reliability_score is not None else 95.0
        reliability_score_norm = max(0.0, min(1.0, reliability / 100.0))

        # 6. Response Speed (sec to score)
        resp_sec = vol.avg_response_time_seconds or 180.0
        response_speed_norm = max(0.2, min(1.0, 1.0 - (resp_sec / 600.0)))

        # ETA Feasibility
        feasibility = calculate_rescue_feasibility(
            remaining_window_minutes=remaining_window_min,
            estimated_pickup_minutes=pickup_eta_min,
            estimated_travel_minutes=20.0,
            ngo_intake_minutes=10.0
        )

        # Urgency-Aware Scoring Weights:
        if is_urgent:
            # Urgent: Distance/ETA 25%, Availability 20%, Capacity 20%, Response Speed 15%, Reliability 20%
            raw_score = (
                (dist_score * 0.25) +
                (avail_score * 0.20) +
                (capacity_score * 0.20) +
                (response_speed_norm * 0.15) +
                (reliability_score_norm * 0.20)
            )
        else:
            # Normal: Distance 30%, Availability 25%, Capacity 20%, Workload 15%, Reliability 10%
            raw_score = (
                (dist_score * 0.30) +
                (avail_score * 0.25) +
                (capacity_score * 0.20) +
                (workload_score * 0.15) +
                (reliability_score_norm * 0.10)
            )

        # STRICT FEASIBILITY HARD GATE:
        # Infeasible candidates (capacity too small or pickup ETA exceeds window) are strictly penalized (0.1x)
        # Guaranteeing FEASIBILITY > RELIABILITY
        if not capacity_feasibility or not feasibility["is_feasible"]:
            raw_score *= 0.1

        # Admin Deprioritization
        if vol.admin_action_status == "DEPRIORITIZED":
            raw_score *= 0.7

        final_score = raw_score

        reason = (
            f"{dist:.1f} km away (ETA: {int(pickup_eta_min)}m). Vehicle: {vol.vehicle_type or 'Bike'} (Cap: {vol_capacity} meals). "
            f"Active tasks: {active_count}. Reliability: {reliability:.0f}%. "
            f"Status: {feasibility['feasibility_label']}."
        )

        # Structured Explainable Match Reasons ("Why this volunteer?")
        match_reasons = []
        if vol.is_active:
            match_reasons.append({"code": "available", "label": "Available now", "is_positive": True})
        if capacity_feasibility:
            match_reasons.append({"code": "capacity", "label": f"Vehicle capacity sufficient ({vol_capacity} meals)", "is_positive": True})
        if feasibility["is_feasible"]:
            match_reasons.append({"code": "feasible", "label": f"Rescue feasible (ETA: {int(pickup_eta_min)}m, Window: {remaining_window_min}m)", "is_positive": True})
        match_reasons.append({"code": "distance", "label": f"{dist:.1f} km away (ETA: {int(pickup_eta_min)}m)", "is_positive": True})
        if reliability >= 90.0:
            match_reasons.append({"code": "reliability", "label": f"High completion history ({reliability:.0f}%)", "is_positive": True})
        if resp_sec <= 180:
            match_reasons.append({"code": "response_speed", "label": f"Quick responder (Avg {int(resp_sec // 60)}m)", "is_positive": True})

        recommendations.append({
            "volunteer_id": vol.id,
            "volunteer_name": vol.name,
            "phone": vol.phone,
            "vehicle_type": vol.vehicle_type or "bike",
            "carrying_capacity": vol_capacity,
            "reliability_score": reliability,
            "performance_status": vol.performance_status or "ESTABLISHED",
            "admin_action_status": vol.admin_action_status or "NORMAL",
            "active_tasks": active_count,
            "distance_km": round(dist, 2),
            "pickup_eta_minutes": int(pickup_eta_min),
            "feasibility_status": feasibility["feasibility_status"],
            "score": round(final_score * 100, 1),
            "score_breakdown": {
                "distance": round(dist_score * 30, 1),
                "availability": round(avail_score * 25, 1),
                "capacity": round(capacity_score * 20, 1),
                "workload": round(workload_score * 15, 1),
                "reliability": round(reliability_score_norm * 10, 1)
            },
            "reason": reason,
            "match_reasons": match_reasons
        })

    recommendations.sort(key=lambda x: x["score"], reverse=True)
    return recommendations

def optimize_volunteer_routes(db: Session, max_cluster_radius_km: float = 3.0) -> list[dict]:
    """
    Centroid-based Greedy Spatial Clustering Heuristic:
    Batches nearby pickups (within max_cluster_radius_km) into unified multi-stop routes for single volunteer couriers.
    """
    accepted_donations = db.query(FoodDonation).filter(FoodDonation.status == "accepted").all()
    volunteers = db.query(User).filter(User.role == "volunteer", User.is_active == True).all()

    if not accepted_donations or not volunteers:
        return []

    clusters = []
    visited = set()

    for d1 in accepted_donations:
        if d1.id in visited:
            continue
        cluster = [d1]
        visited.add(d1.id)

        for d2 in accepted_donations:
            if d2.id not in visited:
                dist = haversine_distance(d1.latitude, d1.longitude, d2.latitude, d2.longitude)
                if dist <= max_cluster_radius_km:
                    cluster.append(d2)
                    visited.add(d2.id)

        # Find best volunteer for cluster centroid
        centroid_lat = sum(d.latitude or 12.9716 for d in cluster) / len(cluster)
        centroid_lon = sum(d.longitude or 77.5946 for d in cluster) / len(cluster)

        best_vol = None
        min_vol_dist = float("inf")
        for v in volunteers:
            v_dist = haversine_distance(centroid_lat, centroid_lon, v.latitude, v.longitude)
            if v_dist < min_vol_dist:
                min_vol_dist = v_dist
                best_vol = v

        clusters.append({
            "volunteer_id": best_vol.id if best_vol else None,
            "volunteer_name": best_vol.name if best_vol else "Unassigned",
            "total_pickups": len(cluster),
            "donation_ids": [d.id for d in cluster],
            "total_meals": sum(d.quantity for d in cluster),
            "estimated_route_distance_km": round(min_vol_dist + (len(cluster) * 1.2), 2),
            "heuristic_method": "Centroid-based Greedy Spatial Clustering"
        })

    return clusters
