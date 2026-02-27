import streamlit as st
import pandas as pd
import plotly.express as px
import pycountry

# =========================
# Config
# =========================
st.set_page_config(page_title="CDM Activities in Transition", layout="wide")

DATA_PATH = "CDM.xlsx"  # ubah jika beda lokasi

# =========================
# Helpers
# =========================
SPECIAL_ISO3 = {
    "Republic of Korea": "KOR",
    "Korea, Republic of": "KOR",
    "Viet Nam": "VNM",
    "Iran": "IRN",
    "Iran (Islamic Republic of)": "IRN",
    "Lao PDR": "LAO",
    "Democratic Republic of the Congo": "COD",
    "Congo, The Democratic Republic of the": "COD",
    "Cote d'Ivoire": "CIV",
    "Côte d’Ivoire": "CIV",
}

def token_to_iso3(tok: str):
    tok = str(tok).strip()
    if tok.lower() in ("multiple", "", "nan"):
        return None
    if tok in SPECIAL_ISO3:
        return SPECIAL_ISO3[tok]

    # If ISO2 like "ID"
    if len(tok) == 2 and tok.isalpha():
        c = pycountry.countries.get(alpha_2=tok.upper())
        return c.alpha_3 if c else None

    # If ISO3 like "IDN"
    if len(tok) == 3 and tok.isalpha():
        c = pycountry.countries.get(alpha_3=tok.upper())
        return c.alpha_3 if c else None

    # Country name lookup
    try:
        return pycountry.countries.lookup(tok).alpha_3
    except Exception:
        return None

def split_countries(val):
    if pd.isna(val):
        return []
    s = str(val)
    if ";" in s:
        toks = [t.strip() for t in s.split(";")]
        return [t for t in toks if t and t.lower() != "multiple"]
    return [s.strip()]

