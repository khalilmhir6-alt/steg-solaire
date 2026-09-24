import streamlit as st
from ui.theme import render_filters


def render():
    st.markdown("""
    <div class="steg-subnav">
      <a href="#section-alertes-detail">Alerte de baisse</a>
      <a href="#section-alertes-detail">Situation normale</a>
    </div>
    """, unsafe_allow_html=True)

    render_filters()

    NORMAL_CARD = """
    <div style="background:linear-gradient(135deg,#f0fff4,#d9f2e3);border:1px solid #7dc99b;border-radius:16px;padding:34px;text-align:center;">
      <div style="font-size:21px;font-weight:700;color:#1b5e20;margin-top:8px">Situation normale</div>
      <div style="font-size:15px;color:#3b6e4f;margin-top:6px">Aucune baisse de production solaire prevue sur la periode.</div>
    </div>
    """

    st.markdown('<div id="section-alertes-detail" class="section-anchor"></div>', unsafe_allow_html=True)
    st.markdown(NORMAL_CARD, unsafe_allow_html=True)
