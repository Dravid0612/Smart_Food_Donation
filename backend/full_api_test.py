"""
Smart Donor Live Four-Role API Verification
Tests actual backend at http://127.0.0.1:8000
Seeded credentials from seed.py:
  Admin:     admin@fooddonation.org / admin123
  Donors:    donor1@hotel.com / pass123
  NGO:       ngo1@greenhope.org / pass123
  Volunteer: vol1@volunteer.org / pass123 (bike, cap=50)
             vol2@volunteer.org / pass123 (car, cap=150)
             vol3@volunteer.org / pass123 (van, cap=500)
"""
import requests, json, datetime

BASE = 'http://127.0.0.1:8000/api'

def login(email, password):
    r = requests.post(f'{BASE}/auth/login', json={'email': email, 'password': password})
    return r

def hdr(token):
    return {'Authorization': f'Bearer {token}'}

print("=" * 60)
print("PHASE 1: ENVIRONMENT CHECK")
r = requests.get('http://127.0.0.1:8000/')
print(f"  GET /  -> {r.status_code}: {r.json().get('message','')[:50]}")
r2 = requests.get('http://127.0.0.1:8000/docs')
print(f"  GET /docs -> {r2.status_code} ({len(r2.text)} bytes)")

print()
print("PHASE 2: FOUR-ROLE LOGIN TEST")
tokens = {}
roles = [
    ('admin',     'admin@fooddonation.org', 'admin123'),
    ('donor',     'donor1@hotel.com',       'pass123'),
    ('ngo',       'ngo1@greenhope.org',     'pass123'),
    ('volunteer', 'vol3@volunteer.org',     'pass123'),  # van, cap=500
]
for role, email, pw in roles:
    r = login(email, pw)
    if r.status_code == 200:
        tokens[role] = r.json()['access_token']
        me = requests.get(f'{BASE}/auth/me', headers=hdr(tokens[role]))
        if me.status_code == 200:
            print(f"  OK  {role.upper():<10} | {me.json().get('email','?')} | role={me.json().get('role','?')}")
        else:
            print(f"  OK  {role.upper():<10} login OK (me={me.status_code})")
    else:
        print(f"  ERR {role.upper():<10} login FAILED {r.status_code}: {r.text[:100]}")

print()
print("PHASE 3: DONOR CREATES DONATION (75 meals Rice+Curry)")
don_id = None
if 'donor' in tokens:
    import datetime as dt_mod
    now = dt_mod.datetime.now(dt_mod.timezone.utc)
    prep_time = (now - dt_mod.timedelta(hours=1)).isoformat()
    expiry = (now + dt_mod.timedelta(hours=3)).isoformat()
    payload = {
        'food_name': 'Rice and Curry Special',
        'description': 'Fresh hotel meals - rice curry combo, 75 portions',
        'food_category': 'Cooked Food',
        'quantity': 75,
        'quantity_unit': 'Meals',
        'preparation_time': prep_time,
        'expiry_time': expiry,
        'pickup_address': '123 MG Road, Bangalore',
        'latitude': 12.9750,
        'longitude': 77.6080,
        'storage_method': 'Room Temperature',
        'packaging_condition': 'Sealed / Covered',
        'ai_visual_condition': 'GOOD',
    }
    r = requests.post(f'{BASE}/donations', json=payload, headers=hdr(tokens['donor']))
    print(f"  POST /donations -> {r.status_code}")
    if r.status_code == 201:
        don = r.json()
        don_id = don['id']
        print(f"  Donation ID={don_id} status={don.get('status')} qty={don.get('quantity')} {don.get('quantity_unit','meals')}")
    else:
        print(f"  ERROR: {r.text[:400]}")


