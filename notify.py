"""Email notification delivery for alerts.

SMTP via Gmail (stegsolaire@gmail.com). Credentials live in
.streamlit/secrets.toml under [smtp] — password must be a Gmail App
Password (2-Step Verification → App passwords), never the account password.

Respects each user's email_frequency setting (ui.auth).
"""

from __future__ import annotations

import logging
import smtplib
import time
from email.message import EmailMessage
from pathlib import Path
from typing import Iterable

logger = logging.getLogger("steg.notify")

# Last successful send timestamp per username (process-local).
_last_sent: dict[str, float] = {}

_FREQ_SECONDS = {
    "instant": 0,
    "hourly": 3600,
    "daily": 86400,
    "weekly": 604800,
    "off": None,  # never
}


def _smtp_config() -> dict | None:
    try:
        import streamlit as st
        cfg = st.secrets.get("smtp") if hasattr(st, "secrets") else None
        if not cfg:
            return None
        host = cfg.get("host")
        if not host:
            return None
        return {
            "host": host,
            "port": int(cfg.get("port", 587)),
            "username": cfg.get("username", ""),
            "password": cfg.get("password", ""),
            "from": cfg.get("from") or cfg.get("username", ""),
            "use_tls": bool(cfg.get("use_tls", True)),
        }
    except Exception:
        return None


def is_configured() -> bool:
    cfg = _smtp_config()
    return bool(cfg and cfg.get("password"))


def _frequency_ok(username: str) -> bool:
    """True when this user is due for an email at the current time."""
    try:
        from ui import auth
        freq = (auth.get_settings(username) or {}).get("email_frequency") or "daily"
    except Exception:
        freq = "daily"
    if freq == "off":
        return False
    window = _FREQ_SECONDS.get(freq, 86400)
    if window is None:
        return False
    if window == 0:
        return True
    last = _last_sent.get(username)
    if last is None:
        return True
    return (time.time() - last) >= window


def send_alert_email(to: str, subject: str, body: str) -> bool:
    """Send one alert email. Returns True on success, False otherwise."""
    if not to or "@" not in to:
        logger.warning("notify: skip — invalid/missing recipient %r", to)
        return False

    cfg = _smtp_config()
    if not cfg:
        logger.info(
            "notify: SMTP not configured — would send to %s | %s | %s",
            to, subject, body[:200],
        )
        return False

    msg = EmailMessage()
    msg["From"] = cfg["from"]
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)

    try:
        with smtplib.SMTP(cfg["host"], cfg["port"], timeout=15) as s:
            if cfg["use_tls"]:
                s.starttls()
            if cfg["username"]:
                s.login(cfg["username"], cfg["password"])
            s.send_message(msg)
        logger.info("notify: sent to %s | %s", to, subject)
        return True
    except Exception as exc:
        logger.error("notify: send failed to %s: %s", to, exc)
        return False


def notify_users(usernames: Iterable[str], subject: str, body: str) -> int:
    """Send alert to each named user, respecting their email_frequency.
    Returns how many sends succeeded (or would succeed if unconfigured)."""
    from ui import auth

    sent = 0
    for name in usernames:
        if not _frequency_ok(name):
            continue
        email = auth.get_email(name)
        if not email:
            continue
        ok = send_alert_email(email, subject, body)
        if ok or not is_configured():
            # stub path also marks "attempted" so frequency gate advances
            # only on real success when configured
            if ok:
                _last_sent[name] = time.time()
            sent += 1 if ok else 0
    return sent


def notify_scope_alert(scope: str, level: str, detail: str) -> int:
    """Fan out a ramp alert by role hierarchy (not every user):

      - steg (national)       → every alert
      - admin_<region>        → alerts whose region matches theirs
      - technicien_<district> → only an alert on their exact district scope
    """
    if level not in ("yellow", "red"):
        return 0

    from ui import auth

    label = "jaune" if level == "yellow" else "ROUGE"
    subject = f"[STEG Solaire] Alerte {label} — {scope}"
    body = (
        f"Alerte de baisse de production solaire ({label}).\n\n"
        f"Périmètre : {scope}\n"
        f"Détail : {detail}\n\n"
        f"— STEG Solaire\n"
    )

    parts = str(scope or "").replace("\\", "/").strip("/").split("/")
    alert_region = parts[0] if parts and parts[0] else "tunisia"

    targets = []
    for row in auth.list_users():
        username, role, _fn, region, uscope, email = row
        if not email:
            continue

        if role == auth.ROLE_NATIONAL:
            # steg: every alert (national + region + district)
            targets.append(username)
        elif role == auth.ROLE_ADMIN:
            # region admin: only alerts inside their own region
            if region and region == alert_region:
                targets.append(username)
        elif role == auth.ROLE_TECHNICIAN:
            # technician: only their exact district perimeter
            if uscope and uscope == scope:
                targets.append(username)
        # any other role → no alert email

    return notify_users(targets, subject, body)
