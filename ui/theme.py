"""
Shared STEG theme: constants, CSS, helpers.
Import from here in app.py and page files.
"""

import base64
import os
import streamlit as st
from ui import hierarchy

STEG_BLUE = "#0b3d91"
STEG_BLUE_DARK = "#08295f"
STEG_RED = "#d7263d"
STEG_AMBER = "#f0a202"
GRID = "#8c8c8c"

HORIZON_OPTIONS = [
    ("15 min", 0.25), ("30 min", 0.5), ("45 min", 0.75),
    ("1 heure", 1.0), ("2 heures", 2.0), ("3 heures", 3.0),
    ("4 heures", 4.0), ("6 heures", 6.0), ("12 heures", 12.0),
    ("18 heures", 18.0), ("24 heures", 24.0), ("2 jours", 48.0),
    ("3 jours", 72.0), ("4 jours", 96.0), ("5 jours", 120.0),
    ("6 jours", 144.0), ("1 semaine", 168.0),
]

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def asset_uri(rel, mime):
    with open(os.path.join(APP_DIR, rel), "rb") as f:
        return "data:%s;base64,%s" % (mime, base64.b64encode(f.read()).decode("utf-8"))


def region_label(slug):
    if not slug or slug == "tunisia":
        return "Tout le pays"
    if slug in hierarchy.REGION_LABELS:
        return hierarchy.REGION_LABELS[slug]
    return hierarchy.scope_label(slug)


