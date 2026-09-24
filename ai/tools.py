"""
Fonctions exposées à l'assistant IA (lecture/écriture base de données uniquement).

Périmètre : chaque outil applique la règle de l'homme aveugle via ui.auth —
l'agent ne voit et ne modifie que le scope de l'utilisateur connecté.
"""

from ui import auth, registry, hierarchy

ALLOWED_WC = {300, 400, 500, 550, 600}
MAX_PANEL_ROWS = 100


def _ok(data):
    return {"ok": True, "data": data}


def _err(msg):
    return {"ok": False, "error": msg}


def _panel_row(r):
    return {
        "scope": r[0],
        "n_panels": r[1],
        "wc_per_panel": r[2],
        "total_kwc": r[3],
        "created_at": r[4],
    }


def _resolve_scope(user, scope, default_all_national=False):
    """Normalize + authorize a scope argument. Returns (scope, None) or (None, error)."""
    if scope is None or str(scope).strip() == "":
        if default_all_national and auth.is_national(user):
            return None, None  # None => no filter (national)
        s = auth.scope_of(user)
        if s == "tunisia" and default_all_national:
            return None, None
        return s, None
    s = str(scope).strip().lower().replace("\\", "/").strip("/")
    if s == "tunisia" or s == "nationale":
        s = "tunisia"
    if not hierarchy.is_valid_scope(s):
        return None, f"Périmètre inconnu : '{scope}'. Formats acceptés : région "
        "(ex. nord) ou région/district (ex. nord/nabeul)."
    if not auth.is_scope_allowed(user, s):
        return None, f"Accès refusé : '{s}' est hors de votre périmètre."
    return s, None


# ---------------------------------------------------------------------------
# Outils
# ---------------------------------------------------------------------------

def list_panels(user, scope=None):
    s, err = _resolve_scope(user, scope, default_all_national=True)
    if err:
        return _err(err)
    rows = registry.list_panels(s)
    data = [_panel_row(r) for r in rows[:MAX_PANEL_ROWS]]
    return _ok({
        "scope": s,
        "n_rows": len(rows),
        "rows": data,
        "truncated": len(rows) > MAX_PANEL_ROWS,
        "total_kwc": round(sum(float(r[3] or 0) for r in rows), 3),
    })


def add_panel(user, scope, n_panels, wc_per_panel):
    if scope is None or str(scope).strip() == "":
        return _err("scope est requis (région ou région/district, ex. nord/nabeul).")
    s = str(scope).strip().lower().replace("\\", "/").strip("/")
    if s in ("tunisia", "nationale"):
        return _err("Le national n'est pas un secteur de raccordement : "
                    "choisissez une région ou un district.")
    if not hierarchy.is_valid_scope(s):
        return _err(f"Périmètre inconnu : '{scope}'. Formats : nord | nord/nabeul.")
    if not auth.is_scope_allowed(user, s):
        return _err(f"Accès refusé : '{s}' est hors de votre périmètre.")
    try:
        n = int(n_panels)
        wc = int(wc_per_panel)
    except (TypeError, ValueError):
        return _err("n_panels et wc_per_panel doivent être des entiers.")
    if n < 1 or n > 100000:
        return _err("n_panels doit être entre 1 et 100000.")
    if wc not in ALLOWED_WC:
        return _err(f"wc_per_panel doit être l'une des valeurs : "
                    f"{sorted(ALLOWED_WC)} Wc.")
    total_kwc = registry.add_panels(s, n, wc)
    return _ok({
        "scope": s,
        "scope_label": hierarchy.scope_label(s),
        "n_panels": n,
        "wc_per_panel": wc,
        "total_kwc_added": total_kwc,
    })


def get_forecast(user, scope=None):
    import json
    import os
    from config import RESULT_PATH

    if not os.path.exists(RESULT_PATH):
        return _err("Aucune prévision enregistrée. Ouvrez le Dashboard pour la calculer.")
    with open(RESULT_PATH, encoding="utf-8") as f:
        payload = json.load(f)
    summary = payload.get("summary") or {}
    stored = summary.get("scope")
    if stored and not auth.is_scope_allowed(user, stored):
        return _err(f"La dernière prévision porte sur '{stored}', hors de votre périmètre.")
    if scope:
        s, err = _resolve_scope(user, scope)
        if err:
            return _err(err)
        if s and stored and s != stored:
            return _err(f"La prévision enregistrée concerne '{stored}', pas '{s}'. "
                        "Seule la dernière prévision calculée est disponible en lecture.")
    alerts = payload.get("alerts") or []
    return _ok({
        "scope": stored,
        "summary": summary,
        "n_alerts": len(alerts),
        "alerts": alerts[:10],
        "meta": payload.get("meta"),
    })


