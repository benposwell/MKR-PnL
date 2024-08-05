import requests
from msal import ConfidentialClientApplication
import streamlit as st
import pandas as pd

def get_excel_links_sharepoint(client_id, client_secret, tenant_id, site_id, excel_file_id, sheet_name, range_address):
    graph_url = "https://graph.microsoft.com/v1.0"
    
    app = ConfidentialClientApplication(
        client_id,
        authority=f"https://login.microsoftonline.com/{tenant_id}",
        client_credential=client_secret
    )
    
    result = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
    # table_id = "{EF9B9AEB-3467-4782-B0C4-980E474B002B}"
    
    if "access_token" in result:
        api_url = f"{graph_url}/sites/{site_id}/drive/items/{excel_file_id}/workbook/worksheets/{sheet_name}/range(address='{range_address}')"
        
        headers = {
            'Authorization': 'Bearer ' + result['access_token'],
            'Content-Type': 'application/json'
        }

        response = requests.get(api_url, headers=headers)
        
        # st.write(response.status_code)
        if response.status_code == 200:
            data = response.json()
            values = data['values']

            headers = values[0]
            data_rows = values[2:]

            df = pd.DataFrame(data_rows, columns=headers)
            for column in df.columns:
                if df[column].dtype == 'object':
                    try:
                        df[column] = df[column].apply(convert_to_float)
                    except:
                        pass
            return df
        else:
            return None
    else:
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