import streamlit as st
from utils.email_funcs import send_email
from utils.chat_funcs import check_password
from datetime import datetime
import pandas as pd
import pytz
from utils.funcs import get_data

# st.set_page_config(page_title='Email Generater', page_icon=':chart_with_upwards_trend:', layout='wide', initial_sidebar_state='expanded')
# st.image('images/Original Logo.png')

aest = pytz.timezone('Australia/Sydney')

if not check_password():
    st.stop()

st.sidebar.title(f"Welcome, {st.session_state.logged_in_user}!")

if 'data' not in st.session_state:
    st.session_state.data = None
    st.session_state.dv01_data = None
    st.session_state.cvar_data = None
    st.session_state.curr_exp_data = None



data = st.session_state.data
dv01_data = st.session_state.dv01_data
cvar_data = st.session_state.cvar_data
curr_exp_data = st.session_state.curr_exp_data

st.divider()
st.subheader("Email Generator")
rec_options = ['bposwell@mkrcapital.com.au', 'arowe@mkrcapital.com.au', 'james.austin@missioncrestcapital.com']
recipient = st.multiselect("Select a recipient", rec_options)
interval_options = ['Daily', 'WTD', 'MTD', 'YTD', 'ITD']
interval = st.selectbox("Select an interval", interval_options)

st.session_state.selected_date = pd.to_datetime(datetime.now(aest)).date()
selected_date = st.date_input("Select a date", value=st.session_state.selected_date, key="email_date")
st.session_state.selected_date = selected_date

if 'selected_hour' not in st.session_state:
    st.session_state.selected_hour = datetime.now(aest).hour
if 'selected_minute' not in st.session_state:
    st.session_state.selected_minute = datetime.now(aest).minute

selected_hour = st.selectbox("Select an hour", list(range(0, 24)))
st.session_state.selected_hour = selected_hour

selected_minute = st.selectbox("Select a minute", list(range(0, 59)))
st.session_state.selected_minute = selected_minute

# Formatted date and hour
formatted_date = f"{selected_date.strftime('%Y-%m-%d')}-{selected_hour:02d}-{selected_minute:02d}"

col1, col2 = st.columns(2)
with col1:
    if st.button("Send Email", use_container_width=True):
        # Progres bar
        progress_bar = st.progress(0)
        status_text = st.empty()

        # inputted_date = st.date_input("Select a date")
        most_recent_time, data, curr_exp_data, dv01_data, cvar_data = get_data(formatted_date)


        if data is not None:
            send_email(interval, recipient, data, dv01_data, cvar_data, curr_exp_data, formatted_date)
            status_text.text("Email Sent!")
        else:
            st.warning("Please click 'Refresh Data' to load the data.")
        progress_bar.progress(100)
with col2:
    if st.button("Send Latest", key="send_latest", use_container_width=True):
        progress_bar = st.progress(0)
        status_text = st.empty()

        most_recent_time, data, curr_exp_data ,dv01_data, cvar_data = get_data()
        if data is not None:
            send_email(interval, recipient, data, dv01_data, cvar_data, curr_exp_data, most_recent_time)
            status_text.text("Email Sent!")
        else:
            st.warning("Please click 'Refresh Data' to load the data.")
        progress_bar.progress(100)

st.divider()

if st.sidebar.button("Logout"):
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()