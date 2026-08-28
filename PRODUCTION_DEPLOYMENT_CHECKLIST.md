# Production Deployment Checklist
## Smart Food Rescue Platform

Use this checklist before promoting the Smart Food Rescue platform from Staging/Demo to Live Commercial Production.

---

### 1. Infrastructure & Backend Readiness
- [x] **Health Check Endpoint:** `GET /health` returns `200 OK` with `{"status": "ok", "database": "ok"}`.
- [x] **Environment Separation:** `ENVIRONMENT=production` and `DEBUG=false` configured in backend `.env`.
- [x] **PostgreSQL Database:** Production connection string configured with connection pooling (`pool_size=10, max_overflow=20, pool_recycle=1800`).
- [x] **CORS Origins:** Restricted from wildcard `*` to specific production web/admin client origins.
- [x] **Structured Logging:** Request ID tracking enabled without sensitive payload (OTP/JWT/password) logging.
- [x] **FastAPI Automated Tests:** 227/227 backend tests passing.

---

### 2. External Services Integration
- [ ] **Live SMS Provider Provisioning:**
  - [ ] Provision active Twilio / Fast2SMS account credentials.
  - [ ] Set `SMS_PROVIDER=twilio` or `SMS_PROVIDER=fast2sms` in production `.env`.
  - [ ] Configure DLR Webhook URL `https://api.smartfoodrescue.org/api/webhooks/sms/delivery` with `SMS_WEBHOOK_SECRET`.
  - [ ] Test end-to-end SMS receipt on a physical test mobile device.
- [ ] **Firebase Cloud Messaging (FCM):**
  - [ ] Download production `google-services.json` and place in `mobile/android/app/`.
  - [ ] Configure `FCM_SERVER_KEY` and `FCM_PROJECT_ID` in backend `.env`.
  - [ ] Test push notification delivery when app is in Background and Killed states.

---

### 3. Mobile Client & Release Binaries
- [x] **Static Analysis:** `flutter analyze` completed with 0 errors, 0 warnings, 0 lints.
- [x] **Widget & Unit Tests:** 93/93 Flutter tests passing.
- [x] **Android Permissions:** Location, Notifications, Camera, and Internet properly declared in `AndroidManifest.xml`.
- [x] **Dynamic Base URL:** Configured with `String.fromEnvironment('API_BASE_URL')` pointing to HTTPS production endpoint.
- [x] **Release APK:** `build/app/outputs/flutter-apk/app-release.apk` (58.0 MB) successfully compiled.
- [x] **Release AAB:** `build/app/outputs/bundle/release/app-release.aab` (56.1 MB) successfully compiled.
- [ ] **Google Play Keystore Signing:** Configure `key.properties` and release keystore for production signing.

---

### 4. Security & Privacy Compliance
- [x] **OTP Security:** SHA-256 salted hashes, 5-minute strict TTL, replay attack prevention.
- [x] **Zero OTP Leakage:** Grepped all notifications, logs, and deep-link metadata — zero plaintext OTP leaks.
- [x] **RBAC Isolation:** 4-role domain segregation verified (Donor, NGO, Volunteer, Admin).
- [x] **Privacy Masking:** Recipient phone numbers masked (`+91 98*** **210`) in all user-facing views and audit logs.
- [x] **Irreversible Distribution Accounting:** `partially_distributed` to `completed` transition gated on zero remaining quantity.

---

### 5. Final Deployment Sign-Off
- **Platform Status:** `DEMO READY — EXTERNAL SERVICES STILL NEED VERIFICATION`
- **Remaining Step for Live Production:** Supply live SMS API credentials in `backend/.env`.
