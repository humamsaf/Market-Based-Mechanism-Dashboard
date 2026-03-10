# streamlit_app.py — Global MBM Dashboard
# Single-file app with top navbar via query_params routing
from __future__ import annotations
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import pycountry

st.set_page_config(
    page_title="Global MBM Dashboard",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    section[data-testid="stSidebar"] {display: none !important;}
    button[data-testid="collapsedControl"] {display: none !important;}
    .block-container {
        padding-top: 0 !important;
        padding-left: 2rem;
        padding-right: 2rem;
    }
    .navbar {
        display: flex;
        align-items: center;
        background-color: #1a1a2e;
        padding: 0 2rem;
        height: 56px;
        margin-left: -2rem;
        margin-right: -2rem;
        margin-bottom: 1.5rem;
    }
    .navbar-brand {
        font-size: 18px;
        font-weight: 800;
        color: white !important;
        text-decoration: none !important;
        letter-spacing: 1px;
        margin-right: 2.5rem;
        line-height: 1.2;
    }
    .navbar-brand span {
        font-size: 10px;
        font-weight: 400;
        color: #aab4c8;
        display: block;
        letter-spacing: 0.5px;
    }
    .nav-links { display: flex; height: 56px; align-items: stretch; }
    .nav-link {
        color: #aab4c8 !important;
        text-decoration: none !important;
        font-size: 13px;
        font-weight: 500;
        padding: 0 18px;
        display: flex;
        align-items: center;
        border-bottom: 3px solid transparent;
        white-space: nowrap;
    }
    .nav-link:hover { color: white !important; background: rgba(255,255,255,0.06); }
    .nav-link.active { color: white !important; border-bottom: 3px solid #4a90d9; font-weight: 700; }

    /* Compact filter row */
    div[data-testid="stMultiSelect"] label p {
        font-size: 12px !important;
        font-weight: 600;
        color: #555 !important;
    }
    div[data-testid="stButton"] button {
        height: 38px;
        font-size: 13px;
        border-radius: 6px;
        padding: 0 12px;
    }
</style>
""", unsafe_allow_html=True)

params = st.query_params
page = params.get("page", "mbm")

def nav_link(label, key, icon):
    cls = "nav-link active" if page == key else "nav-link"
    return f'<a class="{cls}" href="?page={key}">{icon} {label}</a>'

st.markdown(f"""
<div class="navbar">
    <a class="navbar-brand" href="?page=mbm">🌍 MBM<span>Market-Based Mechanisms</span></a>
    <div class="nav-links">
        {nav_link("MBM", "mbm", "🗺️")}
        {nav_link("ETS", "ets", "")}
        {nav_link("CBAM", "cbam", "")}
    </div>
</div>
""", unsafe_allow_html=True)

# ── Constants ──────────────────────────────────────────────────
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

MARKER_STYLES = {
    "CBAM":           {"symbol": "square",      "color": "#4a90d9", "size": 4},
    "Tax Incentives": {"symbol": "diamond",     "color": "#9b59b6", "size": 5},
    "Fuel Mandates":  {"symbol": "triangle-up", "color": "#e07b00", "size": 5},
    "Feebates":       {"symbol": "circle",      "color": "#e63946", "size": 4},
    "VCM project":    {"symbol": "asterisk",    "color": "#2a9d8f", "size": 7},
    "AMC":            {"symbol": "cross",       "color": "#5b9bd5", "size": 5},
}

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
    "CBAM":           ( 0.0,  0.0),
    "Tax Incentives": ( 0.0,  1.5),
    "Fuel Mandates":  ( 0.0, -1.5),
    "Feebates":       ( 1.5,  0.0),
    "VCM project":    (-1.5,  0.0),
    "AMC":            ( 1.5,  1.5),
}

CENTROIDS = {
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
    "Côte d'Ivoire": "CIV", "Cote d'Ivoire": "CIV",
    "São Tomé and Príncipe": "STP",
    "Democratic Republic of the Congo": "COD", "Republic of the Congo": "COG",
    "United States": "USA", "Russia": "RUS", "Iran": "IRN", "Syria": "SYR",
    "Vatican City": "VAT", "North Korea": "PRK", "South Korea": "KOR",
    "Laos": "LAO", "Timor-Leste": "TLS", "Brunei Darussalam": "BRN",
    "Bolivia": "BOL", "Venezuela": "VEN", "Tanzania": "TZA",
    "Micronesia": "FSM", "Palestine": "PSE", "Taiwan": "TWN",
    "Vietnam": "VNM", "Moldova": "MDA",
}

# ── Helpers ────────────────────────────────────────────────────
def to_iso3(name: str):
    name = (name or "").strip()
    if name in MANUAL_ISO3:
        return MANUAL_ISO3[name]
    try:
        return pycountry.countries.lookup(name).alpha_3
    except Exception:
        return None

@st.cache_data
def load_raw():
    df = pd.read_excel(FILE_PATH)
    df.columns = [str(c).strip() for c in df.columns]
    return df

@st.cache_data
def load_detail_data():
    xl = pd.ExcelFile(FILE_PATH)

    # ETS — name + price per jurisdiction
    ets = xl.parse("1.a ETS")
    ets = ets[["Instrument name", "Jurisdiction", "Price rate ", "Start date", "Sector coverage"]].copy()
    ets.columns = ["name", "country", "price", "start_date", "sectors"]
    ets["country"] = ets["country"].str.strip()

    # Carbon Tax — name + price per jurisdiction
    ctx = xl.parse("1.b Carbon Tax")
    ctx = ctx[["Instrument name", "Jurisdiction", "Main price rate", "Start date", "Sectoral coverage"]].copy()
    ctx.columns = ["name", "country", "price", "start_date", "sectors"]
    ctx["country"] = ctx["country"].str.strip()

    # Fuel Mandates
    fm = xl.parse("Fuel Mandates")
    fm = fm[["Country", "Fuel mandate (type)", "% / fuel", "Short description + main source"]].copy()
    fm.columns = ["country", "mandate_type", "pct_fuel", "description"]
    fm = fm[fm["mandate_type"].notna()]
    fm["country"] = fm["country"].str.strip()

    # VCM
    vcm = xl.parse("8. VCM")
    vcm = vcm[["Country", "Projects", "Credits"]].copy()
    vcm.columns = ["country", "projects", "credits"]
    vcm["country"] = vcm["country"].str.strip()

    # Feebates
    fb = xl.parse("Sheet23")
    fb = fb[["Country", "Feebate policy", "Policy type", "Status"]].copy()
    fb.columns = ["country", "policy_name", "policy_type", "status"]
    fb = fb[fb["policy_name"].notna() & (fb["policy_name"] != "None identified")]
    fb["country"] = fb["country"].str.strip()

    # Tax Incentives
    ti = xl.parse("6. Tax Incentives", header=1)
    ti = ti[["Country", "Tax benefit – Acquisition", "Tax benefit – Ownership",
             "Incentive – Vehicle purchase", "Incentive – Infrastructure"]].copy()
    ti = ti[ti["Country"].notna()]
    ti["country"] = ti["Country"].str.strip()

    # AMC
    amc = xl.parse("AMC")
    amc = amc[["Country", "Product / Technology", "Sector", "Climate AMC Status"]].copy()
    amc.columns = ["country", "product", "sector", "status"]
    amc = amc[amc["country"].notna()]
    amc["country"] = amc["country"].str.strip()

    # Dashboard fallback for Fuel Mandates (for countries not in detail sheet)
    dash = xl.parse("Dashboard")
    dash.columns = [str(c).strip() for c in dash.columns]
    dash = dash[dash["Country"].notna()]
    fm_col = "4. Fuel Mandates"
    dashboard_fm = {}
    if fm_col in dash.columns:
        for _, r in dash.iterrows():
            if pd.notna(r.get(fm_col)):
                dashboard_fm[str(r["Country"]).strip()] = r[fm_col]

    return {"ets": ets, "ctx": ctx, "fm": fm, "vcm": vcm,
            "feebates": fb, "tax_incentives": ti, "amc": amc,
            "dashboard_fm": dashboard_fm}


def render_mechanism_details(country, mechs):
    """Render detail card below the main country card."""
    details = load_detail_data()

    # Color-coded pill tag
    def pill(label, val, bg, tc):
        return f'<span style="background:{bg};color:{tc};padding:4px 10px;border-radius:4px;font-size:11px;font-weight:600;margin-right:6px;margin-bottom:4px;display:inline-block;white-space:nowrap;">{label}: <b>{val}</b></span>'

    # Section card wrapper
    def card(border_color, bg, content):
        return f'<div style="border-left:4px solid {border_color};padding:14px 16px;margin-bottom:10px;background:{bg};border-radius:0 8px 8px 0;">{content}</div>'

    # Section title (no emoji)
    def title(label, color):
        return f'<div style="font-size:14px;font-weight:800;color:{color};margin-bottom:8px;letter-spacing:0.2px;">{label}</div>'

    # Subdued label row
    def meta(text):
        return f'<div style="font-size:11px;color:#888;margin-top:5px;">{text}</div>'

    rows = ""

    # ── ETS ──
    if "ETS" in mechs:
        ets_rows = details["ets"][details["ets"]["country"] == country]
        if not ets_rows.empty:
            if len(ets_rows) == 1:
                r = ets_rows.iloc[0]
                price = str(r["price"]).strip() if pd.notna(r["price"]) else "N/A"
                start = int(r["start_date"]) if pd.notna(r["start_date"]) else "—"
                sectors = (str(r["sectors"])[:90] + "…") if pd.notna(r["sectors"]) and len(str(r["sectors"])) > 90 else (str(r["sectors"]) if pd.notna(r["sectors"]) else "—")
                content = (title(f'ETS — {r["name"]}', "#457b9d")
                    + pill("Price", price, "#ddeef8", "#1a3a4a")
                    + pill("Est.", start, "#e8f0fe", "#1a2a5e")
                    + meta(f"Sectors: {sectors}"))
                rows += card("#457b9d", "#f7fafd", content)
            else:
                items = "".join(
                    f'<div style="display:flex;justify-content:space-between;align-items:center;padding:5px 0;border-bottom:1px solid #dde8f0;">'
                    f'<span style="font-size:12px;color:#1a1a2e;font-weight:600;">{r["name"]}</span>'
                    f'<span style="font-size:11px;color:#888;">{int(r["start_date"]) if pd.notna(r["start_date"]) else "—"} &nbsp;·&nbsp; '
                    f'<b style="color:#457b9d;">{str(r["price"]).strip() if pd.notna(r["price"]) else "N/A"}</b></span></div>'
                    for _, r in ets_rows.iterrows()
                )
                content = title(f"ETS — {len(ets_rows)} schemes", "#457b9d") + items
                rows += card("#457b9d", "#f7fafd", content)

    # ── Carbon Tax ──
    if "Carbon Tax" in mechs:
        ctx_rows = details["ctx"][details["ctx"]["country"] == country]
        if not ctx_rows.empty:
            if len(ctx_rows) == 1:
                r = ctx_rows.iloc[0]
                price = str(r["price"]).strip() if pd.notna(r["price"]) else "N/A"
                start = int(r["start_date"]) if pd.notna(r["start_date"]) else "—"
                sectors = (str(r["sectors"])[:90] + "…") if pd.notna(r["sectors"]) and len(str(r["sectors"])) > 90 else (str(r["sectors"]) if pd.notna(r["sectors"]) else "—")
                content = (title(f'Carbon Tax — {r["name"]}', "#5a8a3a")
                    + pill("Price", price, "#e0f0d8", "#2a4a1a")
                    + pill("Est.", start, "#e8f0fe", "#1a2a5e")
                    + meta(f"Sectors: {sectors}"))
                rows += card("#5a8a3a", "#f7fdf4", content)
            else:
                items = "".join(
                    f'<div style="display:flex;justify-content:space-between;align-items:center;padding:5px 0;border-bottom:1px solid #d8ecd0;">'
                    f'<span style="font-size:12px;color:#1a1a2e;font-weight:600;">{r["name"]}</span>'
                    f'<span style="font-size:11px;color:#888;">{int(r["start_date"]) if pd.notna(r["start_date"]) else "—"} &nbsp;·&nbsp; '
                    f'<b style="color:#5a8a3a;">{str(r["price"]).strip() if pd.notna(r["price"]) else "N/A"}</b></span></div>'
                    for _, r in ctx_rows.iterrows()
                )
                content = title(f"Carbon Tax — {len(ctx_rows)} schemes", "#5a8a3a") + items
                rows += card("#5a8a3a", "#f7fdf4", content)

    # ── Fuel Mandates ──
    if "Fuel Mandates" in mechs:
        fm_rows = details["fm"][details["fm"]["country"] == country]
        if not fm_rows.empty:
            for _, r in fm_rows.iterrows():
                desc = str(r["description"]) if pd.notna(r["description"]) else "—"
                pct = str(r["pct_fuel"]) if pd.notna(r["pct_fuel"]) else "—"
                content = (title(f'Fuel Mandate — {r["mandate_type"]}', "#e07b00")
                    + f'<div style="background:#fde8c8;color:#5a2a00;padding:6px 10px;border-radius:4px;font-size:11px;font-weight:600;margin-bottom:6px;white-space:normal;word-break:break-word;">Requirement: {pct}</div>'
                    + meta(desc))
                rows += card("#e07b00", "#fff8f0", content)
        else:
            dashboard_val = details.get("dashboard_fm", {}).get(country, None)
            if dashboard_val:
                content = title("Fuel Mandate", "#e07b00") + meta(str(dashboard_val))
                rows += card("#e07b00", "#fff8f0", content)

    # ── VCM ──
    if "VCM project" in mechs:
        vcm_rows = details["vcm"][details["vcm"]["country"] == country]
        if not vcm_rows.empty:
            r = vcm_rows.iloc[0]
            credits = f"{int(r['credits']):,}" if pd.notna(r['credits']) and str(r['credits']).replace('-','').strip().isdigit() else str(r['credits'])
            content = (title("Voluntary Carbon Market (VCM)", "#2a9d8f")
                + pill("Projects", int(r['projects']), "#c8ede9", "#1a4a45")
                + pill("Credits issued", credits, "#c8ede9", "#1a4a45"))
            rows += card("#2a9d8f", "#f0faf9", content)

    # ── Feebates ──
    if "Feebates" in mechs:
        fb_rows = details["feebates"][details["feebates"]["country"] == country]
        for _, r in fb_rows.iterrows():
            content = (title(f'Feebate — {r["policy_name"]}', "#e63946")
                + pill("Type", r['policy_type'], "#fdd8da", "#5a0a0e")
                + pill("Status", r['status'], "#fdd8da", "#5a0a0e"))
            rows += card("#e63946", "#fff0f1", content)

    # ── Tax Incentives ──
    if "Tax Incentives" in mechs:
        ti_rows = details["tax_incentives"][details["tax_incentives"]["country"] == country]
        if not ti_rows.empty:
            r = ti_rows.iloc[0]
            types = []
            if pd.notna(r.get("Tax benefit – Acquisition")): types.append("Acquisition")
            if pd.notna(r.get("Tax benefit – Ownership")): types.append("Ownership")
            if pd.notna(r.get("Incentive – Vehicle purchase")): types.append("Vehicle purchase")
            if pd.notna(r.get("Incentive – Infrastructure")): types.append("Infrastructure")
            pills = "".join(pill(t, "✓", "#ead8f5", "#3a0a5a") for t in types) if types else pill("Status", "Present", "#ead8f5", "#3a0a5a")
            content = title("Tax Incentives", "#9b59b6") + f'<div style="margin-top:2px;">{pills}</div>'
            rows += card("#9b59b6", "#faf0ff", content)

    # ── AMC ──
    if "AMC" in mechs:
        amc_rows = details["amc"][details["amc"]["country"] == country]
        for _, r in amc_rows.iterrows():
            content = (title(f'Advance Market Commitment — {r["product"]}', "#5b9bd5")
                + pill("Sector", r['sector'], "#d8e8f5", "#0a2a5a"))
            rows += card("#5b9bd5", "#f0f6ff", content)

    if rows:
        html = '<div style="margin-top:12px;">'
        html += '<div style="font-size:11px;font-weight:700;color:#999;margin-bottom:10px;text-transform:uppercase;letter-spacing:1.5px;">Mechanism Details</div>'
        html += rows
        html += '</div>'
        st.markdown(html, unsafe_allow_html=True)


def tidy_long(df_raw):
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
    long.loc[mask_vcm, "vcm_projects"] = pd.to_numeric(long.loc[mask_vcm, "mechanism_detail"], errors="coerce")
    long = long[~((~mask_vcm) & (long["mechanism_detail"] == "0"))]
    return df, long

def get_carbon_pricing_type(mechs: set) -> str:
    has_ets = "ETS" in mechs
    has_tax = "Carbon Tax" in mechs
    if has_ets and has_tax: return "ETS + Carbon Tax"
    elif has_ets: return "ETS"
    elif has_tax: return "Carbon Tax"
    return "No Carbon Pricing"

def render_country_card(country, region, long_df):
    CP_DISPLAY = {
        "ETS + Carbon Tax": "ETS and Carbon Tax",
        "Carbon Tax": "Carbon Tax",
        "ETS": "ETS",
        "No Carbon Pricing": "No Carbon Pricing",
    }
    cf = long_df[long_df["Country"] == country]
    mechs = sorted(cf["mechanism_type"].unique()) if len(cf) else []
    cp_type = get_carbon_pricing_type(set(mechs))
    cp_color = CARBON_PRICING_COLORS[cp_type]
    n = len(mechs)
    # Remove CP mechanisms from the detail boxes to avoid duplication
    cp_mechs = {"ETS", "Carbon Tax"}
    other_mechs = [m for m in mechs if m not in cp_mechs]
    n_other = len(other_mechs)
    boxes = ""
    for m in other_mechs:
        bg = MECH_BOX_COLORS.get(m, "#888")
        tc = "white" if bg not in ("#90be6d", "#f0f0f0") else "#333"
        boxes += f'<div style="background:{bg};color:{tc};padding:5px 12px;border-radius:6px;font-weight:700;font-size:12px;border:1.5px solid #222;white-space:nowrap;">{m}</div>'
    st.markdown(f"""
    <div style="background:white;border:2px solid #e0e0e0;border-radius:12px;padding:20px 16px;box-shadow:0 2px 12px rgba(0,0,0,0.06);margin-bottom:12px;">
        <div style="font-size:22px;font-weight:800;color:#1a1a2e;letter-spacing:1px;margin-bottom:4px;">{country.upper()}</div>
        <div style="font-size:12px;color:#888;margin-bottom:14px;">{region}</div>
        <div style="display:flex;gap:8px;margin-bottom:14px;flex-wrap:wrap;align-items:center;">
            <div style="background:{cp_color};color:{'#1a1a2e' if cp_type == 'No Carbon Pricing' else 'white'};padding:5px 14px;border-radius:6px;font-weight:700;font-size:12px;border:1.5px solid #222;">{CP_DISPLAY.get(cp_type, cp_type)}</div>
        </div>
        {f'<div style="display:flex;gap:6px;flex-wrap:wrap;"><div style="font-size:11px;color:#aaa;width:100%;margin-bottom:4px;">Other mechanisms:</div>{boxes}</div>' if boxes else ''}
    </div>
    """, unsafe_allow_html=True)
    if n == 0:
        st.info("No recorded mechanisms for this country.")

# ── Pages ──────────────────────────────────────────────────────
def page_mbm():
    raw = load_raw()
    wide, long = tidy_long(raw)

    vcm_sum_all = long.loc[long["mechanism_type"] == "VCM project", "vcm_projects"].sum(min_count=1)
    vcm_total = 0 if pd.isna(vcm_sum_all) else int(vcm_sum_all)
    n_countries = int(wide["Country"].nunique())
    n_mechs = int(long["mechanism_type"].nunique())

    cp_wide = wide.copy()
    cp_wide["cp_type"] = cp_wide["Country"].apply(
        lambda c: get_carbon_pricing_type(set(long[long["Country"] == c]["mechanism_type"].tolist()))
    )
    n_ets = int((cp_wide["cp_type"] == "ETS").sum())
    n_ctx = int((cp_wide["cp_type"] == "Carbon Tax").sum())
    n_both = int((cp_wide["cp_type"] == "ETS + Carbon Tax").sum())

    st.markdown(f"""
    <div style="
        text-align:center;
        padding: 100px 40px 80px 40px;
        min-height: 80vh;
        display:flex; flex-direction:column; justify-content:center; align-items:center;
        background-image:
            linear-gradient(rgba(255,255,255,0.6), rgba(255,255,255,0.6)),
            url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 1000 500'%3E%3Crect width='1000' height='500' fill='%23dce8f5'/%3E%3C!-- continents simplified --%3E%3C!-- North America --%3E%3Cpath d='M80 80 L200 70 L230 120 L220 200 L180 250 L140 260 L100 230 L70 180 Z' fill='%23b0c8e0' stroke='%23888' stroke-width='1'/%3E%3C!-- South America --%3E%3Cpath d='M150 270 L210 260 L240 310 L230 400 L190 440 L150 420 L130 370 L140 310 Z' fill='%23b0c8e0' stroke='%23888' stroke-width='1'/%3E%3C!-- Europe --%3E%3Cpath d='M430 60 L510 55 L520 100 L490 130 L440 125 L420 100 Z' fill='%23b0c8e0' stroke='%23888' stroke-width='1'/%3E%3C!-- Africa --%3E%3Cpath d='M440 140 L520 130 L540 200 L530 320 L490 370 L450 360 L420 290 L420 200 Z' fill='%23b0c8e0' stroke='%23888' stroke-width='1'/%3E%3C!-- Asia --%3E%3Cpath d='M520 50 L800 60 L830 100 L820 200 L750 230 L680 220 L600 200 L540 160 L510 110 Z' fill='%23b0c8e0' stroke='%23888' stroke-width='1'/%3E%3C!-- Australia --%3E%3Cpath d='M750 300 L850 290 L870 360 L830 400 L760 390 L730 340 Z' fill='%23b0c8e0' stroke='%23888' stroke-width='1'/%3E%3C/svg%3E");
        background-size: cover;
        background-position: center;
        background-repeat: no-repeat;
        border-radius: 12px;
        margin-bottom: 0;
    ">
        <div style="font-size:72px; font-weight:900; color:#1a1a2e; line-height:1.05; letter-spacing:-2px; margin-bottom:72px; white-space:nowrap;">
            Global Market-Based Mechanisms Dashboard
        </div>
        <div style="font-size:18px; color:#666; max-width:900px; margin:0 auto 40px auto; line-height:1.8; font-weight:400;">
            A market-based mechanism (MBM) is a climate policy instrument that uses market principles<br>to create economic incentives for reducing greenhouse gas emissions by allowing the trading or valuation of emission reductions or emission rights.
        </div>
        <div style="display:flex; justify-content:center; gap:48px; flex-wrap:wrap; margin-bottom:48px; align-items:center;">
            <div>
                <div style="font-size:56px; font-weight:900; color:#1a1a2e; line-height:1;">{n_countries}</div>
                <div style="font-size:11px; color:#999; font-weight:700; text-transform:uppercase; letter-spacing:2px; margin-top:6px;">Countries Covered</div>
            </div>
            <div style="width:1px; height:60px; background:#e0e0e0;"></div>
            <div>
                <div style="font-size:56px; font-weight:900; color:#1a1a2e; line-height:1;">{n_mechs}</div>
                <div style="font-size:11px; color:#999; font-weight:700; text-transform:uppercase; letter-spacing:2px; margin-top:6px;">Mechanism Types</div>
            </div>
            <div style="width:1px; height:60px; background:#e0e0e0;"></div>
            <div>
                <div style="font-size:56px; font-weight:900; color:#457b9d; line-height:1;">{n_ets}</div>
                <div style="font-size:11px; color:#999; font-weight:700; text-transform:uppercase; letter-spacing:2px; margin-top:6px;">Countries with ETS</div>
            </div>
            <div style="width:1px; height:60px; background:#e0e0e0;"></div>
            <div>
                <div style="font-size:56px; font-weight:900; color:#5a8a3a; line-height:1;">{n_ctx}</div>
                <div style="font-size:11px; color:#999; font-weight:700; text-transform:uppercase; letter-spacing:2px; margin-top:6px;">Countries with Carbon Tax</div>
            </div>
            <div style="width:1px; height:60px; background:#e0e0e0;"></div>
            <div>
                <div style="font-size:56px; font-weight:900; color:#c97a3a; line-height:1;">{n_both}</div>
                <div style="font-size:11px; color:#999; font-weight:700; text-transform:uppercase; letter-spacing:2px; margin-top:6px;">ETS and Carbon Tax</div>
            </div>
        </div>
        <a onclick="
            var el = document.getElementById('map-section');
            var container = window.parent.document.querySelector('.main');
            if (!container) container = window.parent.document.querySelector('[data-testid=stAppViewContainer]');
            if (container) {{
                var y = el.getBoundingClientRect().top + container.scrollTop - 120;
                container.scrollTo({{top: y, behavior: 'smooth'}});
            }} else {{
                window.parent.scrollTo({{top: el.getBoundingClientRect().top + window.parent.scrollY - 120, behavior: 'smooth'}});
            }}
            return false;"
           href="#map-section"
           style="
               display:inline-flex; align-items:center; gap:10px;
               background:#1a1a2e; color:white;
               padding:16px 40px; border-radius:999px;
               font-size:16px; font-weight:700;
               text-decoration:none; letter-spacing:0.5px;
               box-shadow: 0 6px 24px rgba(26,26,46,0.3);
           "
           onmouseover="this.style.background='#2d2d50'"
           onmouseout="this.style.background='#1a1a2e'">
            ▶ &nbsp;Get Started
        </a>
        <div style="margin-top:40px; padding-top:24px; border-top:1px solid #e8e8e8; font-size:12px; color:#aaa; max-width:860px; line-height:1.8; text-align:center;">
            This dashboard is a product of the <span style="color:#777; font-weight:600;">Market-based Interventions for Deep Decarbonisation (MIDD) Lab</span>,<br>
            based at the <span style="color:#777; font-weight:600;">Grantham Institute – Climate Change and the Environment</span> at <span style="color:#777; font-weight:600;">Imperial College London</span>, and led by <span style="color:#777; font-weight:600;">Dr Gbemi Oluleye</span>.
        </div>
    </div>
    <hr style="border:none; border-top:1px solid #e0e0e0; margin:0 0 24px 0;">
    """, unsafe_allow_html=True)

    # Reset handler — pakai counter untuk force re-render widget dengan key baru
    if "reset_counter" not in st.session_state:
        st.session_state["reset_counter"] = 0

    st.markdown("""
    <div id="map-section" style="margin-bottom:4px;">
        <div style="font-size:36px; font-weight:900; color:#1a1a2e; margin-bottom:4px;">Market-Based Mechanism Map</div>
        <div style="font-size:16px; font-weight:800; color:#1a1a2e; margin-bottom:2px;">Explore the Map</div>
        <div style="font-size:12px; color:#999;">Filter countries by region, mechanism type, or search by name.</div>
    </div>
    """, unsafe_allow_html=True)

    rc = st.session_state["reset_counter"]
    fc1, fc2, fc3, fc4 = st.columns([2, 2, 2, 0.7])
    with fc1:
        region_sel = st.multiselect("Region", sorted(long["Region"].dropna().unique()), key=f"f_region_{rc}", placeholder="All regions")
    with fc2:
        type_sel = st.multiselect("Mechanism type", sorted(long["mechanism_type"].dropna().unique()), key=f"f_type_{rc}", placeholder="All types")
    with fc3:
        country_sel = st.multiselect("Country", sorted(long["Country"].dropna().unique()), key=f"f_country_{rc}", placeholder="All countries")
    with fc4:
        st.markdown('<div style="height:28px"></div>', unsafe_allow_html=True)
        if st.button("↺ Reset", use_container_width=True, key="reset_btn"):
            st.session_state["reset_counter"] += 1
            st.rerun()

    f = long.copy()
    if region_sel:  f = f[f["Region"].isin(region_sel)]
    if type_sel:    f = f[f["mechanism_type"].isin(type_sel)]
    if country_sel: f = f[f["Country"].isin(country_sel)]

    wide_view = wide.copy()
    if region_sel:  wide_view = wide_view[wide_view["Region"].isin(region_sel)]
    if country_sel: wide_view = wide_view[wide_view["Country"].isin(country_sel)]
    # Map
    country_mechs_map = f.groupby("Country")["mechanism_type"].apply(set).to_dict()
    base = wide_view[["Country", "Region"]].drop_duplicates().copy()
    base["iso3"]        = base["Country"].apply(to_iso3)
    base["cp_type"]     = base["Country"].apply(lambda c: get_carbon_pricing_type(country_mechs_map.get(c, set())))
    base["n_mechs"]     = base["Country"].apply(lambda c: len(country_mechs_map.get(c, set())))
    base["region_val"]  = base["Region"].fillna("—")

    MECH_COLORS_HEX = {
        "Carbon Tax":     "#90be6d",
        "ETS":            "#457b9d",
        "Tax Incentives": "#9b59b6",
        "Fuel Mandates":  "#e07b00",
        "VCM project":    "#2a9d8f",
        "Feebates":       "#e63946",
        "CBAM":           "#4a90d9",
        "AMC":            "#5b9bd5",
    }
    # Match symbols to map markers
    MECH_SYMBOL_HOVER = {
        "CBAM":           "■",   # square
        "Tax Incentives": "◆",   # diamond
        "Fuel Mandates":  "▲",   # triangle-up
        "Feebates":       "●",   # circle
        "VCM project":    "✳",   # asterisk-like
        "AMC":            "✚",   # cross
    }

    CP_DISPLAY = {
        "ETS + Carbon Tax": "ETS and Carbon Tax",
        "Carbon Tax": "Carbon Tax",
        "ETS": "ETS",
        "No Carbon Pricing": "No Carbon Pricing",
    }

    def build_hover(c, cp, n, region):
        mechs = sorted(country_mechs_map.get(c, set()))
        cp_color = CARBON_PRICING_COLORS.get(cp, "#888")
        cp_label = CP_DISPLAY.get(cp, cp)
        other = [m for m in mechs if m not in {"ETS", "Carbon Tax"}]
        other_lines = "".join(
            f"<br><span style='color:{MECH_COLORS_HEX.get(m,'#888')}'><b>{MECH_SYMBOL_HOVER.get(m,'■')}</b></span> {m}"
            for m in other
        ) if other else "<br>  —"
        return (
            f"<b>{c}</b>"
            f"<br><span style='color:#999'>{region}</span>"
            f"<br>─────────────"
            f"<br><span style='color:{cp_color}'><b>■</b></span> <b>{cp_label}</b>"
            f"<br>─────────────"
            f"<br><b>Other mechanisms</b>"
            f"{other_lines}"
        )

    base["hover_text"] = base.apply(
        lambda r: build_hover(r["Country"], r["cp_type"], r["n_mechs"], r["region_val"]), axis=1
    )
    m_plot = base.dropna(subset=["iso3"]).copy()

    fig_map = go.Figure()

    for cp_type, color in CARBON_PRICING_COLORS.items():
        subset = m_plot[m_plot["cp_type"] == cp_type]
        if subset.empty: continue
        fig_map.add_trace(go.Choropleth(
            locations=subset["iso3"], z=[1]*len(subset),
            colorscale=[[0, color],[1, color]], showscale=False,
            hovertemplate="%{customdata[0]}<extra></extra>",
            customdata=subset[["hover_text","Country","n_mechs"]].values,
            name=cp_type, showlegend=False,
            marker_line_color="#111111", marker_line_width=1.5,
        ))

    for i, (cp_type, color) in enumerate(CARBON_PRICING_COLORS.items()):
        fig_map.add_trace(go.Scattergeo(
            lat=[None], lon=[None], mode="markers",
            marker=dict(symbol="square", color=color, size=10, line=dict(width=0.5, color="#000000")),
            name=cp_type, showlegend=True, legendgroup="cp",
            legendgrouptitle_text="Carbon Pricing" if i == 0 else "",
            hoverinfo="skip",
        ))

    OTHER_MECHS = ["CBAM", "Tax Incentives", "Fuel Mandates", "Feebates", "VCM project", "AMC"]
    for i, mech in enumerate(OTHER_MECHS):
        style = MARKER_STYLES[mech]
        dlat, dlon = MECH_OFFSETS[mech]
        rows = []
        for country in f[f["mechanism_type"] == mech]["Country"].unique():
            iso3 = to_iso3(country)
            if iso3 and iso3 in CENTROIDS:
                lat, lon = CENTROIDS[iso3]
                rows.append({"country": country, "lat": lat+dlat, "lon": lon+dlon})
        if not rows: continue
        df_m = pd.DataFrame(rows)

        if mech == "VCM project":
            fig_map.add_trace(go.Scattergeo(
                lat=df_m["lat"], lon=df_m["lon"], mode="markers",
                marker=dict(symbol="asterisk", color="#2a9d8f", size=5,
                            line=dict(width=1.2, color="#2a9d8f"), opacity=1.0),
                text=df_m["country"], hoverinfo="skip",
                name=mech, showlegend=True, legendgroup="other",
                legendgrouptitle_text="Other mechanisms" if i == 0 else "",
            ))
        else:
            fig_map.add_trace(go.Scattergeo(
                lat=df_m["lat"], lon=df_m["lon"], mode="markers",
                marker=dict(symbol=style["symbol"], color=style["color"], size=style["size"],
                            line=dict(width=0.5, color="#000000"), opacity=1.0),
                text=df_m["country"], hoverinfo="skip",
                name=mech, showlegend=True, legendgroup="other",
                legendgrouptitle_text="Other mechanisms" if i == 0 else "",
            ))

    fig_map.update_layout(
        height=520, margin=dict(l=0,r=0,t=0,b=0),
        paper_bgcolor="white", uirevision=str(region_sel)+str(type_sel)+str(country_sel), dragmode=False,
        hoverlabel=dict(
            bgcolor="white",
            bordercolor="#cccccc",
            font=dict(size=12, color="#1a1a2e", family="Inter, sans-serif"),
            align="left",
        ),
        geo=dict(
            projection_type="equirectangular",
            showframe=False,
            showcoastlines=True, coastlinecolor="#333333", coastlinewidth=1.5,
            showcountries=True, countrycolor="#333333", countrywidth=1.5,
            showland=True, landcolor="#f5f5f5",
            showocean=False, showlakes=False, bgcolor="white",
            lataxis=dict(range=[-60,85], showgrid=False),
            lonaxis=dict(range=[-180,180], showgrid=False),
            projection_scale=1,
        ),
        legend=dict(
            title="<b>Legend</b>",
            bgcolor="rgba(255,255,255,0.85)", bordercolor="rgba(0,0,0,0)", borderwidth=0,
            x=0.01, y=0.01, xanchor="left", yanchor="bottom",
            font=dict(size=10), tracegroupgap=3, itemsizing="constant",
        ),
        clickmode="event+select",
    )

    col_map, col_card = st.columns([3, 1.2])

    with col_map:
        clicked = st.plotly_chart(
            fig_map, use_container_width=True, key="map_qgis",
            on_select="rerun", selection_mode="points",
            config={"scrollZoom": False, "doubleClick": False, "displayModeBar": False},
        )

    with col_card:
        selected_country = None
        if clicked and clicked.get("selection") and clicked["selection"].get("points"):
            pts = clicked["selection"]["points"]
            if pts:
                pt = pts[0]
                cd = pt.get("customdata")
                txt = pt.get("text")
                if cd and isinstance(cd, (list, tuple)) and len(cd) > 1:
                    selected_country = cd[1]
                elif txt:
                    selected_country = txt

        # Auto-select if exactly 1 country in filter
        if not selected_country and len(country_sel) == 1:
            selected_country = country_sel[0]

        st.markdown("""
        <div style="margin-bottom:12px;">
            <div style="font-size:16px; font-weight:800; color:#1a1a2e; margin-bottom:4px;">Country Detail</div>
            <div style="font-size:12px; color:#999;">Select a country on the map to explore its market-based mechanisms and carbon pricing policies.</div>
        </div>
        """, unsafe_allow_html=True)

        if selected_country:
            region_val = wide[wide["Country"] == selected_country]["Region"].iloc[0] \
                if selected_country in wide["Country"].values else "—"
            render_country_card(selected_country, region_val, long)
            # Get mechs for detail card
            mechs_for_country = list(long[long["Country"] == selected_country]["mechanism_type"].unique())
            render_mechanism_details(selected_country, mechs_for_country)
        else:
            st.markdown("""
            <div style="
                background:#f8f9fa; border:2px dashed #ddd;
                border-radius:12px;
                text-align:center; color:#bbb;
                height:420px;
                display:flex; flex-direction:column;
                justify-content:center; align-items:center;
            ">
                <div style="font-size:36px; margin-bottom:12px;">🗺️</div>
                <div style="font-size:14px; font-weight:600; color:#999;">Click a country</div>
                <div style="font-size:12px; margin-top:6px; color:#bbb;">to see its mechanisms</div>
            </div>""", unsafe_allow_html=True)

    st.divider()
    st.markdown("""
    <div style="margin-bottom:20px;">
        <div style="font-size:28px;font-weight:900;color:#1a1a2e;margin-bottom:4px;">Summary</div>
        <div style="font-size:13px;color:#999;">Overview of market-based mechanism distribution across countries.</div>
    </div>
    """, unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Countries by mechanism type")
        by_type = f.groupby("mechanism_type")["Country"].nunique().reset_index(name="countries").sort_values("countries", ascending=False)
        bar_colors = [MECH_BOX_COLORS.get(m, "#888") for m in by_type["mechanism_type"]]

        fig_bar = go.Figure()

        # One bar per mechanism with legend entry
        for i, row in by_type.iterrows():
            color = MECH_BOX_COLORS.get(row["mechanism_type"], "#888")
            fig_bar.add_trace(go.Bar(
                x=[row["mechanism_type"]],
                y=[row["countries"]],
                name=row["mechanism_type"],
                marker_color=color,
                marker_line_color="#222", marker_line_width=1,
                text=[row["countries"]],
                textposition="outside",
                textfont=dict(size=12, color="#1a1a2e"),
                hovertemplate="%{x}: <b>%{y} countries</b><extra></extra>",
            ))

        fig_bar.update_layout(
            margin=dict(l=0, r=0, t=20, b=0),
            paper_bgcolor="white", plot_bgcolor="white",
            barmode="group",
            xaxis=dict(title="", tickfont=dict(size=11), showgrid=False),
            yaxis=dict(title="Countries", showgrid=True, gridcolor="#f0f0f0"),
            legend=dict(
                bgcolor="rgba(255,255,255,0.9)", bordercolor="#e0e0e0", borderwidth=1,
                font=dict(size=11), itemsizing="constant",
            ),
            hoverlabel=dict(bgcolor="white", bordercolor="#ccc", font=dict(size=12)),
        )
        st.plotly_chart(fig_bar, use_container_width=True, key="bar_type", config={"displayModeBar": False})
    with c2:
        st.subheader("Countries by Carbon Pricing type")
        cp_counts = m_plot["cp_type"].value_counts().reset_index()
        cp_counts.columns = ["type", "count"]
        st.plotly_chart(px.pie(cp_counts, names="type", values="count",
            color="type", color_discrete_map=CARBON_PRICING_COLORS),
            use_container_width=True, key="pie_cp")



def page_placeholder(title, icon):
    st.title(f"{icon} {title}")
    st.info("🚧 This page is under construction.")


@st.cache_data
def load_ets_data():
    import re
    xl = pd.ExcelFile(FILE_PATH)
    ets = xl.parse("1.a ETS")
    ets.columns = [str(c).strip() for c in ets.columns]
    col_map = {}
    for c in ets.columns:
        cl = c.lower()
        if "instrument name" in cl:           col_map[c] = "name"
        elif cl == "jurisdiction":            col_map[c] = "country"
        elif cl == "region":                  col_map[c] = "region"
        elif "start date" in cl:              col_map[c] = "start_date"
        elif "price rate" in cl:              col_map[c] = "price"
        elif "sector coverage" in cl:         col_map[c] = "sectors"
        elif "allocation method" in cl:       col_map[c] = "allocation"
        elif "government revenue" in cl:      col_map[c] = "revenue"
        elif "cap emission" in cl:            col_map[c] = "cap"
        elif cl == "description":             col_map[c] = "description"
        elif "additional information" in cl:  col_map[c] = "additional_info"
        elif cl in ("ghg", "ghg coverage"):  col_map[c] = "ghg"
        elif "share of" in cl:               col_map[c] = "share"
        elif "tighten" in cl:                col_map[c] = "tightening_rate"
        elif "threshold" in cl:              col_map[c] = "threshold"
        elif "revenue recycling" in cl:      col_map[c] = "revenue_recycling"
        elif "funding program" in cl:        col_map[c] = "funding_program"
        elif cl == "source":                  col_map[c] = "source"
    ets = ets.rename(columns=col_map)
    ets = ets[ets["country"].notna()].copy()
    def parse_price(p):
        if pd.isna(p): return None
        m = re.search(r"[\d]+\.?\d*", str(p))
        return float(m.group()) if m else None
    ets["price_num"] = ets["price"].apply(parse_price)
    ets["start_date"] = pd.to_numeric(ets["start_date"], errors="coerce")
    return ets


def page_ets():
    import re as _re
    ets = load_ets_data()

    n_schemes   = len(ets)
    n_countries = ets["country"].nunique()
    prices      = ets["price_num"].dropna()
    avg_price   = prices.mean()
    min_price   = prices.min()
    max_price_v = prices.max()
    total_rev   = "USD 69B+"

    # GHG types — normalised to canonical names
    GHG_NORM = {
        "co2": "CO₂", "co₂": "CO₂", "co₂e": "CO₂", "co₂ only": "CO₂",
        "including co₂": "CO₂", "carbon dioxide": "CO₂",
        "ch4": "CH₄", "methane": "CH₄", "ch4 and n2o": "CH₄",
        "n2o": "N₂O", "nitrous oxide": "N₂O",
        "hfcs": "HFCs", "hydrofluorocarbons": "HFCs",
        "pfcs": "PFCs", "perfluorocarbons": "PFCs",
        "sf6": "SF₆", "sulfur hexafluoride": "SF₆", "sf6 nf3": "SF₆",
        "nf3": "NF₃", "nitrogen trifluoride": "NF₃",
        "other fluorinated ghgs": "Other F-gases",
        "and other fluorinated ghgs": "Other F-gases",
    }
    ghg_set = set()
    for v in ets["ghg"].dropna():
        for g in str(v).split(","):
            g = g.strip().split("(")[0].strip().lower()
            canonical = GHG_NORM.get(g)
            if canonical:
                ghg_set.add(canonical)
    n_ghg = len(ghg_set)

    # Sector types — deduplicated canonical names
    SECTOR_NORM = {
        "power": "Power", "industry": "Industry", "industry and power": "Industry & Power",
        "buildings": "Buildings", "transport": "Transport", "aviation": "Aviation",
        "domestic aviation": "Aviation", "maritime": "Maritime",
        "agriculture and/or forestry fuel use": "Agriculture & Forestry",
        "forestry": "Agriculture & Forestry", "forestry fuel use": "Agriculture & Forestry",
        "waste": "Waste", "mining and extractives": "Mining & Extractives",
        "domestic": "Buildings",
        "iron and steel": "Industry", "chemical": "Industry", "paper": "Industry",
        "nonferrous metals": "Industry", "building materials": "Industry",
        "and ceramics": "Industry",
    }
    sec_set = set()
    for v in ets["sectors"].dropna():
        for s in str(v).split(","):
            s = s.strip().split(":")[0].strip().lower()
            if s and s not in ("nan",""):
                canonical = SECTOR_NORM.get(s, s.title())
                sec_set.add(canonical)
    n_sectors = len(sec_set)
    sectors_list = sorted(sec_set)

    # Funding programs — count real ones only
    INVALID_FP = {"-","—","nan","NaN","","not defined","under development by SEMARAT"}
    n_funding = 0
    fp_col = None
    for _c in ets.columns:
        if "funding" in str(_c).lower():
            fp_col = _c
            break
    if fp_col:
        n_funding = int(ets[fp_col].apply(lambda x: str(x).strip() not in INVALID_FP).sum())

    # ── Hero ──────────────────────────────────────────────────────
    def divv():
        return '<div style="width:1px;height:50px;background:#e0e0e0;align-self:center;"></div>'

    def stat(number, label, sub=None):
        sub_html = f'<div style="font-size:11px;color:#aaa;margin-top:5px;">{sub}</div>' if sub else ""
        return (
            f'<div style="text-align:center;">'
            f'<div style="font-size:44px;font-weight:900;color:#1a1a2e;line-height:1;white-space:nowrap;">{number}</div>'
            f'<div style="font-size:10px;color:#999;font-weight:700;text-transform:uppercase;letter-spacing:2px;margin-top:7px;white-space:nowrap;">{label}</div>'
            f'{sub_html}</div>'
        )

    st.markdown(f"""
    <div style="padding:56px 0 48px 0;border-bottom:1px solid #e8e8e8;margin-bottom:40px;text-align:center;">
        <div style="font-size:11px;font-weight:700;color:#457b9d;letter-spacing:3px;text-transform:uppercase;margin-bottom:32px;">Carbon Pricing Instrument</div>
        <div style="font-size:56px;font-weight:900;color:#1a1a2e;line-height:1.05;margin-bottom:40px;white-space:nowrap;">Emissions Trading Systems (ETS)</div>
        <div style="max-width:960px;margin:0 auto 56px auto;">
            <div style="font-size:16px;color:#666;line-height:1.9;">
                An Emissions Trading System is a market-based approach to controlling pollution by providing economic incentives for reducing emissions. Governments set a cap on total emissions and issue allowances — companies must hold allowances equal to their emissions and can trade them, creating a carbon price signal.
            </div>
        </div>
        <div style="display:flex;justify-content:center;align-items:center;gap:40px;flex-wrap:nowrap;margin-bottom:24px;">
            {stat(n_schemes, "Active Schemes")}
            {divv()}
            {stat(n_countries, "Jurisdictions")}
            {divv()}
            {stat(f"USD {avg_price:.0f}", "Avg. Carbon Price", sub=f"Range USD {min_price:.0f} – {max_price_v:.0f}")}
            {divv()}
            {stat(total_rev, "Revenue (2024)")}
            {divv()}
            {stat(n_ghg, "GHG Types Covered")}
            {divv()}
            {stat(n_sectors, "Sector Types")}
            {divv()}
            {stat(n_funding, "Funding Programs")}
        </div>
        <div style="font-size:13px;color:#888;line-height:2;max-width:960px;margin:0 auto 40px auto;">
            Today, <b>{n_schemes} active ETS schemes</b> operate across <b>{n_countries} jurisdictions</b> — <b>15 in North America</b>, <b>15 in East Asia &amp; Pacific</b>, <b>7 in Europe &amp; Central Asia</b>, and <b>1 in Latin America</b> — with carbon prices ranging from <b>USD {min_price:.0f} to USD {max_price_v:.0f}</b> (avg. <b>USD {avg_price:.0f}/tCO₂</b>). Sectors covered include <b>{", ".join(sectors_list[:-1])}, and {sectors_list[-1]}</b>. Regulated greenhouse gases include CO₂, CH₄, N₂O, HFCs, PFCs, SF₆, and NF₃.
        </div>
        <a onclick="
            var el = document.getElementById('ets-map-section');
            var container = window.parent.document.querySelector('.main');
            if (!container) container = window.parent.document.querySelector('[data-testid=stAppViewContainer]');
            if (container) {{
                var y = el.getBoundingClientRect().top + container.scrollTop - 120;
                container.scrollTo({{top: y, behavior: 'smooth'}});
            }} else {{
                window.parent.scrollTo({{top: el.getBoundingClientRect().top + window.parent.scrollY - 120, behavior: 'smooth'}});
            }}
            return false;"
           href="#ets-map-section"
           style="
               display:inline-flex; align-items:center; gap:10px;
               background:#1a1a2e; color:white;
               padding:16px 40px; border-radius:999px;
               font-size:16px; font-weight:700;
               text-decoration:none; letter-spacing:0.5px;
               box-shadow: 0 6px 24px rgba(26,26,46,0.3);
           "
           onmouseover="this.style.background='#2d2d50'"
           onmouseout="this.style.background='#1a1a2e'">
            ▶ &nbsp;Get Started
        </a>
    </div>
    """, unsafe_allow_html=True)

    # ── Map + Detail────────────────────────
    st.markdown('<div id="ets-map-section"></div>', unsafe_allow_html=True)
    st.markdown("""
    <div style="margin-bottom:16px;">
        <div style="font-size:28px;font-weight:900;color:#1a1a2e;margin-bottom:4px;">ETS Global Map</div>
        <div style="font-size:13px;color:#999;">Countries with active ETS schemes. Click a country to see details.</div>
    </div>
    """, unsafe_allow_html=True)

    # Filters
    regions_all = sorted(ets["region"].dropna().unique())
    countries_all = sorted(ets["country"].dropna().unique())

    if "ets_reset" not in st.session_state:
        st.session_state["ets_reset"] = 0
    rc = st.session_state["ets_reset"]

    fc1, fc2, fc3 = st.columns([2, 2, 0.7])
    with fc1:
        region_sel = st.multiselect("Region", regions_all, key=f"ets_region_{rc}", placeholder="All regions")
    with fc2:
        country_sel = st.multiselect("Country", countries_all, key=f"ets_country_{rc}", placeholder="All countries")
    with fc3:
        st.markdown('<div style="height:28px"></div>', unsafe_allow_html=True)
        if st.button("↺ Reset", key="ets_reset_btn", use_container_width=True):
            st.session_state["ets_reset"] += 1
            st.rerun()

    f_ets = ets.copy()
    if region_sel:  f_ets = f_ets[f_ets["region"].isin(region_sel)]
    if country_sel: f_ets = f_ets[f_ets["country"].isin(country_sel)]

    # ── All-schemes marker coords (one dot per scheme) ────────────
    SCHEME_COORDS = {
        # China
        "Beijing pilot ETS":    (39.90, 116.40),
        "Shanghai pilot ETS":   (31.23, 121.47),
        "Guangdong pilot ETS":  (23.13, 113.26),
        "Shenzhen pilot ETS":   (22.54, 114.05),
        "Tianjin pilot ETS":    (39.08, 117.20),
        "Chongqing pilot ETS":  (29.56, 106.55),
        "Hubei pilot ETS":      (30.60, 114.31),
        "Fujian pilot ETS":     (26.07, 119.30),
        "China national ETS":   (35.86, 104.20),
        # Canada
        "Alberta TIER":                                          (53.93, -116.58),
        "British Columbia OBPS":                                 (53.73, -127.65),
        "Canada federal OBPS":                                   (60.00,  -96.00),
        "New Brunswick OBPS":                                    (46.56,  -66.46),
        "Newfoundland and Labrador Performance Standards System": (53.13,  -57.66),
        "Nova Scotia OBPS":                                      (44.68,  -63.74),
        "Ontario EPS":                                           (50.00,  -86.00),
        "Quebec cap and trade":                                  (52.94,  -73.55),
        "Saskatchewan Output-Based Performance Standards Program":(54.00, -106.00),
        # USA
        "California cap and trade":                 (37.35, -119.00),
        "Colorado GHG crediting trading system":    (39.11, -105.36),
        "Massachusetts ETS":                        (42.40,  -71.38),
        "Oregon ETS":                               (44.00, -120.55),
        "Regional Greenhouse Gas Initiative":       (43.50,  -73.50),
        "Washington CCA":                           (47.40, -120.50),
        # Japan
        "Saitama ETS":          (35.86, 139.65),
        "Tokyo cap and trade":  (35.69, 139.69),
        # Single-country: centroid coordinates
        "Australia safeguard mechanism": (-25.27, 133.78),
        "Austria ETS":          (47.52,  14.55),
        "EU ETS":               (50.85,   4.35),
        "Germany ETS":          (51.17,  10.45),
        "Indonesia ETS":        (-0.79, 113.92),
        "Kazakhstan ETS":       (48.02,  66.92),
        "Korea ETS":            (36.50, 127.98),
        "Mexico ETS":           (23.63, -102.55),
        "Montenegro ETS":       (42.71,  19.37),
        "New Zealand ETS":      (-40.90, 174.89),
        "Switzerland ETS":      (46.82,   8.23),
        "UK ETS":               (55.38,  -3.44),
    }

    def shorten(name):
        return (name.replace(" pilot ETS","").replace(" cap and trade","")
                    .replace(" OBPS","").replace(" ETS","").replace(" CCA","")
                    .replace(" TIER","").replace(" EPS","")
                    .replace(" GHG crediting trading system","")
                    .replace(" Output-Based Performance Standards Program","")
                    .replace(" Performance Standards System","")
                    .replace(" safeguard mechanism",""))

    # ── Build map: choropleth by avg price + orange dots per scheme ─
    country_ets_map   = f_ets.groupby("country")["name"].apply(list).to_dict()
    country_price_map = f_ets.groupby("country")["price_num"].mean().to_dict()

    map_rows = []
    for country, schemes in country_ets_map.items():
        iso3 = to_iso3(country)
        if iso3:
            avg_p = country_price_map.get(country)
            map_rows.append({
                "iso3": iso3, "country": country,
                "avg_price": avg_p if pd.notna(avg_p) else None,
                "n_schemes": len(schemes),
                "schemes_str": "<br>".join(f"  · {s}" for s in schemes),
            })
    map_df = pd.DataFrame(map_rows) if map_rows else pd.DataFrame()

    fig_ets_map = go.Figure()

    # ── Choropleth: same color scheme as MBM map ─────────────────
    # ETS-only countries = #457b9d (blue), also has carbon tax = #f4a261 (orange)
    # Load carbon tax sheet to check overlap
    try:
        ctx_sheet = pd.read_excel(DATA_PATH, sheet_name="1.b Carbon Tax")
        ctx_sheet.columns = [str(c).strip() for c in ctx_sheet.columns]
        ctx_col = next((c for c in ctx_sheet.columns if "jurisdiction" in c.lower()), ctx_sheet.columns[0])
        ctx_countries = set(ctx_sheet[ctx_col].dropna().astype(str).str.strip().tolist())
    except:
        ctx_countries = set()

    ets_countries = set(f_ets["country"].unique())

    if not map_df.empty:
        rows_both    = map_df[map_df["country"].apply(lambda c: c in ets_countries and c in ctx_countries)]
        rows_ets     = map_df[map_df["country"].apply(lambda c: c in ets_countries and c not in ctx_countries)]

        def add_choro(df, color, label):
            if df.empty: return
            fig_ets_map.add_trace(go.Choropleth(
                locations=df["iso3"],
                z=[1]*len(df),
                colorscale=[[0,color],[1,color]],
                showscale=False,
                hovertemplate=(
                    "<b>%{customdata[0]}</b><br>"
                    f"<span style='color:{color}'>■</span> {label}<br>"
                    "%{customdata[1]} scheme(s)<br>"
                    "─────────────<br>"
                    "%{customdata[2]}<extra></extra>"
                ),
                customdata=df[["country","n_schemes","schemes_str"]].values,
                marker_line_color="#555", marker_line_width=0.8,
            ))

        add_choro(rows_both, "#f4a261", "ETS + Carbon Tax")
        add_choro(rows_ets,  "#457b9d", "ETS")

    # ── One dot per country (representative scheme) ──────────────
    COUNTRY_CENTROIDS = {
        "Australia":      (-25.27,  133.78),
        "Austria":        ( 47.52,   14.55),
        "Canada":         ( 60.00,  -96.00),
        "China":          ( 35.86,  104.20),
        "European Union": ( 50.85,    4.35),
        "Germany":        ( 51.17,   10.45),
        "Indonesia":      ( -0.79,  113.92),
        "Japan":          ( 36.20,  138.25),
        "Kazakhstan":     ( 48.02,   66.92),
        "Korea, Rep.":    ( 36.50,  127.98),
        "Mexico":         ( 23.63, -102.55),
        "Montenegro":     ( 42.71,   19.37),
        "New Zealand":    (-40.90,  174.89),
        "Switzerland":    ( 46.82,    8.23),
        "United Kingdom": ( 55.38,   -3.44),
        "United States":  ( 39.50,  -98.35),
    }

    # Pick representative scheme per country (national/federal first)
    REPR_SCHEME = {}
    for country, schemes in f_ets.groupby("country")["name"].apply(list).items():
        national = [s for s in schemes if any(w in s.lower() for w in ["national","federal","safeguard"])]
        REPR_SCHEME[country] = national[0] if national else schemes[0]

    DOT_COLORS = [
        "#e07b00","#2a9d8f","#e63946","#9b59b6",
        "#4a90d9","#f4a261","#5a8a3a","#d63031",
        "#00b894","#6c5ce7","#457b9d","#c97a3a",
        "#fdcb6e","#0984e3","#a29bfe","#fd79a8",
    ]
    country_list = sorted(COUNTRY_CENTROIDS.keys())
    country_color = {c: DOT_COLORS[i % len(DOT_COLORS)] for i, c in enumerate(country_list)}

    dot_lons, dot_lats, dot_colors, dot_hovers, dot_custom = [], [], [], [], []
    for country, coord in COUNTRY_CENTROIDS.items():
        country_schemes = f_ets[f_ets["country"] == country]
        if country_schemes.empty:
            continue
        repr_name = REPR_SCHEME.get(country, country_schemes["name"].iloc[0])
        repr_row  = f_ets[f_ets["name"] == repr_name]
        if repr_row.empty:
            repr_row = country_schemes.iloc[[0]]
        row = repr_row.iloc[0]
        n   = len(country_schemes)
        price_v = row.get("price", "N/A")
        year_v  = int(row["start_date"]) if pd.notna(row.get("start_date")) else "N/A"
        schemes_list = "<br>".join(f"  · {s}" for s in country_schemes["name"].tolist())
        hover = (f"<b>{country}</b><br>{n} scheme(s)<br>"
                 f"Repr: {repr_name}<br>Est. {year_v} · {price_v}<br>"
                 f"──────────<br>{schemes_list}<extra></extra>")
        dot_lons.append(coord[1])
        dot_lats.append(coord[0])
        dot_colors.append(country_color[country])
        dot_hovers.append(hover)
        dot_custom.append([country])  # click → show country detail

    if dot_lons:
        fig_ets_map.add_trace(go.Scattergeo(
            lon=dot_lons, lat=dot_lats,
            mode="markers",
            marker=dict(
                size=11,
                color=dot_colors,
                symbol="diamond",
                line=dict(width=1.5, color="white"),
            ),
            hovertemplate=dot_hovers,
            customdata=dot_custom,
            showlegend=False,
        ))

    fig_ets_map.update_layout(
        height=520, margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="white",
        hoverlabel=dict(bgcolor="white", bordercolor="#ccc", font=dict(size=12), align="left"),
        geo=dict(
            projection_type="equirectangular", showframe=False,
            showcoastlines=True, coastlinecolor="#333", coastlinewidth=1.2,
            showcountries=True, countrycolor="#333", countrywidth=1.2,
            showland=True, landcolor="#f0f0f0",
            showocean=False, bgcolor="white",
            lataxis=dict(range=[-60, 85], showgrid=False),
            lonaxis=dict(range=[-180, 180], showgrid=False),
        ),
    )

        # ── Detail helper functions ─────────────────────────────────
    def fval(v):
        if v is None: return "—"
        try:
            if pd.isna(v): return "—"
        except: pass
        s = str(v).strip()
        return s if s and s not in ("nan","NaN","-","–") else "—"

    def section_title(t):
        st.markdown(f'<div style="font-size:11px;font-weight:800;color:#457b9d;text-transform:uppercase;letter-spacing:2px;margin:16px 0 8px 0;border-bottom:2px solid #e8f0f8;padding-bottom:5px;">{t}</div>', unsafe_allow_html=True)

    def text_field(label, v):
        if v == "—": return
        lbl_html = f'<div style="font-size:9px;font-weight:700;color:#999;text-transform:uppercase;letter-spacing:1.5px;margin-bottom:3px;">{label}</div>' if label else ""
        st.markdown(
            f'<div style="margin-bottom:10px;">{lbl_html}'            f'<div style="font-size:11px;color:#1a1a2e;line-height:1.6;background:#f7fafd;border-radius:6px;padding:8px 10px;">{v}</div>'            f'</div>',
            unsafe_allow_html=True
        )

    def bar_visual(label, pct, display_val, color="#457b9d"):
        pct_w = min(max(float(pct) * 100, 2), 100)
        st.markdown(
            f'<div style="margin-bottom:12px;">'            f'<div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:4px;">'            f'<div style="font-size:9px;font-weight:700;color:#999;text-transform:uppercase;letter-spacing:1px;">{label}</div>'            f'<div style="font-size:13px;font-weight:800;color:{color};">{display_val}</div>'            f'</div>'            f'<div style="background:#e8f0f8;border-radius:4px;height:8px;overflow:hidden;">'            f'<div style="width:{pct_w:.1f}%;background:{color};height:100%;border-radius:4px;"></div>'            f'</div></div>',
            unsafe_allow_html=True
        )

    # ── Map + Detail side by side ───────────────────────────────
    col_map, col_card = st.columns([3, 1.5])

    with col_map:
        clicked = st.plotly_chart(fig_ets_map, use_container_width=True,
                                  key="ets_map", on_select="rerun",
                                  selection_mode="points",
                                  config={"scrollZoom": False, "doubleClick": False,
                                          "displayModeBar": False})

    selected = None        # country name
    selected_scheme = None
    if clicked and clicked.get("selection") and clicked["selection"].get("points"):
        pts = clicked["selection"]["points"]
        if pts:
            cd = pts[0].get("customdata")
            if cd and len(cd) > 0:
                val = cd[0]
                # Dots return country name
                if val in f_ets["country"].values:
                    selected = val
                else:
                    # choropleth fallback
                    selected = val
    if not selected and len(country_sel) == 1:
        selected = country_sel[0]

    with col_card:
        st.markdown("""
        <div style="font-size:15px;font-weight:800;color:#1a1a2e;margin-bottom:4px;">Scheme Detail</div>
        <div style="font-size:11px;color:#999;margin-bottom:12px;">Click a country to explore its ETS schemes.</div>
        """, unsafe_allow_html=True)

        if not selected:
            st.markdown("""
            <div style="background:#f8f9fa;border:2px dashed #ddd;border-radius:12px;
                        padding:56px 12px;text-align:center;color:#bbb;">
                <div style="font-size:32px;margin-bottom:8px;">🗺️</div>
                <div style="font-size:12px;">Click a country on the map</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            schemes = f_ets[f_ets["country"] == selected]

            # If a province was clicked, filter to just that scheme
            if selected_scheme:
                schemes_display = schemes[schemes["name"] == selected_scheme]
                if schemes_display.empty:
                    schemes_display = schemes
            else:
                schemes_display = schemes

            # Country header
            region_lbl = schemes["region"].iloc[0] if not schemes.empty else "—"
            prov_note = f' · {selected_scheme.replace(" pilot ETS","").replace(" ETS","")}' if selected_scheme else ""
            st.markdown(f"""
            <div style="background:linear-gradient(135deg,#1a3a5e 0%,#457b9d 100%);
                    border-radius:14px;padding:24px 28px;margin-bottom:20px;color:white;">
            <div style="font-size:28px;font-weight:900;letter-spacing:1px;margin-bottom:4px;">{selected.upper()}{prov_note}</div>
            <div style="font-size:13px;opacity:0.8;margin-bottom:12px;">{region_lbl}</div>
            <div style="display:flex;gap:8px;flex-wrap:wrap;">
                <div style="background:rgba(255,255,255,0.2);border-radius:6px;padding:4px 14px;font-size:12px;font-weight:700;">{len(schemes)} ETS Scheme(s) total</div>
                {"<div style='background:rgba(255,200,100,0.3);border-radius:6px;padding:4px 14px;font-size:12px;font-weight:700;'>Showing: " + selected_scheme + "</div>" if selected_scheme else ""}
            </div>
            </div>
            """, unsafe_allow_html=True)

            for scheme_idx, (_, r) in enumerate(schemes_display.iterrows()):
                if len(schemes_display) > 1:
                    st.markdown(f'<div style="background:#457b9d;color:white;font-size:12px;font-weight:800;border-radius:8px;padding:7px 14px;margin-bottom:10px;">Scheme {scheme_idx+1}: {r["name"]}</div>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<div style="font-size:15px;font-weight:800;color:#457b9d;margin-bottom:12px;">{r["name"]}</div>', unsafe_allow_html=True)

                # ── Key Metrics ──
                section_title("Key Metrics")
                price_num = r.get("price_num")
                share_num = r.get("share")
                all_prices = f_ets["price_num"].dropna()
                max_price  = all_prices.max() if len(all_prices) else 100
                pv = fval(r.get("price"))
                sv = int(r["start_date"]) if pd.notna(r.get("start_date")) else "—"
                rv = fval(r.get("revenue"))
                st.markdown(
                    f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;margin-bottom:8px;">'                    f'<div style="background:#ddeef8;border-radius:7px;padding:9px 10px;text-align:center;">'                    f'<div style="font-size:9px;font-weight:700;color:#457b9d;text-transform:uppercase;letter-spacing:1px;margin-bottom:3px;">Price Rate</div>'                    f'<div style="font-size:12px;font-weight:900;color:#1a3a5e;">{pv}</div></div>'                    f'<div style="background:#e8f0fe;border-radius:7px;padding:9px 10px;text-align:center;">'                    f'<div style="font-size:9px;font-weight:700;color:#3a5a9e;text-transform:uppercase;letter-spacing:1px;margin-bottom:3px;">Start Date</div>'                    f'<div style="font-size:12px;font-weight:900;color:#1a2a5e;">{sv}</div></div>'                    f'<div style="background:#e8f5e9;border-radius:7px;padding:9px 10px;text-align:center;grid-column:span 2;">'                    f'<div style="font-size:9px;font-weight:700;color:#3a7a3a;text-transform:uppercase;letter-spacing:1px;margin-bottom:3px;">Gov. Revenue (2024)</div>'                    f'<div style="font-size:12px;font-weight:900;color:#1a4a1a;">{rv}</div></div>'                    f'</div>',
                    unsafe_allow_html=True
                )
                if pd.notna(share_num) and share_num not in (None, ""):
                    try: bar_visual("Share of Jurisdiction", float(share_num), f"{float(share_num)*100:.0f}%", "#457b9d")
                    except: pass
                if pd.notna(price_num) and max_price > 0:
                    try: bar_visual("Price vs Max ETS", float(price_num)/float(max_price), f"USD {float(price_num):.2f} / {float(max_price):.0f}", "#2a9d8f")
                    except: pass

                # ── Coverage ──
                section_title("Coverage")
                text_field("GHG Coverage", fval(r.get("ghg")))
                text_field("Sector Coverage", fval(r.get("sectors")))

                # ── Threshold ──
                t1 = fval(r.get("threshold"))
                t2 = fval(r.get("description"))
                if t1 != "—" or t2 != "—":
                    section_title("Threshold")
                    text_field("Threshold", t1)
                    text_field("Description of Threshold", t2)

                # ── Cap & Allocation ──
                section_title("Cap & Allocation")
                text_field("Cap Emissions", fval(r.get("cap")))
                text_field("Tightening Rate", fval(r.get("tightening_rate")))
                text_field("Allocation Method", fval(r.get("allocation")))

                # ── Revenue & Funding ──
                section_title("Revenue & Funding")
                text_field("Revenue Recycling", fval(r.get("revenue_recycling")))
                text_field("Funding Program", fval(r.get("funding_program")))

                # ── Additional Info ──
                ai = fval(r.get("additional_info"))
                if ai != "—":
                    section_title("Additional Information")
                    text_field("", ai)

                # ── Source ──
                src = fval(r.get("source"))
                if src != "—":
                    section_title("Source")
                    for lnk in [s.strip() for s in src.split(";") if s.strip()]:
                        if lnk.startswith("http"):
                            st.markdown(f'<a href="{lnk}" target="_blank" style="font-size:10px;color:#457b9d;word-break:break-all;display:block;margin-bottom:3px;">{lnk}</a>', unsafe_allow_html=True)
                        else:
                            st.markdown(f'<div style="font-size:11px;color:#555;">{lnk}</div>', unsafe_allow_html=True)

                if scheme_idx < len(schemes_display) - 1:
                    st.divider()

    st.divider()

    # ── Timeline ──────────────────────────────────────────────────
    st.markdown("""
    <div style="font-size:28px;font-weight:900;color:#1a1a2e;margin-bottom:4px;">ETS Timeline</div>
    <div style="font-size:13px;color:#999;margin-bottom:16px;">Year each ETS scheme was established.</div>
    """, unsafe_allow_html=True)

    timeline_df = ets[ets["start_date"].notna()].sort_values("start_date").copy()
    REGION_COLORS = {
        "North America":              "#4a90d9",
        "East Asia & Pacific":        "#2a9d8f",
        "Europe & Central Asia":      "#457b9d",
        "Latin America & Caribbean":  "#e07b00",
    }
    tl_colors = [REGION_COLORS.get(r, "#888") for r in timeline_df["region"]]
    fig_tl = go.Figure()
    for region, color in REGION_COLORS.items():
        sub = timeline_df[timeline_df["region"] == region]
        if sub.empty: continue
        fig_tl.add_trace(go.Scatter(
            x=sub["start_date"], y=sub["name"],
            mode="markers+text",
            marker=dict(size=12, color=color, line=dict(width=1, color="#222")),
            text=sub["price"].fillna("N/A"),
            textposition="middle right",
            textfont=dict(size=9, color="#555"),
            name=region,
            hovertemplate="<b>%{y}</b><br>%{x}<br>Price: %{text}<extra></extra>",
        ))
    fig_tl.update_layout(
        height=520, margin=dict(l=0, r=120, t=10, b=0),
        paper_bgcolor="white", plot_bgcolor="white",
        xaxis=dict(title="Year", showgrid=True, gridcolor="#f0f0f0", dtick=2),
        yaxis=dict(title="", showgrid=False, tickfont=dict(size=10)),
        legend=dict(bgcolor="rgba(255,255,255,0.9)", bordercolor="#e0e0e0",
                    borderwidth=1, font=dict(size=11)),
        hoverlabel=dict(bgcolor="white", bordercolor="#ccc", font=dict(size=12), align="left"),
    )
    st.plotly_chart(fig_tl, use_container_width=True, key="ets_timeline",
                    config={"displayModeBar": False})

    st.divider()

    # ── Map + Detail

    

        # ── Charts ────────────────────────────────────────────────────
    st.markdown("""
    <div style="font-size:28px;font-weight:900;color:#1a1a2e;margin-bottom:4px;">Summary</div>
    <div style="font-size:13px;color:#999;margin-bottom:20px;">Distribution of ETS schemes by region and price.</div>
    """, unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Schemes by Region")
        by_region = f_ets.groupby("region")["name"].count().reset_index(name="count")
        fig_r = go.Figure(go.Bar(
            x=by_region["region"], y=by_region["count"],
            marker_color=[REGION_COLORS.get(r, "#888") for r in by_region["region"]],
            marker_line_color="#222", marker_line_width=1,
            text=by_region["count"], textposition="outside",
            hovertemplate="%{x}: <b>%{y} schemes</b><extra></extra>",
        ))
        fig_r.update_layout(
            margin=dict(l=0, r=0, t=10, b=0), paper_bgcolor="white",
            plot_bgcolor="white", showlegend=False,
            xaxis=dict(tickfont=dict(size=10), showgrid=False),
            yaxis=dict(showgrid=True, gridcolor="#f0f0f0"),
        )
        st.plotly_chart(fig_r, use_container_width=True, key="ets_region_bar",
                        config={"displayModeBar": False})

    with c2:
        st.subheader("Carbon Price Distribution")
        price_df = f_ets[f_ets["price_num"].notna()].copy().sort_values("price_num", ascending=False)
        fig_p = go.Figure(go.Bar(
            x=price_df["name"], y=price_df["price_num"],
            marker_color=[REGION_COLORS.get(r, "#888") for r in price_df["region"]],
            marker_line_color="#222", marker_line_width=1,
            text=price_df["price"].fillna("N/A"),
            textposition="outside", textfont=dict(size=8),
            hovertemplate="<b>%{x}</b><br>Price: %{text}<extra></extra>",
        ))
        fig_p.update_layout(
            margin=dict(l=0, r=0, t=10, b=0), paper_bgcolor="white",
            plot_bgcolor="white", showlegend=False,
            xaxis=dict(tickfont=dict(size=8), tickangle=-45, showgrid=False),
            yaxis=dict(title="USD", showgrid=True, gridcolor="#f0f0f0"),
        )
        st.plotly_chart(fig_p, use_container_width=True, key="ets_price_bar",
                        config={"displayModeBar": False})

    st.divider()

    # ── Full Table ────────────────────────────────────────────────
    st.markdown("""
    <div style="font-size:28px;font-weight:900;color:#1a1a2e;margin-bottom:4px;">All ETS Schemes</div>
    <div style="font-size:13px;color:#999;margin-bottom:16px;">Complete list of tracked ETS schemes worldwide.</div>
    """, unsafe_allow_html=True)

    # Search + filter
    ts1, ts2 = st.columns([2, 2])
    with ts1:
        search_q = st.text_input("Search by scheme or country name", placeholder="e.g. EU ETS, China...", key="ets_search")
    with ts2:
        region_tbl = st.multiselect("Filter by region", regions_all, key="ets_tbl_region", placeholder="All regions")

    # Get all original columns for display
    display_cols = {
        "name": "Scheme", "country": "Jurisdiction", "region": "Region",
        "start_date": "Est.", "price": "Price Rate", "share": "Share of Jurisdiction",
        "revenue": "Revenue (2024)", "ghg": "GHG Coverage", "sectors": "Sector Coverage",
        "allocation": "Allocation Method", "cap": "Cap Emissions", "revenue_recycling": "Revenue Recycling",
    }

    tbl = ets.copy()

    if search_q:
        mask = (tbl["name"].str.contains(search_q, case=False, na=False) |
                tbl["country"].str.contains(search_q, case=False, na=False))
        tbl = tbl[mask]
    if region_tbl:
        tbl = tbl[tbl["region"].isin(region_tbl)]

    show_cols = [c for c in display_cols if c in tbl.columns]
    tbl_show = tbl[show_cols].copy()
    tbl_show.columns = [display_cols[c] for c in show_cols]
    tbl_show["Est."] = tbl_show["Est."].apply(lambda x: int(x) if pd.notna(x) else "—")
    st.dataframe(tbl_show, use_container_width=True, hide_index=True)


# ── Router ─────────────────────────────────────────────────────
if page == "mbm":
    page_mbm()
elif page == "ets":
    page_ets()
elif page == "cbam":
    page_placeholder("CBAM", "")
else:
    page_mbm()
