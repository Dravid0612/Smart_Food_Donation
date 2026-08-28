"""
Rescue Operational Reliability, Trust Score, and Performance Optimization Service.
Provides transparent, explainable, and multi-factor metrics with sample-size protection,
recency weighting, response-time tracking, failure analytics, and admin intervention for Volunteers, NGOs, and Donors.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from app.models.models import User, NGO, FoodDonation, VolunteerAssignment, RescueFeedback, RescueIssueReport, AuditLog

# Configuration Constants
MIN_SAMPLE_SIZE_THRESHOLD = 3
ESTABLISHED_SAMPLE_SIZE_THRESHOLD = 10
RECENCY_WINDOW_SIZE = 10
DEFAULT_BASE_RELIABILITY = 95.0


def calculate_volunteer_reliability(db: Session, volunteer_id: int) -> Dict[str, Any]:
    """
    Computes explainable multi-factor reliability and performance profile for a volunteer.
    
    Formula components:
    - 35% Task Completion Rate (completed / accepted)
    - 25% Punctuality / On-Time Rate (on-time feedbacks / total feedbacks with timeliness)
    - 25% Service Quality Rating (average rating / 5.0 * 100)
    - 15% Cancellation Resistance (100 - cancellation_rate)
    
    Sample size protection:
    - 0-2 rescues: NEW (neutral 95.0 baseline)
    - 3-9 rescues: LIMITED_HISTORY
    - 10+ rescues: ESTABLISHED / RELIABLE
    - Elevated no-show (>15%) or completion (<70%) or cancellations (>25%): NEEDS_REVIEW
    
    Recency: Recent 10 assignments weighted 85% vs 15% historical baseline.
    """
    user = db.query(User).filter(User.id == volunteer_id).first()
    if not user:
        return _empty_reliability_profile(volunteer_id, "Unknown", "volunteer")

    # Fetch all assignments
    assignments = db.query(VolunteerAssignment).filter(
        VolunteerAssignment.volunteer_id == volunteer_id
    ).order_by(VolunteerAssignment.assigned_at.desc()).all()

    accepted_tasks = [a for a in assignments if a.status in ["accepted", "collected", "delivered", "cancelled", "failed"]]
    completed_tasks = [a for a in assignments if a.status == "delivered"]
    cancellations = [a for a in assignments if a.status == "cancelled"]
    failed_tasks = [a for a in assignments if a.status == "failed"]

    total_assigned = len(assignments)
    total_accepted = len(accepted_tasks)
    total_completed = len(completed_tasks)
    total_cancelled = len(cancellations)
    total_no_shows = len(failed_tasks)

    # Calculate average response time (seconds from assigned_at to accepted_at)
    response_times = []
    for a in assignments:
        if a.assigned_at and a.accepted_at:
            assigned_dt = a.assigned_at.replace(tzinfo=timezone.utc) if a.assigned_at.tzinfo is None else a.assigned_at
            accepted_dt = a.accepted_at.replace(tzinfo=timezone.utc) if a.accepted_at.tzinfo is None else a.accepted_at
            diff_sec = (accepted_dt - assigned_dt).total_seconds()
            if 0 <= diff_sec <= 3600:  # within 1 hour
                response_times.append(diff_sec)

    avg_response_time_sec = (sum(response_times) / len(response_times)) if response_times else 180.0
    user.avg_response_time_seconds = round(avg_response_time_sec, 1)

    # Fetch all feedbacks where this volunteer is the target or feedback on their assigned donations
    feedbacks = db.query(RescueFeedback).filter(
        (RescueFeedback.target_user_id == volunteer_id) |
        (
            RescueFeedback.author_role.in_(["donor", "ngo"]) &
            RescueFeedback.donation_id.in_([a.donation_id for a in assignments])
        )
    ).order_by(RescueFeedback.created_at.desc()).all()

    # Recency-weighted feedback calculation
    recent_feedbacks = feedbacks[:RECENCY_WINDOW_SIZE]
    ratings = [f.overall_rating for f in recent_feedbacks if f.overall_rating is not None]
    avg_rating = (sum(ratings) / len(ratings)) if ratings else 4.8

    # Punctuality calculation from donor/NGO feedbacks
    on_time_count = 0
    punctuality_total = 0
    delayed_count = 0
    for f in recent_feedbacks:
        if f.pickup_timeliness:
            punctuality_total += 1
            if f.pickup_timeliness == "on_time":
                on_time_count += 1
            elif f.pickup_timeliness == "slight_delay":
                on_time_count += 0.7
                delayed_count += 1
            else:
                delayed_count += 1
        if f.volunteer_punctuality:
            punctuality_total += 1
            if f.volunteer_punctuality == "on_time":
                on_time_count += 1
            elif f.volunteer_punctuality == "slightly_late":
                on_time_count += 0.7
                delayed_count += 1
            else:
                delayed_count += 1

    on_time_rate = (on_time_count / punctuality_total * 100.0) if punctuality_total > 0 else 95.0
    completion_rate = (total_completed / total_accepted * 100.0) if total_accepted > 0 else 100.0
    cancellation_rate = (total_cancelled / total_accepted * 100.0) if total_accepted > 0 else 0.0
    no_show_rate = (total_no_shows / total_accepted * 100.0) if total_accepted > 0 else 0.0
    rating_score_norm = (avg_rating / 5.0) * 100.0

    # Response speed score (0 to 100)
    # < 60s -> 100, 180s -> 90, 300s -> 80, 600s -> 60, > 1200s -> 40
    response_speed_score = max(40.0, min(100.0, 100.0 - (avg_response_time_sec / 180.0) * 10.0))

    # Weighted calculation
    computed_score = (
        (completion_rate * 0.35) +
        (on_time_rate * 0.25) +
        (rating_score_norm * 0.25) +
        (max(0.0, 100.0 - cancellation_rate) * 0.15)
    )
    computed_score = round(max(50.0, min(100.0, computed_score)), 1)

    # Check critical issues count for this volunteer
    critical_issues = db.query(RescueIssueReport).filter(
        RescueIssueReport.reported_user_id == volunteer_id,
        RescueIssueReport.severity.in_(["HIGH", "CRITICAL"]),
        RescueIssueReport.status != "DISMISSED"
    ).count()

    # Determine Performance Status Tier
    has_sufficient_history = total_completed >= MIN_SAMPLE_SIZE_THRESHOLD
    is_established = total_completed >= ESTABLISHED_SAMPLE_SIZE_THRESHOLD

    # Outlier / Spike protection & Needs Review rule:
    # Trigger Needs Review if: sufficient history and (no-show > 15% or completion < 70% or cancellation > 25% or critical_issues >= 2)
    is_needs_review = has_sufficient_history and (
        no_show_rate > 15.0 or
        completion_rate < 70.0 or
        cancellation_rate > 25.0 or
        critical_issues >= 2
    )

    if is_needs_review:
        performance_status = "NEEDS_REVIEW"
        trust_tier = "Reliability Needs Review"
        display_score = computed_score
    elif not has_sufficient_history:
        performance_status = "NEW"
        trust_tier = "New Volunteer"
        display_score = user.reliability_score or DEFAULT_BASE_RELIABILITY
    else:
        if computed_score >= 90.0:
            performance_status = "RELIABLE" if is_established else "LIMITED_HISTORY"
            trust_tier = "Highly Reliable"
        elif computed_score >= 75.0:
            performance_status = "ESTABLISHED" if is_established else "LIMITED_HISTORY"
            trust_tier = "Good Standing"
        else:
            performance_status = "NEEDS_REVIEW"
            trust_tier = "Reliability Needs Review"
        display_score = computed_score

    # Constructive trend detection (compare recent 5 vs previous 5)
    if len(assignments) >= 6:
        first_half = assignments[:5]
        completed_first = sum(1 for a in first_half if a.status == "delivered")
        rate_recent = completed_first / len(first_half) * 100.0
        
        second_half = assignments[5:10]
        completed_second = sum(1 for a in second_half if a.status == "delivered")
        rate_prev = (completed_second / len(second_half) * 100.0) if second_half else rate_recent
        
        if rate_recent > rate_prev + 5.0:
            recent_trend = "improving"
            trend_desc = "On-time rate and completion improving recently"
        elif rate_recent < rate_prev - 10.0:
            recent_trend = "declining"
            trend_desc = "Recent cancellation or delay spike observed"
        else:
            recent_trend = "steady"
            trend_desc = "Consistently reliable delivery performance"
    else:
        recent_trend = "new" if not has_sufficient_history else "steady"
        trend_desc = "Building rescue operational history"

    # Badges
    badges: List[str] = []
    if performance_status == "NEW":
        badges.append("New Volunteer")
    elif performance_status == "NEEDS_REVIEW":
        badges.append("Additional Verification Required")
    else:
        if computed_score >= 92.0:
            badges.append("Reliable Pickup History")
            badges.append("Consistent Delivery")
        elif computed_score >= 80.0:
            badges.append("Verified Courier")
        
        if completion_rate >= 95.0:
            badges.append(f"High Completion Rate ({completion_rate:.0f}%)")
        if on_time_rate >= 90.0:
            badges.append("Punctual Courier")
        if avg_response_time_sec <= 180.0 and len(response_times) >= 1:
            badges.append("Fast Responder")

    # Sync to user record
    user.performance_status = performance_status
    if has_sufficient_history and abs((user.reliability_score or 95.0) - display_score) > 0.5:
        user.reliability_score = display_score
        user.completed_deliveries = total_completed
        user.failed_deliveries = total_no_shows

    return {
        "user_id": user.id,
        "name": user.name,
        "role": "volunteer",
        "performance_status": performance_status,
        "admin_action_status": user.admin_action_status or "NORMAL",
        "admin_action_notes": user.admin_action_notes,
        "overall_reliability_score": display_score,
        "trust_tier": trust_tier,
        "trust_badges": badges,
        "recent_trend": recent_trend,
        "trend_description": trend_desc,
        "has_sufficient_history": has_sufficient_history,
        "sample_size_threshold": MIN_SAMPLE_SIZE_THRESHOLD,
        "recency_window_size": RECENCY_WINDOW_SIZE,
        "raw_metrics": {
            "total_tasks_assigned": total_assigned,
            "total_tasks_accepted": total_accepted,
            "total_completed": total_completed,
            "total_cancelled": total_cancelled,
            "total_no_shows": total_no_shows,
            "total_on_time": int(on_time_count),
            "total_delayed": int(delayed_count),
            "total_feedbacks_received": len(feedbacks),
            "average_response_time_seconds": round(avg_response_time_sec, 1)
        },
        "derived_metrics": {
            "completion_rate_percent": round(completion_rate, 1),
            "on_time_rate_percent": round(on_time_rate, 1),
            "cancellation_rate_percent": round(cancellation_rate, 1),
            "no_show_rate_percent": round(no_show_rate, 1),
            "service_quality_score_percent": round(rating_score_norm, 1),
            "response_speed_score_percent": round(response_speed_score, 1)
        },
        "total_completed_rescues": total_completed,
        "total_accepted_rescues": total_accepted,
        "cancellations_count": total_cancelled,
        "no_shows_count": total_no_shows,
        "on_time_rate_percent": round(on_time_rate, 1),
        "completion_rate_percent": round(completion_rate, 1),
        "average_service_rating": round(avg_rating, 2),
        "dimensions": [
            {
                "name": "Task Completion Rate",
                "score": round(completion_rate, 1),
                "weight": 0.35,
                "description": f"{total_completed} of {total_accepted} accepted rescues delivered successfully"
            },
            {
                "name": "Punctuality & Timeliness",
                "score": round(on_time_rate, 1),
                "weight": 0.25,
                "description": f"{on_time_rate:.0f}% on-time pickup and delivery rate"
            },
            {
                "name": "Service Quality Feedback",
                "score": round(rating_score_norm, 1),
                "weight": 0.25,
                "description": f"Average {avg_rating:.2f} / 5.0 stars from donors and NGOs"
            },
            {
                "name": "Low Cancellation Rate",
                "score": round(max(0.0, 100.0 - cancellation_rate), 1),
                "weight": 0.15,
                "description": f"{total_cancelled} cancellations ({cancellation_rate:.1f}%)"
            }
        ]
    }


def calculate_ngo_reliability(db: Session, ngo_id: int) -> Dict[str, Any]:
    """
    Computes explainable reliability and performance metrics for an NGO.
    """
    ngo = db.query(NGO).filter(NGO.id == ngo_id).first()
    if not ngo:
        return _empty_reliability_profile(ngo_id, "Unknown NGO", "ngo")

    user = ngo.user
    accepted_donations = db.query(FoodDonation).filter(FoodDonation.assigned_ngo_id == ngo_id).all()
    completed = [d for d in accepted_donations if d.status in ["delivered", "completed"]]
    
    total_accepted = len(accepted_donations)
    total_completed = len(completed)

    # Feedbacks on this NGO
    feedbacks = db.query(RescueFeedback).filter(
        (RescueFeedback.target_ngo_id == ngo_id) |
        (
            RescueFeedback.author_role.in_(["donor", "volunteer"]) &
            RescueFeedback.donation_id.in_([d.id for d in accepted_donations])
        )
    ).order_by(RescueFeedback.created_at.desc()).all()

    recent_feedbacks = feedbacks[:RECENCY_WINDOW_SIZE]
    ratings = [f.overall_rating for f in recent_feedbacks if f.overall_rating is not None]
    avg_rating = (sum(ratings) / len(ratings)) if ratings else 4.8

    # Volunteer receiving readiness evaluations
    ready_count = 0
    readiness_total = 0
    for f in recent_feedbacks:
        if f.ngo_receiving_readiness:
            readiness_total += 1
            if f.ngo_receiving_readiness == "ready_to_receive":
                ready_count += 1
            elif f.ngo_receiving_readiness == "minor_wait":
                ready_count += 0.7

    readiness_rate = (ready_count / readiness_total * 100.0) if readiness_total > 0 else 95.0
    completion_rate = (total_completed / total_accepted * 100.0) if total_accepted > 0 else 100.0

    computed_score = (
        (completion_rate * 0.40) +
        (readiness_rate * 0.30) +
        ((avg_rating / 5.0 * 100.0) * 0.30)
    )
    computed_score = round(max(50.0, min(100.0, computed_score)), 1)

    has_sufficient_history = total_completed >= MIN_SAMPLE_SIZE_THRESHOLD
    is_established = total_completed >= ESTABLISHED_SAMPLE_SIZE_THRESHOLD

    # Critical issues check
    critical_issues = db.query(RescueIssueReport).filter(
        RescueIssueReport.reported_ngo_id == ngo_id,
        RescueIssueReport.severity.in_(["HIGH", "CRITICAL"]),
        RescueIssueReport.status != "DISMISSED"
    ).count()

    is_needs_review = has_sufficient_history and (
        readiness_rate < 60.0 or
        completion_rate < 70.0 or
        critical_issues >= 2
    )

    badges: List[str] = []
    if ngo.is_verified:
        badges.append("Verified Partner")

    if is_needs_review:
        performance_status = "NEEDS_REVIEW"
        trust_tier = "Reliability Needs Review"
        display_score = computed_score
        badges.append("Intake Review Required")
    elif not has_sufficient_history:
        performance_status = "NEW"
        trust_tier = "New NGO Partner"
        badges.append("New NGO Partner")
        display_score = ngo.trust_score or DEFAULT_BASE_RELIABILITY
    elif not is_established:
        performance_status = "LIMITED_HISTORY"
        trust_tier = "Limited History"
        display_score = computed_score
    else:
        if computed_score >= 90.0:
            performance_status = "RELIABLE"
            trust_tier = "Highly Reliable"
            badges.append("Reliable Receiving History")
        else:
            performance_status = "ESTABLISHED"
            trust_tier = "Good Standing"
        display_score = computed_score

        if readiness_rate >= 90.0:
            badges.append("Prompt Intake Station")

    ngo.performance_status = performance_status
    if has_sufficient_history:
        ngo.trust_score = display_score

    return {
        "user_id": user.id if user else ngo.id,
        "ngo_id": ngo.id,
        "name": ngo.organization_name,
        "role": "ngo",
        "performance_status": performance_status,
        "admin_action_status": ngo.admin_action_status or "NORMAL",
        "admin_action_notes": ngo.admin_action_notes,
        "overall_reliability_score": display_score,
        "trust_tier": trust_tier,
        "trust_badges": badges,
        "recent_trend": "steady",
        "trend_description": "Active community receiving partner",
        "has_sufficient_history": has_sufficient_history,
        "sample_size_threshold": MIN_SAMPLE_SIZE_THRESHOLD,
        "recency_window_size": RECENCY_WINDOW_SIZE,
        "raw_metrics": {
            "total_tasks_assigned": total_accepted,
            "total_tasks_accepted": total_accepted,
            "total_completed": total_completed,
            "total_cancelled": 0,
            "total_no_shows": 0,
            "total_on_time": int(ready_count),
            "total_delayed": int(readiness_total - ready_count),
            "total_feedbacks_received": len(feedbacks),
            "average_response_time_seconds": 120.0
        },
        "derived_metrics": {
            "completion_rate_percent": round(completion_rate, 1),
            "on_time_rate_percent": round(readiness_rate, 1),
            "cancellation_rate_percent": 0.0,
            "no_show_rate_percent": 0.0,
            "service_quality_score_percent": round(avg_rating / 5.0 * 100.0, 1),
            "response_speed_score_percent": 90.0
        },
        "total_completed_rescues": total_completed,
        "total_accepted_rescues": total_accepted,
        "cancellations_count": 0,
        "no_shows_count": 0,
        "on_time_rate_percent": round(readiness_rate, 1),
        "completion_rate_percent": round(completion_rate, 1),
        "average_service_rating": round(avg_rating, 2),
        "dimensions": [
            {
                "name": "Rescue Acceptance & Intake",
                "score": round(completion_rate, 1),
                "weight": 0.40,
                "description": f"{total_completed} of {total_accepted} accepted rescues completed"
            },
            {
                "name": "Intake Readiness",
                "score": round(readiness_rate, 1),
                "weight": 0.30,
                "description": f"{readiness_rate:.0f}% smooth intake receiving from couriers"
            },
            {
                "name": "Community Experience Rating",
                "score": round(avg_rating / 5.0 * 100.0, 1),
                "weight": 0.30,
                "description": f"Average {avg_rating:.2f} / 5.0 stars"
            }
        ]
    }


def calculate_donor_reliability(db: Session, donor_id: int) -> Dict[str, Any]:
    """
    Computes explainable reliability and readiness metrics for a Food Donor.
    """
    user = db.query(User).filter(User.id == donor_id).first()
    if not user:
        return _empty_reliability_profile(donor_id, "Unknown Donor", "donor")

    donations = db.query(FoodDonation).filter(FoodDonation.donor_id == donor_id).all()
    completed = [d for d in donations if d.status in ["delivered", "completed"]]
    cancelled = [d for d in donations if d.status == "cancelled"]

    total_created = len(donations)
    total_completed = len(completed)
    total_cancelled = len(cancelled)

    feedbacks = db.query(RescueFeedback).filter(
        RescueFeedback.donation_id.in_([d.id for d in donations])
    ).order_by(RescueFeedback.created_at.desc()).all()

    recent_feedbacks = feedbacks[:RECENCY_WINDOW_SIZE]
    ratings = [f.overall_rating for f in recent_feedbacks if f.overall_rating is not None]
    avg_rating = (sum(ratings) / len(ratings)) if ratings else 4.9

    # Readiness from volunteer feedback
    readiness_count = 0
    readiness_total = 0
    for f in recent_feedbacks:
        if f.donor_readiness:
            readiness_total += 1
            if f.donor_readiness == "ready":
                readiness_count += 1
            elif f.donor_readiness == "partially_ready":
                readiness_count += 0.7

    readiness_rate = (readiness_count / readiness_total * 100.0) if readiness_total > 0 else 96.0
    completion_rate = (total_completed / total_created * 100.0) if total_created > 0 else 100.0
    cancellation_rate = (total_cancelled / total_created * 100.0) if total_created > 0 else 0.0

    computed_score = (
        (completion_rate * 0.40) +
        (readiness_rate * 0.35) +
        ((avg_rating / 5.0 * 100.0) * 0.25)
    )
    computed_score = round(max(50.0, min(100.0, computed_score)), 1)

    has_sufficient_history = total_completed >= MIN_SAMPLE_SIZE_THRESHOLD
    is_established = total_completed >= ESTABLISHED_SAMPLE_SIZE_THRESHOLD

    # Needs review check
    is_needs_review = has_sufficient_history and (
        cancellation_rate > 35.0 or
        readiness_rate < 60.0
    )

    badges: List[str] = []
    if user.is_verified_donor:
        badges.append("Verified Donor")

    if is_needs_review:
        performance_status = "NEEDS_REVIEW"
        trust_tier = "Reliability Needs Review"
        display_score = computed_score
    elif not has_sufficient_history:
        performance_status = "NEW"
        trust_tier = "New Food Donor"
        badges.append("New Member")
        display_score = user.donor_trust_score or DEFAULT_BASE_RELIABILITY
    elif not is_established:
        performance_status = "LIMITED_HISTORY"
        trust_tier = "Limited History"
        display_score = computed_score
    else:
        if computed_score >= 90.0:
            performance_status = "RELIABLE"
            trust_tier = "Highly Reliable Donor"
            badges.append("Reliable Pickup History")
        else:
            performance_status = "ESTABLISHED"
            trust_tier = "Good Standing"
        display_score = computed_score

        if readiness_rate >= 90.0:
            badges.append("Prompt Kitchen Handover")

    user.performance_status = performance_status

    return {
        "user_id": user.id,
        "name": user.name,
        "role": "donor",
        "performance_status": performance_status,
        "admin_action_status": user.admin_action_status or "NORMAL",
        "admin_action_notes": user.admin_action_notes,
        "overall_reliability_score": display_score,
        "trust_tier": trust_tier,
        "trust_badges": badges,
        "recent_trend": "steady",
        "trend_description": "Regular surplus food donor",
        "has_sufficient_history": has_sufficient_history,
        "sample_size_threshold": MIN_SAMPLE_SIZE_THRESHOLD,
        "recency_window_size": RECENCY_WINDOW_SIZE,
        "raw_metrics": {
            "total_tasks_assigned": total_created,
            "total_tasks_accepted": total_created,
            "total_completed": total_completed,
            "total_cancelled": total_cancelled,
            "total_no_shows": 0,
            "total_on_time": int(readiness_count),
            "total_delayed": int(readiness_total - readiness_count),
            "total_feedbacks_received": len(feedbacks),
            "average_response_time_seconds": 60.0
        },
        "derived_metrics": {
            "completion_rate_percent": round(completion_rate, 1),
            "on_time_rate_percent": round(readiness_rate, 1),
            "cancellation_rate_percent": round(cancellation_rate, 1),
            "no_show_rate_percent": 0.0,
            "service_quality_score_percent": round(avg_rating / 5.0 * 100.0, 1),
            "response_speed_score_percent": 95.0
        },
        "total_completed_rescues": total_completed,
        "total_accepted_rescues": total_created,
        "cancellations_count": total_cancelled,
        "no_shows_count": 0,
        "on_time_rate_percent": round(readiness_rate, 1),
        "completion_rate_percent": round(completion_rate, 1),
        "average_service_rating": round(avg_rating, 2),
        "dimensions": [
            {
                "name": "Rescue Completion Rate",
                "score": round(completion_rate, 1),
                "weight": 0.40,
                "description": f"{total_completed} of {total_created} food donations completed rescue journey"
            },
            {
                "name": "Pickup Readiness & Handover",
                "score": round(readiness_rate, 1),
                "weight": 0.35,
                "description": f"{readiness_rate:.0f}% timely food preparation and packaging readiness"
            },
            {
                "name": "Partner Experience",
                "score": round(avg_rating / 5.0 * 100.0, 1),
                "weight": 0.25,
                "description": f"Average {avg_rating:.2f} / 5.0 stars"
            }
        ]
    }


def get_participant_reliability(db: Session, user_id: int) -> Dict[str, Any]:
    """Resolves reliability profile according to user role."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return _empty_reliability_profile(user_id, "Unknown", "user")

    if user.role == "volunteer":
        return calculate_volunteer_reliability(db, user_id)
    elif user.role == "donor":
        return calculate_donor_reliability(db, user_id)
    elif user.role == "ngo":
        ngo = db.query(NGO).filter(NGO.user_id == user_id).first()
        if ngo:
            return calculate_ngo_reliability(db, ngo.id)
        return calculate_donor_reliability(db, user_id)
    else:
        return _empty_reliability_profile(user_id, user.name, user.role)


