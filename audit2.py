import json

# Llegir wc2026_real_results.json - openfootball
with open("data/wc2026_real_results.json", encoding="utf-8") as f:
    real = json.load(f)

print("=== wc2026_real_results.json - PARTITS KNOCKOUT (sense group) ===")
for m in real["matches"]:
    grp = m.get("group")
    score = m.get("score", {})
    ft = score.get("ft")
    if ft is None:
        # Partits sense resultat registrat o format diferent
        print(f"  {m.get('date')} [NO_FT] {m.get('team1')} vs {m.get('team2')} score_keys={list(score.keys())}")
    if not grp and ft:
        print(f"  {m.get('date')} [KNOCKOUT] {m.get('team1')} {ft} {m.get('team2')}")

print()
print("=== ESTRUCTURA: mostrar 3 partits grups i 3 knockout ===")
grp_count = 0
ko_count = 0
for m in real["matches"]:
    grp = m.get("group")
    score = m.get("score", {})
    if grp and grp_count < 3:
        print(f"  GRUP: {m}")
        grp_count += 1
    elif not grp and ko_count < 3:
        print(f"  KNOCKOUT: {m}")
        ko_count += 1
    if grp_count >= 3 and ko_count >= 3:
        break
