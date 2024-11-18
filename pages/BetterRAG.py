import streamlit as st
import pytz
from datetime import datetime, timedelta
from utils.chat_funcs import check_password, create_new_chat, update_chat_name, generate_subject, delete_chat, load_user_chats, save_user_chats
from utils.funcs import get_mongo_access
from app.rag_service import init_connections, rag_pipeline
import time

### Helper Functions ###########################################################################################
def create_pinecone_date_filter(start_date, end_date):
    unix_start = int(start_date.timestamp())
    unix_end = int(end_date.timestamp())
    return {
        "file_created_at_unix": {
            "$gte": unix_start,
            "$lte": unix_end
        }
    }

def update_date_filter():
    if 'GPT_date_filter' not in st.session_state:
        st.session_state.GPT_date_filter = [min_time, max_time]
    if 'pinecone_date_filter' not in st.session_state:
        st.session_state.pinecone_date_filter = None
    
    date_range_filter = st.date_input("Select Search Date Range", st.session_state.GPT_date_filter,
                                      key="date_range_input", min_value=min_time, max_value=max_time,
                                      help="Filter to documents created within the selected date range")
    
    start_date, end_date = [datetime.combine(dt, datetime.min.time()).astimezone(aest).replace(hour=0, minute=0, second=0, microsecond=0) for dt in date_range_filter]
    
    st.session_state.GPT_date_filter = [start_date, end_date]
    st.session_state.pinecone_date_filter = create_pinecone_date_filter(start_date, end_date)
###################################################################################################################

# Force Login
if not check_password():
    st.stop()
### Global Variables ###########################################################################################
aest = pytz.timezone('Australia/Sydney')
min_time = datetime(2024, 1, 1, tzinfo=aest).date()
max_time = datetime(2030, 12, 31, tzinfo=aest).date()
now = datetime.now(aest)
curr_country_dict = {
    "Australia 🇦🇺": "AUD",
    "New Zealand 🇳🇿": "NZD",
    "United States 🇺🇸": "USD",
    "United Kingdom 🇬🇧": "GBP",
    "Eurozone 🇪🇺": "EUR",
    "Japan 🇯🇵": "JPY",
    "China 🇨🇳": "CNY",
    "Canada 🇨🇦": "CAD",
    "Switzerland 🇨🇭": "CHF",
    "Brazil 🇧🇷": "BRL",
    "Mexico 🇲🇽": "MXN",
    "India 🇮🇳": "INR"
}

client = get_mongo_access()
db = client[st.secrets["MONGO_DB_NAME"]]
custom_chats_collection = db["chats.betterrag_user_chats"]

if 'chats' not in st.session_state:
    st.session_state.chats = load_user_chats(st.session_state.logged_in_user, custom_chats_collection)
if 'current_chat_id' not in st.session_state:
    st.session_state.current_chat_id = None
if 'preloaded_prompt_processed' not in st.session_state:
    st.session_state.preloaded_prompt_processed = False
if 'autofill_prompt' not in st.session_state:
    st.session_state.autofill_prompt = None
if 'show_preloaded_buttons' not in st.session_state:
    st.session_state.show_preloaded_buttons = True
if 'search_comprehensiveness' not in st.session_state:
    st.session_state.search_comprehensiveness = 1.0
if 'answer_detail' not in st.session_state:
    st.session_state.answer_detail = 1.0
###################################################################################################################


preloaded_prompt = st.query_params.get("prompt", None)
preloaded_start_date = datetime.strptime(st.query_params.get("min_date", None), "%Y-%m-%d") if st.query_params.get("min_date") else None
preloaded_end_date = datetime.strptime(st.query_params.get("max_date", None), "%Y-%m-%d") if st.query_params.get("max_date") else None
preloaded_doc_id = st.query_params.get("doc_id", None)
search_comprehensiveness = st.query_params.get("search_comprehensiveness", 1.0)
answer_detail = st.query_params.get("answer_detail", 1.0)
if preloaded_prompt:
    st.session_state.autofill_prompt = preloaded_prompt

    if preloaded_doc_id:
        # TODO: Load the document and all of its chunks into the chat
        st.session_state.doc_filter = {"doc_id": preloaded_doc_id}

    if preloaded_start_date and preloaded_end_date:
        st.session_state.GPT_date_filter = [preloaded_start_date, preloaded_end_date]
        st.session_state.pinecone_date_filter = create_pinecone_date_filter(preloaded_start_date, preloaded_end_date)
        print("For dates:", preloaded_start_date, preloaded_end_date)
        print("CREATED Pinecone Date Filter:", st.session_state.pinecone_date_filter)
    if search_comprehensiveness is not None:
        st.session_state.search_comprehensiveness = float(search_comprehensiveness)
    if answer_detail is not None:
        st.session_state.answer_detail = float(answer_detail)
    
    st.session_state.show_preloaded_buttons = False
    create_new_chat()
    st.session_state.preloaded_prompt_processed = True
    st.query_params.clear()

