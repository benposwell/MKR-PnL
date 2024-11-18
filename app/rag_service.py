import time
import json
import unicodedata
import re
from semantic_router.encoders import OpenAIEncoder
from pinecone import Pinecone, ServerlessSpec
from openai import OpenAI
import streamlit as st

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

# def get_document_title(doc_id, index):
#     matches = index.fetch(ids=[doc_id])
#     return matches[doc_id]['metadata']['document_title']

def gen_query_context(text, index, encoder, filters, search_comprehensiveness):
    query_filter = {}
    for f in filters:
        query_filter.update(f)
    filter = query_filter
    encoded_query = encoder([text])[0]

    top_k = int(5*search_comprehensiveness)
    matches = index.query(
        vector=encoded_query,
        top_k=top_k,
        include_metadata=True,
        filter=filter
    )
    chunks = []
    sources = []
    source_ids = {}
    source_counter = 1
    for m in matches["matches"]:
        content = m["metadata"]["content"]
        title = m["metadata"]["document_title"]
        web_url = m["metadata"].get("web_url", "")
        pre = m["metadata"]["prechunk_id"]
        post = m["metadata"]["postchunk_id"]
        ids_to_fetch = [id for id in [pre, post] if id != '']
        if ids_to_fetch:
            other_chunks = index.fetch(ids=ids_to_fetch)["vectors"]
        else:
            other_chunks = {}

        prechunk = other_chunks.get(pre, {}).get("metadata", {}).get("content", "")
        postchunk = other_chunks.get(post, {}).get("metadata", {}).get("content", "")

        if title not in source_ids:
            source_ids[title] = source_counter
            source_counter += 1
            sources.append({
                "id": source_ids[title],
                 "title": title,
                 "url": web_url,
                 "created_at": m["metadata"]["file_created_at"]
            })
        
        source_id = source_ids[title]

        chunk = f"""[{source_id}] {title}

        {prechunk[-400:]}
        {content}
        {postchunk[:400]}"""
        chunks.append(chunk)
    return chunks, sources

def query_openai(question, chunks, conversation, oai_client, sources, model="gpt-4o", answer_detail=1.0):
    base_system_message = (
        f"You are an AI financial analyst assistant. When providing answers, ensure that you:\n"
        f"1. Include as many relevant perspectives and views as possible from the context, eliminating any directional bias.\n"
        f"2. Maintain extreme accuracy and attention to detail. Provide correct numbers and confirm the existence of events or data as per the context. Strive for completeness and do not exclude any relevant events or misquote forecasts.\n"
        f"3. Be thoughtful and strictly relevant. Exclude courteous statements or unnecessary information not directly related to the query and context.\n"
        f"4. If the relevant information is not present in the context, clearly state that you cannot find the information.\n"
        f"5. Consider second-order effects and interrelated events discussed in the context when formulating your answer.\n"
        f"6. When referencing information from the context, include citations using the source numbers provided.\n"
        f"Remember, your primary goal is to provide accurate, relevant, and unbiased financial analysis based solely on the given context and conversation history.\n"
    )

    if answer_detail < 0.5:
        system_message = base_system_message + f"\nProvide brief and concise answers."
    elif answer_detail < 1.0:
        system_message = base_system_message + f"\nProvide detailed answers, but keep them concise."
    else:
        system_message = base_system_message + f"\nProvide detailed and comprehensive answers."

    def sanitize_text(text):
        if text is None:
            return ""
        text = unicodedata.normalize('NFKD', text)
        text = text.encode('ascii', 'ignore').decode('ascii')
        text = re.sub(r'[^\x20-\x7E\n\t]', '', text)
        return text.replace("\xa0", " ").replace("■", "-").replace("\u2028", " ").replace("\u2029", " ")
    
    sanitized_chunks = [sanitize_text(chunk) for chunk in chunks]
    sanitized_conversation = sanitize_text(conversation)
    sanitized_question = sanitize_text(question)

    source_strings = [f"[{source['id']}] {source['title']}" for source in sources]
    sanitized_sources = [sanitize_text(source_str) for source_str in source_strings]

    # sanitized_sources = [sanitize_text(source) for source in sources]

    user_content = (
        "Analyze the following context and conversation history to answer the current question. Ensure your response aligns with the guidelines provided in the system message.\n\n"
        "Sources:\n" + '\n'.join(sanitized_sources) + "\n\n"
        f"Context information:\n{' '.join(sanitized_chunks)}\n\n"
        f"Conversation history:\n{sanitized_conversation}\n\n"
        f"Current question: {sanitized_question}\n\n"
        "Answer:"
    )

    try:
        completion = oai_client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_content}
        ],
        temperature=0.5,
        stream=True
        )
        return completion
    except Exception as e:
        return f"An error occurred while querying OpenAI: {e}"
    
def rag_pipeline(question, index, conversation, encoder, oai_client, filters, search_comprehensiveness, answer_detail):
    chunks, sources = gen_query_context(question, index, encoder, filters, search_comprehensiveness)
    if len(chunks) == 0:
        return "No context found for this question. Please try again", []
    return query_openai(
        question=question, 
        chunks=chunks, 
        conversation=conversation, 
        oai_client=oai_client, 
        sources=sources,
        answer_detail=answer_detail), sources