def get_alerts(user, scope=None):
    from core import alerts as alerts_core
    from config import DEFAULT_SCENARIO

    s, err = _resolve_scope(user, scope)
    if err:
        return _err(err)
    target = s or auth.scope_of(user)
    state = alerts_core.evaluate_scope_alerts(target, DEFAULT_SCENARIO)

    ramp = []
    import json
    import os
    from config import RESULT_PATH
    if os.path.exists(RESULT_PATH):
        with open(RESULT_PATH, encoding="utf-8") as f:
            payload = json.load(f)
        stored = (payload.get("summary") or {}).get("scope")
        if stored and auth.is_scope_allowed(user, stored) and (not s or s == stored):
            ramp = payload.get("alerts") or []

    return _ok({
        "scope": target,
        "production_vs_prevision": state,
        "ramp_alerts": ramp[:10],
        "n_ramp_alerts": len(ramp),
    })


def get_capacity(user, scope=None):
    s, err = _resolve_scope(user, scope)
    if err:
        return _err(err)
    target = s or auth.scope_of(user)
    mw = hierarchy.scope_capacity_mw(target)
    return _ok({
        "scope": target,
        "scope_label": hierarchy.scope_label(target),
        "installed_mw": round(float(mw), 3),
    })


# ---------------------------------------------------------------------------
# Schémas OpenAI-style (function calling)
# ---------------------------------------------------------------------------

_SCOPE_PROP = {
    "type": "string",
    "description": "Périmètre optionnel en minuscules : région (ex. nord) ou "
                   "région/district (ex. nord/nabeul). Défaut : périmètre de l'utilisateur.",
}

SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "list_panels",
            "description": "Liste les panneaux solaires enregistrés dans la base (lecture).",
            "parameters": {
                "type": "object",
                "properties": {"scope": _SCOPE_PROP},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_panel",
            "description": "Enregistre de nouveaux panneaux raccordés (écriture en base). "
                           "Confirmer d'abord avec l'utilisateur sauf demande explicite.",
            "parameters": {
                "type": "object",
                "properties": {
                    "scope": {
                        "type": "string",
                        "description": "Secteur de raccordement : région ou région/district "
                                       "(le national est refusé). Ex. nord/nabeul.",
                    },
                    "n_panels": {
                        "type": "integer",
                        "description": "Nombre de panneaux (1 à 100000).",
                    },
                    "wc_per_panel": {
                        "type": "integer",
                        "description": "Puissance crête d'un panneau en Wc : "
                                       "300, 400, 500, 550 ou 600.",
                    },
                },
                "required": ["scope", "n_panels", "wc_per_panel"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_forecast",
            "description": "Lit la dernière prévision enregistrée (résumé, pic, énergie, alertes de rampe).",
            "parameters": {
                "type": "object",
                "properties": {"scope": _SCOPE_PROP},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_alerts",
            "description": "Lit l'état des alertes (production vs prévision, pas STEP-1) "
                           "et les alertes de rampe pour un périmètre.",
            "parameters": {
                "type": "object",
                "properties": {"scope": _SCOPE_PROP},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_capacity",
            "description": "Lit la capacité installée (MW) d'un périmètre, panneaux enregistrés inclus.",
            "parameters": {
                "type": "object",
                "properties": {"scope": _SCOPE_PROP},
                "required": [],
            },
        },
    },
]

_DISPATCH = {
    "list_panels": list_panels,
    "add_panel": add_panel,
    "get_forecast": get_forecast,
    "get_alerts": get_alerts,
    "get_capacity": get_capacity,
}


def execute(name, args, user):
    """Exécute un appel d'outil. Retourne toujours un dict JSON-serialisable."""
    fn = _DISPATCH.get(name)
    if fn is None:
        return _err(f"Outil inconnu : {name}")
    if not isinstance(args, dict):
        args = {}
    try:
        return fn(user, **args)
    except TypeError as e:
        return _err(f"Arguments invalides pour {name} : {e}")
    except Exception as e:  # never leak internals to the model
        return _err(f"Erreur interne pendant {name} : {type(e).__name__}")
