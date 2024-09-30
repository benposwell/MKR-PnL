import streamlit as st
from utils.chat_funcs import check_password
from utils.funcs import get_data
import time
import pandas as pd
import math
from datetime import datetime, timedelta
from utils.cal_funcs import get_report
import plotly.graph_objects as go
import pytz
from utils.chat_funcs import generate_chat_url

if not check_password():
    st.stop()

# Variable Initializations
if "data" not in st.session_state:
    st.session_state.data = None

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

st.markdown(
    f"""
    <div style="text-align: center;">
        <h1>Welcome, {st.session_state.logged_in_user}!</h1>
    </div>
    """,
    unsafe_allow_html=True
)


st.markdown(
    """
    <style>
    .stButton button {
        padding: 20px 50px;
        font-size: 20px;
        border-radius: 15px;
        font-weight: bold;
        width: 100%;
        height: 200px;
    }
    </style>
    """,
    unsafe_allow_html=True
)

if st.session_state.data is None:
    with st.spinner("Loading latest data..."):
        st.session_state.update_time, st.session_state.data, st.session_state.curr_exp_data, st.session_state.dv01_data, st.session_state.cvar_data = get_data()
    message_placeholder = st.empty()
    message_placeholder.success("Data loaded!")
    time.sleep(5)
    message_placeholder.empty()

daily = "${:,.0f}".format(float(st.session_state.data.iloc[0]['$ Daily P&L']))
weekly = "${:,.0f}".format(float(st.session_state.data.iloc[0]['$ WTD P&L']))
yearly = "${:,.0f}".format(float(st.session_state.data.iloc[0]['$ YTD P&L']))
inception = "${:,.0f}".format(float(st.session_state.data.iloc[0]['$ ITD P&L']))

st.divider()
mcol1, mcol2, mcol3, mcol4 = st.columns(4)
mcol1.metric("Daily P&L", daily)
mcol2.metric("WTD P&L", weekly)
mcol3.metric("YTD P&L", yearly)
mcol4.metric("ITD P&L", inception)
st.divider()

col_left, col_middle, col_right = st.columns(3)

with col_left:
    if st.button("📊 P&L Analysis", use_container_width=True):
        st.switch_page("pages/pnl_report.py")
    
    if st.button("🎲 Risk Report", use_container_width=True):
        st.switch_page("pages/Risk.py")

    # Create a button called Resources with an appropriate emoji
    if st.button("🔗 Resources", use_container_width=True):
        st.switch_page("pages/Resources.py")

with col_middle:
    if st.button("📖 Historicals", use_container_width=True):
        st.switch_page("pages/Historicals.py")
    if st.button("📧 Emailer", use_container_width=True):
        st.switch_page("pages/Emailer.py")
    if st.button("📈 Mission Crest Reports", use_container_width=True):
        st.switch_page("pages/MissionCrest.py")

with col_right:
    if st.button("🤖 BRAG", use_container_width=True):
        st.switch_page("pages/BetterRAG.py")
    if st.button("📅 Calendar", use_container_width=True):
        st.switch_page("pages/Calendar.py")
    if st.button("📚 Research Portal", use_container_width=True):
        st.switch_page("pages/ResearchPortal.py")
    
st.divider()

st.markdown(
    f"""
    <div>
        <h1>Biggest Movers</h1>
    </div>
    """,
    unsafe_allow_html=True
)
st.divider()
movers_time_horizon = st.selectbox("Select a time period", ["Daily", "Weekly", "Monthly", "Yearly"], key='movers_time_horizon')
time_horizon_dict = {
    "Daily": "$ Daily P&L",
    "Weekly": "$ WTD P&L",
    "Monthly": "$ MTD P&L",
    "Yearly": "$ YTD P&L"
}

top_5_positives = st.session_state.data.sort_values(by=time_horizon_dict[movers_time_horizon], ascending=False).head(5)
top_5_negatives = st.session_state.data.sort_values(by=time_horizon_dict[movers_time_horizon], ascending=True)[1:].head(5)
col1, col2 = st.columns(2)

