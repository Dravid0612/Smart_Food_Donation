import os
import time
import logging
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

logger = logging.getLogger("smart_food_rescue.db")

# Normalize PostgreSQL URLs (Heroku/Render/Supabase use postgres:// which SQLAlchemy 2.0 rejects)
DATABASE_URL = settings.DATABASE_URL
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False, "timeout": 30.0},
        echo=settings.DB_ECHO,
    )

    # Enable WAL mode and foreign key enforcement for SQLite
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        try:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.close()
        except Exception as e:
            logger.warning(f"Could not configure SQLite pragmas: {e}")

else:
    # Production-ready PostgreSQL connection pooling
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        pool_timeout=settings.DB_POOL_TIMEOUT,
        pool_recycle=settings.DB_POOL_RECYCLE,
        echo=settings.DB_ECHO,
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def mask_database_url(url: str) -> str:
    """Masks database credentials for secure diagnostics/logging."""
    if "@" not in url:
        return url
    try:
        prefix, rest = url.split("://", 1)
        creds, host_part = rest.split("@", 1)
        if ":" in creds:
            user, _ = creds.split(":", 1)
            return f"{prefix}://{user}:***@{host_part}"
        return f"{prefix}://***@{host_part}"
    except Exception:
        return "configured_database_url"


def validate_database_connection() -> dict:
    """
    Validates database connectivity on startup or health checks.
    Measures query latency and returns engine metadata.
    """
    start = time.perf_counter()
    dialect = engine.dialect.name
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        latency_ms = round((time.perf_counter() - start) * 1000, 2)
        return {
            "status": "ok",
            "dialect": dialect,
            "latency_ms": latency_ms,
            "database_url": mask_database_url(DATABASE_URL),
        }
    except Exception as e:
        latency_ms = round((time.perf_counter() - start) * 1000, 2)
        logger.error(f"Database connection validation failed ({dialect}): {e}")
        return {
            "status": "unreachable",
            "dialect": dialect,
            "latency_ms": latency_ms,
            "error": str(e),
            "database_url": mask_database_url(DATABASE_URL),
        }


def get_db_diagnostics() -> dict:
    """Returns database engine and connection pool telemetry."""
    dialect = engine.dialect.name
    diag = {
        "dialect": dialect,
        "is_sqlite": dialect == "sqlite",
        "is_postgresql": dialect == "postgresql",
        "database_url": mask_database_url(DATABASE_URL),
        "echo": settings.DB_ECHO,
    }

    # Inspect pool telemetry if available
    pool = getattr(engine, "pool", None)
    if pool:
        diag["pool"] = {
            "size": getattr(pool, "size", lambda: None)(),
            "checked_in": getattr(pool, "checkedin", lambda: None)(),
            "checked_out": getattr(pool, "checkedout", lambda: None)(),
            "overflow": getattr(pool, "overflow", lambda: None)(),
        }
    return diag
