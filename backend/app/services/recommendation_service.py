import math
from sqlalchemy.orm import Session
from app.models.models import NGO, User, FoodDonation, VolunteerAssignment
from app.services.urgency_service import calculate_urgency

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
    urgency_weights = {"Urgent": 1.0, "Use Soon": 0.7, "Fresh": 0.4, "Expired": 0.0}
    urgency_score = urgency_weights.get(urgency, 0.5)

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
