"""Paramètres (Settings) page — Profil, Vue par défaut, Seuils d'alerte."""

import streamlit as st
from ui import auth, hierarchy
from ui.theme import STEG_BLUE, HORIZON_OPTIONS, region_label
from config import (
    RAMP_YELLOW_THRESHOLD,
    RAMP_RED_THRESHOLD,
    RAMP_WINDOW_MINUTES,
)


def render():
    user = st.session_state.get("user", {})
    username = user.get("username", "")
    saved = auth.get_settings(username)

    st.markdown("### Paramètres")

    # ── A) Profil ──────────────────────────────────────────────────────────
    st.markdown("#### Profil")
    with st.container(border=True):
        c1, c2 = st.columns(2)
        c1.text_input("Nom d'utilisateur", value=username, disabled=True,
                       key="pf_user")
        c2.text_input("Rôle", value=user.get("role", ""), disabled=True,
                       key="pf_role")
        st.text_input("Nom complet", value=user.get("full_name", ""),
                       disabled=True, key="pf_fullname")

        saved_email = auth.get_email(username) or user.get("email") or ""
        email_val = st.text_input(
            "Email (notifications d'alerte)",
            value=saved_email, key="pf_email",
            help="Adresse utilisée pour recevoir les alertes par email.",
        )

        freq = saved.get("email_frequency") or "daily"
        if freq not in auth.EMAIL_FREQUENCIES:
            freq = "daily"
        freq_labels = list(auth.EMAIL_FREQUENCY_LABELS.values())
        freq_keys = list(auth.EMAIL_FREQUENCIES)
        freq_idx = freq_keys.index(freq)
        freq_label = st.selectbox(
            "Fréquence des emails",
            freq_labels,
            index=freq_idx,
            key="pf_email_freq",
            help="À quelle fréquence vous souhaitez recevoir les alertes par email.",
        )
        new_freq = freq_keys[freq_labels.index(freq_label)]

        if st.button("Enregistrer les notifications", key="pf_email_btn"):
            email_val = email_val.strip()
            if email_val and ("@" not in email_val or "." not in email_val):
                st.error("Adresse email invalide.")
            else:
                auth.update_email(username, email_val)
                auth.save_settings(username, email_frequency=new_freq)
                if "user" in st.session_state:
                    st.session_state["user"]["email"] = email_val or None
                st.success("Notifications email enregistrées.")
                st.rerun()

        st.markdown("**Changer le mot de passe**")
        pw1, pw2 = st.columns(2)
        new_pw = pw1.text_input("Nouveau mot de passe", type="password",
                                 key="pf_new_pw")
        confirm_pw = pw2.text_input("Confirmer", type="password",
                                     key="pf_confirm_pw")
        if st.button("Mettre à jour le mot de passe", key="pf_pw_btn"):
            if not new_pw:
                st.error("Veuillez saisir un nouveau mot de passe.")
            elif new_pw != confirm_pw:
                st.error("Les mots de passe ne correspondent pas.")
            elif len(new_pw) < 6:
                st.error("Le mot de passe doit faire au moins 6 caractères.")
            else:
                auth.update_password(username, new_pw)
                st.success("Mot de passe mis à jour.")
                st.rerun()

    st.divider()

    # ── B) Vue par défaut ──────────────────────────────────────────────────
    st.markdown("#### Vue par défaut")
    st.caption("Choisissez la région et l'horizon affichés au chargement du dashboard.")

    all_regions = ["tunisia"] + hierarchy.list_regions()
    region_fmt = {s: region_label(s) for s in all_regions}
    horizon_labels = [label for label, _ in HORIZON_OPTIONS]

    default_region_idx = 0
    if saved.get("default_region") and saved["default_region"] in all_regions:
        default_region_idx = all_regions.index(saved["default_region"])

    default_horizon_idx = 0
    if saved.get("default_horizon") and saved["default_horizon"] in horizon_labels:
        default_horizon_idx = horizon_labels.index(saved["default_horizon"])

    with st.form("form_defaults"):
        dc1, dc2 = st.columns(2)
        sel_region = dc1.selectbox(
            "Région par défaut",
            all_regions,
            index=default_region_idx,
            format_func=lambda s: region_fmt[s],
        )
        sel_horizon = dc2.selectbox(
            "Horizon par défaut",
            horizon_labels,
            index=default_horizon_idx,
        )
        if st.form_submit_button("Enregistrer", type="primary"):
            auth.save_settings(username,
                               default_region=sel_region,
                               default_horizon=sel_horizon)
            st.success("Vue par défaut enregistrée.")
            st.rerun()

    st.divider()

    # ── C) Seuils d'alerte ─────────────────────────────────────────────────
    st.markdown("#### Seuils d'alerte")
    st.caption("Valeurs utilisées pour la détection de baisses de production solaire "
               "(rampe). Les valeurs par défaut sont définies dans la config système.")

    ry_default = saved.get("ramp_yellow", RAMP_YELLOW_THRESHOLD) or RAMP_YELLOW_THRESHOLD
    rr_default = saved.get("ramp_red", RAMP_RED_THRESHOLD) or RAMP_RED_THRESHOLD
    rw_default = saved.get("ramp_window", RAMP_WINDOW_MINUTES) or RAMP_WINDOW_MINUTES

    with st.form("form_thresholds"):
        st.markdown(f"**Seuil jaune** — baisse prévisionnelle minimale (défaut : "
                     f"{RAMP_YELLOW_THRESHOLD*100:.0f}%)")
        ry_val = st.slider(
            "Seuil jaune (% de chute / 60 min)",
            min_value=1.0, max_value=50.0,
            value=float(ry_default * 100),
            step=0.5, format="%.1f%%",
            key="th_ry",
        )

        st.markdown(f"**Seuil rouge** — baisse prévisionnelle sévère (défaut : "
                     f"{RAMP_RED_THRESHOLD*100:.0f}%)")
        rr_val = st.slider(
            "Seuil rouge (% de chute / 60 min)",
            min_value=1.0, max_value=60.0,
            value=float(rr_default * 100),
            step=0.5, format="%.1f%%",
            key="th_rr",
        )

        st.markdown(f"**Fenêtre glissante** — durée de la rampe en minutes "
                     f"(défaut : {RAMP_WINDOW_MINUTES} min)")
        rw_val = st.number_input(
            "Fenêtre (minutes)",
            min_value=5, max_value=180,
            value=int(rw_default),
            step=5,
            key="th_rw",
        )

        if st.form_submit_button("Enregistrer les seuils", type="primary"):
            ry_pct = ry_val / 100.0
            rr_pct = rr_val / 100.0
            if ry_pct >= rr_pct:
                st.error("Le seuil jaune doit être inférieur au seuil rouge.")
            else:
                auth.save_settings(username,
                                   ramp_yellow=ry_pct,
                                   ramp_red=rr_pct,
                                   ramp_window=int(rw_val))
                st.success("Seuils d'alerte enregistrés.")
                st.rerun()

    if st.button("Rétablir les valeurs par défaut", key="th_reset"):
        auth.save_settings(username,
                           ramp_yellow=RAMP_YELLOW_THRESHOLD,
                           ramp_red=RAMP_RED_THRESHOLD,
                           ramp_window=RAMP_WINDOW_MINUTES)
        st.success("Valeurs par défaut restaurées.")
        st.rerun()
