"""Identité visuelle « salle de marché vivante » : couleurs, polices, animations, thème des graphiques, composants."""
import html
import datetime as dt
import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

# ---------- Couleurs ----------
FOND = "#060A10"           # fond de l'application
PANNEAU = "#0C131C"        # fond des panneaux
LIGNE = "#1A2633"          # bordures des panneaux
GRILLE = "#141E29"         # grille des graphiques
ENCRE = "#E3EAF2"          # texte principal
GRIS = "#8494A6"           # texte secondaire
DISCRET = "#3A4656"        # éléments estompés
AMBRE = "#FFA62B"          # titres, onglet actif, navigation : la couleur du terminal
PRINCIPAL = "#3FB6FF"      # bleu électrique : série principale (duration de taux, courbe…)
SECOND = "#FFD24A"         # série secondaire (duration de spread…)
PERTE = "#FF5A6A"          # réservé aux pertes
GAIN = "#2EE6A0"           # réservé aux gains

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

POLICE_TITRES = "'Space Grotesk', 'IBM Plex Sans', 'Segoe UI', Arial, sans-serif"
POLICE_TEXTE = "'IBM Plex Sans', 'Segoe UI', Arial, sans-serif"
POLICE_CHIFFRES = "'IBM Plex Mono', 'Consolas', 'Menlo', monospace"

# Le CSS est écrit en clair ; les mots __FOND__, __AMBRE__… sont remplacés par les couleurs ci-dessus.
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600;700&family=IBM+Plex+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap');

html, body, .stApp, .stApp p, .stApp li, .stApp label, .stApp input, .stApp textarea,
.stApp [data-baseweb="select"], .stApp [data-baseweb="tag"] { font-family: __TEXTE__; }
[data-testid="stIconMaterial"] { font-family: 'Material Symbols Rounded' !important; }

/* Fond : nuit profonde, deux halos (ambre, bleu) et une grille très légère de salle de marché */
.stApp {
    background:
        radial-gradient(900px 500px at 85% -10%, rgba(63,182,255,0.10), transparent 60%),
        radial-gradient(700px 420px at 10% 110%, rgba(255,166,43,0.07), transparent 60%),
        linear-gradient(rgba(255,255,255,0.018) 1px, transparent 1px) 0 0 / 100% 32px,
        linear-gradient(90deg, rgba(255,255,255,0.018) 1px, transparent 1px) 0 0 / 32px 100%,
        __FOND__;
    background-attachment: fixed;
}
.block-container { padding-top: 1.1rem; padding-bottom: 3rem; max-width: 1500px; }
header[data-testid="stHeader"] { background: transparent; height: 0; }
#MainMenu, footer { visibility: hidden; }
.stApp p { font-feature-settings: "tnum" 1; }

/* ---------- Animations ---------- */
@keyframes monter   { from { opacity: 0; transform: translateY(14px); } to { opacity: 1; transform: none; } }
@keyframes balayer  { from { clip-path: inset(0 100% 0 0); } to { clip-path: inset(0 0 0 0); } }
@keyframes defiler  { from { transform: translateX(0); } to { transform: translateX(-50%); } }
@keyframes pulser   { 0%, 100% { box-shadow: 0 0 0 0 rgba(46,230,160,0.55); } 70% { box-shadow: 0 0 0 7px rgba(46,230,160,0); } }
@keyframes grandir  { from { width: 0; } to { width: 72px; } }
@keyframes lueur    { 0%, 100% { opacity: 0.35; } 50% { opacity: 1; } }
@media (prefers-reduced-motion: reduce) { *, *::before, *::after { animation: none !important; transition: none !important; } }

/* ---------- Bandeau de cotation qui défile ---------- */
.terminal { display: flex; align-items: stretch; border: 1px solid __LIGNE__; background: rgba(12,19,28,0.92);
            font-family: __CHIFFRES__; font-size: 0.82rem; margin-bottom: 1.4rem; overflow: hidden;
            box-shadow: 0 8px 30px rgba(0,0,0,0.35); }
