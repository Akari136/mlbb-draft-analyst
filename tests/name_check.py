import sqlite3

DB = "mlcounter.db"
names = ["Khufra", "Kadita", "Yu Zhong", "Lapu-Lapu"]

con = sqlite3.connect(DB)
cur = con.cursor()

for n in names:
    cur.execute("SELECT hero FROM heroes WHERE hero = ?", (n,))
    ok = cur.fetchone() is not None
    print(f"{n!r} exists:", ok)

con.close()
