import os
from pathlib import Path
from dotenv import load_dotenv

# Load local environment variables from backend/.env or parent directories
_env_path = Path(__file__).resolve().parent.parent.parent / ".env"
if _env_path.exists():
    load_dotenv(dotenv_path=_env_path)
else:
    load_dotenv()

class Settings:
    PROJECT_NAME: str = "Smart Food Donation Platform"
    API_V1_STR: str = "/api"

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./smart_food.db")
    DB_POOL_SIZE: int = int(os.getenv("DB_POOL_SIZE", "20"))
    DB_MAX_OVERFLOW: int = int(os.getenv("DB_MAX_OVERFLOW", "30"))
    DB_POOL_TIMEOUT: int = int(os.getenv("DB_POOL_TIMEOUT", "30"))
    DB_POOL_RECYCLE: int = int(os.getenv("DB_POOL_RECYCLE", "1800"))
    DB_ECHO: bool = os.getenv("DB_ECHO", "false").lower() in ("true", "1")

    # Security — Short-lived access tokens + 7-day refresh tokens
    JWT_SECRET: str = os.getenv("JWT_SECRET", "super-secret-jwt-key-food-donation-2026-sfd")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))   # 30 minutes
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))        # 7 days
    REFRESH_TOKEN_SECRET: str = os.getenv("REFRESH_TOKEN_SECRET", "refresh-secret-sfd-2026-smart-food-platform")
    ADMIN_PROVISIONING_SECRET: str = os.getenv("ADMIN_PROVISIONING_SECRET", "admin-setup-secret-2026")

    # OTP / QR validity window (hours) — configurable
    OTP_EXPIRE_HOURS: int = int(os.getenv("OTP_EXPIRE_HOURS", "6"))
    QR_EXPIRE_HOURS: int = int(os.getenv("QR_EXPIRE_HOURS", "6"))

    # Login brute-force rate limiting — configurable
    MAX_FAILED_LOGIN_ATTEMPTS: int = int(os.getenv("MAX_FAILED_LOGIN_ATTEMPTS", "5"))
    LOGIN_LOCKOUT_WINDOW_SECONDS: int = int(os.getenv("LOGIN_LOCKOUT_WINDOW_SECONDS", "300"))  # 5 minutes

    # Supabase (Optional)
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_ANON_KEY: str = os.getenv("SUPABASE_ANON_KEY", "")
    SUPABASE_SERVICE_KEY: str = os.getenv("SUPABASE_SERVICE_KEY", "")

    # ─── SMS Provider Configuration ─────────────────────────────────────────
    # Set SMS_PROVIDER=twilio (or msg91/exotel) to use real delivery.
    # Default is "mock" which logs the send but does NOT actually deliver SMS.
    # NEVER commit real credentials — use environment variables or .env file.
    SMS_PROVIDER: str = os.getenv("SMS_PROVIDER", "mock")       # mock | twilio | msg91 | exotel
    SMS_API_KEY: str = os.getenv("SMS_API_KEY", "")             # Provider API key
    SMS_API_SECRET: str = os.getenv("SMS_API_SECRET", "")       # Provider API secret
    SMS_SENDER_ID: str = os.getenv("SMS_SENDER_ID", "SFRESCUE") # Sender ID / from number
    SMS_TEMPLATE_ID: str = os.getenv("SMS_TEMPLATE_ID", "")     # DLT template ID (India)
    SMS_WEBHOOK_SECRET: str = os.getenv("SMS_WEBHOOK_SECRET", "sms-webhook-secret-sfd-2026")

    # ─── Road Routing Provider ──────────────────────────────────────────────
    # Options: heuristic | google | osrm
    ROUTING_PROVIDER: str = os.getenv("ROUTING_PROVIDER", "heuristic").lower()
    GOOGLE_MAPS_API_KEY: str = os.getenv("GOOGLE_MAPS_API_KEY", os.getenv("ROUTING_API_KEY", ""))
    ROUTING_TIMEOUT_SECONDS: float = float(os.getenv("ROUTING_TIMEOUT_SECONDS", "5.0"))

    # ─── AI Vision Provider ─────────────────────────────────────────────────
    # Options: gemini | local
    AI_PROVIDER: str = os.getenv("AI_PROVIDER", "gemini").lower()
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", os.getenv("GOOGLE_API_KEY", ""))
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    AI_TIMEOUT_SECONDS: float = float(os.getenv("AI_TIMEOUT_SECONDS", "10.0"))

    # ─── Firebase Cloud Messaging (FCM HTTP v1) ─────────────────────────────
    # Current FCM HTTP v1 uses OAuth 2.0 service account credentials.
    # Set FCM_PROJECT_ID and GOOGLE_APPLICATION_CREDENTIALS (or FIREBASE_CREDENTIALS_PATH).
    # Default uses a mock adapter that logs but does NOT push to devices.
    FCM_PROJECT_ID: str = os.getenv("FCM_PROJECT_ID", "")
    GOOGLE_APPLICATION_CREDENTIALS: str = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", os.getenv("FIREBASE_CREDENTIALS_PATH", ""))
    FIREBASE_CREDENTIALS_PATH: str = os.getenv("FIREBASE_CREDENTIALS_PATH", os.getenv("GOOGLE_APPLICATION_CREDENTIALS", ""))
    FCM_SERVER_KEY: str = os.getenv("FCM_SERVER_KEY", "")  # Optional legacy fallback only

    # ─── Pickup OTP Settings ────────────────────────────────────────────────
    OTP_PICKUP_EXPIRE_MINUTES: int = int(os.getenv("OTP_PICKUP_EXPIRE_MINUTES", "5"))
    OTP_PHONE_VERIFY_EXPIRE_MINUTES: int = int(os.getenv("OTP_PHONE_VERIFY_EXPIRE_MINUTES", "10"))
    OTP_REGEN_MAX_PER_WINDOW: int = int(os.getenv("OTP_REGEN_MAX_PER_WINDOW", "3"))
    OTP_REGEN_WINDOW_MINUTES: int = int(os.getenv("OTP_REGEN_WINDOW_MINUTES", "10"))
    OTP_PHONE_VERIFY_MAX_PER_WINDOW: int = int(os.getenv("OTP_PHONE_VERIFY_MAX_PER_WINDOW", "3"))
    OTP_PHONE_VERIFY_WINDOW_MINUTES: int = int(os.getenv("OTP_PHONE_VERIFY_WINDOW_MINUTES", "15"))
    # ─── API Optimization & Budget Controls ─────────────────────────────────
    ROUTING_MIN_MOVEMENT_METERS: float = float(os.getenv("ROUTING_MIN_MOVEMENT_METERS", "500.0"))
    ROUTING_CACHE_TTL_SECONDS: int = int(os.getenv("ROUTING_CACHE_TTL_SECONDS", "300"))
    ROUTING_NON_ACTIVE_CACHE_TTL_SECONDS: int = int(os.getenv("ROUTING_NON_ACTIVE_CACHE_TTL_SECONDS", "900"))
    ROUTING_MAX_CANDIDATES_PER_REMATCH: int = int(os.getenv("ROUTING_MAX_CANDIDATES_PER_REMATCH", "5"))

    AI_PROVIDER_COOLDOWN_SECONDS: int = int(os.getenv("AI_PROVIDER_COOLDOWN_SECONDS", "300"))
    AI_MAX_TRANSIENT_RETRIES: int = int(os.getenv("AI_MAX_TRANSIENT_RETRIES", "1"))
    AI_IMAGE_CACHE_TTL_SECONDS: int = int(os.getenv("AI_IMAGE_CACHE_TTL_SECONDS", "86400"))  # 24 hours

    FCM_MAX_TRANSIENT_RETRIES: int = int(os.getenv("FCM_MAX_TRANSIENT_RETRIES", "1"))

settings = Settings()

