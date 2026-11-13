"""Application Streamlit : risque de taux et de spread des obligations privées marocaines.

Pages : Synthèse · Marché · Scénarios · Calculateur.
Lancement :  streamlit run app.py
"""
import os
import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

from calculs import (build_cash_flows, bond_duration, convexite, courbe_prix_rendement,
                     sensibilite_duration, POINTS_COURBE, SCENARIOS, fonction_choc)
from design import (appliquer_style, marque, pied_barre, barre_terminal, entete, section, kpis, ton, afficher,
                    tableau, ECHELLE_SECTEURS, SECTEURS_ORDRE, SECTEURS_COULEURS, PRINCIPAL, SECOND, AMBRE,
                    PERTE, GAIN, GRIS, ENCRE, DISCRET, PANNEAU, LIGNE)

st.set_page_config(page_title="Duration Maroc", page_icon="📈", layout="wide",
                   initial_sidebar_state="expanded")
appliquer_style()


# =====================================================================
# DONNÉES (mises en cache : relues seulement si le fichier change)
# =====================================================================
@st.cache_data(show_spinner=False)
def _lire_resultats(date_modif):
    return pd.read_csv("data/resultats.csv")


@st.cache_data(show_spinner=False)
def _lire_courbe(date_modif):
    return pd.read_csv("data/courbe_bam.csv", parse_dates=["echeance", "date_valeur"])


def donnees():
    """(resultats, courbe), ou (None, None) avec un message si le notebook n'a pas été lancé."""
    if not (os.path.exists("data/resultats.csv") and os.path.exists("data/courbe_bam.csv")):
        st.info("Les résultats n'existent pas encore. Lance le notebook 02_analyse.ipynb : "
                "il crée data/resultats.csv, puis recharge cette page.")
        return None, None
    resultats = _lire_resultats(os.path.getmtime("data/resultats.csv"))
    if "duration_spread" not in resultats.columns:
        st.info("data/resultats.csv vient d'une ancienne version. Relance 02_analyse.ipynb, puis recharge la page.")
        return None, None
    return resultats, _lire_courbe(os.path.getmtime("data/courbe_bam.csv"))


def date_courbe():
    if os.path.exists("data/courbe_bam.csv"):
        d = _lire_courbe(os.path.getmtime("data/courbe_bam.csv"))["date_valeur"].iloc[0]
        return pd.Timestamp(d).strftime("%d/%m/%Y")
    return None


def fmt(x, d=2):
    """Nombre au format français : 1,13."""
    return f"{x:.{d}f}".replace(".", ",").replace("-", "−")


