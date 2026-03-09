# streamlit_app.py
# ------------------------------------------------------------
# Global Market-Based Mechanisms Dashboard
# - Reads: data/Global Market Based Mechanism.xlsx
# - QGIS-style map + click country → detail card
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
    "5. VCM project ": "VCM project",
    "6. Feebates": "Feebates",
    "7. CBAM": "CBAM",
    "8. AMC": "AMC",
}

CARBON_PRICING_COLORS = {
    "ETS + Carbon Tax": "#f4a261",
    "Carbon Tax":       "#90be6d",
    "ETS":              "#457b9d",
    "No Carbon Pricing":"#f0f0f0",
}

# ── Marker styles — outline hitam tipis ─────────────────────
MARKER_STYLES = {
    "CBAM":           {"symbol": "square",      "color": "#4a90d9", "size": 6},
    "Tax Incentives": {"symbol": "diamond",     "color": "#9b59b6", "size": 7},
    "Fuel Mandates":  {"symbol": "triangle-up", "color": "#e07b00", "size": 7},
    "Feebates":       {"symbol": "circle",      "color": "#e63946", "size": 6},
    "VCM project":    {"symbol": "star",        "color": "#2a9d8f", "size": 8},
    "AMC":            {"symbol": "cross",       "color": "#5b9bd5", "size": 7},
}

# ── Warna kotak per mekanisme di card ────────────────────────
MECH_BOX_COLORS = {
    "Carbon Tax":     "#90be6d",
    "ETS":            "#457b9d",
    "Tax Incentives": "#7b2d8b",
    "Fuel Mandates":  "#e07b00",
    "Feebates":       "#e63946",
    "VCM project":    "#2a9d8f",
    "CBAM":           "#1d3557",
    "AMC":            "#5e9bbd",
}

MECH_OFFSETS = {
    "CBAM":           ( 0.0,   0.0),
    "Tax Incentives": ( 0.0,   1.5),
    "Fuel Mandates":  ( 0.0,  -1.5),
    "Feebates":       ( 1.5,   0.0),
    "VCM project":    (-1.5,   0.0),
    "AMC":            ( 1.5,   1.5),
}

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
    "TTO": (10.69, -61.22), "HTI": (18.97, -72.29),  "BLZ": (17.19, -88.50),
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
    "SYC": (-4.68, 55.49),  "FSM": (7.43, 150.55),
    "GNQ": (1.65, 10.27),   "GAB": (-0.80, 11.61),   "CAF": (6.61, 20.94),
    "SSD": (6.88, 31.31),
}

MANUAL_ISO3 = {
    "Côte d'Ivoire": "CIV", "São Tomé and Príncipe": "STP",
    "Democratic Republic of the Congo": "COD", "Republic of the Congo": "COG",
    "United States": "USA", "Russia": "RUS", "Iran": "IRN", "Syria": "SYR",
    "Vatican City": "VAT", "North Korea": "PRK", "South Korea": "KOR",
    "Laos": "LAO", "Timor-Leste": "TLS", "Brunei Darussalam": "BRN",
    "Bolivia": "BOL", "Venezuela": "VEN", "Tanzania": "TZA",
    "Micronesia": "FSM", "Palestine": "PSE", "Taiwan": "TWN",
    "Vietnam": "VNM", "Moldova": "MDA",
}




def to_iso3(name: str):
    name = (name or "").strip()
    if name in MANUAL_ISO3:
        return MANUAL_ISO3[name]
    try:
        return pycountry.countries.lookup(name).alpha_3
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
    long["vcm_projects"] = pd.NA
    mask_vcm = long["mechanism_type"] == "VCM project"
    long.loc[mask_vcm, "vcm_projects"] = pd.to_numeric(
        long.loc[mask_vcm, "mechanism_detail"], errors="coerce"
    )
    long = long[~((~mask_vcm) & (long["mechanism_detail"] == "0"))]
    return df, long


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


