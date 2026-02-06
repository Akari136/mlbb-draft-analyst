import json

META = "hero_data_master.json"  # change to your filename

with open(META, "r", encoding="utf-8") as f:
    data = json.load(f)

print("type:", type(data))
print("keys/sample:", list(data)[:5] if isinstance(data, dict) else "list format")

# Try one hero you know exists
hero = "Atlas"

if isinstance(data, dict):
    print("Atlas meta:", data.get(hero))
else:
    # list of objects? try find
    found = next((x for x in data if x.get("hero")==hero or x.get("name")==hero), None)
    print("Atlas meta:", found)
