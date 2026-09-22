import streamlit as st
from ui.theme import (STEG_BLUE, STEG_RED, HORIZON_OPTIONS,
                       render_filters, get_scope, get_horizon_hours,
                       get_horizon_label, fig_theme)
from ui import hierarchy
from config import DEFAULT_SCENARIO
from core import engine
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime


def render():
    st.markdown("""
    <div class="steg-subnav">
      <a href="#section-production">Production</a>
      <a href="#section-consommation">Consommation</a>
      <a href="#section-comparaison">Comparaison</a>
      <a href="#section-prevision-reel">Prevision vs Reel</a>
    </div>
    """, unsafe_allow_html=True)

    render_filters()

    @st.fragment(run_every=300)
    def production_dashboard():
        scope = get_scope()
        horizon_hours = get_horizon_hours()
        horizon_label = get_horizon_label()

        st.markdown(f"### Production solaire — {hierarchy.scope_label(scope)}  .  Horizon : **{horizon_label}**")

        @st.cache_data(ttl=600, show_spinner=False)
        def run_engine_cached(s, sc, h, n, r, u):
            return engine.build_forecast(s, sc, horizon_hours=h, force_ml=r,
                                         force_weather=n > 0, username=u)

        res = run_engine_cached(scope, DEFAULT_SCENARIO, horizon_hours,
                                datetime.now().minute // 5, False,
                                st.session_state["user"]["username"])

        fut = res["future"]
        now = pd.Timestamp.now(tz="Africa/Tunis")
        now_disp = now.strftime("%H:%M:%S")

        last_run = st.session_state.get("dash_last_run")
        next_refresh = (last_run + pd.Timedelta(seconds=300)) if last_run is not None \
            else (now + pd.Timedelta(seconds=300))
        st.session_state["dash_last_run"] = now

        win = fut[fut.index > now]

        if len(win) > 0:
            t0 = win.index[0]
            t1 = win.index[-1]
            dt_h = (t1 - t0).total_seconds() / 3600.0
            mw = win["inject_ml_mw"]

            if len(win) <= 2:
                energy = float(((mw.iloc[0] + mw.iloc[-1]) / 2) * dt_h) if len(mw) >= 2 \
                    else float(mw.iloc[0] * (dt_h or 0.25))
            else:
                energy = float(mw.sum() * 0.25)

            st.metric(
                f"Energie produite de {t0:%H:%M} a {t1:%H:%M}",
                f"{energy:.2f} MWh",
            )

            if horizon_hours <= 1.0:
                step_rows = "  ".join(
                    f"* {t.strftime('%H:%M')} : {v:.2f} MW" for t, v in zip(win.index, mw)
                )
                st.caption(step_rows)

            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=win.index, y=mw,
                mode="lines+markers", name="Injection PV",
                line=dict(color="#16a34a", width=4),
                marker=dict(size=6, color="#16a34a"),
                fill="tozeroy", fillcolor="rgba(22,163,74,0.15)",
            ))
            fig_theme(fig, 330, margin=dict(l=10, r=10, t=10, b=10))
            fig.update_layout(xaxis_title="", yaxis_title="MW", showlegend=False)
            if horizon_hours <= 1.0:
                fig.update_layout(
                    xaxis=dict(tickformat="%H:%M", dtick=900 * 1000),
                    yaxis=dict(range=[0, max(mw.max() * 1.3, 10)]),
                )
            st.plotly_chart(fig, width="stretch")
        else:
            st.info("Aucune prevision future disponible.")

        st.caption(
            f"Heure actuelle : **{now_disp}**  .  Prochaine actualisation : **{next_refresh:%H:%M:%S}**"
        )

    st.markdown('<div id="section-production" class="section-anchor"></div>', unsafe_allow_html=True)
    production_dashboard()

    st.markdown('<div id="section-cible" class="section-anchor"></div>', unsafe_allow_html=True)

    @st.fragment(run_every=300)
    def cible_dashboard():
        scope = get_scope()
        horizon_hours = get_horizon_hours()
        horizon_label = get_horizon_label()

        st.markdown(
            f"### Cible : 4% de la consommation — {hierarchy.scope_label(scope)}  .  Horizon : **{horizon_label}**"
        )

        @st.cache_data(ttl=600, show_spinner=False)
        def run_engine_cached(s, sc, h, n, r, u):
            return engine.build_forecast(s, sc, horizon_hours=h, force_ml=r,
                                         force_weather=n > 0, username=u)

        res = run_engine_cached(scope, DEFAULT_SCENARIO, horizon_hours,
                         datetime.now().minute // 5, False,
                         st.session_state["user"]["username"])

        fut = res["future"]
        now = pd.Timestamp.now(tz="Africa/Tunis")
        win = fut[fut.index > now]

        if len(win) == 0:
            st.info("Aucune prevision future disponible.")
            return

        # Same reference as the comparison panel: 4 % of the whole scope demand,
        # night included (the annual anchor: ~820 GWh ≈ 4 % de ~19 400 GWh).
        dm, target_mw, day_mask = hierarchy.scope_day_reference(win)


    @st.fragment(run_every=300)
    def demand_dashboard():
        scope = get_scope()
        horizon_hours = get_horizon_hours()
        horizon_label = get_horizon_label()

        st.markdown(f"### Energie necessaire — {hierarchy.scope_label(scope)}")

        @st.cache_data(ttl=600, show_spinner=False)
        def run_engine_cached(s, sc, h, n, r, u):
            return engine.build_forecast(s, sc, horizon_hours=h, force_ml=r,
                                         force_weather=n > 0, username=u)

        res = run_engine_cached(scope, DEFAULT_SCENARIO, horizon_hours,
                         datetime.now().minute // 5, False,
                         st.session_state["user"]["username"])

        fut = res["future"]
        now = pd.Timestamp.now(tz="Africa/Tunis")
        now_disp = now.strftime("%H:%M:%S")

        last_run = st.session_state.get("demand_last_run")
        next_refresh = (last_run + pd.Timedelta(seconds=300)) if last_run is not None \
            else (now + pd.Timedelta(seconds=300))
        st.session_state["demand_last_run"] = now

        win = fut[fut.index > now]

        if len(win) > 0:
            t0 = win.index[0]
            t1 = win.index[-1]
            dm = win["demand_mw"]
            temp = win["temp"]

            if len(win) <= 2:
                energy = float(((dm.iloc[0] + dm.iloc[-1]) / 2)
                               * (t1 - t0).total_seconds() / 3600.0) if len(dm) >= 2 \
                    else float(dm.iloc[0] * 0.25)
            else:
                energy = float(dm.sum() * 0.25)

            peak_mw = float(dm.max())
            peak_t = dm.idxmax()

            st.markdown(
                f"""
                <div style="background:linear-gradient(135deg,#d7263d,#a41c2e);border-radius:16px;
                     padding:22px 28px;box-shadow:0 4px 16px rgba(215,38,61,0.25);color:#fff;">
                  <div style="font-size:15px;font-weight:600;opacity:.92">Energie necessaire de {t0:%H:%M} a {t1:%H:%M}</div>
                  <div style="font-size:44px;font-weight:700;line-height:1.15">{energy:.2f} MWh</div>
                  <div style="font-size:14px;opacity:.9">Pic : {peak_mw:.1f} MW a {peak_t:%H:%M}  .  Temp. moyenne : {temp.mean():.1f} C</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=win.index, y=dm,
                mode="lines+markers", name="Demande",
                line=dict(color=STEG_RED, width=4),
                marker=dict(size=6, color=STEG_RED),
                fill="tozeroy", fillcolor="rgba(215,38,61,0.15)",
            ))
            fig_theme(fig, 330, margin=dict(l=10, r=10, t=10, b=10))
            fig.update_layout(xaxis_title="", yaxis_title="MW", showlegend=False)
            if horizon_hours <= 1.0:
                fig.update_layout(
                    xaxis=dict(tickformat="%H:%M", dtick=900 * 1000),
                    yaxis=dict(range=[0, max(dm.max() * 1.3, 10)]),
                )
            st.plotly_chart(fig, width="stretch")

            st.caption(
                "Calcul : profil horaire STEG x part regionale "
                "x (1 + 2,5 %/C estime au-dessus de 24 C) x weekend (0,85)"
            )
        else:
            st.info("Aucune prevision future disponible.")

        st.caption(
            f"Heure actuelle : **{now_disp}**  .  Prochaine actualisation : **{next_refresh:%H:%M:%S}**"
        )

    demand_dashboard()

    st.markdown('<div id="section-comparaison" class="section-anchor"></div>', unsafe_allow_html=True)

    @st.fragment(run_every=300)
    def comparison_dashboard():
        scope = get_scope()
        horizon_hours = get_horizon_hours()
        horizon_label = get_horizon_label()

        st.markdown(f"### Comparaison Production / Consommation — {hierarchy.scope_label(scope)}  .  Horizon : **{horizon_label}**")

        @st.cache_data(ttl=600, show_spinner=False)
        def run_engine_cached(s, sc, h, n, r, u):
            return engine.build_forecast(s, sc, horizon_hours=h, force_ml=r,
                                         force_weather=n > 0, username=u)

        res = run_engine_cached(scope, DEFAULT_SCENARIO, horizon_hours,
                         datetime.now().minute // 5, False,
                         st.session_state["user"]["username"])

        fut = res["future"]
        if len(fut) == 0:
            st.info("Aucune prevision future disponible.")
            return

        # Same window as the two dashboards above: now -> horizon end.
        now = pd.Timestamp.now(tz="Africa/Tunis")
        win = fut[fut.index > now]

        pv = win["inject_ml_mw"]
        dm, target_mw, day_mask = hierarchy.scope_day_reference(win)

        e_pv = float(pv.sum() * 0.25)
        e_dm = float(dm.sum() * 0.25)
        cover = (e_pv / e_dm * 100) if e_dm > 0 else 0.0
        e_target = float(target_mw.sum() * 0.25)
        e_pv_day = float(pv.to_numpy()[day_mask].sum() * 0.25)
        e_dm_day = float(dm.to_numpy()[day_mask].sum() * 0.25)
        day_cover = (e_pv_day / e_dm_day * 100) if e_dm_day > 0 else 0.0

        # Nombre de pas ou la production ciblee (4 % de la demande).
        n_ok = int((pv >= target_mw).sum())
        n_tot = int(len(pv))
        peak_pv = float(pv.max())
        peak_target = float(target_mw.max())

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=win.index, y=pv,
            mode="lines", name="Production PV estimee (injection)",
            line=dict(color="#16a34a", width=3), connectgaps=False,
        ))
        fig.add_trace(go.Scatter(
            x=win.index, y=target_mw,
            mode="lines", name="Cible : 4% de la consommation",
            line=dict(color=STEG_RED, width=3), connectgaps=False,
        ))
        fig_theme(fig, 380, margin=dict(l=10, r=10, t=10, b=10))
        fig.update_layout(
            xaxis_title="", yaxis_title="MW",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
            xaxis=dict(tickformat="%a %d/%m %H:%M"),
        )
        st.plotly_chart(fig, width="stretch")
        st.markdown(
            f"**Energie PV : {e_pv:.1f} MWh**   |   **Energie consommee : {e_dm:.1f} MWh**"
            f"   |   **Cible solaire (4%) : {e_target:.1f} MWh**"
            f"   |   **Couverture : {cover:.1f}%**"
        )
        st.markdown(
            f"- **Production >= cible : {n_ok} pas sur {n_tot} (" f"{n_ok/n_tot*100:.0f}%)**"
            f" — le solaire atteint ou depasse sa part attendue le jour."
            f"\n- Pic solaire : **{peak_pv:.1f} MW** vs cible max : **{peak_target:.1f} MW**"
            f" (le solaire culmine a x{peak_pv/peak_target:.1f} la cible)."
            f"\n- Partage heures de jour : le solaire couvre **{day_cover:.1f}%**"
            f" de la consommation de jour ({e_pv_day:.1f} / {e_dm_day:.1f} MWh)."
        )

    comparison_dashboard()

    @st.fragment(run_every=300)
    def prevision_reel_section():
        from pages import prevision_reel
        prevision_reel.render_panel()

    prevision_reel_section()

