#!/usr/bin/env python3
"""
build_db.py — Build / refresh a local SQLite DB from MLCounter hero pages.

Supports input lines like:
  https://mlcounter.com/heroes/atlas/
  Atlas | https://mlcounter.com/heroes/atlas/
  Atlas|https://mlcounter.com/heroes/atlas/

Usage:
  python build_db.py --input hero_formatted_list.txt --db mlcounter.db --fresh
"""

import argparse
import random
import re
import sqlite3
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional, Tuple

import requests
from bs4 import BeautifulSoup
from bs4.element import Tag


# -----------------------------
# Text normalization utilities
# -----------------------------

_WS_RE = re.compile(r"\s+")

def norm_text(s: str) -> str:
    """Lowercase, collapse whitespace, and normalize NBSP."""
    if s is None:
        return ""
    s = s.replace("\xa0", " ")
    s = _WS_RE.sub(" ", s)
    return s.strip().lower()

def clean_text(s: str) -> str:
    """Collapse whitespace + normalize NBSP without forcing lowercase."""
    if s is None:
        return ""
    s = s.replace("\xa0", " ")
    s = _WS_RE.sub(" ", s)
    return s.strip()


# -----------------------------
# Parsing structures
# -----------------------------

@dataclass
class HeroRecord:
    name: str
    url: str
    role: Optional[str] = None
    specialty: Optional[str] = None
    lane: Optional[str] = None
    win_rate: Optional[float] = None
    tier: Optional[str] = None
    weak_against: Optional[List[str]] = None
    strong_against: Optional[List[str]] = None


# -----------------------------
# HTTP
# -----------------------------

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive",
}

def fetch_html(session: requests.Session, url: str, retries: int = 3, timeout: int = 25) -> str:
    last_err: Optional[Exception] = None
    for attempt in range(1, retries + 1):
        try:
            r = session.get(url, headers=DEFAULT_HEADERS, timeout=timeout)
            r.raise_for_status()
            return r.text
        except Exception as e:
            last_err = e
            if attempt < retries:
                time.sleep(1.5 * attempt)
    raise RuntimeError(f"Failed to fetch {url}: {last_err}")


# -----------------------------
# HTML parsing (robust)
# -----------------------------

def find_all_counter_heading_p(soup: BeautifulSoup, kind: str) -> List[Tag]:
    """
    Return ALL <p> tags that contain 'is weak against' or 'is strong against',
    because some pages include duplicates (TOC, template blocks, etc.).
    """
    needle = "is weak against" if kind == "weak" else "is strong against"
    matches: List[Tag] = []
    for p in soup.find_all("p"):
        t = norm_text(p.get_text(" ", strip=True))
        if needle in t:
            matches.append(p)
    return matches

def _extract_hero_name_from_figure(fig: Tag) -> Optional[str]:
    """
    Extract hero name from a <figure> block.
    Priority:
      1) figcaption a text
      2) figcaption plain text
      3) img alt
    """
    if not fig or not isinstance(fig, Tag):
        return None

    figcap = fig.find("figcaption")
    if figcap:
        a = figcap.find("a")
        if a:
            name = clean_text(a.get_text(" ", strip=True))
            if name:
                return name

        cap_text = clean_text(figcap.get_text(" ", strip=True))
        if cap_text:
            return cap_text

    img = fig.find("img")
    if img:
        alt = clean_text(img.get("alt") or "")
        if alt:
            return alt

    return None

def extract_hero_list_from_columns(cols_div: Tag, max_items: int = 5) -> List[str]:
    """
    Extract hero names from a wp-block-columns grid section.
    Works even when figcaptions don't contain <a> tags (plain text captions).
    """
    if not cols_div:
        return []

    heroes: List[str] = []
    seen = set()

    for fig in cols_div.find_all("figure"):
        name = _extract_hero_name_from_figure(fig)
        if not name:
            continue
        key = name.strip().lower()
        if key in seen:
            continue
        seen.add(key)
        heroes.append(name)
        if len(heroes) >= max_items:
            break

    return heroes

