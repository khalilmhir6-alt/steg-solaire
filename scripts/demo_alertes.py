# -*- coding: utf-8 -*-
"""Copie CORRECTE et COMPLETE de scripts/demo_alertes.py (STEP-1, headless,
PUR) — regime par _cfg.DEMO_DEVIATION + importlib.reload CORE.alerts (aucune
ecriture, jamais). Tout le reste CI-DESSOUS est le contenu REEL du fichier.
"""

import importlib
import io
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

import config as _cfg
from core import alerts as _alerts_mod


def _set_demo_regime(deviation: float | None) -> None:
    """Bascule DEMO_DEVIATION EN MÉMOIRE SEULEMENT (aucune écriture).

    alerts.py fait `from config import DEMO_DEVIATION` (import direct, donc la
    valeur est capturée à l'import du module). Pour changer de régime SANS rien
    écrire ni toucher core/alerts.py, on affecte _cfg.DEMO_DEVIATION puis on
    RELOAD le module (importlib.reload) : son import direct repart sur la
    nouvelle valeur. Rien n'est jamais écrit dans le log, jamais dans config.
    """
    global evaluate_scope_alerts

    _cfg.DEMO_DEVIATION = deviation
    reloaded = importlib.reload(_alerts_mod)
    from core.alerts import evaluate_scope_alerts as _fresh

    evaluate_scope_alerts = _fresh


def _list_regions() -> list[str]:
    try:
        from ui.hierarchy import list_regions

        return list(list_regions())
    except Exception:
        return []


def _demo_scopes() -> list[str]:
    return (
        ["tunisia"]
        + _list_regions()
        + ["nord/nabeul", "nord/absent_feuil"]
    )


def _fmt(r: dict) -> str:
    return (
        "   %-16s  %-9s  %8s  %6s/%4s  %-8s  %-8s  %6s  %-6s  %-4s  %-4s  %-4s"
        % (
            r.get("scope", ""),
            r.get("scope_level", ""),
            ("%.1f MW" % r.get("installed_mw", 0.0)),
            ("%s%%" % r.get("threshold_yellow_pct", 0.0)),
            ("%s%%" % r.get("threshold_red_pct", 0.0)),
            r.get("current_state", ""),
            r.get("outlook_state", ""),
            ("%.1f%%" % r.get("deviation_pct", 0.0)),
            "sous" if r.get("direction_under") else ("sur" if r.get("direction_over") else "="),
            "nuit" if r.get("night") else "jour",
            "demo" if r.get("demo") else "---",
            "ABSENT" if not r.get("available") else "OK",
        )
    )


def main() -> None:
    regimes = [None, 0.15, 0.30]
    out = io.StringIO()
    out.write("=== Demo STEP-1 : alertes production-vs-prevision (PAS d'ecriture) ===\n")
    out.write(
        "   %-16s  %-9s  %8s  %6s/%4s  %-8s  %-8s  %6s  %-6s  %-4s  %-4s  %-4s\n"
        % ("scope", "niveau", "inst.", "jaune", "rouge", "courant", "outlook", "ecart", "direc", "nuit", "demo", "dispo")
    )
    out.write("   " + "-" * 105 + "\n")

    unavailable = []

    for regime in regimes:
        out.write("\n--- Regime DEMO_DEVIATION = %s ---\n" % (
            "OFF (None)" if regime is None else "%.2f" % regime
        ))
        _set_demo_regime(regime)
        for scope in _demo_scopes():
            r = evaluate_scope_alerts(scope)

            if not r.get("available"):
                unavailable.append(scope)
            out.write(_fmt(r) + "\n")

    # ---- Résumé : scopes indisponibles + POURQUOI ---------------------------
    out.write("\n=== RÉSUMÉ : scopes INDISPONIBLES + pourquoi ===\n")
    for scope in sorted(set(unavailable)):
        log_present = os.path.exists(
            os.path.join(BASE, "data", "forecast_actual.jsonl")
        )
        if not log_present:
            why = "log absent"
        else:
            why = "0 ligne pour ce scope dans le log (jaune/rouge inaccessibles)"
        out.write("   %-16s : %s\n" % (scope, why))

    # ---- Note STEP-2 (la question posée) ------------------------------------
    out.write(
        "\n=== NOTE — quels scopes sont-ils loggés, et quand ? ===\n"
        "   Le capture forecast_actual.jsonl n'est rempli QUE quand core/engine"
        ".build_forecast() est appelé pour un scope précis (le panneau "
        "\"Prévision vs Réel\" de la page concernée déclenche build_forecast ; "
        "source=\"simulated\" = jumeau simulé ancré sur le GHI STEG réel + "
        "géométrie). Donc AUJOURD'HUI uniquement les scopes dont une PAGE du "
        "dashboard est ouverte/consultée sont évalués en continu : national "
        "(tunisia) + les régions/districts des pages réellement visitées.\n"
        "   Il N'y a PAS d'évaluation périodique de TOUS les scopes (7 régions "
        "+ districts) hors pages : un scope jamais visité n'a AUCUNE ligne -> "
        "alertes = \"unavailable\" (vert forcé, jaune/rouge inaccessibles).\n"
        "   Pour STEP-2, l'option propre est un évaluateur horaire (APS) qui "
        "appelle build_forecast() + evaluate_scope_alerts() pour CHAQUE scope "
        "de la hiérarchie (national + 7 régions + 63 districts) à chaque pas, "
        "et écrit SA LIGNE dans le même JSONL — rendant tous les scopes "
        "évaluables en continu. C'est un changement de core/engine.py + un "
        "scheduler, hors périmètre STEP-1 (qui ne touche que core/alerts.py "
        "en lecture pure).\n"
    )

    print(out.getvalue())


if __name__ == "__main__":
    main()
