import streamlit as st
import pandas as pd
from datetime import datetime
from pinecone import Pinecone, ServerlessSpec
from semantic_router.encoders import OpenAIEncoder
import time
from openai import OpenAI
from utils.chat_funcs import check_password

if not check_password():
    st.stop()

st.title("Research Portal")

@st.cache_resource
def init_connections():
    encoder = OpenAIEncoder(name="text-embedding-3-large", openai_api_key=st.secrets["OPENAI_API_KEY_MKR"])
    pc = Pinecone(api_key=st.secrets["PINECONE_API_KEY"])
    spec = ServerlessSpec(cloud="aws", region="us-east-1")
    index_name = st.secrets["PINECONE_INDEX_NAME"]
    if index_name not in pc.list_indexes().names():
        st.write("Index not found. Try again later.")
    else:
        index = pc.Index(index_name)
    oai_client = OpenAI(api_key=st.secrets["OPENAI_API_KEY_MKR"])
    return encoder, index, oai_client

@st.cache_data
def get_document_list(_index):
    results = index.query(
        vector=[0]*3072,
        top_k=1000,
        include_metadata=True
    )
    return [match['metadata'] for match in results['matches']]


def display_documents(documents, filters):
    filtered_docs = documents

    if filters['file_name']:
        filtered_docs = [doc for doc in filtered_docs if filters['file_name'].lower() in doc['document_title'].lower()]
    
    if filters['start_date'] and filters['end_date']:
        filtered_docs = [doc for doc in filtered_docs if filters['start_date'] <= datetime.strptime(doc['file_created_at'].split('T')[0], '%Y-%m-%d').date() <= filters['end_date']]
    
    if filters['file_sender']:
        filtered_docs = [doc for doc in filtered_docs if filters['file_sender'].lower() in doc['file_sender'].lower()]

    if filtered_docs:
        # Create a DataFrame with unique documents based on document_title
        unique_docs = pd.DataFrame(filtered_docs).drop_duplicates(subset='document_title')

        unique_docs['Summary'] = "AI Summary"

        summaries = [
            "This article explores the impact of recent monetary policy decisions on global markets. It analyzes how central banks' interest rate adjustments have influenced inflation rates, currency valuations, and international trade. The author argues that coordinated efforts among major economies are crucial for maintaining economic stability in an increasingly interconnected world.",
            "The study examines the long-term effects of automation on labor markets. It presents data showing both job displacement and creation across various sectors, highlighting the need for adaptive workforce strategies. The researchers conclude that while automation poses challenges, it also offers opportunities for economic growth and improved productivity.",
            "This paper investigates the relationship between environmental regulations and economic performance in developing countries. Through case studies and statistical analysis, it demonstrates that well-designed green policies can stimulate innovation and create new markets. The authors propose a framework for balancing environmental protection with economic development goals."
        ]

        for i, summary in enumerate(summaries):
            if i<len(unique_docs):
                unique_docs.iloc[i, unique_docs.columns.get_loc('Summary')] = summary
        
        for _, doc in unique_docs.iterrows():
            if 'web_url' in doc and doc['web_url']:
                unique_docs.loc[_, 'web_url'] = f"[{doc['document_title']}]({doc['web_url']})"
            else:
                unique_docs.loc[_, 'web_url'] = f"{doc['document_title']} (No URL available)"
        df_to_display = unique_docs[['document_title', 'file_created_at', 'file_sender', 'Summary', 'web_url']]
        
        df_to_display = df_to_display.rename(columns={
            'document_title': 'Document Title',
            'file_created_at': 'File Created At',
            'file_sender': 'File Sender'
        })
        st.data_editor(
            df_to_display,
            column_config={
                "web_url": st.column_config.LinkColumn("URL", width="medium"),
                "Summary": st.column_config.TextColumn("Summary", 
                                                       help="AI Summary of the document",
                                                       width="large")
            },
            hide_index=True,
            use_container_width=True
        )
    else:
        st.write("No documents found matching the filters.")

# Main app
pc, index, oai_client = init_connections()


if 'documents' not in st.session_state:
    st.session_state.documents = get_document_list(index)

if st.button('Refresh Document List'):
    # Create spinner
    with st.spinner("Refreshing Document List"):
        st.session_state.documents = get_document_list(index)

st.divider()
st.write("**Thematic Search**")
col1, col2 = st.columns(2)
with col1:
    search_theme = st.multiselect("Enter a theme", ['Inflation', 'CPI', 'Central Banks', 'FX', 'Options', 'Commodity News', 'Trade Recommendations'])
with col2:
    country_theme = st.multiselect("Pick a Country", ['Australia', 'UK', 'US', 'Eurozone'])

st.divider()
st.write("**Advanced Search**")
# Filters
documents_df = pd.DataFrame(st.session_state.documents)
file_name_filter = st.multiselect("File Name", documents_df['document_title'].unique())
date_range = st.date_input("Select Date Range", [])
file_sender_filter = st.multiselect("File Sender", documents_df['file_sender'].unique())

# If a date range is selected, split it into start and end dates
if len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date, end_date = None, None

filters = {
    'file_name': file_name_filter,
    'start_date': start_date,
    'end_date': end_date,
    'file_sender': file_sender_filter
}

display_documents(st.session_state.documents, filters)

