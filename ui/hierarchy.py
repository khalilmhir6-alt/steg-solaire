"""
STEG distribution hierarchy: Tunisia > 7 regions > districts.

Resolves a user scope into:
  - Display label + breadcrumb path
  - Aggregated installed capacity (from the STEG bulletin, proportional per district)
  - Covered district list (for drill-down navigation)
"""

from config import (
    REGION_LABELS,
    DISTRICTS,
    CAPACITY_SCENARIOS,
    DEFAULT_SCENARIO,
    DEMAND_BASELINE_MW,
    NATIONAL_DEMAND_GWH,
    NATIONAL_SOLAR_GWH,
    BULLETIN_REFERENCE,
)

NATIONAL_SLUG = "tunisia"


def list_regions():
    return [r for r in REGION_LABELS]


def districts_of_region(region):
    return sorted(
        (slug for slug, (reg, _, _) in DISTRICTS.items() if reg == region),
        key=lambda s: DISTRICTS[s][1],
    )


def _region_installs(region):
    return sum(n for reg, _, n in DISTRICTS.values() if reg == region)


def region_capacity_mw(region, scenario=None):
    """Installed MW for a region under the chosen capacity scenario."""
    scenario = scenario or DEFAULT_SCENARIO
    cap = CAPACITY_SCENARIOS[scenario]
    if region in cap:
        return float(cap[region])
    # scenario missing region -> scale from the real bulletin share
    totals = CAPACITY_SCENARIOS[DEFAULT_SCENARIO]
    real_total = sum(totals.values())
    share = totals.get(region, 0.0) / real_total
    return round(share * sum(cap.values()), 2)


def district_capacity_mw(district, scenario=None):
    """District capacity estimated proportionally to install count within region."""
    region, label, installs = DISTRICTS[district]
    reg_installs = _region_installs(region)
    if reg_installs <= 0:
        return 0.0
    return round(region_capacity_mw(region, scenario) * installs / reg_installs, 3)


def scope_capacity_mw(scope, scenario=None):
    """Total installed MW covered by a scope string (e.g. 'nord/nabeul')."""
    parts = _parse_scope(scope)
    if parts == [NATIONAL_SLUG]:
        c = CAPACITY_SCENARIOS[scenario or DEFAULT_SCENARIO]
        return round(sum(c.values()), 1)
    region = parts[0]
    if len(parts) == 1:
        return region_capacity_mw(region, scenario)
    return district_capacity_mw(parts[1], scenario)


# Total PV installations across the whole country (sum over the bulletin's
# regional/district counts). Used as the denominator for every scope's share.
def _installs_total():
    return sum(n for _, _, n in DISTRICTS.values())


def _installs_scope(scope):
    """Installations covered by a scope string (national / region / district)."""
    parts = _parse_scope(scope)
    if parts == [NATIONAL_SLUG]:
        return _installs_total()
    if len(parts) == 1:
        return _region_installs(parts[0])
    _, _, n = DISTRICTS[parts[1]]
    return n


# Reference scale so the national hourly profile integrates to the real
# national annual consumption (~19 400 GWh). The baseline's daily sum, over a
# full year, must reach NATIONAL_DEMAND_GWH before weather/season variation.
_annual_baseline_gwh = sum(DEMAND_BASELINE_MW.values()) * 365 / 1000.0
_NATIONAL_K = float(NATIONAL_DEMAND_GWH / _annual_baseline_gwh) if _annual_baseline_gwh else 1.0


def scope_demand_profile(scope, scenario=None):
    """Hourly demand profile (MW) for the scope.

    Anchored to the real national consumption (~19 400 GWh/an) and split across
    regions / districts by their actual share of PV installations (bulletin), so
    every level is consistent with the national truth. The engine then varies it
    with season, temperature and weekend effects.
    """
    parts = _parse_scope(scope)
    share = _installs_scope(scope) / _installs_total() if _installs_total() else 1.0
    scale = _NATIONAL_K * share
    return {h: round(v * scale, 2) for h, v in DEMAND_BASELINE_MW.items()}


