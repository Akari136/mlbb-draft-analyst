"""
mlbb_init_scraper.py - MLBB Initialization Scraper (Fandom MediaWiki API)

What it does:
1) Parses List_of_heroes (via api.php?action=parse) to get:
   - hero, hero_url, roles, specialties, lanes
   (ignores hero order, price, region, release date)

2) Crawls each hero page (via api.php?action=parse) to extract:
   - "Hero stats" wikitable rows (Attribute, Level 1, Level 15, Growth)
   - Specifically stores "Basic Attack range" into hero_features.basic_attack_range

Stores into SQLite:
- hero_core
- hero_base_stats
- hero_features

RUN:
  python mlbb_init_scraper.py test     # quick test (5 heroes)
  python mlbb_init_scraper.py          # full run
"""

from __future__ import annotations

import random
import re
import sqlite3
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import requests
from bs4 import BeautifulSoup


API_URL = "https://mobile-legends.fandom.com/api.php"


# ----------------------------
# Data model
# ----------------------------

@dataclass
class HeroCore:
    hero: str
    hero_url: str
    roles: Optional[str]
    specialties: Optional[str]
    lanes: Optional[str]


# ----------------------------
# Helpers
# ----------------------------

def clean_num(s: Optional[str]) -> Optional[float]:
    """
    Converts strings like:
      '2,225' -> 2225.0
      '17 (13.7%)' -> 17.0
      '1.10' -> 1.1
    Returns None if no parseable number.
    """
    if not s:
        return None
    t = s.strip().replace(",", "")
    m = re.match(r"^\s*([0-9]+(?:\.[0-9]+)?)", t)
    if not m:
        return None
    try:
        return float(m.group(1))
    except ValueError:
        return None


# ----------------------------
# Scraper
# ----------------------------

