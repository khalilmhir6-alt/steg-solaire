# -*- coding: utf-8 -*-
"""Production-vs-forecast alert state. STEP-1 only: the PURE COMPUTATION.

STEP-1 scope (the contract, nothing more):
  * reads ONLY the tail of the append-only capture core/engine.py writes
    (config, ACTUAL_LOG_PATH — JSONL; today source="simulated": a simulated
    twin whose physics are kept anchored on the REAL STEG GHI + geometry, so
    the picture is honest for an operator trial) — exactly the SAME tail, the
    SAME day reference, and the SAME payload the dashboard panel "Prévision
    vs Réel" reads. Convention: the alert picture must agree with the panel.
  * NO Streamlit. NO auth / role / route logic. NO change to the forecast
    model. NO write to the log.
  * DEMO_DEVIATION is applied IN MEMORY ONLY (the observed "actual" of the
    last daytime HOOT is scaled by (1-DEMO_DEVIATION) in the computed series
    and is NEVER written back); the returned dict carries demo=True then.

Persistence is STATELESS: each call replays the last ALERT_RECENT_STEPS
daytime steps through a small persistence state machine — a yellow/red flips
only after ALERT_PERSISTENCE_STEPS CONSECUTIVE steps at-or-beyond that level
(and back to green needs the same consecutive count below). There is NO
module-level state dict, so repeated calls on the same window are identical.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any

import numpy as np
import pandas as pd

from config import (
    ACTUAL_LOG_PATH,
    ALERT_PERSISTENCE_STEPS,
    ALERT_RECENT_STEPS,
    ALERT_THRESHOLDS,
    DEFAULT_SCENARIO,
    DEMO_DEVIATION,
)


# ---------------------------------------------------------------------------
# Scope level / installed capacity / day mask — SAME single source of truth
# as the dashboard (ui.hierarchy). Anything the panels derive for scope,
# alerts derive here from that same hierarchy so they can NEVER disagree.
# ---------------------------------------------------------------------------


def _scope_level(scope: str) -> str:
    """'national' for tunisia, 'region' for the 7 regions, 'district' else."""
    if scope in ("tunisia", "nationale"):
        return "national"
    try:
        from ui.hierarchy import list_regions

        if scope in list_regions():
            return "region"
    except Exception:
        pass
    return "district"


def _installed_capacity_mw(scope: str) -> float:
    """Installed capacity in MW of *scope*, from ui.hierarchy (same reference
    every panel labels 'capacité installée'). 0 when unknown."""
    try:
        from ui.hierarchy import scope_capacity_mw

        cap = scope_capacity_mw(scope)
        return float(cap) if cap and cap > 0 else 0.0
    except Exception:
        return 0.0


def _day_mask(df: pd.DataFrame) -> np.ndarray:
    """Day mask over df.index via ui.hierarchy.scope_day_reference — the SAME
    reference every dashboard panel uses for 'day'. Fallback: treat as day
    whenever forecast or actual is > 0."""
    try:
        from ui.hierarchy import scope_day_reference

        _, _, day_mask = scope_day_reference(df.index)
        return np.asarray(day_mask, dtype=bool)
    except Exception:
        f = df["forecast_mw"].to_numpy(dtype=float)
        a = df["actual_mw"].to_numpy(dtype=float)
        return (f > 0.0) | (a > 0.0)


# ---------------------------------------------------------------------------
# Log reading — the EXACT tail filter the panel "Prévision vs Réel" applies
# (same ACTUAL_LOG_PATH, same scope scenario horizon; same day reference) so
# alerts and dashboard judge the SAME steps.
# ---------------------------------------------------------------------------


def _load_recent_series(
    scope: str,
    scenario: str | None,
    horizon_hours: int | None,
    as_of: str | None = None,
) -> pd.DataFrame | None:
    """Tail of ACTUAL_LOG_PATH for *scope* (+ optional scenario/horizon), the
    last ALERT_RECENT_STEPS rows, sorted, deduped, indexed by ts. None when
    the log is missing or has no row for this scope."""
    if not ACTUAL_LOG_PATH or not os.path.exists(ACTUAL_LOG_PATH):
        return None

    recs = []
    with open(ACTUAL_LOG_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except Exception:
                continue
            if rec.get("scope") != scope:
                continue
            if scenario is not None and rec.get("scenario") != scenario:
                continue
            if horizon_hours is not None:
                hh = rec.get("horizon_hours")
                if hh is not None and int(hh) != int(horizon_hours):
                    continue
            recs.append(rec)

    if not recs:
        return None

    df = pd.DataFrame(recs)
    df["ts"] = pd.to_datetime(df["ts"])
    if as_of is not None:
        try:
            cutoff = pd.Timestamp(as_of)
            if cutoff.tzinfo is not None:
                cutoff = cutoff.tz_convert(None)
            df = df[df["ts"] <= cutoff]
        except Exception:
            pass
    df = (
        df.sort_values("ts")
        .drop_duplicates("ts", keep="last")
        .tail(ALERT_RECENT_STEPS)
        .set_index("ts")
    )
    return df


# ---------------------------------------------------------------------------
# Step classification + stateless persistence replay
# ---------------------------------------------------------------------------


def _classify_step(dev_mw: float, capacity_mw: float, level: str) -> str:
    """One step's state from |deviation|/capacity vs ALERT_THRESHOLDS[level]:
    green | yellow | red."""
    if capacity_mw <= 0:
        return "green"
    yellow_frac, red_frac = ALERT_THRESHOLDS[level]
    frac = abs(dev_mw) / capacity_mw
    if frac >= red_frac:
        return "red"
    if frac >= yellow_frac:
        return "yellow"
    return "green"


def _replay_persistence(states: list[str]) -> str:
    """Replay the daytime step states (oldest -> newest) through the persistence
    rule specified for STEP-1:

      * yellow/red becomes the CURRENT state only after
        ALERT_PERSISTENCE_STEPS CONSECUTIVE steps at-or-beyond that level
        (red also counts toward yellow);
      * returning to green requires the same number of consecutive steps
        below yellow.

    Stateless: uses only `states`, NO module dict. The newest homogeneous run
    wins when it is long enough; otherwise green (no flip yet)."""
    p = max(1, int(ALERT_PERSISTENCE_STEPS))
    if not states:
        return "green"

    # Count the trailing homogeneous run (oldest-first order).
    run_class = states[-1]
    run_len = 1
    for s in reversed(states[:-1]):
        if s == run_class:
            run_len += 1
        else:
            break

    if run_len >= p:
        if run_class == "red":
            return "red"
        if run_class == "yellow":
            return "yellow"
        return run_class  # "green"

    # A run that is yellow/red but shorter than p: persistence not reached
    # yet (the last steps are "too close to now" to flip) -> green.
    # Same for a short green run: it is already green.
    return "green"


def _classify_signed_outlook(
    outlook_dev_mw: float, capacity_mw: float, level: str
) -> str:
    """Classify the OUTLOOK step (a SINGLE projected deviation, MW — signed)
    with the same yellow/red thresholds (|dev| over yellow/red)."""
    return _classify_step(outlook_dev_mw, capacity_mw, level)


def evaluate_scope_alerts(
    scope: str,
    scenario: str | None = None,
    horizon_hours: int | None = None,
    as_of: str | None = None,
) -> dict[str, Any]:
    """Evaluate the alert state for *scope* (STEP-1 pure computation).

    Returns a dict:
        scope, scope_level               : the scope + its hierarchy level
        installed_mw                     : installed capacity (MW)
        threshold_yellow_pct / red_pct   : yellow/red as % of installed
        current_state                    : green|yellow|red (persistence
                                          applied); green at night
        outlook_state                    : green|yellow|red — mean SIGNED
                                          deviation of the last 3 daytime
                                          steps applied to the next forecast
                                          step, then classified
        deviation_pct                    : |actual-forecast| / installed (%)
                                          on the last daytime step
        direction_under / direction_over : 0/1 flags (under / over production)
        night                            : True when last step is outside the
                                          day reference (forced green)
        demo                             : True when DEMO_DEVIATION was applied
                                          (in-memory only, never written)
        available                        : False when log missing/empty for
                                          scope -> current_state="green" and
                                          yellow/red UNREACHABLE
        n_steps                          : daytime steps actually evaluated
        evaluated_ts                     : iso ts of the newest daytime step
    """
    scenario = scenario or DEFAULT_SCENARIO
    level = _scope_level(scope)
    installed_mw = _installed_capacity_mw(scope)
    cap = installed_mw

    df = _load_recent_series(scope, scenario, horizon_hours, as_of)
    if df is None or df.empty:
        return {
            "scope": scope,
            "scope_level": level,
            "installed_mw": round(cap, 2),
            "threshold_yellow_pct": (
                ALERT_THRESHOLDS[level][0] * 100.0 if cap > 0 else None
            ),
            "threshold_red_pct": (
                ALERT_THRESHOLDS[level][1] * 100.0 if cap > 0 else None
            ),
            "current_state": "green",
            "outlook_state": "green",
            "deviation_pct": 0.0,
            "direction_under": False,
            "direction_over": False,
            "night": False,
            "demo": False,
            "available": False,
            "n_steps": 0,
            "evaluated_ts": None,
        }

    day_mask = _day_mask(df)
    day_idx = np.flatnonzero(day_mask)
    if day_idx.size == 0:
        # Night window: forced green (production at night ~ 0, nothing to
        # alert on) — same rule every dashboard panel uses.
        return {
            "scope": scope,
            "scope_level": level,
            "installed_mw": round(cap, 2),
            "threshold_yellow_pct": (
                ALERT_THRESHOLDS[level][0] * 100.0 if cap > 0 else None
            ),
            "threshold_red_pct": (
                ALERT_THRESHOLDS[level][1] * 100.0 if cap > 0 else None
            ),
            "current_state": "green",
            "outlook_state": "green",
            "deviation_pct": 0.0,
            "direction_under": False,
            "direction_over": False,
            "night": True,
            "demo": False,
            "available": True,
            "n_steps": int(len(df)),
            "evaluated_ts": None,
        }

    forecast = df["forecast_mw"].to_numpy(dtype=float)
    actual = df["actual_mw"].to_numpy(dtype=float).copy()

    # DEMO_DEVIATION is applied IN MEMORY ONLY to the last daytime steps (one
    # hour = up to 4 steps) — NEVER written to the log.
    demo = False
    if DEMO_DEVIATION and float(DEMO_DEVIATION) > 0:
        demo = True
        last_hour = day_idx[-min(4, day_idx.size):]
        actual[last_hour] *= 1.0 - float(DEMO_DEVIATION)

    dev_mw = actual - forecast
    day_dev_mw = dev_mw[day_idx]
    day_forecast = forecast[day_idx]

    # ---- Current state (persistence replayed over daytime steps) ------------
    states = [_classify_step(d, cap, level) for d in day_dev_mw]
    current_state = _replay_persistence(states)

    # ---- Deviation / direction on the last daytime step ---------------------
    last_dev = float(day_dev_mw[-1])
    direction_under = bool(last_dev < 0)
    direction_over = bool(last_dev > 0)
    dev_pct = abs(last_dev) / cap * 100.0 if cap > 0 else 0.0

    # ---- Outlook: mean SIGNED deviation of the last 3 daytime steps applied
    #      to the next forecast step, then classified with same thresholds ----
    outlook_state = "green"
    outlook_dev = 0.0
    outlook_dev_pct = 0.0
    if len(day_dev_mw) >= 1:
        mean_signed = float(np.mean(day_dev_mw[-3:]))
        outlook_dev = mean_signed
        next_forecast = float(day_forecast[-1]) if len(day_forecast) else 0.0
        outlook_dev_pct = abs(outlook_dev) / cap * 100.0 if cap > 0 else 0.0
    outlook_state = _classify_signed_outlook(outlook_dev, cap, level)

    return {
        "scope": scope,
        "scope_level": level,
        "installed_mw": round(cap, 2),
        "threshold_yellow_pct": (
            ALERT_THRESHOLDS[level][0] * 100.0 if cap > 0 else None
        ),
        "threshold_red_pct": (
            ALERT_THRESHOLDS[level][1] * 100.0 if cap > 0 else None
        ),
        "current_state": current_state,
        "outlook_state": outlook_state,
        "deviation_pct": round(dev_pct, 2),
        "outlook_deviation_pct": round(outlook_dev_pct, 2),
        "direction_under": direction_under,
        "direction_over": direction_over,
        "night": False,
        "demo": demo,
        "available": True,
        "n_steps": int(len(day_idx)),
        "evaluated_ts": df.index[day_idx[-1]].isoformat(),
    }
