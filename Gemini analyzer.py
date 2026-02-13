"""
Google Gemini API Integration - 100% FREE!

Gemini offers generous free tier:
- 15 requests per minute
- 1 million tokens per minute
- 1,500 requests per day

Perfect for hobby projects!
"""

import json
import os
from typing import List, Dict, Optional

# You'll need: pip install google-generativeai
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False


class GeminiNotesAnalyzer:
    """AI-powered notes analysis using FREE Google Gemini API"""
    
    def __init__(self, api_key: Optional[str] = None):
        if not GEMINI_AVAILABLE:
            raise ImportError("google-generativeai not installed. Run: pip install google-generativeai")
        
        # Try to get API key from environment or parameter
        self.api_key = api_key or os.getenv('GEMINI_API_KEY')
        
        if not self.api_key:
            raise ValueError(
                "Gemini API key required. Get free key at: "
                "https://makersuite.google.com/app/apikey"
            )
        
        # Configure Gemini
        genai.configure(api_key=self.api_key)
        
        # Use Gemini 1.5 Flash (fastest, still free)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
    
    def analyze_notes(self, notes: List[Dict], focus: str = "all") -> Dict:
        """
        Analyze game notes using Gemini AI
        
        Args:
            notes: List of game note dictionaries
            focus: 'mistakes', 'learnings', 'matchups', 'strategy', 'all'
        
        Returns:
            Dictionary with categorized insights
        """
        if not notes:
            return {"error": "No notes to analyze"}
        
        # Build the prompt
        prompt = self._build_analysis_prompt(notes, focus)
        
        try:
            # Call Gemini API
            response = self.model.generate_content(prompt)
            
            # Parse JSON response
            insights = self._parse_ai_response(response.text)
            
            return {
                "success": True,
                "total_notes_analyzed": len(notes),
                "insights": insights,
                "model": "gemini-1.5-flash",
                "cost": "FREE! 🎉"
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "fallback": "Use pattern-based analysis instead"
            }
    
    def _build_analysis_prompt(self, notes: List[Dict], focus: str) -> str:
        """Build analysis prompt for Gemini"""
        
        # Group notes by hero
        by_hero = {}
        for note in notes:
            hero = note['your_hero']
            if hero not in by_hero:
                by_hero[hero] = []
            by_hero[hero].append(note)
        
        prompt = f"""You are analyzing Mobile Legends: Bang Bang game notes from a player.
Extract actionable insights from these {len(notes)} game notes.

NOTES DATA:
"""
        
        for hero, hero_notes in by_hero.items():
            prompt += f"\n{hero} ({len(hero_notes)} games):\n"
            for note in hero_notes:
                enemies_str = ", ".join(note['enemies']) if note['enemies'] else "Unknown"
                prompt += f"  [{note['result']}] vs {enemies_str}: {note['notes']}\n"
        
        prompt += """

TASK: Analyze these notes and extract:

1. REPEATED MISTAKES
   - What errors appear multiple times?
   - Hero-specific bad habits?
   - Timing/positioning mistakes?

2. KEY LEARNINGS  
   - What strategies worked well?
   - Counter-play discoveries?
   - Power spike awareness?

3. MATCHUP PATTERNS
   - Which enemies are problematic?
   - Favorable matchups?
   - Specific strategies per matchup?

4. TOP RECOMMENDATIONS
   - Most important improvements to make
   - Prioritized by impact

OUTPUT FORMAT (valid JSON only):
{
  "mistakes": [
    {
      "hero": "Thamuz",
      "pattern": "Trading aggressively before level 2",
      "frequency": 3,
      "evidence": ["quote from note 1", "quote from note 2"],
      "recommendation": "Wait for level 2 power spike before all-ins",
      "severity": "high"
    }
  ],
  "learnings": [
    {
      "hero": "Thamuz",
      "insight": "Level 2 timing is critical for trades",
      "context": "Multiple notes mention level advantage",
      "application": "Use level 2 spike to dominate lane"
    }
  ],
  "matchups": [
    {
      "hero": "Thamuz",
      "enemy": "Alpha",
      "pattern": "Struggling with early trades",
      "win_rate_noted": "33%",
      "tip": "Harass from range before committing. Alpha sustain negates early damage."
    }
  ],
  "top_recommendations": [
    {
      "priority": "HIGH",
      "type": "Mistake to Fix",
      "hero": "Thamuz",
      "recommendation": "Respect level timings in early game",
      "impact": "Will improve lane phase in 80% of games"
    }
  ]
}

IMPORTANT: 
- Return ONLY valid JSON, no markdown formatting
- Be specific and actionable
- Base insights on actual note content
- Include evidence quotes from notes
"""
        
        return prompt
    
    def _parse_ai_response(self, response_text: str) -> Dict:
        """Parse Gemini's response into structured format"""
        
        # Clean up response (remove markdown if present)
        cleaned = response_text.strip()
        
        # Remove markdown code blocks if present
        if cleaned.startswith('```json'):
            cleaned = cleaned[7:]
        if cleaned.startswith('```'):
            cleaned = cleaned[3:]
        if cleaned.endswith('```'):
            cleaned = cleaned[:-3]
        
        cleaned = cleaned.strip()
        
        try:
            insights = json.loads(cleaned)
            return insights
        except json.JSONDecodeError as e:
            # If parsing fails, return error with raw text
            return {
                "parse_error": str(e),
                "raw_response": response_text,
                "suggestion": "AI response was not valid JSON. Using pattern analysis instead."
            }
    
    def quick_summarize(self, notes: List[Dict], max_notes: int = 10) -> str:
        """Quick text summary of notes (lightweight request)"""
        
        if not notes:
            return "No notes to summarize."
        
        # Limit notes to avoid token overuse
        notes_sample = notes[:max_notes]
        
        prompt = f"Summarize these {len(notes_sample)} Mobile Legends game notes in 2-3 sentences:\n\n"
        
        for note in notes_sample:
            prompt += f"[{note['result']}] {note['your_hero']}: {note['notes']}\n"
        
        prompt += "\nProvide a brief, actionable summary of the main patterns you see."
        
        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            return f"Error generating summary: {e}"


