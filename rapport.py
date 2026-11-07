"""Exports des résultats : un fichier Excel (un onglet par analyse) et un rapport HTML avec graphiques."""
import json
import pandas as pd
import altair as alt

from calculs import SCENARIOS, POINTS_COURBE
from pipeline import resume_secteurs, tous_les_scenarios

HYPOTHESES = [
    "Taux sans risque : courbe des taux de référence des Bons du Trésor (Bank Al-Maghrib), interpolée linéairement.",
    "Prime de risque : milieu de la fourchette annoncée dans la note d'opération AMMC (prime à l'émission).",
    "Tranche fixe : coupon = taux BDT à la maturité résiduelle + prime (tranche valorisée proche du pair).",
    "Tranche révisable : coupon = BDT 1 an + prime ; exposée aux taux jusqu'à sa prochaine révision seulement.",
    "Coupons annuels aux dates anniversaires de l'échéance ; temps en fractions d'année (Exact/365).",
    "Chaque flux est actualisé à son propre taux : courbe BAM(t) + prime. Duration et convexité effectives (±1 pb).",
    "Échéance manquante dans le PDF : date de visa AMMC + maturité (colonne echeance_estimee).",
    "Scénarios de courbe inspirés des 6 scénarios IRRBB de Bâle, amplitudes illustratives.",
    "Choc de spread : appliqué sur tout l'échéancier, révisables comprises (la prime ne se révise pas).",
    "Moyennes simples par tranche, non pondérées par les montants. Perpétuelles et remboursables en actions exclues.",
]

COLONNES_TRANCHES = ["emetteur", "tranche", "type", "secteur", "nature_taux", "remboursement",
                     "echeance", "echeance_estimee", "maturite_res", "prochain_flux_ans", "taux_bam_%",
                     "prime_pb", "coupon_%", "prix_plein", "coupon_couru", "prix_pied", "macaulay",
                     "modifiee", "convexite", "duration_spread", "dv01", "seuil_pb"]


# =====================================================================
# EXCEL
# =====================================================================
def exporter_excel(resultats, courbe, chemin="data/rapport_resultats.xlsx"):
    """Un onglet par analyse, colonnes ajustées, en-têtes figés."""
    secteurs = resume_secteurs(resultats)
    scenarios = tous_les_scenarios(resultats, courbe)
    chocs = [c for c in resultats.columns if c.startswith("choc_")]
    krd = [c for c in resultats.columns if c.startswith("KRD")]

    feuilles = {
        "Lisez-moi": pd.DataFrame({"Hypothèses du modèle": HYPOTHESES}),
        "Courbe BAM": courbe.assign(**{"taux (%)": courbe["taux"] * 100})[["echeance", "maturite", "taux (%)"]]
                      if "echeance" in courbe.columns else courbe,
        "Tranches": resultats[[c for c in COLONNES_TRANCHES if c in resultats.columns]],
        "Par secteur": secteurs.reset_index(),
        "Stress parallèle": resultats[["emetteur", "tranche", "secteur", "nature_taux"] + chocs],
        "Scénarios de courbe": scenarios,
        "Scénarios par secteur": scenarios.groupby("secteur")[list(SCENARIOS)].mean().round(3).reset_index(),
        "Définition scénarios": pd.DataFrame(SCENARIOS, index=[f"{p:g} an(s)" for p in POINTS_COURBE])
                                  .T.rename_axis("scénario (chocs en pb)").reset_index(),
        "Key rate durations": resultats.groupby("secteur")[krd].mean().round(3).reset_index(),
    }

    with pd.ExcelWriter(chemin, engine="openpyxl") as writer:
        for nom, df in feuilles.items():
            df.to_excel(writer, sheet_name=nom, index=False)
            ws = writer.sheets[nom]
            ws.freeze_panes = "A2"
            for col in ws.columns:
                largeur = max(len(str(c.value)) if c.value is not None else 0 for c in col)
                ws.column_dimensions[col[0].column_letter].width = min(max(10, largeur + 2), 60 if nom == "Lisez-moi" else 40)
            for cellule in ws[1]:
                cellule.font = cellule.font.copy(bold=True)
    return chemin


