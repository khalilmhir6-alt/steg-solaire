# -*- coding: utf-8 -*-
"""RUN-1 : exécute demo_alertes.py avec le python STEG (celui qui a numpy),
puis affiche le code retour. Pur sous-processus : rien d'autre."""
import os
import subprocess
import sys

PY = r"C:\Users\Khalil\AppData\Local\Programs\Python\Python312\python.exe"
DEMO = r"C:\STEG_Project\scripts\demo_alertes.py"

if not os.path.exists(PY):
    sys.exit("python STEG introuvable : %s" % PY)

print("=== [RUN-1] demo_alertes.py avec le python STEG ===")
print("   python : %s" % PY)
r = subprocess.run(
    [PY, DEMO],
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace",
)
print("   [code retour] = %s" % r.returncode)
if r.returncode:
    print("\n--- stderr (traceback complet à analyser si non-numpy) ---")
    print(r.stderr)
print("\n--- stdout (À COLLER — la preuve STEP-1) ---")
print(r.stdout)
