# Library Imports
import requests
import streamlit as st
import pandas as pd
from io import StringIO
import re
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
from plotly.subplots import make_subplots
from msal import ConfidentialClientApplication
import base64
import os
import mimetypes
import msal
from datetime import datetime
import uuid


def send_email(interval, recipients, data, dv01_data, cvar_data, curr_exp_data, formatted_date):
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
        if not isinstance(description, str):
            description = str(description)
        match = re.search(r'[A-Z]{3}/[A-Z]{3}', description)
        if match:
            return match.group(0)
        return None

    def generate_pnl_charts(data, interval):
        total_pnl = data.groupby("Book Name")[f'$ {interval} P&L'].sum().reset_index()
        total_pnl.columns = ['Book Name', f'Total {interval} P&L']
        # Overall PNL
        fig_total = px.bar(total_pnl, x='Book Name', y=f'Total {interval} P&L', title = f'Total {interval} P&L by Book')
        fig_total.update_layout(xaxis_title="Book Name", yaxis_title=f"Total {interval} P&L (USD)", hovermode="closest")
        img_path = os.path.abspath(os.path.join(os.getcwd(), "images", "total_pnl.png"))
        pio.write_image(fig_total, "images/total_pnl.png", width=1000, height=1000, engine="kaleido")
        fig_total.write_image(img_path, width=1000, height=1000, engine="kaleido")

        # Currency PNL
        currency_data = data[data["Book Name"].isin(['DM FX', 'EM FX'])]
        currency_data = currency_data[((currency_data['Quantity'] != 0) | (currency_data[f'$ {interval} P&L'] != 0))]
        currency_data.loc[:, 'Currency Pair'] = currency_data['Description'].apply(lambda x : extract_currency_pair(x))

        fig1 = make_subplots(specs=[[{"secondary_y": True}]])
        fig1.add_trace(
            go.Bar(x=currency_data['Currency Pair'], y=currency_data['Quantity'], name='Quantity'), secondary_y=False
        )
        fig1.add_trace(
            go.Scatter(x=currency_data['Currency Pair'], y=currency_data[f'$ {interval} P&L'], name=f"{interval} P&L", mode='markers', marker=dict(
                color='black', size=5, symbol='diamond'
            )), secondary_y=True
        )
        fig1.update_layout(title_text="FX Positions", xaxis_title="Currency", hovermode="closest")
        fig1.update_yaxes(title_text="Quantity", secondary_y=False)
        fig1.update_yaxes(title_text=f"$ {interval} P&L", secondary_y=True)
        img_path = os.path.abspath(os.path.join(os.getcwd(), "images", "fx_positions.png"))
        fig1.write_image(img_path, width=1000, height=1000, engine="kaleido")

        # Futures Charts
        futures_data = data[data["Book Name"].isin(['Equity trading', 'Short term trading', 'Commodities'])]
        futures_data = futures_data[((futures_data['Quantity'] != 0) | (futures_data[f'$ {interval} P&L'] != 0))]

        fig2 = make_subplots(specs=[[{"secondary_y": True}]])
        fig2.add_trace(
            go.Bar(x=futures_data['Description'], y=futures_data['$ Overall Cost'], name='Overall Cost'), secondary_y=False
        )
        fig2.add_trace(
            go.Scatter(x=futures_data['Description'], y=futures_data[f'$ {interval} P&L'], name=f"{interval} P&L", mode='markers', marker=dict(
                color='black', size=5, symbol='diamond'
            )), secondary_y=True
        )
        fig2.update_layout(title_text="Futures Positions", xaxis_title="Description", hovermode="closest")
        fig2.update_yaxes(title_text="$ Overall Cost", secondary_y=False)
        fig2.update_yaxes(title_text=f"$ {interval} P&L", secondary_y=True)
        fig2.write_image("images/futures_positions.png", width=1000, height=1000, engine="kaleido")

        # Futures Rates Data
        rates_data = data[data["Book Name"].isin(['USD rates', 'DM Rates'])]
        rates_data = rates_data[((rates_data['Quantity'] != 0) | (rates_data[f'$ {interval} P&L'] != 0))]

        fig10 = make_subplots(specs=[[{"secondary_y": True}]])
        fig10.add_trace(
            go.Bar(x=rates_data['Description'], y=rates_data['Book DV01'], name='DV01'), secondary_y=False
        )
        fig10.add_trace(
            go.Scatter(x=rates_data['Description'], y=rates_data[f'$ {interval} P&L'], name=f"{interval} P&L", mode='markers', marker=dict(
                color='black', size=5, symbol='diamond'
            )), secondary_y=True
        )
        fig10.update_layout(title_text="Rates Futures Positions", xaxis_title="Description", hovermode="closest")
        fig10.update_yaxes(title_text="DV01", secondary_y=False)
        fig10.update_yaxes(title_text=f"$ {interval} P&L", secondary_y=True)
        fig10.write_image("images/rates_positions.png", width=1000, height=1000, engine="kaleido")


        # Swaps Charts
        swaps_data = data[data["Book Name"].isin(['Cross Market Rates', 'AUD Rates', 'NZD Rates'])]
        swaps_data = swaps_data[((swaps_data['Quantity'] != 0) | (swaps_data[f'$ {interval} P&L'] != 0))]
        fig3 = make_subplots(specs=[[{"secondary_y": True}]])
        fig3.add_trace(go.Bar(x=swaps_data['Description'], y=swaps_data['Book DV01'], name='DV01'), secondary_y=False)
        fig3.add_trace(go.Scatter(x=swaps_data['Description'], y=swaps_data[f'$ {interval} P&L'], name=f"{interval} P&L", mode='markers', marker=dict(
                color='black', size=5, symbol='diamond'
            )), secondary_y=True)
        fig3.update_layout(title_text="Swaps Positions", xaxis_title="Description", hovermode="closest")
        fig3.update_yaxes(title_text="DV01", secondary_y=False)
        fig3.update_yaxes(title_text=f"$ {interval} P&L", secondary_y=True)
        fig3.write_image("images/swaps_positions.png", width=1000, height=1000, engine="kaleido")

        # Options Charts

        options_data = data[data["Book Name"].isin(['FX options'])]
        options_data = options_data[(options_data['Quantity'] != 0) | (options_data[f'$ {interval} P&L'] != 0)]
        fig4 = make_subplots(specs=[[{"secondary_y": True}]])
        fig4.add_trace(
            go.Bar(x=options_data['Description'], y=options_data['Quantity'], name='Quantity'),
            secondary_y=False
        )
        fig4.add_trace(
            go.Scatter(x=options_data['Description'], y=options_data[f'$ {interval} P&L'], name=f"{interval} P&L", mode='markers', marker=dict(
                color='black', size=5, symbol='diamond'
            )),
            secondary_y=True
        )
        fig4.update_layout(
            title_text="Options Positions",
            xaxis_title="Description",
            hovermode="closest"
        )
        fig4.update_yaxes(title_text="Quantity", secondary_y=False)
        fig4.update_yaxes(title_text=f"$ {interval} P&L", secondary_y=True) 
        fig4.write_image("images/options_positions.png", width=1000, height=1000, engine="kaleido")
        return total_pnl

    def generate_message(subject, body_content, images, to_recipients, df=None, cc_recipients=None, logo_path = 'images/Original Logo.png'):
        message = {
            "subject": subject,
            "body": {
                "contentType": "HTML",
                "content": ""
            },
            "toRecipients": [{"emailAddress": {"address": recipient}} for recipient in to_recipients],
            "attachments": []
        }

        if cc_recipients:
            message["ccRecipients"] = [{"emailAddress": {"address": recipient}} for recipient in cc_recipients]

        html_content = "<html><body style='font-family: Arial, sans-serif;'>"
        if logo_path:
            with open(logo_path, "rb") as logo_file:
                logo_data = logo_file.read()
                logo_base64 = base64.b64encode(logo_data).decode("utf-8")
            
            logo_content_type, _ = mimetypes.guess_type(logo_path)
            logo_content_id = str(uuid.uuid4())

            logo_attachment = {
                "@odata.type": "#microsoft.graph.fileAttachment",
                "name": "logo.png",  
                "contentType": logo_content_type,
                "contentBytes": logo_base64,
                "contentId": logo_content_id,
                "isInline": True
            }

            message["attachments"].append(logo_attachment)
            html_content += f'<div style="text-align: center; margin-bottom: 20px;"><img src="cid:{logo_content_id}" alt="Logo" style="max-width: 200px; height: auto;"></div>'
        
        
        html_content += body_content

        for image_path in images:
            with open(image_path, "rb") as image_file:
                image_data = image_file.read()
                image_base64 = base64.b64encode(image_data).decode("utf-8")

            file_name = os.path.basename(image_path)
            content_type, _ = mimetypes.guess_type(image_path)
            content_id = str(uuid.uuid4())

            attachment = {
                "@odata.type": "#microsoft.graph.fileAttachment",
                "name": file_name,
                "contentType": content_type,
                "contentBytes": image_base64,
                "contentId": content_id,
                "isInline": True
            }

            message["attachments"].append(attachment)
            html_content += f'<img src="cid:{content_id}" alt="{file_name}">'
            if file_name == 'total_pnl.png' and df is not None:
                html_content += "<h3>Data Table:</h3>"
                html_content += df.to_html(index=False, classes='dataframe', border=1)
                html_content += """
                <style>
                .dataframe {
                    border-collapse: collapse;
                    margin: 10px 0;
                    font-size: 0.9em;
                    font-family: Arial, sans-serif;
                    min-width: 400px;
                    box-shadow: 0 0 20px rgba(0, 0, 0, 0.15);
                }
                .dataframe thead tr {
                    background-color: #009879;
                    color: #ffffff;
                    text-align: left;
                }
                .dataframe th,
                .dataframe td {
                    padding: 12px 15px;
                }
                .dataframe tbody tr {
                    border-bottom: 1px solid #dddddd;
                }
                .dataframe tbody tr:nth-of-type(even) {
                    background-color: #f3f3f3;
                }
                .dataframe tbody tr:last-of-type {
                    border-bottom: 2px solid #009879;
                }
                </style>
                """


        html_content += "</body></html>"
        message["body"]["content"] = html_content

        return message
    
    def send_email_with_attachment(json_message, user_email, file_path=None):
        tenant_id = st.secrets['MAIL_TENANT_ID']
        authority_url = f'https://login.microsoftonline.com/{tenant_id}'
        scopes = ['https://graph.microsoft.com/.default']

        app = msal.ConfidentialClientApplication(
            st.secrets['MAIL_CLIENT_ID'],
            authority=authority_url,
            client_credential=st.secrets['MAIL_CLIENT_SECRET'],
        )

        result = app.acquire_token_for_client(scopes=scopes)

        if 'access_token' in result:
            access_token = result['access_token']
        else:
            print('Error obtaining access token')
            print(result)
            return None

        # Prepare the attachment
        if file_path:
            file_name = os.path.basename(file_path)
            with open(file_path, 'rb') as file:
                file_content = file.read()
            
            encoded_file = base64.b64encode(file_content).decode('utf-8')
            time_to_send = datetime.now().strftime('%d-%m-%Y_%H:%M')
            # Make Pretty
            file_name = file_name.replace(".xlsx", "")

            # Add attachment to the message
            json_message['attachments'] = [{
                '@odata.type': '#microsoft.graph.fileAttachment',
                'name': file_name + f'_{time_to_send}.xlsx',
                'contentBytes': encoded_file
            }]

        send_mail_body = {
            "message": json_message,
            "saveToSentItems": "true"
        }

        # Send the email with attachment
        endpoint = f'https://graph.microsoft.com/v1.0/users/{user_email}/sendMail'
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json',
        }

        response = requests.post(endpoint, headers=headers, json=send_mail_body)

        if response.status_code == 202:
            print('Email sent successfully with attachment')
        else:
            print('Error sending email')
            print(response.json())
        
        return response

    today = datetime.now()
    date_str = today.strftime("%m/%d/%Y")
    latest_hour = today.hour
    date_spt = today.strftime("%Y-%m-%d")
    # formatted_date = f"{date_spt}-{latest_hour:02d}-00"
    pio.templates.default = "plotly"

    df = data

    exclude_columns = ['Book Name', 'Holding Scenario', 'Description', 'Active']

    for column in df.columns:
        if column not in exclude_columns:
            df[column] = df[column].apply(convert_to_float)

    total_pnl_df = generate_pnl_charts(df, interval)
    total_pnl_df[f'Total {interval} P&L'] = total_pnl_df[f'Total {interval} P&L'].apply(lambda x: f'${x:,.2f}')

    # Calculate the grand total
    grand_total = total_pnl_df[f'Total {interval} P&L'].str.replace('$', '').str.replace(',', '').astype(float).sum()

    # Create a new row for the grand total
    grand_total_row = pd.DataFrame({'Book Name': ['Grand Total'], f'Total {interval} P&L': [f'${grand_total:,.2f}']})

    # Concatenate the original dataframe with the grand total row
    total_pnl_df = pd.concat([total_pnl_df, grand_total_row], ignore_index=True)

    # Rename the column to reflect dollar values
    total_pnl_df = total_pnl_df.rename(columns={f'Total {interval} P&L': f'Total {interval} P&L ($)'})
        # Send email with charts
    
    subject = f"P&L Update - {formatted_date}"
    if dv01_data is not None and cvar_data is not None and curr_exp_data is not None:
        dv01_total = dv01_data.drop(columns=['Description', 'Date']).groupby('Currency').sum().sum(axis=1)[:-1]['Grand Total']
        cvar_total = cvar_data.iloc[-1]['Daily Fund CVaR']
        total_USD = curr_exp_data[curr_exp_data['Currency']=='USD']['Book NMV (Total)'].values[0]

        body_content = f"""
        <body>
            <p>Hi All,</p>
            <p>Please find the {interval} P&L update below.</p>
            <p>The report was last updated at {formatted_date}.</p>
            <p>Total DV01 is ${dv01_total:,.2f}, Total CVaR is ${cvar_total:,.2f} and Total USD Exposure is ${total_USD:,.2f}.</p>
            <p>To access this report online, please <a href="https://mkrcapital.streamlit.app/">click here</a>.</p>
            <p>Thanks.</p>
        </body>

        """
    else:
        body_content = f"""
        <body>
            <p>Hi All,</p>
            <p>Please find the {interval} P&L update below.</p>
            <p>The report was last updated at {formatted_date}.</p>
            <p>To access this report online, please <a href="https://mkrcapital.streamlit.app/">click here</a>.</p>
            <p>Thanks.</p>
        </body>

        """
    images = ["images/total_pnl.png", "images/fx_positions.png", "images/futures_positions.png", "images/rates_positions.png","images/swaps_positions.png", "images/options_positions.png"]

    
    # recievers = ["bposwell@mkrcapital.com.au", "arowe@mkrcapital.com.au", "james.austin@missioncrestcapital.com"]

    # recievers = ["bposwell@gmail.com"]
    message = generate_message(
        subject=subject,
        body_content=body_content,
        images=images,
        to_recipients=recipients,
        df=total_pnl_df,
        cc_recipients=[]
    )

    send_email_with_attachment(
        json_message=message,
        user_email="bposwell@mkrcapital.com.au"
    )