# =====================================================================
# HTML
# =====================================================================
def _graphique_rendement_duration(resultats):
    cols = ["emetteur", "tranche", "secteur", "nature_taux", "maturite_res", "ytm_%", "modifiee"]
    return alt.Chart(resultats[cols]).mark_point(size=80, opacity=0.8, filled=True).encode(
        x=alt.X("modifiee:Q", title="Duration de taux (effective)"),
        y=alt.Y("ytm_%:Q", title="Rendement (%)", scale=alt.Scale(zero=False)),
        color=alt.Color("secteur:N", title="Secteur"),
        shape=alt.Shape("nature_taux:N", title="Taux"),
        tooltip=["emetteur", "tranche", "secteur", "nature_taux", "maturite_res", "ytm_%", "modifiee"],
    ).properties(width=720, height=380, title="Rendement vs risque de taux (une tranche = un point)")


def _graphique_courbe(courbe):
    donnees = pd.DataFrame({"maturite": courbe["maturite"], "taux_pct": courbe["taux"] * 100})
    return alt.Chart(donnees).mark_line(point=True).encode(
        x=alt.X("maturite:Q", title="Maturité (années)"),
        y=alt.Y("taux_pct:Q", title="Taux (%)", scale=alt.Scale(zero=False)),
    ).properties(width=720, height=260, title="Courbe des taux de référence BDT (Bank Al-Maghrib)")


def _graphique_scenarios(scenarios):
    moyennes = (scenarios.groupby("secteur")[list(SCENARIOS)].mean()
                .reset_index().melt(id_vars="secteur", var_name="scénario", value_name="variation_%"))
    return alt.Chart(moyennes).mark_bar().encode(
        x=alt.X("variation_%:Q", title="Variation moyenne du prix (%)"),
        y=alt.Y("secteur:N", title=None),
        color=alt.condition(alt.datum["variation_%"] < 0, alt.value("#c0392b"), alt.value("#2e86c1")),
        row=alt.Row("scénario:N", title=None, header=alt.Header(labelAngle=0, labelAlign="left")),
        tooltip=["scénario", "secteur", alt.Tooltip("variation_%:Q", format=".2f")],
    ).properties(width=520, height=110, title="Impact moyen des scénarios de courbe, par secteur")


def _graphique_krd(resultats):
    krd = [c for c in resultats.columns if c.startswith("KRD")]
    donnees = (resultats.groupby("secteur")[krd].mean().reset_index()
               .melt(id_vars="secteur", var_name="point", value_name="KRD"))
    base = alt.Chart(donnees).encode(x=alt.X("point:N", sort=krd, title="Point de la courbe"),
                                     y=alt.Y("secteur:N", title=None))
    return (base.mark_rect().encode(color=alt.Color("KRD:Q", scale=alt.Scale(scheme="blues")))
            + base.mark_text().encode(text=alt.Text("KRD:Q", format=".2f"))
            ).properties(width=520, height=220, title="Key rate durations moyennes par secteur")


def _scripts_vega(specs):
    """Charge la version de Vega-Lite qui correspond à celle d'Altair (v5 ou v6)."""
    schema = next(iter(specs.values()))["$schema"]          # ex. .../vega-lite/v6.4.1.json
    version_vl = schema.rsplit("/v", 1)[1].replace(".json", "")
    if version_vl.startswith("6"):
        vega, embed = "6.2.0", "7.0.2"
    else:
        vega, embed = "5.30.0", "6.26.0"
    return "\n".join(f'<script src="https://cdn.jsdelivr.net/npm/{lib}@{v}"></script>'
                     for lib, v in [("vega", vega), ("vega-lite", version_vl), ("vega-embed", embed)])


