"""Courbe des taux de référence des Bons du Trésor (Bank Al-Maghrib)."""
import os
import requests
import numpy as np
import pandas as pd
from bs4 import BeautifulSoup

URL_BAM = ("https://www.bkam.ma/Marches/Principaux-indicateurs/Marche-obligataire/"
           "Marche-des-bons-de-tresor/Marche-secondaire/Taux-de-reference-des-bons-du-tresor")
HEADERS = {"User-Agent": "Mozilla/5.0"}
FICHIER_COURBE = "data/courbe_bam.csv"


def telecharger_courbe():
    """Scrape la page BAM et renvoie un DataFrame propre : echeance, maturite (ans), taux (décimal)."""
    reponse = requests.get(URL_BAM, headers=HEADERS, timeout=30)
    reponse.raise_for_status()
    soup = BeautifulSoup(reponse.text, "lxml")

    lignes = []
    for tr in soup.find("table").find_all("tr")[1:]:
        cellules = [td.get_text(strip=True) for td in tr.find_all("td")]
        if len(cellules) == 4 and "/" in cellules[0]:      # on écarte l'en-tête et la ligne "Total"
            lignes.append(cellules)

    df = pd.DataFrame(lignes, columns=["echeance", "transaction", "taux", "date_valeur"])
    df["echeance"] = pd.to_datetime(df["echeance"], format="%d/%m/%Y")
    df["date_valeur"] = pd.to_datetime(df["date_valeur"], format="%d/%m/%Y")
    df["taux"] = (df["taux"].str.replace("%", "").str.replace(",", ".")
                            .str.strip().astype(float) / 100)
    df["maturite"] = (df["echeance"] - df["date_valeur"]).dt.days / 365
    return df.sort_values("maturite")[["echeance", "maturite", "taux", "date_valeur"]]


def get_courbe_bam(rafraichir=False):
    """Renvoie la courbe : depuis le cache CSV, ou en la téléchargeant (si demandé ou si absent)."""
    if rafraichir or not os.path.exists(FICHIER_COURBE):
        courbe = telecharger_courbe()
        os.makedirs("data", exist_ok=True)
        courbe.to_csv(FICHIER_COURBE, index=False)
        return courbe
    return pd.read_csv(FICHIER_COURBE, parse_dates=["echeance", "date_valeur"])


def taux_bam(maturite, courbe):
    """Taux BDT pour une maturité donnée (en années), par interpolation linéaire."""
    return float(np.interp(maturite, courbe["maturite"], courbe["taux"]))
