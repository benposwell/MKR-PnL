import requests
from msal import ConfidentialClientApplication
import streamlit as st
import pandas as pd
from io import StringIO
import re
import plotly.express as px

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
        st.error("Failed to acquire token")
        return None
    
def convert_to_float(value):
    if isinstance(value, str):
        value = value.replace(',', '').replace('$', '').replace('(', '-').replace(')', '')
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