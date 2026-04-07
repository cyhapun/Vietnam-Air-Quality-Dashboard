import streamlit as st


def inject_css(css_path: str = "styles/main.css"):
    with open(css_path, "r", encoding="utf-8") as f:
        css = f.read()
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