class MLBBFandomAPIScraper:
    def __init__(self, db_path: str = "mlcounter.db", polite_delay: float = 0.35):
        self.db_path = db_path
        self.polite_delay = polite_delay

        self.sess = requests.Session()
        self.sess.headers.update({
            "User-Agent": "MLBB-Draft-Analyst/1.0 (Educational Project; MediaWiki API)",
            "Accept": "application/json,text/plain,*/*",
        })

    # ---------- API parse ----------

    def api_parse_html(self, page: str, timeout: int = 30) -> str:
        """
        Calls action=parse and returns rendered HTML. Includes retry/backoff.
        """
        params = {
            "action": "parse",
            "page": page,
            "prop": "text",
            "redirects": 1,
            "format": "json",
            "formatversion": 2,
            "maxlag": 5,
        }

        last_err = None
        for attempt in range(6):
            try:
                r = self.sess.get(API_URL, params=params, timeout=timeout)

                # Common throttling/bot responses
                if r.status_code in (403, 429, 503):
                    time.sleep((2 ** attempt) + random.uniform(0.2, 1.0))
                    continue

                r.raise_for_status()
                data = r.json()

                if "error" in data:
                    raise RuntimeError(f"API error for page={page}: {data['error']}")

                parse = data.get("parse")
                if not parse or "text" not in parse:
                    raise RuntimeError(f"No parse.text returned for page={page}")

                return parse["text"]

            except Exception as e:
                last_err = e
                time.sleep((2 ** attempt) + random.uniform(0.2, 0.8))

        raise RuntimeError(f"Failed to parse page={page}. Last error: {last_err}")

    # ---------- DB ----------

    def ensure_tables(self) -> None:
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        cur.execute("""
        CREATE TABLE IF NOT EXISTS hero_core (
            hero TEXT PRIMARY KEY,
            hero_url TEXT NOT NULL,
            roles TEXT,
            specialties TEXT,
            lanes TEXT,
            scraped_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS hero_base_stats (
            hero TEXT NOT NULL,
            attribute TEXT NOT NULL,
            level1 TEXT,
            level15 TEXT,
            growth TEXT,
            scraped_at TEXT DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (hero, attribute)
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS hero_features (
            hero TEXT PRIMARY KEY,
            hp_base REAL,
            hp_regen REAL,
            mana REAL,
            mana_regen REAL,
            physical_attack REAL,
            magic_power REAL,
            physical_defense REAL,
            magic_defense REAL,
            attack_speed REAL,
            movement_speed REAL,
            basic_attack_range REAL,
            scraped_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """)

        conn.commit()
        conn.close()

    def save_hero_core(self, heroes: List[HeroCore]) -> None:
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        for h in heroes:
            cur.execute("""
            INSERT OR REPLACE INTO hero_core (hero, hero_url, roles, specialties, lanes)
            VALUES (?, ?, ?, ?, ?)
            """, (h.hero, h.hero_url, h.roles, h.specialties, h.lanes))

        conn.commit()
        conn.close()

    def save_hero_base_stats(self, hero: str, base_stats: Dict[str, Tuple[str, str, str]]) -> None:
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        for attr, (lvl1, lvl15, growth) in base_stats.items():
            cur.execute("""
            INSERT OR REPLACE INTO hero_base_stats (hero, attribute, level1, level15, growth)
            VALUES (?, ?, ?, ?, ?)
            """, (hero, attr, lvl1, lvl15, growth))

        conn.commit()
        conn.close()

    def save_hero_features(self, hero: str, base_stats: Dict[str, Tuple[str, str, str]]) -> None:
        # lowercased attribute lookup
        lookup = {k.lower(): v for k, v in base_stats.items()}

        def lvl1(attr_name: str) -> Optional[float]:
            row = lookup.get(attr_name.lower())
            if not row:
                return None
            return clean_num(row[0])

        features = {
            "hp_base": lvl1("HP"),
            "hp_regen": lvl1("HP Regen"),
            "mana": lvl1("Mana"),
            "mana_regen": lvl1("Mana Regen"),
            "physical_attack": lvl1("Physical Attack"),
            "magic_power": lvl1("Magic Power"),
            "physical_defense": lvl1("Physical Defense"),
            "magic_defense": lvl1("Magic Defense"),
            "attack_speed": lvl1("Attack Speed"),
            "movement_speed": lvl1("Movement Speed"),
            "basic_attack_range": lvl1("Basic Attack range"),  # exact label seen on wiki
        }

        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("""
        INSERT OR REPLACE INTO hero_features
        (hero, hp_base, hp_regen, mana, mana_regen,
         physical_attack, magic_power, physical_defense, magic_defense,
         attack_speed, movement_speed, basic_attack_range)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            hero,
            features["hp_base"],
            features["hp_regen"],
            features["mana"],
            features["mana_regen"],
            features["physical_attack"],
            features["magic_power"],
            features["physical_defense"],
            features["magic_defense"],
            features["attack_speed"],
            features["movement_speed"],
            features["basic_attack_range"],
        ))
        conn.commit()
        conn.close()

    # ---------- Parsing: List_of_heroes ----------

    def parse_list_of_heroes(self) -> List[HeroCore]:
        """
        Robustly finds the correct hero list table and extracts:
        - hero, hero_url
        - roles, specialties, lanes (best effort by headers)

        Fixes the "Found 0 heroes" issue by:
        - selecting the right wikitable via header signals
        - extracting hero link from ANY cell in the row (icon cell included)
        """
        html = self.api_parse_html("List_of_heroes")
        soup = BeautifulSoup(html, "html.parser")

        tables = soup.find_all("table", class_=lambda c: c and "wikitable" in c)
        if not tables:
            raise RuntimeError("No wikitable found on List_of_heroes (API HTML).")

        def norm_headers(tr) -> List[str]:
            return [th.get_text(" ", strip=True).lower() for th in tr.find_all(["th", "td"])]

        # Choose the best matching table
        target_table = None
        target_headers: Optional[List[str]] = None
        best_score = -1

        for tbl in tables:
            header_tr = tbl.find("tr")
            if not header_tr:
                continue
            hdrs = norm_headers(header_tr)

            score = 0
            score += 2 if any("hero" in h for h in hdrs) else 0
            score += 2 if any("role" in h for h in hdrs) else 0
            score += 2 if any("special" in h for h in hdrs) else 0
            score += 1 if any("lane" in h for h in hdrs) else 0

            if score > best_score:
                best_score = score
                target_table = tbl
                target_headers = hdrs

        if not target_table or not target_headers or best_score < 3:
            raise RuntimeError("Could not identify the main hero list table on List_of_heroes.")

        def find_idx(keys: List[str]) -> Optional[int]:
            for i, h in enumerate(target_headers):
                for k in keys:
                    if k in h:
                        return i
            return None

        idx_roles = find_idx(["role"])
        idx_specs = find_idx(["special"])
        idx_lanes = find_idx(["lane"])

        def is_valid_hero_href(href: str) -> bool:
            if not href or not href.startswith("/wiki/"):
                return False
            low = href.lower()
            bad = ["file:", "category:", "special:", "template:", "module:", "help:", "list_of"]
            return not any(b in low for b in bad)

        out: Dict[str, HeroCore] = {}

        # iterate data rows
        for tr in target_table.find_all("tr")[1:]:
            cells = tr.find_all(["td", "th"])
            if not cells:
                continue

            # Find the first valid /wiki/ link anywhere in the row
            hero_a = None
            for a in tr.find_all("a", href=True):
                href = a["href"].strip()
                if is_valid_hero_href(href):
                    # prefer a with title attribute
                    if a.get("title"):
                        hero_a = a
                        break
                    if hero_a is None:
                        hero_a = a

            if not hero_a:
                continue

            hero_url = hero_a["href"].strip()
            hero_name = (hero_a.get("title") or hero_a.get_text(" ", strip=True) or "").strip()
            if not hero_name:
                continue

            def safe_cell_text(idx: Optional[int]) -> Optional[str]:
                if idx is None or idx < 0 or idx >= len(cells):
                    return None
                txt = cells[idx].get_text(" ", strip=True)
                return txt if txt else None

            out[hero_url] = HeroCore(
                hero=hero_name,
                hero_url=hero_url,
                roles=safe_cell_text(idx_roles),
                specialties=safe_cell_text(idx_specs),
                lanes=safe_cell_text(idx_lanes),
            )

        return list(out.values())

    # ---------- Parsing: hero page stats ----------

    def parse_hero_page_stats(self, hero_title: str) -> Dict[str, Tuple[str, str, str]]:
        """
        Extracts the "Hero stats" table rows:
        Attribute | Level 1 | Level 15 | Growth
        """
        html = self.api_parse_html(hero_title)
        soup = BeautifulSoup(html, "html.parser")

        hero_stats_table = None
        for table in soup.find_all("table", class_=lambda c: c and "wikitable" in c):
            first_tr = table.find("tr")
            if first_tr and "hero stats" in first_tr.get_text(" ", strip=True).lower():
                hero_stats_table = table
                break

        if not hero_stats_table:
            raise RuntimeError(f"Hero stats table not found for: {hero_title}")

        base_stats: Dict[str, Tuple[str, str, str]] = {}
        for tr in hero_stats_table.find_all("tr"):
            tds = tr.find_all("td")
            if len(tds) < 4:
                continue

            attr = tds[0].get_text(" ", strip=True)
            lvl1 = tds[1].get_text(" ", strip=True)
            lvl15 = tds[2].get_text(" ", strip=True)
            growth = tds[3].get_text(" ", strip=True)

            if attr:
                base_stats[attr] = (lvl1, lvl15, growth)

        return base_stats

    # ---------- Main pipeline ----------

    def initialize(self, limit: Optional[int] = None) -> None:
        """
        Initialization pipeline:
        1) Create tables
        2) Parse List_of_heroes -> save hero_core
        3) For each hero -> parse hero stats -> save hero_base_stats + hero_features
        """
        self.ensure_tables()

        print("1) Parsing List_of_heroes (API)...")
        heroes = self.parse_list_of_heroes()
        heroes.sort(key=lambda x: x.hero.lower())
        if limit is not None:
            heroes = heroes[:limit]

        print(f"   Found {len(heroes)} heroes. Saving hero_core...")
        self.save_hero_core(heroes)

        print("2) Crawling hero pages for base stats (+ basic attack range)...")
        ok = 0
        failed: List[Tuple[str, str]] = []

        for i, h in enumerate(heroes, 1):
            print(f"   [{i}/{len(heroes)}] {h.hero} ... ", end="", flush=True)
            try:
                base_stats = self.parse_hero_page_stats(h.hero)
                self.save_hero_base_stats(h.hero, base_stats)
                self.save_hero_features(h.hero, base_stats)

                ok += 1
                bar = None
                # sometimes casing differs
                for k in base_stats.keys():
                    if k.strip().lower() == "basic attack range":
                        bar = base_stats[k][0]
                        break
                print(f"✓ (Basic Attack range L1={bar})")
            except Exception as e:
                failed.append((h.hero, str(e)))
                print(f"✗ ({e})")

            time.sleep(self.polite_delay + random.uniform(0.1, 0.5))

        print("\nInitialization complete.")
        print(f"Success: {ok}/{len(heroes)}")
        if failed:
            print(f"Failed: {len(failed)} (first 10)")
            for hero, err in failed[:10]:
                print(f" - {hero}: {err}")


# ----------------------------
# CLI
# ----------------------------

def main():
    import sys

    # IMPORTANT: run this file, not the old ml_wiki_scraper_v2.py
    scraper = MLBBFandomAPIScraper(db_path="mlcounter.db", polite_delay=0.35)

    if len(sys.argv) > 1 and sys.argv[1].lower() == "test":
        print("🧪 TEST MODE (limit=5)\n")
        scraper.initialize(limit=5)
    else:
        print("🚀 FULL INIT MODE\n")
        scraper.initialize(limit=None)


if __name__ == "__main__":
    main()