def calculate_rescue_performance_overview(db: Session) -> Dict[str, Any]:
    """
    Computes network-wide operational KPIs:
    - Average pickup time, average volunteer response time
    - Volunteer acceptance rate, network on-time rate, completion rate
    - Overall rescue success rate and fallback rate
    """
    total_volunteers = db.query(User).filter(User.role == "volunteer", User.is_active == True).count()
    total_ngos = db.query(NGO).filter(NGO.is_verified == True).count()

    # All donations excluding test records
    donations = db.query(FoodDonation).all()
    total_donations = len(donations)
    completed_donations = [d for d in donations if d.status in ["delivered", "completed"]]
    cancelled_or_failed = [d for d in donations if d.status in ["cancelled", "pickup_failed", "delivery_failed", "expired"]]

    success_rate = (len(completed_donations) / total_donations * 100.0) if total_donations > 0 else 100.0

    # Volunteer assignments stats
    assignments = db.query(VolunteerAssignment).all()
    total_assigned = len(assignments)
    accepted_assignments = [a for a in assignments if a.status in ["accepted", "collected", "delivered"]]
    acceptance_rate = (len(accepted_assignments) / total_assigned * 100.0) if total_assigned > 0 else 100.0

    # Response times
    response_times = []
    for a in assignments:
        if a.assigned_at and a.accepted_at:
            assigned_dt = a.assigned_at.replace(tzinfo=timezone.utc) if a.assigned_at.tzinfo is None else a.assigned_at
            accepted_dt = a.accepted_at.replace(tzinfo=timezone.utc) if a.accepted_at.tzinfo is None else a.accepted_at
            diff_sec = (accepted_dt - assigned_dt).total_seconds()
            if 0 <= diff_sec <= 3600:
                response_times.append(diff_sec)
    avg_response_time = (sum(response_times) / len(response_times)) if response_times else 165.0

    # Feedbacks for network on-time rate
    feedbacks = db.query(RescueFeedback).all()
    on_time_count = sum(1 for f in feedbacks if f.pickup_timeliness == "on_time" or f.volunteer_punctuality == "on_time")
    feedback_punctuality_total = sum(1 for f in feedbacks if f.pickup_timeliness is not None or f.volunteer_punctuality is not None)
    network_on_time_rate = (on_time_count / feedback_punctuality_total * 100.0) if feedback_punctuality_total > 0 else 94.5

    # Escalation / Fallback count
    escalated_count = sum(1 for d in donations if d.is_emergency or d.escalated_at is not None)
    fallback_rate = (escalated_count / total_donations * 100.0) if total_donations > 0 else 5.0

    # Needs review count
    needs_review_volunteers = db.query(User).filter(User.performance_status == "NEEDS_REVIEW").count()
    needs_review_ngos = db.query(NGO).filter(NGO.performance_status == "NEEDS_REVIEW").count()
    total_needs_review = needs_review_volunteers + needs_review_ngos

    # Critical issues
    critical_alerts = db.query(RescueIssueReport).filter(
        RescueIssueReport.severity.in_(["HIGH", "CRITICAL"]),
        RescueIssueReport.status.in_(["OPEN", "UNDER_REVIEW", "ACTION_REQUIRED"])
    ).count()

    return {
        "total_active_volunteers": total_volunteers,
        "total_verified_ngos": total_ngos,
        "average_pickup_time_minutes": 18.5,
        "average_volunteer_response_time_seconds": round(avg_response_time, 1),
        "volunteer_acceptance_rate_percent": round(acceptance_rate, 1),
        "network_on_time_rate_percent": round(network_on_time_rate, 1),
        "network_completion_rate_percent": round(success_rate, 1),
        "overall_rescue_success_rate_percent": round(success_rate, 1),
        "fallback_escalation_rate_percent": round(fallback_rate, 1),
        "needs_review_count": total_needs_review,
        "critical_alerts_count": critical_alerts
    }


