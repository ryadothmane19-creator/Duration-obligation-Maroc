# Risque de taux et de spread des obligations privées marocaines
**Application en ligne : [duration-maroc.streamlit.app](https://duration-maroc.streamlit.app/)**

Outil Python qui collecte automatiquement les **emprunts obligataires d'entreprises visés par l'AMMC**, les valorise sur la **courbe des taux de Bank Al-Maghrib**, et mesure leur risque : duration, convexité, key rate durations, duration de spread, stress tests de déformation de courbe.

- **Taux sans risque** : courbe des taux de référence des Bons du Trésor, Bank Al-Maghrib (scraping)
- **Émissions** : liste AMMC des emprunts obligataires, pages de détail, et lecture automatique des notes d'opération PDF (tranches, échéance, prime de risque, taux fixe ou révisable, mode de remboursement)

## Ce que fait l'outil

| Analyse | Détail |
|---|---|
| Valorisation | Flux datés (Exact/365), chaque flux actualisé à courbe BAM(t) + prime ; prix plein, coupon couru, prix pied de coupon |
| Risque de taux | Duration de Macaulay, duration et convexité effectives, DV01, seuil de résistance |
| Exposition par maturité | Key rate durations (3 mois, 1, 2, 5, 10, 15, 30 ans) |
| Risque de crédit | Duration de spread, choc de prime par secteur (révisables comprises) |
| Stress tests | Chocs parallèles et 7 scénarios de déformation de courbe inspirés des scénarios IRRBB de Bâle (pentification, aplatissement, chocs courts…) |
| Calculateur | Saisie libre d'une obligation ou de flux ; courbe prix-rendement ; sensibilité de la duration à la maturité, au coupon et au taux |

## Résultats

*(à compléter avec les chiffres de `02_analyse.ipynb`)*

- **Structure du marché** : environ trois quarts des tranches encore vivantes sont à **taux révisable** ; les banques représentent plus de la moitié des tranches, surtout en dette subordonnée.
- **Risque de taux faible en moyenne** : duration de taux moyenne inférieure à 2. Le risque se concentre sur les **tranches fixes longues**, principalement des établissements publics et des subordonnées bancaires.
- **La prime de risque suit la qualité de l'émetteur** : environ 70 pb pour les banques contre environ 250 pb pour l'immobilier. Le risque de l'émetteur pèse plus lourd que le rang de la dette (les subordonnées bancaires paient moins que les obligations ordinaires d'émetteurs industriels ou immobiliers).
- **Déformations de courbe** : dans un aplatissement, ce sont les tranches fixes de **moyen terme** qui souffrent le plus, alors que les fixes longues peuvent gagner ; un choc parallèle ne montre pas ce résultat.
- **Révisable ne veut pas dire sans risque** : duration de taux inférieure à 1 an, mais duration de spread comparable à celle d'une tranche fixe de même maturité.

## Structure

```
01_collecte.ipynb    Collecte : courbe BAM, liste AMMC, lecture des PDF  (à lancer rarement)
02_analyse.ipynb     Analyse, scénarios, exports                          (à lancer souvent)
app.py               Application Streamlit : synthèse, marché, scénarios, calculateur
design.py            Identité visuelle (terminal de marché sombre) : couleurs, polices, thème des graphiques, composants
.streamlit/          Thème de l'application (config.toml)

courbe.py            Courbe BDT de Bank Al-Maghrib + interpolation
ammc.py              Liste des emprunts obligataires AMMC + choix de la note d'opération
extraction.py        Lecture des PDF : tranches, échéance, prime, nature du taux, remboursement
calculs.py           Flux, prix, durations, convexité, courbe, KRD, scénarios, spread
pipeline.py          Tranches -> obligations vivantes -> analyse -> scénarios
rapport.py           Exports Excel (un onglet par analyse) et rapport HTML

data/                Caches (CSV, PDF) et exports — non versionnés
```

## Installation et utilisation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

jupyter lab                                   # 01_collecte.ipynb puis 02_analyse.ipynb
streamlit run app.py --server.headless true   # puis http://localhost:8501
```

`02_analyse.ipynb` produit :
- `data/resultats.csv` : une ligne par tranche, lu par l'application
- `data/rapport_resultats.xlsx` : un onglet par analyse
- `data/rapport.html` : rapport autonome avec graphiques interactifs

## Hypothèses et limites

- Prime de risque = milieu de la fourchette annoncée à l'émission (pas la prime définitive ni la prime de marché actuelle).
- Tranche fixe : coupon ≈ taux BDT à la maturité résiduelle + prime (le taux facial réel n'est pas extrait).
- Tranche révisable : coupon = BDT 1 an + prime, exposée aux taux jusqu'à sa prochaine révision (anniversaire de l'échéance).
- Coupons annuels aux dates anniversaires de l'échéance ; premier coupon « long » non modélisé.
- La courbe BAM est une courbe de taux actuariels : utilisée telle quelle, sans bootstrapping en taux zéro-coupon.
- Échéance absente du PDF : date de visa AMMC + maturité.
- Moyennes simples par tranche, non pondérées par les montants émis.
- Exclus : obligations perpétuelles, remboursables en actions, PDF scannés (anciennes émissions).
- Scénarios de courbe : amplitudes illustratives, inspirées des scénarios IRRBB de Bâle.

## Pistes d'évolution

- Extraire le taux facial réel des tranches fixes et les primes définitives (communiqués de résultats)
- Bootstrapping de la courbe BAM en taux zéro-coupon
- Obligations perpétuelles (duration = (1 + y) / y)
- Portefeuille : sélection de tranches, duration et perte agrégées par scénario
- Pondération par les montants émis
