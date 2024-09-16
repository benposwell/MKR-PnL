import streamlit as st
import pytz
from semantic_router.encoders import OpenAIEncoder
from pinecone import Pinecone, ServerlessSpec
from openai import OpenAI
from datetime import datetime, timedelta
from utils.chat_funcs import check_password, create_new_chat, update_chat_name, generate_subject, delete_chat, load_user_chats, save_user_chats
from pymongo import MongoClient
from utils.funcs import get_mongo_access
import time
import json
import unicodedata
import re



if not check_password():
    st.stop()

aest = pytz.timezone('Australia/Sydney')
    
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
                 "url": web_url
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
        f"6. After your main response, if applicable, provide a concise list of additional relevant topics or ideas from the context for further exploration.\n"
        f"7. When referencing information from the context, include citations using the source numbers provided.\n"
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

# Get Mongo
client = get_mongo_access()
db = client[st.secrets["MONGO_DB_NAME"]]
custom_chats_collection = db["chats.betterrag_user_chats"]

st.title("BetterRAG - Developer Edition")
st.write("Warning, not for production use")

if 'chats' not in st.session_state:
    st.session_state.chats = load_user_chats(st.session_state.logged_in_user, custom_chats_collection)
if 'current_chat_id' not in st.session_state:
    st.session_state.current_chat_id = None

# Date Filtering
min_time = datetime(2024, 1, 1, tzinfo=aest).date()
max_time = datetime(2030, 12, 31, tzinfo=aest).date()
now = datetime.now(aest)

# Initiaise Session State Variables
if 'GPT_date_filter' not in st.session_state:
    st.session_state.GPT_date_filter = [min_time, max_time]

this_week_button = st.button("This Week", use_container_width=True, help=f"Filter to documents created between {datetime.strftime(now - timedelta(days=now.weekday()), '%Y-%m-%d')} and {datetime.strftime(now, '%Y-%m-%d')}")
last_week_button = st.button("Last Week", use_container_width=True, help=f"Filter to documents created between {datetime.strftime(now - timedelta(days=now.weekday() + 7), '%Y-%m-%d')} and {datetime.strftime(now - timedelta(days=now.weekday()), '%Y-%m-%d')}")
all_time_button = st.button("All Time", use_container_width=True, help=f"Filter to documents created between {datetime.strftime(min_time, '%Y-%m-%d')} and {datetime.strftime(max_time, '%Y-%m-%d')}")

if this_week_button:
    start_of_week = now - timedelta(days=now.weekday())
    end_of_week = start_of_week + timedelta(days=6)
    st.session_state.GPT_date_filter = [start_of_week.date(), end_of_week.date()]
elif last_week_button:
    start_of_last_week = now - timedelta(days=now.weekday() + 7)
    end_of_last_week = start_of_last_week + timedelta(days=6)
    st.session_state.GPT_date_filter = [start_of_last_week.date(), end_of_last_week.date()]
elif all_time_button:
    st.session_state.GPT_date_filter = [min_time, max_time]

date_range_filter = st.date_input("Select Date Range", st.session_state.get('GPT_date_filter', [min_time, max_time]), key="GPT_date_filter", min_value=min_time, max_value=max_time, help="Filter to documents created within the selected date range")
date_range_filter = [datetime.combine(dt, datetime.min.time()).astimezone(aest).replace(hour=0, minute=0, second=0, microsecond=0) for dt in date_range_filter]
unix_start, unix_end = [int(dt.timestamp()) for dt in date_range_filter]

pinecone_date_filter = {
    "file_created_at_unix": {
        "$gte": unix_start,
        "$lte": unix_end
    }
}

search_comprehensiveness = st.slider("Search Comprehensiveness", min_value = 0.5, max_value = 2.0, value = 1.0, step = 0.1, help="Adjust the comprehensiveness of the search. Higher values will search more documents but may increase costs.")
answer_detail = st.slider("Answer Detail", min_value = 0.5, max_value = 2.0, value = 1.0, step = 0.1, help = "Adjust the level of detail in the answer. Higher values will provide more comprehensive answers but may increase costs.")

