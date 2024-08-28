import streamlit as st
from st_pages import add_page_title, get_nav_from_toml
import base64

st.set_page_config(layout="wide", initial_sidebar_state="collapsed", page_icon="images/icon.png")

st.markdown(
    """
    <style>
    img {
        border-radius: 15px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

nav = get_nav_from_toml(".streamlit/pages.toml")

st.logo("images/icon.png",
        link="https://mkrcapital.streamlit.app/")

st.markdown(
    """<a href="https://mkrcapital.streamlit.app/" target="_self">
    <img src="data:image/png;base64,{}" style="width:100%; height:auto;">
    </a>""".format(
        base64.b64encode(open("images/Original Logo.png", "rb").read()).decode()
    ),
    unsafe_allow_html=True,
)

pg = st.navigation(nav)

pg.run()