# Plot for top 5 positive movers
with col1:
    fig_positive = go.Figure(data=[
        go.Bar(
            x=top_5_positives['Description'],
            y=top_5_positives[time_horizon_dict[movers_time_horizon]],
            marker_color='green'
        )
    ])
    fig_positive.update_layout(
        title='Top 5 Positive Movers',
        xaxis_title='Description',
        yaxis_title=time_horizon_dict[movers_time_horizon],
        height=400
    )
    st.plotly_chart(fig_positive, use_container_width=True)

# Plot for top 5 negative movers
with col2:
    fig_negative = go.Figure(data=[
        go.Bar(
            x=top_5_negatives['Description'],
            y=top_5_negatives[time_horizon_dict[movers_time_horizon]],
            marker_color='red'
        )
    ])
    fig_negative.update_layout(
        title='Top 5 Negative Movers',
        xaxis_title='Description',
        yaxis_title=time_horizon_dict[movers_time_horizon],
        height=400
    )
    st.plotly_chart(fig_negative, use_container_width=True)


st.markdown(
    f"""
    <div>
        <h1>Key Portfolio Events this Week</h1>
    </div>
    """,
    unsafe_allow_html=True
)
st.divider()

curr_exp_data = st.session_state.curr_exp_data
if curr_exp_data is not None:
    countries_of_interest = [curr_country_dict[curr] if not type(curr) == float else "" for curr in curr_exp_data['Currency'].unique()]
    print(countries_of_interest)


week_events = pd.read_csv('data/bbg_sample_cal.csv')
averages = pd.read_csv('data/bbg_averages.csv')
week_events = week_events[week_events['COUNTRY_NAME'].isin(countries_of_interest)]
week_events['RELEASE_DATE_TIME'] = pd.to_datetime(week_events['RELEASE_DATE_TIME'])
week_events['FORMATTED_TIME'] = week_events['RELEASE_DATE_TIME'].dt.strftime("%H:%M, %A - %B %d")
events_this_week = week_events[(week_events['RELEASE_DATE_TIME'].dt.date >= datetime.now(pytz.timezone('Australia/Sydney')).date()) & (week_events['RELEASE_DATE_TIME'].dt.date <= datetime.now(pytz.timezone('Australia/Sydney')).date() + timedelta(days=7))]
events_this_week = events_this_week[(events_this_week['RELEVANCY'] == 'Very High') | (events_this_week['RELEVANCY'] == 'High')]
events_this_week = events_this_week.merge(averages, on='ID', how='left')

events_this_week['BRAG Summary'] = events_this_week.apply(lambda row: generate_chat_url(
    prompt=f"Provide details on the following event:{row['EVENT_NAME']} in {row['COUNTRY_NAME']}. Include a summary of all analyst forecasts and expectations, ensuring that a comprehensive overview is generated. If you can find it in the context, also include previous figures for this event, and any other relevant information.",
    min_date=None,
    max_date=None,
    search_comprehensiveness=None,
    answer_detail=None
), axis=1)
cols_to_show = ['FORMATTED_TIME', 'COUNTRY_NAME', 'EVENT_NAME', 'RELEVANCY', 'PRIOR', 'BRAG Summary', 'SURVEY_MEDIAN', '3M Average', '6M Average', '1Y Average', '3Y Average']

st.data_editor(
    events_this_week[cols_to_show],
    column_config={
        "BRAG Summary": st.column_config.LinkColumn("BRAG Summary", 
                                                    width="medium", 
                                                    display_text="Generate BRAG Summary")
    },
    hide_index=True,
    use_container_width=True
)

st.divider()

# if 'report_html' not in st.session_state:
#     st.session_state.report_html = get_report()

# if 'report_html' in st.session_state and st.session_state.report_html:
#     st.html(st.session_state.report_html)

# Apply custom CSS styling
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
st.image("images/mt_aspiring.jpg", use_column_width=True)
st.divider()

if st.sidebar.button("Logout"):
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()