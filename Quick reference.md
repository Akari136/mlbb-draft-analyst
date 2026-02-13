# 🎮 MLBB Draft Analyst - Quick Reference Card

## 📱 5 Pages

### 🎯 Draft Analysis
**What:** Get hero recommendations based on enemies
**When:** Before picking in ranked
**Shows:**
- Top 10 recommended heroes (scored)
- Personal win rate + confidence (⭐⭐⭐)
- Counter matchups (strong/weak)
- Meta bonuses (tier, win rate)
- ⚠️ Matchup warnings from your history
- Personal KDA with each hero

**Controls:**
- Hero pool (manual or lane preset)
- Enemy picks
- Teammate picks (for future synergy)
- Banned heroes
- Weights (sidebar)
- Personal performance toggle

---

### 📝 Log Game
**What:** Record match results
**When:** After every game (while fresh!)
**Enter:**
- Date, hero, role, result
- KDA (kills/deaths/assists)
- MVP status
- Teammates (4)
- Enemies (5)
- **Notes** (MOST IMPORTANT! Be detailed!)

**Good Note Examples:**
✅ "Traded too early vs Alpha, ignored his sustain"
✅ "Forgot Kalea ult range, got pulled in teamfight"
✅ "Level 2 spike worked great, dominated lane"

❌ "Good game" (too vague)
❌ "Lost" (no insight)

---

### 📊 Game History
**What:** View stats + visual trends
**When:** Weekly review, before ranked sessions
**Tabs:**
- **Overview:** Win rate trend, role distribution
- **Hero Performance:** Compare all heroes (charts!)
- **Enemy Matchups:** Win rates vs specific enemies
- **Trends:** Day-of-week performance, long-term trends

**Insights:**
- Best/worst heroes (by WR)
- Best/worst days (by WR)
- Problematic enemies
- Performance trends

---

### 🧠 Notes Insights
**What:** Extract patterns from your notes
**When:** After 10-20 games, before ranked push
**Options:**
1. **🤖 AI Analysis (Gemini)** - Deep, contextual insights (FREE!)
2. **Smart Pattern Analysis** - Fast, offline pattern matching
3. **Simple Stats** - Just numbers

**AI Finds:**
- ❌ Repeated mistakes (with frequency)
- 💡 Key learnings
- ⚔️ Matchup patterns
- 🎯 Priority recommendations

**Needs:** Gemini API key (free from makersuite.google.com)

---

### ⚙️ Settings
**What:** Database management
**When:** Rarely (usually never)
**Actions:**
- View stats (total games logged)
- Clear all history (danger zone!)

---

## 🎯 Typical Workflow

### Before Ranked Session:
1. **Check Game History** - Review recent performance
2. **Check Notes Insights** - Review AI recommendations
3. **Note problematic matchups** - Who to avoid
4. **Note best heroes** - Who you're hot with

### During Draft:
1. Open **Draft Analysis**
2. Add **enemy picks** as they appear
3. Add **teammate picks**
4. Add **bans**
5. Select your **hero pool** (or lane preset)
6. Click **🚀 Run Analysis**
7. Pick from **top 3 recommendations**
8. Watch for **⚠️ warnings**

### After Game:
1. Go to **Log Game**
2. Enter all details
3. **Write detailed notes!** (this is the gold!)
4. Save

### Weekly Review:
1. **Game History** → Check trends
2. **Notes Insights** → Run AI analysis
3. Apply **top recommendations**
4. Repeat!

---

## 🔑 Key Features to Maximize

### ⭐ Personal Performance (v1.1)
- Tracks YOUR win rate per hero
- Learns YOUR matchup history
- Warns about YOUR bad matchups
- Confidence levels (⭐⭐⭐ = reliable data)

**Example:**
```
#1 Thamuz (Score: 7.4) ⭐⭐⭐
Your WR: 70% (10 games)
⚠️ You're 1-4 vs Fredrinn

Reasoning: 
- Strong vs Yuzhong (+1.25)
- Your WR: 70% ⭐⭐⭐ (+1.60)
- Tier S (+0.90)
```

### 📊 Visual Insights (v1.2 - Phase 2)
- **Trend charts** show improvement over time
- **Hero comparisons** reveal best performers
- **Day analysis** finds optimal play times
- **Enemy charts** highlight problem matchups

### 🤖 AI Analysis (v1.2 - Phase 2)
- Understands **context** (not just keywords)
- Finds **creative insights**
- Ranks by **priority**
- Explains **why** + **how to fix**

**Example AI Output:**
```
🔴 HIGH PRIORITY
Mistake: Trading before level 2 power spike
Seen: 3 times (67% of losses mention this)
Fix: Wait for level 2, then all-in
Impact: Could prevent 2-3 deaths per game
```

---

## 💡 Pro Tips

1. **Write detailed notes!**
   - Note specific mistakes
   - Note what worked
   - Note enemy abilities you forgot
   - Note timing issues

2. **Log consistently**
   - Don't skip games
   - Log immediately (memory fades!)
   - Even log losses (especially losses!)

3. **Trust the data**
   - If you're 1-5 with a hero, **don't pick it**
   - If you're 5-1 vs an enemy, **capitalize**
   - Let stats override feelings

4. **Use AI weekly**
   - Don't spam it daily (same insights)
   - Run after 10-20 new games
   - Apply recommendations, then test

5. **Review before sessions**
   - Quick check of best heroes
   - Quick check of worst matchups
   - Mental prep for draft

---

## 🆓 Cost: $0

| Feature | API/Service | Cost | Limit |
|---------|-------------|------|-------|
| Draft Analysis | Local | $0 | ∞ |
| Game Logging | SQLite | $0 | ∞ |
| Pattern Analysis | Local | $0 | ∞ |
| Charts/Graphs | Local | $0 | ∞ |
| AI Analysis | Gemini | $0 | 1,500/day |

**Perfect for students! No credit card ever needed!** 🎓

---

## 📈 Success Metrics

Track your improvement:
- ✅ Win rate increasing? (check trends tab)
- ✅ Fewer repeated mistakes? (AI analysis)
- ✅ Better hero pool? (performance charts)
- ✅ Improved KDA? (hero stats)

**Goal:** 5-10% win rate improvement after 2-3 weeks!

---

## 🚨 Quick Troubleshooting

**"No personal history"**
→ Play 3+ games with that hero

**"Charts not showing"**
→ Need visualizations.py file

**"Gemini API error"**
→ Check GEMINI_API_KEY environment variable

**"No insights found"**
→ Write more detailed notes!

**"Confidence: low ⭐"**
→ Play more games (need 5+ for ⭐⭐⭐)

---

## 🎯 Bottom Line

1. **Log every game** with detailed notes
2. **Use AI weekly** to extract insights
3. **Check charts** before ranked
4. **Apply recommendations**
5. **Track improvement**
6. **Climb ranks!** 🚀

**Your notes are GOLD. The AI turns them into DIAMONDS.** 💎