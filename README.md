# Smart Food Waste Donation Platform

## Overview

This repository contains a working demo for a Smart Food Waste Donation Platform with:

- FastAPI backend
- SQLAlchemy models and CRUD APIs
- JWT authentication
- Flutter frontend with Material 3 UI

## Backend

Run the API:

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Frontend

Run the Flutter app:

```bash
cd mobile
flutter pub get
flutter run
```

## Notes

- Configure environment variables in backend/.env before running.
- The current implementation includes donor, NGO, admin flows, authentication, and donation CRUD.
- On first launch, create accounts from the app: make a donor to post food, an NGO to accept/complete it, and an admin to view dashboard totals.
- The Android app targets the default emulator API address (`10.0.2.2:8000`). Update `mobile/lib/app/core/api_service.dart` when using a physical device or another backend host.
- Image upload, recommendations, volunteer assignment, and analytics are not part of this demo.
