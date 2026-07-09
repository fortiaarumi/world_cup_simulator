import json

with open("data/live_stats_2026.json", encoding="utf-8") as f:
    data = json.load(f)

matches = data["matches"]
print(f"Total partits al JSON: {len(matches)}")

# 1. DUPLICATS: cerca tots els parells (team1,team2) que apareixen mes d'un cop
from collections import Counter
pair_counts = Counter()
for m in matches:
    key = (m.get("team1","").lower(), m.get("team2","").lower())
    pair_counts[key] += 1

print("\n=== PARELLS DUPLICATS (apareixen mes d'un cop) ===")
dup_found = False
for (t1, t2), cnt in sorted(pair_counts.items(), key=lambda x: -x[1]):
    if cnt > 1:
        dup_found = True
        print(f"  {cnt}x  {t1} vs {t2}")
        # Mostrar tots els partits d'aquest parell
        for m in matches:
            if m.get("team1","").lower() == t1 and m.get("team2","").lower() == t2:
                print(f"       -> data={m.get('date')}  g1={m.get('g1')} g2={m.get('g2')}  xg={m.get('xg1')}/{m.get('xg2')}  corners={m.get('corners1')}/{m.get('corners2')}")
if not dup_found:
    print("  Cap duplicat exacte per (team1, team2)")

# 2. Cerca especifica: tots els partits amb Noruega i Franca (en qualsevol ordre)
print("\n=== TOTS ELS PARTITS: Noruega <-> Franca (totes les combinacions) ===")
for m in matches:
    t1 = m.get("team1","").lower()
    t2 = m.get("team2","").lower()
    has_nor = "norueg" in t1 or "norueg" in t2 or "norw" in t1 or "norw" in t2
    has_fra = "franci" in t1 or "franci" in t2 or "france" in t1 or "france" in t2
    if has_nor and has_fra:
        print(f"  data={m.get('date')}  {m.get('team1')} {m.get('g1')}-{m.get('g2')} {m.get('team2')}  xg={m.get('xg1')}/{m.get('xg2')}  corners={m.get('corners1')}/{m.get('corners2')}")

# 3. Analisi de la logica de deduplicacio del scraper (linia 140-144)
print("\n=== ANALISI LOGICA DE DEDUPLICACIO DEL SCRAPER ===")
print("  El scraper comprova: m['team1'] == match_data['team1'] AND m['team2'] == match_data['team2']")
print("  Si el nou partit te l'ordre INVERS (equips intercanviats), NO detecta el duplicat -> afegeix NOU registre")
print("  Exemple: 'Noruega' vs 'Francia' (amistoso) != 'Francia' vs 'Noruega' (Mundial) -> dos registres separats")
print()
print("  PERO si la URL de Flashscore apunta al MATEIX amistoso amb el mateix ordre, SI actualitza.")

# 4. Comprovar les URLs actuals de ro16_urls.txt
print("\n=== URLS ro16_urls.txt - ANALISI ===")
print("  URL Franca-Paraguay:")
print("  https://flashscore.es/partido/futbol/FRANCIA/PARAGUAY/?mid=M5YPKKbB")
print("  -> Franca apareix primer (team1=Franca, team2=Paraguay)")
print("  -> Pero al JSON tenim: Paraguay(0)-Francia(0) -> ORDRE INVERS!")
print("  -> Explicacio: el scraper captura participantName en l'ordre del DOM,")
print("     que a Flashscore pot ser visitant-local o local-visitant depenent de la pagina")
print()

# 5. Analisi del detailScore: com captura el marcador
print("=== DETALL DEL PROBLEMA DEL MARCADOR ===")
print("  Codi: marcador = soup.find(class_=lambda x: x and 'detailScore' in x)")
print("  Resultat del find: el primer element amb 'detailScore' a la classe")
print("  Format esperat: '1-0' o '0-0'")
print()
print("  PROBLEMA DETECTAT: per partits acabats en Flashscore,")
print("  el 'detailScore' pot contenir text com '1 - 0' (amb espais)")
print("  o pot estar en un subelement. El parse:")
print("  g1 = int(resultado.split('-')[0])  # agafa la part ESQUERRA del -")
print("  Si el format es '1 - 0', split('-') dona ['1 ', ' 0']")
print("  i int('1 ') funciona be (Python ignora espais en int())")
print()
print("  PERO si el format a Flashscore d'un partit acabat es diferent")
print("  (ex: nomes mostra el temps extra, o el resultat als penals),")
print("  el parse pot fallar i retornar 0-0 per defecte (parse_int falla silenciosament)")

print("\n=== CONCLUSIO: per que molts partits surten 0-0? ===")
print("  Hipotesi 1 (mes probable): el 'detailScore' de Flashscore per partits")
print("  JA ACABATS mostra el resultat en un format diferent al dels partits en directe.")
print("  Ex: pot mostrar '1\\n-\\n0' en elements separats, o pot estar en un span")
print("  que el selector de clase no captura correctament.")
print()
print("  Hipotesi 2: el CSS class 'detailScore' ha canviat en la versio actual de Flashscore.")
print("  El scraper usa classes CSS que poden variar amb actualitzacions del lloc web.")