def render_css():
    gear_uri = asset_uri("assets/settings-gear.svg", "image/svg+xml")
    st.markdown(f"""
<style>
:root {{
  --steg-blue: {STEG_BLUE};
  --steg-blue-dark: {STEG_BLUE_DARK};
  --steg-red: {STEG_RED};
}}
html, body {{
  background: #f4f7fc !important;
  margin: 0 !important;
  padding: 0 !important;
  padding-top: 0 !important;
}}
[data-testid="stAppViewContainer"], [data-testid="stMain"] {{
  background: transparent !important;
  margin-top: 0 !important; padding-top: 0 !important;
}}
[data-testid="stAppViewBlockContainer"],
[data-testid="stMainBlockContainer"],
[data-testid="block-container"] {{
  margin-top: 0 !important; padding-top: 0 !important;
}}
[data-testid="stAppViewContainer"] {{
  background: #f4f7fc !important;
}}
[data-testid="stAppViewContainer"]:has(.steg-login),
html:has(.steg-login), body:has(.steg-login),
[data-testid="stAppViewContainer"]:has(.steg-login) [data-testid="stMain"] {{
  background: linear-gradient(135deg, {STEG_BLUE} 0%, #1b5ec1 100%) !important;
}}
[data-testid="stHeader"] {{ background: transparent; display: none !important; height: 0 !important; }}
[data-testid="stElementContainer"]:has(> [data-testid="stMarkdownContainer"] > style) {{
  display: none !important;
}}
h1, h2, h3, h4 {{ color: {STEG_BLUE}; }}
.stMarkdown h3 {{
  background: linear-gradient(135deg, {STEG_BLUE} 0%, #1b5ec1 100%);
  color: #ffffff !important; padding: 10px 18px; border-radius: 10px;
  border-left: none; margin: 0.4rem 0 0.7rem 0 !important;
  box-shadow: 0 2px 8px rgba(11, 61, 145, 0.18);
}}
button[kind="primary"], [data-testid="stBaseButton-primary"] {{
  background: linear-gradient(135deg, {STEG_BLUE} 0%, #1b5ec1 100%) !important;
  border: 1px solid #1b5ec1 !important; color: #ffffff !important;
  font-weight: 700 !important; border-radius: 10px !important;
  padding: 0.45rem 1.25rem !important;
  box-shadow: 0 2px 8px rgba(11, 61, 145, 0.18);
}}
button[kind="primary"]:hover, [data-testid="stBaseButton-primary"]:hover {{
  background: linear-gradient(135deg, {STEG_BLUE_DARK} 0%, {STEG_BLUE} 100%) !important;
}}
[data-testid="stMetric"] {{
  background: linear-gradient(135deg, {STEG_BLUE} 0%, #1b5ec1 100%);
  border: none; border-radius: 12px; padding: 14px;
  box-shadow: 0 2px 8px rgba(11, 61, 145, 0.18);
}}
[data-testid="stMetricLabel"], [data-testid="stMetricValue"], [data-testid="stMetricDelta"] {{
  color: #ffffff !important;
}}
[data-testid="stMetricLabel"], [data-testid="stMetricDelta"] {{ opacity: 0.92; }}
.stAlert, .stSuccess {{ border-radius: 10px; }}
[data-testid="stWidgetLabel"] {{ color: #1f2a44; font-weight: 600; }}
[data-testid="stWidgetDescription"] p, [data-testid="stCaptionContainer"] p {{ color: #5b6478; }}
[data-testid="stBaseButton-secondary"] {{
  background: transparent !important; border: 1px solid {STEG_BLUE} !important;
  color: {STEG_BLUE} !important; border-radius: 10px !important;
  font-weight: 600; padding: 0.45rem 1.25rem !important;
}}
[data-testid="stBaseButton-secondary"]:hover {{
  background: rgba(11, 61, 145, 0.08) !important;
}}
[data-testid="stMainBlockContainer"] .stHorizontalBlock:has(.steg-topbar-brand) {{
  position: sticky !important; top: 0 !important; z-index: 9999;
  align-items: center;
  background: linear-gradient(135deg, {STEG_BLUE} 0%, #1b5ec1 100%);
  padding: 0 24px; height: 68px;
  box-shadow: 0 2px 8px rgba(11,61,145,0.25);
  margin-top: 0 !important; margin-bottom: 0 !important;
  padding-top: 0 !important;
  margin-left: calc(-50vw + 50%) !important;
  margin-right: calc(-50vw + 50%) !important;
  width: 100vw !important;
  max-width: 100vw !important;
  border-radius: 0 !important;
}}
.stHorizontalBlock:has(.steg-topbar-brand) > [data-testid="stColumn"]:last-child {{
  justify-content: flex-end;
}}
[data-testid="stMainBlockContainer"] .stHorizontalBlock:has(.steg-topbar-brand)
  > [data-testid="stColumn"]:last-child [data-testid="stBaseButton-tertiary"] {{
  background: transparent url("{gear_uri}") center / 22px 22px no-repeat !important;
  border: none !important;
  border-radius: 0 !important;
  width: 40px !important; height: 40px !important;
  min-height: 40px !important;
  padding: 0 !important;
  margin: 0 !important;
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
  color: transparent !important;
  font-size: 0 !important;
  box-shadow: none !important;
}}
[data-testid="stMainBlockContainer"] .stHorizontalBlock:has(.steg-topbar-brand)
  > [data-testid="stColumn"]:last-child [data-testid="stBaseButton-tertiary"] span,
[data-testid="stMainBlockContainer"] .stHorizontalBlock:has(.steg-topbar-brand)
  > [data-testid="stColumn"]:last-child [data-testid="stBaseButton-tertiary"] div,
[data-testid="stMainBlockContainer"] .stHorizontalBlock:has(.steg-topbar-brand)
  > [data-testid="stColumn"]:last-child [data-testid="stBaseButton-tertiary"] p {{
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
  color: transparent !important;
  font-size: 0 !important;
}}
[data-testid="stMainBlockContainer"] .stHorizontalBlock:has(.steg-topbar-brand)
  > [data-testid="stColumn"]:last-child [data-testid="stBaseButton-tertiary"] span,
[data-testid="stMainBlockContainer"] .stHorizontalBlock:has(.steg-topbar-brand)
  > [data-testid="stColumn"]:last-child [data-testid="stBaseButton-tertiary"] div,
[data-testid="stMainBlockContainer"] .stHorizontalBlock:has(.steg-topbar-brand)
  > [data-testid="stColumn"]:last-child [data-testid="stBaseButton-tertiary"] p {{
  background: none !important;
  border: none !important;
  width: auto !important; height: auto !important;
  min-height: 0 !important;
  color: transparent !important;
  font-size: 0 !important;
}}
[data-testid="stMainBlockContainer"] .stHorizontalBlock:has(.steg-topbar-brand)
  > [data-testid="stColumn"]:last-child [data-testid="stBaseButton-tertiary"] svg {{
  display: none !important;
}}
[data-testid="stMainBlockContainer"] .stHorizontalBlock:has(.steg-topbar-brand)
  > [data-testid="stColumn"]:last-child [data-testid="stBaseButton-tertiary"]:hover {{
  background: transparent url("{gear_uri}") center / 22px 22px no-repeat !important;
  border: none !important;
  box-shadow: none !important;
}}
[data-testid="stMainBlockContainer"] .stHorizontalBlock:has(.steg-topbar-brand) [data-testid="stColumn"] {{
  display: flex; align-items: center;
}}
[data-testid="stMainBlockContainer"] .stHorizontalBlock:has(.steg-topbar-brand) [data-testid="stElementContainer"],
[data-testid="stMainBlockContainer"] .stHorizontalBlock:has(.steg-topbar-brand) [data-testid="stMarkdownContainer"] {{
  margin-top: 0 !important; margin-bottom: 0 !important;
}}
[data-testid="stMainBlockContainer"] .stHorizontalBlock:has(.steg-topbar-brand) [data-testid="stMarkdownContainer"] {{
  display: flex !important; align-items: center !important;
}}
[data-testid="stMainBlockContainer"] .stHorizontalBlock:has(.steg-topbar-brand) [data-testid="stBaseButton-tertiary"],
[data-testid="stMainBlockContainer"] .stHorizontalBlock:has(.steg-topbar-brand) [data-testid="stBaseButton-tertiary"] span,
[data-testid="stMainBlockContainer"] .stHorizontalBlock:has(.steg-topbar-brand) [data-testid="stBaseButton-tertiary"] div,
[data-testid="stMainBlockContainer"] .stHorizontalBlock:has(.steg-topbar-brand) [data-testid="stBaseButton-tertiary"] p {{
  color: #ffffff !important; font-weight: 700 !important;
  font-size: 19px !important;
}}
[data-testid="stMainBlockContainer"] .stHorizontalBlock:has(.steg-topbar-brand) [data-testid="stBaseButton-tertiary"]:hover {{
  background: rgba(255,255,255,0.15) !important;
}}
[data-testid="stMainBlockContainer"] .stHorizontalBlock:has(.steg-topbar-brand) [data-testid="stBaseButton-primary"] {{
  background: #ffffff !important; border: 1px solid #ffffff !important;
  border-radius: 999px !important; box-shadow: 0 2px 6px rgba(0,0,0,0.18);
}}
[data-testid="stMainBlockContainer"] .stHorizontalBlock:has(.steg-topbar-brand) [data-testid="stBaseButton-primary"],
[data-testid="stMainBlockContainer"] .stHorizontalBlock:has(.steg-topbar-brand) [data-testid="stBaseButton-primary"] span,
[data-testid="stMainBlockContainer"] .stHorizontalBlock:has(.steg-topbar-brand) [data-testid="stBaseButton-primary"] div,
[data-testid="stMainBlockContainer"] .stHorizontalBlock:has(.steg-topbar-brand) [data-testid="stBaseButton-primary"] p {{
  color: {STEG_BLUE} !important; font-weight: 700 !important;
  font-size: 19px !important;
}}
[data-testid="stTextInputField"], [data-testid="stNumberInputField"],
  [data-testid="stTextAreaField"], [data-testid="stMultiSelectBase"] {{
    background: #ffffff !important; border: 1px solid #c9d1e0 !important;
    border-radius: 8px !important; position: relative !important;
    box-sizing: border-box !important;
  }}
  [data-testid="stTextInputField"], [data-testid="stNumberInputField"] {{
    height: 44px !important;
  }}
  [data-testid="stTextInputField"]:focus-within,
  [data-testid="stNumberInputField"]:focus-within,
  [data-testid="stTextAreaField"]:focus-within,
  [data-testid="stMultiSelectBase"]:focus-within {{
    border: 1px solid {STEG_BLUE} !important;
  }}
  [data-testid="stTextInputField"] input, [data-testid="stNumberInputField"] input {{
    background: #ffffff !important; color: #1f2a44 !important;
    -webkit-text-fill-color: #1f2a44 !important;
    caret-color: #1f2a44 !important;
    font-weight: 500 !important; border: none !important;
    box-shadow: none !important; border-radius: 8px !important;
    width: 100% !important; height: 44px !important;
    padding: 0 12px !important; box-sizing: border-box !important;
    opacity: 1 !important;
  }}
  [data-testid="stTextArea"] textarea {{
    background: #ffffff !important; color: #1f2a44 !important;
    border: 1px solid #c9d1e0 !important; border-radius: 8px !important;
    box-shadow: none !important;
  }}
  [data-testid="stTextArea"] textarea:focus {{
    border: 1px solid {STEG_BLUE} !important;
  }}
  [data-testid="stTextInputField"] input::placeholder,
  [data-testid="stNumberInputField"] input::placeholder,
  [data-testid="stTextArea"] textarea::placeholder {{
    color: #8a94a8 !important; font-weight: 400 !important;
  }}
  [data-testid="stTextInputField"] button {{
    background: #ffffff !important; border: none !important;
    position: absolute !important; right: 4px !important;
    top: 50% !important; transform: translateY(-50%) !important;
    height: 40px !important; width: 36px !important;
    display: flex !important; align-items: center !important;
    justify-content: center !important;
  }}
  [data-testid="stTextInputField"] button svg,
  [data-testid="stTextInputField"] button span {{
    fill: #5b6478 !important; color: #5b6478 !important;
  }}
  [data-testid="stNumberInputStepUp"], [data-testid="stNumberInputStepDown"] {{
    background: #ffffff !important;
  }}
  [data-testid="stNumberInputStepUp"] svg, [data-testid="stNumberInputStepDown"] svg {{
    fill: {STEG_BLUE} !important;
  }}
  [data-testid="stSelectbox"] [role="combobox"],
  [data-testid="stSelectbox"] div:has(> [role="combobox"]),
  [data-testid="stMultiSelectBase"] div:has(> [role="combobox"]) {{
    background: #ffffff !important; color: #1f2a44 !important;
    font-weight: 500 !important; border: 1px solid #c9d1e0 !important;
    border-radius: 8px !important; min-height: 44px !important;
    box-sizing: border-box !important;
  }}
  [data-testid="stSelectbox"] [aria-label="Open"],
  [data-testid="stMultiSelectBase"] [aria-label="Open"] {{
    background: transparent !important;
  }}
  [data-testid="stSelectbox"] [aria-label="Open"] svg,
  [data-testid="stMultiSelectBase"] [aria-label="Open"] svg {{
    fill: {STEG_BLUE} !important;
  }}
  ul[role="listbox"], [data-baseweb="popover"] [role="listbox"],
  [data-baseweb="popover"] [role="option"] {{
    background: #ffffff !important; color: #1f2a44 !important;
  }}
  [data-baseweb="popover"] [role="option"]:hover {{
    background: #e3edff !important;
  }}
  [data-baseweb="popover"] input:not([type="checkbox"]) {{
    background: #ffffff !important; color: #1f2a44 !important;
  }}
[data-testid="stDataFrame"] {{
  border: 1px solid #dbe4f2; border-radius: 10px; overflow: hidden;
}}
[data-testid="stHeader"] {{ display: none !important; height: 0 !important; min-height: 0 !important; padding: 0 !important; margin: 0 !important; }}
[data-testid="stToolbar"] {{ display: none !important; }}
#MainMenu {{ visibility: hidden; }}
[data-testid="stAppViewBlockContainer"] {{ padding-top: 0 !important; margin-top: 0 !important; }}
[data-testid="stMainBlockContainer"] {{ padding-top: 0 !important; margin-top: 0 !important; }}
[data-testid="block-container"] {{ padding-top: 0 !important; margin-top: 0 !important; }}
[data-testid="stMain"] {{ padding-top: 0 !important; margin-top: 0 !important; }}
[data-testid="stMainBlockContainer"] > *:first-child {{
  margin-top: 0 !important; padding-top: 0 !important;
}}
.stApp, #root {{
  margin: 0 !important; padding-top: 0 !important;
}}
.steg-topbar-brand {{
  display: flex; align-items: center; gap: 10px;
  line-height: 1;
}}
.steg-topbar-brand img {{
  display: block; height: 30px; flex-shrink: 0;
}}
.steg-topbar-brand span {{
  display: inline-flex; align-items: center; line-height: 1;
  font-size: 19px; font-weight: 700; color: #fff; letter-spacing: .3px;
  white-space: nowrap;
}}

.steg-subnav {{
  display: flex; justify-content: center; gap: 8px; padding: 12px 24px;
  background: #f0f4fa; border-bottom: 1px solid #e3e8f0;
}}
.steg-subnav a {{
  text-decoration: none; font-weight: 600; font-size: 14px;
  padding: 10px 28px; border-radius: 8px;
  background: #fff; color: {STEG_BLUE};
  border: 1px solid #d0d9e8; transition: all .15s;
}}
.steg-subnav a:hover {{
  background: {STEG_BLUE}; color: #fff; border-color: {STEG_BLUE};
  box-shadow: 0 2px 6px rgba(11,61,145,0.20);
}}
.section-anchor {{ scroll-margin-top: 60px; }}
.steg-footer {{
  text-align: center; color: #5b6478;
  font-size: 0.75rem; line-height: 1.4;
  padding: 12px 0 20px 0;
  border-top: 1px solid #e3e8f0;
  margin-top: 2.5rem;
}}
.steg-footer .steg-footer-version {{ font-weight: 600; color: {STEG_BLUE}; }}
</style>
""", unsafe_allow_html=True)


