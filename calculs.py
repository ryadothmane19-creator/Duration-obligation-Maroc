"""Calculs obligataires.

Partie 1 - Calculateur (taux de rendement unique) : flux, prix, durations, convexité.
Partie 2 - Flux datés : dates de coupon réelles, temps en fractions d'année, coupon couru.
Partie 3 - Actualisation sur la courbe BAM : chaque flux à son propre taux, duration effective.
Partie 4 - Scénarios : chocs non parallèles de courbe, key rate durations, choc de spread.
"""
import numpy as np
import pandas as pd


# =====================================================================
# PARTIE 1 - CALCULATEUR (un seul taux de rendement)
# =====================================================================
def build_cash_flows(face, coupon_rate, maturite, remboursement="in fine"):
    """Flux annuels d'une obligation (temps 1, 2, ..., maturité).
    - in fine      : coupons chaque année, tout le nominal à la fin
    - amortissable : nominal remboursé par parts égales, coupon sur le capital restant
    """
    times = list(range(1, maturite + 1))
    if remboursement == "amortissable":
        part = face / maturite
        restant = face
        cash_flows = []
        for _ in times:
            cash_flows.append(restant * coupon_rate + part)
            restant -= part
    else:
        cash_flows = [face * coupon_rate] * maturite
        cash_flows[-1] += face
    return cash_flows, times


def bond_duration(cash_flows, times, ytm, frequency=1):
    """Prix, duration de Macaulay et duration modifiée, pour un rendement unique."""
    if len(cash_flows) != len(times):
        raise ValueError("cash_flows et times doivent avoir la même longueur.")
    periodic_yield = ytm / frequency
    price = 0
    weighted_pv = 0
    for C, t in zip(cash_flows, times):
        pv = C / (1 + periodic_yield) ** (frequency * t)
        price += pv
        weighted_pv += t * pv
    macaulay = weighted_pv / price
    modified = macaulay / (1 + periodic_yield)
    return price, macaulay, modified


def convexite(cash_flows, times, ytm):
    """Convexité : courbure de la relation prix-rendement.  C = Σ t(t+1)·PV_t / (P·(1+y)²)"""
    prix = 0
    somme = 0
    for C, t in zip(cash_flows, times):
        pv = C / (1 + ytm) ** t
        prix += pv
        somme += t * (t + 1) * pv
    return somme / (prix * (1 + ytm) ** 2)


def courbe_prix_rendement(cash_flows, times, ytm, ecart=0.04, n=81):
    """Prix exact, approximation par la duration, et par duration + convexité (ytm ± ecart)."""
    prix_0, _, mod = bond_duration(cash_flows, times, ytm)
    conv = convexite(cash_flows, times, ytm)
    lignes = []
    for k in range(n):
        y = ytm - ecart + 2 * ecart * k / (n - 1)
        if y <= -0.99:
            continue
        dy = y - ytm
        exact, _, _ = bond_duration(cash_flows, times, y)
        lignes.append({
            "rendement_%": round(y * 100, 3),
            "Prix exact": exact,
            "Approximation duration": prix_0 * (1 - mod * dy),
            "Duration + convexité": prix_0 * (1 - mod * dy + 0.5 * conv * dy ** 2),
        })
    return pd.DataFrame(lignes)


def sensibilite_duration(parametre, valeurs, face, coupon_rate, maturite, ytm, remboursement="in fine"):
    """Durations quand UN seul paramètre varie (maturite, coupon ou rendement), les autres fixés."""
    lignes = []
    for v in valeurs:
        c, m, y = coupon_rate, maturite, ytm
        if parametre == "maturite":
            m = int(v)
        elif parametre == "coupon":
            c = v
        elif parametre == "rendement":
            y = v
        cf, t = build_cash_flows(face, c, m, remboursement)
        _, mac, mod = bond_duration(cf, t, y)
        lignes.append({parametre: v, "Macaulay": mac, "Modifiée": mod})
    return pd.DataFrame(lignes)


# =====================================================================
# PARTIE 2 - FLUX DATÉS (fractions d'année, Exact/365)
# =====================================================================
def ajouter_annees(d, n):
    """Date d + n années (gère le 29 février)."""
    d = pd.Timestamp(d)
    try:
        return d.replace(year=d.year + n)
    except ValueError:
        return d.replace(year=d.year + n, day=28)


