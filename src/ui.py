import streamlit as st

def page_header(title: str, subtitle: str = ""):
    st.title(title)
    if subtitle:
        st.caption(subtitle)
