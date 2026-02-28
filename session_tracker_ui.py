"""
session_tracker_ui.py - UI components for live session tracking

Add this to your app.py to enable live draft session tracking.
"""

import streamlit as st
from session_tracker import SessionTracker
from datetime import datetime


def render_session_sidebar(db_path: str):
    """
    Render the live session tracker sidebar.
    Call this at the top of Draft Analysis page.
    """
    
    tracker = SessionTracker(db_path)
    
    # Auto-cleanup on load
    deleted = tracker.cleanup_abandoned_sessions()
    
    # Initialize session state
    if 'active_session_id' not in st.session_state:
        st.session_state.active_session_id = None
    
    # If we have a session_id in state, verify it still exists and is valid
    if st.session_state.active_session_id:
        session = tracker.get_session(st.session_state.active_session_id)
        if not session or session['status'] != 'in_progress':
            # Session doesn't exist or was completed - clear it
            st.session_state.active_session_id = None
    
    # If still no active session in state, check if there's one in DB
    if not st.session_state.active_session_id:
        active = tracker.get_active_session()
        if active:
            st.session_state.active_session_id = active['session_id']
    
    # Sidebar container
    with st.sidebar:
        st.divider()
        st.header("📋 Live Session")
        
        # Session stats
        stats = tracker.get_session_stats()
        if stats['total'] > 0:
            with st.expander("📊 Session Stats", expanded=False):
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Total", stats['total'])
                    st.metric("Completed", stats['completed'])
                with col2:
                    st.metric("Active", stats['in_progress'])
                    if stats['abandoned'] > 0:
                        st.metric("Abandoned", stats['abandoned'], delta_color="inverse")
        
        # Check if we have an active session
        if st.session_state.active_session_id:
            session = tracker.get_session(st.session_state.active_session_id)
            
            if session and session['status'] == 'in_progress':
                render_active_session_panel(tracker, session)
            else:
                # Session was completed or deleted
                st.session_state.active_session_id = None
                st.rerun()
        else:
            # No active session - show start button
            if st.button("🎮 Start New Session", type="primary", use_container_width=True):
                session_id = tracker.create_session()
                st.session_state.active_session_id = session_id
                st.success(f"Session #{session_id} started!")
                st.rerun()


def render_active_session_panel(tracker: SessionTracker, session: dict):
    """Render the active session panel with live updates"""
    
    session_id = session['session_id']
    
    # IMPORTANT: Re-fetch session from DB to get latest data
    session = tracker.get_session(session_id)
    if not session:
        st.session_state.active_session_id = None
        st.rerun()
        return
    
    # Session header with refresh button
    col_h1, col_h2 = st.columns([3, 1])
    with col_h1:
        st.success(f"🟢 Session #{session_id} Active")
    with col_h2:
        if st.button("🔄", key="refresh_session", help="Refresh session data"):
            st.rerun()
    
    with st.container(border=True):
        # Your hero (if picked)
        if session['your_hero']:
            st.markdown(f"### ⚔️ {session['your_hero']}")
            if session['your_role']:
                st.caption(f"Role: {session['your_role']}")
        else:
            st.info("👆 Pick your hero from recommendations above")
        
        st.divider()
        
        # Enemy team
        st.markdown("**Enemy Team:**")
        enemies = session.get('enemies', [])
        if enemies:
            for enemy in enemies:
                st.write(f"🔴 {enemy}")
        else:
            st.caption("_No enemies added yet_")
        
        # Teammate team  
        st.markdown("**Your Team:**")
        teammates = session.get('teammates', [])
        if teammates:
            for teammate in teammates:
                st.write(f"🔵 {teammate}")
        else:
            st.caption("_No teammates added yet_")
        
        # Banned heroes
        banned = session.get('banned', [])
        if banned:
            st.markdown("**Banned:**")
            st.caption(", ".join(banned))
    
    st.caption(f"Started: {session['started_at'][:16]}")
    
    # Action buttons
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("✅ Complete", use_container_width=True, type="primary", key="complete_session_btn"):
            st.session_state.show_complete_modal = True
            st.rerun()
    
    with col2:
        if st.button("❌ Cancel", use_container_width=True, key="cancel_session_btn"):
            tracker.cancel_session(session_id)
            st.session_state.active_session_id = None
            st.success("Session cancelled")
            st.rerun()