@st.cache_data
def load_data(path: str) -> pd.DataFrame:
    df = pd.read_excel(path)

    # Clean column names (strip)
    df.columns = [c.strip() for c in df.columns]

    # Parse dates if exist
    for col in ["A6 relevant period from", "A6 relevant period to", "Approval Date"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    # Standardize key columns if your sheet has odd spaces
    # Example: " Reductions (ktCO2e/yr)" has leading space in your file
    if " Reductions (ktCO2e/yr)" in df.columns and "Reductions (ktCO2e/yr)" not in df.columns:
        df = df.rename(columns={" Reductions (ktCO2e/yr)": "Reductions (ktCO2e/yr)"})

    return df

def apply_filters(df: pd.DataFrame) -> pd.DataFrame:
    # Sidebar filters
    st.sidebar.header("Filters")

    # Build options safely
    def multiselect(col, label):
        if col not in df.columns:
            return None
        opts = sorted([x for x in df[col].dropna().unique().tolist()])
        return st.sidebar.multiselect(label, opts)

    f_region = multiselect("Region", "Region")
    f_subregion = multiselect("Sub-region", "Sub-region")
    f_host = multiselect("Host country", "Host Party")
    f_type = multiselect("Type", "Activity Type (Type)")
    f_type1 = multiselect("Type.1", "Tech Type (Type.1)")
    f_transition = multiselect("Transition Request", "Transition Request")
    f_method = multiselect("Methodology after transition", "Methodology after transition")
    f_approved = multiselect("Approved by Host Party", "Approved by Host Party")

    out = df.copy()

    def filt(col, selected):
        nonlocal out
        if selected and col in out.columns:
            out = out[out[col].isin(selected)]

    filt("Region", f_region)
    filt("Sub-region", f_subregion)
    filt("Host country", f_host)
    filt("Type", f_type)
    filt("Type.1", f_type1)
    filt("Transition Request", f_transition)
    filt("Methodology after transition", f_method)
    filt("Approved by Host Party", f_approved)

    # Text search (Title)
    if "Title" in out.columns:
        q = st.sidebar.text_input("Search in Title")
        if q:
            out = out[out["Title"].astype(str).str.contains(q, case=False, na=False)]

    # Clear
    st.sidebar.caption("Tip: kosongkan pilihan untuk reset.")
    return out

def make_exploded_for_geo(df_filtered: pd.DataFrame) -> pd.DataFrame:
    # explode Host country for multi-country rows (e.g., "CL; EG; ...")
    ex = df_filtered.copy()
    ex["host_token"] = ex["Host country"].apply(split_countries)
    ex = ex.explode("host_token")
    ex["country_clean"] = ex["host_token"].astype(str).str.strip()
    ex["iso3"] = ex["country_clean"].apply(token_to_iso3)
    ex = ex[ex["iso3"].notna()]  # drop 'multiple' / unknown
    return ex

# =========================
# App
# =========================
st.title("List of CDM activities in transition (Streamlit)")

df = load_data(DATA_PATH)
df_f = apply_filters(df)

# KPIs
total_selected = len(df_f)
requested_transition = (df_f["Transition Request"].astype(str).str.lower() == "yes").sum() if "Transition Request" in df_f.columns else 0
approved_yes = (df_f["Approved by Host Party"].astype(str).str.lower() == "yes").sum() if "Approved by Host Party" in df_f.columns else 0

if "Reductions (ktCO2e/yr)" in df_f.columns:
    reductions_sum = pd.to_numeric(df_f["Reductions (ktCO2e/yr)"], errors="coerce").fillna(0).sum()
else:
    reductions_sum = 0

k1, k2, k3, k4 = st.columns(4)
k1.metric("Selected", f"{total_selected:,}")
k2.metric("Requested transition", f"{requested_transition:,}")
k3.metric("Approved by Host Party (yes)", f"{approved_yes:,}")
k4.metric("Reductions sum (ktCO2e/yr)", f"{reductions_sum:,.1f}")

st.divider()

# Top bar + map side-by-side
left, right = st.columns([1.05, 1.0], gap="large")

ex = make_exploded_for_geo(df_f)

# Bar chart: counts by host party
with left:
    st.subheader("CDM Activity by Host Party")
    topn = st.slider("Top N", min_value=5, max_value=30, value=10, step=1)
    counts = (
        ex.groupby("country_clean", dropna=True)
          .size()
          .reset_index(name="count")
          .sort_values("count", ascending=False)
          .head(topn)
    )
    fig_bar = px.bar(
        counts,
        x="count",
        y="country_clean",
        orientation="h",
        labels={"count": "Activities", "country_clean": "Host Party"},
    )
    fig_bar.update_layout(height=380, margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig_bar, use_container_width=True)

# ======================
# PIE: Emission reductions by Host Country
# ======================
st.subheader("Emission Reductions by Host Country (ktCO2e/yr)")

def split_countries(val):
    if pd.isna(val):
        return []
    s = str(val)
    if ";" in s:
        toks = [t.strip() for t in s.split(";")]
        return [t for t in toks if t and t.lower() != "multiple"]
    return [s.strip()] if s.strip().lower() != "multiple" else []

# Pastikan nama kolom reductions benar (kadang ada spasi depan di Excel)
if "Reductions (ktCO2e/yr)" not in df.columns and " Reductions (ktCO2e/yr)" in df.columns:
    df = df.rename(columns={" Reductions (ktCO2e/yr)": "Reductions (ktCO2e/yr)"})

if "Reductions (ktCO2e/yr)" in df.columns and "Host country" in df.columns:
    pie_df = df.copy()

    # numeric reductions
    pie_df["reductions"] = pd.to_numeric(pie_df["Reductions (ktCO2e/yr)"], errors="coerce").fillna(0)

    # explode countries
    pie_df["host_token"] = pie_df["Host country"].apply(split_countries)
    pie_df = pie_df.explode("host_token")
    pie_df["host_token"] = pie_df["host_token"].astype(str).str.strip()
    pie_df = pie_df[pie_df["host_token"].notna() & (pie_df["host_token"] != "")]

    # sum reductions by country
    red_by_country = (
        pie_df.groupby("host_token", as_index=False)["reductions"]
        .sum()
        .sort_values("reductions", ascending=False)
    )

    # Top N + Others biar pie chart nggak berantakan
    topn_pie = st.slider("Top N countries (pie)", 5, 25, 10, 1)
    top = red_by_country.head(topn_pie)
    others_sum = red_by_country["reductions"].iloc[topn_pie:].sum()

    if others_sum > 0:
        top = pd.concat(
            [top, pd.DataFrame([{"host_token": "Others", "reductions": others_sum}])],
            ignore_index=True
        )

    fig_pie = px.pie(
        top,
        names="host_token",
        values="reductions",
        hole=0.35,  # donut style
    )
    fig_pie.update_layout(height=420, margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig_pie, use_container_width=True)
else:
    st.info("Kolom 'Host country' atau 'Reductions (ktCO2e/yr)' tidak ditemukan di dataset.")
with right:
    st.subheader("World map (by host party)")
    # Choropleth by activity count
    geo_counts = ex.groupby("iso3").size().reset_index(name="count")
    fig_map = px.choropleth(
        geo_counts,
        locations="iso3",
        color="count",
        projection="natural earth",
        labels={"count": "Activities"},
    )
    fig_map.update_layout(height=380, margin=dict(l=0, r=0, t=10, b=0))
    st.plotly_chart(fig_map, use_container_width=True)

st.divider()

# Detail table (like UNFCCC bottom table)
st.subheader("Details")
cols_prefer = [
    "Region", "Sub-region", "Host country", "Title", "Type", "Type.1",
    "Reductions (ktCO2e/yr)",
    "A6 relevant period from", "A6 relevant period to",
    "A6 relevant period \n(in years)",
    "Transition Request", "Methodology after transition",
    "Sectoral Sope", "Approved by Host Party", "Approval Date"
]
cols_show = [c for c in cols_prefer if c in df_f.columns]
if not cols_show:
    cols_show = df_f.columns.tolist()

st.dataframe(df_f[cols_show], use_container_width=True, height=420)
