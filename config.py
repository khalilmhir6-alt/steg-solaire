"""
Central configuration for the STEG Solaire forecasting & grid-risk platform.

Carries:
  - Physical parameters (Tunis, panel geometry, derate).
  - The STEG distribution hierarchy (7 regions -> ~50 districts) and
    installed capacities sourced from the STEG IPV statistical bulletin.
  - Capacity scenarios (real data, spec, ambitious).
  - Alert thresholds (spec: Yellow 10% / Red 20% drop in 60 min).
"""

import os

# ---------------------------------------------------------------------------
# Location & solar geometry
# ---------------------------------------------------------------------------
LATITUDE = 36.8065
LONGITUDE = 10.1815
TIMEZONE = "Africa/Tunis"

TILT_ANGLE = 30          # STEG/ANME recommended for Tunis
AZIMUTH = 180            # south-facing
DERATE_FACTOR = 0.85     # inverter + DC/AC + urban soiling/dust losses
ALBEDO = 0.2             # albedo
SURFACE_TYPE = "urban"   # albedo / loss profile flavour


FORECAST_DAYS = 7        # "Week" horizon default
FORECAST_DAYS_MAX = 16   # Open-Meteo hard cap (kept available in config)

# Forecast time grid: the whole pipeline runs on a 15-minute step.
STEP_MINUTES = 15
HORIZON_MIN_HOURS = STEP_MINUTES / 60.0   # 0.25 h = 15 min
HORIZON_MAX_HOURS = FORECAST_DAYS * 24.0  # 168 h = 1 week

# ---------------------------------------------------------------------------
# Capacity scenarios (MW installed)
# ---------------------------------------------------------------------------
CAPACITY_SCENARIOS = {
    # Key: display label -> {region -> MW}
    "Reel (bulletin STEG mars-26)": {
        "tunis": 95.7, "nord": 53.4, "nord_ouest": 20.5,
        "centre": 101.5, "sfax": 99.1, "sud_ouest": 14.4, "sud": 71.3,
    },
    "Spec MVP (30 MW)": {"tunis": 30.0},
    "Scenario 500 MW (futur/ambitieux)": {
        "tunis": 125.0, "nord": 75.0, "nord_ouest": 30.0,
        "centre": 120.0, "sfax": 105.0, "sud_ouest": 20.0, "sud": 85.0,
    },
}
DEFAULT_SCENARIO = "Reel (bulletin STEG mars-26)"

# ---------------------------------------------------------------------------
# Fleet profile: real STEG distribution of system size tiers (bulletin 5.1)
# size_kwc -> number of installations (national, since 2011)
# ---------------------------------------------------------------------------
FLEET_SIZE_DISTRIBUTION_KWC = {
    1: 8322, 2: 54213, 3: 49054, 4: 15599,
    5: 6528, 6: 3791, 7: 1211, 8: 1193,
    9: 566, 10: 1249, 11: 334, 12: 2919,
}

# ---------------------------------------------------------------------------
# Hierarchy: STEG distribution regions -> districts (bulletin 3.3)
# District keys are the scope slugs used in URLs and routing.
# ---------------------------------------------------------------------------
REGION_LABELS = {
    "tunis": "TUNIS", "nord": "NORD", "nord_ouest": "NORD OUEST",
    "centre": "CENTRE", "sfax": "SFAX", "sud_ouest": "SUD OUEST", "sud": "SUD",
}

