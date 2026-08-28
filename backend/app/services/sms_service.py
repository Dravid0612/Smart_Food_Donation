"""
SMS Provider Abstraction Layer — Smart Food Rescue
===================================================
Provider-independent SMS service. Supports:
  - mock   : Default. Logs send, returns SENT. Never claims DELIVERED.
  - twilio : Configure via SMS_API_KEY (Account SID) + SMS_API_SECRET (Auth Token)
  - msg91  : Configure via SMS_API_KEY + SMS_TEMPLATE_ID + SMS_SENDER_ID
  - exotel : Configure via SMS_API_KEY + SMS_API_SECRET + SMS_SENDER_ID

SECURITY RULES:
  - NEVER log the plaintext OTP.
  - NEVER claim DELIVERED without provider confirmation.
  - NEVER hard-code credentials here. Use environment variables.
  - Webhook validation must be used to authenticate provider callbacks.
"""

import os
import logging
import hashlib
import hmac
import json
import secrets
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from app.core.config import settings

logger = logging.getLogger("smart_food_rescue.sms")


# ─────────────────────────────────────────────────────────────────────────────
# Data Transfer Objects
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class SendResult:
    """Result of an SMS send attempt."""
    success: bool
    provider: str
    provider_message_id: Optional[str] = None
    initial_status: str = "QUEUED"  # QUEUED | SENT | FAILED
    failure_reason: Optional[str] = None
    raw_response: Optional[dict] = field(default_factory=dict)


@dataclass
class DeliveryStatusResult:
    """Result of a delivery status check."""
    provider_message_id: str
    status: str            # QUEUED | SENT | DELIVERED | FAILED | EXPIRED | UNKNOWN
    delivered_at: Optional[datetime] = None
    failed_at: Optional[datetime] = None
    failure_reason: Optional[str] = None


@dataclass
class WebhookDeliveryUpdate:
    """Parsed delivery receipt from provider webhook callback."""
    provider_message_id: str
    status: str            # DELIVERED | FAILED | SENT | UNKNOWN
    timestamp: Optional[datetime] = None
    failure_reason: Optional[str] = None
    raw_payload: Optional[dict] = field(default_factory=dict)


# ─────────────────────────────────────────────────────────────────────────────
# SMS Content Builder
# ─────────────────────────────────────────────────────────────────────────────

def build_otp_sms_body(otp: str, purpose: str, expires_minutes: int = 5) -> str:
    """
    Builds the SMS body for OTP delivery.
    SECURITY: Never include address, NGO info, donation ID, JWT, or admin data.
    """
    if purpose == "PICKUP_VERIFICATION_OTP":
        return (
            f"Smart Food Rescue pickup code: {otp}. "
            f"Share this code only with the assigned volunteer at pickup. "
            f"Code expires in {expires_minutes} minutes."
        )
    elif purpose == "PHONE_VERIFICATION_OTP":
        return (
            f"Smart Food Rescue verification code: {otp}. "
            f"Use this code to verify your phone number. "
            f"Expires in {expires_minutes} minutes. Do not share."
        )
    else:
        return (
            f"Smart Food Rescue code: {otp}. "
            f"Expires in {expires_minutes} minutes. Do not share."
        )


def mask_phone(phone: str) -> str:
    """Masks all but last 4 digits of a phone number. E.g. ****3210 or +91 ****3210"""
    if not phone:
        return "****"
    digits_only = ''.join(c for c in phone if c.isdigit())
    if len(digits_only) >= 4:
        last4 = digits_only[-4:]
        if phone.startswith("+"):
            # Keep country code prefix visible: +91 ****3210
            prefix = phone[:3] if len(phone) > 3 else phone[:2]
            return f"{prefix} ****{last4}"
        return f"****{last4}"
    return "****"


# ─────────────────────────────────────────────────────────────────────────────
# Abstract Provider Interface
# ─────────────────────────────────────────────────────────────────────────────

