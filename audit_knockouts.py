import json

try:
    with open("data/live_stats_2026.json", "r", encoding="utf-8") as f:
        data = json.load(f)
except FileNotFoundError:
    print("No s'ha trobat data/live_stats_2026.json")
    exit()

matches = data.get("matches", [])
with open("audit_knockouts.txt", "w", encoding="utf-8") as out:
    out.write("=== PARTITS DEL MUNDIAL DE JULIOL (KNOCKOUTS) EN EL JSON ===\n")
    for m in matches:
        date_parts = m['date'].split('.')
        if len(date_parts) == 3 and date_parts[1] == "07" and date_parts[2] == "2026":
            suspicious = "⚠️ POTENCIALMENT INCORRECTE" if (m['g1'] == 0 and m['g2'] == 0) else ""
            out.write(f"[{m['date']}] {m['team1']} {m['g1']} - {m['g2']} {m['team2']}  {suspicious}\n")
