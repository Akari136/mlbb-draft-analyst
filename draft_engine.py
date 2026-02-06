#!/usr/bin/env python3
"""
draft_engine.py — Draft recommendation engine using:
- Counter DB (strong_against / weak_against)
- Meta weighting (win/pick/ban + tier) from meta.json

Includes:
- Robust name normalization
- DB-as-source-of-truth alias resolution
- Dynamic explanations
- Inverse counter inference (FAST, cached):
    If enemy is weak against hero => hero is strong vs enemy
    If enemy is strong against hero => hero is weak vs enemy
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
from dataclasses import dataclass
from typing import Dict, List, Optional, Literal, Tuple


# -----------------------------
# Helpers
# -----------------------------

_WS_RE = re.compile(r"\s+")

def clean_text(s: str) -> str:
    if s is None:
        return ""
    s = s.replace("\xa0", " ")
    s = _WS_RE.sub(" ", s)
    return s.strip()

def normalize_key(s: str) -> str:
    s = clean_text(s).lower()
    s = re.sub(r"[^a-z0-9]+", "", s)
    return s

def parse_percent(x: Optional[str]) -> Optional[float]:
    if not x:
        return None
    x = clean_text(x)
    m = re.search(r"([0-9]+(?:\.[0-9]+)?)", x)
    if not m:
        return None
    try:
        return float(m.group(1))
    except ValueError:
        return None


# -----------------------------
# Explainability structures
# -----------------------------

ReasonType = Literal["counter_strong", "counter_weak", "meta", "tier"]

@dataclass
class Reason:
    type: ReasonType
    delta: float
    detail: str

def render_explanation(reasons: List[Reason], max_reasons: int = 3) -> str:
    if not reasons:
        return "No strong signals detected (neutral pick)."
    reasons_sorted = sorted(reasons, key=lambda r: abs(r.delta), reverse=True)[:max_reasons]
    parts: List[str] = []
    for r in reasons_sorted:
        sign = "+" if r.delta >= 0 else ""
        parts.append(f"{r.detail} ({sign}{r.delta:.3f})")
    return "; ".join(parts)


# -----------------------------
# Data classes
# -----------------------------

@dataclass
class PickResult:
    hero: str
    score: float
    strong_hits: List[str]
    weak_hits: List[str]
    meta_bonus: float
    counter_bonus: float
    reasons: List[Reason]
    explain: str
    early_tip: str


# -----------------------------
# Draft Engine
# -----------------------------

class DraftEngine:
    def __init__(
        self,
        db_path: str = "mlcounter.db",
        meta_path: str = "meta.json",
        weights: Optional[Dict[str, float]] = None,
    ):
        self.conn = sqlite3.connect(db_path)
        self.cur = self.conn.cursor()

        self.hero_key_to_dbname = self._build_db_hero_index()

        self.meta = self._load_meta(meta_path)
        self.meta_key_to_name = {normalize_key(k): k for k in self.meta.keys()} if self.meta else {}

        self.aliases = self._build_aliases()

        # Default weights (safe-ish)
        self.w = {
            "strong_hit": 1.25,
            "weak_hit": -1.25,
            "win": 0.18,
            "pick": 0.02,
            "ban": 0.05,
            "tier": 0.75,
        }
        if weights:
            self.w.update(weights)

        self.tier_value = {
            "S+": 1.5, "S": 1.2, "S-": 1.0,
            "A+": 0.8, "A": 0.6, "A-": 0.4,
            "B+": 0.2, "B": 0.0, "B-": -0.1,
            "C+": -0.2, "C": -0.3, "C-": -0.4,
            "PENDING ANALYSIS": 0.0,
        }

    def close(self):
        self.conn.close()

    # ---------- indexing / loading ----------

    def _build_db_hero_index(self) -> Dict[str, str]:
        self.cur.execute("SELECT hero FROM heroes")
        out: Dict[str, str] = {}
        for (hero,) in self.cur.fetchall():
            out[normalize_key(hero)] = hero
        return out

    def _load_meta(self, path: str) -> Dict:
        if not path or not os.path.exists(path):
            return {}
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}

    def _build_aliases(self) -> Dict[str, str]:
        """
        Maps common user spellings to the DB hero names.
        Target value must exist in DB to be inserted.
        """
        alias_targets = {
            "popol and kupa": "popolandkupa",
            "popol & kupa": "popolandkupa",
            "yi sun shin": "yisunshin",
            "yss": "yisunshin",
            "lapu lapu": "lapulapu",
            "lapu-lapu": "lapulapu",
            "x borg": "xborg",
            "x-borg": "xborg",
            "x.borg": "xborg",
        }

        aliases: Dict[str, str] = {}
        for raw_alias, target_norm in alias_targets.items():
            target_db = self.hero_key_to_dbname.get(target_norm)
            if target_db:
                aliases[normalize_key(raw_alias)] = target_db
        return aliases

    # ---------- name resolution ----------

    def resolve_to_db_name(self, raw_name: str) -> Optional[str]:
        k = normalize_key(raw_name)
        if k in self.aliases:
            return self.aliases[k]
        return self.hero_key_to_dbname.get(k)

    def resolve_meta_entry(self, db_hero_name: str) -> Optional[dict]:
        if not self.meta:
            return None
        k = normalize_key(db_hero_name)
        meta_name = self.meta_key_to_name.get(k)
        if not meta_name:
            return None
        return self.meta.get(meta_name)

    # ---------- DB queries ----------

    def _get_relation_list(self, hero: str, relation: str) -> List[str]:
        self.cur.execute(
            "SELECT other_hero FROM counters WHERE hero = ? AND relation = ?",
            (hero, relation),
        )
        return [r[0] for r in self.cur.fetchall()]

    def _get_relation_hits(self, hero: str, enemies: List[str], relation: str) -> List[str]:
        if not enemies:
            return []
        placeholders = ",".join(["?"] * len(enemies))
        q = f"""
        SELECT other_hero
        FROM counters
        WHERE hero = ?
          AND relation = ?
          AND other_hero IN ({placeholders})
        """
        self.cur.execute(q, [hero, relation, *enemies])
        return [r[0] for r in self.cur.fetchall()]

    # ---------- meta scoring ----------

    def _meta_bonus_and_reasons(self, hero: str) -> Tuple[float, List[Reason]]:
        m = self.resolve_meta_entry(hero)
        if not m:
            return 0.0, []

        win = parse_percent(m.get("win_rate"))
        pick = parse_percent(m.get("pick_rate"))
        ban = parse_percent(m.get("ban_rate"))

        tier_raw = m.get("tier") or ""
        tier_key = clean_text(str(tier_raw)).upper()
        tier_val = self.tier_value.get(tier_key, 0.0)

        win_bonus = (win - 50.0) * self.w["win"] if win is not None else 0.0
        pick_bonus = pick * self.w["pick"] if pick is not None else 0.0
        ban_bonus = ban * self.w["ban"] if ban is not None else 0.0
        tier_bonus = tier_val * self.w["tier"]

        total = win_bonus + pick_bonus + ban_bonus + tier_bonus

        reasons: List[Reason] = []
        if win is not None and abs(win_bonus) > 0.01:
            reasons.append(Reason("meta", win_bonus, f"Win Rate {win:.2f}%"))
        if pick is not None and abs(pick_bonus) > 0.01:
            reasons.append(Reason("meta", pick_bonus, f"Pick Rate {pick:.2f}%"))
        if ban is not None and abs(ban_bonus) > 0.01:
            reasons.append(Reason("meta", ban_bonus, f"Ban Rate {ban:.2f}%"))
        if abs(tier_bonus) > 0.01:
            reasons.append(Reason("tier", tier_bonus, f"Tier {tier_key.title()}"))

        return total, reasons

    # ---------- recommend ----------

    def recommend(
        self,
        pool: List[str],
        enemies: List[str],
        base_score: float = 5.0,
        top_n: int = 10,
        max_reasons: int = 3,
        use_inverse: bool = True,
    ) -> List[PickResult]:
        # Resolve inputs -> DB names
        db_enemies: List[str] = []
        for x in enemies:
            v = self.resolve_to_db_name(x)
            if v:
                db_enemies.append(v)

        db_pool: List[str] = []
        for x in pool:
            v = self.resolve_to_db_name(x)
            if v:
                db_pool.append(v)

        # Cache inverse lists ONCE per call
        enemy_cache: Dict[str, Dict[str, set]] = {}
        if use_inverse:
            for e in db_enemies:
                enemy_cache[e] = {
                    "weak": set(self._get_relation_list(e, "weak_against")),
                    "strong": set(self._get_relation_list(e, "strong_against")),
                }

        def uniq(seq: List[str]) -> List[str]:
            out: List[str] = []
            seen = set()
            for x in seq:
                if x not in seen:
                    seen.add(x)
                    out.append(x)
            return out

        results: List[PickResult] = []

        for hero in db_pool:
            reasons: List[Reason] = []

            # direct hits (hero -> enemy)
            strong_direct = self._get_relation_hits(hero, db_enemies, "strong_against")
            weak_direct = self._get_relation_hits(hero, db_enemies, "weak_against")

            # inverse hits (enemy -> hero)
            strong_inv: List[str] = []
            weak_inv: List[str] = []
            if use_inverse and db_enemies:
                for e in db_enemies:
                    if hero in enemy_cache[e]["weak"]:
                        strong_inv.append(e)
                    if hero in enemy_cache[e]["strong"]:
                        weak_inv.append(e)

            strong_hits = uniq(strong_direct + strong_inv)
            weak_hits = uniq(weak_direct + weak_inv)

            counter_bonus = (
                len(strong_hits) * self.w["strong_hit"]
                + len(weak_hits) * self.w["weak_hit"]
            )

            # Reason messages show whether it came from direct/inverse
            if strong_hits:
                src_note = []
                if strong_direct:
                    src_note.append("direct")
                if strong_inv:
                    src_note.append("inverse")
                reasons.append(
                    Reason(
                        "counter_strong",
                        len(strong_hits) * self.w["strong_hit"],
                        f"Strong vs {', '.join(strong_hits)} ({'/'.join(src_note)})" if src_note else f"Strong vs {', '.join(strong_hits)}",
                    )
                )

            if weak_hits:
                src_note = []
                if weak_direct:
                    src_note.append("direct")
                if weak_inv:
                    src_note.append("inverse")
                reasons.append(
                    Reason(
                        "counter_weak",
                        len(weak_hits) * self.w["weak_hit"],
                        f"Weak vs {', '.join(weak_hits)} ({'/'.join(src_note)})" if src_note else f"Weak vs {', '.join(weak_hits)}",
                    )
                )

            meta_bonus, meta_reasons = self._meta_bonus_and_reasons(hero)
            reasons.extend(meta_reasons)

            m_data = self.resolve_meta_entry(hero) or {}
            tip = m_data.get("early_tips") or m_data.get("early_tip") or "Tactical analysis pending."

            score = base_score + counter_bonus + meta_bonus
            explain = render_explanation(reasons, max_reasons=max_reasons)

            results.append(
                PickResult(
                    hero=hero,
                    score=round(score, 3),
                    strong_hits=strong_hits,
                    weak_hits=weak_hits,
                    meta_bonus=round(meta_bonus, 3),
                    counter_bonus=round(counter_bonus, 3),
                    reasons=reasons,
                    explain=explain,
                    early_tip=tip,
                )
            )

        results.sort(key=lambda r: r.score, reverse=True)
        return results[:top_n]


# -----------------------------
# Quick CLI test
# -----------------------------
if __name__ == "__main__":
    engine = DraftEngine("mlcounter.db", "meta.json")

    enemies = ["Yuzhong"]
    pool = ["Thamuz", "Terizla", "Argus", "Martis", "Lapu-Lapu"]

    res = engine.recommend(pool=pool, enemies=enemies, top_n=10, use_inverse=True)

    print("ENEMIES:", enemies)
    print("POOL:", pool)
    print("\nRESULTS:")
    for r in res:
        print(f"{r.hero:<12} score={r.score:<6} counter={r.counter_bonus:<6} meta={r.meta_bonus:<6}")
        print(f"  strong_hits: {r.strong_hits}")
        print(f"  weak_hits:   {r.weak_hits}")
        print(f"  why: {r.explain}")
        print(f"  tip: {r.early_tip}\n")

    engine.close()