def dates_coupons(echeance, aujourd_hui):
    """Dates de coupon restantes (anniversaires de l'échéance) et date du dernier coupon payé."""
    echeance, aujourd_hui = pd.Timestamp(echeance), pd.Timestamp(aujourd_hui)
    dates = []
    k = 0
    while True:
        d = ajouter_annees(echeance, -k)
        if d <= aujourd_hui:
            return sorted(dates), d
        dates.append(d)
        k += 1


def flux_dates(coupon_rate, echeance, aujourd_hui, remboursement="in fine", nature_taux="fixe",
               nominal=100, jouissance=None, projection_complete=False, differe_ans=0, maturite_ans=None):
    """Flux futurs (pour 100 de capital restant), leurs temps en années, et le coupon couru.

    - fixe in fine      : coupons + nominal à l'échéance
    - fixe amortissable : capital remboursé par parts égales sur les échéances restantes
    - différé d'amortissement (differe_ans, maturite_ans) : le capital n'est remboursé que sur les
                          (maturite_ans - differe_ans) dernières échéances ; avant, coupons seuls
    - révisable         : par défaut, un seul flux à la prochaine révision (coupon + capital),
                          car le coupon suivant s'ajuste aux taux. Avec projection_complete=True,
                          on garde tout l'échéancier (utile pour le risque de SPREAD, qui ne se révise pas).
    """
    aujourd_hui = pd.Timestamp(aujourd_hui)
    dates, dernier = dates_coupons(echeance, aujourd_hui)
    times = [(d - aujourd_hui).days / 365 for d in dates]
    coupon = nominal * coupon_rate

    if jouissance is not None and not pd.isna(jouissance) and pd.Timestamp(jouissance) > dernier:
        dernier = pd.Timestamp(jouissance)          # aucun coupon encore payé : on part de la jouissance
    couru = coupon * max((aujourd_hui - dernier).days, 0) / 365

    if nature_taux == "révisable" and not projection_complete:
        return [nominal + coupon], [times[0]], couru

    if remboursement == "amortissable":
        nb_amort = len(dates)                       # par défaut : chaque échéance restante amortit
        if differe_ans and maturite_ans and not pd.isna(maturite_ans) and not pd.isna(differe_ans):
            nb_amort = max(1, min(len(dates), int(maturite_ans) - int(differe_ans)))
        part = nominal / nb_amort
        restant = nominal
        flux = []
        for k in range(len(dates)):
            amortit = k >= len(dates) - nb_amort      # seules les dernières échéances remboursent
            flux.append(restant * coupon_rate + (part if amortit else 0))
            if amortit:
                restant -= part
    else:
        flux = [coupon] * len(dates)
        flux[-1] += nominal
    return flux, times, couru


# =====================================================================
# PARTIE 3 - ACTUALISATION SUR LA COURBE BAM
# =====================================================================
def taux_courbe(t, courbe):
    """Taux BDT de maturité t (interpolation linéaire, plat au-delà des extrémités)."""
    return float(np.interp(t, courbe["maturite"], courbe["taux"]))


def prix_courbe(flux, times, courbe, prime, choc=None):
    """Prix plein : chaque flux actualisé à SON taux, r_BAM(t) + prime + choc(t).
    choc : fonction t -> choc en décimal (None = pas de choc)."""
    prix = 0.0
    for C, t in zip(flux, times):
        r = taux_courbe(t, courbe) + prime + (choc(t) if choc else 0.0)
        prix += C / (1 + r) ** t
    return prix


def mesures_courbe(flux, times, courbe, prime):
    """Prix plein, duration de Macaulay, duration effective et convexité effective.
    Duration et convexité effectives : on décale toute la courbe de ±1 pb et on observe le prix."""
    p0 = prix_courbe(flux, times, courbe, prime)
    pvs = [C / (1 + taux_courbe(t, courbe) + prime) ** t for C, t in zip(flux, times)]
    macaulay = sum(t * pv for t, pv in zip(times, pvs)) / p0
    h = 0.0001
    p_haut = prix_courbe(flux, times, courbe, prime, choc=lambda t: h)
    p_bas = prix_courbe(flux, times, courbe, prime, choc=lambda t: -h)
    duration_eff = (p_bas - p_haut) / (2 * p0 * h)
    convexite_eff = (p_bas + p_haut - 2 * p0) / (p0 * h ** 2)
    return p0, macaulay, duration_eff, convexite_eff


