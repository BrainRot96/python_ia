import streamlit as st, sys, platform

st.set_page_config(page_title="Test Streamlit", page_icon="✅")
st.title("✅ Streamlit fonctionne")
st.write("Python :", sys.version)
st.write("Plateforme :", platform.platform())
st.success("Si tu vois ceci, tout marche.")