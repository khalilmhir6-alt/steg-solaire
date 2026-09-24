"""
Moteur de conversation de l'assistant : Groq API (compatible OpenAI,
function calling) + system prompt prompts/assistant_system.md.

Clé API : variable d'environnement GROQ_API_KEY ou .streamlit/secrets.toml.
Aucune dépendance ajoutée (requests déjà utilisée par l'app).
"""

import json
import os
from pathlib import Path

import requests

from config import BASE_DIR
from ui import auth
from ai import tools as ai_tools

PROMPT_PATH = os.path.join(BASE_DIR, "prompts", "assistant_system.md")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-20b")
MAX_TOOL_ROUNDS = 6
MAX_HISTORY = 30
REQUEST_TIMEOUT = 60


def has_api_key():
    return bool(_api_key())


def _api_key():
    key = (os.environ.get("GROQ_API_KEY") or "").strip()
    if key and not key.lower().startswith("your-"):  # ignore placeholder values
        return key
    try:
        import streamlit as st
        key = st.secrets.get("GROQ_API_KEY", "")
        if isinstance(key, str) and key.strip() and not key.strip().lower().startswith("your-"):
            return key.strip()
    except Exception:
        pass
    return ""


def _load_prompt():
    try:
        return Path(PROMPT_PATH).read_text(encoding="utf-8")
    except OSError:
        return ("Tu es l'assistant intégré à l'application STEG Solaire. "
                "Réponds en français.")


def build_system_prompt(user):
    """System prompt + contexte de session (jamais stocké dans l'historique)."""
    from ui import hierarchy

    scope = auth.scope_of(user)
    parts = [
        _load_prompt(),
        "",
        "CONTEXTE SESSION",
        f"- Utilisateur : {user.get('username')} "
        f"({user.get('full_name') or user.get('role')})",
        f"- Rôle : {user.get('role')}",
        f"- Périmètre : {scope} ({hierarchy.scope_label(scope)})",
        "- Les fonctions appliquent déjà ce périmètre : une requête hors scope "
        "renverra une erreur d'accès — ne contourne jamais cette règle.",
    ]
    return "\n".join(parts)


def _post(payload, key):
    resp = requests.post(
        GROQ_URL,
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=REQUEST_TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()


def run_turn(history, user):
    """Un tour : appel Groq + exécution des tool_calls jusqu'à réponse finale.

    history : liste [{"role","content"}] (sans system, tool_calls exclus).
    Retourne (reply_text, history_maj_sans_system).
    """
    key = _api_key()
    if not key:
        return ("Clé API manquante : renseignez GROQ_API_KEY dans "
                ".streamlit/secrets.toml ou dans l'environnement."), list(history)

    msgs = [{"role": "system", "content": build_system_prompt(user)}]
    msgs.extend(history[-MAX_HISTORY:])
    convo = list(msgs)

    try:
        for _ in range(MAX_TOOL_ROUNDS):
            data = _post({
                "model": GROQ_MODEL,
                "messages": convo,
                "tools": ai_tools.SCHEMAS,
                "tool_choice": "auto",
                "temperature": 0.2,
            }, key)
            msg = data["choices"][0]["message"]
            convo.append(msg)

            tool_calls = msg.get("tool_calls") or []
            if not tool_calls:
                reply = (msg.get("content") or "").strip()
                if not reply:
                    reply = "Désolé, je n'ai pas de réponse à produire pour l'instant."
                return reply, _strip_to_history(convo)

            for call in tool_calls:
                fn = call.get("function") or {}
                name = fn.get("name") or ""
                try:
                    args = json.loads(fn.get("arguments") or "{}")
                except json.JSONDecodeError:
                    args = {}
                result = ai_tools.execute(name, args, user)
                convo.append({
                    "role": "tool",
                    "tool_call_id": call.get("id"),
                    "content": json.dumps(result, ensure_ascii=False),
                })

        return ("J'ai atteint la limite d'actions pour ce message. "
                "Pouvez-vous reformuler ou découper votre demande ?"), \
            _strip_to_history(convo)
    except requests.HTTPError as e:
        status = e.response.status_code if e.response is not None else "?"
        return f"Erreur du service IA (HTTP {status}). Réessayez plus tard.", \
            _strip_to_history(convo)
    except requests.RequestException:
        return ("Impossible de joindre le service IA (réseau). "
                "Vérifiez votre connexion puis réessayez."), list(history)
    except Exception:
        return "Une erreur interne est survenue lors de l'appel IA.", list(history)


def _strip_to_history(convo):
    """Conserve uniquement user/assistant (avec texte) pour le stockage session."""
    out = []
    for m in convo:
        if m.get("role") == "system":
            continue
        if m.get("role") == "tool":
            continue
        if m.get("tool_calls"):
            # assistant turn with tool calls: keep only textual content if any
            content = (m.get("content") or "").strip()
            if content:
                out.append({"role": "assistant", "content": content})
            continue
        if m.get("role") in ("user", "assistant") and (m.get("content") or "").strip():
            out.append({"role": m["role"], "content": m["content"]})
    return out
