"""
Assistant IA flottant : bouton circulaire en bas à droite, panneau overlay.

Rendu appelé en fin de app.py (après le footer, uniquement connecté).

Le panneau vit dans un @st.fragment : une question ne re-exécute QUE le
panneau — la page (dashboard, moteur, graphiques) reste intacte.
Cycle d'une question :
  idle -> (envoi) typing -> call -> idle, chaque transition par
  st.rerun(scope="fragment"). Pendant l'appel IA, la bulle « ● ● ● »
  animée reste à l'écran (l'état peint précédemment n'est pas effacé).
"""

import streamlit as st
from streamlit.runtime.scriptrunner_utils.script_run_context import get_script_run_ctx

from ai import agent
from ui.theme import STEG_BLUE, asset_uri

_LOGO = asset_uri("assets/steg_logo_mark.png", "image/png")

_CSS = """
<style>
/* barre de progression / indicateur global Streamlit : invisible */
[data-testid="stDecoration"] { display: none !important; }

/* ---- CLOSED : FAB circulaire bas-droite ---- */
[data-testid="stVerticalBlock"]:has(> [data-testid="stElementContainer"] .steg-ai-state.is-closed)
  [data-testid="stButton"] {
  position: fixed !important;
  bottom: 26px !important; right: 26px !important;
  z-index: 99999 !important;
  width: auto !important;
}
[data-testid="stVerticalBlock"]:has(> [data-testid="stElementContainer"] .steg-ai-state.is-closed)
  [data-testid="stButton"] button {
  width: 58px !important; height: 58px !important;
  min-height: 58px !important; padding: 0 !important;
  border-radius: 50% !important;
  background:
    url("__LOGO__") center / auto 22px no-repeat,
    radial-gradient(circle, #ffffff 0 16px, transparent 17px),
    linear-gradient(135deg, __BLUE__ 0%, #1b5ec1 100%) !important;
  border: 2px solid rgba(255,255,255,0.55) !important;
  color: transparent !important;
  font-size: 0 !important; line-height: 0 !important;
  box-shadow: 0 10px 28px rgba(11, 61, 145, 0.45) !important;
  display: flex !important; align-items: center !important;
  justify-content: center !important;
  transition: transform 0.15s ease, box-shadow 0.15s ease !important;
}
[data-testid="stVerticalBlock"]:has(> [data-testid="stElementContainer"] .steg-ai-state.is-closed)
  [data-testid="stButton"] button span,
[data-testid="stVerticalBlock"]:has(> [data-testid="stElementContainer"] .steg-ai-state.is-closed)
  [data-testid="stButton"] button p,
[data-testid="stVerticalBlock"]:has(> [data-testid="stElementContainer"] .steg-ai-state.is-closed)
  [data-testid="stButton"] button div {
  display: none !important;
}
[data-testid="stVerticalBlock"]:has(> [data-testid="stElementContainer"] .steg-ai-state.is-closed)
  [data-testid="stButton"] button:hover {
  transform: scale(1.06) !important;
  box-shadow: 0 14px 34px rgba(11, 61, 145, 0.55) !important;
}
[data-testid="stVerticalBlock"]:has(> [data-testid="stElementContainer"] .steg-ai-state.is-closed)
  [data-testid="stButton"] button:focus,
[data-testid="stVerticalBlock"]:has(> [data-testid="stElementContainer"] .steg-ai-state.is-closed)
  [data-testid="stButton"] button:focus-visible {
  outline: none !important; box-shadow: 0 10px 28px rgba(11,61,145,0.45) !important;
}

/* ---- OPEN : panneau overlay bas-droite ---- */
[data-testid="stVerticalBlock"]:has(> [data-testid="stElementContainer"] .steg-ai-state.is-open) {
  position: fixed !important;
  bottom: 26px !important; right: 26px !important;
  z-index: 99999 !important;
  width: min(400px, calc(100vw - 32px)) !important;
  max-width: 400px !important;
  max-height: min(72vh, 680px) !important;
  overflow-y: auto !important;
  background: #ffffff !important;
  border: 1px solid #d7deeb !important;
  border-radius: 18px !important;
  box-shadow: 0 18px 48px rgba(11, 61, 145, 0.28) !important;
  padding: 14px 16px 12px !important;
  margin: 0 !important;
  display: flex !important; flex-direction: column !important;
}
[data-testid="stVerticalBlock"]:has(> [data-testid="stElementContainer"] .steg-ai-state.is-open)
  > [data-testid="stElementContainer"]:has([data-testid="stChatInput"]) {
  margin-top: auto !important;
}
[data-testid="stVerticalBlock"]:has(> [data-testid="stElementContainer"] .steg-ai-state.is-open)
  h4,
[data-testid="stVerticalBlock"]:has(> [data-testid="stElementContainer"] .steg-ai-state.is-open)
  h3 {
  margin: 0 !important; padding: 0 !important;
  background: none !important; box-shadow: none !important;
  color: __BLUE__ !important; font-size: 1.05rem !important;
}
[data-testid="stChatMessage"] {
  background: transparent !important;
  border: none !important;
  border-radius: 0 !important;
  padding: 2px 0 !important;
  margin: 2px 0 !important;
  gap: 6px !important;
  box-shadow: none !important;
}
[data-testid="stChatMessage"] > img,
[data-testid="stChatMessage"] [data-testid="stChatMessageAvatarUser"],
[data-testid="stChatMessage"] [data-testid="stChatMessageAvatarCustom"],
[data-testid="stChatMessage"] [data-testid="stChatMessageAvatarAssistant"] {
  display: none !important;
}
[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] p {
  font-size: 0.8rem !important; line-height: 1.4 !important;
  color: #1f2a44 !important; margin: 0 !important;
}
[data-testid="stVerticalBlock"]:has(> [data-testid="stElementContainer"] .steg-ai-state.is-open)
  [data-testid="stChatInput"] {
  position: sticky !important; bottom: 0 !important;
  z-index: 5 !important;
  margin-top: auto !important;
  background: #ffffff !important;
  padding-top: 8px !important;
}
[data-testid="stVerticalBlock"]:has(> [data-testid="stElementContainer"] .steg-ai-state.is-open)
  [data-testid="stWidgetLabel"] {
  display: none !important;
}
.steg-ai-state { display: none !important; }

/* ---- bulle « réflexion » : trois points animés ---- */
.steg-ai-typing {
  display: inline-flex !important; gap: 5px !important;
  align-items: center !important; padding: 2px 4px !important;
}
.steg-ai-typing i {
  display: block !important; width: 8px !important; height: 8px !important;
  border-radius: 50% !important; background: #7f8aa5 !important;
  animation: steg-ai-bounce 1.15s infinite ease-in-out !important;
}
.steg-ai-typing i:nth-child(2) { animation-delay: 0.15s !important; }
.steg-ai-typing i:nth-child(3) { animation-delay: 0.30s !important; }
@keyframes steg-ai-bounce {
  0%, 80%, 100% { transform: translateY(0); opacity: 0.45; }
  40%           { transform: translateY(-5px); opacity: 1; }
}
</style>
""".replace("__BLUE__", STEG_BLUE).replace("__LOGO__", _LOGO)

