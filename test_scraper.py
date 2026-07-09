import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data_scraper import extraer_partido_completo, formatear_para_simulador
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

URL = "https://www.flashscore.es/partido/futbol/francia-QkGeVG1n/noruega-8rP6JO0H/resumen/estadisticas/general/?mid=bsJSJ30L"

options = Options()
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
try:
    datos = extraer_partido_completo(URL, driver)
    fmt = formatear_para_simulador(datos)
    print("=== DADES FORMATEJADES ===")
    for k, v in fmt.items():
        print(f"  {k}: {v}")
finally:
    driver.quit()