st.markdown(
    f"""
    <div style="text-align: center;">
        <h1>BRAG</h1>
    </div>
    """,
    unsafe_allow_html=True
)
st.divider()

### Filtering ###############################################################################################
col1, col2, col3  = st.columns(3)
with col1:
    if st.button("This Week", use_container_width=True, 
                                 help=f"Filter to documents created between {datetime.strftime(now - timedelta(days=now.weekday()), '%Y-%m-%d')} and {datetime.strftime(now, '%Y-%m-%d')}"):
        start_of_week = now - timedelta(days=now.weekday())
        end_of_week = start_of_week + timedelta(days=6)
        st.session_state.GPT_date_filter = [start_of_week.date(), end_of_week.date()]
        st.session_state.pinecone_date_filter = create_pinecone_date_filter(start_of_week, end_of_week)
                
with col2:
    if st.button("Last Week", use_container_width=True, 
                                 help=f"Filter to documents created between {datetime.strftime(now - timedelta(days=now.weekday() + 7), '%Y-%m-%d')} and {datetime.strftime(now - timedelta(days=now.weekday()), '%Y-%m-%d')}"):
        start_of_last_week = now - timedelta(days=now.weekday() + 7)
        end_of_last_week = start_of_last_week + timedelta(days=6)
        st.session_state.GPT_date_filter = [start_of_last_week, end_of_last_week]
        st.session_state.pinecone_date_filter = create_pinecone_date_filter(start_of_last_week, end_of_last_week)
        
with col3:
    if st.button("All Time", use_container_width=True, 
                                help=f"Filter to documents created between {datetime.strftime(min_time, '%Y-%m-%d')} and {datetime.strftime(max_time, '%Y-%m-%d')}"):
        st.session_state.GPT_date_filter = [min_time, max_time]
        st.session_state.pinecone_date_filter = None

update_date_filter()

col1, col2 = st.columns(2)
with col1:
    search_comprehensiveness = st.slider("Search Comprehensiveness", 
                                         min_value = 0.5, 
                                         max_value = 4.0, 
                                         value = st.session_state.search_comprehensiveness, 
                                         step = 0.1, 
                                         help="Adjust the comprehensiveness of the search. Higher values will search more documents. Returns 5*search_comprehensiveness documents.")
    st.session_state.search_comprehensiveness = search_comprehensiveness
with col2:
    answer_detail = st.slider("Answer Detail", 
                              min_value = 0.5, 
                              max_value = 2.0, 
                              value = st.session_state.answer_detail, 
                              step = 0.1, 
                              help = "Adjust the level of detail in the answer. Higher values will provide more comprehensive answers.")
    st.session_state.answer_detail = answer_detail

encoder, index, oai_client = init_connections()
# if st.session_state.doc_filter is not None:
    # doc_id = st.session_state.doc_filter['doc_id']
    # document_title = get_document_title(doc_id, index)
    # st.write(f"Summarising Document: {document_title}")
###################################################################################################################




# Configure Sidebar ###########################################################################################
st.sidebar.title(f"Welcome, {st.session_state.logged_in_user}!")
if st.sidebar.button("🏠", key="home_button", help="Return to BRAG Home", use_container_width=True):
    st.session_state.current_chat_id = None
    st.rerun()
if st.sidebar.button("➕", key="new_chat", use_container_width=True):
    save_user_chats(st.session_state.logged_in_user, st.session_state.chats, custom_chats_collection)
    create_new_chat()
st.sidebar.divider()
st.sidebar.write("Existing Chats:")
for chat_id, chat_data in st.session_state.chats.items():
    if isinstance(chat_data, dict) and 'name' in chat_data:
        truncated_name = chat_data['name']
        col1, col2 = st.sidebar.columns([0.9, 0.1])
        with col1:
            if chat_id == st.session_state.current_chat_id:
                if st.button(truncated_name, key=f"select_{chat_id}", use_container_width=True, type="primary"):
                    st.session_state.current_chat_id = chat_id
            else:
                if st.button(truncated_name, key=f"select_{chat_id}", use_container_width=True):
                    st.session_state.current_chat_id = chat_id
        with col2:
            if st.button("🗑️", key=f"delete_{chat_id}", use_container_width=True):
                delete_chat(chat_id, st.session_state.logged_in_user, custom_chats_collection, rerun=True)
st.divider()
###################################################################################################################

