import streamlit as st
import pandas as pd
from datetime import datetime
from pinecone import Pinecone, ServerlessSpec
from semantic_router.encoders import OpenAIEncoder
import time
from openai import OpenAI
from utils.chat_funcs import check_password, generate_chat_url
from utils.research_funcs import display_metrics

if not check_password():
    st.stop()

st.title("BRAG Research Portal")

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

# @st.cache_data
def get_document_list(_index):
    results = index.query(
        vector=[0]*3072,
        top_k=10000,
        include_metadata=True
    )
    return [match['metadata'] for match in results['matches']]


def display_documents(documents, filters):
    filtered_docs = documents

    if filters['file_text']:
        filtered_docs = [doc for doc in filtered_docs if filters['file_text'].lower() in doc['document_title'].lower()]

    if filters['file_name']:
        filtered_docs = [doc for doc in filtered_docs if filters['file_name'].lower() in doc['document_title'].lower()] # BUG IN THIS LINE
    
    if filters['start_date'] and filters['end_date']:
        filtered_docs = [doc for doc in filtered_docs if filters['start_date'] <= datetime.strptime(doc['file_created_at'].split('T')[0], '%Y-%m-%d').date() <= filters['end_date']]
    
    if filters['sender_text']:
        filtered_docs = [doc for doc in filtered_docs if filters['sender_text'].lower() in doc['file_sender'].lower()]

    if filters['file_sender']:
        if isinstance(filters['file_sender'], list):
            filtered_docs = [doc for doc in filtered_docs if any(sender.lower() in doc['file_sender'].lower() for sender in filters['file_sender'])]
        else:
            filtered_docs = [doc for doc in filtered_docs if filters['file_sender'].lower() in doc['file_sender'].lower()]

    if filtered_docs:
        # Create a DataFrame with unique documents based on document_title
        unique_docs = pd.DataFrame(filtered_docs).drop_duplicates(subset='document_title')

        unique_docs['BRAG Summary'] = unique_docs.apply(lambda row: generate_chat_url(
            prompt=f"Provide a summary of the analysis contained within the document titled {row['document_title']}. Include all key points and findings.",
            doc_id = row['doc_id'],
            min_date=None,
            max_date=None,
            search_comprehensiveness=None,
            answer_detail=None
        ), axis=1)
    
        for _, doc in unique_docs.iterrows():
            if 'web_url' in doc and doc['web_url']:
                unique_docs.loc[_, 'web_url'] = doc['web_url']
            else:
                unique_docs.loc[_, 'web_url'] = f"No URL available"
        # Convert df_to_display['file_created_at'] to a string with format DD-MM-YYYY 

        unique_docs['formatted_datetime'] = unique_docs['file_created_at'].apply(lambda x: x.split('T')[0])
        
        df_to_display = unique_docs[['document_title', 'formatted_datetime', 'file_sender', 'BRAG Summary', 'web_url']]

        df_to_display = df_to_display.rename(columns={
            'document_title': 'Document Title',
            'formatted_datetime': 'File Created At',
            'file_sender': 'File Sender'
        })

        st.data_editor(
            df_to_display,
            column_config={
                "File Created At": st.column_config.TextColumn("File Created At", width="small"),
                "web_url": st.column_config.LinkColumn("URL", width="medium", display_text="View Document in Sharepoint"),
                "BRAG Summary": st.column_config.LinkColumn("BRAG Summary", 
                                                       help="AI Summary of the document",
                                                       width="medium",
                                                       display_text="Generate BRAG Summary")
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

# st.divider()
# st.write("**Thematic Search**")
# col1, col2 = st.columns(2)
# with col1:
#     search_theme = st.multiselect("Enter a theme", ['Inflation', 'CPI', 'Central Banks', 'FX', 'Options', 'Commodity News', 'Trade Recommendations'])
# with col2:
#     country_theme = st.multiselect("Pick a Country", ['Australia', 'UK', 'US', 'Eurozone'])

# st.divider()

# Filters
documents_df = pd.DataFrame(st.session_state.documents)
col1, col2, col3 = st.columns(3)
with col1:
    file_text = st.text_input("Search Documents", "")
    file_name_filter = st.multiselect("Document Title", documents_df['document_title'].unique())
with col2:
    date_range = st.date_input("Select Date Range", [])
with col3:
    sender_text = st.text_input("Search Senders", "")
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
    'file_sender': file_sender_filter,
    'file_text': file_text,
    'sender_text': sender_text
}
# st.write(st.session_state.documents)

display_documents(st.session_state.documents, filters)

display_metrics(st.session_state.documents)

# Create frequency plot of number of documents by day
