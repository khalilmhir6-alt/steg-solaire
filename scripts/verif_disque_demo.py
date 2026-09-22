# -*- coding: utf-8 -*-
"""Contrôle réel du DISQUE : core/alerts.py existe, compile, et contient
evaluate_scope_alerts ; scripts/demo_alertes.py existe et compile ; la
réécriture anti-UnboundLocal est effectivement POSÉE (global + importlib).
Aucune écriture. Sortie 100% texte (à coller)."""

import io
import os
import subprocess
import sys

base = r"C:\STEG_Project"


def coller() -> str:
    out = []
    out.append("=== [1] core/alerts.py : état disque + py_compile ===")
    pa = os.path.join(base, "core", "alerts.py")
    exists = os.path.exists(pa)
    out.append("   existe : %s" % ("OUI" if exists else "ABSENT"))
    if exists:
        src = io.open(pa, "r", encoding="utf-8").read()
        out.append("   octets : %d  lignes : %d" % (len(src.encode("utf-8")), src.count(chr(10))))
        has_eval = "def evaluate_scope_alerts(" in src
        out.append("   def evaluate_scope_alerts( : %s" % ("OUI" if has_eval else "ABSENT"))
        has_demo = "DEMO_DEVIATION" in src
        out.append("   DEMO_DEVIATION (import direct config) : %s" % ("OUI" if has_demo else "ABSENT"))
        try:
            import py_compile

            py_compile.compile(pa, doraise=True)
            out.append("   py_compile : OK")
        except Exception as e:
            out.append("   py_compile : ECHEC -> %s" % str(e).splitlines()[-1][:90])

    out.append("")
    out.append("=== [2] scripts/demo_alertes.py : état disque + py_compile ===")
    pd = os.path.join(base, "scripts", "demo_alertes.py")
    exists_d = os.path.exists(pd)
    out.append("   existe : %s" % ("OUI" if exists_d else "ABSENT"))
    if exists_d:
        srcd = io.open(pd, "r", encoding="utf-8").read()
        has_set = "def _set_demo_regime" in srcd
        has_glob = "global evaluate_scope_alerts" in srcd
        has_reload = "importlib.reload" in srcd or "core.alerts" in srcd
        out.append("   _set_demo_regime : %s" % ("OUI" if has_set else "ABSENT"))
        out.append("   global (anti UnboundLocal) : %s" % ("OUI" if has_glob else "ABSENT"))
        out.append("   reload/alerts-rebond : %s" % ("OUI" if has_reload else "ABSENT"))
        try:
            import py_compile

            py_compile.compile(pd, doraise=True)
            out.append("   py_compile(scripts/demo_alertes.py) : OK")
        except Exception as e:
            out.append("   py_compile : ECHEC -> %s" % str(e).splitlines()[-1][:90])

    return chr(10).join(out)


if __name__ == "__main__":
    print(coller())