# Chat UI #########################################################################################################
if st.session_state.current_chat_id:
    current_chat = st.session_state.chats[st.session_state.current_chat_id]
    col1, col2 = st.columns([10, 1])
    with col1:
        title_placeholder = st.empty()
        title_placeholder.subheader(f"{current_chat.get('name', 'Unnamed Chat')}")
    with col2:
        if st.button("➕", key="interior_new_chat", help="Create a new chat", use_container_width=True, type="secondary"):
            st.session_state.doc_filter = None
            save_user_chats(st.session_state.logged_in_user, st.session_state.chats, custom_chats_collection)
            create_new_chat()
            st.rerun()
        # st.button("➕", key="interior_new_chat", help="Create a new chat", 
        #           on_click=lambda: (save_user_chats(st.session_state.logged_in_user, st.session_state.chats, custom_chats_collection), create_new_chat(), 
                                    # st.rerun()), 
                # use_container_width=True, type="secondary")

    if len(current_chat['messages']) == 0 and st.session_state.show_preloaded_buttons:
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Summarise Daily Events 📅", use_container_width=True):
                date_string = datetime.strftime(now, '%A, %B %d, %Y')
                prompt = f"""
                    Summarise key upcoming events on {date_string} that I need to know about. Include a preview that details analyst forecasts
                """
                st.session_state.autofill_prompt = prompt
                st.session_state.show_preloaded_buttons = False
                st.rerun()
            if st.button("ANZ Preview 🇦🇺", use_container_width=True):
                this_week_string = datetime.strftime(now - timedelta(days=now.weekday()), '%Y-%m-%d')
                prompt = f"""
                    Summarise any upcoming economic calendar events that will occur in Australia and New Zealand or that are related to the AUD and NZD from {now.strftime('%Y-%m-%d')} onwards for the week starting {this_week_string}. Include a preview that details analyst forecasts and current positioning.
                """
                start_of_week = now - timedelta(days=now.weekday())
                end_of_week = start_of_week + timedelta(days=6)
                st.session_state.GPT_date_filter = [start_of_week.date(), end_of_week.date()]
                st.session_state.pinecone_date_filter = create_pinecone_date_filter(start_of_week, end_of_week)
                st.session_state.autofill_prompt = prompt
                st.session_state.show_preloaded_buttons = False
                st.rerun()
        with col2:
            if st.button("Latest News Preview 📰", use_container_width=True):
                prompt = f"""
                    Summarise all the research that we have received in the last 24 hours. The time now is {datetime.strftime(now, '%A, %B %d, %Y at %H:%M %p')}.
                """
                start_of_day = now - timedelta(days=1)
                end_of_day = now
                st.session_state.GPT_date_filter = [start_of_day.date(), end_of_day.date()]
                st.session_state.pinecone_date_filter = create_pinecone_date_filter(start_of_day, end_of_day)
                st.session_state.autofill_prompt = prompt
                st.session_state.show_preloaded_buttons = False
                st.rerun()
            if st.button("US Preview 🇺🇸", use_container_width=True):
                this_week_string = datetime.strftime(now - timedelta(days=now.weekday()), '%Y-%m-%d')
                prompt = f"""
                    Summarise any upcoming economic calendar events that will occur in the United States or that are related to the USD from {now.strftime('%Y-%m-%d')} onwards for the week starting {this_week_string}. Include a preview that details analyst forecasts and current positioning.
                """
                start_of_week = now - timedelta(days=now.weekday())
                end_of_week = start_of_week + timedelta(days=6)
                st.session_state.GPT_date_filter = [start_of_week.date(), end_of_week.date()]   
                st.session_state.pinecone_date_filter = create_pinecone_date_filter(start_of_week, end_of_week)
                st.session_state.autofill_prompt = prompt
                st.session_state.show_preloaded_buttons = False
                st.rerun()
        # Create a dropdown list of countries
        form = st.form(key="country_form")
        with form:
            countries = [
                "Australia 🇦🇺", "New Zealand 🇳🇿", "United States 🇺🇸", "United Kingdom 🇬🇧", "Eurozone 🇪🇺", 
                "Japan 🇯🇵", "China 🇨🇳", "Canada 🇨🇦", "Switzerland 🇨🇭", "Brazil 🇧🇷", "Mexico 🇲🇽", "India 🇮🇳"
            ]
            selected_country = st.selectbox("Select a country for weekly preview:", countries)
            submitted = st.form_submit_button("Generate", use_container_width=True, type="primary")
            this_week_string = datetime.strftime(now - timedelta(days=now.weekday()), '%Y-%m-%d')
            if submitted:
                prompt = f"""
                    Summarise any upcoming economic calendar events that will occur in {selected_country} or that are related to the {curr_country_dict[selected_country]} currency from {now.strftime('%Y-%m-%d')} onwards for the week starting {this_week_string}. Include a preview that details analyst forecasts and current positioning.
                """
                time_now = now
                start_of_week = time_now - timedelta(days=time_now.weekday())
                end_of_week = start_of_week + timedelta(days=6)
                st.session_state.GPT_date_filter = [start_of_week.date(), end_of_week.date()]
                st.session_state.pinecone_date_filter = create_pinecone_date_filter(start_of_week, end_of_week)
                st.session_state.autofill_prompt = prompt
                st.session_state.show_preloaded_buttons = False
                st.rerun()
    
    for message in current_chat['messages']:
        with st.chat_message(message['role'], avatar='images/icon.png' if message["role"] == "assistant" else "human"):
            st.markdown(message['content'])
    
    prompt = st.chat_input(f"How can I help you this {'evening' if datetime.now(aest).hour >=18 else 'afternoon' if datetime.now(aest).hour>=12 else 'morning'}?")

    if prompt or st.session_state.autofill_prompt:
        prompt = prompt or st.session_state.autofill_prompt
        st.session_state.autofill_prompt = None
        st.session_state.show_preloaded_buttons = False
        # st.session_state.preloaded_prompt_processed = True
        if len(current_chat['messages']) == 0:
            stream = generate_subject(prompt, oai_client)

            full_chat_name = ""
            for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    full_chat_name += chunk.choices[0].delta.content
                    title_placeholder.subheader(full_chat_name)

            update_chat_name(st.session_state.current_chat_id, full_chat_name)
        
        with st.chat_message("user"):
            st.markdown(prompt)
        
        conversation = "\n".join([f"{m['role']}: {m['content']}" for m in current_chat['messages'][-5:]])
        
        with st.chat_message("assistant", avatar="images/icon.png"):
            message_placeholder = st.empty()
            full_response = ""
            with st.spinner("Researching..."):
                if st.session_state.doc_filter:
                    completion, sources = rag_pipeline(prompt, index, conversation, encoder, oai_client, [st.session_state.pinecone_date_filter, st.session_state.doc_filter], st.session_state.search_comprehensiveness, st.session_state.answer_detail)
                    # st.session_state.doc_filter = None
                else:
                    completion, sources = rag_pipeline(prompt, index, conversation, encoder, oai_client, [st.session_state.pinecone_date_filter], st.session_state.search_comprehensiveness, st.session_state.answer_detail)
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
                    date_time_formatted = datetime.strptime(source['created_at'].split('+')[0], '%Y-%m-%dT%H:%M:%S')
                    sources_md += f"- [{source['id']}] [{source['title']}]({source['url']}) (Created: {date_time_formatted.strftime('%H:%M %A, %B %d, %Y')})\n"
                full_response += sources_md
            
            message_placeholder.markdown(full_response)

        
        current_chat['messages'].append({"role": "user", "content": prompt})
        current_chat['messages'].append({"role": "assistant", "content": full_response})
        save_user_chats(st.session_state.logged_in_user, st.session_state.chats, custom_chats_collection)
        st.rerun()
