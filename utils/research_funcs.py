import pandas as pd
import plotly.graph_objects as go
import streamlit as st


def display_metrics(documents):
    # Convert file_created_at to datetime
    documents_df = pd.DataFrame(documents)
    documents_df['file_created_at'] = pd.to_datetime(documents_df['file_created_at'], errors='coerce', utc=True)
    # Group by file_created_at and count the number of documents
    documents_by_day = documents_df.groupby(documents_df['file_created_at'].dt.date).size().reset_index(name='count')
    
    # Create the plotly figure
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=documents_by_day['file_created_at'],
        y=documents_by_day['count'],
        mode='lines+markers',
        name='Number of Documents'
    ))
    
    # Update layout
    fig.update_layout(
        title='Number of Documents by Day',
        xaxis_title='Date',
        yaxis_title='Number of Documents',
        height=600,
        width=1000
    )
    
    # Display the plot using Streamlit
    st.plotly_chart(fig, use_container_width=True)