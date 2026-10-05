import time
import uuid
import logging
from datetime import datetime, timezone
from fastapi import FastAPI, Request, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from app.core.config import settings
from app.db.session import engine, validate_database_connection, get_db_diagnostics
from app.db.base import Base
import app.models # Ensures all models are registered with Base metadata

logger = logging.getLogger("smart_food_rescue.api")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

# Create database tables automatically
Base.metadata.create_all(bind=engine)

def _ensure_sqlite_columns():
    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            result = conn.execute(text("PRAGMA table_info(food_donations)"))
            existing_cols = {row[1] for row in result.fetchall()}
            
            new_cols = [
                ("food_source", "VARCHAR(50) DEFAULT 'KNOWN'"),
                ("custom_food_name", "VARCHAR(255)"),
                ("food_description", "TEXT"),
                ("major_ingredients", "TEXT"),
                ("quantity_unit_label", "VARCHAR(100)"),
                ("estimated_meals", "FLOAT"),
                ("rule_coverage", "VARCHAR(50) DEFAULT 'HIGH'"),
                ("classification_source", "VARCHAR(50) DEFAULT 'rule_exact'"),
                ("classification_confidence", "FLOAT DEFAULT 1.0"),
                ("last_alerted_urgency", "VARCHAR(50)"),
                ("last_alerted_at", "DATETIME"),
                ("current_alert_wave", "INTEGER DEFAULT 0"),
                ("wave_timeout_at", "DATETIME"),
                ("alert_history_json", "TEXT"),
                ("pickup_mode", "VARCHAR(50) DEFAULT 'volunteer_dispatch'"),
            ]
            for col_name, col_type in new_cols:
                if col_name not in existing_cols:
                    try:
                        conn.execute(text(f"ALTER TABLE food_donations ADD COLUMN {col_name} {col_type}"))
                    except Exception:
                        pass

            # Match offers
            result_offers = conn.execute(text("PRAGMA table_info(match_offers)"))
            existing_offer_cols = {row[1] for row in result_offers.fetchall()}
            offer_cols = [
                ("wave_number", "INTEGER DEFAULT 1"),
                ("first_viewed_at", "DATETIME"),
                ("response_time_seconds", "FLOAT"),
            ]
            for col_name, col_type in offer_cols:
                if col_name not in existing_offer_cols:
                    try:
                        conn.execute(text(f"ALTER TABLE match_offers ADD COLUMN {col_name} {col_type}"))
                    except Exception:
                        pass

            # Users — phone verification + language
            result_users = conn.execute(text("PRAGMA table_info(users)"))
            existing_user_cols = {row[1] for row in result_users.fetchall()}
            user_new_cols = [
                ("preferred_language", "VARCHAR(10) DEFAULT 'en'"),
                ("phone_verified", "BOOLEAN DEFAULT 0"),
                ("phone_country_code", "VARCHAR(10) DEFAULT '+91'"),
                ("phone_normalized", "VARCHAR(20)"),
            ]
            for col_name, col_type in user_new_cols:
                if col_name not in existing_user_cols:
                    try:
                        conn.execute(text(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}"))
                    except Exception:
                        pass

            # Notifications — event type, deep-link, dedup, FCM tracking
            result_notif = conn.execute(text("PRAGMA table_info(notifications)"))
            existing_notif_cols = {row[1] for row in result_notif.fetchall()}
            notif_new_cols = [
                ("event_type", "VARCHAR(100)"),
                ("deep_link_data", "TEXT"),
                ("dedup_key", "VARCHAR(255)"),
                ("is_sent", "BOOLEAN DEFAULT 0"),
                ("sent_at", "DATETIME"),
                ("opened_at", "DATETIME"),
            ]
            for col_name, col_type in notif_new_cols:
                if col_name not in existing_notif_cols:
                    try:
                        conn.execute(text(f"ALTER TABLE notifications ADD COLUMN {col_name} {col_type}"))
                    except Exception:
                        pass

            conn.commit()
    except Exception as e:
        logger.warning(f"SQLite column verification skipped: {e}")

if engine.dialect.name == "sqlite":
    _ensure_sqlite_columns()

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup validation and background monitor
    db_res = validate_database_connection()
    logger.info(
        f"[Startup] Database connection verified: dialect={db_res['dialect']} "
        f"latency={db_res['latency_ms']}ms status={db_res['status']} url={db_res['database_url']}"
    )
    from app.services.proactive_dispatch_service import BackgroundUrgencyMonitor
    BackgroundUrgencyMonitor.start(interval_seconds=60)
    yield
    # Graceful shutdown of background monitor
    from app.services.proactive_dispatch_service import BackgroundUrgencyMonitor
    BackgroundUrgencyMonitor.stop()

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Structured Request Tracing Middleware
@app.middleware("http")
async def request_tracing_middleware(request: Request, call_next):
    request_id = f"SR-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
    request.state.request_id = request_id
    start_time = time.time()

    # Process request
    try:
        response = await call_next(request)
        duration_ms = round((time.time() - start_time) * 1000, 2)
        response.headers["X-Request-ID"] = request_id
        
        # Log request without sensitive payloads (never log passwords, tokens, or OTPs)
        logger.info(
            f"[{request_id}] {request.method} {request.url.path} -> {response.status_code} ({duration_ms}ms)"
        )
        return response
    except Exception as e:
        duration_ms = round((time.time() - start_time) * 1000, 2)
        logger.error(f"[{request_id}] {request.method} {request.url.path} FAILED ({duration_ms}ms): {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": "We couldn't complete that request right now. Please try again.",
                "error_code": "INTERNAL_SERVER_ERROR",
                "request_id": request_id,
            },
            headers={"X-Request-ID": request_id},
        )