# =====================================================================
# PAGE : SYNTHÈSE
# =====================================================================
def page_synthese():
    resultats, courbe = donnees()
    if resultats is None:
        entete("Duration Maroc", "Risque de taux et de spread des obligations privées marocaines.")
        return

    from pipeline import resume_secteurs
    secteurs = resume_secteurs(resultats)
    part_rev = (resultats["nature_taux"] == "révisable").mean() * 100
    d_taux, d_spread = resultats["modifiee"].mean(), resultats["duration_spread"].mean()

    entete("Le risque des obligations privées marocaines",
           f"{len(resultats)} tranches visées par l'AMMC et encore en vie, valorisées sur la courbe "
           f"des Bons du Trésor de Bank Al-Maghrib du {date_courbe()}.")

    # --- L'idée clé : duration de taux vs duration de spread ---
    st.markdown(
        f'<div class="panneau"><p class="constat">Le marché paraît peu sensible aux taux : '
        f'{fmt(part_rev, 0)} % des tranches sont révisables. Mais face à une hausse des primes de risque, '
        f'il est {fmt(d_spread / d_taux, 1)} fois plus exposé.</p>'
        f'<p class="explication">Pour chaque secteur, le point bleu mesure la perte (%) si les taux de BAM '
        f'montent de 1 %, le point jaune la perte si la prime de l\'émetteur monte de 1 %. '
        f'La révision du coupon protège contre le premier risque, jamais contre le second.</p></div>',
        unsafe_allow_html=True)

    halteres = secteurs.reset_index()[["secteur", "duration_taux_moy", "duration_spread_moy"]]
    longue = halteres.melt(id_vars="secteur", var_name="mesure", value_name="duration")
    longue["mesure"] = longue["mesure"].map({"duration_taux_moy": "Duration de taux",
                                             "duration_spread_moy": "Duration de spread"})
    ordre = halteres.sort_values("duration_spread_moy", ascending=False)["secteur"].tolist()
    y = alt.Y("secteur:N", sort=ordre, title=None,
              axis=alt.Axis(labelFontSize=13, labelColor=ENCRE, labelPadding=12, labelLimit=260))
    barre = alt.Chart(halteres).mark_rule(strokeWidth=3, color=LIGNE).encode(
        y=y, x=alt.X("duration_taux_moy:Q", title="Duration (perte en % pour +1 %)"), x2="duration_spread_moy:Q")
    points = alt.Chart(longue).mark_circle(size=230, opacity=1, stroke=PANNEAU, strokeWidth=2).encode(
        y=y, x="duration:Q",
        color=alt.Color("mesure:N", title=None, scale=alt.Scale(domain=["Duration de taux", "Duration de spread"],
                                                               range=[PRINCIPAL, SECOND])),
        tooltip=["secteur", "mesure", alt.Tooltip("duration:Q", format=".2f")])
    etiquettes = alt.Chart(longue).mark_text(dy=-17, fontSize=12, fontWeight=600, color=GRIS).encode(
        y=y, x="duration:Q", text=alt.Text("duration:Q", format=".2f"))
    afficher((barre + points + etiquettes).properties(height=300))

    # --- Chiffres clés ---
    kpis([
        {"valeur": len(resultats), "libelle": "Tranches vivantes",
         "note": f"{(resultats['nature_taux'] == 'fixe').sum()} fixes, {(resultats['nature_taux'] == 'révisable').sum()} révisables"},
        {"valeur": f"{fmt(part_rev, 0)} %", "libelle": "À taux révisable", "note": "coupon recalculé chaque année"},
        {"valeur": fmt(d_taux), "libelle": "Duration de taux moyenne", "note": "perte en % pour +1 % de taux"},
        {"valeur": fmt(d_spread), "libelle": "Duration de spread moyenne", "note": "perte en % pour +1 % de prime"},
        {"valeur": f"{fmt(resultats['choc_+100pb_%'].mean())} %", "libelle": "Choc de +100 pb", "ton": "perte",
         "note": "variation moyenne du prix"},
    ])

    gauche, droite = st.columns([1, 1], gap="large")
    with gauche:
        section("La courbe des taux sans risque", "Taux de référence des Bons du Trésor, Bank Al-Maghrib.")
        c = pd.DataFrame({"maturité": courbe["maturite"], "taux": courbe["taux"] * 100})
        ligne = alt.Chart(c).mark_line(color=PRINCIPAL, strokeWidth=2.5, interpolate="monotone").encode(
            x=alt.X("maturité:Q", title="Maturité (années)"),
            y=alt.Y("taux:Q", title="Taux (%)", scale=alt.Scale(zero=False)))
        pts = alt.Chart(c).mark_circle(size=70, color=PRINCIPAL, stroke=PANNEAU, strokeWidth=1.5).encode(
            x="maturité:Q", y="taux:Q",
            tooltip=[alt.Tooltip("maturité:Q", format=".2f", title="Maturité"), alt.Tooltip("taux:Q", format=".3f", title="Taux (%)")])
        afficher((ligne + pts).properties(height=280))
    with droite:
        section("Qui émet, et à quel prix", "Primes à l'émission : le risque de l'émetteur se lit dans sa prime.")
        primes = secteurs.reset_index()
        barres = alt.Chart(primes).mark_bar(cornerRadiusEnd=4, height=22).encode(
            y=alt.Y("secteur:N", sort="-x", title=None, axis=alt.Axis(labelColor=ENCRE, labelFontSize=12)),
            x=alt.X("prime_moy_pb:Q", title="Prime de risque moyenne (pb)"),
            color=alt.Color("secteur:N", scale=ECHELLE_SECTEURS, legend=None),
            tooltip=["secteur", alt.Tooltip("prime_moy_pb:Q", format=".0f", title="Prime (pb)"),
                     alt.Tooltip("tranches:Q", title="Tranches")])
        texte = barres.mark_text(align="left", dx=6, color=GRIS, fontWeight=600).encode(
            text=alt.Text("prime_moy_pb:Q", format=".0f"))
        afficher((barres + texte).properties(height=280))

    section("Synthèse par secteur")
    tableau(secteurs.reset_index(), decimales=2)


