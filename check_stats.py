import json
try:
    with open('data/live_stats_2026.json', encoding='utf-8') as f:
        d = json.load(f)
    print(f"Total partits guardats: {len(d['matches'])}")
    print("Últims 16 partits guardats:")
    for m in d['matches'][-16:]:
        print(f"  {m['date']}: {m['team1']} {m['g1']}-{m['g2']} {m['team2']}")
except Exception as e:
    print(f"Error: {e}")
