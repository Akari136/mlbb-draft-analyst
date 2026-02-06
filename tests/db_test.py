import sqlite3

DB = "mlcounter.db"  # change if needed

con = sqlite3.connect(DB)
cur = con.cursor()

print("tables:", cur.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall())
print("hero_count:", cur.execute("SELECT COUNT(*) FROM heroes;").fetchone()[0])
print("counter_count:", cur.execute("SELECT COUNT(*) FROM counters;").fetchone()[0])

hero = "Atlas"
sa = cur.execute("""
SELECT other_hero FROM counters
WHERE hero=? AND relation='strong_against'
ORDER BY other_hero
""", (hero,)).fetchall()

wa = cur.execute("""
SELECT other_hero FROM counters
WHERE hero=? AND relation='weak_against'
ORDER BY other_hero
""", (hero,)).fetchall()

print(hero, "strong:", [x[0] for x in sa])
print(hero, "weak:", [x[0] for x in wa])

con.close()
