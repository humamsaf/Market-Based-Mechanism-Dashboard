# pages/3_CDM.py
import streamlit as st
import pandas as pd
import plotly.express as px
import pycountry

from utils.paths import data_path

st.set_page_config(page_title="CDM Activities in Transition", page_icon="📜", layout="wide")

DATA_PATH = data_path("CDM.xlsx")

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

    if len(tok) == 2 and tok.isalpha():
        c = pycountry.countries.get(alpha_2=tok.upper())
        return c.alpha_3 if c else None

    if len(tok) == 3 and tok.isalpha():
        c = pycountry.countries.get(alpha_3=tok.upper())
        return c.alpha_3 if c else None

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
        return [t for t in toks if t]
    if "," in s:
        toks = [t.strip() for t in s.split(",")]
        return [t for t in toks if t]
    return [s.strip()]

@st.cache_data(show_spinner=False)
def load_data(path):
    df = pd.read_excel(path)
    df.columns = [str(c).strip() for c in df.columns]
    return df

st.title("📜 CDM Activities in Transition")
st.caption("CDM dataset → map + filters")

try:
    df = load_data(DATA_PATH)
except FileNotFoundError:
    st.error(f"File tidak ditemukan: {DATA_PATH}. Pastikan `CDM.xlsx` ada di folder `data/`.")
    st.stop()

if df.empty:
    st.warning("Dataset kosong.")
    st.stop()

# Heuristic: detect a country column (adjust if needed)
country_col = None
for c in df.columns:
    lc = c.lower()
    if "host" in lc and "country" in lc:
        country_col = c
        break
if country_col is None:
    # fallback: any column contains "country"
    for c in df.columns:
        if "country" in c.lower():
            country_col = c
            break

if country_col is None:
    st.error("Tidak menemukan kolom country/host country di CDM.xlsx. Tolong cek nama kolomnya.")
    st.dataframe(df.head(20), use_container_width=True)
    st.stop()

# explode multi-country entries if any
tmp = df.copy()
tmp["__countries__"] = tmp[country_col].apply(split_countries)
tmp = tmp.explode("__countries__")
tmp["iso3"] = tmp["__countries__"].apply(token_to_iso3)

left, right = st.columns([2, 1])

with right:
    st.subheader("Filters")
    valid = tmp.dropna(subset=["__countries__"])
    countries = pd.Series(valid["__countries__"].unique()).sort_values()
    selected = st.multiselect("Host country", options=countries.tolist(), default=[])
    if selected:
        tmp2 = tmp[tmp["__countries__"].isin(selected)].copy()
    else:
        tmp2 = tmp.copy()

    st.metric("Rows", len(tmp2))

with left:
    st.subheader("Map (counts by country)")
    grp = tmp2.dropna(subset=["iso3"]).groupby(["iso3", "__countries__"]).size().reset_index(name="count")
    if grp.empty:
        st.info("Tidak ada data map (ISO3 tidak terdeteksi). Coba cek format nama negara.")
    else:
        fig = px.choropleth(
            grp,
            locations="iso3",
            color="count",
            hover_name="__countries__",
            color_continuous_scale="Blues",
        )
        fig.update_layout(margin=dict(l=0, r=0, t=0, b=0))
        st.plotly_chart(fig, use_container_width=True)

st.divider()
with st.expander("Raw data preview"):
    st.dataframe(df, use_container_width=True)
