"""Identité visuelle : un terminal de marché sombre (couleurs, polices, thème des graphiques, composants)."""
import html
import datetime as dt
import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

# ---------- Couleurs ----------
FOND = "#0B1017"           # fond de l'application
PANNEAU = "#111923"        # fond des panneaux
LIGNE = "#1E2935"          # bordures des panneaux
GRILLE = "#18222D"         # grille des graphiques
ENCRE = "#D9E1EA"          # texte principal
GRIS = "#7F8C9C"           # texte secondaire
DISCRET = "#3A4656"        # éléments estompés
AMBRE = "#FFA028"          # titres, onglet actif, navigation : la couleur du terminal
PRINCIPAL = "#4FC3F7"      # série principale (duration de taux, courbe…)
SECOND = "#F5C542"         # série secondaire (duration de spread…)
PERTE = "#FF5C5C"          # réservé aux pertes
GAIN = "#3DD68C"           # réservé aux gains

# Une couleur fixe par secteur (palette vérifiée en mode sombre : luminosité, daltonisme, contraste)
SECTEURS_ORDRE = ["Banque", "Établissement public", "Immobilier", "Société de financement", "Industrie & services"]
SECTEURS_COULEURS = ["#2E9FD6", "#C98324", "#D54A7C", "#8372E2", "#83983A"]
ECHELLE_SECTEURS = alt.Scale(domain=SECTEURS_ORDRE, range=SECTEURS_COULEURS)

LIBELLES = {
    "emetteur": "Émetteur", "tranche": "Tranche", "secteur": "Secteur", "type": "Type",
    "nature_taux": "Taux", "remboursement": "Remboursement", "echeance": "Échéance",
    "maturite_res": "Maturité restante (ans)", "prime_pb": "Prime (pb)", "coupon_%": "Coupon (%)",
    "ytm_%": "Rendement (%)", "prix_plein": "Prix plein", "coupon_couru": "Coupon couru",
    "prix_pied": "Prix pied de coupon", "macaulay": "Macaulay", "modifiee": "Duration de taux",
    "duration_spread": "Duration de spread", "convexite": "Convexité", "dv01": "DV01 (MAD)",
    "seuil_pb": "Seuil (pb)", "variation_%": "Variation (%)", "effet_courbe_%": "Effet courbe (%)",
    "effet_spread_%": "Effet spread (%)", "tranches": "Tranches", "part_revisable_pct": "Révisables (%)",
    "prime_moy_pb": "Prime moyenne (pb)", "ytm_moy_pct": "Rendement moyen (%)",
    "duration_taux_moy": "Duration de taux", "duration_spread_moy": "Duration de spread",
    "seuil_median_pb": "Seuil médian (pb)",
    "choc_-100pb_%": "Choc −100 pb (%)", "choc_+50pb_%": "Choc +50 pb (%)",
    "choc_+100pb_%": "Choc +100 pb (%)", "choc_+200pb_%": "Choc +200 pb (%)",
}

POLICE_TEXTE = "'IBM Plex Sans', 'Segoe UI', Arial, sans-serif"
POLICE_CHIFFRES = "'IBM Plex Mono', 'Consolas', 'Menlo', monospace"

CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600;700&family=IBM+Plex+Sans:wght@400;500;600;700&display=swap');

html, body, .stApp, .stApp p, .stApp li, .stApp label, .stApp input, .stApp textarea,
.stApp h1, .stApp h2, .stApp h3, .stApp [data-baseweb="select"], .stApp [data-baseweb="tag"] {{
    font-family: {POLICE_TEXTE};
}}
[data-testid="stIconMaterial"] {{ font-family: 'Material Symbols Rounded' !important; }}
.stApp {{ background: {FOND}; }}
.block-container {{ padding-top: 1.1rem; padding-bottom: 2.5rem; max-width: 1500px; }}
header[data-testid="stHeader"] {{ background: transparent; height: 0; }}
#MainMenu, footer {{ visibility: hidden; }}
.stApp p {{ font-feature-settings: "tnum" 1; }}

/* Barre de cotation en haut de page */
.terminal {{ display: flex; align-items: stretch; border: 1px solid {LIGNE}; background: {PANNEAU};
            font-family: {POLICE_CHIFFRES}; font-size: 0.82rem; margin-bottom: 1.2rem; overflow-x: auto; }}