# =====================================================================
# PAGE : MARCHÉ
# =====================================================================
def vue_rendement_risque(df):
    """Une bulle par secteur ; un clic sur une bulle affiche les tranches de ce secteur."""
    section("Rendement contre risque de taux, par secteur",
            "Chaque bulle résume un secteur : sa position donne le rendement et la duration moyens, sa taille "
            "le nombre de tranches. Clique sur une bulle pour voir ses tranches.")

    bulles = (df.groupby("secteur")
              .agg(tranches=("emetteur", "count"), rendement=("ytm_%", "mean"), duration=("modifiee", "mean"),
                   spread=("duration_spread", "mean"), prime=("prime_pb", "mean"),
                   revisables=("nature_taux", lambda s: (s == "révisable").mean() * 100))
              .reset_index())
    choix = alt.selection_point(name="secteur_choisi", fields=["secteur"], on="click", clear="dblclick")
    def bornes(col, gauche, droite):
        lo, hi = bulles[col].min(), bulles[col].max()
        e = (hi - lo) or 1
        return [lo - gauche * e, hi + droite * e]
    x = alt.X("duration:Q", title="Duration de taux moyenne",
              scale=alt.Scale(domain=bornes("duration", 0.15, 0.45), nice=False))
    y = alt.Y("rendement:Q", title="Rendement moyen (%)",
              scale=alt.Scale(domain=bornes("rendement", 0.2, 0.2), nice=False))
    cercles = alt.Chart(bulles).mark_circle(stroke=PANNEAU, strokeWidth=2).encode(
        x=x, y=y,
        size=alt.Size("tranches:Q", scale=alt.Scale(range=[500, 4200]), legend=None),
        color=alt.condition(choix, alt.Color("secteur:N", scale=ECHELLE_SECTEURS, legend=None),
                            alt.value("#222D3A")),
        opacity=alt.value(0.9),
        tooltip=[alt.Tooltip("secteur:N", title="Secteur"), alt.Tooltip("tranches:Q", title="Tranches"),
                 alt.Tooltip("rendement:Q", title="Rendement moyen (%)", format=".2f"),
                 alt.Tooltip("duration:Q", title="Duration de taux", format=".2f"),
                 alt.Tooltip("spread:Q", title="Duration de spread", format=".2f"),
                 alt.Tooltip("prime:Q", title="Prime moyenne (pb)", format=".0f"),
                 alt.Tooltip("revisables:Q", title="Révisables (%)", format=".0f")],
    ).add_params(choix)
    # Étiquette à droite de la bulle, sauf si une autre bulle est juste à droite : alors à gauche
    dx_tot = (bulles["duration"].max() - bulles["duration"].min()) or 1
    dy_tot = (bulles["rendement"].max() - bulles["rendement"].min()) or 1
    def cote(ligne):
        voisins = bulles[(bulles["duration"] > ligne["duration"])
                         & ((bulles["duration"] - ligne["duration"]) < 0.35 * dx_tot)
                         & ((bulles["rendement"] - ligne["rendement"]).abs() < 0.15 * dy_tot)]
        return "gauche" if len(voisins) else "droite"
    bulles["cote"] = bulles.apply(cote, axis=1)
    couleur_nom = alt.condition(choix, alt.value(ENCRE), alt.value(DISCRET))
    noms_d = alt.Chart(bulles).transform_filter(alt.datum.cote == "droite").mark_text(
        align="left", dx=42, fontSize=13, fontWeight=700).encode(x=x, y=y, text="secteur:N", color=couleur_nom)
    noms_g = alt.Chart(bulles).transform_filter(alt.datum.cote == "gauche").mark_text(
        align="right", dx=-42, fontSize=13, fontWeight=700).encode(x=x, y=y, text="secteur:N", color=couleur_nom)
    noms = noms_d + noms_g
    graphique = (cercles + noms).properties(height=420)

    clic = None
    try:
        evenement = st.altair_chart(graphique, width="stretch", theme=None, on_select="rerun", key="bulles")
        valeurs = evenement.selection.get("secteur_choisi", []) if evenement else []
        clic = valeurs[0]["secteur"] if valeurs else None
    except TypeError:                                   # Streamlit trop ancien pour on_select
        afficher(graphique)
        clic = st.selectbox("Secteur à détailler", ["Aucun"] + bulles["secteur"].tolist())
        clic = None if clic == "Aucun" else clic

    if clic is None:
        st.caption("Clique sur une bulle pour afficher ses tranches ; double-clique pour revenir à la vue d'ensemble.")
        return

    # ---------- Détail du secteur choisi ----------
    d = df[df["secteur"] == clic].copy()
    d["nom"] = d["emetteur"] + " " + d["tranche"].astype(str)
    fixes = d[d["nature_taux"] == "fixe"]
    section(f"{clic} : {len(d)} tranches",
            f"{(d['nature_taux'] == 'révisable').sum()} révisables, {len(fixes)} fixes. "
            "Les révisables restent groupées à gauche : leur coupon s'ajuste, leur duration de taux est courte.")
    couleur = dict(zip(SECTEURS_ORDRE, ECHELLE_SECTEURS.range))[clic] if clic in SECTEURS_ORDRE else PRINCIPAL
    points = alt.Chart(d).mark_point(size=110, filled=True, opacity=0.9, strokeWidth=0, color=couleur).encode(
        x=alt.X("modifiee:Q", title="Duration de taux"),
        y=alt.Y("ytm_%:Q", title="Rendement (%)", scale=alt.Scale(zero=False)),
        shape=alt.Shape("nature_taux:N", title="Taux", scale=alt.Scale(domain=["fixe", "révisable"],
                                                                     range=["circle", "square"])),
        tooltip=[alt.Tooltip("emetteur:N", title="Émetteur"), alt.Tooltip("tranche:N", title="Tranche"),
                 alt.Tooltip("nature_taux:N", title="Taux"),
                 alt.Tooltip("maturite_res:Q", title="Maturité restante", format=".2f"),
                 alt.Tooltip("ytm_%:Q", title="Rendement (%)", format=".2f"),
                 alt.Tooltip("modifiee:Q", title="Duration de taux", format=".2f"),
                 alt.Tooltip("duration_spread:Q", title="Duration de spread", format=".2f")])
    exposees = d.nlargest(min(3, len(d)), "modifiee")
    etiquettes = alt.Chart(exposees).mark_text(align="left", dx=9, dy=-9, fontSize=12, fontWeight=600,
                                               color=ENCRE).encode(x="modifiee:Q", y="ytm_%:Q", text="nom:N")
    gauche, droite = st.columns([2, 1], gap="large")
    with gauche:
        afficher((points + etiquettes).properties(height=340))
    with droite:
        kpis([
            {"valeur": f"{fmt(d['ytm_%'].mean())} %", "libelle": "Rendement moyen"},
            {"valeur": fmt(d["modifiee"].mean()), "libelle": "Duration de taux"},
            {"valeur": fmt(d["duration_spread"].mean()), "libelle": "Duration de spread"},
        ])
    section("Les tranches les plus exposées du secteur")
    tableau(d.nlargest(min(8, len(d)), "modifiee"),
            ["emetteur", "tranche", "nature_taux", "maturite_res", "prime_pb", "ytm_%", "modifiee",
             "duration_spread", "choc_+100pb_%"], couleur=["choc_+100pb_%"])