# district slug -> (region, display label, installs since 2011)
DISTRICTS = {
    # --- TUNIS ---
    "tunis_ville": ("tunis", "TUNIS VILLE", 1923),
    "ariana": ("tunis", "ARIANA", 5688),
    "ezzahra": ("tunis", "EZZAHRA", 4509),
    "mourouj": ("tunis", "MOUROUJ", 2287),
    "kram": ("tunis", "KRAM", 4820),
    "bardo": ("tunis", "BARDO", 2667),
    "mannouba": ("tunis", "MANNOUBA", 2559),
    "el_menzah": ("tunis", "EL MENZAH", 4085),
    # --- NORD ---
    "zaghouan": ("nord", "ZAGHOUAN", 974),
    "bizerte": ("nord", "BIZERTE", 3402),
    "menzel_bourguiba": ("nord", "MENZEL BOURGUIBA", 709),
    "nabeul": ("nord", "NABEUL", 4344),
    "menzel_bzelfa": ("nord", "MENZEL B-ZELFA", 2688),
    "menzel_temime": ("nord", "MENZEL TEMIME", 2878),
    "hammamet": ("nord", "HAMMAMET", 2299),
    # --- NORD OUEST ---
    "beja": ("nord_ouest", "BEJA", 4185),
    "jendouba": ("nord_ouest", "JENDOUBA", 918),
    "kef": ("nord_ouest", "KEF", 1361),
    "siliana": ("nord_ouest", "SILIANA", 546),
    "tabarka": ("nord_ouest", "TABARKA", 354),
    # --- CENTRE ---
    "sousse": ("centre", "SOUSSE", 4633),
    "sousse_nord": ("centre", "SOUSSE NORD", 4942),
    "monastir": ("centre", "MONASTIR", 5087),
    "moknine": ("centre", "MOKNINE", 7242),
    "mahdia": ("centre", "MAHDIA", 4293),
    "kairouan": ("centre", "KAIROUAN", 1780),
    "kairouan_nord": ("centre", "KAIROUAN NORD", 1028),
    "el_jem": ("centre", "EL JEM", 1672),
    "msaken": ("centre", "MSAKEN", 2421),
    "enfidha": ("centre", "ENFIDHA", 587),
    "kasserine": ("sud_ouest", "KASSERINE", 320),
    "sidi_bouzid": ("sud_ouest", "SIDI-BOUZID", 833),
    "sbeitla": ("sud_ouest", "SBEITLA", 120),
    # --- SFAX ---
    "sfax_ville": ("sfax", "SFAX VILLE", 6301),
    "jbeniana": ("sfax", "JBENIANA", 2212),
    "sfax_nord": ("sfax", "SFAX NORD", 10112),
    "mahres": ("sfax", "MAHRES", 3121),
    "sfax_sud": ("sfax", "SFAX SUD", 9189),
    # --- SUD OUEST ---
    "gafsa": ("sud_ouest", "GAFSA", 1162),
    "metlaoui": ("sud_ouest", "METLAOUI", 244),
    "tozeur": ("sud_ouest", "TOZEUR", 1796),
    "maknassy": ("sud_ouest", "MAKNASSY", 181),
    # --- SUD ---
    "gabes": ("sud", "GABES", 2253),
    "kebili": ("sud", "KEBILI", 3255),
    "zarzis": ("sud", "ZARZIS", 2182),
    "mednine": ("sud", "MEDNINE", 2552),
    "jerba": ("sud", "JERBA", 7488),
    "tataouine": ("sud", "TATAOUINE", 2155),
    "ben_guerdene": ("sud", "BEN GUERDENE", 914),
    "gabes_nord": ("sud", "GABES NORD", 1708),
}

# ---------------------------------------------------------------------------
# Alert thresholds (from spec)
# ---------------------------------------------------------------------------
RAMP_YELLOW_THRESHOLD = 0.10   # 10% predicted drop within 60 min
RAMP_RED_THRESHOLD = 0.20      # 20% predicted drop within 60 min
RAMP_WINDOW_MINUTES = 60
CONFIDENCE_LEVEL = 0.90        # prediction interval coverage

# ---------------------------------------------------------------------------
# Production-vs-forecast alert thresholds (STEP-1 solid core, no UI page yet)
# Fractions of the scope's INSTALLED capacity -> yellow / red. Persistence:
# a state only flips after ALERT_PERSISTENCE_STEPS consecutive steps beyond
# the threshold (and the same count below to come back to green).
# ---------------------------------------------------------------------------
ALERT_THRESHOLDS = {
    "national": (0.05, 0.10),   # tunisia (5% / 10% of installed capacity)
    "region":   (0.08, 0.15),   # the 7 regions
    "district": (0.10, 0.20),   # leaf districts
}
ALERT_PERSISTENCE_STEPS = 2     # consecutive steps to flip / to return green
ALERT_RECENT_STEPS = 12         # last N steps read from ACTUAL_LOG
DEMO_DEVIATION = None           # None=off; fraction (0.15 / 0.30) simulated
                                # UNDER-production for one daytime hour, applied
                                # in memory ONLY (never written to the JSONL).

