"""Assemble tout : PDF AMMC -> tranches -> obligations vivantes -> analyse de risque -> scénarios."""
import os
import time
import pandas as pd

from calculs import (flux_dates, mesures_courbe, prix_courbe, taux_courbe, duration_spread,
                     key_rate_durations, variation_tranche, SCENARIOS)

FICHIER_TRANCHES = "data/tranches.csv"
FICHIER_RESULTATS = "data/resultats.csv"


# =====================================================================
# SECTEURS
# =====================================================================
SECTEURS = {
    "Banque": ["ATTIJARI", "BMCE", "BANK OF AFRICA", "BANQUE CENTRALE POPULAIRE", "BCP", "CIH",
               "CDM", "CREDIT DU MAROC", "CRÉDIT DU MAROC", "BMCI", "SOCIETE GENERALE", "SOCIÉTÉ GÉNÉRALE",
               "CFG", "CREDIT AGRICOLE", "CRÉDIT AGRICOLE", "CREDIT IMMOBILIER", "CRÉDIT IMMOBILIER",
               "BANQUE POPULAIRE", "AL BARID", "ARAB BANK", "CITIBANK"],
    "Société de financement": ["WAFASALAF", "EQDOM", "SALAFIN", "SOFAC", "RCI", "LEASING",
                               "MAGHREBAIL", "WAFABAIL", "BAIL", "DAR ASSAFAA", "VIVALIS", "ACRED"],
    "Établissement public": ["FEC", "ONCF", "ONEE", "ONE ", "ONEP", "OCP", "AUTOROUTES", "ADM",
                             "AGENCE NATIONALE DES PORTS", "ANP", "CDG", "OMRANE", "MASEN",
                             "ROYAL AIR MAROC", "RAM", "TMSA", "BNDE", "SNTL", "CAISSE", "OFFICE"],
    "Immobilier": ["ADDOHA", "ALLIANCES", "DAR SAADA", "ARADEI", "CGI", "PALMERAIE",
                   "IMMOBILI", "PROMOTION", "RESIDENCES", "RÉSIDENCES", "IMMOLOG", "AKDITAL IMMO"],
}


def secteur(emetteur):
    """Classe un émetteur dans un secteur à partir de mots-clés de son nom."""
    nom = f" {str(emetteur).upper()} "
    for nom_secteur, mots in SECTEURS.items():
        for mot in mots:
            if f" {mot}" in nom:
                return nom_secteur
    return "Industrie & services"


# =====================================================================
# 1. TRANCHES (lecture des notes d'opération)
# =====================================================================
def construire_tranches(base, rafraichir=False):
    """Lit chaque note d'opération et renvoie une ligne par tranche (avec cache CSV)."""
    from extraction import analyser_note

    if not rafraichir and os.path.exists(FICHIER_TRANCHES):
        return pd.read_csv(FICHIER_TRANCHES, parse_dates=["jouissance", "echeance", "date_visa"])

    lignes = []
    avec_pdf = base[base["pdf_note"].notna()]
    debut = time.time()
    for i, (_, em) in enumerate(avec_pdf.iterrows(), start=1):
        try:
            for t in analyser_note(em["pdf_note"]):
                t.update({"emetteur": em["emetteur"], "type": em["type"],
                          "date_visa": em["date_visa"], "montant_mdh": em["montant_mdh"],
                          "pdf_note": em["pdf_note"]})
                lignes.append(t)
        except Exception as erreur:
            lignes.append({"emetteur": em["emetteur"], "pdf_note": em["pdf_note"], "erreur": str(erreur)})
        if i % 10 == 0:
            print(f"PDF : {i}/{len(avec_pdf)}  ({time.time() - debut:.0f} s)")

    tranches = pd.DataFrame(lignes)
    for col in ["jouissance", "echeance"]:
        tranches[col] = pd.to_datetime(tranches[col], errors="coerce")
    tranches.to_csv(FICHIER_TRANCHES, index=False)
    return tranches


def charger_tranches():
    """Relit data/tranches.csv (créé par 01_collecte.ipynb)."""
    if not os.path.exists(FICHIER_TRANCHES):
        raise FileNotFoundError("data/tranches.csv introuvable : lance d'abord 01_collecte.ipynb.")
    return pd.read_csv(FICHIER_TRANCHES, parse_dates=["jouissance", "echeance", "date_visa"])


# =====================================================================
# 2. OBLIGATIONS VIVANTES
# =====================================================================
def obligations_vivantes(tranches, aujourd_hui=None):
    """Tranches complètes, non remboursées, sans doublon, avec leur secteur."""
    aujourd_hui = pd.Timestamp(aujourd_hui or pd.Timestamp.today().normalize())
    tranches = tranches.copy()

    # Échéance manquante : date de visa + maturité (la jouissance suit le visa de quelques semaines)
    manque = tranches["echeance"].isna() & tranches["maturite_ans"].notna() & tranches["date_visa"].notna()
    tranches["echeance_estimee"] = manque
    tranches.loc[manque, "echeance"] = [
        v + pd.DateOffset(years=int(m))
        for v, m in zip(tranches.loc[manque, "date_visa"], tranches.loc[manque, "maturite_ans"])
    ]

    ok = tranches.dropna(subset=["echeance", "prime_pb", "nature_taux"]).copy()
    ok = ok[ok["echeance"] > aujourd_hui]
    ok = ok.drop_duplicates(subset=["emetteur", "tranche", "echeance", "prime_pb", "nature_taux"])
    ok["secteur"] = ok["emetteur"].apply(secteur)
    ok["remboursement"] = ok["remboursement"].fillna("in fine")
    return ok.reset_index(drop=True)


