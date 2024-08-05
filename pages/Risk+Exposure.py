import streamlit as st
import pandas as pd
import plotly.express as px
import time
from utils.funcs import convert_to_float, get_excel_links_sharepoint
import re

st.set_page_config(page_title="Risk & Exposure",
                   initial_sidebar_state='collapsed',
                   layout='wide')

st.image('images/Original Logo.png')
st.title('Risk & Exposure Report')


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

dv_data = st.session_state.data
tab1, tab2 = st.tabs(["DV01 Risk Report", "Currency Exposure Report"])
def create_heatmap(data, title):
    fig = px.imshow(data, 
                    labels=dict(x="Bucket", y="Currency", color="DV01"),
                    x=data.columns, 
                    y=data.index,
                    color_continuous_scale="RdBu_r",
                    title=title)
    fig.update_layout(height=600, width=1000)
    return fig

def extract_currency_pair(text):
    # Regular expression to match the currency pair in the format XXX/YYY
    pattern = r'[A-Z]{3}/[A-Z]{3}'
    match = re.search(pattern, text)
    
    if match:
        return match.group()
    else:
        return None
    

def create_bar_chart(data, title, x_title, y_title, use_values=True):
    fig = px.bar(data, 
                 x=data.index, 
                 y=data.values if use_values else data[y_title],
                #  y=data[y_title],#.values, 
                 title=title,
                 labels={"x": x_title, "y": y_title})
    fig.update_layout(height=600)
    return fig


with tab1:
    st.write("COMING SOON!")
    # view_option = st.selectbox("Select a View Option", ["By Currency", "By Bucket", "By Instrument"], key="DV01_view_option")
    # if view_option == "By Currency":
    #     fig = create_heatmap(dv_data, "DV01 Heatmap by Currency and Bucket")
    #     st.plotly_chart(fig)
        
    #     if st.checkbox("Show Raw Data"):
    #         st.subheader("Raw Data")
    #         st.dataframe(dv_data.groupby("Currency").sum().drop(columns="Description"))

    # elif view_option == "By Bucket":
    #     total_dv01 = dv_data.sum()
    #     st.write(total_dv01)
    #     fig = create_bar_chart(total_dv01, "Total DV01 Risk by Bucket", "Bucket", "Total DV01")
    #     st.plotly_chart(fig)
        
    #     if st.checkbox("Show Raw Data"):
    #         csv = total_dv01.to_csv(index=False)
    #         st.download_button(
    #             label="Download data as CSV",
    #             data=csv,
    #             file_name="total_dv01.csv",
    #             mime="text/csv"
    #         )

    #         st.subheader("Raw Data")
    #         st.dataframe(total_dv01[2:])

    # else:
    #     st.dataframe(dv_data)

with tab2:
    curr_data = st.session_state.data
    curr_data['Currency'] = curr_data['Description'].apply(extract_currency_pair)
    curr_data = curr_data[['Currency', '$ NMV']]
    
    # Drop na in currency
    curr_data = curr_data.dropna(subset=["Currency"], how="any")
    # to_numeric
    curr_data['$ NMV'] = pd.to_numeric(curr_data['$ NMV'], errors='coerce')
    # Fill na with 0
    curr_data['$ NMV'] = curr_data['$ NMV'].fillna(0)
    curr_data = curr_data.groupby("Currency").sum()
    # Add total
    total = curr_data.sum()
    all_data = pd.concat([curr_data, pd.DataFrame({'$ NMV': [total['$ NMV']]}, index=['Total'])])
    
    # curr_data = curr_data.set_index("Currency")
    # curr_data = curr_data[['FX Rate', 'Book NMV (Total)']]
    fig = create_bar_chart(all_data, "Exposure by Currency", "Currency", "$ NMV", False)
    # fig = create_bar_chart(curr_data, "Exposure by Currency", "Currency", "Book NMV (Total)", False)
    st.plotly_chart(fig) 
    if st.checkbox("Show Raw Data", key="show_raw_data_curr_exp"):
        st.subheader("Raw Data")
        st.dataframe(all_data)

