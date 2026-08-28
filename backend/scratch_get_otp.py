import sqlite3

conn = sqlite3.connect('smart_food.db')
cur = conn.cursor()
rows = cur.execute('SELECT id, food_name, status, verification_otp FROM food_donations WHERE assigned_volunteer_id IS NOT NULL ORDER BY id DESC LIMIT 5').fetchall()
for r in rows:
    print(r)
