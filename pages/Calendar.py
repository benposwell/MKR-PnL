import streamlit as st
import pandas as pd
from datetime import datetime
from utils.cal_funcs import generate_day_ahead_preview, store_report, get_report
from utils.chat_funcs import check_password
from utils.email_funcs import send_html_email
from pinecone import Pinecone


if not check_password():
    st.stop()

pc = Pinecone(api_key = st.secrets["PINECONE_API_KEY"])
# assistant = pc.assistant.Assistant(
#     assistant_name = st.secrets["PINECONE_ASSISTANT_NAME"]
# )

curr_country_dict = {
    'AUD': 'Australia',
    'NZD': 'New Zealand',
    'USD': 'United States',
    'CAD': 'Canada',
    'GBP': 'United Kingdom',
    'EUR': 'Eurozone',
    'CHF': 'Switzerland',
    'JPY': 'Japan',
    'CNY': 'China',
    'INR': 'India',
    'RUB': 'Russia',
    'ZAR': 'South Africa',
    'BRL': 'Brazil',
    'MXN': 'Mexico',
    'COP': 'Colombia',
    'CLP': 'Chile',
    'PEN': 'Peru',
    'ARS': 'Argentina',
    'UYU': 'Uruguay',
    'PYG': 'Paraguay',
    'BOB': 'Bolivia',
    'VND': 'Vietnam',
    'THB': 'Thailand',
    'IDR': 'Indonesia',
    'MYR': 'Malaysia',
    'SGD': 'Singapore',
    'PHP': 'Philippines',
    'KRW': 'South Korea',
    'HKD': 'Hong Kong',
    'TWD': 'Taiwan',
    'CNY': 'China',
    'INR': 'India',
    'RUB': 'Russia',
    'ZAR': 'South Africa',
    'BRL': 'Brazil',
    'MXN': 'Mexico',
    'COP': 'Colombia',
    'CLP': 'Chile',
    'PEN': 'Peru',
    'ARS': 'Argentina',
    'UYU': 'Uruguay',
    'PYG': 'Paraguay',
    'BOB': 'Bolivia',
    'VND': 'Vietnam',
    'THB': 'Thailand',
    'IDR': 'Indonesia',
    'MYR': 'Malaysia',
    'SGD': 'Singapore',
    'PHP': 'Philippines',
    'KRW': 'South Korea',
    'HKD': 'Hong Kong',
    'TWD': 'Taiwan',
    'CNH': 'China',
    'TRY': 'Turkey'
}

# Initialize session state
if 'show_raw_data' not in st.session_state:
    st.session_state.show_raw_data = False
if 'report_html' not in st.session_state:
    st.session_state.report_html = None


# st.title("Economic Calendar")
st.markdown(f"""
    <div style="text-align: center;">
        <h1>Economic Calendar</h1>
    </div>
    """, unsafe_allow_html=True)


cal_events = pd.read_csv("data/bbg_sample_cal.csv")
cal_events['ID'] = cal_events['ID'].str.replace('Country', '')
cal_events['RELEASE_DATE_TIME'] = pd.to_datetime(cal_events['RELEASE_DATE_TIME'])


# col1, col2 = st.columns(2)
# with col1:
#     date_selector = st.date_input("Select Date", value=datetime.now())
#     impacts = (cal_events['RELEVANCY'].unique())
#     default_impacts = ['Very High', 'High']
#     selected_impacts = st.multiselect("Select Impact Levels", impacts, default=default_impacts, key = "report_impacts_selector")

# with col2:
#     countries = (cal_events['COUNTRY_NAME'].unique())
#     default_countries = ['Australia', 'United States', 'Japan', 'United Kingdom', 'China']
#     selected_countries = st.multiselect("Select Countries", countries, default=default_countries, key="report_countries_selector")
    
    
# Function to toggle show_raw_data
def toggle_raw_data():
    st.session_state.show_raw_data = not st.session_state.show_raw_data

# col1, col2 = st.columns(2)
# with col2:
#     if st.button("Generate Daily Report", use_container_width=True):
#         filtered_df = cal_events[
#             (cal_events['RELEASE_DATE_TIME'].dt.date == date_selector) &
#             (cal_events['COUNTRY_NAME'].isin(selected_countries)) &
#             (cal_events['RELEVANCY'].isin(selected_impacts))
#         ]
#         with st.spinner("Generating report..."):
#             report_html = generate_day_ahead_preview(filtered_df, assistant)
#             st.session_state.report_html = report_html
#             store_report(st.session_state.report_html)
        
# with col1:
#     if st.button("Auto Generate Report", use_container_width=True):
#         curr_exp_data = st.session_state.curr_exp_data
#         if curr_exp_data is not None:
#             countries_of_interest = [curr_country_dict[curr] if not type(curr) == float else "" for curr in curr_exp_data['Currency'].unique()]

#         filtered_df = cal_events[
#             (cal_events['RELEASE_DATE_TIME'].dt.date == datetime.now().date()) &
#             (cal_events['COUNTRY_NAME'].isin(countries_of_interest)) &
#             (cal_events['RELEVANCY'].isin(['High', 'Very High']))
#         ]
#         with st.spinner("Generating report..."):
#             report_html = generate_day_ahead_preview(filtered_df, assistant)
#             st.session_state.report_html = report_html
#             store_report(st.session_state.report_html)

# st.divider()
# if st.session_state.report_html is None:
#     st.session_state.report_html = get_report()


# if st.session_state.report_html is not None:
#     st.success("Report has already been generated.")
#     if st.button("View Report", key="view_report", use_container_width=True):
#         st.html(st.session_state.report_html)

# if hasattr(st.session_state, 'report_html'):
#     st.subheader("Email Report")
#     rec_options = ['bposwell@mkrcapital.com.au', 'arowe@mkrcapital.com.au', 'james.austin@missioncrestcapital.com']
#     recipient = st.multiselect("Select a recipient", rec_options)
#     if st.button("Send Report", use_container_width=True):
#         send_html_email(f"Day Ahead Preview - {datetime.now().strftime('%d-%m-%Y')}", st.session_state.report_html, recipient)



st.divider()
# Use a button to toggle the state
st.button("Toggle Raw Data", on_click=toggle_raw_data)
if st.session_state.show_raw_data:
    # Convert to datetime objects once
    cal_events['RELEASE_DATE_TIME'] = pd.to_datetime(cal_events['RELEASE_DATE_TIME'])
    st.write("Raw Calendar Data")
    # Add interactive filters
    st.subheader("Filter Calendar Events")
    
    # Date range filter
    date_range = st.date_input("Select Date Range", [cal_events['RELEASE_DATE_TIME'].min(), cal_events['RELEASE_DATE_TIME'].max()], key="raw_date_range")
    
    # Country filter
    countries = (cal_events['COUNTRY_NAME'].unique())
    selected_countries = st.multiselect("Select Countries", countries, default=countries, key="raw_countries_selector")
    
    # Impact filter
    impacts = (cal_events['RELEVANCY'].unique())
    selected_impacts = st.multiselect("Select Impact Levels", impacts, default=impacts, key="raw_impacts_selector")
    
    # Apply filters
    filtered_df = cal_events[
        (cal_events['RELEASE_DATE_TIME'].dt.date.between(date_range[0], date_range[1])) &
        (cal_events['COUNTRY_NAME'].isin(selected_countries)) &
        (cal_events['RELEVANCY'].isin(selected_impacts))
    ]
    
    st.write(f"Showing {len(filtered_df)} events")
    st.dataframe(filtered_df, use_container_width=True, hide_index=True)

if st.sidebar.button("Logout"):
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()