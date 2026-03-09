# streamlit_app.py
# ------------------------------------------------------------
# Global Market-Based Mechanisms Dashboard
# - Reads: data/Global Market Based Mechanism.xlsx
# - QGIS-style map:
#     Country fill  = Carbon Pricing type (Carbon Tax / ETS / Both / None)
#     Scatter markers = Other mechanisms (CBAM, Tax Incentives, etc.)
# ------------------------------------------------------------

from __future__ import annotations

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import pycountry

st.set_page_config(page_title="Global MBM Dashboard", layout="wide")

FILE_PATH = "data/Global Market Based Mechanism.xlsx"

MECH_COLS = {
    "1. Carbon Tax": "Carbon Tax",
    "2. ETS": "ETS",
    "3. Tax Incentives": "Tax Incentives",
    "4. Fuel Mandates": "Fuel Mandates",
    "5. VCM project ": "VCM project",  # note trailing space matches your sheet header
    "6. Feebates": "Feebates",
    "7. CBAM": "CBAM",
    "8. AMC": "AMC",
}

# ── QGIS colour scheme (Carbon Pricing = country fill) ──────
CARBON_PRICING_COLORS = {
    "ETS + Carbon Tax": "#f4a261",   # orange
    "Carbon Tax":       "#90be6d",   # green
    "ETS":              "#457b9d",   # blue
    "No Carbon Pricing":"#d9d9d9",   # light grey
}

# ── Marker styles per other mechanism (QGIS legend) ─────────
MARKER_STYLES = {
    "CBAM":           {"symbol": "square",      "color": "#1d3557", "size": 9},
    "Tax Incentives": {"symbol": "diamond",     "color": "#9b5de5", "size": 10},
    "Fuel Mandates":  {"symbol": "triangle-up", "color": "#f4a261", "size": 11},
    "Feebates":       {"symbol": "circle",      "color": "#e63946", "size": 9},
    "VCM project":    {"symbol": "star",        "color": "#2a9d8f", "size": 12},
    "AMC":            {"symbol": "cross",       "color": "#457b9d", "size": 10},
}

