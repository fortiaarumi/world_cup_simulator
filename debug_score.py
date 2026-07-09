from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import time

URL = "https://www.flashscore.es/partido/futbol/francia-QkGeVG1n/paraguay-YaNlqp6j/resumen/estadisticas/general/?mid=M5YPKKbB"

options = Options()
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
driver.get(URL)
time.sleep(8)  # espera fixa

# Acceptar cookies si apareix
try:
    driver.find_element(By.ID, "onetrust-accept-btn-handler").click()
    time.sleep(2)
except: pass

time.sleep(3)
soup = BeautifulSoup(driver.page_source, "html.parser")

print("=== TITLE DE LA PAGINA ===")
print(" ", driver.title)

print()
print("=== TOTS els elements amb 'detailScore' a la classe ===")
found = soup.find_all(class_=lambda x: x and "detailScore" in str(x))
if not found:
    print("  CAP element amb detailScore trobat!")
for el in found:
    print(f"  TAG={el.name}  CLASSE={el.get('class')}  TEXT='{el.get_text(strip=True)}'")

print()
print("=== Elements amb 'score' (minuscules) a la classe, text curt ===")
for el in soup.find_all(class_=lambda x: x and "score" in str(x).lower()):
    t = el.get_text(strip=True)
    if t and len(t) < 15:
        print(f"  TAG={el.name}  CLASSE={el.get('class')}  TEXT='{t}'")

print()
print("=== Cercar el text 0-1 o 1-0 en el DOM ===")
for el in soup.find_all(string=lambda t: t and t.strip() in ["0","1","0-1","1-0","0 - 1","1 - 0"]):
    p = el.parent
    gp = p.parent if p else None
    print(f"  TEXT='{el.strip()}'  PARENT_CLASS={p.get('class') if p else '?'}  GRANDPARENT_CLASS={gp.get('class') if gp else '?'}")

driver.quit()
print("\nFET.")