.terminal > div {{ padding: 0.5rem 0.9rem; border-right: 1px solid {LIGNE}; white-space: nowrap; display: flex; align-items: center; gap: 0.5rem; }}
.terminal .code {{ background: {AMBRE}; color: #120B00; font-weight: 700; letter-spacing: 0.04em; }}
.terminal .lib {{ color: {GRIS}; }}
.terminal .val {{ color: {ENCRE}; font-weight: 600; }}
.terminal .heure {{ margin-left: auto; border-right: none; border-left: 1px solid {LIGNE}; color: {GRIS}; }}

/* Barre latérale : liste de fonctions */
section[data-testid="stSidebar"] {{ background: #070B10; border-right: 1px solid {LIGNE}; }}
section[data-testid="stSidebar"] [role="radiogroup"] label {{
    padding: 0.5rem 0.7rem; border-radius: 2px; margin-bottom: 1px; width: 100%; border-left: 3px solid transparent;
}}
section[data-testid="stSidebar"] [role="radiogroup"] label:hover {{ background: #101820; }}
section[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) {{ background: #141D27; border-left-color: {AMBRE}; }}
section[data-testid="stSidebar"] [role="radiogroup"] label p {{ font-family: {POLICE_CHIFFRES}; font-size: 0.88rem; color: {GRIS}; }}
section[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) p {{ color: {AMBRE}; font-weight: 600; }}
section[data-testid="stSidebar"] [role="radiogroup"] label > div > div:not([data-testid="stMarkdownContainer"]),
section[data-testid="stSidebar"] [role="radiogroup"] label > div:first-child:not(:has([data-testid="stMarkdownContainer"])) {{ display: none; }}

.marque {{ margin: 0.1rem 0 1.3rem; font-family: {POLICE_CHIFFRES}; }}
.marque-nom {{ color: {AMBRE}; font-weight: 700; font-size: 1.02rem; letter-spacing: 0.06em; }}
.marque-sous {{ color: {GRIS}; font-size: 0.75rem; margin-top: 0.15rem; }}
.pied-barre {{ color: {GRIS}; font-size: 0.75rem; line-height: 1.55; margin-top: 1.6rem;
              border-top: 1px solid {LIGNE}; padding-top: 0.9rem; }}

/* En-tête de page */
.entete {{ border-bottom: 1px solid {LIGNE}; margin-bottom: 1.1rem; padding-bottom: 0.7rem; }}
.entete h1 {{ font-size: 1.45rem; font-weight: 600; margin: 0 0 0.25rem; color: {ENCRE}; letter-spacing: 0; }}
.entete p {{ color: {GRIS}; font-size: 0.92rem; margin: 0; max-width: 90ch; }}

/* Panneau de constat */
.panneau {{ border: 1px solid {LIGNE}; border-left: 3px solid {AMBRE}; background: {PANNEAU};
           padding: 1rem 1.2rem 0.4rem; margin-bottom: 0.8rem; }}
.panneau .constat {{ font-size: 1.1rem; font-weight: 600; color: {ENCRE}; line-height: 1.45; max-width: 80ch; margin: 0 0 0.35rem; }}
.panneau .explication {{ color: {GRIS}; font-size: 0.88rem; max-width: 90ch; margin: 0 0 0.5rem; }}

/* Chiffres clés : cases de cotation */
.kpis {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 0;
        margin: 0.4rem 1px 1.2rem 0; }}
.kpi {{ background: {PANNEAU}; padding: 0.7rem 0.9rem; border: 1px solid {LIGNE}; margin: 0 -1px -1px 0; }}
.kpi-libelle {{ color: {GRIS}; font-size: 0.78rem; font-weight: 500; }}
.kpi-valeur {{ font-family: {POLICE_CHIFFRES}; font-size: 1.45rem; font-weight: 600; color: {ENCRE};
              line-height: 1.25; margin-top: 0.15rem; }}
.kpi-note {{ color: {DISCRET}; font-size: 0.74rem; margin-top: 0.1rem; color: #5D6B7C; }}
.kpi.perte .kpi-valeur {{ color: {PERTE}; }}
.kpi.gain .kpi-valeur {{ color: {GAIN}; }}

/* Titres de panneau */
.section {{ margin: 1.1rem 0 0.5rem; border-bottom: 1px solid {LIGNE}; padding-bottom: 0.35rem; }}
.section h3 {{ font-family: {POLICE_CHIFFRES}; font-size: 0.86rem; font-weight: 600; margin: 0; color: {AMBRE};
              letter-spacing: 0.05em; text-transform: uppercase; }}
.section p {{ color: {GRIS}; font-size: 0.84rem; margin: 0.2rem 0 0; max-width: 95ch; }}

/* Onglets : fonctions */
.stTabs [role="tablist"] {{ gap: 0; border-bottom: 1px solid {LIGNE}; box-shadow: none; margin-bottom: 0.4rem; }}
.stTabs [role="tab"] {{ height: 36px; padding: 0 14px; border-radius: 0; background: transparent; border: none;
                       border-bottom: 2px solid transparent; display: flex; align-items: center; }}
.stTabs [role="tab"] p {{ font-family: {POLICE_CHIFFRES}; font-size: 0.84rem; color: {GRIS}; font-weight: 500; }}
.stTabs [role="tab"][aria-selected="true"] {{ border-bottom-color: {AMBRE}; background: #121B25; }}
.stTabs [role="tab"][aria-selected="true"] p {{ color: {AMBRE}; font-weight: 600; }}
.stTabs .react-aria-SelectionIndicator, .stTabs [data-baseweb="tab-highlight"],
.stTabs [data-baseweb="tab-border"] {{ display: none; }}

/* Champs, tableaux, étiquettes */
.stApp [data-baseweb="tag"] {{ background: #1A2531 !important; border: 1px solid {LIGNE}; border-radius: 2px; }}
.stApp [data-baseweb="tag"] span, .stApp [data-baseweb="tag"] svg {{ color: {ENCRE} !important; fill: {GRIS} !important;
    font-family: {POLICE_CHIFFRES}; font-size: 0.8rem; }}
.stApp input, .stApp [data-baseweb="select"] > div, .stNumberInput > div {{ border-radius: 2px !important; }}
.stApp input {{ font-family: {POLICE_CHIFFRES}; }}
[data-testid="stDataFrame"], [data-testid="stDataEditor"] {{ border: 1px solid {LIGNE}; border-radius: 0; }}
[data-testid="stExpander"] details {{ border: 1px solid {LIGNE}; border-radius: 0; background: {PANNEAU}; }}
[data-testid="stVegaLiteChart"] {{ border: 1px solid {LIGNE}; background: {PANNEAU}; }}
.stCaption, [data-testid="stCaptionContainer"] p {{ color: {GRIS} !important; }}
:focus-visible {{ outline: 2px solid {AMBRE} !important; outline-offset: 2px; }}
</style>
"""


def appliquer_style():
    st.markdown(CSS, unsafe_allow_html=True)
    _enregistrer_theme_altair()


def _theme():
    return {"config": {
        "font": "IBM Plex Sans, Segoe UI, Arial, sans-serif", "background": PANNEAU,
        "padding": 12, "view": {"stroke": None},
        "axis": {"labelColor": GRIS, "titleColor": GRIS, "gridColor": GRILLE, "domainColor": LIGNE,
                 "tickColor": LIGNE, "labelFontSize": 11, "titleFontSize": 11, "titleFontWeight": 500,
                 "labelFont": "IBM Plex Mono, Consolas, monospace", "titlePadding": 10, "labelPadding": 6},
        "legend": {"labelColor": ENCRE, "titleColor": GRIS, "labelFontSize": 11, "titleFontSize": 11,
                   "orient": "bottom", "symbolSize": 80},
        "header": {"labelColor": ENCRE, "titleColor": GRIS},
        "range": {"category": SECTEURS_COULEURS},
        "title": {"color": AMBRE, "fontSize": 12, "fontWeight": 600, "anchor": "start",
                  "font": "IBM Plex Mono, Consolas, monospace"},
        "text": {"color": ENCRE},
        "line": {"strokeWidth": 2}, "point": {"size": 70},
    }}


def _enregistrer_theme_altair():
    try:                                    # Altair >= 5.5
        alt.theme.register("terminal", enable=True)(_theme)
    except AttributeError:
        alt.themes.register("terminal", _theme)
        alt.themes.enable("terminal")


# ---------- Composants ----------
def marque(date_courbe=None):
    sous = f"Courbe BAM {date_courbe}" if date_courbe else "Bank Al-Maghrib · AMMC"
    st.sidebar.markdown(f'<div class="marque"><div class="marque-nom">DURATION MAROC</div>'
                        f'<div class="marque-sous">{html.escape(sous)}</div></div>', unsafe_allow_html=True)


def pied_barre():
    st.sidebar.markdown(
        '<div class="pied-barre">Sources : taux de référence des Bons du Trésor (Bank Al-Maghrib), '
        "emprunts obligataires visés par l'AMMC.<br>Projet personnel ; hypothèses dans le README.</div>",
        unsafe_allow_html=True)


def barre_terminal(courbe=None):
    """Barre de cotation : taux BDT clés de la courbe Bank Al-Maghrib, date de valeur, heure."""
    cases = ['<div class="code">DURATION MAROC</div>']
    if courbe is not None:
        for m, nom in [(1, "BDT 1A"), (2, "2A"), (5, "5A"), (10, "10A")]:
            t = float(np.interp(m, courbe["maturite"], courbe["taux"])) * 100
            cases.append(f'<div><span class="lib">{nom}</span><span class="val">{t:.3f} %</span></div>'.replace(".", ","))
        if "date_valeur" in courbe.columns:
            d = pd.Timestamp(courbe["date_valeur"].iloc[0]).strftime("%d/%m/%Y")
            cases.append(f'<div><span class="lib">Courbe du</span><span class="val">{d}</span></div>')
    cases.append(f'<div class="heure">{dt.datetime.now().strftime("%d/%m %H:%M")}</div>')
    st.markdown(f'<div class="terminal">{"".join(cases)}</div>', unsafe_allow_html=True)


def entete(titre, texte):
    st.markdown(f'<div class="entete"><h1>{html.escape(titre)}</h1><p>{html.escape(texte)}</p></div>',
                unsafe_allow_html=True)


def section(titre, texte=None):
    p = f"<p>{html.escape(texte)}</p>" if texte else ""
    st.markdown(f'<div class="section"><h3>{html.escape(titre)}</h3>{p}</div>', unsafe_allow_html=True)


def kpis(cartes):
    """cartes : liste de dict(valeur, libelle, note=None, ton=None) ; ton = 'perte' ou 'gain'."""
    blocs = []
    for c in cartes:
        note = f'<div class="kpi-note">{html.escape(c["note"])}</div>' if c.get("note") else ""
        blocs.append(f'<div class="kpi {c.get("ton") or ""}"><div class="kpi-libelle">{html.escape(c["libelle"])}</div>'
                     f'<div class="kpi-valeur">{html.escape(str(c["valeur"]))}</div>{note}</div>')
    st.markdown(f'<div class="kpis">{"".join(blocs)}</div>', unsafe_allow_html=True)


def ton(valeur):
    return "perte" if valeur < 0 else ("gain" if valeur > 0 else None)


def afficher(graph):
    """Affiche un graphique Altair avec NOTRE thème (theme=None désactive celui de Streamlit)."""
    try:
        st.altair_chart(graph, width="stretch", theme=None)
    except TypeError:
        st.altair_chart(graph, use_container_width=True, theme=None)


def tableau(df, colonnes=None, couleur=(), decimales=2, hauteur=None, index=False):
    """Tableau lisible : libellés en français, nombres arrondis, colonnes de variation en rouge/vert."""
    d = df[colonnes].copy() if colonnes else df.copy()
    d = d.rename(columns=LIBELLES)
    couleur = [LIBELLES.get(c, c) for c in couleur]
    numeriques = d.select_dtypes("number").columns
    style = d.style.format({c: f"{{:.{decimales}f}}" for c in numeriques}, na_rep="–")

    def colorer(v):
        if pd.isna(v) or v == 0:
            return ""
        return f"color: {PERTE if v < 0 else GAIN}; font-weight: 600"
    if couleur:
        style = (style.map if hasattr(style, "map") else style.applymap)(colorer, subset=couleur)
    options = {"hide_index": not index}
    if hauteur:
        options["height"] = hauteur
    try:
        st.dataframe(style, width="stretch", **options)
    except TypeError:
        st.dataframe(style, use_container_width=True, **options)
