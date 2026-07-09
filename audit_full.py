import json

NAME_MAP = {
    "Francia": "France", "Noruega": "Norway", "Paraguay": "Paraguay",
    "Espana": "Spain", "Espagna": "Spain", "Belgica": "Belgium",
    "Suiza": "Switzerland", "Marruecos": "Morocco", "Egipto": "Egypt",
    "Brasil": "Brazil", "Argentina": "Argentina", "Colombia": "Colombia",
    "Canada": "Canada", "Inglaterra": "England", "Mexico": "Mexico",
}

def nn(n):
    return NAME_MAP.get(n, n)

# === 1. wc2026_real_results.json ===
with open("data/wc2026_real_results.json", encoding="utf-8") as f:
    real = json.load(f)

print("=== 1. wc2026_real_results.json - TOTS ELS PARTITS DE FRANCA ===")
for m in real["matches"]:
    t1 = m.get("team1","")
    t2 = m.get("team2","")
    if "France" in [t1,t2] or "Francia" in [t1,t2]:
        score = m.get("score",{})
        ft = score.get("ft","?")
        grp = m.get("group","KNOCKOUT")
        print(f"  {m.get('date')}  [{grp}]  {t1}  {ft}  {t2}")

print()
print("=== 2. live_stats_2026.json (SCRAPER) - PARTITS AMB FRANCA ===")
with open("data/live_stats_2026.json", encoding="utf-8") as f:
    live = json.load(f)

france_matches = []
for m in live["matches"]:
    t1 = m.get("team1","")
    t2 = m.get("team2","")
    if "ranci" in t1.lower() or "ranci" in t2.lower():
        france_matches.append(m)

france_matches.sort(key=lambda x: x.get("date",""))
for m in france_matches:
    t1 = m.get("team1","")
    t2 = m.get("team2","")
    g1 = m.get("g1","?")
    g2 = m.get("g2","?")
    xg1 = m.get("xg1","?")
    xg2 = m.get("xg2","?")
    c1 = m.get("corners1","?")
    c2 = m.get("corners2","?")
    d = m.get("date","?")
    print(f"  {d}  {t1} ({g1}) - ({g2}) {t2}   xG: {xg1}-{xg2}   corners: {c1}-{c2}")

print()
print("=== 3. live_stats_2026.json - NORUEGA FRANCA (tots) ===")
for m in live["matches"]:
    t1 = m.get("team1","").lower()
    t2 = m.get("team2","").lower()
    if ("norueg" in t1 or "norw" in t1) and ("franci" in t2 or "france" in t2):
        print("  TROBAT (local=Noruega):", m)
    if ("norueg" in t2 or "norw" in t2) and ("franci" in t1 or "france" in t1):
        print("  TROBAT (local=France):", m)
