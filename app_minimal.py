"""Minimal main app for debugging"""

import streamlit as st

st.set_page_config(page_title="Assemblée Nationale", page_icon="🏛️", layout="wide")

st.title("🏛️ Assemblée Nationale")
st.write("Test homepage - no data loading")

col1, col2 = st.columns(2)

with col1:
    st.markdown("### 👥 Députés")
    if st.button("Voir les députés", key="btn_deputies"):
        st.switch_page("pages/1_Députés.py")

with col2:
    st.markdown("### 📊 Activité")
    if st.button("Voir l'activité", key="btn_activity"):
        st.switch_page("pages/4_Activité.py")
