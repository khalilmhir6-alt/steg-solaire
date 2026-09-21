import streamlit as st
from ui.theme import render_filters, region_label
from ui import auth, hierarchy
from config import REGION_LABELS
import pandas as pd

ROLE_LABELS = {
    auth.ROLE_NATIONAL: "Superviseur national",
    auth.ROLE_ADMIN: "Superviseur de region",
    auth.ROLE_TECHNICIAN: "Technicien",
}


def _districts_of(region):
    return hierarchy.districts_of_region(region)


def render():
    user = st.session_state.get("user")
    region = auth.region_of(user)
    national = auth.is_national(user)

    st.markdown("""
    <div class="steg-subnav">
      <a href="#section-admin-form">Ajouter un compte</a>
      <a href="#section-admin-list">Comptes existants</a>
    </div>
    """, unsafe_allow_html=True)

    render_filters()

    # ------------------------------------------------------------------ create
    st.markdown('<div id="section-admin-form" class="section-anchor"></div>', unsafe_allow_html=True)
    st.markdown("### Ajouter un compte")
    st.caption("Creez un technicien pour un secteur, ou un superviseur de region (reserve a steg).")

    role_label = "Technicien" if not national else st.selectbox(
        "Type de compte", ["Technicien", "Superviseur de region"],
        key="admin_new_role")

    # region selection
    if national:
        regions = hierarchy.list_regions()
        areg = st.selectbox("Region", regions,
                            format_func=lambda s: region_label(s), key="admin_new_region")
    else:
        areg = region
        st.info(f"Votre perimetre : **{region_label(areg)}**.")

    target_scope = areg
    if role_label == "Technicien":
        districts = _districts_of(areg)
        if districts:
            adist = st.selectbox("Secteur (district) de rattachement", districts,
                                 format_func=lambda s: hierarchy.DISTRICTS[s][1],
                                 key="admin_new_district")
            target_scope = f"{areg}/{adist}"
        else:
            st.warning("Aucun district dans cette region.")
            target_scope = None

    with st.form("add_admin_form"):
        auser = st.text_input("Identifiant", key="admin_new_user")
        apwd = st.text_input("Mot de passe", type="password", key="admin_new_pwd")
        submit = st.form_submit_button("Creer le compte", type="primary")

    if submit:
        if not (auser.strip() and apwd.strip()):
            st.error("Veuillez saisir un identifiant et un mot de passe.")
        elif target_scope is None:
            st.error("Impossible de determiner le perimetre du compte.")
        else:
            role = auth.ROLE_ADMIN if role_label == "Superviseur de region" \
                else auth.ROLE_TECHNICIAN
            if not auth.can_create(user, role, target_scope):
                st.error("Droits insuffisants pour creer ce compte.")
            else:
                full_name = {
                    auth.ROLE_ADMIN: f"Admin {region_label(areg)}",
                    auth.ROLE_TECHNICIAN: f"Technicien {hierarchy.scope_label(target_scope)}",
                }[role]
                auth.add_user(auser.strip(), apwd, role, full_name=full_name,
                              region=areg, scope=target_scope)
                st.success(f"Compte **{auser.strip()}** cree ({role_label}) pour "
                           f"{hierarchy.scope_label(target_scope)}.")

    # ------------------------------------------------------------------ list
    st.markdown('<div id="section-admin-list" class="section-anchor"></div>', unsafe_allow_html=True)
    st.markdown("### Comptes existants")

    me = auth.scope_of(user)
    rows = [u for u in auth.list_users()
            if national or (u[1] == auth.ROLE_TECHNICIAN and u[3] == region)]

    if not rows:
        st.caption("Aucun compte dans ce perimetre.")
        return

    data = []
    for username, role, full_name, uregion, uscope in rows:
        data.append({
            "Identifiant": username,
            "Role": ROLE_LABELS.get(role, role),
            "Nom": full_name or "",
            "Perimetre": hierarchy.scope_label(uscope or uregion),
        })

    dfu = pd.DataFrame(data)
    st.dataframe(dfu, width="stretch", hide_index=True)

    st.markdown("**Supprimer un compte**  ")
    target_name = st.selectbox("Compte a supprimer",
                               sorted(u[0] for u in rows if u[0] != user["username"]),
                               key="admin_del_user")
    target_row = next(u for u in rows if u[0] == target_name)
    target_user = {"username": target_name, "role": target_row[1],
                   "region": target_row[3], "scope": target_row[4]}

    if st.button("Supprimer", type="primary", key="admin_del_btn"):
        if auth.can_delete(user, target_user):
            auth.delete_user(target_name)
            st.success(f"Compte **{target_name}** supprime.")
            st.rerun()
        else:
            st.error("Vous ne pouvez supprimer que des comptes sous votre propre perimetre.")