def render_complete_session_modal(tracker: SessionTracker, session: dict, heroes: list):
    """Modal dialog to complete a session after the game"""
    
    session_id = session['session_id']
    
    st.markdown("## 🏁 Complete Session")
    st.markdown(f"### {session['your_hero']} vs {', '.join(session.get('enemies', [])[:3])}")
    
    with st.form("complete_session_form"):
        st.subheader("Add Missing Heroes")
        
        # Allow adding more enemies/teammates
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Enemy Team:**")
            current_enemies = session.get('enemies', [])
            
            # Show current enemies
            for enemy in current_enemies:
                st.write(f"✓ {enemy}")
            
            # Add more enemies
            available_enemies = [h for h in heroes if h not in current_enemies and h != session['your_hero']]
            additional_enemies = st.multiselect(
                "Add more enemies",
                options=available_enemies,
                key="additional_enemies"
            )
        
        with col2:
            st.markdown("**Your Team:**")
            current_teammates = session.get('teammates', [])
            
            # Show current teammates
            for teammate in current_teammates:
                st.write(f"✓ {teammate}")
            
            # Add more teammates
            available_teammates = [h for h in heroes if h not in current_teammates and h != session['your_hero']]
            additional_teammates = st.multiselect(
                "Add more teammates",
                options=available_teammates,
                key="additional_teammates"
            )
        
        st.divider()
        st.subheader("Game Result")
        
        col_a, col_b = st.columns(2)
        
        with col_a:
            result = st.selectbox("Result", ["Win", "Loss"])
            mvp_status = st.selectbox("MVP Status", ["None", "MVP", "Gold Medal", "Silver Medal"])
        
        with col_b:
            kills = st.number_input("Kills", min_value=0, value=0, step=1)
            deaths = st.number_input("Deaths", min_value=0, value=0, step=1)
            assists = st.number_input("Assists", min_value=0, value=0, step=1)
        
        notes = st.text_area("Notes", placeholder="What did you learn from this game?")
        
        col1, col2 = st.columns(2)
        
        with col1:
            submit = st.form_submit_button("💾 Save & Next Session", type="primary", use_container_width=True)
        
        with col2:
            cancel = st.form_submit_button("↩️ Back to Game", use_container_width=True)
        
        if submit:
            # VALIDATE: Check if hero was picked
            if not session.get('your_hero'):
                st.error("❌ Cannot save session - you didn't pick a hero!")
                st.info("💡 Go back and click 'I Pick [Hero]' button on your chosen hero first.")
                return
            
            # Update enemies and teammates with additions
            final_enemies = current_enemies + additional_enemies
            final_teammates = current_teammates + additional_teammates
            
            # VALIDATE: Must have at least one enemy
            if not final_enemies:
                st.error("❌ Cannot save game without any enemies!")
                st.info("💡 Add at least one enemy hero from the draft.")
                return
            
            tracker.update_session(
                session_id,
                enemies=final_enemies,
                teammates=final_teammates
            )
            
            # Complete the session
            tracker.complete_session(
                session_id,
                result=result,
                kills=kills,
                deaths=deaths,
                assists=assists,
                mvp_status=mvp_status if mvp_status != "None" else None,
                notes=notes
            )
            
            # Copy to game history
            try:
                tracker.copy_session_to_game_history(session_id)
            except ValueError as e:
                st.error(f"❌ {str(e)}")
                return
            except Exception as e:
                st.error(f"❌ Error saving to game history: {e}")
                return
            
            # Clear active session
            st.session_state.active_session_id = None
            st.session_state.show_complete_modal = False
            
            st.success("✅ Session saved! Starting new session...")
            
            # Auto-start next session
            new_session_id = tracker.create_session()
            st.session_state.active_session_id = new_session_id
            
            st.balloons()
            st.rerun()
        
        if cancel:
            st.session_state.show_complete_modal = False
            st.rerun()


