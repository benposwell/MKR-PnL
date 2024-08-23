import requests
from msal import ConfidentialClientApplication
import streamlit as st
import pandas as pd
from io import StringIO
import re
import plotly.express as px
from datetime import datetime, timedelta
import pytz


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
            if 'DV0' in file_path:
                df = pd.read_csv(csv_content, header=[1])
            elif 'Cur' in file_path:
                df = pd.read_csv(csv_content)
            else:
                df = pd.read_csv(csv_content)

                exclude_columns = ['Book Name', 'Holding Scenario', 'Description', 'Active']

                for column in df.columns:
                    if column not in exclude_columns:
                        df[column] = df[column].apply(convert_to_float)
            return df
        else:
            return None
    else:
        st.error(file_path)
        st.error("Failed to acquire token")
        return None
    
# def get_files_from_sharepoint_folder(client_id, client_secret, tenant_id, site_id, folder_path):
#     graph_url = "https://graph.microsoft.com/v1.0"
    
#     app = ConfidentialClientApplication(
#         client_id,
#         authority=f"https://login.microsoftonline.com/{tenant_id}",
#         client_credential=client_secret
#     )
    
#     result = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
#     if "access_token" in result:
#         # Construct the API URL to list files in the folder
#         api_url = f"{graph_url}/sites/{site_id}/drive/root:{folder_path}:/children"
        
#         headers = {
#             'Authorization': 'Bearer ' + result['access_token']
#         }

#         response = requests.get(api_url, headers=headers)
        
#         if response.status_code == 200:
#             files_data = response.json().get('value', [])
#             file_list = [file['name'] for file in files_data if file.get('file')]
#             return file_list
#         else:
#             print(f"Error: {response.status_code}, {response.text}")
#             return None
#     else:
#         print("Failed to acquire token")
#         return None
def get_files_from_sharepoint_folder(client_id, client_secret, tenant_id, site_id, folder_path):
    graph_url = "https://graph.microsoft.com/v1.0"

    app = ConfidentialClientApplication(
        client_id,
        authority=f"https://login.microsoftonline.com/{tenant_id}",
        client_credential=client_secret
    )

    result = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
    if "access_token" in result:
        api_url = f"{graph_url}/sites/{site_id}/drive/root:{folder_path}:/children"
        headers = {
            'Authorization': 'Bearer ' + result['access_token']
        }

        file_list = []
        while api_url:
            response = requests.get(api_url, headers=headers)
            if response.status_code == 200:
                files_data = response.json()
                file_list.extend([file['name'] for file in files_data.get('value', []) if file.get('file')])
                api_url = files_data.get('@odata.nextLink', None)  # Get the next page URL if it exists
            else:
                print(f"Error: {response.status_code}, {response.text}")
                return None

        return file_list
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
            if df is not None and not df.empty:
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

# def extract_datetime(file_name, name=''):
#     match = re.search(r'data_(\d{4}-\d{2}-\d{2}-\d{2}-\d{2})', file_name)
#     if match:
#         return datetime.strptime(match.group(1), '%Y-%m-%d-%H-%M')
#     return datetime.min

# def extract_curr(file_name, name=''):
#     match = re.search(r'data_Cur(\d{4}-\d{2}-\d{2}-\d{2}-\d{2})', file_name)
#     if match:
#         return datetime.strptime(match.group(1), '%Y-%m-%d-%H-%M')
#     return datetime.min

# def extract_dv01(file_name, name=''):
#     match = re.search(r'data_DV0(\d{4}-\d{2}-\d{2}-\d{2}-\d{2})', file_name)
#     if match:
#         return datetime.strptime(match.group(1), '%Y-%m-%d-%H-%M')
#     return datetime.min

# def extract_cvar(file_name, name=''):
#     match = re.search(r'data_VaR(\d{4}-\d{2}-\d{2}-\d{2}-\d{2})', file_name)
#     if match:
#         return datetime.strptime(match.group(1), '%Y-%m-%d-%H-%M')
#     return datetime.min

