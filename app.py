"""
STEG Solaire — Plateforme de prevision & pilotage de l'injection PV
Multi-page app navigated with st.navigation / st.Page.
Page switches happen in place (same browser tab, no raw links / new windows).

Run:  streamlit run app.py
"""

import streamlit as st
from ui import auth
from ui.theme import render_css, render_nav, steg_loading_css, render_footer
from pages import dashboard, alertes, admin, panneaux, parametres

st.set_page_config(page_title="STEG Solaire", page_icon="assets/steg_favicon.png", layout="wide")

render_css()
steg_loading_css()

# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
auth.init()


def login_ui():
    from ui.theme import asset_uri

    # Login-only styling: full-page blue gradient + one centered white card.
    # Scoped to the presence of .steg-login so no other page is affected.
    st.markdown('<div class="steg-login" aria-hidden="true"></div>', unsafe_allow_html=True)
    st.markdown("""
    <style>
    [data-testid="stAppViewContainer"]:has(.steg-login) {
      background: linear-gradient(135deg, #0b3d91 0%, #1b5ec1 100%) !important;
      min-height: 100vh !important;
      display: flex !important; align-items: center !important;
      justify-content: center !important;
    }
    [data-testid="stAppViewContainer"]:has(.steg-login) [data-testid="stMain"],
    [data-testid="stAppViewContainer"]:has(.steg-login) [data-testid="stAppViewBlockContainer"] {
      min-height: 100vh !important; width: 100% !important;
      display: flex !important; align-items: center !important;
      justify-content: center !important;
    }
    [data-testid="stAppViewContainer"]:has(.steg-login) [data-testid="block-container"],
    [data-testid="stAppViewContainer"]:has(.steg-login) [data-testid="stMainBlockContainer"] {
      width: 100% !important; max-width: 500px !important;
      margin-left: auto !important; margin-right: auto !important;
      padding: 0 16px !important;
    }
    [data-testid="stAppViewContainer"]:has(.steg-login) [data-testid="stForm"] {
      background: #ffffff !important; width: 100% !important;
      padding: 36px 40px 32px !important; border-radius: 16px !important;
      box-shadow: 0 16px 44px rgba(0, 0, 0, 0.28) !important;
    }
    [data-testid="stAppViewContainer"]:has(.steg-login) h2 {
      color: #1f2a44 !important; text-align: center;
      margin: 12px 0 8px !important; font-size: 1.6rem !important;
    }
    [data-testid="stAppViewContainer"]:has(.steg-login) [data-testid="stMarkdownContainer"]
      a[data-testid="stHeaderActionElements"] {
      display: none !important;
    }
    [data-testid="stAppViewContainer"]:has(.steg-login) [data-testid="stCaptionContainer"] p,
    [data-testid="stAppViewContainer"]:has(.steg-login) [data-testid="stCaptionContainer"] div {
      color: #5b6478 !important; text-align: center;
      font-size: 0.85rem !important; line-height: 1.4 !important;
      margin-bottom: 20px !important;
    }
    [data-testid="stAppViewContainer"]:has(.steg-login) [data-testid="stWidgetLabel"] p {
      color: #1f2a44 !important; font-size: 0.9rem !important;
      margin-bottom: 6px !important;
    }
    [data-testid="stAppViewContainer"]:has(.steg-login) [data-testid="stTextInputField"] {
      background: #ffffff !important; border: 1px solid #c9d1e0 !important;
      border-radius: 8px !important; width: 100% !important;
      height: 44px !important; padding-right: 40px !important;
      position: relative !important;
      box-sizing: border-box !important;
    }
    [data-testid="stAppViewContainer"]:has(.steg-login) [data-testid="stTextInputField"]:focus-within {
      border: 1px solid #0b3d91 !important;
    }
    [data-testid="stAppViewContainer"]:has(.steg-login) [data-testid="stTextInputField"] input,
    [data-testid="stAppViewContainer"]:has(.steg-login) [data-testid="stTextInputBase"] input,
    [data-testid="stAppViewContainer"]:has(.steg-login) input {
      background: #ffffff !important; color: #1f2a44 !important;
      -webkit-text-fill-color: #1f2a44 !important;
      caret-color: #1f2a44 !important;
      font-weight: 500 !important; border-radius: 8px !important;
      width: 100% !important; height: 44px !important;
      padding: 0 12px !important; font-size: 0.95rem !important;
      box-shadow: none !important; border: none !important;
      box-sizing: border-box !important; opacity: 1 !important;
    }
    [data-testid="stAppViewContainer"]:has(.steg-login) input::placeholder {
      color: #8a94a8 !important; -webkit-text-fill-color: #8a94a8 !important;
      opacity: 1 !important;
    }
    [data-testid="stAppViewContainer"]:has(.steg-login) [data-testid="stTextInputField"] button {
      background: #ffffff !important; border: none !important;
      position: absolute !important; right: 4px !important; top: 50% !important;
      transform: translateY(-50%) !important;
      height: 40px !important; width: 36px !important;
      display: flex !important; align-items: center !important;
      justify-content: center !important;
    }
    [data-testid="stAppViewContainer"]:has(.steg-login)
      [data-testid="stTextInputField"] button svg,
    [data-testid="stAppViewContainer"]:has(.steg-login)
      [data-testid="stTextInputField"] button span {
      fill: #5b6478 !important; color: #5b6478 !important;
    }
    [data-testid="stAppViewContainer"]:has(.steg-login)
      div:has(> [data-testid="stBaseButton-primary"]) {
      width: 100% !important; margin-top: 22px !important;
    }
    [data-testid="stAppViewContainer"]:has(.steg-login) [data-testid="stBaseButton-primary"] {
      width: 100% !important; height: 46px !important;
      background: linear-gradient(135deg, #0b3d91 0%, #1b5ec1 100%) !important;
      border: 1px solid #1b5ec1 !important; color: #ffffff !important;
      font-weight: 700 !important; font-size: 0.95rem !important;
      text-align: center !important; border-radius: 8px !important;
      padding: 0 1.25rem !important; box-shadow: none !important;
      box-sizing: border-box !important;
    }
    [data-testid="stAppViewContainer"]:has(.steg-login) [data-testid="stBaseButton-primary"]:hover {
      background: linear-gradient(135deg, #08295f 0%, #0b3d91 100%) !important;
    }
    [data-testid="stAppViewContainer"]:has(.steg-login) [data-testid="stBaseButton-primary"]:focus {
      outline: none !important; box-shadow: none !important;
    }
    [data-testid="stAppViewContainer"]:has(.steg-login) .steg-login-logo {
      display: flex; justify-content: center;
    }
    [data-testid="stAppViewContainer"]:has(.steg-login) .steg-login-logo img {
      width: auto; height: 90px; object-fit: contain;
      image-rendering: auto;
      image-rendering: crisp-edges;
      image-rendering: -webkit-optimize-contrast;
      -webkit-backface-visibility: hidden;
      backface-visibility: hidden;
      transform: translateZ(0);
    }
    </style>
    """, unsafe_allow_html=True)

    logo = asset_uri("assets/steg_logo.png", "image/png")
    with st.form("login"):
        st.markdown(
            f'<div class="steg-login-logo"><img src="{logo}" alt="STEG"></div>',
            unsafe_allow_html=True)
        st.markdown("## STEG Solaire")
        st.caption("Plateforme de prévision PV & pilotage de l'injection")
        u = st.text_input("Identifiant", value="steg")
        p = st.text_input("Mot de passe", type="password", value="solaire2026")
        ok = st.form_submit_button("Se connecter", type="primary")

    if ok:
        user = auth.verify(u, p)
        if user:
            st.session_state["user"] = user
            st.session_state["global_scope"] = auth.scope_of(user)
            st.rerun()
        else:
            st.error("Identifiants invalides.")


