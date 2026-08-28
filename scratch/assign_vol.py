import sqlite3
import requests

conn = sqlite3.connect("backend/smart_food.db")
cur = conn.cursor()
cur.execute("UPDATE users SET vehicle_type = 'bike', carrying_capacity = 50 WHERE id = 8")
conn.commit()
conn.close()

r = requests.post("http://127.0.0.1:8000/api/auth/login", json={"email": "vol1@volunteer.org", "password": "pass123"})
token = r.json()["access_token"]
res = requests.post(
    "http://127.0.0.1:8000/api/volunteers/assignments?donation_id=107&volunteer_id=8",
    headers={"Authorization": f"Bearer {token}"}
)
print("Step 10 Result:", res.status_code, res.json())
