import streamlit as st
import pandas as pd
# import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
from plotly.subplots import make_subplots
from datetime import datetime, time
import pytz
from st_pages import add_page_title, get_nav_from_toml

from utils.funcs import extract_currency_pair, get_data
from utils.chat_funcs import check_password

pio.templates.default = "plotly"
aest = pytz.timezone('Australia/Sydney')

if 'data' not in st.session_state:
    st.session_state.data = None  
    st.session_state.update_time = None
    st.session_state.curr_exp_data = None
    st.session_state.dv01_data = None
    st.session_state.cvar_data = None
if 'combined_df' not in st.session_state:
    st.session_state.combined_df = None  
if 'historical_data' not in st.session_state:
    st.session_state.historical_data = None

if not check_password():
    st.stop()

st.sidebar.title(f"Welcome, {st.session_state.logged_in_user}!")

st.divider()
if 'use_latest' not in st.session_state:
    st.session_state.use_latest = True
if 'selected_date' not in st.session_state or st.session_state.selected_date is None:
    st.session_state.selected_date = pd.to_datetime(datetime.now(aest))
if 'selected_hour' not in st.session_state:
    st.session_state.selected_hour = datetime.now(aest).hour

use_latest = st.toggle("Use latest data", value=st.session_state.use_latest)
st.session_state.use_latest = use_latest

if not use_latest:
    col1, col2 = st.columns(2)
    with col1:
        selected_date = st.date_input("Select a date", value=st.session_state.selected_date)
    with col2:
        selected_hour = st.selectbox("Select an hour", range(24), index=st.session_state.selected_hour)
    
    selected_datetime = datetime.combine(selected_date, time(hour=selected_hour, minute=0))
    selected_datetime = pytz.timezone('Australia/Sydney').localize(selected_datetime)
    formatted_date = selected_datetime.strftime('%Y-%m-%d-%H-00')
    st.session_state.selected_date = selected_datetime

    if st.button("Refresh Data"):
        progress_bar = st.progress(0)
        status_text = st.empty()
        status_text.text("Loading data...")
        st.session_state.update_time, st.session_state.data, st.session_state.curr_exp_data, st.session_state.dv01_data, st.session_state.cvar_data  = get_data(formatted_date)
        if st.session_state.data is not None:
            progress_bar.progress(100)
            status_text.text("Data Loaded!")
        else:
            st.warning("Data not available for the selected date.")