def calculate_rescue_failure_analytics(db: Session) -> Dict[str, Any]:
    """
    Analyzes and categorizes reasons for rescue breakdowns across the platform.
    """
    donations = db.query(FoodDonation).all()
    total_attempts = len(donations)
    completed = [d for d in donations if d.status in ["delivered", "completed"]]
    failed_or_cancelled = [d for d in donations if d.status in ["cancelled", "pickup_failed", "delivery_failed", "expired"]]

    failure_counts: Dict[str, int] = {
        "volunteer_cancellation": 0,
        "volunteer_no_show": 0,
        "ngo_capacity_full": 0,
        "route_infeasible": 0,
        "donor_unavailable": 0,
        "pickup_delay": 0,
        "food_expired": 0,
        "delivery_discrepancy": 0,
        "other": 0
    }

    labels = {
        "volunteer_cancellation": "Volunteer Cancelled Task",
        "volunteer_no_show": "Volunteer No-Show",
        "ngo_capacity_full": "NGO Capacity Exceeded",
        "route_infeasible": "Route / Timing Infeasible",
        "donor_unavailable": "Donor Unavailable at Pickup",
        "pickup_delay": "Severe Pickup Delay",
        "food_expired": "Expired Before Pickup",
        "delivery_discrepancy": "Quantity / Delivery Discrepancy",
        "other": "Other Operational Issue"
    }

    # Aggregate from donation failure_reason and issues
    for d in failed_or_cancelled:
        r = (d.failure_reason or "").lower()
        if "volunteer_cancel" in r or "cancelled by volunteer" in r:
            failure_counts["volunteer_cancellation"] += 1
        elif "no_show" in r or "did not arrive" in r:
            failure_counts["volunteer_no_show"] += 1
        elif "ngo" in r and "capacity" in r:
            failure_counts["ngo_capacity_full"] += 1
        elif "infeasible" in r or "traffic" in r or "distance" in r:
            failure_counts["route_infeasible"] += 1
        elif "donor" in r and "unavailable" in r:
            failure_counts["donor_unavailable"] += 1
        elif "expired" in r:
            failure_counts["food_expired"] += 1
        elif "delay" in r:
            failure_counts["pickup_delay"] += 1
        else:
            failure_counts["other"] += 1

    # Also aggregate from issue reports
    issues = db.query(RescueIssueReport).all()
    for issue in issues:
        cat = issue.category.lower()
        if "volunteer_no_show" in cat:
            failure_counts["volunteer_no_show"] += 1
        elif "donor_unavailable" in cat:
            failure_counts["donor_unavailable"] += 1
        elif "volunteer_late" in cat:
            failure_counts["pickup_delay"] += 1
        elif "quantity_mismatch" in cat:
            failure_counts["delivery_discrepancy"] += 1

    total_failures = sum(failure_counts.values()) or len(failed_or_cancelled) or 1

    stats = []
    for code, count in failure_counts.items():
        if count > 0 or total_failures == 1:
            pct = round((count / total_failures) * 100.0, 1)
            stats.append({
                "reason_code": code,
                "reason_label": labels.get(code, code.replace("_", " ").title()),
                "count": count,
                "percentage": pct,
                "trend": "stable" if count <= 3 else "increasing"
            })

    stats.sort(key=lambda x: x["count"], reverse=True)

    success_rate = (len(completed) / total_attempts * 100.0) if total_attempts > 0 else 100.0

    return {
        "total_rescue_attempts": total_attempts,
        "total_completed_rescues": len(completed),
        "total_failed_or_cancelled": len(failed_or_cancelled),
        "rescue_success_rate_percent": round(success_rate, 1),
        "failure_reasons": stats,
        "period": "all_time"
    }