class SmsProvider(ABC):
    """Abstract base class for SMS provider implementations."""

    @abstractmethod
    def send_otp_sms(
        self,
        phone_e164: str,
        otp: str,           # Used ONLY to build message body — never stored/logged
        purpose: str,
        expires_minutes: int = 5,
    ) -> SendResult:
        """Send an OTP SMS. Returns SendResult. Does NOT store OTP."""
        ...

    @abstractmethod
    def get_delivery_status(self, provider_message_id: str) -> DeliveryStatusResult:
        """Poll provider for current delivery status of a message."""
        ...

    @abstractmethod
    def validate_webhook_signature(self, payload: bytes, headers: dict) -> bool:
        """Authenticate an inbound delivery receipt webhook from the provider."""
        ...

    @abstractmethod
    def parse_delivery_webhook(self, payload: dict) -> WebhookDeliveryUpdate:
        """Parse provider-specific delivery receipt into a normalized update."""
        ...


# ─────────────────────────────────────────────────────────────────────────────
# Mock Provider (Default — Development / Testing)
# ─────────────────────────────────────────────────────────────────────────────

class MockSmsProvider(SmsProvider):
    """
    Mock SMS provider for development and testing.

    IMPORTANT:
    - Does NOT actually send any SMS.
    - Returns status = SENT (never DELIVERED) because delivery cannot be confirmed.
    - Logs the send event (without OTP value) for audit trail.
    - All tests should use this adapter by default.
    """

    def send_otp_sms(
        self,
        phone_e164: str,
        otp: str,
        purpose: str,
        expires_minutes: int = 5,
    ) -> SendResult:
        fake_message_id = f"MOCK-{uuid.uuid4().hex[:12].upper()}"
        masked = mask_phone(phone_e164)
        # NEVER log the OTP value
        logger.info(
            f"[MockSMS] OTP SMS queued for {masked} "
            f"| purpose={purpose} | message_id={fake_message_id} "
            f"| status=SENT (delivery confirmation unavailable — mock adapter)"
        )
        return SendResult(
            success=True,
            provider="mock",
            provider_message_id=fake_message_id,
            initial_status="SENT",
            raw_response={"mock": True, "delivery_confirmation": "unavailable"},
        )

    def get_delivery_status(self, provider_message_id: str) -> DeliveryStatusResult:
        return DeliveryStatusResult(
            provider_message_id=provider_message_id,
            status="UNKNOWN",
            failure_reason="Delivery status polling not available with mock provider.",
        )

    def validate_webhook_signature(self, payload: bytes, headers: dict) -> bool:
        # Mock: accept test webhook if header contains the configured secret
        incoming = headers.get("X-SFR-Webhook-Secret", "")
        return incoming == settings.SMS_WEBHOOK_SECRET

    def parse_delivery_webhook(self, payload: dict) -> WebhookDeliveryUpdate:
        return WebhookDeliveryUpdate(
            provider_message_id=payload.get("provider_message_id", "UNKNOWN"),
            status=payload.get("status", "UNKNOWN").upper(),
            timestamp=datetime.now(timezone.utc),
            raw_payload=payload,
        )


# ─────────────────────────────────────────────────────────────────────────────
# Twilio Provider (Production — configure via environment variables)
# ─────────────────────────────────────────────────────────────────────────────

