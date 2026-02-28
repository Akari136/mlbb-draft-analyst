"""
cleanup_sessions.py - Clean up abandoned draft sessions

Run this to:
1. Delete abandoned in-progress sessions
2. Reset session numbering
3. Show session statistics
"""

import sqlite3
from datetime import datetime

db_path = "mlcounter.db"

conn = sqlite3.connect(db_path)
cur = conn.cursor()

print("="*60)
print("SESSION CLEANUP UTILITY")
print("="*60)

# Get current stats
cur.execute("""
    SELECT 
        COUNT(*) as total,
        SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
        SUM(CASE WHEN status = 'in_progress' THEN 1 ELSE 0 END) as in_progress
    FROM draft_sessions
""")

stats = cur.fetchone()
total, completed, in_progress = stats[0] or 0, stats[1] or 0, stats[2] or 0
abandoned = total - completed - in_progress

print(f"\nCurrent Stats:")
print(f"  Total sessions: {total}")
print(f"  Completed: {completed}")
print(f"  In Progress: {in_progress}")
print(f"  Abandoned: {abandoned}")

if total == 0:
    print("\n✅ No sessions to clean!")
    conn.close()
    exit()

print("\n" + "="*60)
print("CLEANUP OPTIONS")
print("="*60)
print("1. Delete abandoned sessions (in_progress > 24h old)")
print("2. Delete ALL in_progress sessions")
print("3. Delete ALL sessions (fresh start)")
print("4. Show session details")
print("5. Exit")

choice = input("\nChoose option (1-5): ").strip()

if choice == "1":
    # Delete old abandoned sessions
    cur.execute("""
        DELETE FROM draft_sessions 
        WHERE status = 'in_progress' 
        AND datetime(started_at) < datetime('now', '-1 day')
    """)
    deleted = cur.rowcount
    conn.commit()
    print(f"\n✅ Deleted {deleted} abandoned sessions (>24h old)")

elif choice == "2":
    # Delete all in-progress
    confirm = input(f"Delete {in_progress} in-progress sessions? (y/n): ")
    if confirm.lower() == 'y':
        cur.execute("DELETE FROM draft_sessions WHERE status = 'in_progress'")
        deleted = cur.rowcount
        conn.commit()
        print(f"\n✅ Deleted {deleted} in-progress sessions")
    else:
        print("\n❌ Cancelled")

elif choice == "3":
    # Delete ALL sessions
    confirm = input(f"⚠️  DELETE ALL {total} SESSIONS? This cannot be undone! (type 'DELETE'): ")
    if confirm == 'DELETE':
        cur.execute("DELETE FROM draft_sessions")
        deleted = cur.rowcount
        
        # Reset auto-increment
        cur.execute("DELETE FROM sqlite_sequence WHERE name='draft_sessions'")
        
        conn.commit()
        print(f"\n✅ Deleted ALL {deleted} sessions and reset numbering")
    else:
        print("\n❌ Cancelled")

elif choice == "4":
    # Show details
    print("\n" + "="*60)
    print("SESSION DETAILS")
    print("="*60)
    
    cur.execute("""
        SELECT session_id, status, your_hero, started_at, completed_at
        FROM draft_sessions
        ORDER BY session_id DESC
        LIMIT 20
    """)
    
    for row in cur.fetchall():
        sid, status, hero, started, completed = row
        hero = hero or "(no hero)"
        print(f"\nSession #{sid}: {status}")
        print(f"  Hero: {hero}")
        print(f"  Started: {started}")
        if completed:
            print(f"  Completed: {completed}")

elif choice == "5":
    print("\n👋 Bye!")
else:
    print("\n❌ Invalid choice")

conn.close()

print("\n" + "="*60)
print("Done!")
print("="*60)