def add_pick_hero_button(hero_name: str, role: str, db_path: str):
    """
    Add "I Picked This" button to recommendation results.
    Call this for each hero in the results.
    """
    
    tracker = SessionTracker(db_path)
    
    # DEBUG: Check if session exists
    active_session_id = st.session_state.get('active_session_id')
    
    # DEBUG INFO (remove after testing)
    with st.expander("🔍 DEBUG INFO", expanded=False):
        st.write(f"Session ID in state: {active_session_id}")
        st.write(f"Hero: {hero_name}, Role: {role}")
    
    if not active_session_id:
        # No active session
        st.warning("⚠️ No active session! Click 'Start New Session' in sidebar first.")
        return
    
    # Get session from DB
    try:
        session = tracker.get_session(active_session_id)
    except Exception as e:
        st.error(f"❌ Error getting session: {e}")
        return
    
    if not session:
        # Session doesn't exist in DB
        st.error(f"❌ Session #{active_session_id} not found in database!")
        st.caption("Try clicking 🔄 refresh or start a new session")
        return
    
    current_hero = session.get('your_hero')
    
    # DEBUG: Show current state
    with st.expander("🔍 SESSION STATE", expanded=False):
        st.write(f"Current hero in session: {current_hero}")
        st.write(f"Session status: {session.get('status')}")
        st.write(f"Session data: {session}")
    
    if current_hero == hero_name:
        # This hero is already picked - show prominent indicator
        st.success(f"✅ **YOU PICKED THIS!**", icon="⚔️")
        st.write(f"**{hero_name}** is locked in for this session")
    elif current_hero:
        # Different hero is picked - show which one
        st.info(f"Currently picked: **{current_hero}**")
        if st.button(f"Switch to {hero_name}", key=f"pick_{hero_name}", use_container_width=True, type="secondary"):
            st.write("🔄 Switch button clicked!")  # DEBUG
            try:
                tracker.update_session(
                    session['session_id'],
                    hero=hero_name,
                    role=role
                )
                st.success(f"✅ Switched to **{hero_name}**! Click 🔄 in sidebar to see update.")
                st.balloons()
            except Exception as e:
                st.error(f"❌ Error switching hero: {e}")
                import traceback
                st.code(traceback.format_exc())
    else:
        # No hero picked yet
        st.write("👇 Click button below to lock in this hero")  # DEBUG
        if st.button(f"✅ I Pick {hero_name}", key=f"pick_{hero_name}", use_container_width=True, type="primary"):
            st.write("🎯 Button was clicked!")  # DEBUG
            try:
                st.write(f"Updating session {session['session_id']} with hero={hero_name}, role={role}")  # DEBUG
                tracker.update_session(
                    session['session_id'],
                    hero=hero_name,
                    role=role
                )
                st.success(f"✅ **{hero_name} LOCKED IN!** 🎯", icon="⚔️")
                st.write("Check the sidebar (click 🔄 to refresh)")
                st.balloons()
                st.write("✅ Hero saved to database!")  # DEBUG
            except Exception as e:
                st.error(f"❌ Error picking hero: {e}")
                import traceback
                st.code(traceback.format_exc())


def sync_session_with_draft_inputs(
    db_path: str,
    enemies: list,
    teammates: list,
    banned: list
):
    """
    Sync session with current draft inputs.
    Call this when enemies/teammates/banned changes in the draft UI.
    """
    
    if st.session_state.get('active_session_id'):
        tracker = SessionTracker(db_path)
        
        # Get current session data
        current_session = tracker.get_session(st.session_state.active_session_id)
        
        # Only update if data has changed (avoid unnecessary DB writes)
        if current_session:
            # Handle None values safely
            current_enemies = current_session.get('enemies') or []
            current_teammates = current_session.get('teammates') or []
            current_banned = current_session.get('banned') or []
            
            # Ensure input lists are not None
            enemies = enemies or []
            teammates = teammates or []
            banned = banned or []
            
            # Check if anything changed
            if (set(current_enemies) != set(enemies) or 
                set(current_teammates) != set(teammates) or 
                set(current_banned) != set(banned)):
                
                tracker.update_session(
                    st.session_state.active_session_id,
                    enemies=enemies,
                    teammates=teammates,
                    banned=banned
                )


# Integration example for app.py
"""
HOW TO INTEGRATE INTO APP.PY:

1. At the top of Draft Analysis page (around line 250):
   
   from session_tracker_ui import (
       render_session_sidebar,
       render_complete_session_modal,
       add_pick_hero_button,
       sync_session_with_draft_inputs
   )

2. After page title:
   
   render_session_sidebar(db_path)

3. After user selects enemies/teammates/banned:
   
   sync_session_with_draft_inputs(db_path, enemies, teammates, banned)

4. In the results display, for each hero:
   
   with col3:
       add_pick_hero_button(r.hero, pool_role, db_path)

5. Check for complete modal at top of page:
   
   if st.session_state.get('show_complete_modal'):
       session = tracker.get_session(st.session_state.active_session_id)
       render_complete_session_modal(tracker, session, heroes)
       st.stop()  # Don't render rest of page
"""