def duration_spread(flux_complets, times_complets, courbe, prime):
    """Sensibilité du prix à la prime de risque (+1 pb sur la prime seulement), en %."""
    h = 0.0001
    p0 = prix_courbe(flux_complets, times_complets, courbe, prime)
    p1 = prix_courbe(flux_complets, times_complets, courbe, prime + h)
    return -(p1 - p0) / (p0 * h)


# =====================================================================
# PARTIE 4 - SCÉNARIOS DE COURBE, KEY RATE DURATIONS, CHOC DE SPREAD
# =====================================================================
POINTS_COURBE = [0.25, 1, 2, 5, 10, 15, 30]      # points de la courbe (années)

# Chocs en points de base à chaque point de la courbe (interpolés entre les points).
# Inspirés des 6 scénarios standards IRRBB du Comité de Bâle (amplitudes illustratives).
SCENARIOS = {
    "Hausse parallèle":          [100, 100, 100, 100, 100, 100, 100],
    "Baisse parallèle":          [-100, -100, -100, -100, -100, -100, -100],
    "Pentification":             [-65, -50, -35, 0, 50, 75, 90],
    "Aplatissement":             [90, 75, 55, 20, -20, -35, -45],
    "Hausse des taux courts":    [150, 120, 90, 45, 15, 5, 0],
    "Baisse des taux courts":    [-150, -120, -90, -45, -15, -5, 0],
    "BAM +50 pb, 10 ans -20 pb": [50, 50, 35, 10, -20, -20, -20],
}


def fonction_choc(chocs_pb, points=POINTS_COURBE):
    """Liste de chocs (pb) aux points de la courbe -> fonction t -> choc (décimal), interpolée."""
    chocs = np.array(chocs_pb, dtype=float) / 10000
    return lambda t: float(np.interp(t, points, chocs))


def key_rate_durations(flux, times, courbe, prime, points=POINTS_COURBE):
    """Sensibilité du prix à chaque point de la courbe (+1 pb sur UN point à la fois).
    Leur somme ≈ duration effective."""
    p0 = prix_courbe(flux, times, courbe, prime)
    krd = {}
    for i, point in enumerate(points):
        bosse = [0] * len(points)
        bosse[i] = 1
        p1 = prix_courbe(flux, times, courbe, prime, choc=fonction_choc(bosse, points))
        krd[f"KRD {point:g}a"] = -(p1 - p0) / (p0 * 0.0001)
    return krd


def variation_tranche(coupon_rate, echeance, aujourd_hui, remboursement, nature_taux, prime, courbe,
                      chocs_pb=None, spread_pb=0.0, differe_ans=0, maturite_ans=None):
    """Variation du prix plein (%) d'une tranche sous un choc de courbe ET/OU un choc de spread.

    - Choc de courbe : la tranche révisable n'y est exposée que jusqu'à sa prochaine révision.
    - Choc de spread : la prime ne se révise jamais, donc fixe ET révisable y sont exposées
      sur toute leur durée de vie (échéancier complet).
    Renvoie (variation_courbe_%, variation_spread_%, variation_totale_%).
    """
    choc = fonction_choc(chocs_pb) if chocs_pb is not None else None
    ds = spread_pb / 10000

    # 1) Effet de la courbe
    flux, times, _ = flux_dates(coupon_rate, echeance, aujourd_hui, remboursement, nature_taux,
                                differe_ans=differe_ans, maturite_ans=maturite_ans)
    p0 = prix_courbe(flux, times, courbe, prime)
    v_courbe = (prix_courbe(flux, times, courbe, prime, choc=choc) / p0 - 1) * 100 if choc else 0.0

    # 2) Effet du spread (échéancier complet, y compris pour les révisables)
    fc, tc, _ = flux_dates(coupon_rate, echeance, aujourd_hui, remboursement, nature_taux,
                           projection_complete=True, differe_ans=differe_ans, maturite_ans=maturite_ans)
    q0 = prix_courbe(fc, tc, courbe, prime)
    v_spread = (prix_courbe(fc, tc, courbe, prime + ds) / q0 - 1) * 100 if ds else 0.0

    # 3) Total : composition des deux effets
    v_total = ((1 + v_courbe / 100) * (1 + v_spread / 100) - 1) * 100
    return v_courbe, v_spread, v_total
