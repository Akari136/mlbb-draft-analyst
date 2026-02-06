from __future__ import annotations

import os
import sqlite3
import json
from datetime import datetime
from typing import List, Optional
import streamlit as st
from draft_engine import DraftEngine


# -----------------------------
# Config
# -----------------------------
st.set_page_config(page_title="⚔️ MLBB Draft Analyst", page_icon="⚔️", layout="wide")

DEFAULT_DB = "mlcounter.db"
DEFAULT_META = "meta.json"


# -----------------------------
# Database Utilities
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

def ensure_game_history_table(db_path: str):
    """Ensure game_history table exists"""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    cur.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name='game_history'
    """)
    
    if not cur.fetchone():
        cur.execute("""
            CREATE TABLE game_history (
                game_id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                your_hero TEXT NOT NULL,
                your_role TEXT,
                teammates TEXT,
                enemies TEXT NOT NULL,
                result TEXT NOT NULL,
                mvp_status TEXT,
                kills INTEGER,
                deaths INTEGER,
                assists INTEGER,
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
    
    conn.close()

def log_game(db_path: str, game_data: dict):
    """Insert a game record into the database"""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    cur.execute("""
        INSERT INTO game_history 
        (date, your_hero, your_role, teammates, enemies, result, 
         mvp_status, kills, deaths, assists, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        game_data['date'],
        game_data['your_hero'],
        game_data['your_role'],
        json.dumps(game_data['teammates']),
        json.dumps(game_data['enemies']),
        game_data['result'],
        game_data.get('mvp_status'),
        game_data.get('kills'),
        game_data.get('deaths'),
        game_data.get('assists'),
        game_data.get('notes', '')
    ))
    
    conn.commit()
    conn.close()

def get_game_history(db_path: str, limit: int = 50) -> List[dict]:
    """Retrieve game history"""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    cur.execute("""
        SELECT * FROM game_history 
        ORDER BY date DESC, game_id DESC 
        LIMIT ?
    """, (limit,))
    
    rows = cur.fetchall()
    conn.close()
    
    games = []
    for row in rows:
        game = dict(row)
        game['teammates'] = json.loads(game['teammates']) if game['teammates'] else []
        game['enemies'] = json.loads(game['enemies']) if game['enemies'] else []
        games.append(game)
    
    return games

def get_hero_stats(db_path: str, hero: Optional[str] = None) -> dict:
    """Get win rate and performance stats for a hero"""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    if hero:
        cur.execute("""
            SELECT 
                COUNT(*) as total_games,
                SUM(CASE WHEN result = 'Win' THEN 1 ELSE 0 END) as wins,
                AVG(kills) as avg_kills,
                AVG(deaths) as avg_deaths,
                AVG(assists) as avg_assists
            FROM game_history
            WHERE your_hero = ?
        """, (hero,))
    else:
        cur.execute("""
            SELECT 
                COUNT(*) as total_games,
                SUM(CASE WHEN result = 'Win' THEN 1 ELSE 0 END) as wins,
                AVG(kills) as avg_kills,
                AVG(deaths) as avg_deaths,
                AVG(assists) as avg_assists
            FROM game_history
        """)
    
    row = cur.fetchone()
    conn.close()
    
    if row and row[0] > 0:
        total, wins = row[0], row[1] or 0
        return {
            'total_games': total,
            'wins': wins,
            'losses': total - wins,
            'win_rate': (wins / total * 100) if total > 0 else 0,
            'avg_kills': row[2] or 0,
            'avg_deaths': row[3] or 0,
            'avg_assists': row[4] or 0,
        }
    return {
        'total_games': 0,
        'wins': 0,
        'losses': 0,
        'win_rate': 0,
        'avg_kills': 0,
        'avg_deaths': 0,
        'avg_assists': 0,
    }

def delete_game(db_path: str, game_id: int):
    """Delete a game record"""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("DELETE FROM game_history WHERE game_id = ?", (game_id,))
    conn.commit()
    conn.close()


# -----------------------------
# Initialize
# -----------------------------
# Sidebar for navigation
st.sidebar.title("📱 Navigation")
page = st.sidebar.radio(
    "Choose a page:",
    ["🎯 Draft Analysis", "📝 Log Game", "📊 Game History", "⚙️ Settings"]
)

st.sidebar.divider()

# Data source config
st.sidebar.header("Data Sources")
db_path = st.sidebar.text_input("DB path", value=DEFAULT_DB)
meta_path = st.sidebar.text_input("Meta JSON path", value=DEFAULT_META)

# Ensure game history table exists
ensure_game_history_table(db_path)

# Load heroes
heroes = db_hero_list(db_path)
if not heroes:
    st.error("No heroes found. Check your mlcounter.db path.")
    st.stop()


# -----------------------------
# Hero Pool Presets
# -----------------------------
DEFAULT_POOLS = {
    "EXP Lane": ["Argus", "Lapulapu", "Terizla", "Yuzhong", "Martis", "Thamuz"],
    "Gold Lane": ["Brody", "Claude", "Harith", "Miya", "Wanwan"],
    "Jungler": ["Martis", "Fredrinn", "Nolan", "Ling"],
    "Roam": ["Atlas", "Khufra", "Diggie", "Kaja", "Akai", "Tigreal"],
    "Mid Lane": ["Valir", "Kadita", "Lylia", "Pharsa", "Yve"],
}


# =============================
# PAGE: DRAFT ANALYSIS
# =============================
if page == "🎯 Draft Analysis":
    st.title("⚔️ MLBB Draft Analyst")
    st.caption("Counter DB + Meta Weighting + Dynamic Explanations + Pro Tips")
    
    # Settings in sidebar
    with st.sidebar:
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
        
        st.subheader("Personal Performance Weights")
        personal_wr_w = st.number_input("Personal WR weight", value=0.08, step=0.01,
                                        help="Weight for your personal win rate deviation from 50%")
        matchup_win_w = st.number_input("Good matchup bonus", value=1.5, step=0.1,
                                       help="Bonus when you have 60%+ WR vs enemy")
        matchup_loss_w = st.number_input("Bad matchup penalty", value=-1.8, step=0.1,
                                        help="Penalty when you have <40% WR vs enemy")
        min_games = st.number_input("Min games for confidence", value=5, step=1,
                                   help="Minimum games for high confidence rating")

    weights = {
        "strong_hit": float(strong_hit),
        "weak_hit": float(weak_hit),
        "win": float(win_w),
        "pick": float(pick_w),
        "ban": float(ban_w),
        "tier": float(tier_w),
        "personal_wr": float(personal_wr_w),
        "matchup_win": float(matchup_win_w),
        "matchup_loss": float(matchup_loss_w),
        "min_games_confidence": int(min_games),
    }

    # Main UI
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

    # Toggle for personal performance
    use_personal = st.checkbox("Use personal performance data", value=True, 
                               help="Adjust recommendations based on your game history")
    
    # Run Analysis
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
                use_personal=use_personal,
            )

            st.subheader("Analysis Results")
            for i, r in enumerate(results, start=1):
                with st.container(border=True):
                    c1, c2, c3 = st.columns([3, 1, 1])
                    with c1:
                        st.markdown(f"### #{i} {r.hero}")
                        
                        # Show matchup warnings prominently
                        if r.matchup_warnings:
                            for warning in r.matchup_warnings:
                                st.warning(warning)
                        
                        st.markdown(f"**Reasoning:** {r.explain}")
                        st.info(f"💡 **Pro-Tip:** {r.early_tip}")
                    with c2:
                        st.metric("Engine Score", f"{r.score:.2f}")
                    with c3:
                        if r.personal_stats and r.personal_stats.total_games > 0:
                            # Show confidence indicator
                            conf_emoji = {
                                "high": "⭐⭐⭐",
                                "medium": "⭐⭐",
                                "low": "⭐",
                                "none": ""
                            }
                            delta_color = "normal"
                            if r.personal_stats.win_rate >= 55:
                                delta_color = "normal"
                            elif r.personal_stats.win_rate <= 45:
                                delta_color = "inverse"
                            
                            st.metric(
                                "Your Win Rate", 
                                f"{r.personal_stats.win_rate:.1f}%",
                                f"{r.personal_stats.total_games}g {conf_emoji[r.personal_stats.confidence]}",
                                delta_color=delta_color
                            )
                        else:
                            st.caption("No personal history")

                    with st.expander("Technical Breakdown"):
                        col_a, col_b = st.columns(2)
                        with col_a:
                            st.write(f"**Counter bonus:** {r.counter_bonus:+.2f}")
                            st.write(f"**Meta bonus:** {r.meta_bonus:+.2f}")
                            st.write(f"**Personal bonus:** {r.personal_bonus:+.2f}")
                            st.write(f"**Strong hits:** {', '.join(r.strong_hits) if r.strong_hits else 'None'}")
                            st.write(f"**Weak hits:** {', '.join(r.weak_hits) if r.weak_hits else 'None'}")
                        with col_b:
                            if r.personal_stats and r.personal_stats.total_games > 0:
                                st.write(f"**Personal Record:** {r.personal_stats.wins}W - {r.personal_stats.losses}L")
                                st.write(f"**Confidence:** {r.personal_stats.confidence.title()}")
                                
                                # Show matchup details
                                if enemies:
                                    st.write("**Matchup History:**")
                                    for enemy in enemies:
                                        matchup = engine._get_matchup_stats(r.hero, enemy)
                                        if matchup and matchup.total > 0:
                                            emoji = "✅" if matchup.win_rate >= 50 else "❌"
                                            st.caption(f"{emoji} vs {enemy}: {matchup.wins}-{matchup.losses}")
                            else:
                                st.caption("Play some games to build matchup history!")

        except Exception as e:
            st.error(f"Engine Error: {e}")
            import traceback
            st.code(traceback.format_exc())
        finally:
            engine.close()


# =============================
# PAGE: LOG GAME
# =============================
elif page == "📝 Log Game":
    st.title("📝 Log Game")
    st.caption("Record your match results to build performance history")
    
    with st.form("log_game_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            game_date = st.date_input("Game Date", value=datetime.now())
            your_hero = st.selectbox("Your Hero", options=heroes)
            your_role = st.selectbox("Your Role", options=list(DEFAULT_POOLS.keys()))
            result = st.selectbox("Result", options=["Win", "Loss"])
        
        with col2:
            mvp_status = st.selectbox("MVP Status", options=["None", "MVP", "Gold Medal", "Silver Medal"])
            kills = st.number_input("Kills", min_value=0, value=0, step=1)
            deaths = st.number_input("Deaths", min_value=0, value=0, step=1)
            assists = st.number_input("Assists", min_value=0, value=0, step=1)
        
        st.subheader("Team Composition")
        teammates = st.multiselect("Teammates (4 heroes)", options=heroes, max_selections=4)
        enemies = st.multiselect("Enemy Team (5 heroes)", options=heroes, max_selections=5)
        
        notes = st.text_area("Notes (optional)", placeholder="Any observations about the game...")
        
        submitted = st.form_submit_button("💾 Save Game", type="primary", use_container_width=True)
        
        if submitted:
            if not enemies:
                st.error("Please select at least one enemy hero")
            else:
                game_data = {
                    'date': game_date.strftime('%Y-%m-%d'),
                    'your_hero': your_hero,
                    'your_role': your_role,
                    'teammates': teammates,
                    'enemies': enemies,
                    'result': result,
                    'mvp_status': mvp_status if mvp_status != "None" else None,
                    'kills': kills,
                    'deaths': deaths,
                    'assists': assists,
                    'notes': notes
                }
                
                try:
                    log_game(db_path, game_data)
                    st.success(f"✅ Game logged successfully! ({result} with {your_hero})")
                    st.balloons()
                except Exception as e:
                    st.error(f"Error logging game: {e}")


# =============================
# PAGE: GAME HISTORY
# =============================
elif page == "📊 Game History":
    st.title("📊 Game History")
    
    # Overall stats
    overall_stats = get_hero_stats(db_path)
    
    if overall_stats['total_games'] > 0:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Games", overall_stats['total_games'])
        with col2:
            st.metric("Win Rate", f"{overall_stats['win_rate']:.1f}%")
        with col3:
            st.metric("Record", f"{overall_stats['wins']}W - {overall_stats['losses']}L")
        with col4:
            kda = (overall_stats['avg_kills'] + overall_stats['avg_assists']) / max(overall_stats['avg_deaths'], 1)
            st.metric("Avg KDA", f"{kda:.2f}")
        
        st.divider()
        
        # Hero-specific stats
        st.subheader("Hero Statistics")
        
        # Get all heroes you've played
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("""
            SELECT your_hero, COUNT(*) as games
            FROM game_history
            GROUP BY your_hero
            ORDER BY games DESC
        """)
        hero_game_counts = cur.fetchall()
        conn.close()
        
        if hero_game_counts:
            selected_hero = st.selectbox(
                "View stats for hero:",
                options=["All Heroes"] + [h[0] for h in hero_game_counts],
                format_func=lambda x: f"{x} ({dict(hero_game_counts).get(x, 0)} games)" if x != "All Heroes" else x
            )
            
            if selected_hero != "All Heroes":
                hero_stats = get_hero_stats(db_path, selected_hero)
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Games Played", hero_stats['total_games'])
                with col2:
                    st.metric("Win Rate", f"{hero_stats['win_rate']:.1f}%")
                with col3:
                    kda_val = (hero_stats['avg_kills'] + hero_stats['avg_assists']) / max(hero_stats['avg_deaths'], 1)
                    st.metric("Avg KDA", f"{kda_val:.2f}")
                
                st.caption(f"Avg: {hero_stats['avg_kills']:.1f} / {hero_stats['avg_deaths']:.1f} / {hero_stats['avg_assists']:.1f}")
        
        st.divider()
        
        # Recent games
        st.subheader("Recent Games")
        limit = st.slider("Show last N games", min_value=5, max_value=100, value=20, step=5)
        
        games = get_game_history(db_path, limit=limit)
        
        for game in games:
            result_color = "🟢" if game['result'] == "Win" else "🔴"
            kda_str = f"{game['kills']}/{game['deaths']}/{game['assists']}" if game['kills'] is not None else "N/A"
            
            with st.expander(f"{result_color} {game['date']} - {game['your_hero']} ({game['result']}) - KDA: {kda_str}"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**Role:** {game['your_role']}")
                    st.write(f"**Result:** {game['result']}")
                    if game['mvp_status']:
                        st.write(f"**MVP:** {game['mvp_status']}")
                    st.write(f"**KDA:** {kda_str}")
                
                with col2:
                    st.write(f"**Teammates:** {', '.join(game['teammates']) if game['teammates'] else 'None'}")
                    st.write(f"**Enemies:** {', '.join(game['enemies'])}")
                
                if game['notes']:
                    st.write(f"**Notes:** {game['notes']}")
                
                # Delete button
                if st.button(f"🗑️ Delete Game #{game['game_id']}", key=f"del_{game['game_id']}"):
                    delete_game(db_path, game['game_id'])
                    st.rerun()
    else:
        st.info("📭 No games logged yet. Head to the 'Log Game' page to start tracking your performance!")


# =============================
# PAGE: SETTINGS
# =============================
elif page == "⚙️ Settings":
    st.title("⚙️ Settings")
    
    st.subheader("Database Management")
    st.write(f"**Current Database:** `{db_path}`")
    st.write(f"**Meta File:** `{meta_path}`")
    
    total_games = get_hero_stats(db_path)['total_games']
    st.write(f"**Total Games Logged:** {total_games}")
    
    st.divider()
    
    st.subheader("Danger Zone")
    st.warning("⚠️ These actions cannot be undone!")
    
    if st.button("🗑️ Clear All Game History", type="secondary"):
        confirm = st.checkbox("I understand this will delete all my game history")
        if confirm:
            if st.button("⚠️ Confirm Delete All", type="secondary"):
                conn = sqlite3.connect(db_path)
                cur = conn.cursor()
                cur.execute("DELETE FROM game_history")
                conn.commit()
                conn.close()
                st.success("All game history deleted")
                st.rerun()