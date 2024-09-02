import streamlit as st
import pandas as pd
import numpy as np
from pinecone import Pinecone
from pinecone_plugins.assistant.models.chat import Message
from utils.chat_funcs import upload_files, list_and_delete_files, get_file_list, create_new_chat, update_chat_name, generate_subject, delete_chat, load_user_chats, save_user_chats, check_password
from pymongo import MongoClient
from utils.funcs import get_mongo_access

if not check_password():
    st.stop()

# Initialize Pinecone
pc = Pinecone(api_key=st.secrets["PINECONE_API_KEY"])
assistant = pc.assistant.Assistant(
    assistant_name=st.secrets["PINECONE_ASSISTANT_NAME"]
)

# client = MongoClient(st.secrets["MONGO_URI"])
client = get_mongo_access()
db = client[st.secrets["MONGO_DB_NAME"]]
chats_collection = db["chats.user_chats"]

# st.image('images/Original Logo.png')

# Create tabs
tab1, tab2 = st.tabs(["Chat", "Manage Files"])

if 'chats' not in st.session_state:
    st.session_state.chats = load_user_chats(st.session_state.logged_in_user, chats_collection)

if 'current_chat_id' not in st.session_state:
    st.session_state.current_chat_id = None

# st.sidebar.title("User Management")
st.sidebar.title(f"Welcome, {st.session_state.logged_in_user}!")

if st.sidebar.button("New Chat", key="new_chat"):
    create_new_chat()
    save_user_chats(st.session_state.logged_in_user, st.session_state.chats, chats_collection)

st.sidebar.write("Existing Chats:")
cols = st.sidebar.columns(2)  # Create 2 columns
for i, (chat_id, chat_data) in enumerate(st.session_state.chats.items()):
    col = cols[i % 2]  # Alternate between columns
    with col:
        if isinstance(chat_data, dict) and 'name' in chat_data:
            truncated_name = " ".join(chat_data['name'].split()[:3]) + "..."
            # Create a container for each chat button
            chat_container = st.container()
            # Add chat selection button
            if chat_container.button(truncated_name, key=f"select_{chat_id}", use_container_width=True):
                st.session_state.current_chat_id = chat_id
            # Add delete button
            if chat_container.button("🗑️", key=f"delete_{chat_id}", use_container_width=True):
                delete_chat(chat_id)
                save_user_chats(st.session_state.logged_in_user, st.session_state.chats, chats_collection)

with tab1:
    # st.markdown("---")
    files = get_file_list(assistant)

    if files:
        st.success(f"{len(files)} file(s) already uploaded and ready to use.")
    else:
        st.info("No files uploaded yet. You can upload files in the 'Manage Files' tab.")

    if st.session_state.current_chat_id:
        current_chat = st.session_state.chats[st.session_state.current_chat_id]
        st.subheader(f"Current Chat: {current_chat.get('name', 'Unnamed Chat')}")

        # Display chat messages
        if 'messages' in current_chat:
            for message in current_chat['messages']:
                with st.chat_message(message["role"], avatar='images/icon.png' if message["role"] == "assistant" else "human"):
                    st.markdown(message["content"])

        # Chat input
        if prompt := st.chat_input("What would you like to know?"):
            if 'messages' not in current_chat:
                current_chat['messages'] = []
            current_chat['messages'].append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            if len(current_chat['messages']) == 1:
                new_chat_name = generate_subject(prompt)
                update_chat_name(st.session_state.current_chat_id, new_chat_name)
 
            with st.chat_message("assistant", avatar='images/icon.png'):
                message_placeholder = st.empty()
                full_response = ""
                chat_context = [Message(content=msg['content'], role=msg['role']) for msg in current_chat['messages']]
                for response in assistant.chat_completions(messages=chat_context, stream=True):
                    if response.choices[0].delta.content is not None:
                        full_response += response.choices[0].delta.content
                        message_placeholder.markdown(full_response + "▌")
                message_placeholder.markdown(full_response)
            current_chat['messages'].append({"role": "assistant", "content": full_response})
            save_user_chats(st.session_state.logged_in_user, st.session_state.chats, chats_collection)
            st.rerun()
    else:
        st.info("Please create a new chat or select an existing one from below:")
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
                        save_user_chats(st.session_state.logged_in_user, st.session_state.chats, chats_collection)
        

with tab2:
    st.title("Manage Uploaded Files")
    st.write("Upload new files or manage existing ones:")
    upload_files(assistant)
    st.write("---")
    list_and_delete_files(assistant)

if st.sidebar.button("Logout"):
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()
