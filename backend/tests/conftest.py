import pytest
import sys
import os

# Ensure backend root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from seed import seed_database
from app.db.session import SessionLocal

@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """Seeds the SQLite database with test users, NGOs, volunteers, and donations before running tests."""
    seed_database()

@pytest.fixture(scope="function")
def db_session():
    """Provides a fresh database session for test functions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

