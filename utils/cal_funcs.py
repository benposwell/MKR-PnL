import pandas as pd
import streamlit as st
from typing import List, Dict
from datetime import datetime
import math
from pinecone import Pinecone
from pinecone_plugins.assistant.models.chat import Message
import io
from collections import defaultdict
from pymongo import MongoClient
from utils.funcs import get_mongo_access

curr_country_dict = {
    'AUD': 'Australia',
    'NZD': 'New Zealand',
    'USD': 'United States',
    'CAD': 'Canada',
    'GBP': 'United Kingdom',
    'EUR': 'Eurozone',
    'CHF': 'Switzerland',
    'JPY': 'Japan',
    'CNY': 'China',
    'INR': 'India',
    'RUB': 'Russia',
    'ZAR': 'South Africa',
    'BRL': 'Brazil',
    'MXN': 'Mexico',
    'COP': 'Colombia',
    'CLP': 'Chile',
    'PEN': 'Peru',
    'ARS': 'Argentina',
    'UYU': 'Uruguay',
    'PYG': 'Paraguay',
    'BOB': 'Bolivia',
    'VND': 'Vietnam',
    'THB': 'Thailand',
    'IDR': 'Indonesia',
    'MYR': 'Malaysia',
    'SGD': 'Singapore',
    'PHP': 'Philippines',
    'KRW': 'South Korea',
    'HKD': 'Hong Kong',
    'TWD': 'Taiwan',
    'CNY': 'China',
    'INR': 'India',
    'RUB': 'Russia',
    'ZAR': 'South Africa',
    'BRL': 'Brazil',
    'MXN': 'Mexico',
    'COP': 'Colombia',
    'CLP': 'Chile',
    'PEN': 'Peru',
    'ARS': 'Argentina',
    'UYU': 'Uruguay',
    'PYG': 'Paraguay',
    'BOB': 'Bolivia',
    'VND': 'Vietnam',
    'THB': 'Thailand',
    'IDR': 'Indonesia',
    'MYR': 'Malaysia',
    'SGD': 'Singapore',
    'PHP': 'Philippines',
    'KRW': 'South Korea',
    'HKD': 'Hong Kong',
    'TWD': 'Taiwan',
}
country_curr_dict = {
    'Australia': 'AUD',
    'New Zealand': 'NZD',
    'United States': 'USD',
    'Canada': 'CAD',
    'United Kingdom': 'GBP',
    'Eurozone': 'EUR',
    'Switzerland': 'CHF',
    'Japan': 'JPY',
    'China': 'CNY',
    'India': 'INR',
    'Russia': 'RUB',
    'South Africa': 'ZAR',
    'Brazil': 'BRL',
    'Mexico': 'MXN',
    'Colombia': 'COP',
    'Chile': 'CLP',
    'Peru': 'PEN',
    'Argentina': 'ARS',
    'Uruguay': 'UYU',
    'Paraguay': 'PYG',
    'Bolivia': 'BOB',
    'Vietnam': 'VND',
    'Thailand': 'THB',
    'Indonesia': 'IDR',
    'Malaysia': 'MYR',
    'Singapore': 'SGD',
    'Philippines': 'PHP',
    'South Korea': 'KRW',
    'Hong Kong': 'HKD',
    'Taiwan': 'TWD',
    'Turkey': 'TRY',
    'Italy': 'EUR',
    'Indonesia': 'IDR'
}



def generate_batch_prompt(events: pd.DataFrame) -> str:
    curr_exp_data = st.session_state.curr_exp_data
    
    prompt = "Using the reports we have stored from our preferred analysts, please could you provide a brief analysis for the following upcoming economic events. For each event, consider its potential impact on the market, what traders should watch for, and how it might affect the relevant currency exchange rate. If you do not have any relevant information on the particular event, please write 'No Information Available'.\n\n"
    
    
    for _, event in events.iterrows():
        prompt += f"- {event['EVENT_NAME']} ({event['COUNTRY_NAME']}, Impact: {event['RELEVANCY']}, Time: {event['RELEASE_DATE_TIME']})\n"
        curr = country_curr_dict[event['COUNTRY_NAME']]
        if curr_exp_data is not None:
            position = curr_exp_data.loc[curr_exp_data['Currency'] == curr, 'Book NMV (Total)'].values[0] if not curr_exp_data.loc[curr_exp_data['Currency'] == curr, 'Book NMV (Total)'].empty else None
            if position is not None:
                prompt += f"For reference, we have a total of USD ${round(position)} exposure to the {curr} currency.\n"
    prompt += "\nPlease provide your analysis for each event separately."
    print(prompt)
    return prompt

