# MLBB Draft Analyst - Enhanced with Game History Tracking

## 🆕 What's New

Your draft analyst now tracks your personal game history and uses it to enhance recommendations!

## 📦 Installation

No new dependencies needed! Uses the same SQLite database you already have.

### Quick Start

1. **Replace your current `app.py`** with the new `app_enhanced.py`:
   ```bash
   cp app_enhanced.py app.py
   ```

2. **Run the app** (the database table will be created automatically):
   ```bash
   streamlit run app.py
   ```

That's it! The app will automatically create the `game_history` table on first run.

## 🎯 New Features

### 1. **📝 Log Game Page**
Manually record your match results:
- Date and hero you played
- Your role/lane
- Win or Loss
- MVP status (MVP, Gold, Silver)
- KDA stats (Kills/Deaths/Assists)
- Teammate and enemy team composition
- Optional notes for each game

### 2. **📊 Game History Page**
View your performance statistics:
- **Overall Stats**: Total games, win rate, avg KDA
- **Hero-Specific Stats**: Win rate and performance per hero
- **Recent Games Log**: Detailed match history with filtering
- **Delete Games**: Remove incorrect entries

### 3. **Enhanced Draft Analysis**
The draft analysis page now shows:
- **Your personal win rate** for each recommended hero
- **Games played** count next to recommendations
- **Personal KDA stats** in the technical breakdown

## 📖 Usage Guide

### Logging a Game

1. Go to **"📝 Log Game"** page
2. Fill in the form:
   - Select the date (defaults to today)
   - Choose your hero and role
   - Select Win/Loss
   - (Optional) Add MVP status and KDA
   - Select your teammates (4 heroes)
   - Select enemy team (5 heroes)
   - Add any notes about the game
3. Click **"💾 Save Game"**

### Viewing Your Stats

1. Go to **"📊 Game History"** page
2. See your overall performance at the top
3. Select a specific hero to see detailed stats
4. Scroll down to view recent games
5. Expand any game to see full details
6. Delete games if you made a mistake

### Using Personal Data in Draft Analysis

The **"🎯 Draft Analysis"** page automatically shows:
- Your personal win rate for each recommended hero
- How many games you've played with that hero
- Your average KDA in the technical breakdown

This helps you balance:
- **Meta recommendations** (from the engine)
- **Your personal performance** (from your history)

Example: The engine might recommend Hero A with a high score, but if you see you have a 30% win rate with them, you might choose Hero B instead!

## 🔮 Next Steps: Historical Performance Integration

After you log some games, we can add:
- **Matchup learning**: "You're 0-3 as Thamuz vs Yuzhong - avoid this!"
- **Confidence scoring**: Boost recommendations for heroes you perform well with
- **Enemy pattern detection**: "You struggle against Harith - consider banning"
- **Role performance**: "Your win rate as Jungler is 65% vs 45% in Gold Lane"

## 📊 Database Schema

The new `game_history` table structure:
```sql
CREATE TABLE game_history (
    game_id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    your_hero TEXT NOT NULL,
    your_role TEXT,
    teammates TEXT,           -- JSON array
    enemies TEXT NOT NULL,    -- JSON array
    result TEXT NOT NULL,     -- 'Win' or 'Loss'
    mvp_status TEXT,          -- 'MVP', 'Gold Medal', 'Silver Medal', or NULL
    kills INTEGER,
    deaths INTEGER,
    assists INTEGER,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## 🛠️ Troubleshooting

**Q: The table isn't being created?**
A: Run the initialization script manually:
```bash
python init_game_history.py mlcounter.db
```

**Q: I made a mistake logging a game**
A: Go to Game History page, expand the game, and click "🗑️ Delete Game"

**Q: Can I export my data?**
A: Yes! Your data is in the SQLite database. You can query it with any SQLite tool or write a simple export script.

## 💡 Tips

1. **Log games consistently** - The more data, the better the insights
2. **Add notes** - Future you will appreciate context like "They had no tank" or "Fed early"
3. **Review before ranked** - Check your hero stats before jumping into ranked matches
4. **Track patterns** - Notice which enemy comps give you trouble

## 🚀 Future Enhancements (Coming Soon)

- Auto-adjust draft recommendations based on your personal win rates
- Matchup-specific warnings (e.g., "You're 1-5 vs this enemy comp")
- Performance trends over time
- Export to CSV/Excel
- Screenshot upload + OCR for automated logging