# =====================================================================
# 3. ANALYSE DE RISQUE (une ligne par tranche)
# =====================================================================
def analyser_marche(vivantes, courbe, aujourd_hui=None, chocs_pb=(-100, 50, 100, 200)):
    """Flux datés actualisés chacun sur la courbe BAM + prime.
    Fixe : coupon ≈ BDT(maturité résiduelle) + prime.  Révisable : coupon = BDT 1 an + prime."""
    aujourd_hui = pd.Timestamp(aujourd_hui or pd.Timestamp.today().normalize())
    resultats = []
    for _, o in vivantes.iterrows():
        prime = o["prime_pb"] / 10000
        mat_res = (pd.Timestamp(o["echeance"]) - aujourd_hui).days / 365
        maturite_ref = 1.0 if o["nature_taux"] == "révisable" else mat_res
        coupon = taux_courbe(maturite_ref, courbe) + prime

        flux, times, couru = flux_dates(coupon, o["echeance"], aujourd_hui, o["remboursement"],
                                        o["nature_taux"], jouissance=o.get("jouissance"))
        prix, mac, dur, conv = mesures_courbe(flux, times, courbe, prime)
        fc, tc, _ = flux_dates(coupon, o["echeance"], aujourd_hui, o["remboursement"],
                               o["nature_taux"], projection_complete=True)

        ligne = {
            "emetteur": o["emetteur"], "tranche": o["tranche"], "type": o["type"],
            "secteur": o["secteur"], "nature_taux": o["nature_taux"],
            "remboursement": o["remboursement"], "echeance": pd.Timestamp(o["echeance"]).date(),
            "echeance_estimee": bool(o.get("echeance_estimee", False)),
            "maturite_res": round(mat_res, 2), "prochain_flux_ans": round(times[0], 2),
            "taux_bam_%": round(taux_courbe(mat_res, courbe) * 100, 3), "prime_pb": o["prime_pb"],
            "coupon_%": round(coupon * 100, 3), "ytm_%": round(coupon * 100, 3),
            "prix_plein": round(prix, 3), "coupon_couru": round(couru, 3),
            "prix_pied": round(prix - couru, 3),
            "macaulay": round(mac, 3), "modifiee": round(dur, 3), "convexite": round(conv, 2),
            "duration_spread": round(duration_spread(fc, tc, courbe, prime), 3),
            "dv01": round(dur * prix * 1000 * 0.0001, 2),               # MAD par titre de 100 000
            "seuil_pb": round(coupon / dur * 10000) if dur >= 0.5 else None,   # non significatif < 6 mois
        }
        for c in chocs_pb:
            p_choc = prix_courbe(flux, times, courbe, prime, choc=lambda t, c=c: c / 10000)
            ligne[f"choc_{c:+d}pb_%"] = round((p_choc - prix) / prix * 100, 2)
        ligne.update({k: round(v, 3) for k, v in key_rate_durations(flux, times, courbe, prime).items()})
        resultats.append(ligne)
    return pd.DataFrame(resultats).sort_values("modifiee").reset_index(drop=True)


def resume_secteurs(resultats):
    """Moyennes par secteur (médiane pour le seuil, sensible aux durations très courtes)."""
    return (resultats.groupby("secteur")
            .agg(tranches=("emetteur", "count"),
                 part_revisable_pct=("nature_taux", lambda s: round((s == "révisable").mean() * 100)),
                 prime_moy_pb=("prime_pb", "mean"),
                 ytm_moy_pct=("ytm_%", "mean"),
                 duration_taux_moy=("modifiee", "mean"),
                 duration_spread_moy=("duration_spread", "mean"),
                 seuil_median_pb=("seuil_pb", "median"))
            .round(2)
            .sort_values("duration_taux_moy"))


# =====================================================================
# 4. SCÉNARIOS (courbe + spread)
# =====================================================================
def impact_scenario(resultats, courbe, chocs_pb=None, spreads_pb=None, aujourd_hui=None):
    """Impact d'un scénario sur chaque tranche.
    chocs_pb   : chocs aux points de la courbe (liste), ou None
    spreads_pb : dict {secteur: choc de prime en pb}, ou None
    """
    aujourd_hui = pd.Timestamp(aujourd_hui or pd.Timestamp.today().normalize())
    spreads_pb = spreads_pb or {}
    lignes = []
    for _, o in resultats.iterrows():
        v_c, v_s, v_t = variation_tranche(o["coupon_%"] / 100, o["echeance"], aujourd_hui,
                                          o["remboursement"], o["nature_taux"], o["prime_pb"] / 10000,
                                          courbe, chocs_pb, spreads_pb.get(o["secteur"], 0.0))
        lignes.append({"emetteur": o["emetteur"], "tranche": o["tranche"], "secteur": o["secteur"],
                       "nature_taux": o["nature_taux"], "maturite_res": o["maturite_res"],
                       "effet_courbe_%": round(v_c, 3), "effet_spread_%": round(v_s, 3),
                       "variation_%": round(v_t, 3)})
    return pd.DataFrame(lignes)


def tous_les_scenarios(resultats, courbe, aujourd_hui=None):
    """Variation (%) de chaque tranche sous chacun des scénarios de courbe prédéfinis."""
    tableau = resultats[["emetteur", "tranche", "secteur", "nature_taux", "maturite_res"]].copy()
    for nom, chocs in SCENARIOS.items():
        tableau[nom] = impact_scenario(resultats, courbe, chocs, aujourd_hui=aujourd_hui)["variation_%"].values
    return tableau
