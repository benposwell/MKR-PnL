import streamlit as st

st.markdown(
    f"""
    <div style="text-align: center;">
        <h1>Useful Resources</h1>
    </div>
    """,
    unsafe_allow_html=True
)

# st.title("Useful Resources")

st.markdown(
    """
    <style>
    .stLinkButton a {
        padding: 20px 50px;
        font-size: 20px;
        border-radius: 15px;
        font-weight: bold;
        width: 100%;
        height: 200px;
        display: flex;
        justify-content: center;
        align-items: center;
        text-decoration: none;
        color: white; /* Optional: Text color */
    }
    .stLinkButton {
        width: 100% !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

col_left, col_middle, col_right = st.columns(3)

with col_left:
    st.link_button("Notion", "https://www.notion.so/Projects-Tasks-deb9ab6168764784a8882e00fe7515ed", use_container_width=True)
    # if st.button("Notion", use_container_width=True):
    #     st.switch_page("pages/pnl_report.py")

with col_middle:
    st.link_button("Weekly Meeting Teams Link", "https://teams.microsoft.com/l/meetup-join/19%3ameeting_OWNkZTRkYmItOTcxNS00ZTAzLTlkZWYtMTAyNDc5NDM2MGYx%40thread.v2/0?context=%7b%22Tid%22%3a%22c5d97c29-33b6-48cd-ab0a-b9ac56c50a20%22%2c%22Oid%22%3a%222e768bb4-e616-494f-b478-fb150b2ec7de%22%7d", use_container_width=True)
        
with col_right:
    st.link_button("Website", "https://mkrcapital.com.au", use_container_width=True)

if st.sidebar.button("Logout"):
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()