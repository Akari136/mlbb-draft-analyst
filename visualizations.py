"""
Enhanced Game History visualizations for Phase 2
Adds charts, graphs, and visual insights
"""

import streamlit as st
import sqlite3
import json
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from typing import List, Dict, Optional


def create_win_rate_chart_data(db_path: str, days: int = 30) -> Dict:
    """Generate data for win rate over time chart"""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    cutoff_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
    
    cur.execute("""
        SELECT date, result
        FROM game_history
        WHERE date >= ?
        ORDER BY date ASC
    """, (cutoff_date,))
    
    rows = cur.fetchall()
    conn.close()
    
    if not rows:
        return {"dates": [], "win_rates": [], "game_counts": []}
    
    # Calculate rolling win rate
    dates = []
    win_rates = []
    game_counts = []
    
    wins = 0
    total = 0
    
    for date, result in rows:
        total += 1
        if result == "Win":
            wins += 1
        
        dates.append(date)
        win_rates.append((wins / total * 100) if total > 0 else 0)
        game_counts.append(total)
    
    return {
        "dates": dates,
        "win_rates": win_rates,
        "game_counts": game_counts
    }


def create_hero_performance_data(db_path: str, min_games: int = 3) -> List[Dict]:
    """Generate hero performance comparison data"""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    cur.execute("""
        SELECT 
            your_hero,
            COUNT(*) as total_games,
            SUM(CASE WHEN result = 'Win' THEN 1 ELSE 0 END) as wins,
            AVG(kills) as avg_kills,
            AVG(deaths) as avg_deaths,
            AVG(assists) as avg_assists
        FROM game_history
        GROUP BY your_hero
        HAVING total_games >= ?
        ORDER BY total_games DESC
    """, (min_games,))
    
    rows = cur.fetchall()
    conn.close()
    
    heroes = []
    for row in rows:
        hero, total, wins, kills, deaths, assists = row
        heroes.append({
            'hero': hero,
            'total_games': total,
            'wins': wins,
            'losses': total - wins,
            'win_rate': (wins / total * 100) if total > 0 else 0,
            'avg_kills': kills or 0,
            'avg_deaths': deaths or 0,
            'avg_assists': assists or 0,
            'kda': ((kills or 0) + (assists or 0)) / max(deaths or 1, 1)
        })
    
    return heroes


def create_role_distribution_data(db_path: str) -> Dict:
    """Get role play frequency"""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    cur.execute("""
        SELECT your_role, COUNT(*) as count
        FROM game_history
        GROUP BY your_role
        ORDER BY count DESC
    """)
    
    rows = cur.fetchall()
    conn.close()
    
    return {role: count for role, count in rows if role}


def create_enemy_encounter_data(db_path: str, top_n: int = 10) -> List[Dict]:
    """Get most faced enemies with win rates"""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    cur.execute("""
        SELECT enemies, result
        FROM game_history
        WHERE enemies IS NOT NULL
    """)
    
    rows = cur.fetchall()
    conn.close()
    
    enemy_stats = defaultdict(lambda: {'wins': 0, 'losses': 0})
    
    for row in rows:
        enemies = json.loads(row['enemies']) if row['enemies'] else []
        result = row['result']
        
        for enemy in enemies:
            if result == 'Win':
                enemy_stats[enemy]['wins'] += 1
            else:
                enemy_stats[enemy]['losses'] += 1
    
    # Convert to list and calculate win rates
    enemy_list = []
    for enemy, stats in enemy_stats.items():
        total = stats['wins'] + stats['losses']
        if total >= 2:  # Minimum 2 encounters
            enemy_list.append({
                'enemy': enemy,
                'total': total,
                'wins': stats['wins'],
                'losses': stats['losses'],
                'win_rate': (stats['wins'] / total * 100) if total > 0 else 0
            })
    
    # Sort by total encounters
    enemy_list.sort(key=lambda x: x['total'], reverse=True)
    return enemy_list[:top_n]


def create_performance_heatmap_data(db_path: str) -> Dict:
    """Create day-of-week performance data"""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    cur.execute("""
        SELECT date, result
        FROM game_history
        ORDER BY date ASC
    """)
    
    rows = cur.fetchall()
    conn.close()
    
    day_stats = defaultdict(lambda: {'wins': 0, 'losses': 0})
    
    for date_str, result in rows:
        try:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            day_name = date_obj.strftime('%A')  # Monday, Tuesday, etc.
            
            if result == 'Win':
                day_stats[day_name]['wins'] += 1
            else:
                day_stats[day_name]['losses'] += 1
        except:
            continue
    
    # Convert to structured format
    days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    heatmap_data = []
    
    for day in days_order:
        stats = day_stats[day]
        total = stats['wins'] + stats['losses']
        heatmap_data.append({
            'day': day,
            'total': total,
            'wins': stats['wins'],
            'losses': stats['losses'],
            'win_rate': (stats['wins'] / total * 100) if total > 0 else 0
        })
    
    return heatmap_data


