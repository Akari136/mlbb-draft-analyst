from __future__ import annotations

import os
import sqlite3
from typing import List
import streamlit as st
from draft_engine import DraftEngine


# -----------------------------
# Config
# -----------------------------
st.set_page_config(page_title="⚔️ MLBB Draft Analyst", page_icon="⚔️", layout="wide")
st.title("⚔️ MLBB Draft Analyst")
st.caption("Counter DB + Meta Weighting + Dynamic Explanations + Pro Tips")

DEFAULT_DB = "mlcounter.db"
DEFAULT_META = "meta.json"


# -----------------------------
# Utilities
# -----------------------------
@st.cache_data(show_spinner=False)
def db_hero_list(db_path: str) -> List[str]:
    if not os.path.exists(db_path):
        return []
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        cur.execute("SELECT hero FROM heroes ORDER BY hero COLLATE NOCASE;")
        return [r[0] for r in cur.fetchall()]
    finally:
        conn.close()

def pick_default_pool(hero_list: List[str], candidates: List[str]) -> List[str]:
    s = set(hero_list)
    return [h for h in candidates if h in s]


# -----------------------------
# Sidebar
# -----------------------------
with st.sidebar:
    st.header("Data Sources")
    db_path = st.text_input("DB path", value=DEFAULT_DB)
    meta_path = st.text_input("Meta JSON path", value=DEFAULT_META)

    st.divider()
    st.header("Draft Calibration")
    base_score = st.number_input("Base score", value=5.0, step=0.5)
    top_n = st.slider("Top N results", min_value=3, max_value=20, value=10)

    use_inverse = st.checkbox("Use inverse counter inference (recommended)", value=True)

    st.subheader("Weights")
    strong_hit = st.number_input("Strong hit (+)", value=1.25, step=0.1)
    weak_hit = st.number_input("Weak hit (-)", value=-1.25, step=0.1)

    win_w = st.number_input("Win weight", value=0.18, step=0.01)
    pick_w = st.number_input("Pick weight", value=0.02, step=0.01)
    ban_w = st.number_input("Ban weight", value=0.05, step=0.01)
    tier_w = st.number_input("Tier weight", value=0.75, step=0.05)

weights = {
    "strong_hit": float(strong_hit),
    "weak_hit": float(weak_hit),
    "win": float(win_w),
    "pick": float(pick_w),
    "ban": float(ban_w),
    "tier": float(tier_w),
}


# -----------------------------
# Hero Lists & Presets
# -----------------------------
heroes = db_hero_list(db_path)
if not heroes:
    st.error("No heroes found. Check your mlcounter.db path.")
    st.stop()

DEFAULT_POOLS = {
    "EXP Lane": ["Argus", "Lapulapu", "Terizla", "Yuzhong", "Martis", "Thamuz"],
    "Gold Lane": ["Brody", "Claude", "Harith", "Miya", "Wanwan"],
    "Jungler": ["Martis", "Fredrinn", "Nolan", "Ling"],
    "Roam": ["Atlas", "Khufra", "Diggie", "Kaja", "Akai", "Tigreal"],
    "Mid Lane": ["Valir", "Kadita", "Lylia", "Pharsa", "Yve"],
}


# -----------------------------
# Main UI
# -----------------------------
col_left, col_right = st.columns([1, 1], gap="large")

with col_left:
    st.subheader("1) Your Hero Pool")
    role = st.selectbox("Lane Preset", options=list(DEFAULT_POOLS.keys()), index=0)
    preset_pool = pick_default_pool(heroes, DEFAULT_POOLS.get(role, []))
    pool = st.multiselect("Active Pool", options=heroes, default=preset_pool)

with col_right:
    st.subheader("2) Enemy Team")
    enemies = st.multiselect("Enemy Picks", options=heroes, default=[])
    avoid = st.multiselect("Banned/Teammate Locked", options=heroes, default=[])

st.divider()


# -----------------------------
# Run engine
# -----------------------------
if st.button("🚀 Run Draft Analysis", type="primary", use_container_width=True):
    if not pool:
        st.warning("Please select at least one hero for your pool.")
        st.stop()

    final_pool = [h for h in pool if h not in set(avoid)]

    engine = DraftEngine(db_path=db_path, meta_path=meta_path, weights=weights)
    try:
        if not engine.meta:
            st.warning("meta.json not loaded/found. Meta bonuses will be 0.")

        results = engine.recommend(
            pool=final_pool,
            enemies=enemies,
            base_score=float(base_score),
            top_n=int(top_n),
            use_inverse=use_inverse,
        )

        st.subheader("Analysis Results")
        for i, r in enumerate(results, start=1):
            with st.container(border=True):
                c1, c2 = st.columns([3, 1])
                with c1:
                    st.markdown(f"### #{i} {r.hero}")
                    st.markdown(f"**Reasoning:** {r.explain}")
                    st.info(f"💡 **Pro-Tip:** {r.early_tip}")
                with c2:
                    st.metric("Engine Score", f"{r.score:.2f}")

                with st.expander("Technical Breakdown"):
                    st.write(f"Counter bonus: {r.counter_bonus:+.2f}")
                    st.write(f"Meta bonus: {r.meta_bonus:+.2f}")
                    st.write(f"Strong hits: {', '.join(r.strong_hits) if r.strong_hits else 'None'}")
                    st.write(f"Weak hits: {', '.join(r.weak_hits) if r.weak_hits else 'None'}")

    except Exception as e:
        st.error(f"Engine Error: {e}")
    finally:
        engine.close()
