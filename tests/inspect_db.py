import sqlite3, random

conn = sqlite3.connect("mlcounter.db")
cur = conn.cursor()

cur.execute("SELECT hero FROM heroes;")
heroes = [r[0] for r in cur.fetchall()]
h = random.choice(heroes)

for rel in ("strong_against","weak_against"):
    cur.execute("""
    SELECT other_hero FROM counters
    WHERE hero=? AND relation=?
    """, (h, rel))
    print(h, rel, [r[0] for r in cur.fetchall()])

conn.close()