def page_marche():
    resultats, courbe = donnees()
    entete("Le marché, tranche par tranche",
           "Rendement, sensibilité aux taux et résistance aux chocs de chaque tranche encore en vie.")
    if resultats is None:
        return
    from pipeline import impact_scenario, resume_secteurs

    f1, f2 = st.columns([1, 3])
    natures = f1.multiselect("Taux", ["fixe", "révisable"], default=["fixe", "révisable"])
    presents = [s for s in SECTEURS_ORDRE if s in set(resultats["secteur"])]
    secteurs = f2.multiselect("Secteurs", presents, default=presents)
    df = resultats[resultats["nature_taux"].isin(natures) & resultats["secteur"].isin(secteurs)].copy()
    if df.empty:
        st.info("Aucune tranche ne correspond à ces filtres. Ajoute au moins un type de taux et un secteur.")
        return

    kpis([
        {"valeur": len(df), "libelle": "Tranches affichées"},
        {"valeur": f"{fmt(df['ytm_%'].mean())} %", "libelle": "Rendement moyen"},
        {"valeur": fmt(df["modifiee"].mean()), "libelle": "Duration de taux moyenne"},
        {"valeur": fmt(df["duration_spread"].mean()), "libelle": "Duration de spread moyenne"},
    ])

    onglets = st.tabs(["Rendement et risque", "Stress test", "Par secteur", "Toutes les tranches"])

    with onglets[0]:
        vue_rendement_risque(df)

    with onglets[1]:
        choc = st.slider("Choc sur toute la courbe (points de base)", -200, 300, 100, step=25, key="choc_marche")
        df["variation_%"] = impact_scenario(df, courbe, chocs_pb=[choc] * len(POINTS_COURBE))["variation_%"].values
        moyenne = df["variation_%"].mean()
        kpis([
            {"valeur": f"{fmt(moyenne)} %", "libelle": "Variation moyenne", "ton": ton(moyenne)},
            {"valeur": f"{fmt(df['variation_%'].min())} %", "libelle": "Pire tranche", "ton": ton(df["variation_%"].min())},
            {"valeur": f"{(df['variation_%'] < 0).sum()} / {len(df)}", "libelle": "Tranches en perte"},
        ])
        colonnes = ["emetteur", "tranche", "secteur", "nature_taux", "maturite_res", "ytm_%", "variation_%"]
        a, b = st.columns(2, gap="large")
        with a:
            section("Les plus résistantes")
            tableau(df.nlargest(10, "variation_%"), colonnes, couleur=["variation_%"])
        with b:
            section("Les plus exposées")
            tableau(df.nsmallest(10, "variation_%"), colonnes, couleur=["variation_%"])

    with onglets[2]:
        section("Moyennes par secteur", "Le seuil est la médiane de la hausse de taux absorbée en un an "
                "(non calculé pour les durations inférieures à 6 mois).")
        tableau(resume_secteurs(df).reset_index())
        section("Fixe ou révisable, par secteur")
        croise = pd.crosstab(df["secteur"], df["nature_taux"]).reset_index()
        longue = croise.melt(id_vars="secteur", var_name="Taux", value_name="Tranches")
        empile = alt.Chart(longue).mark_bar(height=22).encode(
            y=alt.Y("secteur:N", title=None, sort="-x", axis=alt.Axis(labelColor=ENCRE)),
            x=alt.X("Tranches:Q", stack="normalize", title="Part des tranches", axis=alt.Axis(format="%")),
            color=alt.Color("Taux:N", scale=alt.Scale(domain=["fixe", "révisable"], range=[PRINCIPAL, "#285A78"]),
                            title=None),
            tooltip=["secteur", "Taux", "Tranches"])
        afficher(empile.properties(height=240))

    with onglets[3]:
        colonnes = ["emetteur", "tranche", "secteur", "type", "nature_taux", "remboursement", "echeance",
                    "maturite_res", "prime_pb", "ytm_%", "prix_plein", "coupon_couru", "prix_pied",
                    "macaulay", "modifiee", "convexite", "duration_spread", "dv01", "seuil_pb"]
        tableau(df, [c for c in colonnes if c in df.columns], hauteur=520)


