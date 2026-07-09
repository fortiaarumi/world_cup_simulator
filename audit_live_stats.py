import json

try:
    with open("data/live_stats_2026.json", "r", encoding="utf-8") as f:
        data = json.load(f)
except FileNotFoundError:
    print("No s'ha trobat data/live_stats_2026.json")
    exit()

matches = data.get("matches", [])
print(f"Total partits a live_stats_2026.json: {len(matches)}")

print("\n=== RESULTAT DE NORUEGA - FRANÇA ===")
for m in matches:
    t1 = m["team1"].lower()
    t2 = m["team2"].lower()
    if ("norueg" in t1 or "norw" in t1 or "norueg" in t2 or "norw" in t2) and \
       ("franc" in t1 or "franc" in t2):
        print(f"[{m['date']}] {m['team1']} {m['g1']} - {m['g2']} {m['team2']}")
        print(f"   -> xG: {m['xg1']} - {m['xg2']}")
        print(f"   -> Corners: {m['corners1']} - {m['corners2']}")

print("\n=== POSSIBLES MARCADORS INCORRECTES (0-0, 0-1, etc. que podrien ser errors de HT) ===")
# Considerem "sospitosos" els partits 0-0 que sabem que van fallar als vuitens
# O partits amb molts xG pero 0 gols
suspicious = []
for m in matches:
    # Mostrem tots els que son de Juliol (vuitens de final aprox)
    date_parts = m['date'].split('.')
    if len(date_parts) == 3 and date_parts[1] == "07" and date_parts[2] == "2026":
        suspicious.append(m)
    elif m['g1'] == 0 and m['g2'] == 0:
        suspicious.append(m)

# Mostrarem només una llista de 20 per no saturar
for m in suspicious[:25]:
    print(f"[{m['date']}] {m['team1']} {m['g1']} - {m['g2']} {m['team2']}  (xG: {m['xg1']} - {m['xg2']})")
if len(suspicious) > 25:
    print(f"... i {len(suspicious) - 25} partits mes amagats.")