def render_hero_comparison_chart(heroes_data: List[Dict]):
    """Render hero performance comparison using Streamlit native charts"""
    import pandas as pd
    
    if not heroes_data:
        st.info("Play at least 3 games with a hero to see comparison charts")
        return
    
    # Win Rate Comparison
    st.subheader("📊 Hero Win Rate Comparison")
    df_wr = pd.DataFrame([
        {'Hero': h['hero'], 'Win Rate (%)': h['win_rate']} 
        for h in heroes_data
    ])
    st.bar_chart(df_wr.set_index('Hero'))
    
    # Games Played
    st.subheader("🎮 Games Played per Hero")
    df_games = pd.DataFrame([
        {'Hero': h['hero'], 'Games': h['total_games']} 
        for h in heroes_data
    ])
    st.bar_chart(df_games.set_index('Hero'))
    
    # KDA Comparison
    st.subheader("⚔️ Average KDA")
    df_kda = pd.DataFrame([
        {
            'Hero': h['hero'],
            'Kills': h['avg_kills'],
            'Deaths': h['avg_deaths'],
            'Assists': h['avg_assists']
        }
        for h in heroes_data
    ])
    st.bar_chart(df_kda.set_index('Hero'))


def render_win_rate_trend(chart_data: Dict):
    """Render win rate over time"""
    import pandas as pd
    
    if not chart_data['dates']:
        st.info("Play more games to see trends over time")
        return
    
    st.subheader("📈 Win Rate Trend")
    
    df = pd.DataFrame({
        'Date': chart_data['dates'],
        'Win Rate (%)': chart_data['win_rates']
    })
    
    st.line_chart(df.set_index('Date'))
    
    # Show stats
    col1, col2, col3 = st.columns(3)
    with col1:
        current_wr = chart_data['win_rates'][-1] if chart_data['win_rates'] else 0
        st.metric("Current Win Rate", f"{current_wr:.1f}%")
    with col2:
        total_games = chart_data['game_counts'][-1] if chart_data['game_counts'] else 0
        st.metric("Total Games", total_games)
    with col3:
        if len(chart_data['win_rates']) >= 2:
            recent_wr = chart_data['win_rates'][-1]
            old_wr = chart_data['win_rates'][0]
            trend = recent_wr - old_wr
            st.metric("Trend", f"{trend:+.1f}%", delta=f"{trend:+.1f}%")


def render_role_distribution(role_data: Dict):
    """Render role distribution pie chart"""
    import pandas as pd
    
    if not role_data:
        st.info("Log games with role information to see distribution")
        return
    
    st.subheader("🎭 Role Distribution")
    
    df = pd.DataFrame([
        {'Role': role, 'Games': count}
        for role, count in role_data.items()
    ])
    
    st.bar_chart(df.set_index('Role'))
    
    # Show percentages
    total = sum(role_data.values())
    cols = st.columns(len(role_data))
    for idx, (role, count) in enumerate(role_data.items()):
        with cols[idx]:
            pct = (count / total * 100) if total > 0 else 0
            st.metric(role, f"{pct:.1f}%", f"{count} games")


def render_enemy_matchup_chart(enemy_data: List[Dict]):
    """Render enemy encounter statistics"""
    import pandas as pd
    
    if not enemy_data:
        st.info("Play more games to see enemy matchup data")
        return
    
    st.subheader("👥 Most Faced Enemies")
    
    df = pd.DataFrame([
        {
            'Enemy': e['enemy'],
            'Win Rate (%)': e['win_rate'],
            'Total': e['total']
        }
        for e in enemy_data
    ])
    
    st.bar_chart(df.set_index('Enemy')['Win Rate (%)'])
    
    # Detailed table
    with st.expander("📋 Detailed Enemy Stats"):
        for enemy in enemy_data:
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                st.write(f"**{enemy['enemy']}**")
            with col2:
                st.write(f"{enemy['wins']}W - {enemy['losses']}L")
            with col3:
                color = "🟢" if enemy['win_rate'] >= 50 else "🔴"
                st.write(f"{color} {enemy['win_rate']:.1f}%")


def render_day_performance(heatmap_data: List[Dict]):
    """Render day-of-week performance"""
    import pandas as pd
    
    if not heatmap_data or all(d['total'] == 0 for d in heatmap_data):
        st.info("Play games throughout the week to see performance patterns")
        return
    
    st.subheader("📅 Performance by Day of Week")
    
    # Filter days with games
    days_with_games = [d for d in heatmap_data if d['total'] > 0]
    
    if days_with_games:
        df = pd.DataFrame([
            {'Day': d['day'], 'Win Rate (%)': d['win_rate']}
            for d in days_with_games
        ])
        
        st.bar_chart(df.set_index('Day'))
        
        # Find best/worst days
        best_day = max(days_with_games, key=lambda x: x['win_rate'])
        worst_day = min(days_with_games, key=lambda x: x['win_rate'])
        
        col1, col2 = st.columns(2)
        with col1:
            st.success(f"🌟 Best: {best_day['day']} ({best_day['win_rate']:.1f}%)")
        with col2:
            st.error(f"📉 Worst: {worst_day['day']} ({worst_day['win_rate']:.1f}%)")