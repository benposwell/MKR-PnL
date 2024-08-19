import requests
from msal import ConfidentialClientApplication
import streamlit as st
import pandas as pd
from io import StringIO
import re
import plotly.express as px
from datetime import datetime, timedelta

def get_csv_from_sharepoint_by_path(client_id, client_secret, tenant_id, site_id, file_path):
    graph_url = "https://graph.microsoft.com/v1.0"
    
    app = ConfidentialClientApplication(
        client_id,
        authority=f"https://login.microsoftonline.com/{tenant_id}",
        client_credential=client_secret
    )
    
    result = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
    
    if "access_token" in result:
        api_url = f"{graph_url}/sites/{site_id}/drive/root:{file_path}:/content"
        
        headers = {
            'Authorization': 'Bearer ' + result['access_token']
        }

        response = requests.get(api_url, headers=headers)
        
        if response.status_code == 200:
            csv_content = StringIO(response.text)
            df = pd.read_csv(csv_content)
        
            return df
        else:
            st.error(f"Error: {response.status_code}, {response.text}")
            return None
    else:
        st.error(file_path)
        st.error("Failed to acquire token")
        return None
    
def get_files_from_sharepoint_folder(client_id, client_secret, tenant_id, site_id, folder_path):
    graph_url = "https://graph.microsoft.com/v1.0"
    
    app = ConfidentialClientApplication(
        client_id,
        authority=f"https://login.microsoftonline.com/{tenant_id}",
        client_credential=client_secret
    )
    
    result = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
    if "access_token" in result:
        # Construct the API URL to list files in the folder
        api_url = f"{graph_url}/sites/{site_id}/drive/root:{folder_path}:/children"
        
        headers = {
            'Authorization': 'Bearer ' + result['access_token']
        }

        response = requests.get(api_url, headers=headers)
        
        if response.status_code == 200:
            files_data = response.json().get('value', [])
            file_list = [file['name'] for file in files_data if file.get('file')]
            return file_list
        else:
            print(f"Error: {response.status_code}, {response.text}")
            return None
    else:
        print("Failed to acquire token")
        return None


    
def convert_to_float(value):
    if isinstance(value, str):
        value = value.replace(',', '').replace('$', '').replace('(', '-').replace(')', '')
        value = value.replace('USD', '')
        try:
            return float(value)
        except ValueError:
            return value
    elif isinstance(value, (int, float)):
        return float(value)
    return value

def extract_currency_pair(description):
    # Use regex to find the currency pair pattern
    match = re.search(r'[A-Z]{3}/[A-Z]{3}', description)
    if match:
        return match.group(0)
    return None

def generate_file_path(today, base="/ProfitLoss/data"):
    return f"{base}_{today}.csv"

def process_24h_data(input_time):
    CLIENT_ID = st.secrets["CLIENT_ID"]
    CLIENT_SECRET = st.secrets["CLIENT_SECRET"]
    TENANT_ID = st.secrets["TENANT_ID"]
    SITE_ID = st.secrets["SITE_ID"]

    end_time = datetime.strptime(input_time, '%Y-%m-%d-%H-%M')

    file_names = []
    for i in range(24):
        current_time = end_time - timedelta(hours=i)
        current_time = current_time.replace(minute=0, second=0, microsecond=0) 
        file_name = f"/ProfitLoss/data_{current_time.strftime('%Y-%m-%d-%H-%M')}.csv"
        file_names.insert(0, file_name)  # Insert at beginning to maintain chronological order
    
    # Process each file and combine into one dataframe
    combined_df = pd.DataFrame()
    for file_name in file_names:
        try:
            df = get_csv_from_sharepoint_by_path(CLIENT_ID, CLIENT_SECRET, TENANT_ID, SITE_ID, file_name)
            date_str = file_name.split('_')[1].replace('.csv', '')
            df['date'] = date_str

            combined_df = pd.concat ([combined_df, df], ignore_index=True)
        except Exception as e:
            continue
    return combined_df

def get_historical_data():
    CLIENT_ID = st.secrets["CLIENT_ID"]
    CLIENT_SECRET = st.secrets["CLIENT_SECRET"]
    TENANT_ID = st.secrets["TENANT_ID"]
    SITE_ID = st.secrets["SITE_ID"]
    
    files = get_files_from_sharepoint_folder(CLIENT_ID, CLIENT_SECRET, TENANT_ID, SITE_ID, folder_path="/ProfitLoss")

    to_map = []
    
        # If f contains 09-00 as the time field
    pattern = r'data_\d{4}-\d{1,2}-\d{1,2}-09-00'

    to_map = [f for f in files if re.search(pattern, f)]

    # Process each file and combine into one dataframe
    combined_df = pd.DataFrame()
    for f_path in to_map:
        try:
            f_path = f"/ProfitLoss/{f_path}"
            df = get_csv_from_sharepoint_by_path(CLIENT_ID, CLIENT_SECRET, TENANT_ID, SITE_ID, f_path)
            date_str = f_path.split('_')[1].replace('.csv', '')
            df['date'] = date_str
            
            combined_df = pd.concat([combined_df, df], ignore_index=True)
        except Exception as e:
            continue
    return combined_df
