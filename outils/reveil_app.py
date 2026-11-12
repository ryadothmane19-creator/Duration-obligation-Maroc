"""Ouvre l'application Streamlit et clique sur le bouton de réveil si elle s'est endormie.
Lancé automatiquement par GitHub Actions (.github/workflows/reveil_app.yml)."""
import os
import sys
import time

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

URL = os.environ.get("APP_URL", "https://duration-maroc.streamlit.app/")
BOUTON = "//button[contains(., 'get this app back up')]"

options = Options()
for arg in ["--headless=new", "--no-sandbox", "--disable-dev-shm-usage", "--window-size=1400,1000"]:
    options.add_argument(arg)
navigateur = webdriver.Chrome(options=options)

try:
    navigateur.get(URL)
    time.sleep(15)                                    # laisse la page de Streamlit se charger
    boutons = navigateur.find_elements(By.XPATH, BOUTON)
    if not boutons:
        print("L'application est déjà réveillée.")
        sys.exit(0)
    print("Application endormie : clic sur le bouton de réveil.")
    boutons[0].click()
    time.sleep(60)                                    # le redémarrage prend environ une minute
    if navigateur.find_elements(By.XPATH, BOUTON):
        print("Le bouton est toujours là : le réveil a échoué.")
        sys.exit(1)
    print("Application réveillée.")
finally:
    navigateur.quit()
