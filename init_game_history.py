#!/usr/bin/env python3
"""
Initialize the game_history table in mlcounter.db
Run this once to add game tracking capabilities
"""

import sqlite3
import sys

def init_game_history_table(db_path: str = "mlcounter.db"):
    """Add game_history table to existing database"""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    # Check if table already exists
    cur.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name='game_history'
    """)
    
    if cur.fetchone():
        print("✓ game_history table already exists")
        conn.close()
        return
    
    # Create the table
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
    print("✓ game_history table created successfully!")
    print("\nTable structure:")
    print("  - game_id: Auto-incrementing ID")
    print("  - date: Game date (YYYY-MM-DD)")
    print("  - your_hero: Hero you played")
    print("  - your_role: Lane/role you played")
    print("  - teammates: JSON array of teammate heroes")
    print("  - enemies: JSON array of enemy heroes")
    print("  - result: 'Win' or 'Loss'")
    print("  - mvp_status: 'MVP', 'Gold', 'Silver', or None")
    print("  - kills/deaths/assists: KDA stats")
    print("  - notes: Free-form notes")
    print("  - created_at: Auto timestamp")

if __name__ == "__main__":
    db_path = sys.argv[1] if len(sys.argv) > 1 else "mlcounter.db"
    init_game_history_table(db_path)