encoder, index, oai_client = init_connections()
st.sidebar.title(f"Welcome, {st.session_state.logged_in_user}!")

if st.sidebar.button("New Chat", key="new_chat"):
    save_user_chats(st.session_state.logged_in_user, st.session_state.chats, custom_chats_collection)
    create_new_chat()

st.sidebar.write("Existing Chats:")
cols = st.sidebar.columns(2)
for i, (chat_id, chat_data) in enumerate(st.session_state.chats.items()):
    col = cols[i % 2]
    with col:
        if isinstance(chat_data, dict) and 'name' in chat_data:
            truncated_name = " ".join(chat_data['name'].split()[:3]) + "..."
            chat_container = st.container()
            if chat_container.button(truncated_name, key=f"select_{chat_id}", use_container_width=True):
                st.session_state.current_chat_id = chat_id


            if chat_container.button("🗑️", key=f"delete_{chat_id}", use_container_width=True):
                delete_chat(chat_id)
                save_user_chats(st.session_state.logged_in_user, st.session_state.chats, custom_chats_collection)

if st.session_state.current_chat_id:
    current_chat = st.session_state.chats[st.session_state.current_chat_id]
    st.subheader(f"Current Chat: {current_chat.get('name', 'Unnamed Chat')}")
    for message in current_chat['messages']:
        with st.chat_message(message['role'], avatar='images/icon.png' if message["role"] == "assistant" else "human"):
            st.markdown(message['content'])
    
    if prompt := st.chat_input("What would you like to know?"):
        with st.chat_message("user"):
            st.markdown(prompt)

        if len(current_chat['messages']) == 0:
            new_chat_name = generate_subject(prompt)
            update_chat_name(st.session_state.current_chat_id, new_chat_name)
        
        conversation = "\n".join([f"{m['role']}: {m['content']}" for m in current_chat['messages'][-5:]])

        with st.chat_message("assistant", avatar="images/icon.png"):
            message_placeholder = st.empty()
            full_response = ""
            completion, sources = rag_pipeline(prompt, index, conversation, encoder, oai_client, [pinecone_date_filter], search_comprehensiveness, answer_detail)
            for response in completion:
                if isinstance(response, str):
                    full_response += response
                else:
                    if response.choices[0].delta.content is not None:
                        full_response += response.choices[0].delta.content
                        message_placeholder.markdown(full_response + "▌")
            
            if sources:
                sources_md = "\n\n### Sources:\n"
                for source in sources:
                    sources_md += f"- [{source['id']}] [{source['title']}]({source['url']})\n"
                full_response += sources_md
            
            message_placeholder.markdown(full_response)

        
        current_chat['messages'].append({"role": "user", "content": prompt})
        current_chat['messages'].append({"role": "assistant", "content": full_response})
        save_user_chats(st.session_state.logged_in_user, st.session_state.chats, custom_chats_collection)
        st.rerun()
else:
    st.info("Please create a new chat or select an existing one from below:")
    if len(st.session_state.chats) > 0:
        body_cols = st.columns(2)  # Create 2 columns
        for i, (chat_id, chat_data) in enumerate(st.session_state.chats.items()):
            col = body_cols[i % 2]  # Alternate between columns
            with col:
                if isinstance(chat_data, dict) and 'name' in chat_data:
                    truncated_name = " ".join(chat_data['name'].split()[:3]) + "..."
                    # Create a container for each chat button
                    chat_container = st.container()
                    # Add chat selection button
                    if chat_container.button(truncated_name, key=f"body_select_{chat_id}", use_container_width=True):
                        st.session_state.current_chat_id = chat_id
                    # Add delete button
                    if chat_container.button("🗑️", key=f"body_delete_{chat_id}", use_container_width=True):
                        delete_chat(chat_id)
                        save_user_chats(st.session_state.logged_in_user, st.session_state.chats, custom_chats_collection)
    else:
        # Place a new chat button 
        if st.button("Create New Chat", key="create_new_chat", use_container_width=True):
            save_user_chats(st.session_state.logged_in_user, st.session_state.chats, custom_chats_collection)
            create_new_chat()


if st.sidebar.button("Logout"):
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()