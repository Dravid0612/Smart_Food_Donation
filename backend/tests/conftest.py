import pytest
import sys
import os

# Ensure backend root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from seed import seed_database
from app.db.session import SessionLocal
from app.models.models import VolunteerAssignment, User, FoodDonation

@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """Seeds the SQLite database with test users, NGOs, volunteers, and donations before running tests."""
    seed_database()

@pytest.fixture(scope="function", autouse=True)
def isolate_test_database_state():
    """
    Per-test isolation fixture:
    Cleans up any active or test-created volunteer assignments and restores active user state
    both before and after each test function.
    This guarantees that single-active-assignment enforcement works correctly within each test
    without cross-test state leakage or volunteer lockouts.
    """
    def _reset():
        db = SessionLocal()
        try:
            db.query(VolunteerAssignment).delete()
            db.query(FoodDonation).filter(FoodDonation.assigned_volunteer_id.isnot(None)).update(
                {FoodDonation.assigned_volunteer_id: None}, synchronize_session=False
            )
            db.query(User).update({User.is_active: True})
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()

    _reset()
    yield
    _reset()

@pytest.fixture(scope="function")
def db_session():
    """Provides a fresh database session for test functions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