def render_country_card(country: str, region: str, long_df: pd.DataFrame):
    """Render detail card — nama, region, CP type, N mechs, kotak warna per mekanisme."""
    cf = long_df[long_df["Country"] == country].copy()
    mechs = sorted(cf["mechanism_type"].unique()) if len(cf) else []
    mechs_set = set(mechs)
    cp_type = get_carbon_pricing_type(mechs_set)
    cp_color = CARBON_PRICING_COLORS[cp_type]
    n_mechs = len(mechs)

    # Kotak mekanisme — warna beda per mech
    boxes_html = ""
    for m in mechs:
        bg = MECH_BOX_COLORS.get(m, "#888")
        # pilih warna teks: putih untuk warna gelap, hitam untuk terang
        txt_color = "white" if bg not in ("#90be6d", "#f0f0f0") else "#333"
        boxes_html += f"""
        <div style="
            background:{bg};
            color:{txt_color};
            padding:5px 12px;
            border-radius:6px;
            font-weight:700;
            font-size:12px;
            border: 1.5px solid #222;
            white-space:nowrap;
        ">{m}</div>"""

    st.markdown(f"""
    <div style="
        background: white;
        border: 2px solid #e0e0e0;
        border-radius: 12px;
        padding: 20px 24px;
        box-shadow: 0 4px 16px rgba(0,0,0,0.08);
        margin-bottom: 12px;
    ">
        <div style="font-size:22px; font-weight:800; color:#1a1a2e; letter-spacing:1px; margin-bottom:4px;">
            {country.upper()}
        </div>
        <div style="font-size:12px; color:#888; margin-bottom:14px;">
            {region}
        </div>
        <div style="display:flex; gap:8px; margin-bottom:14px; flex-wrap:wrap; align-items:center;">
            <div style="
                background:{cp_color};
                color:#333;
                padding:5px 14px;
                border-radius:6px;
                font-weight:600;
                font-size:12px;
                border: 1.5px solid #222;
            ">{cp_type}</div>
            <div style="
                background:#1a1a2e;
                color:white;
                padding:5px 14px;
                border-radius:6px;
                font-weight:700;
                font-size:12px;
                border: 1.5px solid #222;
            ">{n_mechs} MECHANISM{'S' if n_mechs != 1 else ''}</div>
        </div>
        <div style="display:flex; gap:6px; flex-wrap:wrap;">
            {boxes_html}
        </div>
    </div>
    """, unsafe_allow_html=True)

    if n_mechs == 0:
        st.info("No recorded mechanisms for this country.")


# ===== Load
raw = load_raw()
wide, long = tidy_long(raw)

# ===== Header
st.title("Global Market-Based Mechanisms Dashboard")
st.caption(
    "Coverage: 194 countries and territories. Click a country on the map to see details."
)

# ===== Sidebar
st.sidebar.header("Filters")
region_sel  = st.sidebar.multiselect("Region",         sorted(long["Region"].dropna().unique()), key="f_region")
type_sel    = st.sidebar.multiselect("Mechanism type", sorted(long["mechanism_type"].dropna().unique()), key="f_type")
country_sel = st.sidebar.multiselect("Country",        sorted(long["Country"].dropna().unique()), key="f_country")
keyword     = st.sidebar.text_input("Search in details", value="", key="f_kw").strip()
st.sidebar.caption(
    f"Active filters → Region:{len(region_sel)} | Type:{len(type_sel)} | Country:{len(country_sel)} | Keyword:'{keyword}'"
)

if st.sidebar.button("Reset filters", use_container_width=True):
    for k in ["f_region", "f_type", "f_country", "f_kw"]:
        st.session_state.pop(k, None)
    st.rerun()

f = long.copy()
if region_sel:   f = f[f["Region"].isin(region_sel)]
if type_sel:     f = f[f["mechanism_type"].isin(type_sel)]
if country_sel:  f = f[f["Country"].isin(country_sel)]
if keyword:      f = f[f["mechanism_detail"].str.contains(keyword, case=False, na=False)]

# ===== KPIs
k1, k2, k3, k4 = st.columns(4)
k1.metric("Countries covered", int(wide["Country"].nunique()))
wide_view = wide.copy()
if region_sel:   wide_view = wide_view[wide_view["Region"].isin(region_sel)]
if country_sel:  wide_view = wide_view[wide_view["Country"].isin(country_sel)]
k2.metric("Countries in view", int(wide_view["Country"].nunique()))
k3.metric("Mechanism types in view", int(f["mechanism_type"].nunique()))
vcm_sum = f.loc[f["mechanism_type"] == "VCM project", "vcm_projects"].sum(min_count=1)
k4.metric("VCM projects (sum)", 0 if pd.isna(vcm_sum) else int(vcm_sum))

st.divider()

# ===== Map
st.subheader("World Map")
st.caption("🖱️ Click on a country to view its detail")

country_mechs_map = f.groupby("Country")["mechanism_type"].apply(set).to_dict()

base = wide_view[["Country", "Region"]].drop_duplicates().copy()
base["iso3"]       = base["Country"].apply(to_iso3)
base["cp_type"]    = base["Country"].apply(lambda c: get_carbon_pricing_type(country_mechs_map.get(c, set())))
base["hover_mechs"]= base["Country"].apply(
    lambda c: "<br>".join(sorted(country_mechs_map.get(c, {"No recorded mechanisms"})))
)
base["n_mechs"] = base["Country"].apply(lambda c: len(country_mechs_map.get(c, set())))

missing_iso = base[base["iso3"].isna()]["Country"].tolist()
if missing_iso:
    st.warning(
        f"ISO3 not found for {len(missing_iso)} countries/territories (not shown on map). "
        f"Examples: {', '.join(missing_iso[:10])}"
    )

m_plot = base.dropna(subset=["iso3"]).copy()

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
            "%{customdata[1]} mechanisms<br>"
            "──────────<br>"
            "%{customdata[2]}"
            "<extra></extra>"
        ),
        customdata=subset[["Country", "n_mechs", "hover_mechs"]].values,
        name=cp_type,
        showlegend=False,          # sembunyikan dari legend (diganti dummy di bawah)
        marker_line_color="#111111",
        marker_line_width=0.8,
    ))

