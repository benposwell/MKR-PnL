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


def gen_query_context(text, index, encoder, filters, search_comprehensiveness, doc_id=None):
    """
    Generate query context with adaptive retrieval based on query type and document focus.
    
    Parameters:
    - text: The query text
    - index: Pinecone index
    - encoder: Text encoder
    - filters: List of filter dictionaries
    - search_comprehensiveness: Float indicating search depth multiplier
    - doc_id: Optional specific document ID to focus on
    
    Returns:
    - chunks: List of relevant text chunks
    - sources: List of source documents
    """
    query_filter = {}
    for f in filters:
        if f:  # Only update if filter is not None
            query_filter.update(f)
    
    encoded_query = encoder([text])[0]
    print(f"Encoded query: {encoded_query}")

    # Check if filters contains doc_id
    if 'doc_id' in query_filter:
        doc_id = query_filter['doc_id']
    else:
        doc_id = None
    
    if doc_id:
        # For single-document queries, retrieve more chunks from that specific document
        query_filter['doc_id'] = doc_id
        base_k = 15  # Higher base_k for single document to get more context
    else:
        # For general queries, use a lower base_k but scale with document length
        base_k = 8
    
    # Calculate adaptive top_k based on search comprehensiveness
    top_k = int(base_k * search_comprehensiveness)
    
    # Set reasonable bounds
    top_k = min(max(top_k, 5), 30)  # Never less than 5 or more than 30 chunks
    
    # First query to get initial matches
    matches = index.query(
        vector=encoded_query,
        top_k=top_k,
        include_metadata=True,
        filter=query_filter
    )
    
    chunks = []
    sources = []
    source_ids = {}
    source_counter = 1
    
    # Track which documents we're pulling from
    doc_chunk_counts = {}
    
    for m in matches["matches"]:
        content = m["metadata"]["content"]
        title = m["metadata"]["document_title"]
        doc_id = m["metadata"]["doc_id"]
        web_url = m["metadata"].get("web_url", "")
        
        # Track chunks per document
        doc_chunk_counts[doc_id] = doc_chunk_counts.get(doc_id, 0) + 1
        
        # Get surrounding context
        pre = m["metadata"]["prechunk_id"]
        post = m["metadata"]["postchunk_id"]
        ids_to_fetch = [id for id in [pre, post] if id != '']
        
        if ids_to_fetch:
            other_chunks = index.fetch(ids=ids_to_fetch)["vectors"]
        else:
            other_chunks = {}

        # Print chunk relevance
        print(f"Chunk relevance: {m['score']}")
            
        prechunk = other_chunks.get(pre, {}).get("metadata", {}).get("content", "")
        postchunk = other_chunks.get(post, {}).get("metadata", {}).get("content", "")
        
        # Add source information
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
        
        # Format chunk with context
        chunk = f"""[{source_id}] {title}

        {prechunk[-400:]}
        {content}
        {postchunk[:400]}"""
        chunks.append(chunk)
    
    # If we're heavily focused on one document, get additional context
    if doc_id or max(doc_chunk_counts.values(), default=0) > top_k * 0.6:
        most_referenced_doc = max(doc_chunk_counts.items(), key=lambda x: x[1])[0]
        additional_filter = query_filter.copy()
        additional_filter['doc_id'] = most_referenced_doc
        
        # Get additional chunks from the most referenced document
        additional_matches = index.query(
            vector=encoded_query,
            top_k=5,  # Get a few more chunks for context
            include_metadata=True,
            filter=additional_filter
        )
        
        # Add new chunks that weren't in the original results
        existing_chunk_ids = {m["id"] for m in matches["matches"]}
        for m in additional_matches["matches"]:
            if m["id"] not in existing_chunk_ids:
                # Process and add the new chunk (similar to above)
                content = m["metadata"]["content"]
                title = m["metadata"]["document_title"]
                web_url = m["metadata"].get("web_url", "")
                
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

                {content}"""
                chunks.append(chunk)
    
    return chunks, sources

# def gen_query_context(text, index, encoder, filters, search_comprehensiveness):
#     query_filter = {}
#     for f in filters:
#         query_filter.update(f)
#     filter = query_filter
#     encoded_query = encoder([text])[0]

#     top_k = int(5*search_comprehensiveness)
#     matches = index.query(
#         vector=encoded_query,
#         top_k=top_k,
#         include_metadata=True,
#         filter=filter
#     )
#     chunks = []
#     sources = []
#     source_ids = {}
#     source_counter = 1
#     for m in matches["matches"]:
#         content = m["metadata"]["content"]
#         title = m["metadata"]["document_title"]
#         web_url = m["metadata"].get("web_url", "")
#         pre = m["metadata"]["prechunk_id"]
#         post = m["metadata"]["postchunk_id"]
#         ids_to_fetch = [id for id in [pre, post] if id != '']
#         if ids_to_fetch:
#             other_chunks = index.fetch(ids=ids_to_fetch)["vectors"]
#         else:
#             other_chunks = {}

#         prechunk = other_chunks.get(pre, {}).get("metadata", {}).get("content", "")
#         postchunk = other_chunks.get(post, {}).get("metadata", {}).get("content", "")

#         if title not in source_ids:
#             source_ids[title] = source_counter
#             source_counter += 1
#             sources.append({
#                 "id": source_ids[title],
#                  "title": title,
#                  "url": web_url,
#                  "created_at": m["metadata"]["file_created_at"]
#             })
        
#         source_id = source_ids[title]

#         chunk = f"""[{source_id}] {title}

#         {prechunk[-400:]}
#         {content}
#         {postchunk[:400]}"""
#         chunks.append(chunk)
#     return chunks, sources

def query_openai(question, chunks, conversation, oai_client, sources, model="gpt-4o-mini", answer_detail=1.0):
    base_system_message = (
        f"You are an AI financial analyst assistant. When providing answers, ensure that you:\n"
        f"1. Include as many relevant perspectives and views as possible from the context, eliminating any directional bias.\n"
        f"2. Maintain extreme accuracy and attention to detail. Provide correct numbers and confirm the existence of events or data as per the context. Strive for completeness and do not exclude any relevant events or misquote forecasts.\n"
        f"3. Be thoughtful and strictly relevant. Exclude courteous statements or unnecessary information not directly related to the query and context.\n"
        f"4. If the relevant information is not present in the context, clearly state that you cannot find the information.\n"
        f"5. Consider second-order effects and interrelated events discussed in the context when formulating your answer.\n"
        f"6. When referencing information from the context, include citations using the source numbers provided.\n"
        f"Remember, your primary goal is to provide accurate, well evidenced, relevant, and unbiased financial analysis based solely on the given context and conversation history.\n"
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

    # Write user_content to a test file
    with open("test_user_content.txt", "w") as f:
        f.write(user_content)
        f.write(f"\n\nDocument filter: {st.session_state.doc_filter}")

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