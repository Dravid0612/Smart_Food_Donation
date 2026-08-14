import math
import numpy as np
from scipy.optimize import linear_sum_assignment
from sqlalchemy.orm import Session
from app.models.models import NGO, User, FoodDonation, VolunteerAssignment
from app.services.urgency_service import calculate_urgency, calculate_urgency_score

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

def recommend_ngos(db: Session, donation: FoodDonation) -> list[dict]:
    ngos = db.query(NGO).filter(NGO.is_verified == True, NGO.is_available == True).all()
    recommendations = []

    urgency = calculate_urgency(donation.preparation_time, donation.expiry_time)
    urgency_score = calculate_urgency_score(donation.preparation_time, donation.expiry_time, donation.food_category)

    for ngo in ngos:
        # 1. Distance score (0-1, closer is higher)
        dist = haversine_distance(donation.latitude, donation.longitude, ngo.latitude, ngo.longitude)
        dist_score = max(0.0, 1.0 - (dist / 20.0)) # 0 score at 20km+

        # 2. Capacity score
        if ngo.current_capacity >= donation.quantity:
            capacity_score = 1.0
        elif ngo.current_capacity > 0:
            capacity_score = ngo.current_capacity / float(donation.quantity)
        else:
            capacity_score = 0.0

        # 3. Availability score
        avail_score = 1.0 if ngo.is_available else 0.0

        # Final weighted score
        final_score = (
            (dist_score * 0.35) +
            (capacity_score * 0.25) +
            (avail_score * 0.20) +
            (urgency_score * 0.20)
        )

        reason = (
            f"{dist:.1f} km away. "
            f"{'Capacity available' if capacity_score == 1.0 else 'Partial capacity'}. "
            f"High match for {urgency.lower()} donation."
        )

        recommendations.append({
            "ngo_id": ngo.id,
            "organization_name": ngo.organization_name,
            "distance_km": round(dist, 2),
            "score": round(final_score * 100, 1),
            "reason": reason,
            "capacity": ngo.capacity,
            "current_capacity": ngo.current_capacity,
            "is_available": ngo.is_available
        })

    recommendations.sort(key=lambda x: x["score"], reverse=True)
    return recommendations

def global_batch_match_ngos(db: Session) -> dict:
    """
    Solves Global Bipartite Maximum Weight Matching using the Hungarian Algorithm (linear_sum_assignment).
    Matches all active pending donations with available verified NGOs simultaneously for maximum platform efficiency.
    """
    pending_donations = db.query(FoodDonation).filter(FoodDonation.status == "pending").all()
    available_ngos = db.query(NGO).filter(NGO.is_verified == True, NGO.is_available == True).all()

    if not pending_donations or not available_ngos:
        return {"matched_pairs": [], "unmatched_donations": [d.id for d in pending_donations], "global_efficiency_score": 0.0}

    n_donations = len(pending_donations)
    n_ngos = len(available_ngos)

    # Construct Cost Matrix (N_donations x N_ngos)
    cost_matrix = np.zeros((n_donations, n_ngos))

    for i, donation in enumerate(pending_donations):
        recs = recommend_ngos(db, donation)
        rec_map = {r["ngo_id"]: r["score"] for r in recs}
        for j, ngo in enumerate(available_ngos):
            score = rec_map.get(ngo.id, 0.0)
            # Hungarian algorithm minimizes cost, so cost = -score
            cost_matrix[i, j] = -score

    row_ind, col_ind = linear_sum_assignment(cost_matrix)

    matched_pairs = []
    total_score = 0.0

    for r, c in zip(row_ind, col_ind):
        score = -cost_matrix[r, c]
        if score > 10.0: # Minimum viability threshold
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
    volunteers = db.query(User).filter(User.role == "volunteer", User.is_active == True).all()
    recommendations = []

    for vol in volunteers:
        dist = haversine_distance(donation.latitude, donation.longitude, vol.latitude, vol.longitude)
        dist_score = max(0.0, 1.0 - (dist / 15.0))

        # Check active assignments
        active_count = db.query(VolunteerAssignment).filter(
            VolunteerAssignment.volunteer_id == vol.id,
            VolunteerAssignment.status.in_(["assigned", "accepted", "collected"])
        ).count()

        workload_score = max(0.0, 1.0 - (active_count * 0.3))

        score = (dist_score * 0.6) + (workload_score * 0.4)

        reason = f"{dist:.1f} km away with {active_count} active pickup(s)."

        recommendations.append({
            "volunteer_id": vol.id,
            "volunteer_name": vol.name,
            "phone": vol.phone,
            "distance_km": round(dist, 2),
            "score": round(score * 100, 1),
            "reason": reason
        })

    recommendations.sort(key=lambda x: x["score"], reverse=True)
    return recommendations

def optimize_volunteer_routes(db: Session, max_cluster_radius_km: float = 3.0) -> list[dict]:
    """
    Batches nearby pickups (within max_cluster_radius_km) into unified multi-stop routes for single volunteer drivers (VRPTW heuristic).
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
            "estimated_route_distance_km": round(min_vol_dist + (len(cluster) * 1.2), 2)
        })

    return clusters