def scope_day_reference(win):
    """Single source of truth for the 4 % solar-cible comparison used by every
    dashboard panel.

    Returns ``(dm, target_mw, day_mask)``:
      - ``dm``        : future-window hourly demand (MW)
      - ``target_mw`` : 4 % of that demand — the annual anchor, night included
                        (~820 GWh ≈ 4 % de ~19 400 GWh)
      - ``day_mask``  : day-only rule (night -> 0) so every panel judges the red
                        and the green on the same daylight scale. Identical
                        logic everywhere; one fallback, one pvlib call.
    """
    dm = win["demand_mw"]
    target_mw = dm * 0.04
    try:
        import pvlib
        from config import LATITUDE, LONGITUDE
        sp = pvlib.solarposition.get_solarposition(
            win.index.tz_convert("UTC"), LATITUDE, LONGITUDE)
        day_mask = (sp["apparent_elevation"] > 0).to_numpy()
    except Exception:
        day_mask = (dm.to_numpy() > 100.0) | (target_mw.to_numpy() > 0.0)
    return dm, target_mw, day_mask


def _parse_scope(scope):
    """Normalise a scope string into parts, e.g. 'nord/nabeul' -> ['nord', 'nabeul']."""
    if not scope:
        return [NATIONAL_SLUG]
    parts = [p.strip().lower() for p in str(scope).replace("\\", "/").split("/") if p.strip()]
    if parts[0] not in (NATIONAL_SLUG,) and parts[0] not in REGION_LABELS:
        parts = [NATIONAL_SLUG] + parts
    return parts


def scope_label(scope):
    parts = _parse_scope(scope)
    if parts == [NATIONAL_SLUG]:
        return "Tunisia (nationale)"
    region = REGION_LABELS.get(parts[0], parts[0].upper())
    if len(parts) == 1:
        return region
    district = DISTRICTS.get(parts[1], parts[1])
    return f"{district[1] if isinstance(district, tuple) else district}"

    return district


def breadcrumb(scope):
    """Return [(label, scope)] clickable trail from Tunisia down to the scope."""
    parts = _parse_scope(scope)
    trail = [("Tunisia", NATIONAL_SLUG)]
    if parts == [NATIONAL_SLUG]:
        return trail
    trail.append((REGION_LABELS[parts[0]], parts[0]))
    if len(parts) >= 2:
        label = DISTRICTS.get(parts[1], parts[1])
        label = label[1] if isinstance(label, tuple) else label
        trail.append((label, "/".join(parts[:2])))
    return trail


def child_scopes(scope):
    """Direct drill-down children of a scope."""
    parts = _parse_scope(scope)
    if parts == [NATIONAL_SLUG]:
        return [("Regions", r) for r in list_regions()]
    if len(parts) == 1:
        return [("Districts", f"{parts[0]}/{d}") for d in districts_of_region(parts[0])]
    return []  # district is the deepest available level today


def is_valid_scope(scope):
    parts = _parse_scope(scope)
    if parts == [NATIONAL_SLUG]:
        return True
    if parts[0] not in REGION_LABELS:
        return False
    if len(parts) == 1:
        return True
    return parts[1] in DISTRICTS and DISTRICTS[parts[1]][0] == parts[0]


def scope_capacity_label(capacity_mw):
    return f"{capacity_mw:,.1f} MW installés"


def annual_energy_balance_gwh(scope, scenario=None):
    """Annual 2026 energy balance (GWh) for the scope, install-driven.

    Uses the two real national anchors from the bulletin / calendar year:
      - NATIONAL_SOLAR_GWH (~820 GWh, the average energy the installed fleet
        produces each year — we already discussed this number)
      - NATIONAL_DEMAND_GWH (~19 400 GWh, real STEG consumption)
    and splits BOTH by the scope's actual share of PV installations, the only
    per-region truth the bulletin carries. So the full-year balance at every
    level (national → region → district) is consistent with the national truth.

    NOTE: this is an ESTIMATE (saison estivale + synthèse), not a forecast —
    the live engine only reaches FORECAST_DAYS_MAX; real Oct-Dec 2026 weather is
    not fetchable. Values are labelled "estimé" in the UI.
    """
    installs_scope = _installs_scope(scope)
    installs_total = _installs_total()
    share = (installs_scope / installs_total) if installs_total else 1.0

    solar_gwh = float(NATIONAL_SOLAR_GWH) * share
    demand_gwh = float(NATIONAL_DEMAND_GWH) * share
    cover_pct = (solar_gwh / demand_gwh * 100.0) if demand_gwh else 0.0
    return {
        "scope": scope,
        "installs": installs_scope,
        "share_pct": round(share * 100.0, 2),
        "solar_gwh": round(solar_gwh, 1),
        "demand_gwh": round(demand_gwh, 1),
        "solar_pct_demand": round(cover_pct, 2),
        "solar_pct_national": round(solar_gwh / NATIONAL_SOLAR_GWH * 100.0, 2)
        if NATIONAL_SOLAR_GWH else 0.0,
    }


def bulletin_summary():
    ref = BULLETIN_REFERENCE
    return ref