_TYPING_HTML = '<span class="steg-ai-typing" aria-label="réflexion"><i></i><i></i><i></i></span>'


def _ensure_state():
    if "steg_ai_open" not in st.session_state:
        st.session_state["steg_ai_open"] = False
    if "steg_ai_messages" not in st.session_state:
        st.session_state["steg_ai_messages"] = []
    if "steg_ai_phase" not in st.session_state:
        # idle | typing (peindre les points) | call (appel IA en cours)
        st.session_state["steg_ai_phase"] = "idle"


def render(user=None):
    """Point d'entrée appelé par app.py (hors fragment : CSS injecté une fois)."""
    _ensure_state()
    st.markdown(_CSS, unsafe_allow_html=True)
    _panel()


def _rerun_panel():
    """Re-exécute le SEUL panneau si possible.

    scope="fragment" n'est autorisé que pendant un rerun de fragment
    (interaction widget -> pas de rechargement de la page). Pendant un
    run complet (chargement initial, tests), on retombe sur un rerun
    classique — sans boucle, car les widgets sont éphémères."""
    ctx = get_script_run_ctx()
    if ctx is not None and ctx.fragment_ids_this_run:
        st.rerun(scope="fragment")
    else:
        st.rerun()


@st.fragment
def _panel():
    """Fragment autonome : aucune re-exécution du dashboard ni du moteur."""
    user = st.session_state.get("user")
    if not user:
        return
    _ensure_state()

    is_open = st.session_state["steg_ai_open"]
    phase = st.session_state["steg_ai_phase"]
    state_cls = "is-open" if is_open else "is-closed"

    with st.container():
        st.markdown(
            f'<span class="steg-ai-state {state_cls}" aria-hidden="true"></span>',
            unsafe_allow_html=True,
        )

        if not is_open:
            if st.button("", key="steg_ai_fab", type="primary"):
                st.session_state["steg_ai_open"] = True
                _rerun_panel()
            return

        head = st.columns([1, 0.18])
        with head[0]:
            st.markdown(
                f'<div style="display:flex;align-items:center;gap:10px;">'
                f'<img src="{_LOGO}" alt="STEG" style="height:18px;width:auto;display:block;">'
                f'<span style="color:{STEG_BLUE};font-weight:700;font-size:1.05rem;">'
                f'Assistant STEG</span></div>',
                unsafe_allow_html=True,
            )
        with head[1]:
            if st.button("X", key="steg_ai_close", help="Fermer"):
                st.session_state["steg_ai_open"] = False
                _rerun_panel()

        msgs = st.session_state["steg_ai_messages"]

        # --- 1) rendu : historique de haut en bas ---
        for m in msgs:
            with st.chat_message(m["role"]):
                st.markdown(m["content"])

        if phase in ("typing", "call"):
            with st.chat_message("assistant"):
                st.markdown(_TYPING_HTML, unsafe_allow_html=True)

        if not agent.has_api_key():
            st.caption(
                "⚠ Clé API absente — renseignez `GROQ_API_KEY` dans "
                "`.streamlit/secrets.toml`."
            )

        # --- 2) run « typing » terminé -> run suivant : appel IA ---
        if phase == "typing":
            st.session_state["steg_ai_phase"] = "call"
            _rerun_panel()

        # --- 3) appel IA bloquant : l'écran garde la bulle « ● ● ● » ---
        if phase == "call":
            reply, _ = agent.run_turn(msgs, user)
            msgs.append({"role": "assistant", "content": reply})
            st.session_state["steg_ai_phase"] = "idle"
            _rerun_panel()

        # --- 4) saisie en bas du panneau ---
        prompt = st.chat_input("Posez votre question…", key="steg_ai_input")
        if prompt:
            prompt = prompt.strip()
            if prompt and phase == "idle":
                msgs.append({"role": "user", "content": prompt})
                st.session_state["steg_ai_phase"] = "typing"
                _rerun_panel()