.terminal .code { background: __AMBRE__; color: #120B00; font-weight: 700; letter-spacing: 0.06em;
                  padding: 0.55rem 0.95rem; white-space: nowrap; display: flex; align-items: center; gap: 0.55rem;
                  position: relative; z-index: 2; box-shadow: 8px 0 18px rgba(6,10,16,0.9); }
.terminal .direct { width: 8px; height: 8px; border-radius: 50%; background: #120B00; animation: lueur 1.6s ease-in-out infinite; }
.terminal .fenetre { flex: 1; overflow: hidden; position: relative;
                     mask-image: linear-gradient(90deg, transparent, #000 4%, #000 96%, transparent);
                     -webkit-mask-image: linear-gradient(90deg, transparent, #000 4%, #000 96%, transparent); }
.terminal .piste { display: flex; width: max-content; animation: defiler 38s linear infinite; }
.terminal:hover .piste { animation-play-state: paused; }
.terminal .item { padding: 0.55rem 1.1rem; border-right: 1px solid __LIGNE__; white-space: nowrap;
                  display: flex; align-items: center; gap: 0.5rem; }
.terminal .lib { color: __GRIS__; }
.terminal .val { color: __ENCRE__; font-weight: 600; }
.terminal .hausse { color: __GAIN__; font-weight: 600; }
.terminal .baisse { color: __PERTE__; font-weight: 600; }
.terminal .heure { border-left: 1px solid __LIGNE__; color: __GRIS__; padding: 0.55rem 0.95rem; white-space: nowrap;
                   display: flex; align-items: center; position: relative; z-index: 2; background: __PANNEAU__; }

/* ---------- Barre latérale ---------- */
section[data-testid="stSidebar"] { background: linear-gradient(180deg, #080D14, #05080D); border-right: 1px solid __LIGNE__; }
section[data-testid="stSidebar"] [role="radiogroup"] label {
    padding: 0.55rem 0.75rem; border-radius: 3px; margin-bottom: 2px; width: 100%; border-left: 3px solid transparent;
    transition: background 0.2s ease, transform 0.2s ease, border-color 0.2s ease;
}
section[data-testid="stSidebar"] [role="radiogroup"] label:hover { background: #0F1822; transform: translateX(3px); }
section[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) {
    background: linear-gradient(90deg, rgba(255,166,43,0.16), rgba(255,166,43,0.02)); border-left-color: __AMBRE__; }
section[data-testid="stSidebar"] [role="radiogroup"] label p { font-family: __CHIFFRES__; font-size: 0.88rem; color: __GRIS__; }
section[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) p { color: __AMBRE__; font-weight: 600; }
section[data-testid="stSidebar"] [role="radiogroup"] label > div > div:not([data-testid="stMarkdownContainer"]),
section[data-testid="stSidebar"] [role="radiogroup"] label > div:first-child:not(:has([data-testid="stMarkdownContainer"])) { display: none; }

.marque { margin: 0.1rem 0 1.4rem; font-family: __CHIFFRES__; }
.marque-nom { font-family: __TITRES__; font-weight: 700; font-size: 1.25rem; letter-spacing: 0.04em;
              background: linear-gradient(90deg, __AMBRE__, #FFD27A); -webkit-background-clip: text; background-clip: text; color: transparent; }
.marque-sous { color: __GRIS__; font-size: 0.75rem; margin-top: 0.3rem; display: flex; align-items: center; gap: 0.45rem; }
.marque-sous .point { width: 7px; height: 7px; border-radius: 50%; background: __GAIN__; animation: pulser 2s infinite; }
.pied-barre { color: __GRIS__; font-size: 0.75rem; line-height: 1.55; margin-top: 1.6rem;
              border-top: 1px solid __LIGNE__; padding-top: 0.9rem; }

/* ---------- En-tête de page ---------- */
.entete { margin-bottom: 1.3rem; padding-bottom: 0.2rem; animation: monter 0.5s ease both; }
.entete h1 { font-family: __TITRES__; font-size: 2rem; font-weight: 700; margin: 0 0 0.35rem; color: __ENCRE__;
             letter-spacing: -0.01em; line-height: 1.15; }
.entete .trait { height: 3px; width: 72px; background: linear-gradient(90deg, __AMBRE__, __PRINCIPAL__);
                 border-radius: 2px; margin: 0.2rem 0 0.7rem; animation: grandir 0.8s 0.15s ease both; }
.entete p { color: __GRIS__; font-size: 0.95rem; margin: 0; max-width: 90ch; }

/* ---------- Panneau de constat ---------- */
.panneau { position: relative; border: 1px solid __LIGNE__; background: linear-gradient(135deg, rgba(255,166,43,0.07), __PANNEAU__ 45%);
           padding: 1.1rem 1.3rem 0.5rem; margin-bottom: 1rem; border-radius: 6px; overflow: hidden;
           animation: monter 0.55s 0.1s ease both; }
.panneau::before { content: ""; position: absolute; left: 0; top: 0; bottom: 0; width: 3px;
                   background: linear-gradient(180deg, __AMBRE__, __PRINCIPAL__); }
.panneau .constat { font-family: __TITRES__; font-size: 1.2rem; font-weight: 600; color: __ENCRE__; line-height: 1.45;
                    max-width: 80ch; margin: 0 0 0.4rem; }
.panneau .explication { color: __GRIS__; font-size: 0.88rem; max-width: 90ch; margin: 0 0 0.55rem; }

/* ---------- Chiffres clés : cartes qui s'illuminent ---------- */
.kpis { display: flex; flex-wrap: wrap; gap: 10px; margin: 0.5rem 0 1.3rem; }
.kpi { flex: 1 1 165px; position: relative; background: __PANNEAU__; padding: 0.8rem 1rem 0.75rem;
       border: 1px solid __LIGNE__; border-radius: 6px; overflow: hidden;
       transition: transform 0.25s ease, border-color 0.25s ease, box-shadow 0.25s ease;
       animation: monter 0.5s ease both; animation-delay: calc(var(--i, 0) * 70ms + 0.1s); }
.kpi::after { content: ""; position: absolute; left: 0; right: 0; top: 0; height: 2px;
              background: linear-gradient(90deg, transparent, __AMBRE__, transparent);
              transform: scaleX(0); transition: transform 0.35s ease; }
.kpi:hover { transform: translateY(-3px); border-color: rgba(255,166,43,0.55);
             box-shadow: 0 10px 28px rgba(0,0,0,0.45), 0 0 22px rgba(255,166,43,0.16); }
.kpi:hover::after { transform: scaleX(1); }
.kpi-libelle { color: __GRIS__; font-size: 0.78rem; font-weight: 500; }
.kpi-valeur { font-family: __CHIFFRES__; font-size: 1.6rem; font-weight: 600; color: __ENCRE__;
              line-height: 1.25; margin-top: 0.2rem; white-space: nowrap; }
.kpi-note { font-size: 0.74rem; margin-top: 0.15rem; color: #62728A; }
.kpi.perte .kpi-valeur { color: __PERTE__; text-shadow: 0 0 18px rgba(255,90,106,0.35); }
.kpi.gain .kpi-valeur { color: __GAIN__; text-shadow: 0 0 18px rgba(46,230,160,0.35); }
.kpi.perte { border-bottom: 2px solid rgba(255,90,106,0.6); }
.kpi.gain { border-bottom: 2px solid rgba(46,230,160,0.6); }

/* ---------- Titres de panneau ---------- */
.section { margin: 1.4rem 0 0.6rem; animation: monter 0.5s ease both; }
.section h3 { font-family: __CHIFFRES__; font-size: 0.84rem; font-weight: 600; margin: 0; color: __AMBRE__;
              letter-spacing: 0.08em; text-transform: uppercase; display: flex; align-items: center; gap: 0.6rem; }
.section h3::before { content: ""; width: 10px; height: 10px; border-radius: 2px;
                      background: linear-gradient(135deg, __AMBRE__, __PRINCIPAL__); flex: none; }
.section h3::after { content: ""; flex: 1; height: 1px; background: linear-gradient(90deg, __LIGNE__, transparent); }
.section p { color: __GRIS__; font-size: 0.85rem; margin: 0.3rem 0 0; max-width: 95ch; }

/* ---------- Graphiques : ils se dessinent de gauche à droite à leur arrivée ---------- */
[data-testid="stVegaLiteChart"] { border: 1px solid __LIGNE__; background: __PANNEAU__; border-radius: 6px;
                                  overflow: hidden; transition: border-color 0.25s ease, box-shadow 0.25s ease; }
[data-testid="stVegaLiteChart"] canvas, [data-testid="stVegaLiteChart"] svg { animation: balayer 1.1s cubic-bezier(.2,.7,.2,1) both; }
[data-testid="stVegaLiteChart"]:hover { border-color: rgba(63,182,255,0.45); box-shadow: 0 0 24px rgba(63,182,255,0.10); }
#vg-tooltip-element { background: #0E1722 !important; color: __ENCRE__ !important; border: 1px solid rgba(255,166,43,0.5) !important;
                      border-radius: 6px !important; font-family: __CHIFFRES__ !important; font-size: 12px !important;
                      box-shadow: 0 8px 24px rgba(0,0,0,0.5) !important; }
#vg-tooltip-element td.key { color: __GRIS__ !important; }

/* ---------- Onglets ---------- */
.stTabs [role="tablist"] { gap: 4px; border-bottom: 1px solid __LIGNE__; box-shadow: none; margin-bottom: 0.6rem; }
.stTabs [role="tab"] { height: 38px; padding: 0 15px; border-radius: 4px 4px 0 0; background: transparent; border: none;
                       border-bottom: 2px solid transparent; display: flex; align-items: center; transition: background 0.2s ease; }
.stTabs [role="tab"]:hover { background: rgba(255,255,255,0.03); }
.stTabs [role="tab"] p { font-family: __CHIFFRES__; font-size: 0.84rem; color: __GRIS__; font-weight: 500; }
.stTabs [role="tab"][aria-selected="true"] { border-bottom-color: __AMBRE__;
    background: linear-gradient(180deg, rgba(255,166,43,0.0), rgba(255,166,43,0.10));
    box-shadow: 0 6px 14px -8px rgba(255,166,43,0.7); }
.stTabs [role="tab"][aria-selected="true"] p { color: __AMBRE__; font-weight: 600; }
.stTabs .react-aria-SelectionIndicator, .stTabs [data-baseweb="tab-highlight"],
.stTabs [data-baseweb="tab-border"] { display: none; }
.stTabs [role="tabpanel"] { animation: monter 0.4s ease both; }

/* ---------- Champs, tableaux, étiquettes ---------- */
.stApp [data-baseweb="tag"] { background: rgba(255,166,43,0.14) !important; border: 1px solid rgba(255,166,43,0.45); border-radius: 4px; }
.stApp [data-baseweb="tag"] span, .stApp [data-baseweb="tag"] svg { color: __ENCRE__ !important; fill: __AMBRE__ !important;
    font-family: __CHIFFRES__; font-size: 0.8rem; }
.stApp input, .stApp [data-baseweb="select"] > div, .stNumberInput > div { border-radius: 4px !important; }
.stApp input { font-family: __CHIFFRES__; }
[data-testid="stDataFrame"], [data-testid="stDataEditor"] { border: 1px solid __LIGNE__; border-radius: 6px; overflow: hidden;
    animation: monter 0.5s 0.15s ease both; }
[data-testid="stExpander"] details { border: 1px solid __LIGNE__; border-radius: 6px; background: __PANNEAU__; }
.stCaption, [data-testid="stCaptionContainer"] p { color: __GRIS__ !important; }
[data-testid="stSlider"] [role="slider"] { box-shadow: 0 0 0 5px rgba(255,166,43,0.18); }
:focus-visible { outline: 2px solid __AMBRE__ !important; outline-offset: 2px; }
</style>
"""

JETONS = {"__FOND__": FOND, "__PANNEAU__": PANNEAU, "__LIGNE__": LIGNE, "__ENCRE__": ENCRE, "__GRIS__": GRIS,
          "__AMBRE__": AMBRE, "__PRINCIPAL__": PRINCIPAL, "__PERTE__": PERTE, "__GAIN__": GAIN,
          "__TITRES__": POLICE_TITRES, "__TEXTE__": POLICE_TEXTE, "__CHIFFRES__": POLICE_CHIFFRES}

# Petit script : les chiffres clés « comptent » de 0 jusqu'à leur valeur (0,9 s) quand ils apparaissent ou changent.
COMPTEUR = """
<script>
(function () {
  const P = window.parent, doc = P.document;
  if (P.__dmCompteur) return;
  P.__dmCompteur = true;
  if (P.matchMedia && P.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  const MOTIF = /[−-]?\\d+(?:[ \\u202f\\u00a0]\\d{3})*(?:,\\d+)?/;
  function animer(el, final) {
    const m = final.match(MOTIF);
    if (!m) { el.textContent = final; return; }
    const brut = m[0], neg = /^[−-]/.test(brut), espaces = /\\d[ \\u202f\\u00a0]\\d/.test(brut);
    const dec = (brut.split(',')[1] || '').length;
    const cible = parseFloat(brut.replace(/^[−-]/, '').replace(/[ \\u202f\\u00a0]/g, '').replace(',', '.'));
    const t0 = performance.now(), duree = 900;
    function ecrire(v) {
      let [e, f] = v.toFixed(dec).split('.');
      if (espaces) e = e.replace(/\\B(?=(\\d{3})+(?!\\d))/g, ' ');
      return (neg ? '−' : '') + e + (f ? ',' + f : '');
    }
    function pas(t) {
      const p = Math.min(1, (t - t0) / duree), k = 1 - Math.pow(1 - p, 3);
      el.textContent = p < 1 ? final.replace(brut, ecrire(cible * k)) : final;
      if (p < 1) P.requestAnimationFrame(pas);
    }
    P.requestAnimationFrame(pas);
  }
  function scanner() {
    doc.querySelectorAll('.kpi-valeur[data-v]').forEach(function (el) {
      const v = el.getAttribute('data-v');
      if (el.dataset.vu !== v) { el.dataset.vu = v; animer(el, v); }
    });
  }
  let attente = false;
  new P.MutationObserver(function () {
    if (attente) return; attente = true;
    P.requestAnimationFrame(function () { attente = false; scanner(); });
  }).observe(doc.body, { childList: true, subtree: true });
  scanner();
})();
</script>
"""


def _css():
    css = CSS
    for jeton, valeur in JETONS.items():
        css = css.replace(jeton, valeur)
    return css


def appliquer_style():
    st.markdown(_css(), unsafe_allow_html=True)
    _enregistrer_theme_altair()
    _installer_compteur()


def _installer_compteur():
    """Le script tourne dans un petit cadre invisible et agit sur la page (même origine)."""
    try:
        with st.sidebar:
            if hasattr(st, "iframe"):            # Streamlit récent
                st.iframe(COMPTEUR, height=1)
            else:                                # Streamlit plus ancien
                import streamlit.components.v1 as components
                components.html(COMPTEUR, height=0)
    except Exception:
        pass                                     # sans animation, les chiffres restent simplement affichés


def _theme():
    return {"config": {
        "font": "IBM Plex Sans, Segoe UI, Arial, sans-serif", "background": PANNEAU,
        "padding": 14, "view": {"stroke": None},
        "axis": {"labelColor": GRIS, "titleColor": GRIS, "gridColor": GRILLE, "gridOpacity": 0.8,
                 "domain": False, "tickColor": LIGNE, "tickSize": 4, "labelFontSize": 11, "titleFontSize": 11,
                 "titleFontWeight": 500, "labelFont": "IBM Plex Mono, Consolas, monospace",
                 "titlePadding": 10, "labelPadding": 6},
        "legend": {"labelColor": ENCRE, "titleColor": GRIS, "labelFontSize": 11, "titleFontSize": 11,
                   "orient": "bottom", "symbolSize": 90, "symbolStrokeWidth": 0},
        "header": {"labelColor": ENCRE, "titleColor": GRIS},
        "range": {"category": SECTEURS_COULEURS},
        "title": {"color": AMBRE, "fontSize": 12, "fontWeight": 600, "anchor": "start",
                  "font": "IBM Plex Mono, Consolas, monospace"},
        "text": {"color": ENCRE},
        "line": {"strokeWidth": 2.5, "strokeCap": "round"}, "point": {"size": 70},
        "bar": {"cornerRadiusEnd": 4},
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
                        f'<div class="marque-sous"><span class="point"></span>{html.escape(sous)}</div></div>',
                        unsafe_allow_html=True)


def pied_barre():
    st.sidebar.markdown(
        '<div class="pied-barre">Sources : taux de référence des Bons du Trésor (Bank Al-Maghrib), '
        "emprunts obligataires visés par l'AMMC.<br>Projet personnel ; hypothèses dans le README.</div>",
        unsafe_allow_html=True)


def _pct(x, d=3):
    return f"{x:.{d}f} %".replace(".", ",")


def barre_terminal(courbe=None):
    """Bandeau de cotation qui défile : taux BDT clés, pentes de la courbe, date de valeur ; heure fixe à droite."""
    items = []
    if courbe is not None:
        def taux(m):
            return float(np.interp(m, courbe["maturite"], courbe["taux"])) * 100
        for m, nom in [(0.25, "BDT 3M"), (1, "BDT 1A"), (2, "2A"), (5, "5A"), (10, "10A"), (15, "15A"), (20, "20A"), (30, "30A")]:
            if m <= courbe["maturite"].max() + 1:
                items.append(f'<div class="item"><span class="lib">{nom}</span><span class="val">{_pct(taux(m))}</span></div>')
        for a, b, nom in [(2, 10, "Pente 2A-10A"), (1, 5, "Pente 1A-5A")]:
            pb = (taux(b) - taux(a)) * 100
            sens, fleche = ("hausse", "▲") if pb >= 0 else ("baisse", "▼")
            items.append(f'<div class="item"><span class="lib">{nom}</span>'
                         f'<span class="{sens}">{fleche} {f"{pb:+.0f}".replace("-", "−")} pb</span></div>')
        if "date_valeur" in courbe.columns:
            d = pd.Timestamp(courbe["date_valeur"].iloc[0]).strftime("%d/%m/%Y")
            items.append(f'<div class="item"><span class="lib">Courbe du</span><span class="val">{d}</span></div>')
    if not items:
        items.append('<div class="item"><span class="lib">Courbe BAM indisponible</span></div>')
    piste = "".join(items) * 2              # contenu en double : la boucle de défilement est continue
    st.markdown(
        f'<div class="terminal"><div class="code"><span class="direct"></span>DURATION MAROC</div>'
        f'<div class="fenetre"><div class="piste">{piste}</div></div>'
        f'<div class="heure">{dt.datetime.now().strftime("%d/%m %H:%M")}</div></div>',
        unsafe_allow_html=True)


def entete(titre, texte):
    st.markdown(f'<div class="entete"><h1>{html.escape(titre)}</h1><div class="trait"></div>'
                f'<p>{html.escape(texte)}</p></div>', unsafe_allow_html=True)


def section(titre, texte=None):
    p = f"<p>{html.escape(texte)}</p>" if texte else ""
    st.markdown(f'<div class="section"><h3>{html.escape(titre)}</h3>{p}</div>', unsafe_allow_html=True)


def kpis(cartes):
    """cartes : liste de dict(valeur, libelle, note=None, ton=None) ; ton = 'perte' ou 'gain'."""
    blocs = []
    for i, c in enumerate(cartes):
        note = f'<div class="kpi-note">{html.escape(c["note"])}</div>' if c.get("note") else ""
        valeur = html.escape(str(c["valeur"]))
        blocs.append(f'<div class="kpi {c.get("ton") or ""}" style="--i:{i}">'
                     f'<div class="kpi-libelle">{html.escape(c["libelle"])}</div>'
                     f'<div class="kpi-valeur" data-v="{valeur}">{valeur}</div>{note}</div>')
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
