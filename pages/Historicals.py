
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from utils.funcs import create_heatmap, create_dv01_bar_chart, get_data, process_24h_data, get_historical_data
from utils.chat_funcs import check_password
from datetime import datetime
import pytz
import plotly.io as pio

pio.templates.default = "plotly"
aest = pytz.timezone('Australia/Sydney')
# st.set_page_config(page_title='Historicals Report', page_icon=':chart_with_upwards_trend:', layout='wide', initial_sidebar_state='expanded')
# st.image('images/Original Logo.png')

tab1, tab2 = st.tabs(["Intraday P&L", "Historical P&L"])
if not check_password():
    st.stop()

st.sidebar.title(f"Welcome, {st.session_state.logged_in_user}!")

with tab1:
        if 'selected_date' not in st.session_state:
            st.session_state.selected_date = pd.to_datetime(datetime.now(aest)).date()
        if 'selected_time' not in st.session_state:
            st.session_state.selected_time = datetime.now(aest).time()

        st.write("Intraday P&L Analysis")
        # selected_date = st.date_input("Select a date", value=datetime.date.today()).strftime('%Y-%m-%d')

        selected_date = st.date_input("Select a date", value=st.session_state.selected_date, key="date_input")
        st.session_state.selected_date = selected_date

        selected_time = st.time_input("Select a time", value=st.session_state.selected_time, key="time_input")
        st.session_state.selected_time = selected_time

        formatted_date = selected_date.strftime('%Y-%m-%d')
        formatted_time = selected_time.strftime('%H-%M')    
    
        if st.button("Calculate Intraday P&L"):
            progress_bar = st.progress(0)
            status_text = st.empty()
            status_text.text("Loading data...")
            st.session_state.combined_df = process_24h_data(f"{formatted_date}-{formatted_time}")
            progress_bar.progress(100)
            status_text.text("Data Loaded!")
        else:
            combined_df = None
            st.warning("Please click 'Calculate Intraday P&L' to load the data.")

        st.divider()
        if st.session_state.combined_df is not None:
            combined_df = st.session_state.combined_df
            # Drop rows with null in 'Book Name' column
            combined_df = combined_df.dropna(subset=['FundShortName'])

            combined_df['date'] = pd.to_datetime(combined_df['date'], format='%Y-%m-%d-%H-%M')

            # Group by date and book name, then sum the '$ Daily P&L'
            grouped = combined_df.groupby(['date', 'Book Name'])['$ Daily P&L'].sum().reset_index()

            # Calculate the total '$ Daily P&L' across all book names
            total_pnl = grouped.groupby('date')['$ Daily P&L'].sum().reset_index()

            # Create a list of unique book names
            book_names = grouped['Book Name'].unique()

            # Create the figure with two y-axes
            fig = make_subplots(specs=[[{"secondary_y": True}]])

            # Add total '$ Daily P&L' line
            fig.add_trace(
                go.Scatter(x=total_pnl['date'], y=total_pnl['$ Daily P&L'], name='Total $ Daily P&L', 
                        line=dict(color='black', width=3)),
                secondary_y=False,
            )

            # Add individual book name lines
            for book in book_names:
                book_data = grouped[grouped['Book Name'] == book]
                fig.add_trace(
                    go.Scatter(x=book_data['date'], y=book_data['$ Daily P&L'], name=book, 
                            line=dict(width=1), opacity=0.7),
                    secondary_y=True,
                )

            # Update layout
            fig.update_layout( 
                title='Daily P&L: Total and by Book Name',
                xaxis_title='Date',
                yaxis_title='Total $ Daily P&L',
                yaxis2_title='Individual Book $ Daily P&L',
                legend_title='Book Names',
                hovermode='x unified'
            )

            # Update y-axes
            fig.update_yaxes(title_text="Total $ Daily P&L", secondary_y=False)
            fig.update_yaxes(title_text="Individual Book $ Daily P&L", secondary_y=True)
            st.plotly_chart(fig, use_container_width=True)
        