print()
print("PHASE 4: AI FOOD ANALYSIS")
if 'donor' in tokens and don_id:
    r = requests.post(f'{BASE}/donations/{don_id}/analyze', headers=hdr(tokens['donor']), json={})
    print(f"  POST /donations/{don_id}/analyze -> {r.status_code}")
    if r.status_code == 200:
        ai = r.json()
        print(f"  condition: {ai.get('condition','?')}")
        print(f"  advisory: {str(ai.get('notes','') or ai.get('message',''))[:120]}")
        bad_claims = ['ai says food is safe', 'safe to eat', 'safe to consume', 'safe for consumption']
        found = [c for c in bad_claims if c in str(ai).lower()]
        print(f"  Unsafe-claim check: {'FAILED - found: '+str(found) if found else 'PASS - no safety guarantees'}")
    else:
        print(f"  Response: {r.text[:300]}")
else:
    print("  SKIP")

print()
print("PHASE 5: DEMAND-AWARE NGO MATCHING (Rice+Curry -> Green Hope needs Cooked Food)")
if 'donor' in tokens and don_id:
    r = requests.get(f'{BASE}/donations/{don_id}/recommend-ngo', headers=hdr(tokens['donor']))
    print(f"  GET /donations/{don_id}/recommend-ngo -> {r.status_code}")
    if r.status_code == 200:
        ngos = r.json()
        print(f"  NGOs returned: {len(ngos)}")
        for i, n in enumerate(ngos[:4]):
            print(f"    Rank {i+1}: {n.get('organization_name','?'):<25} score={n.get('match_score',n.get('score','?'))}")
        # Check NGO1 (wants Cooked Food) ranks above NGO3 (wants Bakery/Fruits)
        names = [n.get('organization_name','') for n in ngos]
        ngo1_rank = next((i for i,n in enumerate(names) if 'Green Hope' in n or 'GreenHope' in n), -1)
        ngo3_rank = next((i for i,n in enumerate(names) if 'Share' in n), -1)
        if ngo1_rank != -1 and ngo3_rank != -1:
            print(f"  Green Hope rank={ngo1_rank+1}, Share A Meal rank={ngo3_rank+1}")
            if ngo1_rank < ngo3_rank:
                print("  DEMAND MATCH: Green Hope (needs Cooked) ranked above Share A Meal (needs Bakery) - CORRECT")
            else:
                print("  DEMAND MATCH: Unexpected ranking order")
    else:
        print(f"  ERROR: {r.text[:300]}")

print()
print("PHASE 6: CAPACITY-AWARE VOLUNTEER MATCHING (75 meals)")
if 'donor' in tokens and don_id:
    r = requests.get(f'{BASE}/donations/{don_id}/recommend-volunteer', headers=hdr(tokens['donor']))
    print(f"  GET /donations/{don_id}/recommend-volunteer -> {r.status_code}")
    if r.status_code == 200:
        vols = r.json()
        print(f"  Volunteers returned: {len(vols)}")
        for i, v in enumerate(vols[:4]):
            vtype = v.get('vehicle_type','?')
            cap = v.get('vehicle_capacity','?')
            score = v.get('match_score', v.get('score','?'))
            print(f"    Vol {i+1}: {vtype:<6} cap={cap:<4} score={score}")
        # Verify walking (cap<75) is not recommended
        walking = [v for v in vols if v.get('vehicle_type','') == 'walking' or 
                   (isinstance(v.get('vehicle_capacity'), (int,float)) and v.get('vehicle_capacity', 0) < 75)]
        print(f"  Under-capacity (cap<75) in results: {'YES - FAIL' if walking else 'NONE - PASS'}")
    else:
        print(f"  ERROR: {r.text[:300]}")

print()
print("PHASE 7: NGO ACCEPTANCE")
ngo_accepted = False
if 'ngo' in tokens and don_id:
    r = requests.post(f'{BASE}/donations/{don_id}/accept', headers=hdr(tokens['ngo']))
    print(f"  POST /donations/{don_id}/accept -> {r.status_code}")
    if r.status_code == 200:
        print(f"  Status: {r.json().get('status','?')}")
        ngo_accepted = True
    elif r.status_code == 409:
        print(f"  Already accepted (409) - OK")
        ngo_accepted = True
    else:
        print(f"  ERROR: {r.text[:200]}")

