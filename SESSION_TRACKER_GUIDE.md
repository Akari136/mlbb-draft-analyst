# 🎮 Live Session Tracker - Integration Guide

## What You're Getting

**Live Draft Session Tracker** - A persistent sidebar that:
1. ✅ Tracks your draft in real-time
2. ✅ Updates as you add enemies/teammates
3. ✅ Locks in your hero pick
4. ✅ Opens completion modal after game
5. ✅ Auto-starts next session
6. ✅ Syncs with main game history

---

## 🎯 The Complete Workflow

```
┌─────────────────────────────────────────────────┐
│ Draft Analysis Page                             │
├─────────────────────────────────────────────────┤
│                                                 │
│  [Sidebar]                 [Main Content]       │
│  ┌──────────────┐         ┌────────────────┐   │
│  │ 📋 Live      │         │ Draft Analysis │   │
│  │ Session      │         │                │   │
│  │              │         │ Pool: [...]    │   │
│  │ 🟢 Session#1 │         │ Enemies: Alpha │◄──┤─ Auto-syncs
│  │              │         │ Teammates: ... │   │
│  │ Enemy Team:  │         │                │   │
│  │ 🔴 Alpha     │◄────────┼────────────────┘   │
│  │              │         │                    │
│  │ Your Team:   │         │ Recommendations:   │
│  │ 🔵 (empty)   │         │ #1 Thamuz 8.5     │
│  │              │         │    [✅ I Pick]    │◄─ Click!
│  │ ✅ Complete  │         │ #2 Fredrinn 7.8   │
│  │ ❌ Cancel    │         │    [✅ I Pick]    │
│  └──────────────┘         └────────────────────┘
│                                                 │
└─────────────────────────────────────────────────┘

         │
         │ Click "✅ I Pick Thamuz"
         ▼

┌─────────────────────────────────────────────────┐
│ [Sidebar Updates]                               │
│  ┌──────────────┐                               │
│  │ 📋 Session#1 │                               │
│  │              │                               │
│  │ ⚔️ Thamuz    │◄─── Your hero locked!        │
│  │ EXP Lane     │                               │
│  │              │                               │
│  │ Enemy: Alpha │                               │
│  │ Team: Brody  │                               │
│  └──────────────┘                               │
└─────────────────────────────────────────────────┘

         │
         │ ... Draft continues, game is played ...
         │
         │ Click "✅ Complete"
         ▼

┌─────────────────────────────────────────────────┐
│ 🏁 Complete Session Modal                       │
├─────────────────────────────────────────────────┤
│                                                 │
│  Thamuz vs Alpha, Kalea, Sun                    │
│                                                 │
│  Add Missing Heroes:                            │
│  ┌─────────────────┬─────────────────┐         │
│  │ Enemy Team:     │ Your Team:      │         │
│  │ ✓ Alpha         │ ✓ Brody         │         │
│  │ ✓ Kalea (draft) │ ✓ Valir (draft) │         │
│  │ ✓ Sun (draft)   │ + Add more...   │         │
│  │ + Add Vexana    │                 │         │
│  │ + Add Aldous    │                 │         │
│  └─────────────────┴─────────────────┘         │
│                                                 │
│  Game Result:                                   │
│  Result: [Win ▼]    KDA: 8 / 2 / 6             │
│  MVP: [Gold Medal]                              │
│                                                 │
│  Notes: _____________________________           │
│                                                 │
│  [💾 Save & Next Session] [↩️ Back to Game]    │
│                                                 │
└─────────────────────────────────────────────────┘

         │
         │ Click "💾 Save & Next Session"
         ▼

┌─────────────────────────────────────────────────┐
│  ✅ Session saved to game history!              │
│  🎮 Session #2 started automatically            │
│  🎈 [Balloons animation]                        │
└─────────────────────────────────────────────────┘
```

---

## 📦 Files You Got

1. **`session_tracker.py`** - Backend database logic
2. **`session_tracker_ui.py`** - Streamlit UI components
3. This guide!

---

## 🔧 Integration Steps

### Step 1: Add Files to Project

Put these files in your project folder:
```
your_project/
├── app.py
├── draft_engine.py
├── session_tracker.py          ← NEW!
├── session_tracker_ui.py       ← NEW!
├── mlcounter.db
└── ...
```

### Step 2: Update app.py

Find the **Draft Analysis** section (around line 240) and add:

```python
# At the top of app.py, with other imports:
from session_tracker_ui import (
    render_session_sidebar,
    render_complete_session_modal,
    add_pick_hero_button,
    sync_session_with_draft_inputs
)
from session_tracker import SessionTracker

# Initialize session state
if 'show_complete_modal' not in st.session_state:
    st.session_state.show_complete_modal = False
```

### Step 3: Add Session Sidebar

Right after the Draft Analysis page title:

```python
if page == "🎯 Draft Analysis":
    st.title("⚔️ MLBB Draft Analyst")
    st.caption("Counter DB + Meta Weighting + Live Session Tracking")
    
    # NEW: Render live session sidebar
    render_session_sidebar(db_path)
    
    # NEW: Check if completing session
    tracker = SessionTracker(db_path)
    if st.session_state.get('show_complete_modal') and st.session_state.get('active_session_id'):
        session = tracker.get_session(st.session_state.active_session_id)
        if session:
            render_complete_session_modal(tracker, session, heroes)
            st.stop()  # Don't render rest of page while modal is open
    
    # ... rest of draft analysis code
```

