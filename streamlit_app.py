import streamlit as st
import pandas as pd
# import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
from plotly.subplots import make_subplots

from utils.funcs import convert_to_float, get_csv_from_sharepoint_by_path, extract_currency_pair

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
    FILE_PATH = st.secrets["FILE_PATH"]

    df = get_csv_from_sharepoint_by_path(CLIENT_ID, CLIENT_SECRET, TENANT_ID, SITE_ID, FILE_PATH)
    
    
    exclude_columns = ['Book Name', 'Holding Scenario', 'Description', 'Active']

    for column in df.columns:
        if column not in exclude_columns:
            df[column] = df[column].apply(convert_to_float)

    return df

if st.button("Refresh Data"):
    st.divider()
    progress_bar = st.progress(0)
    status_text = st.empty()
    status_text.text("Loading data...")
    st.session_state.data = get_data()
    progress_bar.progress(100)
    status_text.text("Data Loaded!")
    st.divider()

if st.session_state.data is None:
    st.warning("Please click 'Refresh Data' to load the data.")
else:
    data = st.session_state.data
    st.write(data)
    data['Date'] = pd.to_datetime(data['Date'], format='%d/%m/%Y')
    max_date = data['Date'].max().strftime('%d/%m/%Y')
    st.subheader(body=f"MKR Daily Report for {max_date}")
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

        # Create Plots
        fig = px.bar(df_filtered, x="Book Name", y='$ Daily P&L', title='Contributors to Daily P&L by Book', hover_data=['Description', 'Notional Quantity', 'Fincad Price'])#, 'Par Swap Rate'])
        fig.update_layout(xaxis_title="Book Name", yaxis_title="Daily P&L (USD)", hovermode="closest" )

        fig_total = px.bar(total_pnl, x='Book Name', y='Total Daily P&L', title = 'Total Daily P&L by Book')
        fig_total.update_layout(xaxis_title="Book Name", yaxis_title="Total Daily P&L (USD)", hovermode="closest")

        st.plotly_chart(fig_total, use_container_width=True)
        st.plotly_chart(fig, use_container_width=True)

        # Show Raw Data
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
            aggregated_data = df_filtered[['Book Name', '$ Daily P&L', '$ MTD P&L', '$ YTD P&L', '$ P&L', 'Book DV01']].groupby("Book Name", as_index=False).sum()
            aggregated_data['$ Daily P&L'] = pd.to_numeric(aggregated_data['$ Daily P&L'], errors='coerce')
            aggregated_data['$ Daily P&L'] = aggregated_data['$ Daily P&L'].fillna(0)

            total_pnl = aggregated_data['$ Daily P&L'].sum()
            aggregated_data = pd.concat([aggregated_data, pd.DataFrame({'Book Name': ['Total'], '$ Daily P&L': [total_pnl]})])
            st.write(aggregated_data)

    with tab2:
        # Create Book Selector & Filter Data
        books = ['DM FX', 'EM FX']
        book = st.multiselect("Select a book", books)

        currency_data = data[data["Book Name"].isin(book)]
        # currency_data = currency_data[currency_data['Notional Quantity'] != 0]
        currency_data = currency_data[((currency_data['Notional Quantity'] != 0) | (currency_data['$ Daily P&L'] != 0))]

        currency_data['Currency Pair'] = currency_data['Description'].apply(extract_currency_pair)

        # Generate Chart
        fig1 = make_subplots(specs=[[{"secondary_y": True}]])
        fig1.add_trace(
            go.Bar(x=currency_data['Currency Pair'], y=currency_data['Notional Quantity'], name='Notional Quantity'), secondary_y=False
        )
        fig1.add_trace(
            go.Scatter(x=currency_data['Currency Pair'], y=currency_data['$ Daily P&L'], name="Daily P&L", mode='markers', marker=dict(
                color='black', size=5, symbol='diamond'
            )), secondary_y=True
        )
        fig1.update_layout(title_text="FX Positions", xaxis_title="Currency", hovermode="closest")
        fig1.update_yaxes(title_text="Notional Quantity", secondary_y=False)
        fig1.update_yaxes(title_text="$ Daily P&L", secondary_y=True)

        # Display Chart and Data
        st.plotly_chart(fig1, use_container_width=True)
        st.dataframe(currency_data[['Book Name', 'Currency Pair', 'Notional Quantity', 'Fincad Price', '$ Daily P&L', '$ MTD P&L', '$ YTD P&L', '$ P&L']])

    with tab3:
        books = ['USD rates', 'DM Rates', 'Equity trading']
        book = st.multiselect("Select a book", books, key="futures_book")

        futures_data = data[data["Book Name"].isin(book)]
        futures_data = futures_data[((futures_data['Notional Quantity'] != 0) | (futures_data['$ Daily P&L'] != 0))]

        fig2 = make_subplots(specs=[[{"secondary_y": True}]])
        fig2.add_trace(
            go.Bar(x=futures_data['Description'], y=futures_data['Notional Quantity'], name='Notional Quantity'), secondary_y=False
        )
        fig2.add_trace(
            go.Scatter(x=futures_data['Description'], y=futures_data['$ Daily P&L'], name="Daily P&L", mode='markers', marker=dict(
                color='black', size=5, symbol='diamond'
            )), secondary_y=True
        )
        fig2.update_layout(title_text="Futures Positions", xaxis_title="Description", hovermode="closest")
        fig2.update_yaxes(title_text="Notional Quantity", secondary_y=False)
        fig2.update_yaxes(title_text="$ Daily P&L", secondary_y=True)

        st.plotly_chart(fig2, use_container_width=True)

        st.dataframe(futures_data[['Book Name', 'Description', 'Notional Quantity', 'Fincad Price', '$ Daily P&L', '$ MTD P&L', '$ YTD P&L', '$ P&L']])

    with tab4:
        books = ['Cross Market Rates', 'AUD Rates', 'NZD Rates']
        book = st.multiselect("Select a book", books, key="swaps_book")

        swaps_data = data[data["Book Name"].isin(book)]
        swaps_data = swaps_data[((swaps_data['Notional Quantity'] != 0) | (swaps_data['$ Daily P&L'] != 0))]

        fig3 = make_subplots(specs=[[{"secondary_y": True}]])

        # Add bar chart for Notional Quantity
        fig3.add_trace(
            go.Bar(x=swaps_data['Description'], y=swaps_data['Notional Quantity'], name='Notional Quantity'),
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
        fig3.update_yaxes(title_text="Notional Quantity", secondary_y=False)
        fig3.update_yaxes(title_text="$ Daily P&L", secondary_y=True)

        # Display the chart in Streamlit
        st.plotly_chart(fig3, use_container_width=True)
        st.dataframe(swaps_data[['Book Name', 'Description', 'Notional Quantity', 'Fincad Price', '$ Daily P&L', '$ MTD P&L', '$ YTD P&L', '$ P&L']]) #Par Swap Rate'

    with tab5:
        books = ['FX options']
        book = st.multiselect("Select a book", books, key="options_book")

        options_data = data[data["Book Name"].isin(book)]
        options_data_filtered = options_data[(options_data['Notional Quantity'] != 0) | (options_data['$ Daily P&L'] != 0)]

        fig4 = make_subplots(specs=[[{"secondary_y": True}]])

        # Add bar chart for Notional Quantity
        fig4.add_trace(
            go.Bar(x=options_data_filtered['Description'], y=options_data_filtered['Notional Quantity'], name='Notional Quantity'),
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
        fig4.update_yaxes(title_text="Notional Quantity", secondary_y=False)
        fig4.update_yaxes(title_text="$ Daily P&L", secondary_y=True)

        # Display the chart in Streamlit
        st.plotly_chart(fig4, use_container_width=True)
        st.dataframe(options_data[['Book Name', 'Description', 'Notional Quantity', 'Fincad Price', '$ Daily P&L', '$ MTD P&L', '$ YTD P&L', '$ P&L']])





# CAN WE HAVE A RELATED EVENTS SECTION WHICH TIES IN WITH OUR DATA?