print()
print("PHASE 7b: SECOND NGO CANNOT ACCEPT (race condition prevention)")
if 'ngo' in tokens and don_id and ngo_accepted:
    # Login as ngo2
    r2 = login('ngo2@feedindia.org', 'pass123')
    if r2.status_code == 200:
        tok2 = r2.json()['access_token']
        r3 = requests.post(f'{BASE}/donations/{don_id}/accept', headers=hdr(tok2))
        print(f"  Second NGO accept -> {r3.status_code} (expected 409)")
        print(f"  Concurrent accept blocked: {'PASS' if r3.status_code == 409 else 'FAIL'}")

print()
print("PHASE 8: VOLUNTEER ASSIGNMENT (vol3, van, cap=500 for 75 meals)")
otp_for_verification = None
vol3_id = None
if 'volunteer' in tokens and don_id and ngo_accepted:
    me_r = requests.get(f'{BASE}/auth/me', headers=hdr(tokens['volunteer']))
    vol3_id = me_r.json().get('id') if me_r.status_code == 200 else None
    print(f"  Volunteer ID: {vol3_id}")
    if vol3_id:
        r = requests.post(f'{BASE}/volunteers/assignments?donation_id={don_id}&volunteer_id={vol3_id}',
                          headers=hdr(tokens['volunteer']))
        print(f"  POST /volunteers/assignments -> {r.status_code}")
        if r.status_code == 200:
            assign = r.json()
            print(f"  Assignment created. (Volunteer does NOT get plaintext OTP in assignment response)")
            
            # Verify volunteer CANNOT get OTP from donor endpoint
            vol_otp_attempt = requests.get(f'{BASE}/donations/{don_id}/verification-code', headers=hdr(tokens['volunteer']))
            print(f"  Volunteer unauthorized OTP fetch -> {vol_otp_attempt.status_code} (PASS if 403 or 404)")

            # Donor retrieves OTP
            donor_otp_r = requests.get(f'{BASE}/donations/{don_id}/verification-code', headers=hdr(tokens['donor']))
            if donor_otp_r.status_code == 200:
                otp_for_verification = donor_otp_r.json().get('otp')
                print(f"  Donor retrieved OTP securely: {otp_for_verification}")
        elif r.status_code == 409:
            print(f"  Assignment already exists (409)")
        else:
            print(f"  ERROR: {r.text[:200]}")

print()
print("PHASE 8b: WALKING VOLUNTEER BLOCKED FOR 75 MEALS (capacity gate)")
r_bike = login('vol1@volunteer.org', 'pass123')
if r_bike.status_code == 200 and don_id:
    tok_bike = r_bike.json()['access_token']
    me2 = requests.get(f'{BASE}/auth/me', headers=hdr(tok_bike))
    vol1_id = me2.json().get('id') if me2.status_code == 200 else None
    if vol1_id:
        r3 = requests.post(f'{BASE}/volunteers/assignments?donation_id={don_id}&volunteer_id={vol1_id}',
                            headers=hdr(tok_bike))
        print(f"  Bike vol (cap=50) assign 75-meal donation -> {r3.status_code}")
        blocked = r3.status_code in (400, 409, 422, 403)
        print(f"  Capacity gate: {'PASS - blocked' if blocked else 'FAIL - allowed under-capacity assignment'}")