def generate_day_ahead_preview(cal_events, assistant):
    # Filter events for today
    
    today = datetime.now().date()
    today_events = cal_events[cal_events['RELEASE_DATE_TIME'].dt.date == today]
    today_events = today_events.reset_index(drop=True)
    
    report = io.StringIO()
    report.write("""
    <style>
    body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
    h1 { color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; font-size: 24px; text-align: center; }
    h2 { color: #3498db; margin-top: 5px; font-size: 20px; }
    h3 { color: #000000; margin-top: 5px; font-size: 16px; }
    .event { border-bottom: 1px solid #e0e0e0; padding: 10px 0; margin-bottom: 15px; }
    .event-details { font-size: 0.9em; color: #7f8c8d; }
    .analysis { padding: 10px 0; }
    </style>
    """)
    
    report.write(f"<h1>Day Ahead Preview for {today}</h1>")
    
    if today_events.empty:
        report.write("<p>No events scheduled for today.</p>")
        return report.getvalue()
    
    # Group events by currency
    events_by_country = defaultdict(list)
    for _, event in today_events.iterrows():
        events_by_country[event['COUNTRY_NAME']].append(event)
    
    for country, events in events_by_country.items():
        report.write(f"<h2>{country} Events</h2>")
        
        # Calculate the number of batches
        batch_size = 1
        num_batches = math.ceil(len(events) / batch_size)
        
        for i in range(num_batches):
            start_idx = i * batch_size
            end_idx = min((i + 1) * batch_size, len(events))
            batch_events = events[start_idx:end_idx]
            
            # Generate prompt for the batch
            prompt = generate_batch_prompt(pd.DataFrame(batch_events))
            
            # Process with RAG assistant
            chat_context = [Message(content=prompt, role="user")]
            rag_response = ""
            for response in assistant.chat_completions(messages=chat_context, stream=True):
                if response.choices[0].delta.content is not None:
                    rag_response += response.choices[0].delta.content
            
            # Display results for each event in the batch
            for event in batch_events:
                report.write("<div class='event'>")
                report.write(f"<h3>{event['EVENT_NAME']}</h3>")
                print(type(event['SURVEY_MEDIAN']))
                print((event['SURVEY_MEDIAN']))
                report.write(f"<p class='event-details'>Time: {event['RELEASE_DATE_TIME']} | Impact: {event['RELEVANCY']} | Prior: {event['PRIOR'] if not math.isnan(event['PRIOR']) else 'No Prior'} | Frequency: {event['RELEASE_FREQ']} | BBG Median: {event['SURVEY_MEDIAN'] if not math.isnan(event['SURVEY_MEDIAN']) else 'No Survey'} | BBG STD: {round(event['SURVEY_STANDARD_DEVIATION'], 2) if not math.isnan(event['SURVEY_STANDARD_DEVIATION']) else 'No Survey'} </p>")
                
                # Extract the relevant part of the analysis for this event
                event_analysis = rag_response.split(event['EVENT_NAME'])[1].split("###")[0] if event['EVENT_NAME'] in rag_response else "Analysis not available."
                
                report.write("<div class='analysis'>")
                report.write(f"<p>{event_analysis.strip()}</p>")
                report.write("</div>")
                report.write("</div>")

    return report.getvalue()



def store_report(report_html):
    client = get_mongo_access()
    # client = MongoClient(st.secrets["MONGO_URI"])
    db = client[st.secrets["MONGO_DB_NAME"]]
    reports_collection = db["DocumentStore.reports"]
    
    # Update the existing report or insert a new one if it doesn't exist
    reports_collection.update_one(
        {"report_type": "day_ahead_preview"},
        {"$set": {"report": report_html}},
        upsert=True
    )

def get_report():
    client = get_mongo_access()
    # client = MongoClient(st.secrets["MONGO_URI"])
    db = client[st.secrets["MONGO_DB_NAME"]]
    reports_collection = db["DocumentStore.reports"]
    
    # Retrieve the single report
    report = reports_collection.find_one({"report_type": "day_ahead_preview"})
    return report['report'] if report else None