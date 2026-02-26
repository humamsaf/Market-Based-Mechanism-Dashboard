import streamlit as st
from pathlib import Path
from utils.paths import data_path, repo_root

st.set_page_config(
    page_title="Global Dashboard (MBM • CORSIA • CDM)",
    page_icon="🌍",
    layout="wide",
)

st.title("🌍 Global Dashboard")
st.caption("Multi-page Streamlit app: MBM National • CORSIA • CDM")

st.subheader("Status data files (di folder `data/`)")

required_files = [
    "Global Market Based Mechanism.xlsx",
    "2019_2020_CO2_StatePairs_table_Nov2021.xlsx",
    "2024_CO2_StatePairs_table.xlsx",
    "CORSIA_AO_to_State_Attributions_10ed_web-2_extracted.xlsx",
    "CDM.xlsx",
]

cols = st.columns(2)
with cols[0]:
    ok = 0
    for f in required_files:
        p = Path(data_path(f))
        exists = p.exists()
        ok += int(exists)
        st.write(("✅ " if exists else "❌ ") + f)
with cols[1]:
    st.metric("Files present", f"{ok}/{len(required_files)}")
    st.write("Repo root:")
    st.code(str(repo_root()))

st.divider()
st.info("Buka menu di sidebar untuk masuk ke masing-masing dashboard: MBM National / CORSIA / CDM.")
