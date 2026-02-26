# pages/1_MBM_National.py
import streamlit as st
import pandas as pd
import plotly.express as px
import pycountry

# optional, tapi kita include di requirements
from streamlit_plotly_events import plotly_events

from utils.paths import data_path

st.set_page_config(page_title="MBM National", page_icon="🏛️", layout="wide")

FILE_PATH = data_path("Global Market Based Mechanism.xlsx")

MECH_COLS = {
    "1. Carbon Tax": "Carbon Tax",
    "2. ETS": "ETS",
    "3. Tax Incentives": "Tax Incentives",
    "4. Fuel Mandates": "Fuel Mandates",
    "5. VCM project": "VCM project",
    "6. Feebates": "Feebates",
    "7. CBAM": "CBAM",
    "8. AMC": "AMC",
}
MECH_LIST = list(MECH_COLS.values())

MANUAL_ISO3 = {
    "Côte d’Ivoire": "CIV",
    "Côte d'Ivoire": "CIV",
    "São Tomé and Príncipe": "STP",
    "Democratic Republic of the Congo": "COD",
    "Republic of the Congo": "COG",
    "United States": "USA",
    "Russia": "RUS",
    "Iran": "IRN",
    "Syria": "SYR",
    "Vatican City": "VAT",
    "North Korea": "PRK",
    "South Korea": "KOR",
    "Laos": "LAO",
    "Timor-Leste": "TLS",
    "Brunei Darussalam": "BRN",
    "Bolivia": "BOL",
    "Venezuela": "VEN",
    "Tanzania": "TZA",
    "Micronesia": "FSM",
    "Palestine": "PSE",
    "Türkiye": "TUR",
}

def country_to_iso3(name: str):
    if pd.isna(name):
        return None
    n = str(name).strip()
    if n in MANUAL_ISO3:
        return MANUAL_ISO3[n]
    try:
        return pycountry.countries.lookup(n).alpha_3
    except Exception:
        return None

@st.cache_data(show_spinner=False)
def load_data():
    df = pd.read_excel(FILE_PATH)
    # normalize columns
    df.columns = [str(c).strip() for c in df.columns]
    # ensure key column exists
    if "Jurisdiction" not in df.columns:
        # try common fallbacks
        for cand in ["Country", "State", "Jurisdiction "]:
            if cand in df.columns:
                df = df.rename(columns={cand: "Jurisdiction"})
                break
    df["iso3"] = df["Jurisdiction"].apply(country_to_iso3)
    return df

def mech_exists(row, mech_name: str):
    # attempt to detect if mechanism exists in row
    if mech_name not in row.index:
        return False
    v = row.get(mech_name)
    if pd.isna(v):
        return False
    s = str(v).strip().lower()
    if s in ("", "no", "none", "0", "false", "nan", "-"):
        return False
    return True

def show_mech_cards(row):
    st.subheader("Mechanisms")
    cols = st.columns(4)
    for i, mech in enumerate(MECH_LIST):
        col = cols[i % 4]
        present = mech_exists(row, mech)
        with col:
            st.metric(mech, "YES" if present else "NO")

def show_detail(row, mech_selected: str):
    st.subheader(f"Detail: {mech_selected}")
    if mech_selected not in row.index:
        st.warning("Kolom mechanism ini tidak ditemukan di dataset.")
        return
    st.write(row.get(mech_selected))

# =========================
# UI
# =========================
st.title("🏛️ MBM National Dashboard")
st.caption("Click map → pilih negara → lihat ringkasan + 8 mechanism cards")

try:
    df = load_data()
except FileNotFoundError:
    st.error(f"File tidak ditemukan: {FILE_PATH}. Pastikan Excel ada di folder `data/`.")
    st.stop()

if df.empty:
    st.warning("Dataset kosong.")
    st.stop()

# Map dataset for Plotly
map_df = df.dropna(subset=["iso3"]).copy()
map_df["has_any_mech"] = 0
for mech in MECH_LIST:
    if mech in map_df.columns:
        map_df["has_any_mech"] = map_df["has_any_mech"] | map_df[mech].notna().astype(int)

left, right = st.columns([2.2, 1])

with left:
    st.subheader("World map (click a country)")
    fig = px.choropleth(
        map_df,
        locations="iso3",
        color="has_any_mech",
        hover_name="Jurisdiction",
        color_continuous_scale="Blues",
    )
    fig.update_layout(margin=dict(l=0, r=0, t=0, b=0))
    selected = plotly_events(fig, click_event=True, hover_event=False, select_event=False, key="mbm_map_evt")

# Resolve selection
selected_iso3 = None
if selected and isinstance(selected, list) and len(selected) > 0:
    pt = selected[0]
    selected_iso3 = pt.get("location")

with right:
    st.subheader("Country panel")
    if selected_iso3:
        row = df[df["iso3"] == selected_iso3].head(1)
        if row.empty:
            st.warning("Negara tidak ditemukan di tabel.")
        else:
            row = row.iloc[0]
            st.write(f"**Jurisdiction:** {row.get('Jurisdiction')}")
            show_mech_cards(row)

            st.divider()
            mech_selected = st.selectbox("Drilldown mechanism", MECH_LIST, key="mbm_mech_select")
            show_detail(row, mech_selected)
    else:
        st.info("Klik negara di peta untuk melihat detail di panel ini.")

st.divider()
with st.expander("Raw data preview"):
    st.dataframe(df, use_container_width=True)
