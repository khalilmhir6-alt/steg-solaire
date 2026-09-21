"""
Registre local des nouvelles installations de panneaux solaires (SQLite).

Chaque enregistrement porte un « scope » : une région ('nord') ou un district
('nord/nabeul'). Un enregistrement au niveau district remonte automatiquement
au niveau région (même table, filtrage par préfixe) — rien n'est dupliqué.

Utilisé par l'onglet « Ajout de panneau » pour enregistrer les raccordements
effectués. Tout rôle (steg, admin de région, technicien) peut ajouter des
panneaux, mais uniquement dans son propre périmètre.
"""

import os
import sqlite3
from datetime import datetime

from config import DB_PATH


def _conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    c = sqlite3.connect(DB_PATH)
    cols = {r[1] for r in c.execute("PRAGMA table_info(panels)")}
    if not cols:
        c.execute(
            "CREATE TABLE panels ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT,"
            "scope TEXT NOT NULL,"
            "n_panels INTEGER NOT NULL,"
            "wc_per_panel INTEGER NOT NULL,"
            "total_kwc REAL NOT NULL,"
            "created_at TEXT NOT NULL)"
        )
    if "region" in cols or ("scope" not in cols and cols):
        # legacy schema had 'region TEXT NOT NULL' -> migrate to scope
        c.execute("ALTER TABLE panels RENAME TO panels_legacy")
        c.execute(
            "CREATE TABLE panels ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT,"
            "scope TEXT NOT NULL,"
            "n_panels INTEGER NOT NULL,"
            "wc_per_panel INTEGER NOT NULL,"
            "total_kwc REAL NOT NULL,"
            "created_at TEXT NOT NULL)"
        )
        c.execute(
            "INSERT INTO panels (scope, n_panels, wc_per_panel, total_kwc, created_at)"
            " SELECT region, n_panels, wc_per_panel, total_kwc, created_at"
            " FROM panels_legacy"
        )
        c.execute("DROP TABLE panels_legacy")
    c.commit()
    return c


def add_panels(scope, n_panels, wc_per_panel):
    total_kwc = round(int(n_panels) * int(wc_per_panel) / 1000.0, 3)
    c = _conn()
    c.execute(
        "INSERT INTO panels (scope, n_panels, wc_per_panel, total_kwc, created_at)"
        " VALUES (?,?,?,?,?)",
        (str(scope).strip().lower().lstrip("/"),
         int(n_panels), int(wc_per_panel), total_kwc,
         datetime.now().isoformat(timespec="seconds")),
    )
    c.commit()
    c.close()
    return total_kwc


def list_panels(scope=None):
    """Lignes de panneaux. Sans scope : tout. Avec un scope région ou
    région/district : les lignes du périmètre, district inclus dans sa région
    (roll-up par préfixe)."""
    c = _conn()
    if scope:
        prefix = str(scope).strip().lower().strip("/")
        rows = c.execute(
            "SELECT scope, n_panels, wc_per_panel, total_kwc, created_at"
            " FROM panels WHERE scope=? OR scope LIKE ? ORDER BY id DESC",
            (prefix, prefix + "/%"),
        ).fetchall()
    else:
        rows = c.execute(
            "SELECT scope, n_panels, wc_per_panel, total_kwc, created_at"
            " FROM panels ORDER BY id DESC"
        ).fetchall()
    c.close()
    return rows


def list_regions():
    """Ensemble des niveaux (régions + districts) présents dans le registre."""
    regions = {}
    for scope, _, _, _, _ in list_panels():
        parts = scope.split("/")
        regions.setdefault(parts[0], set()).add(scope)
    return {"regions": sorted(regions), "scopes": sorted({s for s in regions for s in regions[s]})}