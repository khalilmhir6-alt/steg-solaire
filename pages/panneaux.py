import streamlit as st
from ui.theme import render_filters, region_label
from ui import registry, hierarchy, auth
import pandas as pd


def _scope_options(user):
    """Liste des perimetres proposables a l'utilisateur (region ou district)."""
    if auth.is_national(user):
        return ["tunisia"] + hierarchy.list_regions()
    allowed = auth.allowed_scopes(user)
    return [("nationale" if s == "tunisia" else s) for s in allowed]


def render():
    user = st.session_state.get("user")

    st.markdown("""
    <div class="steg-subnav">
      <a href="#section-panneaux-form">Formulaire</a>
      <a href="#section-panneaux-list">Panneaux enregistres</a>
    </div>
    """, unsafe_allow_html=True)

    render_filters()

    opts = _scope_options(user)

    st.markdown('<div id="section-panneaux-form" class="section-anchor"></div>', unsafe_allow_html=True)
    st.markdown("### Ajouter des panneaux solaires")
    st.caption("Enregistrez les nouveaux panneaux raccordes au reseau. Le secteur est limite a votre perimetre.")

    if auth.is_national(user):
        default = "tunisia"
        f = lambda s: region_label(s)
    else:
        default = opts[0]
        f = lambda s: hierarchy.scope_label(s if s != "nationale" else "tunisia")

    with st.form("add_panel_form"):
        pscope = st.selectbox("Secteur de raccordement", opts, index=opts.index(default) if default in opts else 0,
                              format_func=f, key="panel_scope")
        pn = st.number_input("Nombre de panneaux", min_value=1, max_value=100000,
                             value=10, step=1,
                             help="Combien de panneaux ont ete installes ?")
        pw = st.selectbox("Puissance d'un panneau", ["300 Wc", "400 Wc", "500 Wc", "550 Wc", "600 Wc"],
                          index=2, help="Puissance crete d'un seul panneau.")
        submit_panel = st.form_submit_button("Enregistrer les panneaux", type="primary")

    if submit_panel:
        scope = "tunisia" if pscope == "nationale" else pscope
        if not auth.is_scope_allowed(user, scope):
            st.error("Ce secteur est hors de votre perimetre.")
        elif scope == "tunisia":
            st.error("Selectionnez une region ou un district (le national n'est pas un secteur de raccordement).")
        else:
            total_kwc = registry.add_panels(scope, int(pn), int(pw.split()[0]))
            st.success(f"{int(pn)} panneau(x) de {pw} enregistres en "
                       f"{hierarchy.scope_label(scope)} -> **{total_kwc:,.2f} kWc** de capacite ajoutee.")

    st.markdown('<div id="section-panneaux-list" class="section-anchor"></div>', unsafe_allow_html=True)
    st.markdown("### Panneaux enregistres")

    if auth.is_national(user):
        prows = registry.list_panels()
    else:
        scope = auth.scope_of(user)
        prows = registry.list_panels(scope if "/" in scope else scope)

    if prows:
        dfp = pd.DataFrame(prows, columns=["Secteur", "Nb panneaux", "Puissance/panneau [Wc]", "Total [kWc]", "Ajoute le"])
        dfp["Secteur"] = dfp["Secteur"].map(lambda s: hierarchy.scope_label(s))
        st.dataframe(dfp, width="stretch", hide_index=True)
        st.metric("Capacite totale ajoutee", f"{dfp['Total [kWc]'].sum():,.2f} kWc")
    else:
        st.caption("Aucun panneau enregistre pour l'instant.")