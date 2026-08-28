# Smart Food Rescue Platform
> **AI-Powered, Real-Time Surplus Food Recovery & Logistics System**

[![Backend Tests](https://img.shields.io/badge/Backend%20Pytest-227%20Passed-success)](file:///backend/tests)
[![Flutter Tests](https://img.shields.io/badge/Flutter%20Tests-93%20Passed-success)](file:///mobile/test)
[![Static Analysis](https://img.shields.io/badge/Flutter%20Analyze-0%20Issues-brightgreen)](file:///mobile)
[![Languages](https://img.shields.io/badge/Languages-English%20%7C%20Tamil%20%7C%20Hindi-blue)](file:///mobile/lib/core/localization)

---

## 1. System Architecture

The Smart Food Rescue Platform connects Food Donors, Partner NGOs/Shelters, Volunteer Couriers, and Platform Administrators in a hyper-localized logistics lifecycle:

```
[ Food Donor ] ──( 5-Point Safety Check + AI Image Assessment )──► [ Pending Rescue ]
                                                                             │
                                              ┌──────────────────────────────┘
                                              ▼
                                   [ Atomic NGO Acceptance ] (Row Lock / 409 Safe)
                                              │
                                              ▼
                                   [ Feasibility Volunteer Dispatch ]
                                              │
                    ┌─────────────────────────┴─────────────────────────┐
                    ▼                                                   ▼
            [ Volunteer En Route ]                            [ Dynamic Rematching ]
            (Live Telemetry RBAC)                            (ETA > Rescue Window)
                    │                                                   │
                    ▼                                                   ▼
           [ Arrival at Donor ]                               [ New Feasible Courier ]
                    │
                    ▼
         [ SHA-256 Salted OTP Handover ] (Plaintext revealed only to authenticated Donor)
                    │
                    ▼
          [ Delivery at Partner NGO ]
                    │
                    ▼
        [ Received vs. Distributed Accounting ] (Partially Distributed ➔ Completed)
                    │
                    ▼
        [ Two-Way Constructive Feedback ] (Sample-Size Protected Reliability)
```

---

## 2. Technology Stack

- **Backend:** FastAPI (Python 3.13.1), SQLAlchemy ORM, SQLite WAL (Dev/Demo) & PostgreSQL (Production), Pydantic v2, Alembic, Passlib/Bcrypt.
- **Mobile Client:** Flutter 3.47.0 (Dart 3.13.0), Material 3 Glassmorphic Design, Provider State Management, Dio HTTP client, Trilingual Localization (`en`, `ta`, `hi`).
- **Security & Integrity:** SHA-256 Salted Pickup OTPs, Replay Protection, E.164 Phone Normalization, Multi-Provider SMS Abstraction (Twilio / Fast2SMS / Msg91), FCM Push Integration, Role-Based Access Control.

---

## 3. Local Development Setup

### Backend Setup
```bash
# 1. Navigate to backend
cd backend

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env

# 4. Start local development server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Interactive API documentation will be available at: `http://localhost:8000/docs`  
Health check endpoint: `http://localhost:8000/health`

### Mobile Setup
```bash
# 1. Navigate to mobile directory
cd mobile

# 2. Fetch packages
flutter pub get

# 3. Run on connected device / emulator
flutter run
```

---

## 4. Environment Separation

The Flutter client supports build-time environment targets via `--dart-define`:

| Target Environment | Run / Build Command | Resolved API Base URL |
| :--- | :--- | :--- |
| **Development (Emulator)** | `flutter run --dart-define=ENVIRONMENT=development` | `http://10.0.2.2:8000/api` |
| **Development (Physical LAN)** | `flutter run --dart-define=API_BASE_URL=http://192.168.1.50:8000/api` | `http://192.168.1.50:8000/api` |
| **Staging / Demo** | `flutter run --dart-define=ENVIRONMENT=staging` | `https://staging-api.smartfoodrescue.org/api` |
| **Production** | `flutter build apk --release --dart-define=ENVIRONMENT=production` | `https://api.smartfoodrescue.org/api` |

---

## 5. Test Commands

Run the full automated test matrix locally:

```bash
# Backend Automated Tests (227 Tests)
cd backend
python -m pytest tests/ -v

# Mobile Unit & Widget Tests (93 Tests)
cd ../mobile
flutter test

# Mobile Static Analysis
flutter analyze
```

---

## 6. Production Release Builds

```bash
cd mobile

# Generate Production Android App Bundle (Google Play Store)
flutter build appbundle --release --dart-define=ENVIRONMENT=production

# Generate Production Release APK (Direct Device Installation)
flutter build apk --release --dart-define=ENVIRONMENT=production
```

Artifact outputs:
- **AAB:** `mobile/build/app/outputs/bundle/release/app-release.aab` (56.1 MB)
- **APK:** `mobile/build/app/outputs/flutter-apk/app-release.apk` (58.0 MB)

---

## 7. External Services Configuration

### SMS Provider Setup (backend/.env)
```env
# Choose provider: mock | twilio | fast2sms | msg91
SMS_PROVIDER=twilio
SMS_API_KEY=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
SMS_API_SECRET=your_auth_token
SMS_SENDER_ID=+1234567890
SMS_WEBHOOK_SECRET=your_configured_webhook_secret
```

### Push Notifications (FCM)
```env
FCM_SERVER_KEY=your_firebase_server_key
FCM_PROJECT_ID=smart-food-rescue
```

---

## 8. Known Limitations & Production Notes

1. **SMS Gateway:** Live carrier SMS dispatch requires active provider credentials (`Twilio` or `Fast2SMS`). In local test environments, the system defaults to the verified `MockSmsProvider` with full DLR state-machine emulation.
2. **AI Vision Model:** AI visual condition scoring uses an advisory heuristic model. Physical food inspection and human judgment at intake remain the primary standard of food safety.
3. **Database Migration:** For multi-instance production deployments, configure `DATABASE_URL` to a persistent PostgreSQL cluster.