def find_best_columns_after_heading(heading_p: Tag, max_columns_to_check: int = 50) -> Optional[Tag]:
    """
    Scan forward from heading_p and return the first wp-block-columns that
    yields at least 1 hero figure.
    """
    if not heading_p:
        return None

    checked = 0
    for el in heading_p.find_all_next():
        if not isinstance(el, Tag):
            continue
        if el.name != "div":
            continue
        cls = el.get("class") or []
        if "wp-block-columns" not in cls:
            continue

        heroes = extract_hero_list_from_columns(el, max_items=5)
        if heroes:
            return el

        checked += 1
        if checked >= max_columns_to_check:
            break

    return None

def parse_role_lane_specialty_winrate_tier(
    soup: BeautifulSoup
) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[float], Optional[str]]:
    role = specialty = lane = tier = None
    win_rate: Optional[float] = None

    for p in soup.find_all("p"):
        t_raw = clean_text(p.get_text(" ", strip=True))
        t = norm_text(t_raw)

        if t.startswith("role:"):
            role = clean_text(t_raw.split(":", 1)[1])
        elif t.startswith("specialty:"):
            specialty = clean_text(t_raw.split(":", 1)[1])
        elif t.startswith("lane:"):
            lane = clean_text(t_raw.split(":", 1)[1])
        elif t.startswith("win rate:"):
            m_wr = re.search(r"win rate:\s*([0-9]+(?:\.[0-9]+)?)\s*%", t, flags=re.I)
            if m_wr:
                try:
                    win_rate = float(m_wr.group(1))
                except ValueError:
                    pass
            m_tier = re.search(r"tier:\s*([A-Z][+\-]?)", t_raw)
            if m_tier:
                tier = m_tier.group(1).strip()

    return role, lane, specialty, win_rate, tier

def extract_counters(soup: BeautifulSoup, kind: str) -> List[str]:
    """
    Key fix: try ALL matching headings and return the first one that
    actually yields hero names.
    """
    headings = find_all_counter_heading_p(soup, kind)
    for hp in headings:
        cols = find_best_columns_after_heading(hp)
        heroes = extract_hero_list_from_columns(cols, max_items=5)
        if heroes:
            return heroes
    return []

def parse_hero_page(name: str, url: str, html: str) -> HeroRecord:
    soup = BeautifulSoup(html, "html.parser")
    role, lane, specialty, win_rate, tier = parse_role_lane_specialty_winrate_tier(soup)

    weak_against = extract_counters(soup, "weak")
    strong_against = extract_counters(soup, "strong")

    return HeroRecord(
        name=name,
        url=url,
        role=role,
        specialty=specialty,
        lane=lane,
        win_rate=win_rate,
        tier=tier,
        weak_against=weak_against,
        strong_against=strong_against,
    )


# -----------------------------
# Input parsing
# -----------------------------

def parse_input_file(path: str) -> List[Tuple[str, str]]:
    pairs: List[Tuple[str, str]] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            raw = line.strip()
            if not raw or raw.startswith("#"):
                continue

            if "|" in raw:
                left, right = raw.split("|", 1)
                name = clean_text(left)
                url = clean_text(right)
                if not url.startswith("http"):
                    continue
                pairs.append((name, url))
            else:
                url = raw
                if not url.startswith("http"):
                    continue
                slug = url.rstrip("/").split("/")[-1]
                name = slug.replace("-", " ").title()
                pairs.append((name, url))

    return pairs


# -----------------------------
# SQLite
# -----------------------------

