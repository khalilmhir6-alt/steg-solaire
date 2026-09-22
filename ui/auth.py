"""
Credential store (users.db, SQLite) for the demonstration app.

Roles:
  - steg           : national supervisor (full access, manages admins).
  - admin_<region> : region supervisor (works only inside its region).
  - technicien_*   : district technician (fixed perimeter, cannot widen).

Passwords are salted + SHA-256. This is a demo vessel - production DSOs
would integrate their corporate SSO/LDAP. The "solar panel" enrolment is
open to every role (the access difference is only about scope + user mgmt).
"""

import hashlib
import os
import secrets
import sqlite3

from config import DB_PATH, DISTRICTS, REGION_LABELS

_SEED_USER = "steg"
_SEED_PASS = "solaire2026"
_NATIONAL = "tunisia"

ROLE_NATIONAL = "national"
ROLE_ADMIN = "dispatcher"
ROLE_TECHNICIAN = "technicien"


def admin_username(region):
    """Conventional username for a region's administrator, e.g. 'admin_tunis'."""
    if not region or region == _NATIONAL:
        return _SEED_USER
    return f"admin_{region}"


def technician_username(district):
    """Conventional username for a district's technician, e.g. 'technicien_nabeul'."""
    return f"technicien_{district}"


def _conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    c = sqlite3.connect(DB_PATH)
    c.execute(
        "CREATE TABLE IF NOT EXISTS users ("
        "username TEXT PRIMARY KEY, role TEXT NOT NULL, salt TEXT NOT NULL,"
        "pwd_hash TEXT NOT NULL, full_name TEXT, region TEXT, scope TEXT)"
    )
    for col in ("region", "scope"):
        try:
            c.execute(f"ALTER TABLE users ADD COLUMN {col} TEXT")
        except sqlite3.OperationalError:
            pass
    c.commit()
    return c


def _hash(password, salt):
    return hashlib.sha256((salt + password).encode("utf-8")).hexdigest()


def init():
    # Seed canonical accounts ONLY on a fresh database. Existing databases
    # (incl. any manually deleted users) are left untouched so that deletions
    # made through the admin UI persist across restarts. A one-time backfill
    # only repairs missing scope/region metadata on canonical usernames.
    c = _conn()
    count = c.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    c.close()
    if count == 0:
        seed_all()
    else:
        _backfill_canonical_metadata()


def seed_all(overwrite=False):
    """Create the canonical fleet: national + one admin per region + one
    technician per district (idempotent: never touches existing users)."""
    c = _conn()
    if c.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
        add_user(_SEED_USER, _SEED_PASS, ROLE_NATIONAL,
                 "Superviseur STEG", region=_NATIONAL, scope=_NATIONAL)
    c.close()
    seed_region_admins(overwrite=overwrite)
    seed_region_technicians(overwrite=overwrite)


def _backfill_canonical_metadata():
    """Repair metadata (region/scope) of canonical users created before the
    scope column existed, without adding or removing any account."""
    for region in REGION_LABELS:
        _touch_canonical(admin_username(region), ROLE_ADMIN,
                         f"Admin {REGION_LABELS[region].title()}", region, region)
    for district, (region, label, _) in DISTRICTS.items():
        _touch_canonical(technician_username(district), ROLE_TECHNICIAN,
                         f"Technicien {label.title()}", region,
                         f"{region}/{district}")
    _touch_canonical(_SEED_USER, ROLE_NATIONAL, "Superviseur STEG",
                     _NATIONAL, _NATIONAL)


def _touch_canonical(username, role, full_name, region, scope):
    c = _conn()
    row = c.execute(
        "SELECT role, region, scope FROM users WHERE username=?", (username,)
    ).fetchone()
    if row:
        cur_role, cur_region, cur_scope = row
        new_role = role if cur_role != ROLE_TECHNICIAN else cur_role
        new_region = region if cur_region is None else cur_region
        new_scope = scope if cur_scope is None else cur_scope
        if (new_role, new_region, new_scope) != (cur_role, cur_region, cur_scope):
            c.execute("UPDATE users SET role=?, region=?, scope=? WHERE username=?",
                      (new_role, new_region, new_scope, username))
    c.commit()
    c.close()