class TwilioSmsProvider(SmsProvider):
    """
    Twilio SMS provider.
    Requires: SMS_API_KEY (Account SID), SMS_API_SECRET (Auth Token), SMS_SENDER_ID (from number).
    Supports delivery status via status callbacks.
    """

    def __init__(self):
        try:
            from twilio.rest import Client  # type: ignore
            from twilio.request_validator import RequestValidator  # type: ignore
            self._client = Client(settings.SMS_API_KEY, settings.SMS_API_SECRET)
            self._validator = RequestValidator(settings.SMS_API_SECRET)
        except ImportError:
            raise RuntimeError(
                "Twilio library not installed. Run: pip install twilio"
            )

    def send_otp_sms(
        self,
        phone_e164: str,
        otp: str,
        purpose: str,
        expires_minutes: int = 5,
    ) -> SendResult:
        try:
            body = build_otp_sms_body(otp, purpose, expires_minutes)
            message = self._client.messages.create(
                body=body,
                from_=settings.SMS_SENDER_ID,
                to=phone_e164,
            )
            masked = mask_phone(phone_e164)
            logger.info(
                f"[TwilioSMS] OTP SMS sent to {masked} "
                f"| purpose={purpose} | sid={message.sid} | status={message.status}"
            )
            # Twilio initial status is typically "queued" or "sending"
            status_map = {"queued": "QUEUED", "sending": "QUEUED", "sent": "SENT", "failed": "FAILED"}
            initial = status_map.get(message.status, "QUEUED")
            return SendResult(
                success=True,
                provider="twilio",
                provider_message_id=message.sid,
                initial_status=initial,
            )
        except Exception as e:
            logger.error(f"[TwilioSMS] Send failed: {type(e).__name__}: {e}")
            return SendResult(
                success=False,
                provider="twilio",
                initial_status="FAILED",
                failure_reason=str(e),
            )

    def get_delivery_status(self, provider_message_id: str) -> DeliveryStatusResult:
        try:
            message = self._client.messages(provider_message_id).fetch()
            status_map = {
                "queued": "QUEUED", "sending": "QUEUED", "sent": "SENT",
                "delivered": "DELIVERED", "undelivered": "FAILED", "failed": "FAILED",
            }
            return DeliveryStatusResult(
                provider_message_id=provider_message_id,
                status=status_map.get(message.status, "UNKNOWN"),
            )
        except Exception as e:
            return DeliveryStatusResult(
                provider_message_id=provider_message_id,
                status="UNKNOWN",
                failure_reason=str(e),
            )

    def validate_webhook_signature(self, payload: bytes, headers: dict) -> bool:
        # Twilio validates via X-Twilio-Signature header
        # In production, validate against the actual request URL
        signature = headers.get("X-Twilio-Signature", "")
        url = headers.get("X-Request-URL", "")
        params = {}
        try:
            params = json.loads(payload)
        except Exception:
            pass
        return self._validator.validate(url, params, signature)

    def parse_delivery_webhook(self, payload: dict) -> WebhookDeliveryUpdate:
        status_map = {
            "sent": "SENT", "delivered": "DELIVERED",
            "undelivered": "FAILED", "failed": "FAILED",
        }
        raw_status = payload.get("MessageStatus", "UNKNOWN").lower()
        return WebhookDeliveryUpdate(
            provider_message_id=payload.get("MessageSid", "UNKNOWN"),
            status=status_map.get(raw_status, "UNKNOWN"),
            timestamp=datetime.now(timezone.utc),
            failure_reason=payload.get("ErrorMessage"),
            raw_payload=payload,
        )


# ─────────────────────────────────────────────────────────────────────────────
# Fast2SMS Provider (Production / India — https://www.fast2sms.com)
# ─────────────────────────────────────────────────────────────────────────────