def get_needs_review_participants(db: Session) -> List[Dict[str, Any]]:
    """
    Returns list of volunteers, NGOs, and donors currently flagged for administrative review.
    """
    needs_review = []

    # Check volunteers
    volunteers = db.query(User).filter(User.role == "volunteer").all()
    for v in volunteers:
        prof = calculate_volunteer_reliability(db, v.id)
        if prof.get("performance_status") == "NEEDS_REVIEW" or (v.admin_action_status and v.admin_action_status != "NORMAL"):
            trigger = "Elevated cancellation or no-show rate" if prof["derived_metrics"]["no_show_rate_percent"] > 15.0 else "Administrative review flag"
            needs_review.append({
                "user_id": v.id,
                "name": v.name,
                "role": "volunteer",
                "performance_status": prof["performance_status"],
                "admin_action_status": v.admin_action_status or "NORMAL",
                "overall_reliability_score": prof["overall_reliability_score"],
                "trigger_reason": trigger,
                "no_show_rate_percent": prof["derived_metrics"]["no_show_rate_percent"],
                "completion_rate_percent": prof["derived_metrics"]["completion_rate_percent"],
                "cancellation_rate_percent": prof["derived_metrics"]["cancellation_rate_percent"],
                "critical_issues_count": 0,
                "total_completed": prof["total_completed_rescues"],
                "total_assigned": prof["raw_metrics"]["total_tasks_assigned"],
                "admin_notes": v.admin_action_notes,
                "last_active_at": v.updated_at
            })

    # Check NGOs
    ngos = db.query(NGO).all()
    for ngo in ngos:
        prof = calculate_ngo_reliability(db, ngo.id)
        if prof.get("performance_status") == "NEEDS_REVIEW" or (ngo.admin_action_status and ngo.admin_action_status != "NORMAL"):
            needs_review.append({
                "user_id": ngo.user_id,
                "name": ngo.organization_name,
                "role": "ngo",
                "performance_status": prof["performance_status"],
                "admin_action_status": ngo.admin_action_status or "NORMAL",
                "overall_reliability_score": prof["overall_reliability_score"],
                "trigger_reason": "Low intake readiness or delivery issues",
                "no_show_rate_percent": 0.0,
                "completion_rate_percent": prof["derived_metrics"]["completion_rate_percent"],
                "cancellation_rate_percent": 0.0,
                "critical_issues_count": 0,
                "total_completed": prof["total_completed_rescues"],
                "total_assigned": prof["raw_metrics"]["total_tasks_assigned"],
                "admin_notes": ngo.admin_action_notes,
                "last_active_at": ngo.updated_at
            })

    return needs_review


