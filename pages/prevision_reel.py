"""Prevision vs Reel tab.

One chart, two curves on the SAME window (shared Region + Horizon filters,
R1) restricted to the daylight part of the day (day mask from hierarchy,
R4):

  - "Production prevue"   : inject_ml_mw returned by engine.build_forecast
  - "Production reelle"   : read from ACTUAL_LOG_PATH (append-only JSONL the
                            engine writes on every build).

Today the 'actual' stream is SIMULATED: the engine appends one JSONL line per
forecast step where actual_mw = forecast value + a small random variation,
every record flagged source='simulated' so operators can tell the mock from a
real meter at a glance (R1 mock). When a real metering stream is wired in,
only the engine writer's payload swaps to measured MW - the schema, this page
and the append-only capture stay identical.

If the capture file is missing or empty for this window we fall back to a
clearly-labelled simulated series (same shape as the engine mock: seed 7,
+/-2%) so the tab is never empty while the mock is the only source.
"""

import json
import os
from datetime import datetime

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from config import DEFAULT_SCENARIO
from core import engine
from ui import hierarchy
from ui.theme import (
    STEG_BLUE,
    STEG_RED,
    render_filters,
    get_scope,
    get_horizon_hours,
    get_horizon_label,
    fig_theme,
)


def render():
    render_filters()
    render_panel()


def render_panel():

    scope = get_scope()
    horizon_hours = get_horizon_hours()
    horizon_label = get_horizon_label()

    st.markdown(
        f"### Prevision vs Reel - {hierarchy.scope_label(scope)}"
        f"  |  Horizon : **{horizon_label}**"
    )

    @st.cache_data(ttl=600, show_spinner=False)
    def run_engine_cached(s, sc, h, n, r):
        return engine.build_forecast(
            s, sc, horizon_hours=h, force_ml=r, force_weather=n > 0
        )

    res = run_engine_cached(
        scope, DEFAULT_SCENARIO, horizon_hours,
        datetime.now().minute // 5, False,
    )

    fut = res.get("future")
    if fut is None or len(fut) == 0:
        st.info("Aucune projection future dans la fenetre de cet horizon.")
        return

    now = pd.Timestamp.now(tz="Africa/Tunis")
    win = fut.loc[fut.index > now]
    if len(win) == 0:
        st.info("Tous les pas de cet horizon sont deja passes.")
        return

    forecast_mw = win["inject_ml_mw"]

    # Real production: read the append-only capture (engine writes one JSONL
    # line per step on every build). If nothing has been captured yet for this
    # window, fall back to a clearly-labelled SIMULATED series so the tab is
    # never empty - the mock is the same shape as the real stream: forecast
    # value + a small random variation, marked source='simulated'.
    actual_mw, all_simulated = _load_actual_series(win, scope, DEFAULT_SCENARIO)
    if actual_mw is None:
        rng = np.random.default_rng(seed=7)  # same stable mock as engine
        actual_mw = (forecast_mw * (1.0 + rng.normal(0.0, 0.02, size=len(forecast_mw))))\
            .clip(lower=0.0)
        source_label = "Production reelle (simulee)"
    elif all_simulated:
        source_label = "Production reelle (simulee)"
    else:
        source_label = "Production reelle (mesuree)"

    dm, target_mw, day_mask = hierarchy.scope_day_reference(win)

    if day_mask.sum() > 0:
        x = win.index[day_mask]
        f = forecast_mw.to_numpy()[day_mask]
        a = actual_mw.to_numpy()[day_mask]
    else:
        x = win.index
        f = forecast_mw.to_numpy()
        a = actual_mw.to_numpy()

    hi = np.maximum(f, a)
    lo = np.minimum(f, a)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=x, y=hi, mode="lines",
        line=dict(color="rgba(0,0,0,0)", width=0),
        showlegend=False, hoverinfo="skip",
    ))
    fig.add_trace(go.Scatter(
        x=x, y=lo, fill="tonexty", mode="lines",
        line=dict(color="rgba(0,0,0,0)", width=0),
        fillcolor="rgba(211,84,0,0.18)",
        name="Ecart previ/reel",
    ))
    fig.add_trace(go.Scatter(
        x=x, y=f, mode="lines+markers",
        line=dict(color="rgba(11,61,145,0.9)", width=2.2),
        marker=dict(size=4),
        name="Production prevue",
    ))
    fig.add_trace(go.Scatter(
        x=x, y=a, mode="lines+markers",
        line=dict(color="rgba(182,43,71,0.95)", width=2.2),
        marker=dict(size=4),
        name=source_label,
    ))

    fig.update_layout(
        yaxis_title="MW",
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0,
        ),
        margin=dict(l=10, r=10, t=30, b=10),
    )
    fig = fig_theme(fig, height=430)
    st.plotly_chart(fig, width="stretch")

    st.caption(
        "Les valeurs 'reelles' affichees a ce jour sont SIMULEES "
        "(prevision + petite variation aleatoire, source='simulated'). "
        "D\u00e8s qu'un compteur reel sera branche, seul le payload de "
        "l'ecrivain dans core/engine.py basculera vers les MW mesures - "
        "le schema JSONL, la capture append-only et ce graphique restent "
        "identiques."
    )


def _load_actual_series(win, scope, scenario):
    """Read the append-only capture of real-measured production.

    Returns a pd.Series aligned to win.index (nearest match) or None when the
    log is missing/empty. The engine writes one JSONL line per forecast step
    at build time -- today those values are SIMULATED and flagged
    source='simulated' until a real metering stream is wired in; the schema
    and the append writer stay the same once the live meter lands.
    """
    path = getattr(engine, "ACTUAL_LOG_PATH", None)
    if not path or not os.path.exists(path):
        return None, True

    recs = []
    with open(path, encoding="utf-8") as f:
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
            if rec.get("scenario") != scenario:
                continue
            recs.append(rec)

    if not recs:
        return None, True

    df = pd.DataFrame(recs)
    df["ts"] = pd.to_datetime(df["ts"])
    df = df.sort_values("ts").drop_duplicates("ts", keep="last").set_index("ts")
    s = df["actual_mw"].reindex(win.index, method="nearest").round(3)
    all_simulated = all(r.get("source", "simulated") == "simulated" for r in recs)
    return s, all_simulated