def steg_loading_css():
    """White splash: logo gleams over a full-screen white card.

    - Visible on every app view (not on the login page), minimum ~2.6 s,
      then fades out automatically.
    - While a spinner is running (dashboard building), held fully visible
      for as long as the spinner lasts — even if that exceeds the delay.
    - Questions in the assistant never trigger it (fragment reruns only).
    """
    logo = asset_uri("assets/steg_logo_mark.png", "image/png")
    st.markdown(f"""
<style>
[data-testid="stSpinner"] {{
  position: fixed !important; inset: 0 !important; z-index: 9999 !important;
  background: #ffffff !important;
  animation: none !important;
}}
[data-testid="stSpinner"] svg,
[data-testid="stSpinner"] [data-testid="stStatusWidget"],
[data-testid="stSpinner"] .stSpinner-bubble,
[data-testid="stSpinner"] p {{
  display: none !important;
}}
.steg-splash {{
  position: fixed !important; inset: 0 !important; z-index: 10000 !important;
  display: none !important;
  flex-direction: column !important;
  align-items: center !important;
  justify-content: center !important;
  background: #ffffff !important;
  margin: 0 !important; padding: 0 !important;
  text-align: center !important;
  pointer-events: none !important;
  animation: steg-splash-out 0.45s ease 2.6s forwards;
}}
/* App views (hors login) : la page de chargement s'affiche au chargement. */
html:not(:has(.steg-login)) .steg-splash {{
  display: flex !important;
}}
/* Tant que le contenu se construit, le splash reste entièrement visible. */
html:has([data-testid="stSpinner"]) .steg-splash {{
  display: flex !important;
  opacity: 1 !important;
  visibility: visible !important;
}}
@keyframes steg-splash-out {{
  to {{ opacity: 0; visibility: hidden; }}
}}
.steg-splash img {{
  display: block !important;
  width: 64px !important;
  height: auto !important;
  max-width: 40vw !important;
  margin: 0 !important;
  padding: 0 !important;
  border: 0 !important;
  image-rendering: auto !important;
  opacity: 1;
  animation: steg-gleam 1.6s ease-in-out infinite;
}}
@keyframes steg-gleam {{
  0% {{
    opacity: 0.4;
    filter: brightness(0.95);
    transform: scale(0.98);
  }}
  45% {{
    opacity: 1;
    filter: brightness(1.2)
      drop-shadow(0 0 14px rgba(255, 255, 255, 0.95))
      drop-shadow(0 0 22px rgba(11, 61, 145, 0.45));
    transform: scale(1);
  }}
  70% {{
    opacity: 1;
    filter: brightness(1.08)
      drop-shadow(0 0 10px rgba(255, 255, 255, 0.7))
      drop-shadow(0 0 14px rgba(11, 61, 145, 0.3));
    transform: scale(1);
  }}
  100% {{
    opacity: 1;
    filter: none;
    transform: scale(1);
  }}
}}
</style>
<div class="steg-splash" aria-hidden="true">
  <img src="{logo}" alt="STEG" width="64" height="112">
</div>
""", unsafe_allow_html=True)


