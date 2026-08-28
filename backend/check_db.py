import sqlite3

for db in ['smart_food_donation.db', 'smart_food.db']:
    try:
        conn = sqlite3.connect(f'd:/Desktop/Hackathon/Mad-Project/Smart_Food_Donation/backend/{db}')
        c = conn.cursor()
        c.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [r[0] for r in c.fetchall()]
        print(f'{db} tables: {tables}')
        if 'users' in tables:
            c.execute("SELECT id, email, role, is_active FROM users LIMIT 15")
            for r in c.fetchall():
                print(f'  {r}')
        conn.close()
    except Exception as e:
        print(f'{db} error: {e}')
