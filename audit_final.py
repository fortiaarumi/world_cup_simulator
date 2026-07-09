import json

with open("data/live_stats_2026.json", "r", encoding="utf-8") as f:
    live = json.load(f)["matches"]

print("=== VERIFICACIÓ DELS VUITENS DE FINAL (FT) ===")
vuitens = []
for m in live:
    date_parts = m['date'].split('.')
    if len(date_parts) == 3 and date_parts[1] == "07" and date_parts[2] == "2026":
        # Tots els partits de juliol
        vuitens.append(m)

for m in vuitens:
    print(f"{m['date']}: {m['team1']} {m['g1']}-{m['g2']} {m['team2']} | xG: {m['xg1']}-{m['xg2']}")

print("\n=== VERIFICACIÓ D'EMPAT ALS VUITENS ===")
for m in vuitens:
    if m['g1'] == m['g2']:
        print(f"ATENCIÓ: Empat detectat a eliminatòries: {m['team1']} {m['g1']}-{m['g2']} {m['team2']}")
