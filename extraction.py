import os
import re
import time
import requests
import pdfplumber
from datetime import date
from urllib.parse import unquote

HEADERS = {"User-Agent": "Mozilla/5.0"}
DOSSIER_PDF = "data/pdfs"

MOIS = {"janvier": 1, "février": 2, "fevrier": 2, "mars": 3, "avril": 4, "mai": 5,
        "juin": 6, "juillet": 7, "août": 8, "aout": 8, "septembre": 9,
        "octobre": 10, "novembre": 11, "décembre": 12, "decembre": 12}


# ---------- Lecture du PDF ----------
def normaliser(texte):
    for ancien, nouveau in {"’": "'", "‘": "'", "«": '"', "»": '"',
                            " ": " ", "–": "-"}.items():
        texte = texte.replace(ancien, nouveau)
    return texte


def lire_pdf(url, max_pages=20):
    """Texte normalisé des premières pages du PDF.
    Trois niveaux de cache :
      1) le texte déjà extrait (.txt)  -> instantané
      2) le PDF déjà téléchargé (.pdf) -> on extrait seulement le texte
      3) sinon on télécharge (avec une pause de politesse)
    """
    os.makedirs(DOSSIER_PDF, exist_ok=True)
    nom = unquote(url.split("/")[-1])
    chemin_pdf = os.path.join(DOSSIER_PDF, nom)
    chemin_txt = chemin_pdf[:-4] + ".txt"

    if os.path.exists(chemin_txt):
        with open(chemin_txt, encoding="utf-8") as f:
            return f.read()

    if not os.path.exists(chemin_pdf):
        reponse = requests.get(url, headers=HEADERS, timeout=60)
        reponse.raise_for_status()
        with open(chemin_pdf, "wb") as f:
            f.write(reponse.content)
        time.sleep(1)

    with pdfplumber.open(chemin_pdf) as pdf:
        pages = pdf.pages[:max_pages]
        texte = normaliser("\n".join(page.extract_text() or "" for page in pages))

    with open(chemin_txt, "w", encoding="utf-8") as f:
        f.write(texte)
    return texte


# ---------- Outils ----------
def premiere_ligne(lignes, mot):
    for i, l in enumerate(lignes):
        if mot.lower() in l.lower():
            return l, (lignes[i + 1] if i + 1 < len(lignes) else "")
    return "", ""


def nombre(x):
    return float(x.replace(",", "."))


def ajouter_ans(d, n):
    try:
        return d.replace(year=d.year + n)
    except ValueError:              # cas du 29 février
        return d.replace(year=d.year + n, day=28)


def element(liste, i):
    if i < len(liste):
        return liste[i]
    return liste[0] if liste else None


# ---------- Extraction des informations ----------
def extraire_dates(ligne):
    """Reconnaît '02 février 2041', '1er mars 2030' et '02/02/2041'."""
    t = ligne.lower()
    dates = []
    for j, m, a in re.findall(r"(\d{1,2})(?:er)?\s+([a-zéèûô]+)\s+(\d{4})", t):
        if m in MOIS:
            dates.append(date(int(a), MOIS[m], int(j)))
    for j, m, a in re.findall(r"(\d{1,2})/(\d{1,2})/(\d{4})", t):
        try:
            dates.append(date(int(a), int(m), int(j)))
        except ValueError:
            pass
    return dates


def chercher_primes(zone):
    t = zone.lower()
    fourchettes = re.findall(r"(\d+(?:,\d+)?)\s*(?:et|-|à)\s*(\d+(?:,\d+)?)\s*(?:pbs?|points)", t)
    if fourchettes:
        return [(nombre(a) + nombre(b)) / 2 for a, b in fourchettes]
    return [nombre(x) for x in re.findall(r"(\d+(?:,\d+)?)\s*(?:pbs?|points)", t)]


def extraire_primes(lignes):
    for i, l in enumerate(lignes):
        if l.strip().lower().startswith("prime de risque"):
            primes = chercher_primes(l)
            if primes:
                return primes
            primes = chercher_primes(" ".join(lignes[max(i - 2, 0):i + 2]))
            if primes:
                return primes
    return []


def extraire_maturites(ligne):
    return [int(x) for x in re.findall(r"(\d+)\s*ans", ligne.lower())]


def extraire_nature(lignes):
    for l in lignes[:400]:
        b = l.lower()
        if ("révisable" in b or "fixe" in b) and len(b) < 120:
            return re.findall(r"révisable|fixe", b)
    return []


def extraire_remboursement(lignes):
    for i, l in enumerate(lignes):
        if "remboursement" in l.lower() and len(l) < 90:
            zone = " ".join(lignes[max(i - 2, 0):i + 3]).lower()
            trouves = re.findall(r"in fine|amortissable|échéances constantes", zone)
            if trouves:
                return ["in fine" if x == "in fine" else "amortissable" for x in trouves]
    return []


# ---------- Assemblage : une ligne par tranche ----------
def analyser_note(url):
    lignes = lire_pdf(url).split("\n")

    echeances = extraire_dates(premiere_ligne(lignes, "Date d'échéance")[0])
    jouissances = extraire_dates(premiere_ligne(lignes, "Date de jouissance")[0])
    primes = extraire_primes(lignes)
    maturites = extraire_maturites(premiere_ligne(lignes, "Maturité")[0])
    natures = extraire_nature(lignes)
    remboursements = extraire_remboursement(lignes)

    nb_tranches = max(len(primes), len(maturites), len(natures), 1)
    tranches = []
    for i in range(nb_tranches):
        jouissance = element(jouissances, i)
        maturite = element(maturites, i)
        if len(echeances) >= nb_tranches:          # le PDF donne une date par tranche
            echeance = echeances[i]
        elif jouissance and maturite:               # sinon : jouissance + maturité
            echeance = ajouter_ans(jouissance, maturite)
        else:
            echeance = element(echeances, i)
        tranches.append({
            "tranche": chr(ord("A") + i),
            "jouissance": jouissance,
            "echeance": echeance,
            "maturite_ans": maturite,
            "nature_taux": element(natures, i),
            "prime_pb": element(primes, i),
            "remboursement": element(remboursements, i),
        })
    return tranches
