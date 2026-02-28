#!/usr/bin/env python3
"""
draft_engine.py — Draft recommendation engine using:
- Counter DB (strong_against / weak_against)
- Meta weighting (win/pick/ban + tier) from meta.json
- Personal performance history from game_history table

NEW in v1.1:
- Personal win rate weighting
- Matchup-specific learning (hero vs enemy performance)
- Confidence scoring based on games played
- Performance warnings for bad matchups
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

ReasonType = Literal["counter_strong", "counter_weak", "meta", "tier", "personal_wr", "matchup_history"]

@dataclass
class Reason:
    type: ReasonType
    delta: float
    detail: str

def render_explanation(reasons: List[Reason], max_reasons: int = 4) -> str:
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
class PersonalStats:
    """Personal performance statistics for a hero"""
    total_games: int
    wins: int
    losses: int
    win_rate: float
    confidence: str  # "high", "medium", "low", "none"
    
@dataclass
class MatchupStats:
    """Performance of hero vs specific enemy"""
    wins: int
    losses: int
    total: int
    win_rate: float

@dataclass
class PickResult:
    hero: str
    score: float
    strong_hits: List[str]
    weak_hits: List[str]
    meta_bonus: float
    counter_bonus: float
    personal_bonus: float
    synergy_bonus: float  # NEW: For future teammate synergy feature
    reasons: List[Reason]
    explain: str
    early_tip: str
    personal_stats: Optional[PersonalStats]
    matchup_warnings: List[str]  # List of enemy heroes you struggle against
    synergy_hits: List[str]  # NEW: Teammates this hero synergizes with


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

        # Default weights
        self.w = {
            "strong_hit": 1.25,
            "weak_hit": -1.25,
            "win": 0.18,
            "pick": 0.02,
            "ban": 0.05,
            "tier": 0.75,
            # NEW: Personal performance weights
            "personal_wr": 0.08,  # Weight for personal win rate deviation from 50%
            "matchup_win": 1.5,   # Bonus for winning matchup history
            "matchup_loss": -1.8, # Penalty for losing matchup history
            "min_games_confidence": 5,  # Minimum games for high confidence
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

    # ---------- personal performance queries ----------

    def _get_personal_stats(self, hero: str) -> PersonalStats:
        """Get overall personal stats for a hero"""
        try:
            self.cur.execute("""
                SELECT 
                    COUNT(*) as total_games,
                    SUM(CASE WHEN result = 'Win' THEN 1 ELSE 0 END) as wins
                FROM game_history
                WHERE your_hero = ?
            """, (hero,))
            
            row = self.cur.fetchone()
            if row and row[0] > 0:
                total, wins = row[0], row[1] or 0
                losses = total - wins
                win_rate = (wins / total * 100) if total > 0 else 0
                
                # Confidence levels
                if total >= self.w["min_games_confidence"]:
                    confidence = "high"
                elif total >= 3:
                    confidence = "medium"
                elif total >= 1:
                    confidence = "low"
                else:
                    confidence = "none"
                
                return PersonalStats(
                    total_games=total,
                    wins=wins,
                    losses=losses,
                    win_rate=win_rate,
                    confidence=confidence
                )
        except sqlite3.OperationalError:
            # Table doesn't exist yet
            pass
        
        return PersonalStats(0, 0, 0, 0.0, "none")

    def _get_matchup_stats(self, hero: str, enemy: str) -> Optional[MatchupStats]:
        """Get specific matchup history (hero vs enemy)"""
        try:
            self.cur.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN result = 'Win' THEN 1 ELSE 0 END) as wins
                FROM game_history
                WHERE your_hero = ?
                  AND enemies LIKE ?
            """, (hero, f'%"{enemy}"%'))
            
            row = self.cur.fetchone()
            if row and row[0] > 0:
                total, wins = row[0], row[1] or 0
                losses = total - wins
                win_rate = (wins / total * 100) if total > 0 else 0
                
                return MatchupStats(
                    wins=wins,
                    losses=losses,
                    total=total,
                    win_rate=win_rate
                )
        except sqlite3.OperationalError:
            pass
        
        return None

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

    # ---------- personal performance scoring ----------

    def _personal_bonus_and_reasons(
        self, 
        hero: str, 
        enemies: List[str],
        personal_stats: PersonalStats
    ) -> Tuple[float, List[Reason], List[str]]:
        """Calculate bonus/penalty based on personal performance"""
        reasons: List[Reason] = []
        warnings: List[str] = []
        total_bonus = 0.0
        
        # 1. Overall win rate adjustment
        if personal_stats.total_games >= 3:  # Need at least 3 games
            wr_deviation = personal_stats.win_rate - 50.0
            wr_bonus = wr_deviation * self.w["personal_wr"]
            total_bonus += wr_bonus
            
            if abs(wr_bonus) > 0.1:
                confidence_emoji = {
                    "high": "⭐⭐⭐",
                    "medium": "⭐⭐",
                    "low": "⭐",
                    "none": ""
                }
                reasons.append(
                    Reason(
                        "personal_wr",
                        wr_bonus,
                        f"Your WR: {personal_stats.win_rate:.1f}% ({personal_stats.total_games}g) {confidence_emoji[personal_stats.confidence]}"
                    )
                )
        
        # 2. Matchup-specific history
        for enemy in enemies:
            matchup = self._get_matchup_stats(hero, enemy)
            if matchup and matchup.total >= 2:  # Need at least 2 games vs this enemy
                if matchup.win_rate >= 60.0:
                    # Good matchup history
                    bonus = self.w["matchup_win"]
                    total_bonus += bonus
                    reasons.append(
                        Reason(
                            "matchup_history",
                            bonus,
                            f"Strong vs {enemy}: {matchup.wins}-{matchup.losses} in your games"
                        )
                    )
                elif matchup.win_rate <= 40.0:
                    # Bad matchup history
                    penalty = self.w["matchup_loss"]
                    total_bonus += penalty
                    reasons.append(
                        Reason(
                            "matchup_history",
                            penalty,
                            f"Weak vs {enemy}: {matchup.wins}-{matchup.losses} in your games"
                        )
                    )
                    warnings.append(f"⚠️ You're {matchup.wins}-{matchup.losses} vs {enemy}")
        
        return total_bonus, reasons, warnings

    # ---------- recommend ----------

    def recommend(
        self,
        pool: List[str],
        enemies: List[str],
        teammates: Optional[List[str]] = None,  # NEW: For future synergy feature
        base_score: float = 5.0,
        top_n: int = 10,
        max_reasons: int = 4,
        use_inverse: bool = True,
        use_personal: bool = True,  # Toggle personal performance
        use_synergy: bool = False,  # NEW: Toggle synergy (not implemented yet)
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

            # 1. Counter analysis (direct hits)
            strong_direct = self._get_relation_hits(hero, db_enemies, "strong_against")
            weak_direct = self._get_relation_hits(hero, db_enemies, "weak_against")

            # 2. Inverse hits (enemy -> hero)
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

            # Add counter reasons
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
                        f"Strong vs {', '.join(strong_hits[:2])}{'...' if len(strong_hits) > 2 else ''}"
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
                        f"Weak vs {', '.join(weak_hits[:2])}{'...' if len(weak_hits) > 2 else ''}"
                    )
                )

            # 3. Meta bonus
            meta_bonus, meta_reasons = self._meta_bonus_and_reasons(hero)
            reasons.extend(meta_reasons)

            # 4. Personal performance bonus
            personal_bonus = 0.0
            warnings: List[str] = []
            personal_stats = None
            
            if use_personal:
                personal_stats = self._get_personal_stats(hero)
                personal_bonus, personal_reasons, warnings = self._personal_bonus_and_reasons(
                    hero, db_enemies, personal_stats
                )
                reasons.extend(personal_reasons)

            # 5. Synergy bonus (placeholder for future implementation)
            synergy_bonus = 0.0
            synergy_hits: List[str] = []
            # TODO: Implement synergy calculation
            # if use_synergy and teammates:
            #     synergy_bonus, synergy_reasons, synergy_hits = self._synergy_bonus_and_reasons(hero, teammates)
            #     reasons.extend(synergy_reasons)

            # 6. Get tips
            m_data = self.resolve_meta_entry(hero) or {}
            tip = m_data.get("early_tips") or m_data.get("early_tip") or "Tactical analysis pending."

            # 7. Calculate final score
            score = base_score + counter_bonus + meta_bonus + personal_bonus + synergy_bonus
            explain = render_explanation(reasons, max_reasons=max_reasons)

            results.append(
                PickResult(
                    hero=hero,
                    score=round(score, 3),
                    strong_hits=strong_hits,
                    weak_hits=weak_hits,
                    meta_bonus=round(meta_bonus, 3),
                    counter_bonus=round(counter_bonus, 3),
                    personal_bonus=round(personal_bonus, 3),
                    synergy_bonus=round(synergy_bonus, 3),
                    reasons=reasons,
                    explain=explain,
                    early_tip=tip,
                    personal_stats=personal_stats,
                    matchup_warnings=warnings,
                    synergy_hits=synergy_hits,
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

    res = engine.recommend(pool=pool, enemies=enemies, top_n=10, use_inverse=True, use_personal=True)

    print("ENEMIES:", enemies)
    print("POOL:", pool)
    print("\nRESULTS:")
    for r in res:
        print(f"{r.hero:<12} score={r.score:<6} counter={r.counter_bonus:<6} meta={r.meta_bonus:<6} personal={r.personal_bonus:<6}")
        print(f"  strong_hits: {r.strong_hits}")
        print(f"  weak_hits:   {r.weak_hits}")
        if r.personal_stats and r.personal_stats.total_games > 0:
            print(f"  your stats:  {r.personal_stats.wins}-{r.personal_stats.losses} ({r.personal_stats.win_rate:.1f}% WR, {r.personal_stats.confidence} confidence)")
        if r.matchup_warnings:
            for w in r.matchup_warnings:
                print(f"  {w}")
        print(f"  why: {r.explain}")
        print(f"  tip: {r.early_tip}\n")

    engine.close()