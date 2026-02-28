"""
session_tracker.py - Live Draft Session Tracking

Tracks draft sessions in real-time with a persistent sidebar/modal.
Updates as draft progresses, completes after game.
"""

import sqlite3
import json
from datetime import datetime
from typing import Dict, List, Optional


class SessionTracker:
    """Manage live draft sessions"""
    
    def __init__(self, db_path: str = "mlcounter.db"):
        self.db_path = db_path
        self._ensure_sessions_table()
    
    def _ensure_sessions_table(self):
        """Create sessions table if not exists"""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS draft_sessions (
                session_id INTEGER PRIMARY KEY AUTOINCREMENT,
                status TEXT DEFAULT 'in_progress',
                started_at TEXT DEFAULT CURRENT_TIMESTAMP,
                completed_at TEXT,
                
                -- Draft context
                your_hero TEXT,
                your_role TEXT,
                enemies TEXT,
                teammates TEXT,
                banned TEXT,
                
                -- Game result (filled after game)
                result TEXT,
                mvp_status TEXT,
                kills INTEGER,
                deaths INTEGER,
                assists INTEGER,
                notes TEXT
            )
        """)
        
        conn.commit()
        conn.close()
    
    def create_session(self) -> int:
        """Create new draft session, return session_id"""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        
        # First, clean up any old abandoned sessions (older than 24 hours)
        cur.execute("""
            DELETE FROM draft_sessions 
            WHERE status = 'in_progress' 
            AND datetime(started_at) < datetime('now', '-1 day')
        """)
        
        # Check if there's already an active session
        cur.execute("""
            SELECT session_id FROM draft_sessions 
            WHERE status = 'in_progress' 
            ORDER BY started_at DESC 
            LIMIT 1
        """)
        existing = cur.fetchone()
        
        if existing:
            # Verify the session still exists and is valid
            session_id = existing[0]
            cur.execute("SELECT session_id FROM draft_sessions WHERE session_id = ?", (session_id,))
            if cur.fetchone():
                # Reuse existing active session
                conn.close()
                return session_id
        
        # Create new session (no existing valid session found)
        cur.execute("""
            INSERT INTO draft_sessions (status) 
            VALUES ('in_progress')
        """)
        session_id = cur.lastrowid
        
        conn.commit()
        conn.close()
        
        return session_id
    
    def update_session(
        self, 
        session_id: int,
        hero: Optional[str] = None,
        role: Optional[str] = None,
        enemies: Optional[List[str]] = None,
        teammates: Optional[List[str]] = None,
        banned: Optional[List[str]] = None
    ):
        """Update session as draft progresses"""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        
        updates = []
        params = []
        
        if hero is not None:
            updates.append("your_hero = ?")
            params.append(hero)
        
        if role is not None:
            updates.append("your_role = ?")
            params.append(role)
        
        if enemies is not None:
            updates.append("enemies = ?")
            params.append(json.dumps(enemies))
        
        if teammates is not None:
            updates.append("teammates = ?")
            params.append(json.dumps(teammates))
        
        if banned is not None:
            updates.append("banned = ?")
            params.append(json.dumps(banned))
        
        if updates:
            params.append(session_id)
            query = f"UPDATE draft_sessions SET {', '.join(updates)} WHERE session_id = ?"
            cur.execute(query, params)
            conn.commit()
        
        conn.close()
    
    def complete_session(
        self,
        session_id: int,
        result: str,
        kills: int,
        deaths: int,
        assists: int,
        mvp_status: Optional[str] = None,
        notes: Optional[str] = None
    ):
        """Complete session with game results"""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        
        cur.execute("""
            UPDATE draft_sessions 
            SET status = 'completed',
                completed_at = CURRENT_TIMESTAMP,
                result = ?,
                kills = ?,
                deaths = ?,
                assists = ?,
                mvp_status = ?,
                notes = ?
            WHERE session_id = ?
        """, (result, kills, deaths, assists, mvp_status, notes, session_id))
        
        conn.commit()
        conn.close()
    
    def get_session(self, session_id: int) -> Optional[Dict]:
        """Get session data"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        
        cur.execute("""
            SELECT * FROM draft_sessions 
            WHERE session_id = ?
        """, (session_id,))
        
        row = cur.fetchone()
        conn.close()
        
        if row:
            session = dict(row)
            # Parse JSON fields - ensure they're always lists, never None
            for field in ['enemies', 'teammates', 'banned']:
                if session.get(field):
                    try:
                        session[field] = json.loads(session[field])
                    except:
                        session[field] = []
                else:
                    session[field] = []
            return session
        return None
    
    def get_active_session(self) -> Optional[Dict]:
        """Get current in-progress session"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        
        cur.execute("""
            SELECT * FROM draft_sessions 
            WHERE status = 'in_progress'
            ORDER BY started_at DESC
            LIMIT 1
        """)
        
        row = cur.fetchone()
        conn.close()
        
        if row:
            session = dict(row)
            for field in ['enemies', 'teammates', 'banned']:
                if session[field]:
                    session[field] = json.loads(session[field])
                else:
                    session[field] = []
            return session
        return None
    
    def cancel_session(self, session_id: int):
        """Cancel/delete session and reset numbering properly"""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        
        # Delete the session
        cur.execute("""
            DELETE FROM draft_sessions 
            WHERE session_id = ?
        """, (session_id,))
        
        # Check if there are any remaining IN-PROGRESS sessions
        cur.execute("SELECT COUNT(*) FROM draft_sessions WHERE status = 'in_progress'")
        in_progress = cur.fetchone()[0]
        
        # If no in-progress sessions left, reset counter to highest completed session
        if in_progress == 0:
            # Get the highest session_id from completed sessions
            cur.execute("SELECT MAX(session_id) FROM draft_sessions WHERE status = 'completed'")
            max_completed = cur.fetchone()[0]
            
            # Always delete the sequence entry first
            cur.execute("DELETE FROM sqlite_sequence WHERE name='draft_sessions'")
            
            # If there are completed sessions, set counter to that number
            if max_completed is not None:
                cur.execute("""
                    INSERT INTO sqlite_sequence (name, seq) 
                    VALUES ('draft_sessions', ?)
                """, (max_completed,))
        
        conn.commit()
        conn.close()
    
    def copy_session_to_game_history(self, session_id: int):
        """Copy completed session to main game_history table"""
        session = self.get_session(session_id)
        
        if not session or session['status'] != 'completed':
            return False
        
        # VALIDATE: Must have hero
        if not session.get('your_hero'):
            raise ValueError("Cannot save game without selecting a hero! Please pick a hero first.")
        
        # VALIDATE: Must have at least one enemy
        if not session.get('enemies') or len(session['enemies']) == 0:
            raise ValueError("Cannot save game without any enemies!")
        
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        
        cur.execute("""
            INSERT INTO game_history 
            (date, your_hero, your_role, teammates, enemies, result,
             mvp_status, kills, deaths, assists, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.now().strftime('%Y-%m-%d'),
            session['your_hero'],
            session['your_role'] or 'Unknown',
            json.dumps(session['teammates'] or []),
            json.dumps(session['enemies'] or []),
            session['result'],
            session['mvp_status'],
            session['kills'],
            session['deaths'],
            session['assists'],
            session['notes']
        ))
        
        conn.commit()
        conn.close()
        
        return True
    
    def get_recent_sessions(self, limit: int = 10) -> List[Dict]:
        """Get recent sessions (for history view)"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        
        cur.execute("""
            SELECT * FROM draft_sessions 
            ORDER BY started_at DESC
            LIMIT ?
        """, (limit,))
        
        rows = cur.fetchall()
        conn.close()
        
        sessions = []
        for row in rows:
            session = dict(row)
            for field in ['enemies', 'teammates', 'banned']:
                if session[field]:
                    session[field] = json.loads(session[field])
                else:
                    session[field] = []
            sessions.append(session)
        
        return sessions
    
    def cleanup_abandoned_sessions(self) -> int:
        """Clean up abandoned in-progress sessions. Returns count deleted."""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        
        # Delete sessions that are:
        # 1. Still in_progress
        # 2. Older than 24 hours
        # 3. OR have no hero picked and older than 1 hour
        cur.execute("""
            DELETE FROM draft_sessions 
            WHERE status = 'in_progress' 
            AND (
                datetime(started_at) < datetime('now', '-1 day')
                OR (your_hero IS NULL AND datetime(started_at) < datetime('now', '-1 hour'))
            )
        """)
        
        deleted = cur.rowcount
        conn.commit()
        conn.close()
        
        return deleted
    
    def get_session_stats(self) -> Dict:
        """Get session statistics"""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        
        cur.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                SUM(CASE WHEN status = 'in_progress' THEN 1 ELSE 0 END) as in_progress
            FROM draft_sessions
        """)
        
        row = cur.fetchone()
        conn.close()
        
        return {
            'total': row[0] or 0,
            'completed': row[1] or 0,
            'in_progress': row[2] or 0,
            'abandoned': (row[0] or 0) - (row[1] or 0) - (row[2] or 0)
        }


if __name__ == "__main__":
    # Test the tracker
    tracker = SessionTracker()
    
    # Create session
    session_id = tracker.create_session()
    print(f"Created session #{session_id}")
    
    # Simulate draft progression
    tracker.update_session(session_id, enemies=['Alpha'])
    print("Added enemy: Alpha")
    
    tracker.update_session(session_id, teammates=['Brody'])
    print("Added teammate: Brody")
    
    tracker.update_session(session_id, hero='Thamuz', role='EXP Lane')
    print("You picked: Thamuz")
    
    # Get active session
    active = tracker.get_active_session()
    print(f"\nActive session: {active['your_hero']} vs {active['enemies']}")
    
    # Complete after game
    tracker.complete_session(
        session_id,
        result='Win',
        kills=8,
        deaths=2,
        assists=6,
        notes='Good early game trades'
    )
    print("\nSession completed!")
    
    # Copy to game history
    tracker.copy_session_to_game_history(session_id)
    print("Copied to game history!")