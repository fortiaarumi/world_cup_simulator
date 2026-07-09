import json
import os
import time
import random
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

def extraer_partido_completo(url, driver):
    datos_partido = {
        'fecha': 'Desconocida', 
        'url': url, 
        'equipo_local': 'Desconocido', 
        'equipo_visitante': 'Desconocido', 
        'resultado': 'Desconocido', 
        'estadisticas': {}
    }
    try:
        driver.get(url)
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.common.by import By
        import time
        # Acceptar cookies automàticament si apareix el banner
        try:
            cookie_btn = WebDriverWait(driver, 4).until(
                EC.element_to_be_clickable((By.ID, "onetrust-accept-btn-handler"))
            )
            cookie_btn.click()
            time.sleep(0.8)
        except:
            pass
        try:
            WebDriverWait(driver, 8).until(EC.presence_of_element_located((By.CSS_SELECTOR, ".participantName")))
        except:
            pass
        # Esperar que carreguin les estadístiques
        try:
            WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.CLASS_NAME, "stat__category")))
        except:
            pass
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        fecha_element = soup.find(class_=lambda x: x and isinstance(x, str) and 'startTime' in x)
        if fecha_element: datos_partido['fecha'] = fecha_element.text.strip()
            
        enlaces_equipos = soup.find_all('a', class_=lambda x: x and isinstance(x, str) and 'participantName' in x)
        equipos_unicos = []
        for enlace in enlaces_equipos:
            nombre = enlace.text.strip()
            if nombre and nombre not in equipos_unicos: equipos_unicos.append(nombre)
        if len(equipos_unicos) >= 2:
            datos_partido['equipo_local'] = equipos_unicos[0]
            datos_partido['equipo_visitante'] = equipos_unicos[1]
            
        marcador = soup.find(class_=lambda x: x and isinstance(x, str) and 'detailScore' in x)
        if marcador: datos_partido['resultado'] = marcador.text.replace('\n', '').strip()

        todos_los_divs = soup.find_all('div')
        for div in todos_los_divs:
            hijos = div.find_all('div', recursive=False)
            if len(hijos) == 3:
                valor_local, categoria, valor_visitante = hijos[0].text.strip(), hijos[1].text.strip(), hijos[2].text.strip()
                if valor_local and categoria and valor_visitante and any(c.isalpha() for c in categoria) and len(categoria) < 30:
                    datos_partido['estadisticas'][categoria] = {'local': valor_local, 'visitante': valor_visitante}
    except Exception as e:
        print(f"Error en {url}: {e}")
    return datos_partido

def formatear_para_simulador(datos_partido):
    stats = datos_partido['estadisticas']
    
    def parse_float(val):
        try:
            return float(val.replace(',', '.'))
        except:
            return None
            
    def parse_int(val):
        try:
            return int(val)
        except:
            return 0
            
    return {
        "date": datos_partido['fecha'].split(" ")[0] if datos_partido['fecha'] != 'Desconocida' else "2026-06-01",
        "team1": datos_partido['equipo_local'],
        "team2": datos_partido['equipo_visitante'],
        "g1": parse_int(datos_partido['resultado'].split('-')[0]) if '-' in datos_partido['resultado'] else 0,
        "g2": parse_int(datos_partido['resultado'].split('-')[1]) if '-' in datos_partido['resultado'] else 0,
        # Claus reals de Flashscore (en espanyol)
        "xg1": parse_float((stats.get('Goles esperados (xG)', {}) or stats.get('xG', {})).get('local', '0')),
        "xg2": parse_float((stats.get('Goles esperados (xG)', {}) or stats.get('xG', {})).get('visitante', '0')),
        "corners1": parse_int((stats.get('Córneres', {}) or stats.get('Corners', {}) or stats.get('Saques de esquina', {})).get('local', '0')),
        "corners2": parse_int((stats.get('Córneres', {}) or stats.get('Corners', {}) or stats.get('Saques de esquina', {})).get('visitante', '0')),
        "cards1": parse_int(stats.get('Tarjetas amarillas', {}).get('local', '0')) + parse_int(stats.get('Tarjetas rojas', {}).get('local', '0')),
        "cards2": parse_int(stats.get('Tarjetas amarillas', {}).get('visitante', '0')) + parse_int(stats.get('Tarjetas rojas', {}).get('visitante', '0')),
    }

if __name__ == "__main__":
    import sys
    carpeta_raiz = os.path.dirname(os.path.abspath(__file__))
    
    # Agafar l'arxiu per defecte o el que passem per paràmetre
    arxiu_urls = "live_urls.txt"
    if len(sys.argv) > 1:
        arxiu_urls = sys.argv[1]
        
    RUTA_URLS = os.path.join(carpeta_raiz, "data", arxiu_urls)
    RUTA_JSON = os.path.join(carpeta_raiz, "data", "live_stats_2026.json")
    
    opciones = Options()
    # Opciones para ejecución visible, no headless
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=opciones)

    if os.path.exists(RUTA_URLS):
        with open(RUTA_URLS, 'r', encoding='utf-8') as f:
            lista_urls = [l.strip() for l in f if l.strip() and not l.strip().startswith('#')]
    else:
        lista_urls = []

    matches_procesados = []
    
    # Cargar JSON existente si existe
    if os.path.exists(RUTA_JSON):
        with open(RUTA_JSON, 'r', encoding='utf-8') as f:
            datos_existentes = json.load(f)
            matches_procesados = datos_existentes.get("matches", [])

    for url in lista_urls:
        print(f"Procesando: {url}")
        datos = extraer_partido_completo(url, driver)
        if datos['equipo_local'] != 'Desconocido':
            match_data = formatear_para_simulador(datos)
            
            # Buscar si el partido ya existe y actualizarlo, si no añadirlo
            found = False
            for i, m in enumerate(matches_procesados):
                if m['team1'] == match_data['team1'] and m['team2'] == match_data['team2']:
                    matches_procesados[i] = match_data
                    found = True
                    break
            
            if not found:
                matches_procesados.append(match_data)
                
        time.sleep(random.uniform(3, 5))

    with open(RUTA_JSON, 'w', encoding='utf-8') as f:
        json.dump({"matches": matches_procesados}, f, indent=2, ensure_ascii=False)
        
    print(f"Proceso finalizado. {len(matches_procesados)} partidos guardados en {RUTA_JSON}.")
    driver.quit()