with tab2:
    st.write("Historical P&L Analysis")
    if st.button("Calculate Historical P&L"):
        progress_bar = st.progress(0)
        status_text = st.empty()
        status_text.text("Loading data...")
        st.session_state.historical_data = get_historical_data()
        progress_bar.progress(100)
        status_text.text("Data Loaded!")
    else:
        st.session_state.historical_data = None
        st.warning("Please click 'Calculate Historical P&L' to load the data.")
    st.divider()

    if st.session_state.historical_data is not None:

        hist_data = st.session_state.historical_data

        hist_data = hist_data.dropna(subset=['FundShortName'])

        hist_data['date'] = pd.to_datetime(hist_data['date'], format='%Y-%m-%d-%H-%M')

        # Group by date and book name, then sum the '$ Daily P&L'
        grouped_hist_daily = hist_data.groupby(['date', 'Book Name'])['$ Daily P&L'].sum().reset_index()
        grouped_hist_ytd = hist_data.groupby(['date', 'Book Name'])['$ YTD P&L'].sum().reset_index()
        grouped_hist_itd = hist_data.groupby(['date', 'Book Name'])['$ ITD P&L'].sum().reset_index()

        grouped_hist_daily['date'] = pd.to_datetime(grouped_hist_daily['date'], format='%Y-%m-%d').dt.strftime('%Y-%m-%d')
        grouped_hist_ytd['date'] = pd.to_datetime(grouped_hist_ytd['date'], format='%Y-%m-%d').dt.strftime('%Y-%m-%d')
        grouped_hist_itd['date'] = pd.to_datetime(grouped_hist_itd['date'], format='%Y-%m-%d').dt.strftime('%Y-%m-%d')

        # Calculate the total '$ Daily P&L' across all book names
        total_pnl_daily = grouped_hist_daily.groupby('date')['$ Daily P&L'].sum().reset_index()
        total_pnl_ytd = grouped_hist_ytd.groupby('date')['$ YTD P&L'].sum().reset_index()
        total_pnl_itd = grouped_hist_itd.groupby('date')['$ ITD P&L'].sum().reset_index()

        # total_pnl_daily['date'] = pd.to_datetime(total_pnl_daily['date'], format='%Y-%m-%d')
        total_pnl_daily['date'] = pd.to_datetime(total_pnl_daily['date'], format='%Y-%m-%d').dt.strftime('%Y-%m-%d')
        total_pnl_ytd['date'] = pd.to_datetime(total_pnl_ytd['date'], format='%Y-%m-%d').dt.strftime('%Y-%m-%d')
        total_pnl_itd['date'] = pd.to_datetime(total_pnl_itd['date'], format='%Y-%m-%d').dt.strftime('%Y-%m-%d')

        # Create a list of unique book names
        book_names = grouped_hist_daily['Book Name'].unique()

        # DAILY
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_trace(
            go.Scatter(x=total_pnl_daily['date'], y=total_pnl_daily['$ Daily P&L'], name='Total $ Daily P&L', 
                    line=dict(color='black', width=3)),
            secondary_y=False,
        )
        for book in book_names:
            book_data = grouped_hist_daily[grouped_hist_daily['Book Name'] == book]
            fig.add_trace(
                go.Scatter(x=book_data['date'], y=book_data['$ Daily P&L'], name=book, 
                        line=dict(width=1), opacity=0.7),
                secondary_y=True,
            )
        fig.update_layout(
            title='Daily P&L: Total and by Book Name',
            xaxis_title='Date',
            yaxis_title='Total $ Daily P&L',
            yaxis2_title='Individual Book $ Daily P&L',
            legend_title='Book Names',
            hovermode='x unified'
        )
        fig.update_yaxes(title_text="Total $ Daily P&L", secondary_y=False)
        fig.update_yaxes(title_text="Individual Book $ Daily P&L", secondary_y=True)
        st.plotly_chart(fig, use_container_width=True)

        # YTD
        fig2 = make_subplots(specs=[[{"secondary_y": True}]])
        fig2.add_trace(
            go.Scatter(x=total_pnl_ytd['date'], y=total_pnl_ytd['$ YTD P&L'], name='Total $ YTD P&L', 
                    line=dict(color='black', width=3)),
            secondary_y=False,
        )
        for book in book_names:
            book_data = grouped_hist_ytd[grouped_hist_ytd['Book Name'] == book]
            fig2.add_trace(
                go.Scatter(x=book_data['date'], y=book_data['$ YTD P&L'], name=book, 
                        line=dict(width=1), opacity=0.7),
                secondary_y=True,
            )
        fig2.update_layout(
            title='YTD P&L: Total and by Book Name',
            xaxis_title='Date',
            yaxis_title='Total $ YTD P&L',
            yaxis2_title='Individual Book $ YTD P&L',
            legend_title='Book Names',
            hovermode='x unified'
        )
        fig2.update_yaxes(title_text="Total $ YTD P&L", secondary_y=False)
        fig2.update_yaxes(title_text="Individual Book $ YTD P&L", secondary_y=True)

        # ITD
        fig3 = make_subplots(specs=[[{"secondary_y": True}]])
        fig3.add_trace(
            go.Scatter(x=total_pnl_itd['date'], y=total_pnl_itd['$ ITD P&L'], name='Total $ ITD P&L', 
                    line=dict(color='black', width=3)),
            secondary_y=False,
        )
        for book in book_names:
            book_data = grouped_hist_itd[grouped_hist_itd['Book Name'] == book]
            fig3.add_trace(
                go.Scatter(x=book_data['date'], y=book_data['$ ITD P&L'], name=book, 
                        line=dict(width=1), opacity=0.7),
                secondary_y=True,
            )
        fig3.update_layout(
            title='ITD P&L: Total and by Book Name',
            xaxis_title='Date',
            yaxis_title='Total $ ITD P&L',
            yaxis2_title='Individual Book $ ITD P&L',
            legend_title='Book Names',
            hovermode='x unified'
        )
        fig3.update_yaxes(title_text="Total $ ITD P&L", secondary_y=False)
        fig3.update_yaxes(title_text="Individual Book $ ITD P&L", secondary_y=True)

        st.plotly_chart(fig2, use_container_width=True)
        st.plotly_chart(fig3, use_container_width=True)

if st.sidebar.button("Logout"):
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()