# Utility functions
def get_gemini_api_key_instructions() -> str:
    """Return instructions for getting free Gemini API key"""
    return """
# How to Get FREE Gemini API Key

1. Go to: https://makersuite.google.com/app/apikey
2. Click "Create API Key"
3. Copy the key
4. Add to your environment:
   
   Option A (Recommended):
   - Create a file named `.env` in your project folder
   - Add line: GEMINI_API_KEY=your_key_here
   
   Option B:
   - Set environment variable:
     Windows: setx GEMINI_API_KEY "your_key_here"
     Mac/Linux: export GEMINI_API_KEY="your_key_here"

FREE TIER LIMITS (Very Generous):
- 15 requests per minute
- 1 million tokens per minute  
- 1,500 requests per day
- Plenty for hobby projects!

No credit card required! 🎉
"""


def test_gemini_connection(api_key: str) -> bool:
    """Test if Gemini API key works"""
    try:
        analyzer = GeminiNotesAnalyzer(api_key)
        test_notes = [{
            'your_hero': 'Thamuz',
            'enemies': ['Alpha'],
            'result': 'Win',
            'notes': 'Good game'
        }]
        result = analyzer.quick_summarize(test_notes)
        return True
    except Exception as e:
        print(f"Connection test failed: {e}")
        return False


if __name__ == "__main__":
    # Test script
    print("Testing Gemini Integration...")
    print(get_gemini_api_key_instructions())
    
    # Try to analyze sample notes
    api_key = os.getenv('GEMINI_API_KEY')
    if api_key:
        analyzer = GeminiNotesAnalyzer(api_key)
        
        sample_notes = [
            {
                'your_hero': 'Thamuz',
                'enemies': ['Alpha'],
                'result': 'Loss',
                'notes': 'Traded too early without level 2. Got punished by Alpha sustain.'
            },
            {
                'your_hero': 'Thamuz', 
                'enemies': ['Alpha'],
                'result': 'Win',
                'notes': 'Waited for level 2, then all-inned. Dominated lane.'
            }
        ]
        
        print("\nAnalyzing sample notes...")
        result = analyzer.analyze_notes(sample_notes)
        print(json.dumps(result, indent=2))
    else:
        print("\n⚠️ GEMINI_API_KEY not found in environment")
        print("Set it to test the integration")