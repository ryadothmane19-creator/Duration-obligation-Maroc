"""Collecte des emprunts obligataires visés par l'AMMC (niveaux 1 et 2)."""
import os
import re
import time
import requests
import pandas as pd
from bs4 import BeautifulSoup
from urllib.parse import unquote

BASE = "https://www.ammc.ma"
LISTE = BASE + "/fr/espace-emetteurs/liste-operations-financieres"
HEADERS = {"User-Agent": "Mozilla/5.0"}
FILTRES = {
    "field_choix_emetteur_target_id_verf": "All",
    "field_of_nature_titre_value": "3",   # Titres de dettes
    "field_of_nature_op_value": "9",      # Emprunt obligataire
    "field_of_type_op_value": "All",
}
FICHIER_EMISSIONS = "data/ammc_emissions_details.csv"
PAUSE = 2   # secondes entre deux requêtes (politesse envers le site)


# ---------- Niveau 1 : la liste des opérations ----------
def scraper_page_liste(numero_page):
    params = dict(FILTRES)
    params["page"] = numero_page
    reponse = requests.get(LISTE, params=params, headers=HEADERS, timeout=30)
    reponse.raise_for_status()
    table = BeautifulSoup(reponse.text, "lxml").find("table")
    if table is None:
        return []

    operations = []
    for tr in table.find_all("tr")[1:]:
        tds = tr.find_all("td")
        if len(tds) < 4:
            continue
        lien = tds[1].find("a")
        operations.append({
            "operation": tds[1].get_text(strip=True),
            "visa": tds[2].get_text(strip=True),
            "date_visa": tds[3].get_text(strip=True),
            "lien": BASE + lien["href"] if lien else None,
        })
    return operations


def scraper_liste(max_pages=50):
    """Parcourt les pages jusqu'à tomber sur une page vide."""
    toutes = []
    for p in range(max_pages):
        page = scraper_page_liste(p)
        if not page:
            break
        toutes += page
        print(f"Liste - page {p + 1} : {len(page)} émissions")
        time.sleep(PAUSE)
    return pd.DataFrame(toutes)


# ---------- Nettoyage des titres ----------
def classer(titre):
    t = titre.lower()
    if "perpétuel" in t or "perpetuel" in t:
        return "perpétuel"
    if "remboursable" in t and "action" in t:
        return "remboursable en actions"
    if "subordonn" in t:
        return "subordonné"
    if "hypoth" in t:
        return "garanti"
    return "ordinaire"


def extraire_emetteur(titre):
    """'CFG BANK – L'AMMC vise...' → 'CFG BANK' ; 'MAROC LEASING: Emprunt...' → 'MAROC LEASING'"""
    return re.split(r"\s[–-]\s|:", titre, maxsplit=1)[0].strip().upper()


# ---------- Niveau 2 : la page de détail et le bon PDF ----------
def nom_fichier(lien):
    return unquote(lien.split("/")[-1]).upper().replace(" ", "_")


def choisir_note(pdfs):
    """Priorité : note d'opération (NO), puis prospectus / note d'information, jamais le DR."""
    candidats = [l for l in pdfs
                 if not (nom_fichier(l).startswith("DR") or nom_fichier(l).startswith("ACTU"))]
    for l in candidats:
        n = nom_fichier(l)
        if re.search(r"(^|_)NO_", n) or n.startswith("NOTE"):
            return l
    for l in candidats:
        n = nom_fichier(l)
        if "PROSPECTUS" in n or n.startswith("PR_") or n.startswith("NI"):
            return l
    return candidats[0] if len(candidats) == 1 else None


def scraper_detail(url):
    reponse = requests.get(url, headers=HEADERS, timeout=30)
    reponse.raise_for_status()
    soup = BeautifulSoup(reponse.text, "lxml")

    infos = {}
    for tr in soup.find_all("tr"):
        cellules = tr.find_all(["th", "td"])
        if len(cellules) >= 2:
            infos[cellules[0].get_text(strip=True)] = cellules[1].get_text(" ", strip=True)

    pdfs = [a["href"] for a in soup.find_all("a", href=True)
            if a["href"].lower().endswith(".pdf")]
    pdfs = [l if l.startswith("http") else BASE + l for l in pdfs]

    return {
        "conseil": infos.get("Organisme conseil"),
        "montant_kdh": infos.get("Montant total (en millier de Dhs)"),
        "nb_pdfs": len(pdfs),
        "pdf_note": choisir_note(pdfs),
    }


# ---------- Tout en un, avec cache ----------
def collecter_emissions(rafraichir=False):
    """Renvoie la base des emprunts obligataires (depuis le cache CSV si possible)."""
    if not rafraichir and os.path.exists(FICHIER_EMISSIONS):
        return pd.read_csv(FICHIER_EMISSIONS, parse_dates=["date_visa"])

    emissions = scraper_liste()
    emissions["date_visa"] = pd.to_datetime(emissions["date_visa"], format="%d/%m/%Y", errors="coerce")
    emissions["type"] = emissions["operation"].apply(classer)
    emissions["emetteur"] = emissions["operation"].apply(extraire_emetteur)
    emissions["calculable"] = emissions["type"].isin(["ordinaire", "subordonné", "garanti"])
    emissions = emissions[emissions["calculable"]].reset_index(drop=True)

    details = []
    for i, url in enumerate(emissions["lien"], start=1):
        try:
            details.append(scraper_detail(url))
        except Exception as erreur:
            details.append({"pdf_note": None, "erreur": str(erreur)})
        if i % 20 == 0:
            print(f"Détails : {i}/{len(emissions)}")
        time.sleep(PAUSE)

    base = pd.concat([emissions, pd.DataFrame(details)], axis=1)
    base["montant_mdh"] = pd.to_numeric(base["montant_kdh"], errors="coerce") / 1000
    os.makedirs("data", exist_ok=True)
    base.to_csv(FICHIER_EMISSIONS, index=False)
    return base
