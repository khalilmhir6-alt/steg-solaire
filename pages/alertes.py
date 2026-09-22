import streamlit as st
from ui.theme import (STEG_BLUE, render_filters, get_scope, get_horizon_hours)
from config import DEFAULT_SCENARIO
from core import engine
import pandas as pd
from datetime import datetime


def render():
    st.markdown("""
    <div class="steg-subnav">
      <a href="#section-alertes-detail">Alerte de baisse</a>
      <a href="#section-alertes-detail">Situation normale</a>
    </div>
    """, unsafe_allow_html=True)

    render_filters()

    NORMAL_CARD = """
    <div style="background:linear-gradient(135deg,#f0fff4,#d9f2e3);border:1px solid #7dc99b;border-radius:16px;padding:34px;text-align:center;">
      <div style="font-size:21px;font-weight:700;color:#1b5e20;margin-top:8px">Situation normale</div>
      <div style="font-size:15px;color:#3b6e4f;margin-top:6px">Aucune baisse de production solaire prevue sur la periode.</div>
    </div>
    """

    st.markdown('<div id="section-alertes-detail" class="section-anchor"></div>', unsafe_allow_html=True)

    scope = get_scope()
    horizon_hours = get_horizon_hours()

    @st.cache_data(ttl=600, show_spinner=False)
    def run_engine_cached(s, sc, h, n, r, u):
        return engine.build_forecast(s, sc, horizon_hours=h, force_ml=r,
                                     force_weather=n > 0, username=u)

    nonce = datetime.now().minute // 5
    _res = run_engine_cached(scope, DEFAULT_SCENARIO, horizon_hours, nonce, False,
                             st.session_state["user"]["username"])
    alerts = _res["alerts"]
    if not alerts:
        st.markdown(NORMAL_CARD, unsafe_allow_html=True)
    else:
        for a in alerts:
            if a["level"] == "RED":
                titre = "Baisse de production"
            else:
                titre = "Leger risque de baisse"
            t0 = pd.Timestamp(a["t0"])
            t1 = pd.Timestamp(a["t1"])
            with st.container(border=True):
                c1, c2 = st.columns([1, 7])
                c1.markdown(f"### ")
                c2.markdown(f"**{titre}**  \n"
                            f"De {t0:%H:%M} a {t1:%H:%M}, la production solaire devrait "
                            f"chuter d'environ {a['drop_pct']:.0f} % "
                            f"({a['v0_mw']:.1f} MW -> {a['v1_mw']:.1f} MW).")
        st.caption("Ces alertes apparaissent aussi sur le Dashboard (bandes orange/rouge sur la courbe).")