def extract_datetime(file_name, data_type=''):
    pattern_mapping = {
        '': r'data_(\d{4}-\d{2}-\d{2}-\d{2}-\d{2})',
        'Cur': r'data_Cur(\d{4}-\d{2}-\d{2}-\d{2}-\d{2})',
        'DV0': r'data_DV0(\d{4}-\d{2}-\d{2}-\d{2}-\d{2})',
        'VaR': r'data_VaR(\d{4}-\d{2}-\d{2}-\d{2}-\d{2})'
    }

    pattern = pattern_mapping.get(data_type)
    match = re.search(pattern, file_name)

    if match:
        return datetime.strptime(match.group(1), '%Y-%m-%d-%H-%M')

    return datetime.min

def create_heatmap(data, title):
    data = data.groupby('Currency').sum()
    data['Total DV01'] = data.sum(axis=1)
    fig = px.imshow(data, 
                    labels=dict(x="Bucket", y="Currency", color="DV01"),
                    x=data.columns, 
                    y=data.index,
                    color_continuous_scale="RdBu_r",
                    title=title)
    fig.update_layout(height=600, width=1000)
    return fig

def create_dv01_bar_chart(data, title, x_title, y_title):
    fig = px.bar(data, 
                 x=data.index, 
                 y=data.values, 
                 title=title,
                 labels={"x": x_title, "y": y_title})
    fig.update_layout(height=600)
    return fig

def get_data(selected_date):
    CLIENT_ID = st.secrets["CLIENT_ID"]
    CLIENT_SECRET = st.secrets["CLIENT_SECRET"]
    TENANT_ID = st.secrets["TENANT_ID"]
    SITE_ID = st.secrets["SITE_ID"]
    aest = pytz.timezone('Australia/Sydney')
    current_hour = datetime.now(aest).hour

    all_files = get_files_from_sharepoint_folder(CLIENT_ID, CLIENT_SECRET, TENANT_ID, SITE_ID, folder_path="/ProfitLoss")

    most_recent_file = max(all_files, key=lambda file: extract_datetime(file, data_type=''))
    most_recent_time = extract_datetime(most_recent_file)

    most_recent_curr = max(all_files, key=lambda file: extract_datetime(file, data_type='Cur'))
    most_recent_dv01 = max(all_files, key=lambda file: extract_datetime(file, data_type='DV0'))
    most_recent_cvar = max(all_files, key=lambda file: extract_datetime(file, data_type='VaR'))
    # max_date = max([datetime.strptime(f.split('_')[1].replace('.csv', ''), '%Y-%m-%d-%H-%M') for f in all_files])
    # st.write(max_date)
    # formatted_time = max_date
    formatted_time = f"{selected_date.strftime('%Y-%m-%d')}-08-00"
    # formatted_time = f"{selected_date.strftime('%Y-%m-%d')}-{current_hour:02d}-00"

   
    
    # FILE_PATH = generate_file_path(formatted_time)
    FILE_PATH = f"/ProfitLoss/{most_recent_file}"

    df = get_csv_from_sharepoint_by_path(CLIENT_ID, CLIENT_SECRET, TENANT_ID, SITE_ID, FILE_PATH)

    curr_exposure_df = get_csv_from_sharepoint_by_path(CLIENT_ID, CLIENT_SECRET, TENANT_ID, SITE_ID, f'/ProfitLoss/{most_recent_curr}')
    dv01_df = get_csv_from_sharepoint_by_path(CLIENT_ID, CLIENT_SECRET, TENANT_ID, SITE_ID, f'/ProfitLoss/{most_recent_dv01}')
    cvar_df = get_csv_from_sharepoint_by_path(CLIENT_ID, CLIENT_SECRET, TENANT_ID, SITE_ID, f'/ProfitLoss/{most_recent_cvar}')
    
    return most_recent_time, df, curr_exposure_df, dv01_df, cvar_df