import sqlite3, re

_norm_re = re.compile(r"[^a-z0-9]+")
def canon(s: str) -> str:
    return _norm_re.sub("", (s or "").strip().lower())

DB = "mlcounter.db"
tests = ["Yu Zhong", "Yuzhong", "Lapu-Lapu", "Lapu Lapu", "Khufra"]

con = sqlite3.connect(DB)
cur = con.cursor()
cur.execute("SELECT hero FROM heroes")
heroes = [r[0] for r in cur.fetchall()]
alias = {canon(h): h for h in heroes}

for t in tests:
    print(f"{t!r} ->", alias.get(canon(t)))

con.close()