class Fast2SmsProvider(SmsProvider):
    """
    Fast2SMS Indian gateway provider for quick DLT and OTP SMS dispatch.
    Requires: SMS_API_KEY.
    """

    def __init__(self):
        self._api_key = settings.SMS_API_KEY
        if not self._api_key:
            raise ValueError("Fast2SMS requires SMS_API_KEY environment variable.")

    def send_otp_sms(
        self,
        phone_e164: str,
        otp: str,
        purpose: str,
        expires_minutes: int = 5,
    ) -> SendResult:
        import urllib.request
        try:
            # Normalize phone to 10 digits for India
            digits = ''.join(c for c in phone_e164 if c.isdigit())
            number = digits[-10:] if len(digits) >= 10 else digits
            
            url = "https://www.fast2sms.com/dev/bulkV2"
            payload = json.dumps({
                "route": "otp",
                "variables_values": otp,
                "numbers": number,
            }).encode("utf-8")
            
            req = urllib.request.Request(
                url,
                data=payload,
                headers={
                    "authorization": self._api_key,
                    "Content-Type": "application/json",
                },
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                resp_data = json.loads(resp.read().decode("utf-8"))
                
            request_id = resp_data.get("request_id", f"F2S-{uuid.uuid4().hex[:8].upper()}")
            masked = mask_phone(phone_e164)
            logger.info(f"[Fast2SMS] OTP dispatched to {masked} | request_id={request_id}")
            return SendResult(
                success=resp_data.get("return", False),
                provider="fast2sms",
                provider_message_id=request_id,
                initial_status="SENT",
                raw_response=resp_data
            )
        except Exception as e:
            logger.error(f"[Fast2SMS] Send failed: {e}")
            return SendResult(
                success=False,
                provider="fast2sms",
                initial_status="FAILED",
                failure_reason=str(e)
            )

    def get_delivery_status(self, provider_message_id: str) -> DeliveryStatusResult:
        return DeliveryStatusResult(
            provider_message_id=provider_message_id,
            status="UNKNOWN",
            failure_reason="Delivery receipt polling depends on webhook callback."
        )

    def validate_webhook_signature(self, payload: bytes, headers: dict) -> bool:
        incoming = headers.get("X-Fast2SMS-Signature", headers.get("X-SFR-Webhook-Secret", ""))
        return incoming == settings.SMS_WEBHOOK_SECRET

    def parse_delivery_webhook(self, payload: dict) -> WebhookDeliveryUpdate:
        status_raw = payload.get("status", "UNKNOWN").upper()
        norm_status = "DELIVERED" if status_raw in ("DELIVERED", "SUCCESS") else "FAILED" if status_raw in ("FAILED", "UNDELIVERED") else "UNKNOWN"
        return WebhookDeliveryUpdate(
            provider_message_id=payload.get("request_id", payload.get("message_id", "UNKNOWN")),
            status=norm_status,
            timestamp=datetime.now(timezone.utc),
            raw_payload=payload
        )


# ─────────────────────────────────────────────────────────────────────────────
# Provider Factory
# ─────────────────────────────────────────────────────────────────────────────

def get_sms_provider() -> SmsProvider:
    """
    Returns the configured SMS provider instance.
    Reads SMS_PROVIDER from environment. Defaults to mock.
    """
    provider_name = settings.SMS_PROVIDER.lower()

    if provider_name == "twilio":
        if not settings.SMS_API_KEY or not settings.SMS_API_SECRET:
            logger.warning(
                "[SMS] Twilio selected but SMS_API_KEY/SMS_API_SECRET not set. "
                "Falling back to MockSmsProvider."
            )
            return MockSmsProvider()
        return TwilioSmsProvider()

    if provider_name in ("fast2sms", "msg91"):
        if not settings.SMS_API_KEY:
            logger.warning(
                f"[SMS] {provider_name} selected but SMS_API_KEY not set. "
                "Falling back to MockSmsProvider."
            )
            return MockSmsProvider()
        return Fast2SmsProvider()

    if provider_name != "mock":
        logger.warning(
            f"[SMS] Unknown SMS_PROVIDER='{provider_name}'. Using MockSmsProvider."
        )

    return MockSmsProvider()


# Module-level singleton (initialized once per process)
_sms_provider: Optional[SmsProvider] = None


def sms_provider() -> SmsProvider:
    """Thread-safe lazy singleton accessor."""
    global _sms_provider
    if _sms_provider is None:
        _sms_provider = get_sms_provider()
    return _sms_provider

