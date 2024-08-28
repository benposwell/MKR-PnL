import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from utils.funcs import create_heatmap, create_dv01_bar_chart, get_data
from datetime import datetime
import pytz
import plotly.io as pio
from utils.chat_funcs import check_password

pio.templates.default = "plotly"
aest = pytz.timezone('Australia/Sydney')

if not check_password():
    st.stop()

st.sidebar.title(f"Welcome, {st.session_state.logged_in_user}!")

st.divider()

if 'selected_date' not in st.session_state:
    st.session_state.selected_date = pd.to_datetime(datetime.now(aest)).date()
selected_date = st.date_input("Select a date", value=st.session_state.selected_date, key="overall_date")
st.session_state.selected_date = selected_date

if st.button("Refresh Data"):
    progress_bar = st.progress(0)
    status_text = st.empty()
    status_text.text("Loading data...")
    st.session_state.update_time, st.session_state.data, st.session_state.curr_exp_data, st.session_state.dv01_data, st.session_state.cvar_data  = get_data()
    progress_bar.progress(100)
    status_text.text("Data Loaded!")
st.divider()    

if st.session_state.data is None:
    st.warning("Please click 'Refresh Data' to load the data.")
else:
    data = st.session_state.data
    curr_exp_data = st.session_state.curr_exp_data
    dv01_data = st.session_state.dv01_data
    dv01_data = dv01_data.set_index('Currency')
    cvar_data = st.session_state.cvar_data
    current_date = datetime.now(aest).strftime('%m/%d/%Y')
    current_hour = datetime.now(aest).hour
    st.markdown("**DV01 Risk**")
    view_option = st.selectbox("Select a View Option", ["By Currency", "By Bucket"], key="DV01_view_option")

    # Remove first row
    if view_option == "By Currency":
        # dv01_data = dv01_data.set_index('Currency')
        fig = create_heatmap(dv01_data.drop(columns=['Description', 'Date']), "DV01 Heatmap by Currency and Bucket")
        st.plotly_chart(fig)

        if st.checkbox("Show Raw Data"):
            st.write("Raw Data")
            st.dataframe(dv01_data, use_container_width=True)
    if view_option == "By Bucket":
        total_dv01 = dv01_data.sum()
        fig = create_dv01_bar_chart(total_dv01, "Total Dv01 Risk by Bucket", "Bucket", "Total DV01")
        st.plotly_chart(fig)
        
        if st.checkbox("Show Raw Data", key='dv01'):
            st.write("Raw Data")
            st.dataframe(total_dv01)
    st.divider()
    st.markdown("**CVaR Risk**")
    st.write(f"Total CVaR: ${cvar_data.iloc[-1]['Daily Fund CVaR']:,.2f}")
    if st.checkbox("Show Raw Data", key='cvar'):
        st.write("Raw Data")
        st.dataframe(cvar_data, use_container_width=True)

    st.divider()
    st.markdown("**Currency Exposure**")
    if st.checkbox("Show Raw Data", key='curr_exp_raw_data'):
        st.write("Raw Data")
        st.dataframe(curr_exp_data, use_container_width=True)

if st.sidebar.button("Logout"):
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()