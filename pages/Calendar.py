import streamlit as st
import pandas as pd
# import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
import yaml
# from streamlit.legacy_caching import clear_cache

from utils.funcs import convert_to_float, get_excel_links_sharepoint

pio.templates.default = "plotly"

st.set_page_config(page_title='Economic Calendar', page_icon=':chart_with_upwards_trend:', layout='wide', initial_sidebar_state='collapsed')
st.image('images/Original Logo.png')
st.title('Economic Calendar')

st.write("COMING SOON!")