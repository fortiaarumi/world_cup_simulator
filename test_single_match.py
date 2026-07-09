"""
test_single_match.py
====================
Resca UN sol partit de Flashscore i imprimeix totes les estadistiques
que troba. Serveix per verificar que les claus de targetes i xG son correctes
abans de llençar el scraper complet.
"""
import json
import time
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

# URL de prova: Brasil vs Escocia (24/06/2026) - sabem que te estadistiques
URL = "https://www.flashscore.es/partido/futbol/brasil-I9l9aqLq/escocia-fZRU25WH/resumen/estadisticas/general/?mid=EgVZxtj1"

print("=" * 60)
print("  TEST DE RASCADA - UN PARTIT")
print(f"  URL: ...brasil...escocia...")
print("=" * 60)

opciones = Options()
# Mode visible (igual que el scraper principal)
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=opciones)

try:
    driver.get(URL)

    # Acceptar cookies
    try:
        cookie_btn = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.ID, "onetrust-accept-btn-handler"))
        )
        cookie_btn.click()
        print("  Cookies acceptades automaticament!")
        time.sleep(0.8)
    except:
        print("  (Cap banner de cookies detectat - ja estaven acceptades)")

    # Esperar el nom dels equips
    try:
        WebDriverWait(driver, 8).until(EC.presence_of_element_located((By.CSS_SELECTOR, ".participantName")))
    except:
        pass

    # Esperar les estadistiques
    try:
        WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.CLASS_NAME, "stat__category")))
        print("  Estadistiques carregades (stat__category trobat)!")
    except:
        print("  AVIS: stat__category no trobat - esperant 3 seg mes...")
        time.sleep(3)

    soup = BeautifulSoup(driver.page_source, 'html.parser')

    # Extreure equips i resultat
    equips = soup.find_all('a', class_=lambda x: x and 'participantName' in x)
    noms = [e.text.strip() for e in equips if e.text.strip()][:2]
    marcador = soup.find(class_=lambda x: x and 'detailScore' in x)
    print(f"\n  Equips: {noms}")
    print(f"  Resultat: {marcador.text.strip() if marcador else 'N/A'}")

    # Extreure TOTES les estadistiques
    stats = {}
    for div in soup.find_all('div'):
        hijos = div.find_all('div', recursive=False)
        if len(hijos) == 3:
            vl  = hijos[0].text.strip()
            cat = hijos[1].text.strip()
            vv  = hijos[2].text.strip()
            if vl and cat and vv and any(c.isalpha() for c in cat) and len(cat) < 40:
                stats[cat] = {'local': vl, 'visitante': vv}

    print(f"\n  Total categories trobades: {len(stats)}")
    print("\n  ESTADISTIQUES COMPLETES:")
    for k, v in stats.items():
        print(f"    '{k}': local={v['local']}  visitant={v['visitante']}")

    # Comprovació específica dels camps crítics
    print("\n" + "=" * 60)
    print("  COMPROVACIO CAMPS CRITICS:")
    print("=" * 60)

    xg_keys = [k for k in stats if 'xg' in k.lower() or 'esperado' in k.lower() or 'esperats' in k.lower()]
    card_keys = [k for k in stats if 'tarjeta' in k.lower() or 'card' in k.lower()]
    corner_keys = [k for k in stats if 'corner' in k.lower() or 'rnere' in k.lower() or 'esquina' in k.lower()]

    print(f"\n  xG keys trobades: {xg_keys}")
    for k in xg_keys:
        print(f"    -> '{k}': {stats[k]}")

    print(f"\n  Targetes keys trobades: {card_keys}")
    for k in card_keys:
        print(f"    -> '{k}': {stats[k]}")

    print(f"\n  Corners keys trobades: {corner_keys}")
    for k in corner_keys:
        print(f"    -> '{k}': {stats[k]}")

    # Simulem el formatear_para_simulador per veure que guardaria
    def parse_float(val):
        try:
            return float(str(val).replace(',', '.'))
        except:
            return None

    def parse_int(val):
        try:
            return int(val)
        except:
            return 0

    xg1 = parse_float((stats.get('Goles esperados (xG)', {}) or stats.get('xG', {})).get('local', '0'))
    xg2 = parse_float((stats.get('Goles esperados (xG)', {}) or stats.get('xG', {})).get('visitante', '0'))
    c1  = parse_int((stats.get('Córneres', {}) or stats.get('Corners', {}) or stats.get('Saques de esquina', {})).get('local', '0'))
    c2  = parse_int((stats.get('Córneres', {}) or stats.get('Corners', {}) or stats.get('Saques de esquina', {})).get('visitante', '0'))
    card1 = parse_int(stats.get('Tarjetas amarillas', {}).get('local', '0')) + parse_int(stats.get('Tarjetas rojas', {}).get('local', '0'))
    card2 = parse_int(stats.get('Tarjetas amarillas', {}).get('visitante', '0')) + parse_int(stats.get('Tarjetas rojas', {}).get('visitante', '0'))

    print(f"\n  EL QUE GUARDARIA AL JSON:")
    print(f"    xg1 = {xg1}  |  xg2 = {xg2}")
    print(f"    corners1 = {c1}  |  corners2 = {c2}")
    print(f"    cards1 = {card1}  |  cards2 = {card2}")
    if xg1 and xg1 > 0:
        print("\n  xG FUNCIONA!")
    else:
        print("\n  xG encara a 0 - clau incorrecta o no disponible")
    if card1 + card2 > 0:
        print("  TARGETES FUNCIONEN!")
    else:
        print("  Targetes a 0 - clau incorrecta o no disponible")

finally:
    input("\nPrem Enter per tancar el navegador...")
    driver.quit()
    print("Navegador tancat.")
