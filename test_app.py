"""Minimal test app"""

import streamlit as st

st.set_page_config(page_title="Test", page_icon="🧪")

st.title("Test App")
st.write("If you can see this, Streamlit is working!")

if st.button("Click me"):
    st.balloons()