def seed_region_admins(overwrite=False):
    """Create (or reset) one supervisor per region, username admin_<region>.
    Only steg can create admins through the UI; this just guarantees the
    canonical fleet exists for the demo."""
    created = []
    for region in REGION_LABELS:
        username = admin_username(region)
        full_name = f"Admin {REGION_LABELS[region].title()}"
        if _seed_missing_or_overwrite(username, overwrite):
            add_user(username, _SEED_PASS, ROLE_ADMIN, full_name,
                     region=region, scope=region)
            created.append(username)
    return created


def seed_region_technicians(overwrite=False):
    """Create (or reset) one technician per district of the hierarchy,
    username technicien_<district>, so every sub-region has a technician
    ready to test. Region admins can still add more through the admin UI."""
    created = []
    for district, (region, label, _) in sorted(DISTRICTS.items()):
        username = technician_username(district)
        full_name = f"Technicien {label.title()}"
        if _seed_missing_or_overwrite(username, overwrite):
            add_user(username, _SEED_PASS, ROLE_TECHNICIAN, full_name,
                     region=region, scope=f"{region}/{district}")
            created.append(username)
    return created


def _seed_missing_or_overwrite(username, overwrite):
    if overwrite:
        return True
    c = _conn()
    exists = c.execute("SELECT 1 FROM users WHERE username=?", (username,)).fetchone()
    c.close()
    return not exists


def add_user(username, password, role="operator", full_name=None,
             region=None, scope=None):
    c = _conn()
    salt = secrets.token_hex(8)
    scope = scope or region
    c.execute(
        "INSERT OR REPLACE INTO users (username, role, salt, pwd_hash, full_name,"
        " region, scope) VALUES (?,?,?,?,?,?,?)",
        (username, role, salt, _hash(password, salt), full_name, region, scope),
    )
    c.commit()
    c.close()


def delete_user(username):
    c = _conn()
    c.execute("DELETE FROM users WHERE username=?", (username,))
    c.commit()
    c.close()


def list_users():
    c = _conn()
    rows = c.execute(
        "SELECT username, role, full_name, region, scope FROM users ORDER BY username"
    ).fetchall()
    c.close()
    return rows


def verify(username, password):
    c = _conn()
    row = c.execute(
        "SELECT role, salt, pwd_hash, full_name, region, scope FROM users WHERE username=?",
        (username,),
    ).fetchone()
    c.close()
    if row is None:
        return None
    role, salt, expected, full_name, region, scope = row
    if secrets.compare_digest(_hash(password, salt), expected):
        return {"username": username, "role": role, "full_name": full_name,
                "region": region or _NATIONAL, "scope": scope or region or _NATIONAL}
    return None


def region_of(user):
    """Top-level region a user is bound to ('tunisia' for the national account)."""
    if not user:
        return _NATIONAL
    return (user.get("region") or _NATIONAL)


def scope_of(user):
    """Exact perimeter of a user: 'tunisia' | region | region/district."""
    if not user:
        return _NATIONAL
    return (user.get("scope") or user.get("region") or _NATIONAL)


def is_national(user):
    return region_of(user) == _NATIONAL or user.get("role") == ROLE_NATIONAL


def allowed_scopes(user):
    """Scopes a user may open, respecting the 'blind man' rule: each level can
    only ever see what sits below it."""
    if is_national(user):
        return [_NATIONAL] + list(REGION_LABELS)
    region = region_of(user)
    if user.get("role") == ROLE_TECHNICIAN:
        return [scope_of(user)]
    return [region] + [f"{region}/{d}" for d in _districts(region)]


def _districts(region):
    return sorted(d for d, (reg, _, _) in DISTRICTS.items() if reg == region)


def is_scope_allowed(user, scope):
    """True when <scope> (region slug or region/district path) is inside the
    user's permitted perimeter."""
    parts = str(scope or "").replace("\\", "/").strip("/").split("/")
    top = parts[0].strip().lower() if parts and parts[0].strip() else _NATIONAL
    if top == _NATIONAL and len(parts) == 1:
        return is_national(user)
    if top == _NATIONAL:
        return False
    allowed = allowed_scopes(user)
    if scope in allowed:
        return True
    return top in allowed


