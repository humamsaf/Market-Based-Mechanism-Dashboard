# pages/2_CORSIA.py
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

from utils.paths import data_path

st.set_page_config(page_title="CORSIA State-Pair Dashboard", page_icon="✈️", layout="wide")

BASELINE_XLSX = data_path("2019_2020_CO2_StatePairs_table_Nov2021.xlsx")
CURRENT_XLSX  = data_path("2024_CO2_StatePairs_table.xlsx")

AIRLINES_XLSX = data_path("CORSIA_AO_to_State_Attributions_10ed_web-2_extracted.xlsx")

COUNTRY_ALIAS = {
    # tambahkan kalau ada mismatch nama negara
}

def clean_num(x):
    if pd.isna(x):
        return np.nan
    s = str(x).strip().replace(",", "").replace("*", "")
    if s in {"", "-", "—"}:
        return np.nan
    try:
        return float(s)
    except Exception:
        return np.nan

def split_pair(val, delim):
    if pd.isna(val):
        return (None, None)
    p = str(val).split(delim)
    if len(p) == 2:
        return (p[0].strip(), p[1].strip())
    return (p[0].strip(), None)

def fmt_int(x):
    return "—" if pd.isna(x) else f"{int(round(x)):,}"

def fmt_pct(x):
    return "—" if pd.isna(x) else f"{x:.2f}%"

@st.cache_data(show_spinner=False)
def load_baseline():
    raw = pd.read_excel(BASELINE_XLSX, header=None)
    # your original logic likely expects a specific layout; keep as-is:
    # try to find header row heuristically
    header_row = None
    for i in range(min(50, len(raw))):
        row = raw.iloc[i].astype(str).str.lower().tolist()
        if any("state pair" in c for c in row) or any("from" in c for c in row) and any("to" in c for c in row):
            header_row = i
            break
    if header_row is None:
        header_row = 0
    df = pd.read_excel(BASELINE_XLSX, header=header_row)
    df.columns = [str(c).strip() for c in df.columns]
    return df

@st.cache_data(show_spinner=False)
def load_current():
    raw = pd.read_excel(CURRENT_XLSX, header=None)
    header_row = None
    for i in range(min(50, len(raw))):
        row = raw.iloc[i].astype(str).str.lower().tolist()
        if any("state pair" in c for c in row) or (any("from" in c for c in row) and any("to" in c for c in row)):
            header_row = i
            break
    if header_row is None:
        header_row = 0
    df = pd.read_excel(CURRENT_XLSX, header=header_row)
    df.columns = [str(c).strip() for c in df.columns]
    return df

@st.cache_data(show_spinner=False)
def load_airlines():
    df = pd.read_excel(AIRLINES_XLSX)
    df.columns = [str(c).strip() for c in df.columns]
    return df

st.title("✈️ CORSIA State-Pair Dashboard")
st.caption("Baseline vs Current + Airline attribution (info-only)")

# Load data
try:
    df_base = load_baseline()
    df_curr = load_current()
except FileNotFoundError as e:
    st.error(f"File tidak ditemukan: {e}. Pastikan semua Excel ada di folder `data/`.")
    st.stop()

# Minimal normalization: try to locate key columns
def normalize_pairs(df: pd.DataFrame):
    d = df.copy()
    # Find a pair column
    pair_col = None
    for c in d.columns:
        lc = c.lower()
        if "state pair" in lc or "pair" in lc:
            pair_col = c
            break

    # If pair col found, split it. Else try From/To columns.
    if pair_col:
        delim = " - " if d[pair_col].astype(str).str.contains(" - ").any() else "-"
        a, b = zip(*d[pair_col].apply(lambda x: split_pair(x, delim)))
        d["From"] = list(a)
        d["To"] = list(b)
    else:
        # guess
        from_col = next((c for c in d.columns if c.lower() in ["from", "origin", "departure"]), None)
        to_col   = next((c for c in d.columns if c.lower() in ["to", "destination", "arrival"]), None)
        if from_col: d["From"] = d[from_col]
        if to_col:   d["To"] = d[to_col]

    # Find CO2 / emissions col
    co2_col = next((c for c in d.columns if "co2" in c.lower()), None)
    if co2_col:
        d["CO2"] = d[co2_col].apply(clean_num)
    else:
        d["CO2"] = np.nan

    # Alias mapping
    d["From"] = d["From"].replace(COUNTRY_ALIAS)
    d["To"]   = d["To"].replace(COUNTRY_ALIAS)

    return d

base = normalize_pairs(df_base)
curr = normalize_pairs(df_curr)

# Sidebar filters
with st.sidebar:
    st.header("Filters")
    all_countries = pd.Series(pd.concat([base["From"], base["To"], curr["From"], curr["To"]]).dropna().unique()).sort_values()
    c1 = st.selectbox("Country A", options=all_countries, index=0 if len(all_countries) else None)
    c2 = st.selectbox("Country B", options=all_countries, index=1 if len(all_countries) > 1 else 0)

def filter_pair(df: pd.DataFrame, a: str, b: str):
    if not a or not b:
        return df.iloc[0:0]
    m1 = (df["From"] == a) & (df["To"] == b)
    m2 = (df["From"] == b) & (df["To"] == a)
    return df[m1 | m2]

base_pair = filter_pair(base, c1, c2)
curr_pair = filter_pair(curr, c1, c2)

# KPIs
k1, k2, k3 = st.columns(3)
with k1:
    st.metric("Baseline CO2 (tonnes)", fmt_int(base_pair["CO2"].sum()) if not base_pair.empty else "—")
with k2:
    st.metric("Current CO2 (tonnes)", fmt_int(curr_pair["CO2"].sum()) if not curr_pair.empty else "—")
with k3:
    if not base_pair.empty and not curr_pair.empty and base_pair["CO2"].sum() > 0:
        chg = (curr_pair["CO2"].sum() / base_pair["CO2"].sum() - 1) * 100
        st.metric("Change", fmt_pct(chg))
    else:
        st.metric("Change", "—")

st.divider()

# Charts
c_left, c_right = st.columns([1.2, 1])

with c_left:
    st.subheader("Baseline vs Current (selected pair)")
    chart_df = pd.DataFrame({
        "Dataset": ["Baseline", "Current"],
        "CO2": [
            float(base_pair["CO2"].sum()) if not base_pair.empty else 0.0,
            float(curr_pair["CO2"].sum()) if not curr_pair.empty else 0.0,
        ]
    })
    fig = px.bar(chart_df, x="Dataset", y="CO2", text="CO2")
    st.plotly_chart(fig, use_container_width=True)

with c_right:
    st.subheader("Filtered rows (preview)")
    st.write("Baseline rows:", len(base_pair))
    st.write("Current rows:", len(curr_pair))

st.divider()

# Airlines attribution (info only)
try:
    air = load_airlines()
    with st.expander("Airlines attribution (info-only table)"):
        st.dataframe(air, use_container_width=True)
except FileNotFoundError:
    st.warning("File airlines attribution tidak ada. (optional)")
