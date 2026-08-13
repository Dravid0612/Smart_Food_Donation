import os
from datetime import datetime, timedelta, timezone
from app.db.session import SessionLocal, engine
from app.db.base import Base
from app.models.models import User, NGO, FoodDonation, DonationHistory, Reward, Notification
from app.core.security import hash_password

def seed_database():
    # Re-create tables
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

            # Reward
            r = Reward(user_id=d.id, points=20 if d.email == "donor1@hotel.com" else 0, level="Bronze")
            db.add(r)

        # 3. NGOs
        ngos_data = [
            ("Green Hope Foundation", "ngo1@greenhope.org", "pass123", "+919844444444", "Koramangala 4th Block", 12.9340, 77.6210, 200, True),
            ("Feed India Trust", "ngo2@feedindia.org", "pass123", "+919855555555", "Indiranagar 100ft Rd", 12.9710, 77.6410, 150, True),
            ("Share A Meal NGO", "ngo3@shareameal.org", "pass123", "+919866666666", "Whitefield Main Rd", 12.9690, 77.7490, 100, False), # unverified for testing
        ]
        ngos = []
        for org_name, email, pwd, phone, addr, lat, lon, cap, is_ver in ngos_data:
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
                contact_phone=phone
            )
            db.add(ngo_profile)
            db.flush()
            ngos.append(ngo_profile)

        # 4. Volunteers
        volunteers_data = [
            ("Rahul Sharma", "vol1@volunteer.org", "pass123", "+919877777777", "Koramangala", 12.9360, 77.6230),
            ("Priya Patel", "vol2@volunteer.org", "pass123", "+919888888888", "Indiranagar", 12.9770, 77.6420),
            ("Amit Kumar", "vol3@volunteer.org", "pass123", "+919899999999", "MG Road", 12.9740, 77.6090),
        ]
        volunteers = []
        for name, email, pwd, phone, addr, lat, lon in volunteers_data:
            v = User(
                name=name,
                email=email,
                password_hash=hash_password(pwd),
                phone=phone,
                role="volunteer",
                address=addr,
                latitude=lat,
                longitude=lon
            )
            db.add(v)
            db.flush()
            volunteers.append(v)

        # 5. 10 Realistic Donations
        donations_data = [
            ("Vegetable Rice", "Cooked Food", 50.0, "Meals", 1, "pending", None, None, 2, 8),
            ("Fresh Idli & Sambar", "Cooked Food", 30.0, "Meals", 0.5, "accepted", ngos[0].id, None, 1, 4),
            ("Assorted Bakery Bread", "Bakery", 40.0, "Packets", 2, "pending", None, None, 3, 12),
            ("Fresh Seasonal Fruits", "Fruits", 25.0, "Kg", 4, "pending", None, None, 4, 48),
            ("Packed Lunch Boxes", "Packaged Food", 60.0, "Packets", 1, "completed", ngos[1].id, volunteers[1].id, 1, 6),
            ("Chicken & Veg Biryani", "Cooked Food", 45.0, "Meals", 1.5, "volunteer_assigned", ngos[0].id, volunteers[0].id, 2, 5),
            ("Mixed Veggies Basket", "Vegetables", 35.0, "Kg", 3, "pending", None, None, 5, 36),
            ("South Indian Meals", "Cooked Food", 50.0, "Meals", 1, "collected", ngos[1].id, volunteers[1].id, 1, 4),
            ("Fruit Juice Cartons", "Packaged Food", 80.0, "Packets", 6, "pending", None, None, 2, 72),
            ("Paneer Butter Masala & Roti", "Cooked Food", 40.0, "Meals", 0.8, "accepted", ngos[0].id, None, 0.5, 3),
        ]

        for fname, cat, qty, unit, prep_ago_h, status, ngo_id, vol_id, donor_idx, exp_in_h in donations_data:
            donor = donors[(int(donor_idx) - 1) % len(donors)]
            prep_time = now - timedelta(hours=prep_ago_h)
            expiry_time = now + timedelta(hours=exp_in_h)

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
                remarks="Initial donation record seeded"
            )
            db.add(dh)

        db.commit()
        print("Database successfully seeded with 1 Admin, 3 Donors, 3 NGOs, 3 Volunteers, and 10 Food Donations!")

    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