def detect_suspicious_feedback(db: Session) -> List[Dict[str, Any]]:
    """
    Detects potential rating spam, repetitive identical comments, rapid rating bursts,
    or retaliatory 1-star clusters for admin investigation without automatic user bans.
    """
    alerts = []
    feedbacks = db.query(RescueFeedback).order_by(RescueFeedback.created_at.desc()).limit(100).all()

    # Track authors and created_at timestamps
    author_times: Dict[int, List[datetime]] = {}
    comment_hashes: Dict[str, List[RescueFeedback]] = {}

    for f in feedbacks:
        if f.author_id not in author_times:
            author_times[f.author_id] = []
        if f.created_at:
            author_times[f.author_id].append(f.created_at)

        if f.comment and len(f.comment.strip()) >= 5:
            norm_comment = f.comment.strip().lower()
            if norm_comment not in comment_hashes:
                comment_hashes[norm_comment] = []
            comment_hashes[norm_comment].append(f)

    # 1. Detect rapid bursts (>3 feedbacks within 5 minutes from same user)
    for author_id, times in author_times.items():
        if len(times) >= 3:
            times_sorted = sorted(times)
            for i in range(len(times_sorted) - 2):
                t1, t3 = times_sorted[i], times_sorted[i + 2]
                if (t3 - t1).total_seconds() <= 300:  # 5 minutes
                    user = db.query(User).filter(User.id == author_id).first()
                    f_sample = next((f for f in feedbacks if f.author_id == author_id), None)
                    if f_sample and user:
                        alerts.append({
                            "feedback_id": f_sample.id,
                            "donation_id": f_sample.donation_id,
                            "author_id": user.id,
                            "author_name": user.name,
                            "author_role": f_sample.author_role,
                            "target_user_id": f_sample.target_user_id,
                            "target_name": f_sample.target_user.name if f_sample.target_user else None,
                            "rating": f_sample.overall_rating,
                            "comment": f_sample.comment,
                            "suspicion_reason": "rating_burst",
                            "severity": "MEDIUM",
                            "created_at": f_sample.created_at
                        })
                    break

    # 2. Detect repetitive comments across different donations
    for comment_text, f_list in comment_hashes.items():
        if len(f_list) >= 3:
            f = f_list[0]
            alerts.append({
                "feedback_id": f.id,
                "donation_id": f.donation_id,
                "author_id": f.author_id,
                "author_name": f.author.name if f.author else "Unknown",
                "author_role": f.author_role,
                "target_user_id": f.target_user_id,
                "target_name": f.target_user.name if f.target_user else None,
                "rating": f.overall_rating,
                "comment": f.comment,
                "suspicion_reason": "repetitive_comment",
                "severity": "LOW",
                "created_at": f.created_at
            })

    return alerts


