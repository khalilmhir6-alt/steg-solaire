# STEG Solaire — Plateforme de Prévision PV & Pilotage de l'Injection

Application Streamlit multi-page pour la prévision solaire et le pilotage de l'injection photovoltaïque du réseau STEG (Tunisie).

## Architecture

```
app.py                  # Point d'entrée, auth, navigation, topbar
config.py               # Paramètres physiques, hiérarchie STEG, seuils d'alerte
core/
  weather.py            # Météo Open-Meteo (live) / mock synthétique offline
  twin.py               # Jumeau numérique PV (pvlib) → W/kWp → MW injectés
  ML.py                 # Correcteur LightGBM (entraînement + prédiction)
  engine.py             # Pipeline complet : météo → twin → ML → forecast
  alerts.py             # Détection de ramp alerts (jaune/rouge)
pages/
  dashboard.py          # Dashboard principal (production, consommation, comparaison)
  prevision_reel.py     # Prévision vs Réel (forecast + mesures simulées)
  alertes.py            # Liste des alertes de rampe
  admin.py              # Gestion des comptes (steg/admin/technicien)
  panneaux.py           # Ajout de panneaux solaires
ui/
  auth.py               # Authentification, rôles, politique d'accès
  theme.py              # CSS partagé, helpers, rendu du filtre Region/Horizon
  hierarchy.py          # Hiérarchie STEG (7 régions → ~50 districts)
  registry.py           # Registre des panneaux (scope roll-up district → région)
  layers.py             # Utilitaires d'affichage
```

## Pipeline de prévision

```
Open-Meteo (ou mock) → twin.per_kwp() → ML.build_features()
  → ML.train_corrector() → ML.predict() → scale(installed × 0.64)
  → engine.build_forecast() → forecast_result.json
```

- **Météo** : 7 variables (GHI, DNI, DHI, nuages, température, humidité, vent) sur grille 15 min.
- **Jumeau** : calcul géométrique pvlib (tilt 30°, sud, derate 0.85) → production physique par kWp.
- **ML** : correcteur LightGBM entraîné sur les écarts jumeau vs physique, avec intervalles de confiance.
- **Nuit** : production forcée à 0 quand `ghi_clear ≤ 0` (position solaire pvlib).

## Rôles et accès

| Rôle | Portée | Droits |
|------|--------|--------|
| `steg` | Nationale (`tunisia`) | Accès complet, crée/supprime les admins régionaux et techniciens |
| `admin_<region>` | Région (ex: `centre`) | Crée/supprime techniciens de sa région, voit ses districts |
| `technicien_<district>` | District (ex: `centre/monastir`) | Ajoute des panneaux, scope verrouillé |

Règle de l'homme aveugle : chaque niveau ne voit que ce qui est sous lui.

## Installation

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Données

- **Sources** : Open-Meteo API (live, 60 jours archive + 7 jours forecast) ou mock synthétique offline.
- **Hiérarchie** : 7 régions, ~50 districts, 144 979 installations, 456 MW installés (Bulletin STEG mars 2026).
- **Scénarios** : Réel (bulletin), Spec MVP (30 MW), Scénario 500 MW (ambitieux).

## Comptes de démo

Tous les mots de passe : `solaire2026`

| Utilisateur | Rôle | Portée |
|------------|------|--------|
| `steg` | National | Tunisia |
| `admin_tunis` | Admin région | Tunis |
| `admin_centre` | Admin région | Centre |
| `admin_nord` | Admin région | Nord |
| `admin_nord_ouest` | Admin région | Nord Ouest |
| `admin_sfax` | Admin région | Sfax |
| `admin_sud_ouest` | Admin région | Sud Ouest |
| `admin_sud` | Admin région | Sud |
| `technicien_ariana` | Technicien | Tunis / Ariana |
| ... | ... | ... |

58 comptes au total (1 steg + 7 admins + 50 techniciens).
