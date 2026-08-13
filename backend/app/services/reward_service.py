from sqlalchemy.orm import Session
from app.models.models import Reward

def add_reward_points(db: Session, user_id: int, points_to_add: int = 10) -> Reward:
    reward = db.query(Reward).filter(Reward.user_id == user_id).first()
    if not reward:
        reward = Reward(user_id=user_id, points=0, level="Bronze")
        db.add(reward)
        db.flush()

    reward.points += points_to_add
    reward.level = calculate_level(reward.points)
    db.commit()
    db.refresh(reward)
    return reward

def calculate_level(points: int) -> str:
    if points >= 300:
        return "Platinum"
    elif points >= 150:
        return "Gold"
    elif points >= 50:
        return "Silver"
    else:
        return "Bronze"

def get_reward_details(db: Session, user_id: int) -> dict:
    reward = db.query(Reward).filter(Reward.user_id == user_id).first()
    if not reward:
        reward = Reward(user_id=user_id, points=0, level="Bronze")
        db.add(reward)
        db.commit()
        db.refresh(reward)

    level_thresholds = {
        "Bronze": 50,
        "Silver": 150,
        "Gold": 300,
        "Platinum": 500
    }
    next_level = level_thresholds.get(reward.level, 500)
    pts_needed = max(0, next_level - reward.points)

    return {
        "id": reward.id,
        "user_id": reward.user_id,
        "points": reward.points,
        "level": reward.level,
        "next_level_points": next_level,
        "points_to_next_level": pts_needed
    }