# ── Country centroids (iso3 → lat, lon) ─────────────────────
CENTROIDS: dict[str, tuple[float, float]] = {
    "USA": (37.09, -95.71), "CAN": (56.13, -106.35), "MEX": (23.63, -102.55),
    "BRA": (-14.24, -51.93), "ARG": (-38.42, -63.62), "CHL": (-35.68, -71.54),
    "COL": (4.57, -74.30),  "PER": (-9.19, -75.02),  "VEN": (6.42, -66.59),
    "ECU": (-1.83, -78.18), "BOL": (-16.29, -63.59), "PRY": (-23.44, -58.44),
    "URY": (-32.52, -55.77),"GUY": (4.86, -58.93),   "SUR": (3.92, -56.03),
    "GBR": (55.38, -3.44),  "FRA": (46.23, 2.21),    "DEU": (51.17, 10.45),
    "ITA": (41.87, 12.57),  "ESP": (40.46, -3.75),   "PRT": (39.40, -8.22),
    "NLD": (52.13, 5.29),   "BEL": (50.50, 4.47),    "CHE": (46.82, 8.23),
    "AUT": (47.52, 14.55),  "SWE": (60.13, 18.64),   "NOR": (60.47, 8.47),
    "DNK": (56.26, 9.50),   "FIN": (61.92, 25.75),   "POL": (51.92, 19.15),
    "CZE": (49.82, 15.47),  "HUN": (47.16, 19.50),   "ROU": (45.94, 24.97),
    "GRC": (39.07, 21.82),  "IRL": (53.41, -8.24),   "LUX": (49.82, 6.13),
    "RUS": (61.52, 105.32), "UKR": (48.38, 31.17),   "TUR": (38.96, 35.24),
    "CHN": (35.86, 104.20), "JPN": (36.20, 138.25),  "KOR": (35.91, 127.77),
    "IND": (20.59, 78.96),  "AUS": (-25.27, 133.78), "NZL": (-40.90, 174.89),
    "ZAF": (-30.56, 22.94), "NGA": (9.08, 8.68),     "KEN": (-0.02, 37.91),
    "ETH": (9.15, 40.49),   "GHA": (7.95, -1.02),    "TZA": (-6.37, 34.89),
    "EGY": (26.82, 30.80),  "MAR": (31.79, -7.09),   "DZA": (28.03, 1.66),
    "TUN": (33.89, 9.54),   "SAU": (23.89, 45.08),   "ARE": (23.42, 53.85),
    "IRN": (32.43, 53.69),  "PAK": (30.38, 69.35),   "BGD": (23.68, 90.36),
    "IDN": (-0.79, 113.92), "MYS": (4.21, 108.00),   "THA": (15.87, 100.99),
    "VNM": (14.06, 108.28), "PHL": (12.88, 121.77),  "SGP": (1.35, 103.82),
    "KAZ": (48.02, 66.92),  "MNG": (46.86, 103.85),  "AFG": (33.94, 67.71),
    "NPL": (28.39, 84.12),  "LKA": (7.87, 80.77),    "MMR": (21.91, 95.96),
    "KHM": (12.57, 104.99), "LAO": (19.86, 102.50),  "PRK": (40.34, 127.51),
    "ISL": (64.96, -19.02), "LVA": (56.88, 24.60),   "LTU": (55.17, 23.88),
    "EST": (58.60, 25.01),  "SVK": (48.67, 19.70),   "SVN": (46.15, 14.99),
    "HRV": (45.10, 15.20),  "BGR": (42.73, 25.49),   "SRB": (44.02, 21.09),
    "MKD": (41.61, 21.75),  "ALB": (41.15, 20.17),   "BIH": (43.92, 17.68),
    "MNE": (42.71, 19.37),  "CYP": (35.13, 33.43),   "MLT": (35.94, 14.38),
    "GEO": (42.32, 43.36),  "ARM": (40.07, 45.04),   "AZE": (40.14, 47.58),
    "UZB": (41.38, 64.59),  "TKM": (38.97, 59.56),   "KGZ": (41.20, 74.77),
    "TJK": (38.86, 71.28),  "BLR": (53.71, 27.95),   "MDA": (47.41, 28.37),
    "CRI": (9.75, -83.75),  "GTM": (15.78, -90.23),  "HND": (15.20, -86.24),
    "SLV": (13.79, -88.90), "NIC": (12.87, -85.21),  "PAN": (8.54, -80.78),
    "CUB": (21.52, -77.78), "DOM": (18.74, -70.16),  "JAM": (18.11, -77.30),
    "TTO": (10.69, -61.22), "HTI": (18.97, -72.29),
    "CMR": (3.85, 11.50),   "CIV": (7.54, -5.55),    "SEN": (14.50, -14.45),
    "MLI": (17.57, -3.99),  "BFA": (12.36, -1.56),   "NER": (17.61, 8.08),
    "TCD": (15.45, 18.73),  "SDN": (12.86, 30.22),   "SOM": (5.15, 46.20),
    "MOZ": (-18.67, 35.53), "ZMB": (-13.13, 27.85),  "ZWE": (-19.02, 29.15),
    "AGO": (-11.20, 17.87), "COD": (-4.04, 21.76),   "COG": (-0.23, 15.83),
    "MDG": (-18.77, 46.87), "UGA": (1.37, 32.29),    "RWA": (-1.94, 29.87),
    "BDI": (-3.38, 29.92),  "MWI": (-13.25, 34.30),  "BWA": (-22.33, 24.68),
    "NAM": (-22.96, 18.49), "LSO": (-29.61, 28.23),  "SWZ": (-26.52, 31.47),
    "LBR": (6.43, -9.43),   "SLE": (8.46, -11.78),   "GIN": (9.95, -11.24),
    "GMB": (13.44, -15.31), "GNB": (11.80, -15.18),
    "DJI": (11.83, 42.59),  "ERI": (15.18, 39.78),   "LBY": (26.34, 17.23),
    "MRT": (21.01, -10.94), "TGO": (8.62, 0.82),     "BEN": (9.31, 2.32),
    "IRQ": (33.22, 43.68),  "SYR": (34.80, 38.99),   "YEM": (15.55, 48.52),
    "OMN": (21.51, 55.92),  "QAT": (25.35, 51.18),   "KWT": (29.31, 47.48),
    "BHR": (26.00, 50.55),  "JOR": (30.59, 36.24),   "LBN": (33.85, 35.86),
    "ISR": (31.05, 34.85),  "PSE": (31.95, 35.29),
    "TWN": (23.70, 121.00), "HKG": (22.40, 114.11),  "BRN": (4.54, 114.73),
    "TLS": (-8.87, 125.73), "PNG": (-6.31, 143.96),  "FJI": (-17.71, 178.07),
    "MDV": (3.20, 73.22),   "MUS": (-20.35, 57.55),  "COM": (-11.87, 43.87),
    "SYC": (-4.68, 55.49),  "FSM": (7.43, 150.55),   "GNQ": (1.65, 10.27),
    "GAB": (-0.80, 11.61),  "CAF": (6.61, 20.94),    "SSD": (6.88, 31.31),
}

