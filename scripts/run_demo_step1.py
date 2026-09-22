# -*- coding: utf-8 -*-
"""RUN-1 : exécute scripts/demo_alertes.py AVEC le python STEG (numpy dispo),
puis affiche : code retour + stdout (démo STEP-1, preuve) + stderr (traceback
éventuel uniquement). Aucune écriture : la démo ne touche QUE stdout."""

import os
import subprocess
import sys

BASE = r"C:\STEG_Project"
PY = r"C:\Users\Khalil\AppData\Local\Programs\Python\Python312\python.exe"
DEMO = os.path.join(BASE, "scripts", "demo_alertes.py")

if not os.path.exists(PY):
    sys.exit("python STEG introuvable : %s" % PY)

# -- preuve que CE python a bien numpy (sinon l appel basculerait en ABORT) ----
chk = subprocess.run(
    [PY, "-c", "import numpy, pandas; print(numpy.__version__)"],
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace",
)
print("=== [1] python STEG (numpy/pandas) : %s ===" % (
    "OK  numpy %s" % chk.stdout.strip() if chk.returncode == 0 else "ECHEC numpy (!)"
))

# -- compilation des 2 fichiers STEP-1 (avec CE python) -------------------------
for rel in ("core/alerts.py", "scripts/demo_alertes.py"):
    r = subprocess.run(
        [PY, "-m", "py_compile", os.path.join(BASE, rel)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    print("   py_compile %-28s : %s" % (rel, "OK" if r.returncode == 0 else "ECHEC\n" + r.stderr[-300:]))

print()
print("=== [2] EXÉCUTION demo (sortie COMPLÈTE de STEP-1) ====")
r = subprocess.run([PY, DEMO], capture_output=True, text=True, encoding="utf-8", errors="replace")
print("   [code retour] = %s" % r.returncode)
if r.stdout:
    print(r.stdout)
if r.stderr:
    print("   --- stderr (ne retenir que si traceback) ---")
    print(r.stderr)