# =====================================================================
# PAGE : SCÉNARIOS
# =====================================================================
def page_scenarios():
    resultats, courbe = donnees()
    entete("Scénarios de taux et de spread",
           "Déforme la courbe de Bank Al-Maghrib point par point et choque la prime de risque de chaque secteur. "
           "Scénarios de départ inspirés des 6 scénarios IRRBB du Comité de Bâle.")
    if resultats is None:
        return
    from pipeline import impact_scenario

    def editeur(df, **options):
        """Tableau modifiable sur toute la largeur de sa colonne."""
        try:
            return st.data_editor(df, width="stretch", **options)
        except TypeError:
            return st.data_editor(df, use_container_width=True, **options)

    # Colonne de réglages plus large : on lit le nom complet du scénario et la colonne « Choc (pb) »
    reglages, visuel = st.columns([1.25, 1.75], gap="large")
    with reglages:
        nom = st.selectbox("Scénario de courbe", ["Aucun choc de courbe"] + list(SCENARIOS.keys()), index=7)
        base_chocs = SCENARIOS.get(nom, [0] * len(POINTS_COURBE))
        st.caption("Chocs de taux en points de base, modifiables")
        t = pd.DataFrame({"Maturité (ans)": POINTS_COURBE, "Choc (pb)": base_chocs})
        t = editeur(t, disabled=["Maturité (ans)"], hide_index=True, key=f"choc_{nom}",
                    column_config={"Maturité (ans)": st.column_config.NumberColumn(format="%g"),
                                   "Choc (pb)": st.column_config.NumberColumn(format="%d")})
        chocs = t["Choc (pb)"].fillna(0).tolist()

        st.caption("Choc de prime par secteur, en points de base")
        presents = [s for s in SECTEURS_ORDRE if s in set(resultats["secteur"])]
        s = pd.DataFrame({"Secteur": presents, "Choc (pb)": [0.0] * len(presents)})
        s = editeur(s, disabled=["Secteur"], hide_index=True, key="spreads",
                    column_config={"Choc (pb)": st.column_config.NumberColumn(format="%d")})
        spreads_pb = dict(zip(s["Secteur"], s["Choc (pb)"].fillna(0)))

    with visuel:
        section("La courbe avant et après le choc", "Pointillés : courbe actuelle de Bank Al-Maghrib. Trait plein : après le choc.")
        choc_t = fonction_choc(chocs)
        grille = [m / 4 for m in range(1, 121)]
        c = pd.DataFrame({"maturité": grille,
                          "Courbe actuelle": [np.interp(m, courbe["maturite"], courbe["taux"]) * 100 for m in grille]})
        c["Après le choc"] = c["Courbe actuelle"] + [choc_t(m) * 100 for m in grille]
        longue = c.melt(id_vars="maturité", var_name="Courbe", value_name="taux")
        graph = alt.Chart(longue).mark_line(strokeWidth=2.5, interpolate="monotone").encode(
            x=alt.X("maturité:Q", title="Maturité (années)"),
            y=alt.Y("taux:Q", title="Taux (%)", scale=alt.Scale(zero=False)),
            color=alt.Color("Courbe:N", title=None, scale=alt.Scale(domain=["Courbe actuelle", "Après le choc"],
                                                                   range=[GRIS, PRINCIPAL])),
            strokeDash=alt.StrokeDash("Courbe:N", title=None, scale=alt.Scale(
                domain=["Courbe actuelle", "Après le choc"], range=[[5, 4], [1, 0]])),
            tooltip=[alt.Tooltip("maturité:Q", title="Maturité"), "Courbe",
                     alt.Tooltip("taux:Q", format=".3f", title="Taux (%)")])
        zone = alt.Chart(c).mark_area(opacity=0.12, color=PRINCIPAL, interpolate="monotone").encode(
            x="maturité:Q", y=alt.Y("Courbe actuelle:Q", scale=alt.Scale(zero=False)), y2="Après le choc:Q")
        afficher((zone + graph).properties(height=360))

    impact = impact_scenario(resultats, courbe, chocs, spreads_pb)
    moy = impact["variation_%"].mean()
    kpis([
        {"valeur": f"{fmt(moy)} %", "libelle": "Variation moyenne", "ton": ton(moy)},
        {"valeur": f"{fmt(impact['effet_courbe_%'].mean())} %", "libelle": "dont effet courbe",
         "ton": ton(impact["effet_courbe_%"].mean())},
        {"valeur": f"{fmt(impact['effet_spread_%'].mean())} %", "libelle": "dont effet spread",
         "ton": ton(impact["effet_spread_%"].mean())},
        {"valeur": f"{(impact['variation_%'] < 0).sum()} / {len(impact)}", "libelle": "Tranches en perte"},
    ])

    onglets = st.tabs(["Impact par secteur", "Tranches", "Exposition par maturité"])
    with onglets[0]:
        # Barres groupées (fixe / révisable) par secteur, sur toute la largeur : plus de largeur fixe qui déborde
        moyennes = impact.groupby(["secteur", "nature_taux"])["variation_%"].mean().reset_index()
        y = alt.Y("secteur:N", title=None, sort=SECTEURS_ORDRE,
                  axis=alt.Axis(labelColor=ENCRE, labelFontSize=13, labelFontWeight=600, labelPadding=12, labelLimit=260))
        barres = alt.Chart(moyennes).mark_bar(cornerRadiusEnd=4, height=14).encode(
            y=y, yOffset=alt.YOffset("nature_taux:N", sort=["fixe", "révisable"]),
            x=alt.X("variation_%:Q", title="Variation moyenne du prix (%)"),
            color=alt.Color("nature_taux:N", title=None,
                            scale=alt.Scale(domain=["fixe", "révisable"], range=[PRINCIPAL, "#2B6E99"])),
            tooltip=["secteur", "nature_taux", alt.Tooltip("variation_%:Q", format=".2f")])
        def etiquettes(negatif):
            filtre = alt.datum["variation_%"] < 0 if negatif else alt.datum["variation_%"] >= 0
            return alt.Chart(moyennes).transform_filter(filtre).mark_text(
                fontSize=11, fontWeight=600, dx=-6 if negatif else 6, align="right" if negatif else "left",
                color=PERTE if negatif else GAIN).encode(
                y=y, yOffset=alt.YOffset("nature_taux:N", sort=["fixe", "révisable"]), x="variation_%:Q",
                text=alt.Text("variation_%:Q", format=".2f"))
        afficher((barres + etiquettes(True) + etiquettes(False)).properties(height=340))
        st.caption("Bleu vif : tranches à taux fixe. Bleu foncé : tranches révisables. "
                   "Chiffre rouge = perte, vert = gain.")

    with onglets[1]:
        colonnes = ["emetteur", "tranche", "secteur", "nature_taux", "maturite_res",
                    "effet_courbe_%", "effet_spread_%", "variation_%"]
        couleurs = ["effet_courbe_%", "effet_spread_%", "variation_%"]
        a, b = st.columns(2, gap="large")
        with a:
            section("Les plus pénalisées")
            tableau(impact.nsmallest(10, "variation_%"), colonnes, couleur=couleurs)
        with b:
            section("Les plus favorisées")
            tableau(impact.nlargest(10, "variation_%"), colonnes, couleur=couleurs)

    with onglets[2]:
        section("Key rate durations", "Perte (%) si UN seul point de la courbe monte de 1 %. "
                "La somme d'une ligne redonne la duration de taux du secteur.")
        krd_cols = [c for c in resultats.columns if c.startswith("KRD")]
        krd = (resultats.groupby("secteur")[krd_cols].mean().reset_index()
               .melt(id_vars="secteur", var_name="point", value_name="KRD"))
        krd["point"] = krd["point"].str.replace("KRD ", "").str.replace("a", " an")
        ordre_points = [f"{p:g} an" for p in POINTS_COURBE]
        base = alt.Chart(krd).encode(
            x=alt.X("point:N", sort=ordre_points, title="Point de la courbe", axis=alt.Axis(labelAngle=0)),
            y=alt.Y("secteur:N", sort=SECTEURS_ORDRE, title=None, axis=alt.Axis(labelColor=ENCRE, labelFontSize=12)))
        carte = base.mark_rect(cornerRadius=6, stroke=PANNEAU, strokeWidth=3).encode(
            color=alt.Color("KRD:Q", scale=alt.Scale(range=["#122130", PRINCIPAL]), title="KRD"),
            tooltip=["secteur", "point", alt.Tooltip("KRD:Q", format=".3f")])
        texte = base.mark_text(fontSize=12, fontWeight=600).encode(
            text=alt.Text("KRD:Q", format=".2f"),
            color=alt.condition(alt.datum.KRD > 0.6, alt.value("#06121A"), alt.value(ENCRE)))
        afficher((carte + texte).properties(height=300))

    with st.expander("Comment lire l'effet spread"):
        st.markdown("La prime de risque est fixée à l'émission et ne se révise jamais. Une tranche révisable "
                    "est protégée contre une hausse des taux de Bank Al-Maghrib, mais pas contre une hausse "
                    "de la prime de son émetteur : sur ce risque, elle se comporte comme une tranche fixe de "
                    "même maturité.")