else:
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
 
    st.markdown(f"""
    <div style="text-align: center;">
        <h2>MKR Capital Daily Report for {current_date}</h2>
        <p> Last updated at {st.session_state.update_time}<p>
    </div>
    """, unsafe_allow_html=True)


    st.markdown("""
        <style>
            .css-1y0tads {
                justify-content: center;
            }
        </style>
        """, unsafe_allow_html=True)

    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["P+L Report", "FX Positions", "Futures Positions", "Rates Futures", "Swaps Positions", "Options Positions"])

    def create_bar_chart(data, x, y, title, x_title, y_title, hover_data):
        fig = px.bar(data, x=x, y=y,
                    title=title,
                    hover_data=hover_data)
        fig.update_layout(
            xaxis_title=x_title,
            yaxis_title=y_title,
            hovermode="closest"
        )
        return fig

    with tab1:
        # Create Book Selector
        container = st.container()
        all = st.checkbox("Select all")
        all_books = data['Book Name'].unique()
        
        if all:
            selected_books = container.multiselect("Select Book Name(s):",
                all_books,all_books)
        else:
            selected_books =  container.multiselect("Select Book Name(s):",
                all_books)

        # Prepare Data
        df_filtered = data[data["Book Name"].isin(selected_books)]
        total_pnl = df_filtered.groupby("Book Name")['$ Daily P&L'].sum().reset_index()
        total_pnl.columns = ['Book Name', 'Total Daily P&L']

        total_itd_pnl = df_filtered.groupby("Book Name")['$ ITD P&L'].sum().reset_index()
        total_itd_pnl.columns = ['Book Name', 'Total ITD P&L']

        total_ytd_pnl = df_filtered.groupby("Book Name")['$ YTD P&L'].sum().reset_index()
        total_ytd_pnl.columns = ['Book Name', 'Total YTD P&L']

        # Create Plots
        fig = px.bar(df_filtered, x="Book Name", y='$ Daily P&L', title='Contributors to Daily P&L by Book', hover_data=['Description', 'Quantity', 'Par Swap Rate'])
        fig.update_layout(xaxis_title="Book Name", yaxis_title="Daily P&L (USD)", hovermode="closest" )
        
        fig_ytd = px.bar(total_ytd_pnl, x="Book Name", y='Total YTD P&L', title="YTD P&L by Book")
        fig_itd = px.bar(total_itd_pnl, x="Book Name", y='Total ITD P&L', title="ITD P&L by Book")
        fig_ytd.update_layout(xaxis_title="Book Name", yaxis_title="YTD P&L (USD)", hovermode="closest")
        fig_itd.update_layout(xaxis_title="Book Name", yaxis_title="ITD P&L (USD)", hovermode="closest")

        fig_total = px.bar(total_pnl, x='Book Name', y='Total Daily P&L', title = 'Total Daily P&L by Book')
        fig_total.update_layout(xaxis_title="Book Name", yaxis_title="Total Daily P&L (USD)", hovermode="closest")

        st.plotly_chart(fig_total, use_container_width=True)
        
        dv01_total_for_print = dv01_data.drop(columns=['Description', 'Date']).groupby('Currency').sum().sum(axis=1)[:-1]['Grand Total']
        st.write(f"Total DV01: ${dv01_total_for_print:,.2f}")
        st.write(f"Total CVaR: ${cvar_data.iloc[-1]['Daily Fund CVaR']:,.2f}")
        st.write(f"Total USD Exposure: ${curr_exp_data[curr_exp_data['Currency']=='USD']['Book NMV (Total)'].values[0]:,.2f}")


        st.divider()
        st.plotly_chart(fig, use_container_width=True)

        # Show Raw Data
        if 'expanded_view' not in st.session_state:
            st.session_state.expanded_view = False
        
        st.markdown("**Aggregated Data by Book Name**")
        toggle_view_button = st.button("Show More")

        if toggle_view_button:
            st.session_state.expanded_view = not st.session_state.expanded_view
        
        
        if st.session_state.expanded_view:
            st.subheader("All Positions")
            st.dataframe(df_filtered[['Book Name', 'Description', 'Quantity','Par Swap Rate', '$ Daily P&L', '$ YTD P&L', '$ ITD P&L']], use_container_width=True)
        else:
            
            aggregated_data = df_filtered[['Book Name', '$ Daily P&L', '$ MTD P&L', '$ YTD P&L', '$ ITD P&L']].groupby("Book Name", as_index=False).sum()
            aggregated_data['$ Daily P&L'] = pd.to_numeric(aggregated_data['$ Daily P&L'], errors='coerce')
            aggregated_data['$ Daily P&L'] = aggregated_data['$ Daily P&L'].fillna(0)

            total_daily_pnl = aggregated_data['$ Daily P&L'].sum()
            total_monthly_pnl = aggregated_data['$ MTD P&L'].sum()
            total_yearly_pnl = aggregated_data['$ YTD P&L'].sum()
            total_itd_pnl = aggregated_data['$ ITD P&L'].sum()
            
            aggregated_data = pd.concat([aggregated_data, pd.DataFrame({'Book Name': ['Total'], '$ Daily P&L': [total_daily_pnl], '$ MTD P&L': [total_monthly_pnl], '$ YTD P&L': [total_yearly_pnl], '$ ITD P&L': [total_itd_pnl]})])#, ignore_index=True)
            st.dataframe(aggregated_data, use_container_width=True)

        st.divider()
        st.subheader("Long Term Performance")
        st.plotly_chart(fig_ytd, use_container_width=True)
        st.plotly_chart(fig_itd, use_container_width=True)

    with tab2:
        books = ['DM FX', 'EM FX']
        book = st.multiselect("Select a book", books)

        currency_data = data[data["Book Name"].isin(book)]
        currency_data = currency_data[((currency_data['Quantity'] != 0) | (currency_data['$ Daily P&L'] != 0))]

        currency_data['Currency Pair'] = currency_data['Description'].apply(extract_currency_pair)

        # Generate Chart
        fig1 = make_subplots(specs=[[{"secondary_y": True}]])
        fig1.add_trace(
            go.Bar(x=currency_data['Currency Pair'], y=currency_data['Quantity'], name='Quantity'), secondary_y=False
        )
        fig1.add_trace(
            go.Scatter(x=currency_data['Currency Pair'], y=currency_data['$ Daily P&L'], name="Daily P&L", mode='markers', marker=dict(
                color='black', size=5, symbol='diamond'
            )), secondary_y=True
        )
        fig1.update_layout(title_text="FX Positions", xaxis_title="Currency", hovermode="closest")
        fig1.update_yaxes(title_text="Quantity", secondary_y=False)
        fig1.update_yaxes(title_text="$ Daily P&L", secondary_y=True)

        # Display Chart and Data
        st.plotly_chart(fig1, use_container_width=True)
        st.dataframe(currency_data[['Book Name', 'Currency Pair', 'Quantity', '$ Daily P&L', '$ MTD P&L', '$ YTD P&L', '$ ITD P&L']], use_container_width=True)

        st.divider()

        # Currency Exposure Report
        curr_data = st.session_state.data
        # Convert Description to String object
        curr_data['Description'] = curr_data['Description'].astype(str)
        curr_data['Currency'] = curr_data['Description'].apply(extract_currency_pair)
        curr_data = curr_data[['Currency', '$ NMV']]

        # Drop na in currency
        curr_data = curr_data.dropna(subset=["Currency"], how="any")
        # to_numeric
        curr_data['$ NMV'] = pd.to_numeric(curr_data['$ NMV'], errors='coerce')
        curr_data['$ NMV'] = curr_data['$ NMV'].fillna(0)
        curr_data = curr_data.groupby("Currency").sum()
        # Add total
        total = curr_data.sum()
        all_data = pd.concat([curr_data, pd.DataFrame({'$ NMV': [total['$ NMV']]}, index=['Total'])])
        
        fig = px.bar(all_data, x=all_data.index, y='$ NMV', title="Exposure by Currency", labels={"x": "Currency", "y": "$ NMV"})
        st.plotly_chart(fig) 
        if st.checkbox("Show Raw Data", key="show_raw_data_curr_exp"):
            st.subheader("Raw Data")
            st.dataframe(all_data, use_container_width=True)


    with tab3:
        books = ['Equity trading', 'Short term trading', 'Commodities']
        book = st.multiselect("Select a book", books, key="futures_book")

        futures_data = data[data["Book Name"].isin(book)]
        futures_data = futures_data[((futures_data['Quantity'] != 0) | (futures_data['$ Daily P&L'] != 0))]

        fig2 = make_subplots(specs=[[{"secondary_y": True}]])
        fig2.add_trace(
            go.Bar(x=futures_data['Description'], y=futures_data['$ Overall Cost'], name='Overall Cost'), secondary_y=False
        )
        fig2.add_trace(
            go.Scatter(x=futures_data['Description'], y=futures_data['$ Daily P&L'], name="Daily P&L", mode='markers', marker=dict(
                color='black', size=5, symbol='diamond'
            )), secondary_y=True
        )
        fig2.update_layout(title_text="Futures Positions", xaxis_title="Description", hovermode="closest")
        fig2.update_yaxes(title_text="$ Overall Cost", secondary_y=False)
        fig2.update_yaxes(title_text="$ Daily P&L", secondary_y=True)

        st.plotly_chart(fig2, use_container_width=True)

        st.dataframe(futures_data[['Book Name', 'Description', 'Quantity', '$ Overall Cost', '$ Daily P&L', '$ MTD P&L', '$ YTD P&L', '$ ITD P&L']], use_container_width=True)
    with tab4:
        books = ['USD rates', 'DM Rates']
        book = st.multiselect("Select a book", books, key="rates_book")

        rates_data = data[data["Book Name"].isin(book)]
        rates_data = rates_data[((rates_data['Quantity'] != 0) | (rates_data['$ Daily P&L'] != 0))]

        fig10 = make_subplots(specs=[[{"secondary_y": True}]])
        fig10.add_trace(
            go.Bar(x=rates_data['Description'], y=rates_data['Book DV01'], name='DV01'), secondary_y=False
        )
        fig10.add_trace(
            go.Scatter(x=rates_data['Description'], y=rates_data['$ Daily P&L'], name="Daily P&L", mode='markers', marker=dict(
                color='black', size=5, symbol='diamond'
            )), secondary_y=True
        )
        fig10.update_layout(title_text="Futures Positions", xaxis_title="Description", hovermode="closest")
        fig10.update_yaxes(title_text="DV01", secondary_y=False)
        fig10.update_yaxes(title_text="$ Daily P&L", secondary_y=True)

        st.plotly_chart(fig10, use_container_width=True)

        st.dataframe(rates_data[['Book Name', 'Description', 'Book DV01','Quantity', '$ Daily P&L', '$ MTD P&L', '$ YTD P&L', '$ ITD P&L']], use_container_width=True)

    with tab5:
        books = ['Cross Market Rates', 'AUD Rates', 'NZD Rates']
        book = st.multiselect("Select a book", books, key="swaps_book")

        swaps_data = data[data["Book Name"].isin(book)]
        swaps_data = swaps_data[((swaps_data['Quantity'] != 0) | (swaps_data['$ Daily P&L'] != 0))]

        fig3 = make_subplots(specs=[[{"secondary_y": True}]])

        # Add bar chart for Quantity
        fig3.add_trace(
            go.Bar(x=swaps_data['Description'], y=swaps_data['Book DV01'], name='DV01'),
            secondary_y=False
        )

        # Add scatter plot for Daily P&L
        fig3.add_trace(
            go.Scatter(x=swaps_data['Description'], y=swaps_data['$ Daily P&L'], name="Daily P&L", mode='markers', marker=dict(
                color='black', size=5, symbol='diamond'
            )),
            secondary_y=True
        )

        # Update layout
        fig3.update_layout(
            title_text="Swaps Positions",
            xaxis_title="Description",
            hovermode="closest"
        )

        # Update y-axes titles
        fig3.update_yaxes(title_text="DV01", secondary_y=False)
        fig3.update_yaxes(title_text="$ Daily P&L", secondary_y=True)

        # Display the chart in Streamlit
        st.plotly_chart(fig3, use_container_width=True)
        st.dataframe(swaps_data[['Book Name', 'Description', 'Quantity', 'Book DV01', '$ Daily P&L', '$ MTD P&L', '$ YTD P&L', '$ ITD P&L', 'Par Swap Rate']], use_container_width=True)
    with tab6:
        books = ['FX options']
        book = st.multiselect("Select a book", books, key="options_book")

        options_data = data[data["Book Name"].isin(book)]
        options_data_filtered = options_data[(options_data['Quantity'] != 0) | (options_data['$ Daily P&L'] != 0)]

        fig4 = make_subplots(specs=[[{"secondary_y": True}]])

        # Add bar chart for Quantity
        fig4.add_trace(
            go.Bar(x=options_data_filtered['Description'], y=options_data_filtered['Quantity'], name='Quantity'),
            secondary_y=False
        )

        # Add scatter plot for Daily P&L
        fig4.add_trace(
            go.Scatter(x=options_data_filtered['Description'], y=options_data_filtered['$ Daily P&L'], name="Daily P&L", mode='markers', marker=dict(
                color='black', size=5, symbol='diamond'
            )),
            secondary_y=True
        )

        # Update layout
        fig4.update_layout(
            title_text="Options Positions",
            xaxis_title="Description",
            hovermode="closest"
        )

        # Update y-axes titles
        fig4.update_yaxes(title_text="Quantity", secondary_y=False)
        fig4.update_yaxes(title_text="$ Daily P&L", secondary_y=True)

        # Display the chart in Streamlit
        st.plotly_chart(fig4, use_container_width=True)
        st.dataframe(options_data[['Book Name', 'Description', 'Quantity', '$ Daily P&L', '$ MTD P&L', '$ YTD P&L', '$ ITD P&L']], use_container_width=True)

if st.sidebar.button("Logout"):
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()


