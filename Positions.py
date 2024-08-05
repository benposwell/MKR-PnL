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

st.set_page_config(page_title='Position & P/L Report', page_icon=':chart_with_upwards_trend:', layout='wide', initial_sidebar_state='collapsed')
st.image('images/Original Logo.png')
st.title('Position & P/L Report')


if 'data' not in st.session_state:
    st.session_state.data = None  
  
# @st.cache_data
def get_data():
    CLIENT_ID = st.secrets["CLIENT_ID"]
    CLIENT_SECRET = st.secrets["CLIENT_SECRET"]
    TENANT_ID = st.secrets["TENANT_ID"]
    SITE_ID = st.secrets["SITE_ID"]
    FILE_ID = st.secrets["FILE_ID"]
    SHEET_NAME = st.secrets["SHEET_NAME"]
    RANGE_ADDRESS = st.secrets["RANGE_ADDRESS"]

    df = get_excel_links_sharepoint(CLIENT_ID, CLIENT_SECRET, TENANT_ID, SITE_ID, FILE_ID, SHEET_NAME, RANGE_ADDRESS)
    
    exclude_columns = ['Book Name', 'Holding Scenario', 'Description', 'Active']

    for column in df.columns:
        if column not in exclude_columns:
            df[column] = df[column].apply(convert_to_float)

    return df

if st.button("Refresh Data"):
    progress_bar = st.progress(0)
    status_text = st.empty()
    status_text.text("Loading data...")
    st.session_state.data = get_data()
    progress_bar.progress(100)
    status_text.text("Data Loaded!")

if st.session_state.data is None:
    st.warning("Please click 'Refresh Data' to load the data.")
else:
    data = st.session_state.data
    data = data[data['Notional Quantity'] != 0]
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["P+L Report", "FX Positions", "Futures Positions", "Swaps Positions", "Options Positions"])

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
        container = st.container()
        all = st.checkbox("Select all")
        all_books = data['Book Name'].unique()
        
        if all:
            selected_books = container.multiselect("Select Book Name(s):",
                all_books,all_books)
        else:
            selected_books =  container.multiselect("Select Book Name(s):",
                all_books)

        df_filtered = data[data["Book Name"].isin(selected_books)]

        fig = px.bar(df_filtered, x="Book Name", y='$ Daily P&L',
                    title='Daily P&L by Book',
                    hover_data=['Description', 'Notional Quantity', 'Fincad Price']#, 'Par Swap Rate']
        )
        fig.update_layout(
            xaxis_title="Book Name",
            yaxis_title="Daily P&L (USD)",
            hovermode="closest"
        )


        st.plotly_chart(fig, use_container_width=True)

        if 'expanded_view' not in st.session_state:
            st.session_state.expanded_view = False

        toggle_view_button = st.button("Show More")


        if toggle_view_button:
            st.session_state.expanded_view = not st.session_state.expanded_view

        if st.session_state.expanded_view:
            st.subheader("All Positions")
            st.write(df_filtered[['Book Name', 'Description', 'Notional Quantity', 'Fincad Price', '$ Daily P&L']]) #'Par Swap Rate'
        else:
            st.subheader("Aggregated Data by Book Name")
            aggregated_data = df_filtered[['Book Name', '$ Daily P&L', 'Book DV01']].groupby("Book Name", as_index=False).sum()
            aggregated_data['$ Daily P&L'] = pd.to_numeric(aggregated_data['$ Daily P&L'], errors='coerce')
            aggregated_data['$ Daily P&L'] = aggregated_data['$ Daily P&L'].fillna(0)

            total_pnl = aggregated_data['$ Daily P&L'].sum()
            # st.write(type(aggregated_data['$ Daily P&L'].sum()))
            aggregated_data = pd.concat([aggregated_data, pd.DataFrame({'Book Name': ['Total'], '$ Daily P&L': [total_pnl]})])
            st.write(aggregated_data)

    with tab2:
        books = ['DM FX', 'EM FX']
        book = st.multiselect("Select a book", books)

        currency_data = data[data["Book Name"].isin(book)]
        fig1 = px.bar(currency_data, x="Description", y="Notional Quantity",
                    title="FX Positions",
                    hover_data=['Fincad Price', '$ Daily P&L'])
        
        fig1.update_layout(
            xaxis_title="Currency",
            yaxis_title="Notional Quantity",
            hovermode="closest"
        )
        st.plotly_chart(fig1, use_container_width=True)

        st.dataframe(currency_data[['Book Name', 'Description', 'Notional Quantity', 'Fincad Price', '$ Daily P&L', '$ MTD P&L', '$ YTD P&L', '$ P&L']])

    with tab3:
        books = ['USD rates', 'DM Rates', 'Equity trading']
        book = st.multiselect("Select a book", books, key="futures_book")

        

        futures_data = data[data["Book Name"].isin(book)]
        fig2 = px.bar(futures_data, x="Description", y="Notional Quantity",
                    title="Futures Positions",
                    hover_data=['Fincad Price', '$ Daily P&L'])
        
        fig2.update_layout(
            xaxis_title="Description",
            yaxis_title="Notional Quantity",
            hovermode="closest"
        )
        st.plotly_chart(fig2, use_container_width=True)

        st.dataframe(futures_data[['Book Name', 'Description', 'Notional Quantity', 'Fincad Price', '$ Daily P&L', '$ MTD P&L', '$ YTD P&L', '$ P&L']])

    with tab4:
        books = ['Cross Market Rates', 'AUD Rates', 'NZD Rates']
        book = st.multiselect("Select a book", books, key="swaps_book")

        swaps_data = data[data["Book Name"].isin(book)]
        fig3 = px.bar(swaps_data, x="Description", y="Notional Quantity",
                    title="Swaps Positions",
                    hover_data=['Fincad Price', '$ Daily P&L'])#, 'Par Swap Rate'])
        
        fig3.update_layout(
            xaxis_title="Description",
            yaxis_title="Notional Quantity",
            hovermode="closest"
        )
        st.plotly_chart(fig3, use_container_width=True)

        st.dataframe(swaps_data[['Book Name', 'Description', 'Notional Quantity', 'Fincad Price', '$ Daily P&L', '$ MTD P&L', '$ YTD P&L', '$ P&L']]) #Par Swap Rate'

    with tab5:
        books = ['FX options']
        book = st.multiselect("Select a book", books, key="options_book")

        options_data = data[data["Book Name"].isin(book)]
        fig4 = px.bar(options_data, x="Description", y="Notional Quantity",
                    title="Swaps Positions",
                    hover_data=['Fincad Price', '$ Daily P&L'])#, 'Par Swap Rate'])
        
        fig4.update_layout(
            xaxis_title="Description",
            yaxis_title="Notional Quantity",
            hovermode="closest"
        )
        st.plotly_chart(fig4, use_container_width=True)

        st.dataframe(options_data[['Book Name', 'Description', 'Notional Quantity', 'Fincad Price', '$ Daily P&L', '$ MTD P&L', '$ YTD P&L', '$ P&L']])





# CAN WE HAVE A RELATED EVENTS SECTION WHICH TIES IN WITH OUR DATA?

