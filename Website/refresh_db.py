import sqlite3, os

DB_PATH = os.path.join(os.path.dirname(__file__), "orders.db")
conn = sqlite3.connect(DB_PATH)
c = conn.cursor()
c.execute("ALTER TABLE orders ADD COLUMN lat REAL")
c.execute("ALTER TABLE orders ADD COLUMN lon REAL")
conn.commit()
conn.close()
