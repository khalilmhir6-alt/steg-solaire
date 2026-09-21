"""
Layered forecasting & storage-capacity curve builder (strategic layer).

The DSO storage-planning view: for any aggregate scope, produce the
  - geographically layered injection curves (nationale -> région -> district),
  - aggregated capacity curve (MW accumulated by fleet tier / scenario),
  - storage hours curve (injectable output per MWh of storage) used to size
    BESS for the distribution grid.

Everything scales linearly off one per-kWp geometric curve, so the layers
are cheap to recompute for every scenario and scope.
"""

import pandas as pd

from config import CAPACITY_SCENARIOS, DEFAULT_SCENARIO, FLEET_SIZE_DISTRIBUTION_KWC
from ui import hierarchy


def _inject_per_kwp_curve(engine_result):
    """MW per installed MWp across the forecast window (from engine frame)."""
    fut = engine_result["future"].copy()
    fut["mw_per_mwp"] = fut["inject_ml_mw"] / max(engine_result["installed"], 1)
    return fut[["mw_per_mwp"]]


def build_layers(engine_result, scenario=None):
    """Return nested layer structure: physical capacity and injection per node."""
    scenario = scenario or DEFAULT_SCENARIO
    curve = _inject_per_kwp_curve(engine_result)
    mw_per_mwp = curve["mw_per_mwp"]
    times = curve.index

    def node_injection(capacity_mw):
        return (mw_per_mwp * capacity_mw).clip(lower=0).round(3)

    national = {
        "label": "TUNISIA",
        "scope": "tunisia",
        "capacity_mw": hierarchy.scope_capacity_mw("tunisia", scenario),
        "series": node_injection(hierarchy.scope_capacity_mw("tunisia", scenario)),
        "regions": [],
    }
    for reg in hierarchy.list_regions():
        cap = hierarchy.region_capacity_mw(reg, scenario)
        region_node = {
            "label": hierarchy.REGION_LABELS[reg],
            "scope": reg,
            "capacity_mw": cap,
            "series": node_injection(cap),
            "districts": [],
        }
        for d in hierarchy.districts_of_region(reg):
            dcap = hierarchy.district_capacity_mw(d, scenario)
            region_node["districts"].append({
                "label": hierarchy.DISTRICTS[d][1],
                "scope": f"{reg}/{d}",
                "capacity_mw": dcap,
                "series": node_injection(dcap),
            })
        national["regions"].append(region_node)

    # storage sizing curve: MWh of battery (2h/4h/6h) vs. flat-shift potential
    dt_h = (times[1] - times[0]).total_seconds() / 3600.0 if len(times) > 1 else 0.25
    daily_energy_mwh = float(mw_per_mwp.sum() / 1000.0 * dt_h)
    storage_curve = []
    peak_day_mw = float(mw_per_mwp.max())
    for hours in (2, 4, 6):
        # simplistic frontier: shift daylight surplus into evening shoulders
        shift_capacity_mw = round(daily_energy_mwh / 16.0, 3)
        storage_curve.append({
            "duration_h": hours,
            "capacity_mwh": round(shift_capacity_mw * hours, 2),
            "peak_smooth_mw": round(min(shift_capacity_mw, peak_day_mw), 3),
        })

    return {
        "times": times,
        "national": national,
        "scenario": scenario,
        "fleet_tiers": FLEET_SIZE_DISTRIBUTION_KWC,
        "storage_curve": storage_curve,
        "injection_capacity_curve": _capacity_curve(engine_result, scenario),
    }


def _capacity_curve(engine_result, scenario):
    """Accumulated installed MW as function of installation size tier."""
    tiers = sorted(FLEET_SIZE_DISTRIBUTION_KWC)
    total_mw = hierarchy.scope_capacity_mw("tunisia", scenario or DEFAULT_SCENARIO)
    acc = []
    cum = 0.0
    for kwc in tiers:
        n = FLEET_SIZE_DISTRIBUTION_KWC[kwc]
        cum += n * kwc
        acc.append({"size_kwc": kwc, "count": n,
                    "cum_mw": round(cum / 1000.0, 2),
                    "share_of_total": round(cum / 1000.0 / total_mw, 3)})
    return acc