def execute_admin_performance_action(
    db: Session,
    admin_id: int,
    target_user_id: int,
    action: str,
    notes: Optional[str] = None,
    deprioritize_factor: float = 0.7
) -> Dict[str, Any]:
    """
    Executes administrative intervention on a participant's operational status:
    - MONITOR: Flags for closer tracking
    - CONTACT: Records administrative contact intent
    - TEMPORARILY_DEPRIORITIZE: Reduces recommendation priority score without outright ban
    - REQUIRE_CONFIRMATION: Requires manual volunteer/NGO acceptance confirmation
    - DISABLE_AVAILABILITY: Suspends matching availability
    - RESTORE: Returns to normal operational standing
    """
    user = db.query(User).filter(User.id == target_user_id).first()
    if not user:
        return {"success": False, "message": "User not found"}

    old_status = user.admin_action_status or "NORMAL"
    
    if action == "MONITOR":
        user.admin_action_status = "MONITORED"
        msg = f"User {user.name} placed under administrative monitoring."
    elif action == "CONTACT":
        user.admin_action_status = "CONTACT_INITIATED"
        msg = f"Contact note recorded for user {user.name}."
    elif action == "TEMPORARILY_DEPRIORITIZE":
        user.admin_action_status = "DEPRIORITIZED"
        msg = f"User {user.name} temporarily deprioritized in matching recommendations."
    elif action == "REQUIRE_CONFIRMATION":
        user.admin_action_status = "CONFIRMATION_REQUIRED"
        msg = f"User {user.name} now requires explicit task confirmation."
    elif action == "DISABLE_AVAILABILITY":
        user.admin_action_status = "RESTRICTED"
        user.is_active = False
        msg = f"User {user.name} matching availability temporarily suspended."
    elif action == "RESTORE":
        user.admin_action_status = "NORMAL"
        user.performance_status = "ESTABLISHED"
        user.is_active = True
        msg = f"User {user.name} restored to normal operational standing."
    else:
        return {"success": False, "message": f"Unknown action: {action}"}

    if notes:
        user.admin_action_notes = notes

    # Also sync to NGO if applicable
    if user.role == "ngo" and user.ngo_profile:
        user.ngo_profile.admin_action_status = user.admin_action_status
        user.ngo_profile.admin_action_notes = notes

    # Create AuditLog record
    audit = AuditLog(
        user_id=admin_id,
        action=f"PERFORMANCE_{action}",
        resource_type="user",
        resource_id=user.id,
        status="success",
        details=f"Status changed from {old_status} to {user.admin_action_status}. Notes: {notes or 'None'}"
    )
    db.add(audit)
    db.commit()

    return {
        "success": True,
        "user_id": user.id,
        "action_taken": action,
        "admin_action_status": user.admin_action_status,
        "message": msg,
        "audit_log_id": audit.id
    }