def send_html_email(subject, html_content, recipients):
    def generate_message(subject, body_content, to_recipients, cc_recipients=None, logo_path = 'images/Original Logo.png'):
        message = {
            "subject": subject,
            "body": {
                "contentType": "HTML",
                "content": ""
            },
            "toRecipients": [{"emailAddress": {"address": recipient}} for recipient in to_recipients],
            "attachments": []
        }

        if cc_recipients:
            message["ccRecipients"] = [{"emailAddress": {"address": recipient}} for recipient in cc_recipients]

        html_content = "<html><body style='font-family: Arial, sans-serif;'>"
        if logo_path:
            with open(logo_path, "rb") as logo_file:
                logo_data = logo_file.read()
                logo_base64 = base64.b64encode(logo_data).decode("utf-8")
            
            logo_content_type, _ = mimetypes.guess_type(logo_path)
            logo_content_id = str(uuid.uuid4())

            logo_attachment = {
                "@odata.type": "#microsoft.graph.fileAttachment",
                "name": "logo.png",  
                "contentType": logo_content_type,
                "contentBytes": logo_base64,
                "contentId": logo_content_id,
                "isInline": True
            }

            message["attachments"].append(logo_attachment)
            html_content += f'<div style="text-align: center; margin-bottom: 20px;"><img src="cid:{logo_content_id}" alt="Logo" style="max-width: 200px; height: auto;"></div>'
        
        
        html_content += body_content

        html_content += "</body></html>"
        message["body"]["content"] = html_content

        return message
    
    def send_email_with_attachment(json_message, user_email, file_path=None):
        tenant_id = st.secrets['MAIL_TENANT_ID']
        authority_url = f'https://login.microsoftonline.com/{tenant_id}'
        scopes = ['https://graph.microsoft.com/.default']

        app = msal.ConfidentialClientApplication(
            st.secrets['MAIL_CLIENT_ID'],
            authority=authority_url,
            client_credential=st.secrets['MAIL_CLIENT_SECRET'],
        )

        result = app.acquire_token_for_client(scopes=scopes)

        if 'access_token' in result:
            access_token = result['access_token']
        else:
            print('Error obtaining access token')
            print(result)
            return None

        # Prepare the attachment
        if file_path:
            file_name = os.path.basename(file_path)
            with open(file_path, 'rb') as file:
                file_content = file.read()
            
            encoded_file = base64.b64encode(file_content).decode('utf-8')
            time_to_send = datetime.now().strftime('%d-%m-%Y_%H:%M')
            # Make Pretty
            file_name = file_name.replace(".xlsx", "")

            # Add attachment to the message
            json_message['attachments'] = [{
                '@odata.type': '#microsoft.graph.fileAttachment',
                'name': file_name + f'_{time_to_send}.xlsx',
                'contentBytes': encoded_file
            }]

        send_mail_body = {
            "message": json_message,
            "saveToSentItems": "true"
        }

        # Send the email with attachment
        endpoint = f'https://graph.microsoft.com/v1.0/users/{user_email}/sendMail'
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json',
        }

        response = requests.post(endpoint, headers=headers, json=send_mail_body)

        if response.status_code == 202:
            print('Email sent successfully with attachment')
        else:
            print('Error sending email')
            print(response.json())
        
        return response
    
    
    message = generate_message(
        subject=subject,
        body_content=html_content,
        to_recipients=recipients,
        cc_recipients=[]
    )

    send_email_with_attachment(
        json_message=message,
        user_email="bposwell@mkrcapital.com.au"
    )





    
    
