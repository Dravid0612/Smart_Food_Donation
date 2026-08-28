import os

class Settings:
    PROJECT_NAME: str = "Smart Food Donation Platform"
    API_V1_STR: str = "/api"

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./smart_food.db")

    # Security — Short-lived access tokens + 7-day refresh tokens
    JWT_SECRET: str = os.getenv("JWT_SECRET", "super-secret-jwt-key-food-donation-2026-sfd")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))   # 30 minutes
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))        # 7 days
    REFRESH_TOKEN_SECRET: str = os.getenv("REFRESH_TOKEN_SECRET", "refresh-secret-sfd-2026-smart-food-platform")

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

    # ─── Firebase Cloud Messaging (FCM) ─────────────────────────────────────
    # Set FCM_SERVER_KEY / FCM_PROJECT_ID to enable real push notifications.
    # Default uses a mock adapter that logs but does NOT push to devices.
    FCM_SERVER_KEY: str = os.getenv("FCM_SERVER_KEY", "")
    FCM_PROJECT_ID: str = os.getenv("FCM_PROJECT_ID", "")

    # ─── Pickup OTP Settings ────────────────────────────────────────────────
    OTP_PICKUP_EXPIRE_MINUTES: int = int(os.getenv("OTP_PICKUP_EXPIRE_MINUTES", "5"))
    OTP_PHONE_VERIFY_EXPIRE_MINUTES: int = int(os.getenv("OTP_PHONE_VERIFY_EXPIRE_MINUTES", "10"))
    OTP_REGEN_MAX_PER_WINDOW: int = int(os.getenv("OTP_REGEN_MAX_PER_WINDOW", "3"))
    OTP_REGEN_WINDOW_MINUTES: int = int(os.getenv("OTP_REGEN_WINDOW_MINUTES", "10"))
    OTP_PHONE_VERIFY_MAX_PER_WINDOW: int = int(os.getenv("OTP_PHONE_VERIFY_MAX_PER_WINDOW", "3"))
    OTP_PHONE_VERIFY_WINDOW_MINUTES: int = int(os.getenv("OTP_PHONE_VERIFY_WINDOW_MINUTES", "15"))

settings = Settings()