else:
    st.info("Please create a new chat or select an existing one from below:")
    if st.button("➕", key="interior_new_chat", help="Create a new chat", use_container_width=True, type="secondary"):
        st.session_state.doc_filter = None
        save_user_chats(st.session_state.logged_in_user, st.session_state.chats, custom_chats_collection)
        create_new_chat()
        st.rerun()
    # st.button("➕", key="interior_new_chat", help="Create a new chat", 
    #           on_click=lambda: (save_user_chats(st.session_state.logged_in_user, st.session_state.chats, custom_chats_collection), create_new_chat(), st.rerun()), 
            #   use_container_width=True, type="secondary")
    if len(st.session_state.chats) > 0:
        for chat_id, chat_data in st.session_state.chats.items():
            if isinstance(chat_data, dict) and 'name' in chat_data:
                col1, col2 = st.columns([9, 1])
                with col1:
                    if st.button(chat_data['name'], key=f"body_select_{chat_id}", use_container_width=True):
                        st.session_state.current_chat_id = chat_id
                with col2:
                    if st.button("🗑️", key=f"body_delete_{chat_id}", use_container_width=True, help="Delete the selected chat"):
                        delete_chat(chat_id, st.session_state.logged_in_user, custom_chats_collection, rerun=True)

    if st.button("⚠️ Delete All", key="interior_delete_all", use_container_width=True):
        print(st.session_state.chats)
        chat_ids_to_delete = list(st.session_state.chats.keys())
        for chat_id in chat_ids_to_delete:
            print("Deleted chat", chat_id)
            delete_chat(chat_id, st.session_state.logged_in_user, custom_chats_collection, rerun=False)

        st.session_state.chats = {}
        st.session_state.current_chat_id = None
        save_user_chats(st.session_state.logged_in_user, st.session_state.chats, custom_chats_collection)
        st.rerun()
###################################################################################################################

st.sidebar.divider()
if st.sidebar.button("Logout", use_container_width=True):
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()