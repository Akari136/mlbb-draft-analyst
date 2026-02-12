# Update Guide: v1.1.0 - Historical Performance Integration

## 🚀 Quick Update (2 minutes)

```bash
# 1. Backup your current files (optional but recommended)
cp app.py app_v1.0_backup.py
cp draft_engine.py draft_engine_v1.0_backup.py

# 2. Replace with new files
# (Download the new app.py and draft_engine.py from outputs)

# 3. Run the app - table will auto-create
streamlit run app.py

# Done! ✅
```

## 📋 What's New in v1.1.0

### 🎯 Core Features

1. **Personal Win Rate Integration**
   - Your heroes with 60%+ win rate get score boosts
   - Heroes under 40% win rate get penalties
   - Need at least 3 games for this to activate

2. **Matchup Learning**
   - Tracks your record vs specific enemies
   - "You're 4-1 vs Yuzhong" → boost this pick
   - "You're 1-4 vs Fredrinn" → avoid this matchup
   - Need 2+ games vs that enemy

3. **Confidence Levels**
   - ⭐⭐⭐ High (5+ games)
   - ⭐⭐ Medium (3-4 games)  
   - ⭐ Low (1-2 games)

4. **Matchup Warnings**
   - Big yellow warnings when you have bad history
   - Shows prominently at top of recommendations

### 📱 New Pages

Your app now has 4 pages (sidebar navigation):
- **🎯 Draft Analysis** - Main recommendations (enhanced)
- **📝 Log Game** - Record your matches (NEW)
- **📊 Game History** - View stats & history (NEW)
- **⚙️ Settings** - Database management (NEW)

## 🔧 Configuration Options

### New Sidebar Controls

**Personal Performance Toggle**
- Turn on/off personal data usage
- Useful for testing meta-only recommendations

**New Weight Sliders**
- **Personal WR weight** (0.08): How much your win rate matters
- **Good matchup bonus** (1.5): Boost for 60%+ matchup WR
- **Bad matchup penalty** (-1.8): Penalty for <40% matchup WR
- **Min games confidence** (5): Games needed for ⭐⭐⭐ rating

### Recommended Settings

**Aggressive (Trust Your Data)**
```
Personal WR weight: 0.12
Good matchup bonus: 2.0
Bad matchup penalty: -2.5
Min games confidence: 3
```

**Conservative (Balanced)**
```
Personal WR weight: 0.08
Good matchup bonus: 1.5
Bad matchup penalty: -1.8
Min games confidence: 5
```

**Meta-Focused (Minimal Personal)**
```
Personal WR weight: 0.04
Good matchup bonus: 0.8
Bad matchup penalty: -1.0
Min games confidence: 8
```

## 📊 Understanding the New Display

### Draft Analysis Results

**Before (v1.0):**
```
#1 Thamuz
Engine Score: 6.25
Reasoning: Strong vs Yuzhong (+1.25); Tier S (+0.90)
```

**After (v1.1):**
```
#1 Thamuz                    [⭐⭐⭐]
Engine Score: 7.40          Your WR: 70.0% (10g)

⚠️ You're 1-4 vs Fredrinn  ← NEW: Matchup warning

Reasoning: Strong vs Yuzhong (+1.25); Your WR: 70% (10g) ⭐⭐⭐ (+1.60); 
          Strong vs Yuzhong: 4-1 in your games (+1.50); Tier S (+0.90)
          
Technical Breakdown:
├─ Counter bonus: +1.25
├─ Meta bonus: +0.90
├─ Personal bonus: +3.10    ← NEW!
└─ Matchup History:         ← NEW!
   ├─ ✅ vs Yuzhong: 4-1
   └─ ❌ vs Fredrinn: 1-4
```

## 🎮 How to Use

### Day 1-3: Data Collection Phase
1. Log every game you play
2. Be detailed with notes
3. Don't rely on personal data yet (< 3 games per hero)

### Day 4-7: Light Usage
- Heroes with 3+ games start getting personal adjustments
- Warnings appear for bad matchups (2+ losses)
- Check confidence stars ⭐

### Week 2+: Full Integration
- 5+ games = high confidence ⭐⭐⭐
- Matchup data becomes reliable
- Personal data > meta data for your playstyle

## 🐛 Troubleshooting

### "No such table: game_history"
**Fix:** The app should auto-create this, but if not:
```bash
python init_game_history.py mlcounter.db
```

### Personal bonus shows 0.00 for all heroes
**Cause:** Not enough games logged yet
**Fix:** Log at least 3 games with a hero to see personal adjustments

### Matchup warnings not showing
**Cause:** Need at least 2 games vs that specific enemy
**Fix:** Play more games and log them

### "Use personal performance data" checkbox missing
**Cause:** Running old app.py
**Fix:** Make sure you replaced app.py with the new version

### Error: 'PickResult' object has no attribute 'personal_bonus'
**Cause:** draft_engine.py not updated
**Fix:** Replace draft_engine.py with the new version

## 📈 Example Usage Flow

```
SCENARIO: You want to pick for EXP lane
Enemy has: Fredrinn, Claude, Kadita, Khufra, Ling

OLD v1.0 Recommendation:
#1 Thamuz (6.25) - Strong vs Fredrinn (+1.25)
#2 Argus (5.80) - Tier A (+0.60)

NEW v1.1 Recommendation:
#1 Argus (7.90) - Your WR: 75% (8g) ⭐⭐⭐ (+2.00)
    ├─ Strong vs Fredrinn: 5-1 in your games (+1.50)
    └─ Tier A (+0.60)

#2 Thamuz (5.40) - Your WR: 35% (6g) ⭐⭐ (-1.20)
    ├─ ⚠️ You're 1-4 vs Fredrinn
    ├─ Weak vs Fredrinn: 1-4 in your games (-1.80)
    └─ Tier S (+0.90)

RESULT: Even though Thamuz is meta (Tier S), you personally 
struggle vs Fredrinn. Argus is recommended instead because 
you dominate that matchup.
```

## 🔄 Rolling Back (if needed)

If you want to go back to v1.0:
```bash
# Restore your backups
cp app_v1.0_backup.py app.py
cp draft_engine_v1.0_backup.py draft_engine.py

# Restart the app
streamlit run app.py
```

Your game history will remain in the database for when you're ready to upgrade again.

## ✅ Testing Checklist

After updating, verify:
- [ ] App starts without errors
- [ ] All 4 pages appear in sidebar
- [ ] Can log a test game
- [ ] Game appears in history
- [ ] Draft analysis runs (with enemies)
- [ ] "Use personal performance data" toggle works
- [ ] Personal bonus shows in technical breakdown (after 3+ games)
- [ ] Matchup warnings appear (after 2+ games vs enemy)
- [ ] Confidence stars show correctly

## 🆘 Getting Help

If you run into issues:
1. Check the error message in the app
2. Look at the terminal/console output
3. Verify both files were updated
4. Try the initialization script manually
5. Check that mlcounter.db exists and is readable

## 🎯 Next Steps

Now that you have v1.1:
1. **Start logging games** - The more data, the better
2. **Experiment with weights** - Find what works for your playstyle
3. **Review matchup history** - Learn from your patterns
4. **Gather 2+ weeks of data** - Then we'll add Phase 2 (charts/graphs)

Happy drafting! 🎮