# --- helper: country name -> ISO3
MANUAL_ISO3 = {
    "Côte d'Ivoire": "CIV",
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
    "Taiwan": "TWN",
    "Vietnam": "VNM",
    "Moldova": "MDA",
}


def to_iso3(name: str):
    name = (name or "").strip()
    if name in MANUAL_ISO3:
        return MANUAL_ISO3[name]
    try:
        c = pycountry.countries.lookup(name)
        return c.alpha_3
    except Exception:
        return None


@st.cache_data
def load_raw() -> pd.DataFrame:
    df = pd.read_excel(FILE_PATH)
    df.columns = [str(c).strip() for c in df.columns]
    return df


def tidy_long(df_raw: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    keep = ["No", "Country", "Region"] + [c.strip() for c in MECH_COLS.keys()] + ["Total Mechanism"]
    keep = [c for c in keep if c in df_raw.columns]
    df = df_raw[keep].copy()

    df = df[df["Country"].notna()]
    df["Country"] = df["Country"].astype(str).str.strip()
    df = df[df["Country"].str.lower() != "country"]

    value_cols = [c.strip() for c in MECH_COLS.keys() if c.strip() in df.columns]
    long = df.melt(
        id_vars=["No", "Country", "Region"],
        value_vars=value_cols,
        var_name="mechanism_type_raw",
        value_name="mechanism_detail",
    )

    long["mechanism_type"] = (
        long["mechanism_type_raw"]
        .map({k.strip(): v for k, v in MECH_COLS.items()})
        .fillna(long["mechanism_type_raw"])
    )
    long = long.drop(columns=["mechanism_type_raw"])

    long["mechanism_detail"] = long["mechanism_detail"].astype(str).str.strip()
    long = long[(long["mechanism_detail"] != "") & (long["mechanism_detail"].str.lower() != "nan")]

    # VCM numeric
    long["vcm_projects"] = pd.NA
    mask_vcm = long["mechanism_type"] == "VCM project"
    long.loc[mask_vcm, "vcm_projects"] = pd.to_numeric(
        long.loc[mask_vcm, "mechanism_detail"], errors="coerce"
    )

    # drop non-VCM zeros
    long = long[~((~mask_vcm) & (long["mechanism_detail"] == "0"))]

    return df, long


def summarize_mechanisms(df_long: pd.DataFrame) -> pd.DataFrame:
    g = (
        df_long.groupby(["Country", "mechanism_type"])["mechanism_detail"]
        .apply(
            lambda s: "; ".join(
                sorted({x for x in s.astype(str).str.strip() if x and x.lower() != "nan"})
            )
        )
        .reset_index()
    )

    types_list = (
        g.groupby("Country")["mechanism_type"]
        .apply(lambda s: "<br>".join([f"{i+1}. {t}" for i, t in enumerate(sorted(set(s.tolist())))]))
        .reset_index(name="mechanism_types_list_html")
    )

    counts = g.groupby("Country")["mechanism_type"].nunique().reset_index(name="mechanism_type_count")

    vcm = (
        df_long[df_long["mechanism_type"] == "VCM project"]
        .dropna(subset=["vcm_projects"])
        .groupby("Country")["vcm_projects"]
        .sum()
        .reset_index(name="vcm_projects_sum")
    )

    out = counts.merge(types_list, on="Country", how="left").merge(vcm, on="Country", how="left")
    out["vcm_projects_sum"] = pd.to_numeric(out["vcm_projects_sum"], errors="coerce").fillna(0).astype(int)
    out["mechanism_types_list_html"] = out["mechanism_types_list_html"].fillna(
        "No recorded mechanisms in this dataset."
    )
    return out


def get_carbon_pricing_type(country_mechs: set) -> str:
    has_ets = "ETS" in country_mechs
    has_tax = "Carbon Tax" in country_mechs
    if has_ets and has_tax:
        return "ETS + Carbon Tax"
    elif has_ets:
        return "ETS"
    elif has_tax:
        return "Carbon Tax"
    return "No Carbon Pricing"


# ===== Load
raw = load_raw()
wide, long = tidy_long(raw)

# ===== Header
st.title("Global Market-Based Mechanisms Dashboard")
st.caption(
    "Coverage: 194 countries and territories, including UN member states, microstates, and UN observer entities "
    "(e.g. Vatican City and Palestine). Kosovo is not included."
)

# ===== Sidebar (clean)
st.sidebar.header("Filters")
region_sel = st.sidebar.multiselect("Region", sorted(long["Region"].dropna().unique()), key="f_region")
type_sel = st.sidebar.multiselect(
    "Mechanism type", sorted(long["mechanism_type"].dropna().unique()), key="f_type"
)
country_sel = st.sidebar.multiselect("Country", sorted(long["Country"].dropna().unique()), key="f_country")
keyword = st.sidebar.text_input("Search in details", value="", key="f_kw").strip()
st.sidebar.caption(
    f"Active filters → Region:{len(region_sel)} | Type:{len(type_sel)} | Country:{len(country_sel)} | Keyword:'{keyword}'"
)

if st.sidebar.button("Reset filters", use_container_width=True):
    for k in ["f_region", "f_type", "f_country", "f_kw"]:
        if k in st.session_state:
            del st.session_state[k]
    st.rerun()

f = long.copy()
if region_sel:
    f = f[f["Region"].isin(region_sel)]
if type_sel:
    f = f[f["mechanism_type"].isin(type_sel)]
if country_sel:
    f = f[f["Country"].isin(country_sel)]
if keyword:
    f = f[f["mechanism_detail"].str.contains(keyword, case=False, na=False)]

# ===== KPIs
k1, k2, k3, k4 = st.columns(4)
k1.metric("Countries covered", int(wide["Country"].nunique()))

wide_view = wide.copy()
if region_sel:
    wide_view = wide_view[wide_view["Region"].isin(region_sel)]
if country_sel:
    wide_view = wide_view[wide_view["Country"].isin(country_sel)]

k2.metric("Countries in view", int(wide_view["Country"].nunique()))
k3.metric("Mechanism types in view", int(f["mechanism_type"].nunique()))

vcm_sum = f.loc[f["mechanism_type"] == "VCM project", "vcm_projects"].sum(min_count=1)
k4.metric("VCM projects (sum)", 0 if pd.isna(vcm_sum) else int(vcm_sum))

st.divider()

# ===== QGIS-Style World Map =================================
st.subheader("World Map")

# Build per-country carbon pricing classification
country_mechs_map = (
    f.groupby("Country")["mechanism_type"]
    .apply(set)
    .to_dict()
)

base = wide_view[["Country", "Region"]].drop_duplicates().copy()
base["iso3"]           = base["Country"].apply(to_iso3)
base["cp_type"]        = base["Country"].apply(
    lambda c: get_carbon_pricing_type(country_mechs_map.get(c, set()))
)
base["mech_list_html"] = base["Country"].apply(
    lambda c: "<br>".join(sorted(country_mechs_map.get(c, {"No recorded mechanisms"})))
)

missing_iso = base[base["iso3"].isna()]["Country"].tolist()
if missing_iso:
    st.warning(
        f"ISO3 not found for {len(missing_iso)} countries/territories (not shown on map). "
        f"Examples: {', '.join(missing_iso[:10])}"
    )

m_plot = base.dropna(subset=["iso3"]).copy()

# ── Layer 1: Choropleth fill by Carbon Pricing type ─────────
fig_map = go.Figure()

for cp_type, color in CARBON_PRICING_COLORS.items():
    subset = m_plot[m_plot["cp_type"] == cp_type]
    if subset.empty:
        continue
    fig_map.add_trace(go.Choropleth(
        locations=subset["iso3"],
        z=[1] * len(subset),
        colorscale=[[0, color], [1, color]],
        showscale=False,
        hovertemplate=(
            "<b>%{customdata[0]}</b><br>"
            "Carbon Pricing: %{customdata[1]}<br>"
            "Mechanisms:<br>%{customdata[2]}"
            "<extra></extra>"
        ),
        customdata=subset[["Country", "cp_type", "mech_list_html"]].values,
        name=cp_type,
        showlegend=True,
        marker_line_color="white",
        marker_line_width=0.5,
        legendgroup="Carbon Pricing",
        legendgrouptitle_text="Carbon Pricing" if cp_type == "ETS + Carbon Tax" else "",
    ))

# ── Layer 2: Scatter markers per other mechanism ────────────
OTHER_MECHS = ["CBAM", "Tax Incentives", "Fuel Mandates", "Feebates", "VCM project", "AMC"]

first_marker = True
for mech in OTHER_MECHS:
    style = MARKER_STYLES[mech]
    mech_countries = f[f["mechanism_type"] == mech]["Country"].unique()
    rows = []
    for country in mech_countries:
        iso3 = to_iso3(country)
        if iso3 and iso3 in CENTROIDS:
            lat, lon = CENTROIDS[iso3]
            rows.append({"country": country, "lat": lat, "lon": lon})
    if not rows:
        continue
    df_m = pd.DataFrame(rows)
    fig_map.add_trace(go.Scattergeo(
        lat=df_m["lat"],
        lon=df_m["lon"],
        mode="markers",
        marker=dict(
            symbol=style["symbol"],
            color=style["color"],
            size=style["size"],
            line=dict(width=0.8, color="white"),
        ),
        text=df_m["country"],
        hovertemplate="<b>%{text}</b><br>" + mech + "<extra></extra>",
        name=mech,
        showlegend=True,
        legendgroup="Other mechanisms",
        legendgrouptitle_text="Other mechanisms" if first_marker else "",
    ))
    first_marker = False

fig_map.update_layout(
    height=560,
    margin=dict(l=0, r=0, t=10, b=0),
    paper_bgcolor="white",
    geo=dict(
        showframe=False,
        showcoastlines=True,
        coastlinecolor="#aaaaaa",
        showcountries=True,
        countrycolor="#cccccc",
        showland=True,
        landcolor="#f0f0f0",
        showocean=True,
        oceancolor="#e8f4f8",
        projection_type="natural earth",
    ),
    legend=dict(
        title="<b>Legend</b>",
        bgcolor="white",
        bordercolor="#cccccc",
        borderwidth=1,
        x=0.01,
        y=0.38,
        font=dict(size=11),
        tracegroupgap=3,
    ),
)

st.plotly_chart(fig_map, use_container_width=True, key="map_qgis")

# ===== Tabs
tab1, tab2, tab3 = st.tabs(["Summary charts", "Country profile", "Data table"])

with tab1:
    c1, c2 = st.columns(2)

    with c1:
        st.subheader("Countries by mechanism type")
        by_type = (
            f.groupby("mechanism_type")["Country"].nunique()
            .reset_index(name="countries")
            .sort_values("countries", ascending=False)
        )
        st.plotly_chart(px.bar(by_type, x="mechanism_type", y="countries"), use_container_width=True, key="bar_type")

    with c2:
        st.subheader("Countries by Carbon Pricing type")
        cp_counts = m_plot["cp_type"].value_counts().reset_index()
        cp_counts.columns = ["type", "count"]
        st.plotly_chart(
            px.pie(cp_counts, names="type", values="count",
                   color="type", color_discrete_map=CARBON_PRICING_COLORS),
            use_container_width=True, key="pie_cp"
        )

with tab2:
    st.subheader("Country profile")
    countries_all = sorted(wide["Country"].unique())
    default_idx = countries_all.index("United Kingdom") if "United Kingdom" in countries_all else 0
    sel = st.selectbox("Select a country", countries_all, index=default_idx, key="country_profile")

    cf = long[long["Country"] == sel].copy()
    if len(cf):
        st.write("Region:", cf["Region"].iloc[0])
        cp_type = get_carbon_pricing_type(set(cf["mechanism_type"].unique()))
        color = CARBON_PRICING_COLORS[cp_type]
        st.markdown(
            f"**Carbon Pricing:** <span style='background:{color};padding:2px 8px;"
            f"border-radius:4px'>{cp_type}</span>",
            unsafe_allow_html=True
        )
        st.write("---")
    else:
        st.write("Region: —")

    prof = (
        cf.groupby("mechanism_type")["mechanism_detail"]
        .apply(
            lambda s: "\n".join(
                f"- {x}" for x in sorted({v.strip() for v in s.astype(str) if v and v.lower() != "nan"})
            )
        )
        .reset_index()
        .sort_values("mechanism_type")
    )

    for _, r in prof.iterrows():
        st.markdown(f"**{r['mechanism_type']}**")
        st.markdown(r["mechanism_detail"])

with tab3:
    st.subheader("Detail table (filtered)")
    show_cols = ["Country", "Region", "mechanism_type", "mechanism_detail", "vcm_projects"]
    st.dataframe(
        f[show_cols].sort_values(["Country", "mechanism_type"]),
        use_container_width=True,
        hide_index=True,
    )

    csv = f[["Country", "Region", "mechanism_type", "mechanism_detail"]].to_csv(index=False).encode("utf-8")
    st.download_button("Download filtered data (CSV)", csv, "filtered_mbm.csv", "text/csv", use_container_width=True)