def render_nav():
    brand = asset_uri("assets/steg_favicon.png", "image/png")
    return f"""
<div class="steg-topbar-brand">
  <img src="{brand}" alt="STEG">
  <span>STEG Solaire</span>
</div>
"""


APP_VERSION = "1.0"


def render_footer():
    """Minimal internal footer: version + current date. Nothing else."""
    import datetime
    today = datetime.date.today().strftime("%d/%m/%Y")
    return f"""
<div class="steg-footer">
  <span class="steg-footer-version">STEG Solaire v{APP_VERSION}</span>
  &nbsp;&nbsp;·&nbsp;&nbsp; Mis à jour le {today}
</div>
"""


def render_filters():
    """Render shared Region/Horizon filters, restricted to the logged-in
    user's permitted scopes (blind-man rule). Values persist in session_state."""
    from ui import auth
    user = st.session_state.get("user") or {}
    allow_national = auth.is_national(user) or not user
    scopes = auth.allowed_scopes(user) if user else ["tunisia"] + hierarchy.list_regions()

    def fmt(s):
        if s in ("tunisia", "nationale"):
            return "Tunisia (nationale)"
        return hierarchy.scope_label(s)

    fc1, fc2 = st.columns(2)
    with fc1:
        options = scopes if scopes else ["tunisia"]
        # a technician cannot change its perimeter: show locked value
        if user and user.get("role") == auth.ROLE_TECHNICIAN:
            st.selectbox("Region / perimetre", options,
                         format_func=fmt, key="global_scope",
                         help="Votre perimetre est fixe (technicien).")
        else:
            st.selectbox("Region / perimetre", options,
                         format_func=fmt, key="global_scope")
    with fc2:
        st.selectbox(
            "Horizon de prevision",
            [l for l, _ in HORIZON_OPTIONS],
            index=0,
            key="global_horizon",
        )


def get_scope():
    from ui import auth
    user = st.session_state.get("user")
    scope = st.session_state.get("global_scope", "tunisia")
    if user and not auth.is_scope_allowed(user, scope):
        return auth.scope_of(user)
    return scope


def get_horizon_hours():
    label = st.session_state.get("global_horizon", "15 min")
    return dict(HORIZON_OPTIONS)[label]


def get_horizon_label():
    return st.session_state.get("global_horizon", "15 min")


def fig_theme(fig, height, margin=None, **extra):
    fig.update_layout(
        template="plotly_white",
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
        font=dict(family="Segoe UI, Arial, sans-serif", color="#1e2a3a", size=12),
        height=height,
        margin=margin or dict(l=10, r=10, t=30, b=10),
        xaxis=dict(gridcolor="#e3e8f0", zerolinecolor="#c9d3e4"),
        yaxis=dict(gridcolor="#e3e8f0", zerolinecolor="#c9d3e4"),
    )
    if extra:
        fig.update_layout(**extra)
    return fig