# Dummy legend untuk Carbon Pricing — kotak dengan outline hitam
for i, (cp_type, color) in enumerate(CARBON_PRICING_COLORS.items()):
    fig_map.add_trace(go.Scattergeo(
        lat=[None], lon=[None],
        mode="markers",
        marker=dict(
            symbol="square",
            color=color,
            size=10,
            line=dict(width=2.0, color="#000000"),
        ),
        name=cp_type,
        showlegend=True,
        legendgroup="cp",
        legendgrouptitle_text="Carbon Pricing" if i == 0 else "",
        hoverinfo="skip",
    ))

OTHER_MECHS = ["CBAM", "Tax Incentives", "Fuel Mandates", "Feebates", "VCM project", "AMC"]

for i, mech in enumerate(OTHER_MECHS):
    style = MARKER_STYLES[mech]
    dlat, dlon = MECH_OFFSETS[mech]
    mech_countries = f[f["mechanism_type"] == mech]["Country"].unique()
    rows = []
    for country in mech_countries:
        iso3 = to_iso3(country)
        if iso3 and iso3 in CENTROIDS:
            lat, lon = CENTROIDS[iso3]
            rows.append({"country": country, "lat": lat + dlat, "lon": lon + dlon})
    if not rows:
        continue
    df_m = pd.DataFrame(rows)
    df_m["all_mechs"] = df_m["country"].apply(
        lambda c: "<br>".join(sorted(country_mechs_map.get(c, {mech})))
    )
    fig_map.add_trace(go.Scattergeo(
        lat=df_m["lat"],
        lon=df_m["lon"],
        mode="markers",
        marker=dict(
            symbol=style["symbol"],
            color=style["color"],
            size=style["size"],
            line=dict(width=1.5, color="#000000"),
            opacity=1.0,
        ),
        text=df_m["country"],
        hoverinfo="skip",
        name=mech,
        showlegend=True,
        legendgroup="other",
        legendgrouptitle_text="Other mechanisms" if i == 0 else "",
    ))

fig_map.update_layout(
    height=540,
    margin=dict(l=0, r=0, t=5, b=0),
    paper_bgcolor="white",
    uirevision="map_fixed",
    geo=dict(
        projection_type="equirectangular",
        showframe=True,
        framecolor="#333333",
        framewidth=1,
        showcoastlines=True,
        coastlinecolor="#333333",
        coastlinewidth=0.8,
        showcountries=True,
        countrycolor="#333333",
        countrywidth=0.6,
        showland=True,
        landcolor="#f5f5f5",
        showocean=False,
        showlakes=False,
        bgcolor="white",
        lataxis_range=[-60, 85],
        lonaxis_range=[-180, 180],
    ),
    legend=dict(
        title="<b>Legend</b>",
        bgcolor="white",
        bordercolor="#333333",
        borderwidth=1,
        x=0.01,
        y=0.40,
        font=dict(size=11),
        tracegroupgap=5,
        itemsizing="constant",
    ),
    clickmode="event+select",
)

clicked = st.plotly_chart(
    fig_map,
    use_container_width=True,
    key="map_qgis",
    on_select="rerun",
    selection_mode="points",
)

# ===== Detail card di bawah peta
# Try to get clicked country
selected_country = None
if clicked and clicked.get("selection") and clicked["selection"].get("points"):
    pts = clicked["selection"]["points"]
    if pts:
        pt = pts[0]
        cd = pt.get("customdata")
        txt = pt.get("text")
        if cd and isinstance(cd, (list, tuple)) and len(cd) > 0:
            selected_country = cd[0]
        elif txt:
            selected_country = txt

if selected_country:
    region_val = wide[wide["Country"] == selected_country]["Region"].iloc[0] \
        if selected_country in wide["Country"].values else "—"
    render_country_card(selected_country, region_val, long)
else:
    st.markdown("""
    <div style="
        background:#f8f9fa;
        border: 2px dashed #ccc;
        border-radius: 10px;
        padding: 20px 24px;
        text-align: center;
        color: #aaa;
        margin-top: 8px;
    ">
        🗺️ &nbsp;<b>Click a country</b> on the map to see its mechanisms
    </div>
    """, unsafe_allow_html=True)

st.divider()

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
        st.plotly_chart(
            px.bar(by_type, x="mechanism_type", y="countries",
                   color="mechanism_type", color_discrete_sequence=px.colors.qualitative.Set2),
            use_container_width=True, key="bar_type"
        )
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
    st.subheader("Country profile (dropdown)")
    countries_all = sorted(wide["Country"].unique())
    default_idx = countries_all.index("United Kingdom") if "United Kingdom" in countries_all else 0
    sel = st.selectbox("Select a country", countries_all, index=default_idx, key="country_profile")
    region_val2 = wide[wide["Country"] == sel]["Region"].iloc[0] if sel in wide["Country"].values else "—"
    render_country_card(sel, region_val2, long)

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