def init_db(conn: sqlite3.Connection, fresh: bool = False) -> None:
    cur = conn.cursor()
    if fresh:
        cur.execute("DROP TABLE IF EXISTS counters;")
        cur.execute("DROP TABLE IF EXISTS heroes;")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS heroes (
        hero TEXT PRIMARY KEY,
        url TEXT NOT NULL,
        role TEXT,
        lane TEXT,
        specialty TEXT,
        win_rate REAL,
        tier TEXT,
        updated_at TEXT NOT NULL
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS counters (
        hero TEXT NOT NULL,
        other_hero TEXT NOT NULL,
        relation TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        PRIMARY KEY (hero, other_hero, relation),
        FOREIGN KEY (hero) REFERENCES heroes(hero)
    );
    """)

    cur.execute("CREATE INDEX IF NOT EXISTS idx_counters_hero_relation ON counters(hero, relation);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_counters_otherhero ON counters(other_hero);")
    conn.commit()

def upsert_hero(conn: sqlite3.Connection, rec: HeroRecord) -> None:
    cur = conn.cursor()
    now = datetime.now(timezone.utc).isoformat()

    cur.execute("""
    INSERT INTO heroes (hero, url, role, lane, specialty, win_rate, tier, updated_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(hero) DO UPDATE SET
        url=excluded.url,
        role=excluded.role,
        lane=excluded.lane,
        specialty=excluded.specialty,
        win_rate=excluded.win_rate,
        tier=excluded.tier,
        updated_at=excluded.updated_at;
    """, (rec.name, rec.url, rec.role, rec.lane, rec.specialty, rec.win_rate, rec.tier, now))

    cur.execute("DELETE FROM counters WHERE hero = ?;", (rec.name,))

    def _insert_many(items: List[str], relation: str):
        if not items:
            return
        rows = [(rec.name, other, relation, now) for other in items if other]
        cur.executemany("""
            INSERT OR REPLACE INTO counters (hero, other_hero, relation, updated_at)
            VALUES (?, ?, ?, ?);
        """, rows)

    _insert_many(rec.weak_against or [], "weak_against")
    _insert_many(rec.strong_against or [], "strong_against")

    conn.commit()


# -----------------------------
# Main
# -----------------------------

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="Path to hero URL list file (supports 'Name | URL').")
    ap.add_argument("--db", default="mlcounter.db", help="SQLite DB path (default: mlcounter.db).")
    ap.add_argument("--fresh", action="store_true", help="Drop & recreate tables (start from scratch).")
    ap.add_argument("--sleep-min", type=float, default=0.4, help="Min sleep between requests (seconds).")
    ap.add_argument("--sleep-max", type=float, default=1.2, help="Max sleep between requests (seconds).")
    ap.add_argument("--limit", type=int, default=None, help="Only process first N heroes (debug).")
    args = ap.parse_args()

    hero_pairs = parse_input_file(args.input)
    if not hero_pairs:
        print(f"ERROR: no valid hero URLs found in {args.input}", file=sys.stderr)
        sys.exit(1)

    if args.limit is not None:
        hero_pairs = hero_pairs[: max(0, args.limit)]

    print(f"Loaded {len(hero_pairs)} hero URLs from {args.input}")

    conn = sqlite3.connect(args.db)
    try:
        init_db(conn, fresh=args.fresh)

        session = requests.Session()

        total = len(hero_pairs)
        for i, (name, url) in enumerate(hero_pairs, start=1):
            if not url.startswith("http"):
                raise RuntimeError(f"Bad URL for {name}: {url!r}")

            html = fetch_html(session, url)
            rec = parse_hero_page(name, url, html)
            upsert_hero(conn, rec)

            wa = len(rec.weak_against or [])
            sa = len(rec.strong_against or [])
            role = rec.role or "?"
            print(f"[{i}/{total}] Saved {rec.name:<14} | weak_against={wa:<2} strong_against={sa:<2} | role={role}")

            time.sleep(random.uniform(args.sleep_min, args.sleep_max))

    finally:
        conn.close()


if __name__ == "__main__":
    main()