def exporter_html(resultats, courbe, chemin="data/rapport.html", titre="Risque de taux des obligations privées marocaines"):
    """Rapport autonome : chiffres clés, graphiques interactifs, tableaux, hypothèses."""
    scenarios = tous_les_scenarios(resultats, courbe)
    secteurs = resume_secteurs(resultats)
    date_courbe = (pd.to_datetime(courbe["date_valeur"]).iloc[0].date()
                   if "date_valeur" in courbe.columns else "")
    graphiques = {
        "courbe": _graphique_courbe(courbe),
        "nuage": _graphique_rendement_duration(resultats),
        "scenarios": _graphique_scenarios(scenarios),
        "krd": _graphique_krd(resultats),
    }
    specs = {k: json.loads(g.to_json()) for k, g in graphiques.items()}

    pire = scenarios[list(SCENARIOS)].mean().idxmin()
    chiffres = [
        ("Tranches vivantes", f"{len(resultats)}"),
        ("Part à taux révisable", f"{(resultats['nature_taux'] == 'révisable').mean() * 100:.0f} %"),
        ("Duration de taux moyenne", f"{resultats['modifiee'].mean():.2f}"),
        ("Duration de spread moyenne", f"{resultats['duration_spread'].mean():.2f}"),
        ("Scénario le plus pénalisant", pire),
    ]
    tableau_plus_exposees = (resultats.nlargest(10, "modifiee")
                             [["emetteur", "tranche", "secteur", "nature_taux", "maturite_res",
                               "ytm_%", "modifiee", "choc_+100pb_%"]].to_html(index=False, float_format="%.2f"))

    html = f"""<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{titre}</title>
{_scripts_vega(specs)}
<style>
 body {{ font-family: Segoe UI, Helvetica, Arial, sans-serif; margin: 0 auto; max-width: 1000px; padding: 24px 16px; color: #1d2733; }}
 h1 {{ font-size: 26px; margin-bottom: 4px; }} h2 {{ margin-top: 36px; border-bottom: 2px solid #e3e8ee; padding-bottom: 6px; }}
 .sous-titre {{ color: #5b6b7c; margin-top: 0; }}
 .chiffres {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 12px; margin: 20px 0; }}
 .carte {{ background: #f4f7fa; border-radius: 8px; padding: 12px 14px; }}
 .carte .v {{ font-size: 20px; font-weight: 600; }} .carte .l {{ color: #5b6b7c; font-size: 13px; }}
 table {{ border-collapse: collapse; width: 100%; font-size: 13px; overflow-x: auto; display: block; }}
 th, td {{ padding: 6px 8px; border-bottom: 1px solid #e3e8ee; text-align: right; }} th {{ background: #f4f7fa; }}
 td:first-child, th:first-child {{ text-align: left; }}
 .graphique {{ overflow-x: auto; }} li {{ margin-bottom: 4px; }}
</style></head><body>
<h1>{titre}</h1>
<p class="sous-titre">Emprunts obligataires visés par l'AMMC, valorisés sur la courbe Bank Al-Maghrib du {date_courbe}.</p>
<div class="chiffres">{''.join(f'<div class="carte"><div class="v">{v}</div><div class="l">{l}</div></div>' for l, v in chiffres)}</div>

<h2>Courbe des taux</h2><div class="graphique" id="courbe"></div>
<h2>Rendement vs risque de taux</h2><div class="graphique" id="nuage"></div>
<h2>Synthèse par secteur</h2>{secteurs.to_html(float_format="%.2f")}
<h2>Les 10 tranches les plus exposées aux taux</h2>{tableau_plus_exposees}
<h2>Scénarios de déformation de la courbe</h2><div class="graphique" id="scenarios"></div>
<h2>Exposition par point de la courbe</h2><div class="graphique" id="krd"></div>
<h2>Hypothèses</h2><ul>{''.join(f'<li>{h}</li>' for h in HYPOTHESES)}</ul>
<script>
const specs = {json.dumps(specs)};
for (const [id, spec] of Object.entries(specs)) {{ vegaEmbed('#' + id, spec, {{actions: false}}); }}
</script>
</body></html>"""
    with open(chemin, "w", encoding="utf-8") as f:
        f.write(html)
    return chemin
