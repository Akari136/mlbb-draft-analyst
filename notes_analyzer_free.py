#!/usr/bin/env python3
"""
notes_analyzer_free.py - 100% FREE notes analysis (no APIs needed)

Uses local NLP techniques to extract insights:
- Keyword extraction
- Sentiment analysis
- Pattern matching
- Frequency analysis
- Rule-based insight generation
"""

import json
import sqlite3
import re
from typing import List, Dict, Optional, Set, Tuple
from dataclasses import dataclass
from collections import Counter, defaultdict


@dataclass
class Insight:
    """Single extracted insight"""
    category: str  # 'mistake', 'learning', 'matchup', 'strategy'
    hero: str
    insight: str
    confidence: float  # 0-1
    evidence: List[str]  # Quotes from notes
    frequency: int


class FreeNotesAnalyzer:
    """Free local notes analyzer - no API calls needed"""
    
    def __init__(self, db_path: str = "mlcounter.db"):
        self.db_path = db_path
        
        # Pattern dictionaries (expandable)
        self.mistake_patterns = {
            'early_trade': [
                r'traded? too early',
                r'without level \d',
                r'before level \d',
                r'rushed? level',
                r'ignored? (?:his|her|their) damage',
            ],
            'forgot': [
                r'forgot',
                r'didn\'t remember',
                r'should have remembered',
                r'keep forgetting',
            ],
            'positioning': [
                r'bad position',
                r'wrong position',
                r'got caught',
                r'out of position',
            ],
            'timing': [
                r'too late',
                r'too soon',
                r'bad timing',
                r'wrong time',
            ],
            'spell_usage': [
                r'wasted? (?:spell|skill)',
                r'used? .* too early',
                r'(?:spell|skill) on cooldown',
            ],
        }
        
        self.learning_patterns = {
            'power_spike': [
                r'level \d+ (?:power|spike|advantage)',
                r'strong at level',
                r'wait for level',
            ],
            'counter_play': [
                r'counter',
                r'can beat',
                r'weak against',
                r'strong against',
            ],
            'strategy': [
                r'(?:good|better) to',
                r'should (?:have )?',
                r'learned? that',
                r'realized? that',
            ],
        }
        
        self.enemy_threat_words = [
            'dangerous', 'strong', 'hard', 'difficult', 'problematic',
            'struggle', 'struggled', 'trouble', 'pain', 'annoying'
        ]
        
        self.success_words = [
            'good', 'great', 'dominated', 'easy', 'won', 'outplayed',
            'perfect', 'excellent', 'strong', 'advantage'
        ]
    
    def get_all_notes(self, hero: Optional[str] = None) -> List[Dict]:
        """Retrieve all game notes"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        
        if hero:
            cur.execute("""
                SELECT game_id, your_hero, enemies, date, result, notes
                FROM game_history
                WHERE notes IS NOT NULL 
                  AND LENGTH(notes) >= 10
                  AND your_hero = ?
                ORDER BY date DESC
            """, (hero,))
        else:
            cur.execute("""
                SELECT game_id, your_hero, enemies, date, result, notes
                FROM game_history
                WHERE notes IS NOT NULL 
                  AND LENGTH(notes) >= 10
                ORDER BY date DESC
            """)
        
        rows = cur.fetchall()
        conn.close()
        
        notes = []
        for row in rows:
            note = dict(row)
            note['enemies'] = json.loads(note['enemies']) if note['enemies'] else []
            notes.append(note)
        
        return notes
    
    def extract_mistakes(self, notes: List[Dict]) -> List[Insight]:
        """Extract mistake patterns from notes"""
        insights = []
        
        # Group by hero
        by_hero = defaultdict(list)
        for note in notes:
            by_hero[note['your_hero']].append(note)
        
        for hero, hero_notes in by_hero.items():
            mistake_findings = defaultdict(list)
            
            for note in hero_notes:
                text = note['notes'].lower()
                
                # Check each mistake pattern
                for mistake_type, patterns in self.mistake_patterns.items():
                    for pattern in patterns:
                        if re.search(pattern, text, re.IGNORECASE):
                            mistake_findings[mistake_type].append({
                                'note': note['notes'],
                                'game_id': note['game_id'],
                                'result': note['result']
                            })
                            break  # Only count once per note
            
            # Generate insights for frequent mistakes
            for mistake_type, occurrences in mistake_findings.items():
                if len(occurrences) >= 2:  # At least 2 occurrences
                    # Calculate confidence based on frequency
                    confidence = min(len(occurrences) / 5.0, 1.0)
                    
                    # Generate recommendation
                    recommendation = self._generate_mistake_recommendation(
                        mistake_type, occurrences, hero
                    )
                    
                    insights.append(Insight(
                        category='mistake',
                        hero=hero,
                        insight=recommendation,
                        confidence=confidence,
                        evidence=[o['note'] for o in occurrences[:3]],
                        frequency=len(occurrences)
                    ))
        
        return insights
    
    def _generate_mistake_recommendation(
        self, 
        mistake_type: str, 
        occurrences: List[Dict],
        hero: str
    ) -> str:
        """Generate actionable recommendation from mistake pattern"""
        
        recommendations = {
            'early_trade': f"Avoid trading aggressively before power spikes. Wait for level advantage.",
            'forgot': f"Create mental checklist: enemy abilities, cooldowns, ranges.",
            'positioning': f"Improve map awareness. Position behind tanks in team fights.",
            'timing': f"Practice ability timing in training mode. Watch replays to study timing.",
            'spell_usage': f"Save key spells for critical moments. Don't waste on minions.",
        }
        
        return recommendations.get(mistake_type, f"Review {mistake_type} pattern in notes")
    
    def extract_matchup_insights(self, notes: List[Dict]) -> List[Insight]:
        """Extract hero vs enemy matchup patterns"""
        insights = []
        
        # Group by hero + enemy combinations
        matchups = defaultdict(lambda: {'wins': [], 'losses': [], 'notes': []})
        
        for note in notes:
            hero = note['your_hero']
            for enemy in note['enemies']:
                key = f"{hero}_vs_{enemy}"
                matchups[key]['notes'].append(note['notes'].lower())
                
                if note['result'] == 'Win':
                    matchups[key]['wins'].append(note)
                else:
                    matchups[key]['losses'].append(note)
        
        # Analyze each matchup
        for matchup_key, data in matchups.items():
            if len(data['notes']) < 2:  # Need at least 2 games
                continue
            
            hero, enemy = matchup_key.split('_vs_')
            combined_notes = ' '.join(data['notes'])
            
            # Check for threat indicators
            threat_count = sum(
                1 for word in self.enemy_threat_words 
                if word in combined_notes
            )
            
            success_count = sum(
                1 for word in self.success_words
                if word in combined_notes
            )
            
            total_games = len(data['wins']) + len(data['losses'])
            win_rate = len(data['wins']) / total_games if total_games > 0 else 0
            
            # Generate insight
            if threat_count >= 2 or win_rate < 0.4:
                # Difficult matchup
                insight_text = f"Struggles vs {enemy}: {len(data['losses'])}L-{len(data['wins'])}W. "
                
                # Try to extract specific issue
                if 'damage' in combined_notes:
                    insight_text += "Enemy damage is problematic. Consider defensive items."
                elif 'range' in combined_notes or 'distance' in combined_notes:
                    insight_text += "Range/positioning issue. Play safer."
                elif 'level' in combined_notes:
                    insight_text += "Level-dependent matchup. Respect power spikes."
                else:
                    insight_text += "Review matchup fundamentals."
                
                insights.append(Insight(
                    category='matchup',
                    hero=hero,
                    insight=insight_text,
                    confidence=min(total_games / 5.0, 1.0),
                    evidence=data['notes'][:2],
                    frequency=total_games
                ))
            
            elif success_count >= 2 or win_rate > 0.6:
                # Favorable matchup
                insight_text = f"Strong vs {enemy}: {len(data['wins'])}W-{len(data['losses'])}L. Good matchup for {hero}."
                
                insights.append(Insight(
                    category='matchup',
                    hero=hero,
                    insight=insight_text,
                    confidence=min(total_games / 5.0, 1.0),
                    evidence=data['notes'][:2],
                    frequency=total_games
                ))
        
        return insights
    
    def extract_learnings(self, notes: List[Dict]) -> List[Insight]:
        """Extract positive learnings and strategies"""
        insights = []
        
        by_hero = defaultdict(list)
        for note in notes:
            by_hero[note['your_hero']].append(note)
        
        for hero, hero_notes in by_hero.items():
            learning_findings = defaultdict(list)
            
            for note in hero_notes:
                text = note['notes'].lower()
                
                # Check learning patterns
                for learning_type, patterns in self.learning_patterns.items():
                    for pattern in patterns:
                        if re.search(pattern, text, re.IGNORECASE):
                            learning_findings[learning_type].append(note['notes'])
                            break
            
            # Generate insights
            for learning_type, occurrences in learning_findings.items():
                if len(occurrences) >= 1:  # Even 1 learning is valuable
                    
                    if learning_type == 'power_spike':
                        insight_text = f"Understands {hero} power spikes. Leverage level advantages."
                    elif learning_type == 'counter_play':
                        insight_text = f"Learning {hero} matchups effectively. Continue studying counters."
                    else:
                        insight_text = f"Developing {hero} strategy awareness."
                    
                    insights.append(Insight(
                        category='learning',
                        hero=hero,
                        insight=insight_text,
                        confidence=0.7,
                        evidence=occurrences[:2],
                        frequency=len(occurrences)
                    ))
        
        return insights
    
    def generate_full_analysis(self, hero: Optional[str] = None) -> Dict:
        """Generate complete analysis report"""
        notes = self.get_all_notes(hero)
        
        if not notes:
            return {"error": "No notes found"}
        
        # Extract all insights
        mistakes = self.extract_mistakes(notes)
        matchups = self.extract_matchup_insights(notes)
        learnings = self.extract_learnings(notes)
        
        # Sort by confidence and frequency
        mistakes.sort(key=lambda x: (x.confidence, x.frequency), reverse=True)
        matchups.sort(key=lambda x: (x.confidence, x.frequency), reverse=True)
        learnings.sort(key=lambda x: (x.confidence, x.frequency), reverse=True)
        
        # Generate summary
        summary = {
            'total_notes': len(notes),
            'heroes': list(set(n['your_hero'] for n in notes)),
            'date_range': f"{notes[-1]['date']} to {notes[0]['date']}" if notes else "N/A",
            'insights_found': len(mistakes) + len(matchups) + len(learnings),
        }
        
        return {
            'summary': summary,
            'mistakes': [self._insight_to_dict(i) for i in mistakes],
            'matchups': [self._insight_to_dict(i) for i in matchups],
            'learnings': [self._insight_to_dict(i) for i in learnings],
            'top_recommendations': self._get_top_recommendations(mistakes, matchups, learnings),
        }
    
    def _insight_to_dict(self, insight: Insight) -> Dict:
        """Convert Insight to dictionary"""
        return {
            'category': insight.category,
            'hero': insight.hero,
            'insight': insight.insight,
            'confidence': round(insight.confidence, 2),
            'evidence_count': len(insight.evidence),
            'evidence': insight.evidence,
            'frequency': insight.frequency,
        }
    
    def _get_top_recommendations(
        self, 
        mistakes: List[Insight],
        matchups: List[Insight],
        learnings: List[Insight]
    ) -> List[Dict]:
        """Get top 5 actionable recommendations"""
        
        all_insights = []
        
        # Prioritize high-confidence mistakes
        for m in mistakes[:3]:
            all_insights.append({
                'priority': 'HIGH',
                'type': 'Mistake to Fix',
                'hero': m.hero,
                'recommendation': m.insight,
                'impact': f"Seen {m.frequency}x - {int(m.confidence*100)}% confidence",
            })
        
        # Add difficult matchups
        for match in matchups[:2]:
            if 'Struggles' in match.insight:
                all_insights.append({
                    'priority': 'MEDIUM',
                    'type': 'Matchup to Avoid/Practice',
                    'hero': match.hero,
                    'recommendation': match.insight,
                    'impact': f"{match.frequency} games noted",
                })
        
        # Add positive learnings
        for learn in learnings[:1]:
            all_insights.append({
                'priority': 'LOW',
                'type': 'Keep Improving',
                'hero': learn.hero,
                'recommendation': learn.insight,
                'impact': 'Positive pattern',
            })
        
        return all_insights[:5]


# Quick test function
if __name__ == "__main__":
    analyzer = FreeNotesAnalyzer("mlcounter.db")
    
    notes = analyzer.get_all_notes()
    print(f"Found {len(notes)} notes\n")
    
    if notes:
        analysis = analyzer.generate_full_analysis()
        print(json.dumps(analysis, indent=2))