def can_create(user, role, target_scope):
    """Blind-man creation rights, by level."""
    if not user:
        return False
    if role == ROLE_ADMIN:
        # only the national supervisor creates region admins
        return is_national(user)
    if role == ROLE_TECHNICIAN:
        if is_national(user):
            return True
        if user.get("role") != ROLE_ADMIN:
            return False
        return is_scope_allowed(user, target_scope)
    return False


def can_delete(user, target_user):
    """Blind-man deletion rights, by level."""
    if not user or not target_user:
        return False
    if is_national(user):
        return True
    if user.get("role") != ROLE_ADMIN:
        return False
    # a region admin can only delete what sits under its own region
    if target_user.get("role") != ROLE_TECHNICIAN:
        return False
    return region_of(target_user) == region_of(user)


def update_password(username, new_password):
    c = _conn()
    salt = secrets.token_hex(8)
    c.execute("UPDATE users SET salt=?, pwd_hash=? WHERE username=?",
              (salt, _hash(new_password, salt), username))
    c.commit()
    c.close()


# ---------------------------------------------------------------------------
# User settings (default view + alert threshold overrides)
# ---------------------------------------------------------------------------

def _ensure_settings_table(c):
    c.execute(
        "CREATE TABLE IF NOT EXISTS user_settings ("
        "username TEXT PRIMARY KEY,"
        " default_region TEXT,"
        " default_horizon TEXT,"
        " ramp_yellow REAL,"
        " ramp_red REAL,"
        " ramp_window INTEGER"
        ")"
    )
    c.commit()


def get_settings(username):
    c = _conn()
    _ensure_settings_table(c)
    row = c.execute(
        "SELECT default_region, default_horizon, ramp_yellow, ramp_red, ramp_window"
        " FROM user_settings WHERE username=?",
        (username,),
    ).fetchone()
    c.close()
    if row is None:
        return {}
    return {
        "default_region": row[0],
        "default_horizon": row[1],
        "ramp_yellow": row[2],
        "ramp_red": row[3],
        "ramp_window": row[4],
    }


def save_settings(username, default_region=None, default_horizon=None,
                  ramp_yellow=None, ramp_red=None, ramp_window=None):
    c = _conn()
    _ensure_settings_table(c)
    existing = c.execute(
        "SELECT default_region, default_horizon, ramp_yellow, ramp_red, ramp_window"
        " FROM user_settings WHERE username=?",
        (username,),
    ).fetchone()
    if existing:
        dr = default_region if default_region is not None else existing[0]
        dh = default_horizon if default_horizon is not None else existing[1]
        ry = ramp_yellow if ramp_yellow is not None else existing[2]
        rr = ramp_red if ramp_red is not None else existing[3]
        rw = ramp_window if ramp_window is not None else existing[4]
        c.execute(
            "UPDATE user_settings SET default_region=?, default_horizon=?,"
            " ramp_yellow=?, ramp_red=?, ramp_window=? WHERE username=?",
            (dr, dh, ry, rr, rw, username),
        )
    else:
        c.execute(
            "INSERT INTO user_settings"
            " (username, default_region, default_horizon, ramp_yellow, ramp_red, ramp_window)"
            " VALUES (?,?,?,?,?,?)",
            (username, default_region, default_horizon, ramp_yellow, ramp_red, ramp_window),
        )
    c.commit()
    c.close()


def effective_thresholds(username):
    """Return (yellow, red, window) with user overrides or config defaults."""
    from config import RAMP_YELLOW_THRESHOLD, RAMP_RED_THRESHOLD, RAMP_WINDOW_MINUTES
    s = get_settings(username)
    return (
        s.get("ramp_yellow") or RAMP_YELLOW_THRESHOLD,
        s.get("ramp_red") or RAMP_RED_THRESHOLD,
        int(s.get("ramp_window") or RAMP_WINDOW_MINUTES),
    )