# Standardized Error Handling
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    request_id = getattr(request.state, "request_id", f"SR-{uuid.uuid4().hex[:6].upper()}")
    error_code_map = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        409: "STATE_CONFLICT",
        422: "VALIDATION_ERROR",
        429: "RATE_LIMITED",
    }
    error_code = error_code_map.get(exc.status_code, "ERROR")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "error_code": error_code,
            "request_id": request_id,
        },
        headers={"X-Request-ID": request_id},
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    request_id = getattr(request.state, "request_id", f"SR-{uuid.uuid4().hex[:6].upper()}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": "Please check all required fields before continuing.",
            "error_code": "VALIDATION_ERROR",
            "errors": [
                {"loc": list(err.get("loc", [])), "msg": err.get("msg", "Invalid field")}
                for err in exc.errors()
            ],
            "request_id": request_id,
        },
        headers={"X-Request-ID": request_id},
    )

# Import & register routers
from app.api.routes import auth, donations, ngos, volunteers, notifications, rewards, admin, ai, disputes, feedback, performance, webhooks

app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(ai.router, prefix=settings.API_V1_STR)
app.include_router(donations.router, prefix=settings.API_V1_STR)
app.include_router(ngos.router, prefix=settings.API_V1_STR)
app.include_router(volunteers.router, prefix=settings.API_V1_STR)
app.include_router(notifications.router, prefix=settings.API_V1_STR)
app.include_router(rewards.router, prefix=settings.API_V1_STR)
app.include_router(admin.router, prefix=settings.API_V1_STR)
app.include_router(disputes.router, prefix=settings.API_V1_STR)
app.include_router(feedback.router, prefix=settings.API_V1_STR)
app.include_router(performance.router, prefix=settings.API_V1_STR)
app.include_router(webhooks.router, prefix=settings.API_V1_STR)



@app.get("/health")
def health_check():
    db_val = validate_database_connection()
    db_diag = get_db_diagnostics()
    from app.services.proactive_dispatch_service import BackgroundUrgencyMonitor
    monitor_running = getattr(BackgroundUrgencyMonitor, "_running", False)

    is_ok = db_val["status"] == "ok"
    status_code = status.HTTP_200_OK if is_ok else status.HTTP_503_SERVICE_UNAVAILABLE

    return JSONResponse(
        status_code=status_code,
        content={
            "status": "ok" if is_ok else "degraded",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "database": {
                "status": db_val["status"],
                "dialect": db_val["dialect"],
                "latency_ms": db_val["latency_ms"],
                "database_url": db_val["database_url"],
                "pool": db_diag.get("pool"),
            },
            "services": {
                "background_urgency_monitor": "running" if monitor_running else "stopped",
                "sms_provider": settings.SMS_PROVIDER,
                "fcm_configured": bool(settings.FCM_PROJECT_ID and (settings.GOOGLE_APPLICATION_CREDENTIALS or settings.FIREBASE_CREDENTIALS_PATH or os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"))),
            },
            "version": "1.0.0"
        }
    )

@app.get("/health/live")
def liveness_probe():
    """K8s liveness probe: returns 200 if API process is running."""
    return {"status": "alive", "timestamp": datetime.now(timezone.utc).isoformat()}

@app.get("/health/ready")
def readiness_probe():
    """K8s readiness probe: returns 200 only if database connection succeeds."""
    db_val = validate_database_connection()
    if db_val["status"] != "ok":
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "not_ready",
                "reason": "database_unreachable",
                "details": db_val.get("error", "Database check failed")
            }
        )
    return {"status": "ready", "latency_ms": db_val["latency_ms"], "timestamp": datetime.now(timezone.utc).isoformat()}

@app.get("/")
def root():
    return {
        "message": "Welcome to Smart Food Donation Platform API",
        "docs": "/docs",
        "health": "/health",
        "control_center": "/control-center",
        "version": "1.0.0"
    }

# Mount React Web Control Center (Primary Admin Workspace)
import os
from fastapi.staticfiles import StaticFiles
_web_dist = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "web", "dist"))
if os.path.exists(_web_dist):
    app.mount("/control-center", StaticFiles(directory=_web_dist, html=True), name="control-center")

