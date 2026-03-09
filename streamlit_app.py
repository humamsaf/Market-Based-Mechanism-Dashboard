# app.py
# Entry point — jalankan dengan: streamlit run app.py

import streamlit as st

st.set_page_config(
    page_title="Global MBM Dashboard",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS
st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    section[data-testid="stSidebar"] {
        background-color: #1a1a2e;
        min-width: 220px !important;
        max-width: 220px !important;
    }
    section[data-testid="stSidebar"] * {
        color: white !important;
    }
    .block-container {
        padding-top: 1.5rem;
        padding-left: 2rem;
        padding-right: 2rem;
    }
    /* Active nav item */
    [data-testid="stSidebarNav"] a[aria-current="page"] {
        background-color: rgba(255,255,255,0.12) !important;
        border-radius: 8px;
        font-weight: 700;
    }
    [data-testid="stSidebarNav"] a {
        color: #aab4c8 !important;
        border-radius: 8px;
        padding: 6px 12px;
    }
    [data-testid="stSidebarNav"] a:hover {
        background-color: rgba(255,255,255,0.08) !important;
        color: white !important;
    }
    [data-testid="stSidebarNav"] {
        padding-top: 0 !important;
    }
</style>
""", unsafe_allow_html=True)

# Sidebar logo
st.sidebar.markdown("""
<div style="padding: 20px 12px 16px 12px;">
    <div style="font-size:22px; font-weight:800; color:white; letter-spacing:1px;">🌍 MBM</div>
    <div style="font-size:11px; color:#aab4c8; margin-top:2px;">Market-Based Mechanisms</div>
</div>
<hr style="border-color: rgba(255,255,255,0.15); margin: 0 0 8px 0;">
""", unsafe_allow_html=True)

pages = [
    st.Page("pages/global_overview.py", title="Global Overview",  icon="🗺️", default=True),
    st.Page("pages/mbm_national.py",    title="MBM National",     icon="🏭"),
    st.Page("pages/corsia.py",          title="CORSIA",           icon="✈️"),
    st.Page("pages/cdm.py",             title="CDM",              icon="🌱"),
    st.Page("pages/imo.py",             title="IMO",              icon="🚢"),
]

pg = st.navigation(pages, position="sidebar", expanded=True)
pg.run()
