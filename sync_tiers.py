from bs4 import BeautifulSoup
import json
import os

def final_sync():
    # 1. Verification
    html_file = 'official_rank.html'
    json_file = 'hero_data_master.json'
    
    if not os.path.exists(html_file):
        print(f"Error: {html_file} not found!")
        return

    # 2. Parse HTML
    with open(html_file, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f.read(), 'html.parser')

    # 3. Aggressive Data Mining
    # We find all table rows and look for text that looks like a Win Rate (%)
    extracted_data = {}
    for row in soup.find_all(['tr', 'div', 'li']):
        text_content = row.get_text("|", strip=True)
        parts = [p for p in text_content.split("|") if p]
        
        # In the 2026 layout, a valid row has: [Rank, Name, Win%, Pick%, Ban%]
        # Example text: "1|Gloo|58.20%|1.12%|75.40%"
        if len(parts) >= 4 and "%" in parts[2]:
            name = parts[1].strip()
            extracted_data[name] = {
                "win_rate": parts[2],
                "pick_rate": parts[3],
                "ban_rate": parts[4] if len(parts) > 4 else "0%"
            }

    # 4. Merge into JSON
    if not os.path.exists(json_file):
        print(f"Error: {json_file} missing. Please run Phase 1 first!")
        return

    with open(json_file, 'r') as f:
        db = json.load(f)

    updated_count = 0
    for name, stats in extracted_data.items():
        # Fuzzy matching for names like "Yi Sun-shin" vs "Yi Sun-Shin"
        match = next((k for k in db.keys() if name.lower() in k.lower()), None)
        if match:
            db[match].update(stats)
            updated_count += 1

    with open(json_file, 'w') as f:
        json.dump(db, f, indent=4)

    print(f"--- SYNC COMPLETE ---")
    print(f"Successfully integrated real-time data for {updated_count} heroes.")

if __name__ == "__main__":
    final_sync()