import streamlit as st
import spacy
import hmac
from datetime import datetime

def generate_chat_url(prompt, doc_id = None, min_date=None, max_date=None, search_comprehensiveness=None, answer_detail=None):
    chat_url = f"http://localhost:8501/BetterRAG?prompt={prompt}"
    # chat_url = f"https://mkrcapital.streamlit.app/BetterRAG?prompt={prompt}"
    if doc_id:
        chat_url += f"&doc_id={doc_id}"
    if min_date:
        chat_url += f"&min_date={min_date}"
    if max_date:
        chat_url += f"&max_date={max_date}"
    if search_comprehensiveness:
        chat_url += f"&search_comprehensiveness={search_comprehensiveness}"
    if answer_detail:
        chat_url += f"&answer_detail={answer_detail}"
    return chat_url


def create_new_chat():
    chat_id = f"chat_{len(st.session_state.chats) + 1}"
    st.session_state.chats[chat_id] = {
        'name': f"New Chat {len(st.session_state.chats) + 1}",
        'messages': [],
        'created_at': datetime.now().timestamp()  # Add timestamp as created_at field
    }
    st.session_state.show_preloaded_buttons = True
    st.session_state.current_chat_id = chat_id

def delete_chat(chat_id, username, chats_collection, rerun=True):
    if chat_id in st.session_state.chats:
        del st.session_state.chats[chat_id]
        if st.session_state.current_chat_id == chat_id:
            st.session_state.current_chat_id = None

        chats_collection.update_one(
            {"username": username},
            {"$unset": {f"chats.{chat_id}": ""}}
        )
    if rerun:
        st.rerun()

def update_chat_name(chat_id, new_name):
    if chat_id in st.session_state.chats:
        st.session_state.chats[chat_id]['name'] = new_name

def generate_subject(question, openai_client):
    prompt = "Please generate a concise subject for the following question capturing core information. Only output the subject and nothing else."

    user_content = f"Question: {question}"

    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": user_content}
    ]
    
    stream = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        stream=True
    )
    return stream


def display_message(role, content):
    if role == "user":
        st.markdown(f'<div style="background-color: #e6f3ff; padding: 10px; border-radius: 5px; margin-bottom: 10px;"><strong>User:</strong> {content}</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div style="background-color: #f0f0f0; padding: 10px; border-radius: 5px; margin-bottom: 10px;"><strong>Assistant:</strong> {content}</div>', unsafe_allow_html=True)

def check_password():
    st.divider()
    """Returns `True` if the user selected their username."""
    def login_form():
        """Form with a dropdown to select the username"""
        with st.form("Select Username"):
            usernames = list(st.secrets["passwords"].keys())
            st.selectbox("Username", usernames, key="username")
            st.form_submit_button("Continue", on_click=username_selected)

    def username_selected():
        """Records the selected username."""
        st.session_state["password_correct"] = True
        st.session_state["logged_in_user"] = st.session_state["username"]
        del st.session_state["username"]

    # Return True if the username is selected.
    if st.session_state.get("password_correct", False):
        return True

    # Show dropdown for username selection.
    login_form()
    return False

def initialize_user(username, chats_collection):
    new_user = {
        "username":username,
        "chats":{}
    }
    chats_collection.insert_one(new_user)
    return new_user["chats"]

def load_user_chats(username, chats_collection):
    user_chats = chats_collection.find_one({"username": username})
    if user_chats:
        return user_chats["chats"]
    else:
        st.info(f"Welcome, {username}! Initializing your account.")
        return initialize_user(username, chats_collection)
    return {}

def save_user_chats(username, chats, chats_collection):
    chats_collection.update_one(
        {"username": username},
        {"$set": {"chats": chats}},
        upsert=True
    )

# LEGACY CODE
def refresh_file_list(assistant):
    with st.spinner("Refreshing file list..."):
        st.session_state.file_list = assistant.list_files()
    st.success("File list refreshed successfully!")

def get_file_list(assistant):
    if 'file_list' not in st.session_state:
        refresh_file_list(assistant)
    return st.session_state.file_list

def upload_files(assistant):
    uploaded_files = st.file_uploader("Upload PDF or TXT files", type=["pdf", "txt"], accept_multiple_files=True)
    if uploaded_files:
        existing_files = [file.name for file in get_file_list(assistant)]
        for file in uploaded_files:
            if file.name not in existing_files:
                with st.spinner(f"Uploading {file.name}..."):
                    # Save the file temporarily
                    with open(file.name, "wb") as f:
                        f.write(file.getbuffer())
                    # Upload to Pinecone
                    response = assistant.upload_file(file_path=file.name)
                    st.success(f"{file.name} uploaded successfully!")
            else:
                st.info(f"{file.name} is already uploaded.")
        refresh_file_list(assistant)  # Refresh the file list after uploads
        return True
    return False

def list_and_delete_files(assistant):
    files = get_file_list(assistant)
    if files:
        file_names = [file.name for file in files]
        selected_file = st.selectbox("Select a file to delete", file_names)
        
        if st.button("Delete Selected File"):
            file_id = next(file.id for file in files if file.name == selected_file)
            assistant.delete_file(file_id=file_id)
            st.success(f"{selected_file} deleted successfully!")
            refresh_file_list(assistant)  # Refresh the file list after deletion
            st.rerun()
    else:
        st.info("No files uploaded yet.")

    if st.button("Refresh Database"):
        refresh_file_list(assistant)


# def check_password():
#     st.divider()
#     """Returns `True` if the user had a correct password."""
#     def login_form():
#         """Form with widgets to collect user information"""
#         with st.form("Credentials"):
#             st.text_input("Username", key="username")
#             st.text_input("Password", type="password", key="password")
#             st.form_submit_button("Log in", on_click=password_entered)

#     def password_entered():
#         """Checks whether a password entered by the user is correct."""
#         if (
#             st.session_state["username"] in st.secrets["passwords"]
#             and hmac.compare_digest(
#                 st.session_state["password"],
#                 st.secrets.passwords[st.session_state["username"]],
#             )
#         ):
#             st.session_state["password_correct"] = True
#             st.session_state["logged_in_user"] = st.session_state["username"]
#             del st.session_state["password"]  # Don't store the password.
#             del st.session_state["username"]
#         else:
#             st.session_state["password_correct"] = False

#     # Return True if the username + password is validated.
#     if st.session_state.get("password_correct", False):
#         return True

#     # Show inputs for username + password.
#     login_form()
#     if "password_correct" in st.session_state:
#         st.error("😕 User not known or password incorrect")
#     return False