# STEG dispatch nodes (approximate geography; used for operator prompts)
REGION_BACKUP_NODES = {
    "tunis": ["Rades", "La Goulette", "Radès / La Goulette"],
    "nord": ["Menzel Bourguiba", "Rades", "Goulette"],
    "nord_ouest": ["Hammam Lif", "Rades", "Goulette"],
    "centre": ["Sousse", "Moknine", "Mahdia"],
    "sfax": ["Sfax", "Gabès", "Rades"],
    "sud_ouest": ["Tozeur", "Gafsa", "El Jem"],
    "sud": ["Gabès", "Zarzis", "Jerba"],
}
DEFAULT_BACKUP_NODE = ["Rades"]

# ---------------------------------------------------------------------------
# Data / model paths
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
MODEL_DIR = os.path.join(BASE_DIR, "models")
DB_PATH = os.path.join(DATA_DIR, "users.db")
LIGHTGBM_MODEL_PATH = os.path.join(MODEL_DIR, "lgbm_correction.pkl")
MODEL_RETRAIN_HOURS = 24  # refresh the corrector when its checkpoint is older than this
WEATHER_LIVE_PATH = os.path.join(DATA_DIR, "weather_live.json")
WEATHER_MOCK_PATH = os.path.join(DATA_DIR, "weather_mock.json")
RESULT_PATH = os.path.join(DATA_DIR, "forecast_result.json")
ACTUAL_LOG_PATH = os.path.join(DATA_DIR, "forecast_actual.jsonl")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(MODEL_DIR, exist_ok=True)

# Open-Meteo
OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
WEATHER_VARIABLES = [
    "shortwave_radiation",      # GHI (preceding hour mean)
    "direct_normal_irradiance", # DNI
    "diffuse_radiation",        # DHI
    "cloud_cover",
    "temperature_2m",
    "relative_humidity_2m",
    "wind_speed_10m",
]

# ---------------------------------------------------------------------------
# Demand (Greater-Tunis style baseline; scaled per scope). Values in MW.
# ---------------------------------------------------------------------------
DEMAND_BASELINE_MW = {
    0: 180, 1: 170, 2: 165, 3: 160, 4: 160, 5: 165,
    6: 180, 7: 210, 8: 240, 9: 265, 10: 285, 11: 300,
    12: 310, 13: 315, 14: 310, 15: 305, 16: 295, 17: 280,
    18: 260, 19: 240, 20: 225, 21: 210, 22: 195, 23: 185,
}
# Demand scaling per scope: derived from the REAL install counts of the
# bulletin (DISTRICTS), not an arbitrary table. The national level anchors
# demand to the real national consumption, then each region / district is
# weighted by its share of installations (a defensible activity proxy).
NATIONAL_DEMAND_GWH = 19400.0   # STEG consumption 2023=19148 / 2024=19888 GWh
NATIONAL_SOLAR_GWH = 820.0      # ~4% of national demand, full year (see ref)

# Seasonal demand modulation (month -> factor): AC/heat peak in summer,
# mild shoulder, reduced load in winter. Values are ~1.0 on average.
DEMAND_SEASON_FACTOR = {
    1: 0.82, 2: 0.84, 3: 0.92, 4: 0.98, 5: 1.04, 6: 1.10,
    7: 1.16, 8: 1.16, 9: 1.08, 10: 0.98, 11: 0.90, 12: 0.84,
}

# Demand reactivity (Tunisia): AC/refrigeration load makes summer consumption
# climb sharply. These factors modulate the baseline on top of hour + region.
DEMAND_TEMP_REF_C = 24.0      # above this reference, cooling load kicks in
DEMAND_TEMP_COEF = 0.025      # +2.5% demand per °C above reference
DEMAND_WEEKEND_FACTOR = 0.85  # weekend (Sat/Sun) demand vs a working day

# Solar share is now computed LIVE per forecast window in core/engine.py
# (solar_share_pct = future-window solar energy / future-window perimeter demand).
# Reference for that live %: ~4% national for a full year (bulletin Q1-2026
# 175.2 GWh scaled by sun-geometry ~ 820 GWh / ~19 400 GWh national).

# ---------------------------------------------------------------------------
# FYI: real-scale reference (bulletin) — for documentation/display purposes
# ---------------------------------------------------------------------------
BULLETIN_REFERENCE = {
    "installations_tunisia": 144979,
    "mw_tunisia": 456.0,
    "installations_tunis_region": 28538,
    "mw_tunis_region": 95.7,
    "production_gwh_since_2011": 2358.3,
    "injected_gwh_since_2011": 1511.1,
    "injection_ratio": 0.64,
}