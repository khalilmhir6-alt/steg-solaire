"""Prevision vs Reel tab.

One chart, two curves on the SAME window (shared Region + Horizon filters,
R1), matching the Production solaire dashboard at the top of the page
step-for-step:

  - "Production solaire" : inject_ml_mw — identical values and window to the
                           green Production solaire panel (so the two green
                           curves are the same series).
  - "Production prévue"  : inject_phys_mw — the physical forecast (pre-ML
                           correction), which weaves around the ML estimate
                           instead of sitting systematically above it.
"""

from datetime import datetime

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
    def run_engine_cached(s, sc, h, n, r, u):
        return engine.build_forecast(
            s, sc, horizon_hours=h, force_ml=r, force_weather=False, username=u
        )

    res = run_engine_cached(
        scope, DEFAULT_SCENARIO, horizon_hours,
        datetime.now().minute // 5, False,
        st.session_state["user"]["username"],
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

    solaire_mw = win["inject_ml_mw"]
    prevue_mw = win["inject_phys_mw"]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=win.index, y=solaire_mw, mode="lines+markers",
        line=dict(color="#16a34a", width=3),
        marker=dict(size=4, color="#16a34a"),
        name="Production solaire",
    ))
    fig.add_trace(go.Scatter(
        x=win.index, y=prevue_mw, mode="lines+markers",
        line=dict(color=STEG_RED, width=3),
        marker=dict(size=4, color=STEG_RED),
        name="Production prévue",
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