if "user" not in st.session_state:
    login_ui()
    st.stop()

user = st.session_state["user"]
ROLE = user["role"]

# ---------------------------------------------------------------------------
# Pages - st.navigation / st.Page switch the visible content in the same tab
# ---------------------------------------------------------------------------
PAGES = [
    st.Page(dashboard.render, title="Dashboard", icon=":material/dashboard:",
            url_path="dashboard", default=True),
    st.Page(alertes.render, title="Alertes", icon=":material/notifications_active:",
            url_path="alertes"),
    st.Page(admin.render, title="Administrateur", icon=":material/admin_panel_settings:",
            url_path="admin"),
    st.Page(panneaux.render, title="Ajout de panneau", icon=":material/solar_power:",
            url_path="panneaux"),
]
if ROLE == "technicien":
    PAGES = [p for p in PAGES if p is not PAGES[2]]

PAGE_PARAMETRES = st.Page(parametres.render, title="Paramètres",
                          icon=":material/settings:", url_path="parametres")

pg = st.navigation(PAGES + [PAGE_PARAMETRES], position="hidden")

# Load saved defaults for the logged-in user.
_settings = auth.get_settings(user.get("username", ""))
if _settings.get("default_region") and "global_scope" not in st.session_state:
    st.session_state["global_scope"] = _settings["default_region"]
if _settings.get("default_horizon") and "global_horizon" not in st.session_state:
    st.session_state["global_horizon"] = _settings["default_horizon"]

# One unified top bar: brand left, page tabs center, gear icon far right.
top_cols = st.columns([1, 1, 1, 1, 1, 0.5])
with top_cols[0]:
    st.markdown(render_nav(), unsafe_allow_html=True)
for col, page in zip(top_cols[1:5], PAGES):
    with col:
        active = pg is page
        if st.button(page.title, key=f"nav_{page.url_path}",
                     type="primary" if active else "tertiary", width="stretch"):
            if not active:
                st.switch_page(page)
with top_cols[5]:
    if st.button("", key="nav_parametres", type="tertiary",
                 help="Paramètres"):
        st.switch_page(PAGE_PARAMETRES)

pg.run()

st.markdown(render_footer(), unsafe_allow_html=True)

from ui.assistant import render as render_assistant
render_assistant(user)