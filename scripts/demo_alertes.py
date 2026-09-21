# -*- coding: utf-8 -*-
"""Demo STEP-1 : alertes production vs prévision (headless, PUR ▶ stdout).

NE TOUCHE JAMAIS au log forecast_actual.jsonl ni à config.py sur disque.
La bascule de régime passe UNIQUEMENT par config.DEMO_DEVIATION EN MÉMOIRE +
importlib.reload(core.alerts) (car core.alerts importe DEMO_DEVIATION par
import direct → la valeur est re-capturée au reload). Rien n'est écrit, nulle
part, JAMAIS. Ce script n'écrit QUE sur stdout.
"""

from __future__ import annotations

import importlib
import io
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

import config as _cfg
import core.alerts as _alerts_mod
from core.alerts import evaluate_scope_alerts

# ---------------------------------------------------------------------------
# Regimes de démonstration : DEMO_DEVIATION en MÉMOIRE SEULEMENT.
# core.alerts fait `from config import DEMO_DEVIATION` (import direct, figé à
# l'import du module). Pour basculer le régime SANS rien écrire ni relire le
# log, on affecte config.DEMO_DEVIATION puis on RECHARGE le module
# (importlib.reload) : son import direct reparte sur la nouvelle valeur.
# Toute la bascule vit en mémoire ; jamais une écriture.
# ---------------------------------------------------------------------------


def _set_demo_regime(deviation: float | None) -> None:
    global evaluate_scope_alerts
    _cfg.DEMO_DEVIATION = deviation
    global _alerts_mod
    _alerts_mod = importlib.reload(_alerts_mod)
    from core.alerts import evaluate_scope_alerts


def _list_regions() -> list[str]:
    try:
        from ui.hierarchy import list_regions

        return list(list_regions())
    except Exception:
        return []


def _demo_scopes() -> list[str]:
    """tunisia (national) + les 7 régions EXACTES de la source unique +
    2 districts feuilles : nord/nabeul (peuplé dans le log) + nord/absent
    (SANS AUCUNE ligne → prouve "unavailable")."""
    return ["tunisia"] + _list_regions() + ["nord/nabeul", "nord/absent"]


def _fmt(r: dict) -> str:
    level = r.get("scope_level", "district")
    inst = r.get("installed_mw")
    th_y = r.get("threshold_yellow_pct")
    th_r = r.get("threshold_red_pct")
    return (
        "   %-16s  %-9s  %8s  %6s/%4s  %-8s  %-8s  %6s  %-6s  %-4s  %-4s  %-4s"
        % (
            r.get("scope", ""),
            level,
            ("%.1f MW" % inst) if inst else "---",
            ("%s%%" % th_y) if th_y is not None else "--",
            ("%s%%" % th_r) if th_r is not None else "--",
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
    out.write("   " + "-" * 101 + "\n")

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

    # ---- Resume : scopes indisponibles + POURQUOI ----------------------------
    out.write("\n=== RESUME : scopes INDISPONIBLES + pourquoi ===\n")
    for scope in sorted(set(unavailable)):
        log_present = os.path.exists(
            os.path.join(BASE, "data", "forecast_actual.jsonl")
        )
        if not log_present:
            why = "log absent"
        else:
            why = "0 ligne pour ce scope dans le log (jaune/rouge inaccessibles)"
        out.write("   %-16s : %s\n" % (scope, why))

    # ---- NOTE STEP-2 (la question posee : quels scopes sont logges, quand ?) --
    out.write(
        "\n=== NOTE — quels scopes sont-ils logges, et quand ? ===\n"
        "   Le log forecast_actual.jsonl n'est rempli QUE quand core/engine.py"
        ".build_forecast() est appelé pour un scope (le panneau \"Prévision vs "
        "Réel\" de la page concernée déclenche build_forecast ; source="
        "\"simulated\" = jumeau simulé ancré sur le GHI STEG réel + géométrie)."
        "\n   Donc PRODUCTION : uniquement les scopes dont une PAGE du "
        "dashboard est ouverte/consultée sont évalués en continu (national = "
        "tunisia + les régions/districts des pages réellement visitées). "
        "AUCUNE évaluation périodique de tous les scopes (7 régions + "
        "districts) hors pages : un scope jamais visité n'a AUCUNE ligne -> "
        "alertes \"unavailable\" (vert forcé, jaune/rouge inaccessibles).\n"
        "   Pour STEP-2, l'option propre est un évaluateur horaire (APS) qui "
        "appelle build_forecast() + evaluate_scope_alerts() pour CHAQUE scope "
        "de la hiérarchie (national + 7 régions + districts) à chaque pas et "
        "écrit SA LIGNE dans le même JSONL — rendant tous les scopes "
        "évaluables. C'est un changement de core/engine.py + un scheduler, "
        "hors périmètre STEP-1.\n"
    )

    print(out.getvalue())


if __name__ == "__main__":
    main()