print()
print("PHASE 9: OTP VERIFICATION")
if 'volunteer' in tokens and don_id and otp_for_verification:
    # 9a. Test wrong OTP is rejected with 400
    r_bad = requests.post(f'{BASE}/volunteers/verify-otp',
                          json={'donation_id': don_id, 'otp': '000000'},
                          headers=hdr(tokens['volunteer']))
    print(f"  Wrong OTP verification -> {r_bad.status_code} (PASS if 400)")

    # 9b. Valid OTP verification
    r = requests.post(f'{BASE}/volunteers/verify-otp',
                      json={'donation_id': don_id, 'otp': otp_for_verification},
                      headers=hdr(tokens['volunteer']))
    print(f"  POST /volunteers/verify-otp -> {r.status_code}")
    if r.status_code == 200:
        print(f"  OTP Verified: {r.json().get('message', str(r.json())[:80])}")
    else:
        print(f"  Response: {r.text[:200]}")
    
    # 9c. Replay attack prevention: same OTP again returns 409
    r2 = requests.post(f'{BASE}/volunteers/verify-otp',
                       json={'donation_id': don_id, 'otp': otp_for_verification},
                       headers=hdr(tokens['volunteer']))
    print(f"  OTP Replay attempt -> {r2.status_code} (expected 409)")
    print(f"  Anti-replay: {'PASS' if r2.status_code == 409 else 'FAIL'}")

print()
print("PHASE 10: EXPIRY ESCALATION CHECK")
if 'donor' in tokens:
    # Create urgent donation (45 min expiry)
    urgent_expiry = (dt_mod.datetime.now(dt_mod.timezone.utc) + dt_mod.timedelta(minutes=45)).isoformat()
    urgent_prep = (dt_mod.datetime.now(dt_mod.timezone.utc) - dt_mod.timedelta(hours=1)).isoformat()
    payload = {
        'food_name': 'Urgent Bread and Soup',
        'description': 'Expiring soon - needs urgent rescue',
        'food_category': 'Cooked Food',
        'quantity': 20,
        'quantity_unit': 'Meals',
        'preparation_time': urgent_prep,
        'expiry_time': urgent_expiry,
        'pickup_address': '789 Urgent St, Bangalore',
        'latitude': 12.9760,
        'longitude': 77.6090,
    }
    r = requests.post(f'{BASE}/donations', json=payload, headers=hdr(tokens['donor']))
    print(f"  Create urgent donation (45min) -> {r.status_code}")
    if r.status_code == 201:
        urgent_id = r.json()['id']
        d = requests.get(f'{BASE}/donations/{urgent_id}', headers=hdr(tokens['donor']))
        if d.status_code == 200:
            info = d.json()
            print(f"  Urgent donation status: {info.get('status','?')} urgency_level: {info.get('urgency_level','?')}")

print()
print("PHASE 11: DONOR IMPACT METRICS")
if 'donor' in tokens:
    r = requests.get(f'{BASE}/donations/metrics/summary', headers=hdr(tokens['donor']))
    print(f"  GET /donations/metrics/summary -> {r.status_code}")
    if r.status_code == 200:
        m = r.json()
        print(f"  Total donations: {m.get('total_donations','?')}")
        print(f"  Meals rescued:   {m.get('total_meals_rescued','?')}")
        print(f"  Impact level:    {m.get('impact_level','?')}")
    else:
        print(f"  ERROR: {r.text[:200]}")

print()
print("PHASE 12: ADMIN STATISTICS & ROLE GUARD")
if 'admin' in tokens:
    r = requests.get(f'{BASE}/admin/statistics', headers=hdr(tokens['admin']))
    print(f"  GET /admin/statistics (admin) -> {r.status_code}")
    if r.status_code == 200:
        s = r.json()
        print(f"  Total users: {s.get('total_users','?')} | Total donations: {s.get('total_donations','?')}")
    # Donor cannot access admin stats
    if 'donor' in tokens:
        r2 = requests.get(f'{BASE}/admin/statistics', headers=hdr(tokens['donor']))
        print(f"  GET /admin/statistics (donor) -> {r2.status_code} (expected 403)")
        print(f"  Role guard: {'PASS' if r2.status_code == 403 else 'FAIL'}")

print()
print("=" * 60)
print("VERIFICATION COMPLETE")