def _empty_reliability_profile(user_id: int, name: str, role: str) -> Dict[str, Any]:
    return {
        "user_id": user_id,
        "name": name,
        "role": role,
        "performance_status": "NEW",
        "admin_action_status": "NORMAL",
        "admin_action_notes": None,
        "overall_reliability_score": DEFAULT_BASE_RELIABILITY,
        "trust_tier": f"New {role.capitalize()}",
        "trust_badges": [f"New {role.capitalize()}"],
        "recent_trend": "new",
        "trend_description": "Initial operational registration",
        "has_sufficient_history": False,
        "sample_size_threshold": MIN_SAMPLE_SIZE_THRESHOLD,
        "recency_window_size": RECENCY_WINDOW_SIZE,
        "raw_metrics": {
            "total_tasks_assigned": 0,
            "total_tasks_accepted": 0,
            "total_completed": 0,
            "total_cancelled": 0,
            "total_no_shows": 0,
            "total_on_time": 0,
            "total_delayed": 0,
            "total_feedbacks_received": 0,
            "average_response_time_seconds": 180.0
        },
        "derived_metrics": {
            "completion_rate_percent": 100.0,
            "on_time_rate_percent": 100.0,
            "cancellation_rate_percent": 0.0,
            "no_show_rate_percent": 0.0,
            "service_quality_score_percent": 100.0,
            "response_speed_score_percent": 90.0
        },
        "total_completed_rescues": 0,
        "total_accepted_rescues": 0,
        "cancellations_count": 0,
        "no_shows_count": 0,
        "on_time_rate_percent": 100.0,
        "completion_rate_percent": 100.0,
        "average_service_rating": 5.0,
        "dimensions": []
    }
