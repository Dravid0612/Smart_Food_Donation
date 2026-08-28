import os
import json
import secrets
from datetime import datetime, timedelta, timezone
from app.db.session import SessionLocal, engine
from app.db.base import Base
from app.models.models import (
    User, NGO, FoodDonation, DonationHistory, Reward, Notification, VolunteerAssignment,
    RecurringDonation, Rating
)
from app.core.security import hash_password

def seed_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)

        # 1. Admin
        admin = User(
            name="Platform Admin",
            email="admin@fooddonation.org",
            password_hash=hash_password("admin123"),
            phone="+919876543210",
            role="admin",
            address="Central Admin HQ, Bangalore",
            latitude=12.9716,
            longitude=77.5946
        )
        db.add(admin)

        # 2. Donors
        donors_data = [
            ("Taj Hotel Restaurant", "donor1@hotel.com", "pass123", "+919811111111", "MG Road, Bangalore", 12.9750, 77.6080),
            ("Dravid Community Kitchen", "donor2@kitchen.com", "pass123", "+919822222222", "Indiranagar, Bangalore", 12.9784, 77.6408),
            ("Fresh Bakery Mart", "donor3@bakery.com", "pass123", "+919833333333", "Koramangala, Bangalore", 12.9352, 77.6245),
        ]
        donors = []
        for name, email, pwd, phone, addr, lat, lon in donors_data:
            d = User(
                name=name,
                email=email,
                password_hash=hash_password(pwd),
                phone=phone,
                role="donor",
                address=addr,
                latitude=lat,
                longitude=lon
            )
            db.add(d)
            db.flush()
            donors.append(d)

            r = Reward(user_id=d.id, points=20 if d.email == "donor1@hotel.com" else 0, level="Bronze")
            db.add(r)

        # 3. NGOs with Operating Hours & Dynamic Beneficiary Demands
        default_hours = json.dumps({
            "monday": {"open": "08:00", "close": "20:00", "closed": False},
            "tuesday": {"open": "08:00", "close": "20:00", "closed": False},
            "wednesday": {"open": "08:00", "close": "20:00", "closed": False},
            "thursday": {"open": "08:00", "close": "20:00", "closed": False},
            "friday": {"open": "08:00", "close": "20:00", "closed": False},
            "saturday": {"open": "08:00", "close": "18:00", "closed": False},
            "sunday": {"open": "09:00", "close": "14:00", "closed": False}
        })

        ngo1_demands = json.dumps({"Cooked Food": 80, "Bakery": 30, "Fruits": 25})
        ngo2_demands = json.dumps({"Cooked Food": 50, "Packaged Food": 60, "Vegetables": 40})
        ngo3_demands = json.dumps({"Bakery": 20, "Fruits": 50, "Packaged Food": 30})

        ngos_data = [
            ("Green Hope Foundation", "ngo1@greenhope.org", "pass123", "+919844444444", "Koramangala 4th Block", 12.9340, 77.6210, 200, True, default_hours, ngo1_demands),
            ("Feed India Trust", "ngo2@feedindia.org", "pass123", "+919855555555", "Indiranagar 100ft Rd", 12.9710, 77.6410, 150, True, default_hours, ngo2_demands),
            ("Share A Meal NGO", "ngo3@shareameal.org", "pass123", "+919866666666", "Whitefield Main Rd", 12.9690, 77.7490, 100, False, default_hours, ngo3_demands),
        ]
        ngos = []
        for org_name, email, pwd, phone, addr, lat, lon, cap, is_ver, hours, demands in ngos_data:
            u = User(
                name=org_name,
                email=email,
                password_hash=hash_password(pwd),
                phone=phone,
                role="ngo",
                address=addr,
                latitude=lat,
                longitude=lon
            )
            db.add(u)
            db.flush()

            ngo_profile = NGO(
                user_id=u.id,
                organization_name=org_name,
                description="Dedicated to eradicating hunger through surplus food distribution.",
                address=addr,
                latitude=lat,
                longitude=lon,
                capacity=cap,
                current_capacity=cap,
                is_available=True,
                is_verified=is_ver,
                contact_phone=phone,
                operating_hours=hours,
                demand_requirements=demands
            )
            db.add(ngo_profile)
            db.flush()
            ngos.append(ngo_profile)

        # 4. Volunteers with Vehicle Type & Carrying Capacity
        volunteers_data = [
            ("Rahul Sharma", "vol1@volunteer.org", "pass123", "+919877777777", "Koramangala", 12.9360, 77.6230, "bike", 50, 96.0, 12, 1),
            ("Priya Patel", "vol2@volunteer.org", "pass123", "+919888888888", "Indiranagar", 12.9770, 77.6420, "car", 150, 98.0, 24, 0),
            ("Amit Kumar", "vol3@volunteer.org", "pass123", "+919899999999", "MG Road", 12.9740, 77.6090, "van", 500, 94.0, 31, 2),
        ]
        volunteers = []
        for name, email, pwd, phone, addr, lat, lon, vtype, cap, rel, comp, fail in volunteers_data:
            v = User(
                name=name,
                email=email,
                password_hash=hash_password(pwd),
                phone=phone,
                role="volunteer",
                address=addr,
                latitude=lat,
                longitude=lon,
                vehicle_type=vtype,
                carrying_capacity=cap,
                reliability_score=rel,
                completed_deliveries=comp,
                failed_deliveries=fail
            )
            db.add(v)
            db.flush()
            volunteers.append(v)

        # 5. Realistic Donations with AI condition assessment and verification codes
        donations_data = [
            ("Vegetable Rice & Curry", "Cooked Food", 50.0, "Meals", 1, "pending", None, None, 2, 8, "Room Temperature", "Sealed / Covered", "Rice + Curry", "Not detected", "Normal", "Intact", "GOOD", 0.92, 88),
            ("Fresh Idli & Sambar", "Cooked Food", 30.0, "Meals", 0.5, "accepted", ngos[0].id, None, 1, 4, "Heated/Insulated", "Sealed / Covered", "Cooked Meals (Dal & Rice)", "Not detected", "Normal", "Intact", "GOOD", 0.94, 92),
            ("Assorted Bakery Bread", "Bakery", 40.0, "Packets", 2, "pending", None, None, 3, 12, "Room Temperature", "Sealed / Covered", "Assorted Breads & Buns", "Not detected", "Normal", "Intact", "GOOD", 0.90, 86),
            ("Fresh Seasonal Fruits", "Fruits", 25.0, "Kg", 4, "pending", None, None, 4, 48, "Room Temperature", "Open Container", "Fresh Fruit Medley", "Not detected", "Normal", "Exposed", "GOOD", 0.88, 82),
            ("Packed Lunch Boxes", "Packaged Food", 60.0, "Packets", 1, "completed", ngos[1].id, volunteers[1].id, 1, 6, "Room Temperature", "Sealed / Covered", "Packaged Food Box", "Not detected", "Normal", "Intact", "GOOD", 0.95, 94),
            ("Chicken & Veg Biryani", "Cooked Food", 45.0, "Meals", 1.5, "volunteer_assigned", ngos[0].id, volunteers[0].id, 2, 5, "Heated/Insulated", "Sealed / Covered", "Biryani & Gravy", "Not detected", "Normal", "Intact", "GOOD", 0.91, 90),
            ("Mixed Veggies Basket", "Vegetables", 35.0, "Kg", 3, "pending", None, None, 5, 36, "Room Temperature", "Open Container", "Mixed Fresh Vegetables", "Not detected", "Normal", "Exposed", "GOOD", 0.85, 80),
            ("South Indian Meals", "Cooked Food", 50.0, "Meals", 1, "collected", ngos[1].id, volunteers[1].id, 1, 4, "Room Temperature", "Sealed / Covered", "Rice + Curry", "Not detected", "Normal", "Intact", "GOOD", 0.89, 87),
            ("Fruit Juice Cartons", "Packaged Food", 80.0, "Packets", 6, "pending", None, None, 2, 72, "Room Temperature", "Sealed / Covered", "Assorted Tetra Paks", "Not detected", "Normal", "Intact", "GOOD", 0.96, 95),
            ("Paneer Butter Masala & Roti", "Cooked Food", 40.0, "Meals", 0.8, "accepted", ngos[0].id, None, 0.5, 3, "Heated/Insulated", "Sealed / Covered", "Cooked Meals (Dal & Rice)", "Not detected", "Normal", "Intact", "GOOD", 0.93, 91),
        ]

        for fname, cat, qty, unit, prep_ago_h, status, ngo_id, vol_id, donor_idx, exp_in_h, storage, pkg, det_food, spoil, disc, pkg_int, vcond, conf, cscore in donations_data:
            donor = donors[(int(donor_idx) - 1) % len(donors)]
            prep_time = now - timedelta(hours=prep_ago_h)
            expiry_time = now + timedelta(hours=exp_in_h)
            otp = f"{secrets.randbelow(900000) + 100000}"
            qr_token = f"DON-{secrets.token_urlsafe(12)}"

            don = FoodDonation(
                donor_id=donor.id,
                food_name=fname,
                description=f"Freshly prepared {fname.lower()} available for immediate distribution to those in need.",
                food_category=cat,
                quantity=qty,
                quantity_unit=unit,
                preparation_time=prep_time,
                expiry_time=expiry_time,
                pickup_address=donor.address,
                latitude=donor.latitude,
                longitude=donor.longitude,
                image_url=f"https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=400",
                storage_method=storage,
                storage_duration_hours=float(prep_ago_h),
                packaging_condition=pkg,
                pickup_deadline=expiry_time,
                ai_food_detected=det_food,
                ai_visible_spoilage=spoil,
                ai_discoloration=disc,
                ai_packaging_intact=pkg_int,
                ai_visual_condition=vcond,
                ai_confidence_score=conf,
                condition_score=cscore,
                verification_otp=otp,
                qr_code_token=qr_token,
                status=status,
                assigned_ngo_id=ngo_id,
                assigned_volunteer_id=vol_id
            )
            db.add(don)
            db.flush()

            # Status history
            dh = DonationHistory(
                donation_id=don.id,
                old_status=None,
                new_status=status,
                changed_by=donor.id,
                remarks="Initial donation record seeded with AI condition score"
            )
            db.add(dh)

            if vol_id:
                va = VolunteerAssignment(
                    donation_id=don.id,
                    volunteer_id=vol_id,
                    assigned_at=now - timedelta(minutes=30),
                    status="collected" if status == "collected" else "delivered" if status == "completed" else "assigned"
                )
                db.add(va)

        # 6. Seed Recurring Donations for Hotel Partner
        rec1 = RecurringDonation(
            donor_id=donors[0].id,
            template_name="Taj Daily Dinner Buffet Leftover",
            food_name="Assorted Luxury Buffet Meals",
            food_category="Cooked Food",
            typical_quantity=75.0,
            quantity_unit="Meals",
            frequency="Daily",
            preferred_pickup_time="21:30",
            pickup_address=donors[0].address,
            storage_method="Heated/Insulated",
            packaging_condition="Sealed / Covered",
            is_active=True
        )
        rec2 = RecurringDonation(
            donor_id=donors[0].id,
            template_name="Taj Lunch Service Surplus",
            food_name="Curry, Rice & Bread Packets",
            food_category="Cooked Food",
            typical_quantity=40.0,
            quantity_unit="Meals",
            frequency="Daily",
            preferred_pickup_time="15:00",
            pickup_address=donors[0].address,
            storage_method="Heated/Insulated",
            packaging_condition="Sealed / Covered",
            is_active=True
        )
        db.add(rec1)
        db.add(rec2)

        # 7. Seed Initial Two-Way Ratings
        rating1 = Rating(
            donation_id=5, # completed donation
            from_user_id=donors[0].id,
            to_user_id=ngos[1].user_id,
            role_from="donor",
            role_to="ngo",
            rating_score=5,
            feedback="Feed India Trust received our lunch boxes promptly with verified temperature check.",
            tags="On-time, Professional, Dignified"
        )
        rating2 = Rating(
            donation_id=5,
            from_user_id=ngos[1].user_id,
            to_user_id=volunteers[1].id,
            role_from="ngo",
            role_to="volunteer",
            rating_score=5,
            feedback="Priya delivered 60 meal boxes in clean insulated container.",
            tags="Safe Transport, Great Communication"
        )
        db.add(rating1)
        db.add(rating2)

        db.commit()
        print("Database successfully seeded with Operating Hours, Demands, Volunteer Capacities, AI Assessments, Verification Codes, Recurring Templates, and Two-Way Ratings!")

    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()