# =====================================================================
# PAGE : CALCULATEUR
# =====================================================================
def graphique_lignes(df, x, titre_x, titre_y, couleurs, point=None, hauteur=320):
    longue = df.melt(id_vars=x, var_name="Série", value_name="valeur")
    series = list(couleurs)
    base = alt.Chart(longue).mark_line(strokeWidth=2.5).encode(
        x=alt.X(f"{x}:Q", title=titre_x),
        y=alt.Y("valeur:Q", title=titre_y, scale=alt.Scale(zero=False)),
        color=alt.Color("Série:N", title=None, scale=alt.Scale(domain=series, range=list(couleurs.values()))),
        strokeDash=alt.condition(alt.datum["Série"] == "Approximation duration", alt.value([6, 4]), alt.value([1, 0])),
        tooltip=[alt.Tooltip(f"{x}:Q", format=".2f"), "Série:N", alt.Tooltip("valeur:Q", format=",.2f")])
    if point is not None:
        base = base + alt.Chart(pd.DataFrame([point])).mark_circle(
            size=140, color=ENCRE, stroke=PANNEAU, strokeWidth=2).encode(x=f"{x}:Q", y="valeur:Q")
    return base.properties(height=hauteur).interactive()


def page_calculateur():
    entete("Calculateur de duration",
           "Décris une obligation, ou saisis tes propres flux : prix, durations, DV01 et convexité, "
           "avec l'effet d'un choc de taux.")

    mode = st.radio("Mode de saisie", ["Paramètres de l'obligation", "Flux personnalisés"],
                    horizontal=True, key="mode", label_visibility="collapsed")
    entrees, sorties = st.columns([1, 2.3], gap="large")

    with entrees:
        ytm_pct = st.number_input("Rendement exigé (%)", min_value=0.0, value=6.0, step=0.1)
        if mode == "Paramètres de l'obligation":
            nominal = st.number_input("Nominal (MAD)", min_value=1.0, value=100000.0, step=1000.0)
            coupon_pct = st.number_input("Taux de coupon (%)", min_value=0.0, value=5.0, step=0.1)
            maturite = int(st.number_input("Maturité (années)", min_value=1, max_value=50, value=5, step=1))
            remboursement = st.selectbox("Remboursement", ["in fine", "amortissable"])
            cash_flows, times = build_cash_flows(nominal, coupon_pct / 100, maturite, remboursement)
        else:
            st.caption("Ajoute des lignes avec le « + » en bas du tableau.")
            exemple = pd.DataFrame({"Temps (années)": [1.0, 2.0, 3.0, 4.0, 5.0],
                                    "Flux": [50.0, 50.0, 50.0, 50.0, 1050.0]})
            saisie = st.data_editor(exemple, num_rows="dynamic", hide_index=True).dropna()
            times, cash_flows = saisie["Temps (années)"].tolist(), saisie["Flux"].tolist()

    if len(cash_flows) == 0 or sum(cash_flows) <= 0:
        with sorties:
            st.info("Saisis au moins un flux positif pour lancer le calcul.")
        return

    ytm = ytm_pct / 100
    prix, mac, mod = bond_duration(cash_flows, times, ytm)
    conv = convexite(cash_flows, times, ytm)
    dv01 = mod * prix * 0.0001

    with sorties:
        kpis([
            {"valeur": f"{prix:,.2f}".replace(",", " ").replace(".", ","), "libelle": "Prix"},
            {"valeur": f"{fmt(mac)} ans", "libelle": "Duration de Macaulay", "note": "date moyenne des flux"},
            {"valeur": fmt(mod), "libelle": "Duration modifiée", "note": f"−{fmt(mod)} % pour +1 % de taux"},
            {"valeur": f"{dv01:,.2f}".replace(",", " ").replace(".", ","), "libelle": "DV01", "note": "pour +1 pb"},
            {"valeur": fmt(conv), "libelle": "Convexité"},
        ])
        onglets = st.tabs(["Flux", "Choc de taux", "Prix et rendement", "Sensibilités"])

        with onglets[0]:
            detail = pd.DataFrame({"temps": times, "flux": cash_flows})
            detail["actualisation"] = 1 / (1 + ytm) ** detail["temps"]
            detail["PV"] = detail["flux"] * detail["actualisation"]
            detail["poids"] = detail["PV"] / prix * 100
            barres = alt.Chart(detail).mark_bar(color=PRINCIPAL, cornerRadiusTopLeft=4, cornerRadiusTopRight=4,
                                                size=26).encode(
                x=alt.X("temps:Q", title="Temps (années)"), y=alt.Y("poids:Q", title="Poids dans le prix (%)"),
                tooltip=[alt.Tooltip("temps:Q", title="Temps"), alt.Tooltip("flux:Q", format=",.2f", title="Flux"),
                         alt.Tooltip("PV:Q", format=",.2f"), alt.Tooltip("poids:Q", format=".2f", title="Poids (%)")])
            regle = alt.Chart(pd.DataFrame({"x": [mac]})).mark_rule(color=PERTE, strokeDash=[4, 3], strokeWidth=2).encode(x="x:Q")
            note = alt.Chart(pd.DataFrame({"x": [mac], "t": [f"Macaulay {fmt(mac)} ans"]})).mark_text(
                align="left", dx=6, dy=-6, color=PERTE, fontWeight=700).encode(x="x:Q", y=alt.value(12), text="t:N")
            afficher((barres + regle + note).properties(height=300))
            tableau(detail.rename(columns={"temps": "Temps", "flux": "Flux", "actualisation": "Facteur d'actualisation",
                                           "poids": "Poids (%)"}), decimales=4)

        with onglets[1]:
            choc = st.slider("Choc de taux (points de base)", -300, 300, 100, step=25)
            dy = choc / 10000
            prix_choc, _, _ = bond_duration(cash_flows, times, ytm + dy)
            reel = (prix_choc - prix) / prix * 100
            approx_d = -mod * dy * 100
            approx_dc = (-mod * dy + 0.5 * conv * dy ** 2) * 100
            kpis([
                {"valeur": f"{fmt(reel)} %", "libelle": "Variation réelle", "ton": ton(reel)},
                {"valeur": f"{fmt(approx_d)} %", "libelle": "Duration seule",
                 "note": f"erreur de {fmt(abs(approx_d - reel))} point"},
                {"valeur": f"{fmt(approx_dc)} %", "libelle": "Duration et convexité",
                 "note": f"erreur de {fmt(abs(approx_dc - reel), 3)} point"},
            ])
            st.caption("La duration trace une droite, la convexité ajoute la courbure. "
                       "Plus le choc est grand, plus la convexité compte.")

        with onglets[2]:
            courbe_p = courbe_prix_rendement(cash_flows, times, ytm)
            afficher(graphique_lignes(courbe_p, "rendement_%", "Rendement (%)", "Prix",
                                      {"Prix exact": PRINCIPAL, "Approximation duration": GRIS,
                                       "Duration + convexité": SECOND},
                                      point={"rendement_%": ytm * 100, "valeur": prix}, hauteur=380))
            st.caption("Le vrai prix (bleu) reste toujours au-dessus de la tangente en pointillés : "
                       "c'est l'effet de convexité, favorable au porteur.")

        with onglets[3]:
            if mode != "Paramètres de l'obligation":
                st.info("Passe en mode « Paramètres de l'obligation » pour voir comment la duration "
                        "réagit à la maturité, au coupon et au rendement.")
            else:
                st.caption("Chaque graphique fait varier un seul paramètre ; les autres restent ceux saisis à gauche.")
                couleurs = {"Macaulay": PRINCIPAL, "Modifiée": SECOND}
                g1, g2, g3 = st.columns(3)
                with g1:
                    d = sensibilite_duration("maturite", list(range(1, 31)), nominal, coupon_pct / 100, maturite, ytm, remboursement)
                    d["Zéro-coupon"] = d["maturite"]
                    afficher(graphique_lignes(d, "maturite", "Maturité (années)", "Duration",
                                              {**couleurs, "Zéro-coupon": "#285A78"}, hauteur=260)
                             .properties(title="Selon la maturité"))
                with g2:
                    d = sensibilite_duration("coupon", [k / 1000 for k in range(0, 121, 5)], nominal,
                                             coupon_pct / 100, maturite, ytm, remboursement)
                    d["coupon"] *= 100
                    afficher(graphique_lignes(d, "coupon", "Coupon (%)", "Duration", couleurs, hauteur=260)
                             .properties(title="Selon le coupon"))
                with g3:
                    d = sensibilite_duration("rendement", [k / 1000 for k in range(5, 151, 5)], nominal,
                                             coupon_pct / 100, maturite, ytm, remboursement)
                    d["rendement"] *= 100
                    afficher(graphique_lignes(d, "rendement", "Rendement (%)", "Duration", couleurs, hauteur=260)
                             .properties(title="Selon le rendement"))

        with st.expander("Formules"):
            st.latex(r"P = \sum_t \frac{CF_t}{(1+y)^t} \qquad D_{Mac} = \frac{\sum_t t \cdot PV_t}{P} "
                     r"\qquad D_{Mod} = \frac{D_{Mac}}{1+y}")
            st.latex(r"C = \frac{\sum_t t(t+1)\, PV_t}{P\,(1+y)^2} \qquad "
                     r"\frac{\Delta P}{P} \approx -D_{Mod}\,\Delta y + \tfrac{1}{2}\,C\,(\Delta y)^2")


# =====================================================================
# NAVIGATION
# =====================================================================
PAGES = {"F1  Synthèse": page_synthese, "F2  Marché": page_marche, "F3  Scénarios": page_scenarios,
         "F4  Calculateur": page_calculateur}

marque(date_courbe())
choix = st.sidebar.radio("Navigation", list(PAGES), label_visibility="collapsed")
pied_barre()
barre_terminal(_lire_courbe(os.path.getmtime("data/courbe_bam.csv")) if os.path.exists("data/courbe_bam.csv") else None)
PAGES[choix]()
