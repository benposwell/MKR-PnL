import streamlit as st
import pandas as pd
# import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
from plotly.subplots import make_subplots
from datetime import datetime
import pytz

from utils.funcs import convert_to_float, get_csv_from_sharepoint_by_path, extract_currency_pair, generate_file_path, process_24h_data, get_historical_data

pio.templates.default = "plotly"
aest = pytz.timezone('Australia/Sydney')
st.set_page_config(page_title='Position & P/L Report', page_icon=':chart_with_upwards_trend:', layout='wide', initial_sidebar_state='collapsed')
st.image('images/Original Logo.png')
# st.title('Position & P/L Report')


if 'data' not in st.session_state:
    st.session_state.data = None  
if 'combined_df' not in st.session_state:
    st.session_state.combined_df = None  
if 'historical_data' not in st.session_state:
    st.session_state.historical_data = None
  
# @st.cache_data
def get_data(selected_date):
    current_hour = datetime.now(aest).hour
    formatted_time = f"{selected_date.strftime('%Y-%m-%d')}-21-00"
    # formatted_time = f"{selected_date.strftime('%Y-%m-%d')}-{current_hour:02d}-00"

    CLIENT_ID = st.secrets["CLIENT_ID"]
    CLIENT_SECRET = st.secrets["CLIENT_SECRET"]
    TENANT_ID = st.secrets["TENANT_ID"]
    SITE_ID = st.secrets["SITE_ID"]
    
    FILE_PATH = generate_file_path(formatted_time)

    df = get_csv_from_sharepoint_by_path(CLIENT_ID, CLIENT_SECRET, TENANT_ID, SITE_ID, FILE_PATH)
    
    exclude_columns = ['Book Name', 'Holding Scenario', 'Description', 'Active']

    for column in df.columns:
        if column not in exclude_columns:
            df[column] = df[column].apply(convert_to_float)

    return df

st.divider()
if 'selected_date' not in st.session_state:
    st.session_state.selected_date = pd.to_datetime(datetime.now(aest)).date()
selected_date = st.date_input("Select a date", value=st.session_state.selected_date, key="overall_date")
st.session_state.selected_date = selected_date

if st.button("Refresh Data"):
    progress_bar = st.progress(0)
    status_text = st.empty()
    status_text.text("Loading data...")
    st.session_state.data = get_data(selected_date)
    progress_bar.progress(100)
    status_text.text("Data Loaded!")
st.divider()    

if st.session_state.data is None:
    st.warning("Please click 'Refresh Data' to load the data.")
else:
    data = st.session_state.data
    current_date = datetime.now(aest).strftime('%m/%d/%Y')
    current_hour = datetime.now(aest).hour

    st.markdown(f"""
    <div style="text-align: center;">
        <h2>MKR Capital Daily Report for {current_date}</h2>
        <p> Last updated at {current_hour:02d}:00<p>
    </div>
    """, unsafe_allow_html=True)

# Center the tabs using CSS
    st.markdown("""
        <style>
            .css-1y0tads {
                justify-content: center;
            }
        </style>
        """, unsafe_allow_html=True)

    # Create the tabs
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs(["P+L Report", "FX Positions", "Futures Positions", "Swaps Positions", "Options Positions", "Intraday P+L", "Historical P+L"])
    # tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["P+L Report", "FX Positions", "Futures Positions", "Swaps Positions", "Options Positions", "Intraday P+L"])

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
        st.divider()

    with tab2:
        # Create Book Selector & Filter Data
        books = ['DM FX', 'EM FX']
        book = st.multiselect("Select a book", books)

        currency_data = data[data["Book Name"].isin(book)]
        # currency_data = currency_data[currency_data['Quantity'] != 0]
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
        # fig = create_bar_chart(all_data, "Exposure by Currency", "Currency", "$ NMV", False)
        # fig = create_bar_chart(curr_data, "Exposure by Currency", "Currency", "Book NMV (Total)", False)
        st.plotly_chart(fig) 
        if st.checkbox("Show Raw Data", key="show_raw_data_curr_exp"):
            st.subheader("Raw Data")
            st.dataframe(all_data, use_container_width=True)



    with tab3:
        books = ['USD rates', 'DM Rates', 'Equity trading']
        book = st.multiselect("Select a book", books, key="futures_book")

        futures_data = data[data["Book Name"].isin(book)]
        futures_data = futures_data[((futures_data['Quantity'] != 0) | (futures_data['$ Daily P&L'] != 0))]

        fig2 = make_subplots(specs=[[{"secondary_y": True}]])
        fig2.add_trace(
            go.Bar(x=futures_data['Description'], y=futures_data['Quantity'], name='Quantity'), secondary_y=False
        )
        fig2.add_trace(
            go.Scatter(x=futures_data['Description'], y=futures_data['$ Daily P&L'], name="Daily P&L", mode='markers', marker=dict(
                color='black', size=5, symbol='diamond'
            )), secondary_y=True
        )
        fig2.update_layout(title_text="Futures Positions", xaxis_title="Description", hovermode="closest")
        fig2.update_yaxes(title_text="Quantity", secondary_y=False)
        fig2.update_yaxes(title_text="$ Daily P&L", secondary_y=True)

        st.plotly_chart(fig2, use_container_width=True)

        st.dataframe(futures_data[['Book Name', 'Description', 'Quantity', '$ Daily P&L', '$ MTD P&L', '$ YTD P&L', '$ ITD P&L']], use_container_width=True)

    with tab4:
        books = ['Cross Market Rates', 'AUD Rates', 'NZD Rates']
        book = st.multiselect("Select a book", books, key="swaps_book")

        swaps_data = data[data["Book Name"].isin(book)]
        swaps_data = swaps_data[((swaps_data['Quantity'] != 0) | (swaps_data['$ Daily P&L'] != 0))]

        fig3 = make_subplots(specs=[[{"secondary_y": True}]])

        # Add bar chart for Quantity
        fig3.add_trace(
            go.Bar(x=swaps_data['Description'], y=swaps_data['Quantity'], name='Quantity'),
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
        fig3.update_yaxes(title_text="Quantity", secondary_y=False)
        fig3.update_yaxes(title_text="$ Daily P&L", secondary_y=True)

        # Display the chart in Streamlit
        st.plotly_chart(fig3, use_container_width=True)
        st.dataframe(swaps_data[['Book Name', 'Description', 'Quantity', '$ Daily P&L', '$ MTD P&L', '$ YTD P&L', '$ ITD P&L', 'Par Swap Rate']], use_container_width=True)

    with tab5:
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
    
    with tab6:
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
    
    with tab7:
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







# CAN WE HAVE A RELATED EVENTS SECTION WHICH TIES IN WITH OUR DATA?

