import sqlite3

conn = sqlite3.connect('smart_food.db')
cur = conn.cursor()
rows = cur.execute("SELECT id, food_name, status, verification_otp, assigned_volunteer_id FROM food_donations WHERE food_name LIKE '%Guard%'").fetchall()
for r in rows:
    print(r)
