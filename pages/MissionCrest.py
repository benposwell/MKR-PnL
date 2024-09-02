import streamlit as st
import os
from utils.chat_funcs import check_password
import streamlit.components.v1 as components

# Check for password
if not check_password():
    st.stop()

st.title("Historical Mission Crest Reports")
# Get all reports in folder data with html extension
reports = [f for f in os.listdir(os.path.join(os.path.dirname(__file__), "..", "data")) if f.endswith(".html")]

# change to single select
report_name = st.selectbox("Select a Report", reports, key='mission_crest_selector')
selected_report = os.path.join(os.path.dirname(__file__), "..", "data", report_name)

with open(selected_report, "r") as f:
    html_content = f.read()

# Add spinner to below
with st.spinner("Loading report..."):
    components.html(html_content, height = 19000)