### Step 4: Sync Draft Inputs

After the user selects enemies/teammates (around line 330):

```python
    with col_right:
        st.subheader("2) Draft Context")
        
        st.caption("Enemy Team")
        enemies = st.multiselect("Enemy Picks", options=heroes, default=[])
        
        st.caption("Your Team")
        teammates = st.multiselect("Teammate Picks", options=heroes, default=[])
        
        st.caption("Unavailable")
        banned = st.multiselect("Banned Heroes", options=heroes, default=[])
        
        # NEW: Sync with active session
        sync_session_with_draft_inputs(db_path, enemies, teammates, banned)
```

### Step 5: Add "I Pick This" Buttons

In the results display (around line 370):

```python
            for i, r in enumerate(results, start=1):
                with st.container(border=True):
                    c1, c2, c3 = st.columns([3, 1, 1])
                    with c1:
                        st.markdown(f"### #{i} {r.hero}")
                        # ... hero details
                    
                    with c2:
                        st.metric("Engine Score", f"{r.score:.2f}")
                    
                    with c3:
                        # Existing metric
                        if r.personal_stats:
                            st.metric("Your Win Rate", ...)
                        
                        # NEW: Add pick button
                        add_pick_hero_button(r.hero, your_role, db_path)
```

---

## 🎮 How to Use

### Starting a Session

1. Open Draft Analysis page
2. Click **"🎮 Start New Session"** in sidebar
3. Green panel appears: "🟢 Session #1 Active"

### During Draft

1. Add enemies as they pick → Syncs to session automatically
2. Add teammates as they pick → Syncs automatically
3. When it's your turn, click **"✅ I Pick [Hero]"** on your chosen hero
4. Hero gets locked in the session panel
5. Continue adding enemies/teammates as draft continues

### After the Game

1. Click **"✅ Complete"** in session panel
2. Modal opens with pre-filled data
3. Add any missing enemies/teammates (draft completed)
4. Fill in: Result, KDA, MVP, Notes
5. Click **"💾 Save & Next Session"**
6. 🎈 Balloons! Game saved, new session auto-starts!

### Canceling a Session

Click **"❌ Cancel"** if you don't want to track this game

---

## 🎯 Key Features

### Auto-Sync
- Enemies/teammates you add in draft inputs automatically sync to session
- No duplicate data entry!

### Hero Lock
- Once you click "I Pick [Hero]", it's locked
- Can't accidentally change it

### Smart Pre-fill
- Modal shows what you already entered during draft
- Just add what's missing + game results

### Next Session
- Immediately starts new session after saving
- Perfect for grinding ranked games back-to-back

### Persistent
- Session survives page refreshes
- Database-backed (not just memory)

---

## 💡 Pro Tips

### Tip 1: Start Session Before Draft
Start the session even before entering lobby - you can update it as draft happens!

### Tip 2: Use Notes Field
The notes field pre-fills from session, so jot down thoughts during/after game

### Tip 3: Mobile-Friendly
Works great on mobile - sidebar collapses, modal is touch-friendly

### Tip 4: Incomplete Sessions
If you forget to complete a session, you can manually complete it later from session history

---

## 🔍 Database Schema

New table created automatically:

```sql
CREATE TABLE draft_sessions (
    session_id INTEGER PRIMARY KEY,
    status TEXT,           -- 'in_progress' or 'completed'
    started_at TEXT,
    completed_at TEXT,
    
    your_hero TEXT,
    your_role TEXT,
    enemies TEXT,          -- JSON array
    teammates TEXT,        -- JSON array
    banned TEXT,           -- JSON array
    
    result TEXT,
    mvp_status TEXT,
    kills INTEGER,
    deaths INTEGER,
    assists INTEGER,
    notes TEXT
);
```

Completed sessions are copied to `game_history` table!

---

## 🐛 Troubleshooting

### "Session panel not showing"
- Check if `session_tracker.py` is in project folder
- Check imports at top of app.py
- Try restarting Streamlit

### "Can't pick hero"
- Make sure session is started (green panel showing)
- Check if hero is already picked (locked)
- Try refreshing page

### "Modal won't close"
- Click "Back to Game" button
- Or refresh page (session is saved in DB)

### "Session not syncing"
- Make sure `sync_session_with_draft_inputs()` is called
- Check that it's after the multiselect widgets

---

## 🚀 Future Enhancements

Ideas for later:
- **Session History Tab** - Review past sessions
- **Mid-game notes** - Add notes during game (mobile app?)
- **Draft timer** - Track how long you took to decide
- **Pick confidence** - Rate your confidence in the pick
- **Lobby screenshot** - Upload draft screenshot

---

## 🎓 What You Built

This is a **production-quality feature**! You have:
- ✅ Real-time state management
- ✅ Database persistence
- ✅ Modal dialogs
- ✅ Auto-sync
- ✅ Session lifecycle management

**This is portfolio-worthy stuff!** 🌟

---

Ready to integrate? Just follow the 5 steps above and you're live! 🎮🚀