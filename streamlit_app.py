# streamlit_app.py — Global MBM Dashboard
# Single-file app with top navbar via query_params routing
from __future__ import annotations
import re as _re
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
    .block-container { padding-top: 0 !important; padding-left: 2rem; padding-right: 2rem; }
    .navbar { display:flex; align-items:center; background-color:#1a1a2e; padding:0 2rem; height:56px; margin-left:-2rem; margin-right:-2rem; margin-bottom:1.5rem; }
    .navbar-brand { font-size:18px; font-weight:800; color:white !important; text-decoration:none !important; letter-spacing:1px; margin-right:2.5rem; line-height:1.2; }
    .navbar-brand span { font-size:10px; font-weight:400; color:#aab4c8; display:block; letter-spacing:0.5px; }
    .nav-links { display:flex; height:56px; align-items:stretch; }
    .nav-link { color:#aab4c8 !important; text-decoration:none !important; font-size:13px; font-weight:500; padding:0 18px; display:flex; align-items:center; border-bottom:3px solid transparent; white-space:nowrap; }
    .nav-link:hover { color:white !important; background:rgba(255,255,255,0.06); }
    .nav-link.active { color:white !important; border-bottom:3px solid #4a90d9; font-weight:700; }
</style>
""", unsafe_allow_html=True)

params = st.query_params
page = params.get("page", "mbm")

def nav_link(label, key, icon=""):
    cls = "nav-link active" if page == key else "nav-link"
    prefix = f"{icon} " if icon else ""
    return f'<a class="{cls}" href="?page={key}">{prefix}{label}</a>'

st.markdown(f"""
<div class="navbar">
    <a class="navbar-brand" href="?page=mbm">🌍 MBM<span>Market-Based Mechanisms</span></a>
    <div class="nav-links">
        {nav_link("MBM", "mbm", "🗺️")}
        {nav_link("ETS", "ets")}
        {nav_link("CBAM", "cbam")}
    </div>
</div>
""", unsafe_allow_html=True)

# ── Constants ──────────────────────────────────────────────────
FILE_PATH = "data/Global Market Based Mechanism.xlsx"

MECH_COLS = {
    "1. Carbon Tax":     "Carbon Tax",
    "2. ETS":            "ETS",
    "3. Tax Incentives": "Tax Incentives",
    "4. Fuel Mandates":  "Fuel Mandates",
    "5. VCM project ":   "VCM project",
    "6. Feebates":       "Feebates",
    "7. CBAM":           "CBAM",
    "8. AMC":            "AMC",
}

CARBON_PRICING_COLORS = {
    "ETS + Carbon Tax":  "#f4a261",
    "Carbon Tax":        "#90be6d",
    "ETS":               "#457b9d",
    "No Carbon Pricing": "#f0f0f0",
}

CP_DISPLAY = {
    "ETS + Carbon Tax":  "ETS and Carbon Tax",
    "Carbon Tax":        "Carbon Tax",
    "ETS":               "ETS",
    "No Carbon Pricing": "No Carbon Pricing",
}

MARKER_STYLES = {
    "CBAM":           {"symbol": "square",      "color": "#4a90d9", "size": 4},
    "Tax Incentives": {"symbol": "diamond",     "color": "#9b59b6", "size": 5},
    "Fuel Mandates":  {"symbol": "triangle-up", "color": "#e07b00", "size": 5},
    "Feebates":       {"symbol": "circle",      "color": "#e63946", "size": 4},
    "VCM project":    {"symbol": "asterisk",    "color": "#2a9d8f", "size": 5},
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

MECH_SYMBOL_HOVER = {
    "CBAM": "■", "Tax Incentives": "◆", "Fuel Mandates": "▲",
    "Feebates": "●", "VCM project": "✳", "AMC": "✚",
}

CENTROIDS = {
    "USA": (37.09,-95.71), "CAN": (56.13,-106.35), "MEX": (23.63,-102.55),
    "BRA": (-14.24,-51.93),"ARG": (-38.42,-63.62), "CHL": (-35.68,-71.54),
    "COL": (4.57,-74.30),  "PER": (-9.19,-75.02),  "VEN": (6.42,-66.59),
    "ECU": (-1.83,-78.18), "BOL": (-16.29,-63.59), "PRY": (-23.44,-58.44),
    "URY": (-32.52,-55.77),"GUY": (4.86,-58.93),   "SUR": (3.92,-56.03),
    "GBR": (55.38,-3.44),  "FRA": (46.23,2.21),    "DEU": (51.17,10.45),
    "ITA": (41.87,12.57),  "ESP": (40.46,-3.75),   "PRT": (39.40,-8.22),
    "NLD": (52.13,5.29),   "BEL": (50.50,4.47),    "CHE": (46.82,8.23),
    "AUT": (47.52,14.55),  "SWE": (60.13,18.64),   "NOR": (60.47,8.47),
    "DNK": (56.26,9.50),   "FIN": (61.92,25.75),   "POL": (51.92,19.15),
    "CZE": (49.82,15.47),  "HUN": (47.16,19.50),   "ROU": (45.94,24.97),
    "GRC": (39.07,21.82),  "IRL": (53.41,-8.24),   "LUX": (49.82,6.13),
    "RUS": (61.52,105.32), "UKR": (48.38,31.17),   "TUR": (38.96,35.24),
    "CHN": (35.86,104.20), "JPN": (36.20,138.25),  "KOR": (35.91,127.77),
    "IND": (20.59,78.96),  "AUS": (-25.27,133.78), "NZL": (-40.90,174.89),
    "ZAF": (-30.56,22.94), "NGA": (9.08,8.68),     "KEN": (-0.02,37.91),
    "EGY": (26.82,30.80),  "MAR": (31.79,-7.09),   "DZA": (28.03,1.66),
    "SAU": (23.89,45.08),  "ARE": (23.42,53.85),   "IRN": (32.43,53.69),
    "PAK": (30.38,69.35),  "BGD": (23.68,90.36),   "IDN": (-0.79,113.92),
    "MYS": (4.21,108.00),  "THA": (15.87,100.99),  "VNM": (14.06,108.28),
    "PHL": (12.88,121.77), "SGP": (1.35,103.82),   "KAZ": (48.02,66.92),
    "MNG": (46.86,103.85), "ISL": (64.96,-19.02),  "LVA": (56.88,24.60),
    "LTU": (55.17,23.88),  "EST": (58.60,25.01),   "SVK": (48.67,19.70),
    "SVN": (46.15,14.99),  "HRV": (45.10,15.20),   "BGR": (42.73,25.49),
    "SRB": (44.02,21.09),  "MNE": (42.71,19.37),   "MKD": (41.61,21.75),
    "ALB": (41.15,20.17),  "BIH": (43.92,17.68),   "GEO": (42.32,43.36),
    "ARM": (40.07,45.04),  "AZE": (40.14,47.58),   "KGZ": (41.20,74.77),
    "UZB": (41.38,64.59),  "TKM": (38.97,59.56),   "TJK": (38.86,71.28),
    "BLR": (53.71,27.95),  "MDA": (47.41,28.37),   "CRI": (9.75,-83.75),
    "PAN": (8.54,-80.78),  "GTM": (15.78,-90.23),  "CUB": (21.52,-77.78),
    "DOM": (18.74,-70.16), "JAM": (18.11,-77.30),  "TTO": (10.69,-61.22),
    "CMR": (3.85,11.50),   "CIV": (7.54,-5.55),    "SEN": (14.50,-14.45),
    "GHA": (7.95,-1.02),   "NER": (17.61,8.08),    "ETH": (9.15,40.49),
    "TZA": (-6.37,34.89),  "MOZ": (-18.67,35.53),  "ZMB": (-13.13,27.85),
    "ZWE": (-19.02,29.15), "AGO": (-11.20,17.87),  "COD": (-4.04,21.76),
    "MDG": (-18.77,46.87), "UGA": (1.37,32.29),    "RWA": (-1.94,29.87),
    "BWA": (-22.33,24.68), "NAM": (-22.96,18.49),  "LSO": (-29.61,28.23),
    "LBY": (26.34,17.23),  "MRT": (21.01,-10.94),  "IRQ": (33.22,43.68),
    "SYR": (34.80,38.99),  "YEM": (15.55,48.52),   "OMN": (21.51,55.92),
    "QAT": (25.35,51.18),  "KWT": (29.31,47.48),   "JOR": (30.59,36.24),
    "ISR": (31.05,34.85),  "PSE": (31.95,35.29),   "LBN": (33.85,35.86),
    "TWN": (23.70,121.00), "HKG": (22.40,114.11),  "PNG": (-6.31,143.96),
    "FJI": (-17.71,178.07),"MDV": (3.20,73.22),    "MUS": (-20.35,57.55),
}

MANUAL_ISO3 = {
    "Côte d'Ivoire": "CIV", "Cote d'Ivoire": "CIV",
    "Democratic Republic of the Congo": "COD", "Republic of the Congo": "COG",
    "United States": "USA", "Russia": "RUS", "Iran": "IRN", "Syria": "SYR",
    "North Korea": "PRK", "South Korea": "KOR",
    "Laos": "LAO", "Timor-Leste": "TLS", "Brunei Darussalam": "BRN",
    "Bolivia": "BOL", "Venezuela": "VEN", "Tanzania": "TZA",
    "Palestine": "PSE", "Taiwan": "TWN", "Vietnam": "VNM", "Moldova": "MDA",
    "European Union": "EUU", "Korea, Rep.": "KOR",
}

REGION_COLORS_ETS = {
    "North America":             "#4a90d9",
    "East Asia & Pacific":       "#2a9d8f",
    "Europe & Central Asia":     "#457b9d",
    "Latin America & Caribbean": "#e07b00",
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
    df = pd.read_excel(FILE_PATH, sheet_name="Dashboard")
    df.columns = [str(c).strip() for c in df.columns]
    return df

def tidy_long(df_raw):
    keep = ["No","Country","Region"] + [c.strip() for c in MECH_COLS] + ["Total Mechanism"]
    keep = [c for c in keep if c in df_raw.columns]
    df = df_raw[keep].copy()
    df = df[df["Country"].notna()]
    df["Country"] = df["Country"].astype(str).str.strip()
    df = df[df["Country"].str.lower() != "country"]
    value_cols = [c.strip() for c in MECH_COLS if c.strip() in df.columns]
    long = df.melt(id_vars=["No","Country","Region"], value_vars=value_cols,
                   var_name="mechanism_type_raw", value_name="mechanism_detail")
    long["mechanism_type"] = (
        long["mechanism_type_raw"].map({k.strip(): v for k, v in MECH_COLS.items()})
        .fillna(long["mechanism_type_raw"])
    )
    long = long.drop(columns=["mechanism_type_raw"])
    long["mechanism_detail"] = long["mechanism_detail"].astype(str).str.strip()
    long = long[(long["mechanism_detail"] != "") & (long["mechanism_detail"].str.lower() != "nan")]
    mask_vcm = long["mechanism_type"] == "VCM project"
    long["vcm_projects"] = pd.NA
    long.loc[mask_vcm, "vcm_projects"] = pd.to_numeric(long.loc[mask_vcm,"mechanism_detail"], errors="coerce")
    long = long[~((~mask_vcm) & (long["mechanism_detail"] == "0"))]
    return df, long

def get_carbon_pricing_type(mechs: set) -> str:
    has_ets = "ETS" in mechs
    has_tax = "Carbon Tax" in mechs
    if has_ets and has_tax: return "ETS + Carbon Tax"
    if has_ets: return "ETS"
    if has_tax: return "Carbon Tax"
    return "No Carbon Pricing"

@st.cache_data
def load_detail_data():
    xl = pd.ExcelFile(FILE_PATH)

    def safe(sheet, **kw):
        try:
            d = xl.parse(sheet, **kw)
            d.columns = [str(c).strip() for c in d.columns]
            return d
        except Exception:
            return pd.DataFrame()

    def col(df, kw):
        for c in df.columns:
            if kw.lower() in c.lower():
                return c
        return None

    ets_d = safe("1.a ETS")
    ctx_d = safe("1.b Carbon Tax")
    fm_d  = safe("Fuel Mandates")
    vcm_d = safe("8. VCM")
    fee_d = safe("Sheet23")
    ti_d  = safe("6. Tax Incentives", header=1)
    amc_d = safe("AMC")

    ets_rows = []
    for _, r in ets_d.iterrows():
        c = str(r.get("Jurisdiction","")).strip()
        if not c or c == "nan": continue
        ets_rows.append({
            "country": c,
            "name": str(r.get("Instrument name","")).strip(),
            "price": str(r.get("Price rate","")).strip(),
            "start_date": r.get("Start date"),
            "sectors": str(r.get("Sector coverage","")).strip(),
        })

    ctx_rows = []
    for _, r in ctx_d.iterrows():
        jc = col(ctx_d,"jurisdiction") or col(ctx_d,"country")
        c = str(r.get(jc,"") if jc else "").strip()
        if not c or c == "nan": continue
        nc = col(ctx_d,"instrument") or col(ctx_d,"name")
        pc = col(ctx_d,"price")
        ctx_rows.append({
            "country": c,
            "name": str(r.get(nc,"") if nc else "").strip(),
            "price": str(r.get(pc,"") if pc else "").strip(),
            "start_date": r.get("Start date") if "Start date" in ctx_d.columns else None,
            "sectors": str(r.get("Sector coverage","") if "Sector coverage" in ctx_d.columns else "").strip(),
        })

    fm_rows = []
    mt_col = col(fm_d,"mandate") or col(fm_d,"type")
    cc_col = col(fm_d,"country") or col(fm_d,"jurisdiction")
    for _, r in fm_d.iterrows():
        c = str(r.get(cc_col,"") if cc_col else "").strip()
        if not c or c == "nan": continue
        fm_rows.append({
            "country": c,
            "mandate_type": str(r.get(mt_col,"") if mt_col else "").strip(),
            "description": str(r.get(col(fm_d,"description"),"") if col(fm_d,"description") else "").strip(),
        })

    vcm_rows = []
    for _, r in vcm_d.iterrows():
        cc = col(vcm_d,"country") or col(vcm_d,"jurisdiction")
        c = str(r.get(cc,"") if cc else "").strip()
        if not c or c == "nan": continue
        vcm_rows.append({
            "country": c,
            "projects": r.get(col(vcm_d,"project")) if col(vcm_d,"project") else None,
            "credits":  r.get(col(vcm_d,"credit") or col(vcm_d,"issued")) if (col(vcm_d,"credit") or col(vcm_d,"issued")) else None,
        })

    fee_rows = []
    for _, r in fee_d.iterrows():
        cc = col(fee_d,"country") or col(fee_d,"jurisdiction")
        c = str(r.get(cc,"") if cc else "").strip()
        if not c or c == "nan": continue
        pn = col(fee_d,"policy") or col(fee_d,"name")
        nm = str(r.get(pn,"") if pn else "")
        if nm.lower() in ("none identified","nan",""): continue
        fee_rows.append({
            "country": c,
            "policy_name": nm,
            "policy_type": str(r.get(col(fee_d,"type"),"") if col(fee_d,"type") else ""),
            "status": str(r.get(col(fee_d,"status"),"") if col(fee_d,"status") else ""),
        })

    ti_rows = []
    benefit_cols = [c for c in ti_d.columns if c not in ("Country","Region","No") and not c.startswith("Unnamed")]
    for _, r in ti_d.iterrows():
        cc = "Country" if "Country" in ti_d.columns else col(ti_d,"country")
        c = str(r.get(cc,"") if cc else "").strip()
        if not c or c == "nan": continue
        cats = [bc for bc in benefit_cols if pd.notna(r.get(bc)) and str(r.get(bc,"")).strip() not in ("","nan")]
        ti_rows.append({"country": c, "categories": cats})

    amc_rows = []
    for _, r in amc_d.iterrows():
        cc = col(amc_d,"country") or col(amc_d,"jurisdiction")
        c = str(r.get(cc,"") if cc else "").strip()
        if not c or c == "nan": continue
        amc_rows.append({
            "country": c,
            "product": str(r.get(col(amc_d,"product"),"") if col(amc_d,"product") else ""),
            "sector":  str(r.get(col(amc_d,"sector"),"")  if col(amc_d,"sector")  else ""),
        })

    dash = load_raw()
    fm_col = "4. Fuel Mandates"
    dashboard_fm = {}
    if fm_col in dash.columns:
        for _, r in dash.iterrows():
            cv = str(r.get("Country","")).strip()
            vv = str(r.get(fm_col,"")).strip()
            if cv and vv and vv.lower() not in ("nan",""):
                dashboard_fm[cv] = vv

    return dict(ets=ets_rows, ctx=ctx_rows, fm=fm_rows,
                vcm=vcm_rows, feebates=fee_rows, tax_incentives=ti_rows,
                amc=amc_rows, dashboard_fm=dashboard_fm)


def render_country_card(country, region, long_df):
    cf    = long_df[long_df["Country"] == country]
    mechs = sorted(cf["mechanism_type"].unique()) if len(cf) else []
    cp_type  = get_carbon_pricing_type(set(mechs))
    cp_color = CARBON_PRICING_COLORS[cp_type]
    cp_label = CP_DISPLAY.get(cp_type, cp_type)
    cp_tc    = "#1a1a2e" if cp_type == "No Carbon Pricing" else "white"
    others   = [m for m in mechs if m not in {"ETS","Carbon Tax"}]
    boxes = "".join(
        f'<div style="background:{MECH_BOX_COLORS.get(m,"#888")};color:white;padding:5px 12px;'
        f'border-radius:6px;font-weight:700;font-size:12px;border:1.5px solid #222;white-space:nowrap;">{m}</div>'
        for m in others
    )
    st.markdown(f"""
    <div style="background:white;border:2px solid #e0e0e0;border-radius:12px;
                padding:20px 24px;box-shadow:0 4px 16px rgba(0,0,0,0.08);margin-bottom:12px;">
        <div style="font-size:22px;font-weight:800;color:#1a1a2e;letter-spacing:1px;margin-bottom:4px;">{country.upper()}</div>
        <div style="font-size:12px;color:#888;margin-bottom:14px;">{region}</div>
        <div style="margin-bottom:12px;">
            <div style="background:{cp_color};color:{cp_tc};padding:5px 14px;border-radius:6px;
                        font-weight:700;font-size:12px;border:1.5px solid #222;display:inline-block;">{cp_label}</div>
        </div>
        {"<div style='font-size:11px;color:#888;margin-bottom:6px;font-weight:600;text-transform:uppercase;letter-spacing:1px;'>Other mechanisms:</div>" if others else ""}
        <div style="display:flex;gap:6px;flex-wrap:wrap;">{boxes}</div>
    </div>
    """, unsafe_allow_html=True)


def render_mechanism_details(country, long_df):
    detail = load_detail_data()
    cf     = long_df[long_df["Country"] == country]
    mechs  = sorted(cf["mechanism_type"].unique()) if len(cf) else []
    if not mechs:
        return

    def pill(label, val, bg="#e8f0fe", tc="#1a2a5e"):
        return (f'<span style="background:{bg};color:{tc};padding:4px 10px;border-radius:4px;'
                f'font-size:11px;font-weight:600;margin-right:6px;margin-bottom:4px;display:inline-block;">'
                f'{label}: <b>{val}</b></span>')

    def card(border_color, bg, content):
        return (f'<div style="border-left:4px solid {border_color};padding:12px 16px;'
                f'margin-bottom:10px;background:{bg};border-radius:0 8px 8px 0;">{content}</div>')

    def ttl(label, color):
        return f'<div style="font-size:14px;font-weight:800;color:{color};margin-bottom:8px;">{label}</div>'

    def meta(text):
        return f'<div style="font-size:11px;color:#555;margin-top:4px;line-height:1.5;">{text}</div>'

    html = ""

    if "ETS" in mechs:
        rows = [r for r in detail["ets"] if r["country"] == country]
        if rows:
            r = rows[0]
            p = r["price"] if r["price"] and r["price"] != "nan" else "N/A"
            s = str(int(r["start_date"])) if pd.notna(r.get("start_date")) else "N/A"
            sc = (r["sectors"][:60]+"…") if len(r["sectors"])>60 else r["sectors"]
            inner = ttl(r["name"],"#457b9d") + pill("Price",p) + pill("Est.",s) + meta(f"Sectors: {sc}")
            html += card("#457b9d","#f0f5fa",inner)

    if "Carbon Tax" in mechs:
        rows = [r for r in detail["ctx"] if r["country"] == country]
        if rows:
            r = rows[0]
            p = r["price"] if r["price"] and r["price"] != "nan" else "N/A"
            s = str(int(r["start_date"])) if pd.notna(r.get("start_date")) else "N/A"
            sc = (r["sectors"][:60]+"…") if len(r["sectors"])>60 else r["sectors"]
            inner = ttl(r["name"],"#5a8a3a") + pill("Price",p,"#e8f5e9","#1a4a1a") + pill("Est.",s,"#e8f5e9","#1a4a1a") + meta(f"Sectors: {sc}")
            html += card("#5a8a3a","#f0f8f0",inner)

    if "Fuel Mandates" in mechs:
        rows = [r for r in detail["fm"] if r["country"] == country]
        mt = (rows[0].get("mandate_type","") if rows else "") or detail["dashboard_fm"].get(country,"Fuel Mandate")
        desc = rows[0].get("description","") if rows else ""
        req = f'<div style="background:#fff3e0;border-radius:4px;padding:6px 8px;font-size:11px;color:#333;margin-top:4px;">{mt}</div>'
        inner = ttl("Fuel Mandate","#e07b00") + req
        if desc and desc != "nan":
            inner += meta(desc[:120]+"…" if len(desc)>120 else desc)
        html += card("#e07b00","#fff8f0",inner)

    if "VCM project" in mechs:
        rows = [r for r in detail["vcm"] if r["country"] == country]
        inner = ttl("Voluntary Carbon Market (VCM)","#2a9d8f")
        if rows:
            r = rows[0]
            if pd.notna(r.get("projects")): inner += pill("Projects",int(r["projects"]),"#e0f5f2","#1a4a44")
        html += card("#2a9d8f","#f0faf8",inner)

    if "Feebates" in mechs:
        rows = [r for r in detail["feebates"] if r["country"] == country]
        for r in rows:
            pn = r.get("policy_name","Feebate")
            pt = r.get("policy_type",""); sv = r.get("status","")
            inner = ttl(pn,"#e63946")
            if pt and pt != "nan": inner += pill("Type",pt,"#fde8ea","#5a1a1a")
            if sv and sv != "nan": inner += pill("Status",sv,"#fde8ea","#5a1a1a")
            html += card("#e63946","#fff0f1",inner)

    if "Tax Incentives" in mechs:
        rows = [r for r in detail["tax_incentives"] if r["country"] == country]
        if rows:
            cats = rows[0].get("categories",[])
            inner = ttl("Tax Incentives","#7b2d8b") + "".join(pill(c,"","#f3e8ff","#3a1a5e") for c in cats)
            html += card("#7b2d8b","#faf0ff",inner)

    if "AMC" in mechs:
        rows = [r for r in detail["amc"] if r["country"] == country]
        if rows:
            r = rows[0]
            prod = r.get("product","AMC"); sec = r.get("sector","")
            inner = ttl(f'Advance Market Commitment — {prod}',"#5b9bd5")
            if sec and sec != "nan": inner += pill("Sector",sec,"#e8f0fe","#1a2a5e")
            html += card("#5b9bd5","#f0f5ff",inner)

    if html:
        st.markdown('<div style="font-size:11px;font-weight:700;color:#999;text-transform:uppercase;letter-spacing:2px;margin:16px 0 8px 0;">Mechanism Details</div>', unsafe_allow_html=True)
        st.markdown(html, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
#  PAGE: MBM
# ══════════════════════════════════════════════════════════════
def page_mbm():
    raw = load_raw()
    wide, long = tidy_long(raw)

    n_countries = int(wide["Country"].nunique())
    n_mechs     = int(long["mechanism_type"].nunique())

    cp_map = wide[["Country","Region"]].drop_duplicates().copy()
    cp_map["iso3"] = cp_map["Country"].apply(to_iso3)
    country_mechs_all = long.groupby("Country")["mechanism_type"].apply(set).to_dict()
    cp_map["cp_type"] = cp_map["Country"].apply(lambda c: get_carbon_pricing_type(country_mechs_all.get(c,set())))
    n_ets  = int(cp_map["cp_type"].isin(["ETS","ETS + Carbon Tax"]).sum())
    n_ctx  = int(cp_map["cp_type"].isin(["Carbon Tax","ETS + Carbon Tax"]).sum())
    n_both = int((cp_map["cp_type"] == "ETS + Carbon Tax").sum())

    # Hero
    st.markdown(f"""
    <div style="text-align:center;padding:72px 2rem 56px 2rem;border-radius:12px;margin-bottom:0;">
        <div style="font-size:72px;font-weight:900;color:#1a1a2e;line-height:1.05;letter-spacing:-2px;margin-bottom:32px;white-space:nowrap;">
            Global Market-Based Mechanisms Dashboard
        </div>
        <div style="font-size:18px;color:#666;max-width:900px;margin:0 auto 40px auto;line-height:1.8;">
            A market-based mechanism (MBM) is a climate policy instrument that uses market principles<br>
            to create economic incentives for reducing greenhouse gas emissions.
        </div>
        <div style="display:flex;justify-content:center;gap:48px;flex-wrap:wrap;margin-bottom:48px;align-items:center;">
            <div>
                <div style="font-size:56px;font-weight:900;color:#1a1a2e;line-height:1;">{n_countries}</div>
                <div style="font-size:11px;color:#999;font-weight:700;text-transform:uppercase;letter-spacing:2px;margin-top:6px;">Countries Covered</div>
            </div>
            <div style="width:1px;height:60px;background:#e0e0e0;"></div>
            <div>
                <div style="font-size:56px;font-weight:900;color:#1a1a2e;line-height:1;">{n_mechs}</div>
                <div style="font-size:11px;color:#999;font-weight:700;text-transform:uppercase;letter-spacing:2px;margin-top:6px;">Mechanism Types</div>
            </div>
            <div style="width:1px;height:60px;background:#e0e0e0;"></div>
            <div>
                <div style="font-size:56px;font-weight:900;color:#457b9d;line-height:1;">{n_ets}</div>
                <div style="font-size:11px;color:#999;font-weight:700;text-transform:uppercase;letter-spacing:2px;margin-top:6px;">Countries with ETS</div>
            </div>
            <div style="width:1px;height:60px;background:#e0e0e0;"></div>
            <div>
                <div style="font-size:56px;font-weight:900;color:#5a8a3a;line-height:1;">{n_ctx}</div>
                <div style="font-size:11px;color:#999;font-weight:700;text-transform:uppercase;letter-spacing:2px;margin-top:6px;">Countries with Carbon Tax</div>
            </div>
            <div style="width:1px;height:60px;background:#e0e0e0;"></div>
            <div>
                <div style="font-size:56px;font-weight:900;color:#c97a3a;line-height:1;">{n_both}</div>
                <div style="font-size:11px;color:#999;font-weight:700;text-transform:uppercase;letter-spacing:2px;margin-top:6px;">ETS and Carbon Tax</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div id="map-section"></div>', unsafe_allow_html=True)
    st.markdown("<hr style='margin:0 0 24px 0;border:none;border-top:1px solid #e8e8e8;'>", unsafe_allow_html=True)
    st.markdown("""
    <div style="font-size:36px;font-weight:900;color:#1a1a2e;margin-bottom:4px;">Market-Based Mechanism Map</div>
    <div style="font-size:13px;color:#999;margin-bottom:20px;">Select filters to explore. Click a country for details.</div>
    """, unsafe_allow_html=True)

    if "reset_counter" not in st.session_state:
        st.session_state["reset_counter"] = 0
    rc = st.session_state["reset_counter"]

    fc1, fc2, fc3, fc4 = st.columns([2,2,2,0.7])
    with fc1:
        region_sel  = st.multiselect("Region", sorted(long["Region"].dropna().unique()), key=f"f_region_{rc}", placeholder="All regions")
    with fc2:
        type_sel    = st.multiselect("Mechanism type", sorted(long["mechanism_type"].dropna().unique()), key=f"f_type_{rc}", placeholder="All types")
    with fc3:
        country_sel = st.multiselect("Country", sorted(long["Country"].dropna().unique()), key=f"f_country_{rc}", placeholder="All countries")
    with fc4:
        st.markdown('<div style="height:28px"></div>', unsafe_allow_html=True)
        if st.button("↺ Reset", key="reset_btn", use_container_width=True):
            st.session_state["reset_counter"] += 1
            st.rerun()

    f = long.copy()
    if region_sel:  f = f[f["Region"].isin(region_sel)]
    if type_sel:    f = f[f["mechanism_type"].isin(type_sel)]
    if country_sel: f = f[f["Country"].isin(country_sel)]

    wide_view = wide.copy()
    if region_sel:  wide_view = wide_view[wide_view["Region"].isin(region_sel)]
    if country_sel: wide_view = wide_view[wide_view["Country"].isin(country_sel)]

    country_mechs_map = f.groupby("Country")["mechanism_type"].apply(set).to_dict()
    base = wide_view[["Country","Region"]].drop_duplicates().copy()
    base["iso3"]    = base["Country"].apply(to_iso3)
    base["cp_type"] = base["Country"].apply(lambda c: get_carbon_pricing_type(country_mechs_map.get(c,set())))

    def build_hover(country):
        mechs = sorted(country_mechs_map.get(country, {"No recorded mechanisms"}))
        cp    = get_carbon_pricing_type(set(mechs))
        reg   = wide[wide["Country"]==country]["Region"].iloc[0] if country in wide["Country"].values else "—"
        cp_c  = CARBON_PRICING_COLORS.get(cp,"#999")
        cp_l  = CP_DISPLAY.get(cp, cp)
        lines = [f"<b>{country}</b>", f"<span style='color:#999'>{reg}</span>", "─────────────",
                 f'<span style="color:{cp_c}">■</span> {cp_l}']
        others = [m for m in mechs if m not in ("ETS","Carbon Tax")]
        if others:
            lines.append("─────────────")
            for m in others:
                sym = MECH_SYMBOL_HOVER.get(m,"●")
                clr = MECH_COLORS_HEX.get(m,"#888")
                lines.append(f'<span style="color:{clr}">{sym}</span> {m}')
        return "<br>".join(lines)

    base["hover_text"] = base["Country"].apply(build_hover)
    m_plot = base.dropna(subset=["iso3"]).copy()

    fig_map = go.Figure()
    for cp_type_k, color in CARBON_PRICING_COLORS.items():
        subset = m_plot[m_plot["cp_type"] == cp_type_k]
        if subset.empty: continue
        fig_map.add_trace(go.Choropleth(
            locations=subset["iso3"], z=[1]*len(subset),
            colorscale=[[0,color],[1,color]], showscale=False,
            hovertemplate="%{customdata[0]}<extra></extra>",
            customdata=subset[["hover_text","Country"]].values,
            name=cp_type_k, showlegend=False,
            marker_line_color="#111", marker_line_width=1.5,
        ))

    for i, (cp_type_k, color) in enumerate(CARBON_PRICING_COLORS.items()):
        fig_map.add_trace(go.Scattergeo(
            lat=[None], lon=[None], mode="markers",
            marker=dict(symbol="square", color=color, size=12, line=dict(width=0.5, color="#000")),
            name=CP_DISPLAY.get(cp_type_k,cp_type_k), showlegend=True, legendgroup="cp",
            legendgrouptitle_text="Carbon Pricing" if i==0 else "",
            hoverinfo="skip",
        ))

    for i, mech in enumerate(["CBAM","Tax Incentives","Fuel Mandates","Feebates","VCM project","AMC"]):
        style = MARKER_STYLES[mech]
        rows = []
        for country in f[f["mechanism_type"]==mech]["Country"].unique():
            iso3 = to_iso3(country)
            if iso3 and iso3 in CENTROIDS:
                lat, lon = CENTROIDS[iso3]
                rows.append({"country": country, "lat": lat, "lon": lon})
        if not rows: continue
        df_m = pd.DataFrame(rows)
        is_vcm = mech == "VCM project"
        fig_map.add_trace(go.Scattergeo(
            lat=df_m["lat"], lon=df_m["lon"], mode="markers",
            marker=dict(symbol=style["symbol"], color=style["color"], size=style["size"],
                        line=dict(width=0 if is_vcm else 1, color=style["color"] if is_vcm else "#000"),
                        opacity=1.0),
            text=df_m["country"], hoverinfo="skip",
            name=mech, showlegend=True, legendgroup="other",
            legendgrouptitle_text="Other Mechanisms" if i==0 else "",
        ))

    fig_map.update_layout(
        height=520, margin=dict(l=0,r=0,t=0,b=0),
        paper_bgcolor="white", dragmode=False,
        uirevision=str(region_sel)+str(type_sel)+str(country_sel),
        hoverlabel=dict(bgcolor="white", bordercolor="#ccc", font=dict(size=12,color="#1a1a2e"), align="left"),
        geo=dict(
            projection_type="equirectangular", showframe=False,
            showcoastlines=True, coastlinecolor="#333", coastlinewidth=1.5,
            showcountries=True, countrycolor="#333", countrywidth=1.5,
            showland=True, landcolor="#f5f5f5",
            showocean=False, bgcolor="white",
            lataxis=dict(range=[-60,85], showgrid=False),
            lonaxis=dict(range=[-180,180], showgrid=False),
        ),
        legend=dict(bgcolor="rgba(255,255,255,0.85)", borderwidth=0, font=dict(size=10),
                    x=0.01, y=0.01, xanchor="left", yanchor="bottom"),
    )

    col_map, col_card = st.columns([3,1.2])
    with col_map:
        clicked = st.plotly_chart(fig_map, use_container_width=True, key="map_qgis",
                                  on_select="rerun", selection_mode="points",
                                  config={"scrollZoom":False,"doubleClick":False,"displayModeBar":False})
    with col_card:
        selected_country = None
        if clicked and clicked.get("selection") and clicked["selection"].get("points"):
            pts = clicked["selection"]["points"]
            if pts:
                cd = pts[0].get("customdata")
                if cd and len(cd)>1:
                    selected_country = cd[1]
        if not selected_country and len(country_sel)==1:
            selected_country = country_sel[0]

        st.markdown("""
        <div style="font-size:16px;font-weight:800;color:#1a1a2e;margin-bottom:4px;">Country Detail</div>
        <div style="font-size:12px;color:#999;margin-bottom:12px;">Click a country to explore its mechanisms.</div>
        """, unsafe_allow_html=True)

        if selected_country:
            region_val = wide[wide["Country"]==selected_country]["Region"].iloc[0] \
                if selected_country in wide["Country"].values else "—"
            render_country_card(selected_country, region_val, long)
            render_mechanism_details(selected_country, long)
        else:
            st.markdown("""
            <div style="background:#f8f9fa;border:2px dashed #ddd;border-radius:12px;
                        padding:40px 20px;text-align:center;color:#bbb;">
                <div style="font-size:32px;margin-bottom:8px;">🗺️</div>
                <div style="font-size:13px;">Click a country on the map</div>
            </div>""", unsafe_allow_html=True)

    st.markdown("<hr style='margin:24px 0;border:none;border-top:1px solid #e8e8e8;'>", unsafe_allow_html=True)

    st.markdown("""
    <div style="font-size:28px;font-weight:900;color:#1a1a2e;margin-bottom:4px;">Summary</div>
    <div style="font-size:13px;color:#999;margin-bottom:20px;">Distribution of mechanisms across countries.</div>
    """, unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        by_type = f.groupby("mechanism_type")["Country"].nunique().reset_index(name="countries").sort_values("countries",ascending=False)
        fig_bar = go.Figure(go.Bar(
            x=by_type["mechanism_type"], y=by_type["countries"],
            marker_color=[MECH_BOX_COLORS.get(m,"#888") for m in by_type["mechanism_type"]],
            marker_line_color="#222", marker_line_width=1,
            text=by_type["countries"], textposition="outside",
            hovertemplate="%{x}: <b>%{y} countries</b><extra></extra>",
        ))
        fig_bar.update_layout(title="Countries by Mechanism Type", margin=dict(l=0,r=0,t=40,b=0),
                              paper_bgcolor="white", plot_bgcolor="white", showlegend=False,
                              xaxis=dict(tickfont=dict(size=10), showgrid=False),
                              yaxis=dict(showgrid=True, gridcolor="#f0f0f0"))
        st.plotly_chart(fig_bar, use_container_width=True, key="bar_type_summary", config={"displayModeBar":False})
    with c2:
        cp_counts = m_plot["cp_type"].value_counts().reset_index()
        cp_counts.columns = ["type","count"]
        cp_counts["label"] = cp_counts["type"].map(CP_DISPLAY).fillna(cp_counts["type"])
        fig_pie = go.Figure(go.Pie(
            labels=cp_counts["label"], values=cp_counts["count"],
            marker=dict(colors=[CARBON_PRICING_COLORS.get(t,"#888") for t in cp_counts["type"]],
                        line=dict(color="#333",width=1.5)),
            hovertemplate="<b>%{label}</b>: %{value} countries<extra></extra>",
        ))
        fig_pie.update_layout(title="Countries by Carbon Pricing Type",
                              margin=dict(l=0,r=0,t=40,b=0), paper_bgcolor="white")
        st.plotly_chart(fig_pie, use_container_width=True, key="pie_cp_summary", config={"displayModeBar":False})


# ══════════════════════════════════════════════════════════════
#  PAGE: ETS
# ══════════════════════════════════════════════════════════════
@st.cache_data
def load_ets_data():
    xl = pd.ExcelFile(FILE_PATH)
    ets = xl.parse("1.a ETS")
    ets.columns = [str(c).strip() for c in ets.columns]
    col_map = {}
    for c in ets.columns:
        cl = c.lower()
        if "instrument name" in cl:          col_map[c] = "name"
        elif cl == "jurisdiction":           col_map[c] = "country"
        elif cl == "region":                 col_map[c] = "region"
        elif "start date" in cl:             col_map[c] = "start_date"
        elif "price rate" in cl:             col_map[c] = "price"
        elif "sector coverage" in cl:        col_map[c] = "sectors"
        elif "allocation method" in cl:      col_map[c] = "allocation"
        elif "government revenue" in cl:     col_map[c] = "revenue"
        elif "cap emission" in cl:           col_map[c] = "cap"
        elif cl == "description":            col_map[c] = "description"
        elif "additional information" in cl: col_map[c] = "additional_info"
        elif cl in ("ghg","ghg coverage"):   col_map[c] = "ghg"
        elif "share of" in cl:               col_map[c] = "share"
        elif "tighten" in cl:                col_map[c] = "tightening_rate"
        elif "threshold" in cl:              col_map[c] = "threshold"
        elif "revenue recycling" in cl:      col_map[c] = "revenue_recycling"
        elif "funding program" in cl:        col_map[c] = "funding_program"
        elif cl == "source":                 col_map[c] = "source"
    ets = ets.rename(columns=col_map)
    ets = ets[ets["country"].notna()].copy()
    def parse_price(p):
        if pd.isna(p): return None
        m = _re.search(r"[\d]+\.?\d*", str(p))
        return float(m.group()) if m else None
    ets["price_num"] = ets["price"].apply(parse_price)
    ets["start_date"] = pd.to_numeric(ets["start_date"], errors="coerce")
    return ets


def page_ets():
    ets = load_ets_data()

    n_schemes   = len(ets)
    n_countries = ets["country"].nunique()
    prices      = ets["price_num"].dropna()
    avg_price   = prices.mean() if len(prices) else 0
    min_price   = prices.min() if len(prices) else 0
    max_price_v = prices.max() if len(prices) else 100
    total_rev   = "USD 69B+"

    # GHG normalised
    GHG_NORM = {
        "co2":"CO₂","co₂":"CO₂","co₂e":"CO₂","co₂ only":"CO₂",
        "including co₂":"CO₂","carbon dioxide":"CO₂",
        "ch4":"CH₄","methane":"CH₄","ch4 and n2o":"CH₄",
        "n2o":"N₂O","nitrous oxide":"N₂O",
        "hfcs":"HFCs","hydrofluorocarbons":"HFCs",
        "pfcs":"PFCs","perfluorocarbons":"PFCs",
        "sf6":"SF₆","sulfur hexafluoride":"SF₆","sf6 nf3":"SF₆",
        "nf3":"NF₃","nitrogen trifluoride":"NF₃",
        "other fluorinated ghgs":"Other F-gases",
        "and other fluorinated ghgs":"Other F-gases",
    }
    ghg_set = set()
    for v in ets["ghg"].dropna():
        for g in str(v).split(","):
            g = g.strip().split("(")[0].strip().lower()
            c = GHG_NORM.get(g)
            if c: ghg_set.add(c)
    n_ghg = len(ghg_set)

    sec_set = set()
    for v in ets["sectors"].dropna():
        for s in str(v).split(","):
            s = s.strip()
            if s and s not in ("nan",""): sec_set.add(s.split(":")[0].strip())
    n_sectors = len(sec_set)

    INVALID_FP = {"-","—","nan","NaN","","not defined","under development by SEMARAT"}
    n_funding = 0
    fp_col = next((c for c in ets.columns if "funding" in c.lower()), None)
    if fp_col:
        n_funding = int(ets[fp_col].apply(lambda x: str(x).strip() not in INVALID_FP).sum())

    # ── Hero ──────────────────────────────────────────────────────
    def divv():
        return '<div style="width:1px;height:70px;background:#e0e0e0;align-self:center;"></div>'

    def stat(number, label, sub=None):
        sub_html = f'<div style="font-size:12px;color:#aaa;margin-top:6px;">{sub}</div>' if sub else ""
        return (
            f'<div style="text-align:center;">'
            f'<div style="font-size:56px;font-weight:900;color:#1a1a2e;line-height:1;white-space:nowrap;">{number}</div>'
            f'<div style="font-size:11px;color:#999;font-weight:700;text-transform:uppercase;letter-spacing:2px;margin-top:8px;white-space:nowrap;">{label}</div>'
            f'{sub_html}</div>'
        )

    st.markdown(f"""
    <div style="padding:56px 0 48px 0;border-bottom:1px solid #e8e8e8;margin-bottom:40px;text-align:center;">
        <div style="font-size:11px;font-weight:700;color:#457b9d;letter-spacing:3px;text-transform:uppercase;margin-bottom:16px;">Carbon Pricing Instrument</div>
        <div style="font-size:56px;font-weight:900;color:#1a1a2e;line-height:1.05;margin-bottom:20px;white-space:nowrap;">Emissions Trading Systems (ETS)</div>
        <div style="font-size:16px;color:#666;max-width:780px;margin:0 auto 48px auto;line-height:1.9;">
            An Emissions Trading System is a market-based approach to controlling pollution by providing economic incentives
            for reducing emissions. Governments set a cap on total emissions and issue allowances. Companies must hold
            allowances equal to their emissions — they can trade these allowances, creating a carbon price signal.
        </div>
        <div style="display:flex;justify-content:center;align-items:center;gap:48px;flex-wrap:wrap;">
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
    </div>
    """, unsafe_allow_html=True)

    # ── Filters ───────────────────────────────────────────────────
    st.markdown("""
    <div style="font-size:28px;font-weight:900;color:#1a1a2e;margin-bottom:4px;">ETS Global Map</div>
    <div style="font-size:13px;color:#999;margin-bottom:16px;">Countries with active ETS schemes. Click a country to see details.</div>
    """, unsafe_allow_html=True)

    regions_all   = sorted(ets["region"].dropna().unique())
    countries_all = sorted(ets["country"].dropna().unique())

    if "ets_reset" not in st.session_state:
        st.session_state["ets_reset"] = 0
    rc = st.session_state["ets_reset"]

    fc1, fc2, fc3 = st.columns([2,2,0.7])
    with fc1:
        region_sel  = st.multiselect("Region", regions_all, key=f"ets_region_{rc}", placeholder="All regions")
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

    country_ets_map = f_ets.groupby("country")["name"].apply(list).to_dict()
    map_rows = [
        {"iso3": to_iso3(c), "country": c, "n_schemes": len(sl), "schemes_str": "<br>".join(f"  · {s}" for s in sl)}
        for c, sl in country_ets_map.items() if to_iso3(c)
    ]
    map_df = pd.DataFrame(map_rows) if map_rows else pd.DataFrame()

    fig_ets_map = go.Figure()
    if not map_df.empty:
        fig_ets_map.add_trace(go.Choropleth(
            locations=map_df["iso3"], z=map_df["n_schemes"],
            colorscale=[[0,"#c6dff0"],[0.5,"#457b9d"],[1,"#1a3a5e"]],
            showscale=True,
            colorbar=dict(title="Schemes", thickness=12, len=0.5, tickfont=dict(size=10)),
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>%{customdata[1]} scheme(s)<br>"
                "─────────────<br>%{customdata[2]}<extra></extra>"
            ),
            customdata=map_df[["country","n_schemes","schemes_str"]].values,
            marker_line_color="#111", marker_line_width=1.2,
        ))
    fig_ets_map.update_layout(
        height=460, margin=dict(l=0,r=0,t=0,b=0),
        paper_bgcolor="white",
        hoverlabel=dict(bgcolor="white", bordercolor="#ccc", font=dict(size=12), align="left"),
        geo=dict(
            projection_type="equirectangular", showframe=False,
            showcoastlines=True, coastlinecolor="#333", coastlinewidth=1.2,
            showcountries=True, countrycolor="#333", countrywidth=1.2,
            showland=True, landcolor="#f5f5f5",
            showocean=False, bgcolor="white",
            lataxis=dict(range=[-60,85], showgrid=False),
            lonaxis=dict(range=[-180,180], showgrid=False),
        ),
    )

    # Detail helpers
    def fval(v):
        if v is None: return "—"
        try:
            if pd.isna(v): return "—"
        except Exception:
            pass
        s = str(v).strip()
        return s if s and s not in ("nan","NaN","-","–") else "—"

    def section_title(t):
        st.markdown(
            f'<div style="font-size:11px;font-weight:800;color:#457b9d;text-transform:uppercase;'
            f'letter-spacing:2px;margin:16px 0 8px 0;border-bottom:2px solid #e8f0f8;padding-bottom:5px;">{t}</div>',
            unsafe_allow_html=True
        )

    def text_field(label, v):
        if v == "—": return
        lbl = (f'<div style="font-size:9px;font-weight:700;color:#999;text-transform:uppercase;'
               f'letter-spacing:1.5px;margin-bottom:3px;">{label}</div>') if label else ""
        st.markdown(
            f'<div style="margin-bottom:10px;">{lbl}'
            f'<div style="font-size:11px;color:#1a1a2e;line-height:1.6;background:#f7fafd;'
            f'border-radius:6px;padding:8px 10px;">{v}</div></div>',
            unsafe_allow_html=True
        )

    def bar_visual(label, pct, display_val, color="#457b9d"):
        pct_w = min(max(float(pct)*100, 2), 100)
        st.markdown(
            f'<div style="margin-bottom:12px;">'
            f'<div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:4px;">'
            f'<div style="font-size:9px;font-weight:700;color:#999;text-transform:uppercase;letter-spacing:1px;">{label}</div>'
            f'<div style="font-size:13px;font-weight:800;color:{color};">{display_val}</div>'
            f'</div>'
            f'<div style="background:#e8f0f8;border-radius:4px;height:8px;overflow:hidden;">'
            f'<div style="width:{pct_w:.1f}%;background:{color};height:100%;border-radius:4px;"></div>'
            f'</div></div>',
            unsafe_allow_html=True
        )

    col_map_ets, col_card = st.columns([3,1.5])

    with col_map_ets:
        clicked = st.plotly_chart(fig_ets_map, use_container_width=True, key="ets_map",
                                  on_select="rerun", selection_mode="points",
                                  config={"scrollZoom":False,"doubleClick":False,"displayModeBar":False})

    selected = None
    if clicked and clicked.get("selection") and clicked["selection"].get("points"):
        pts = clicked["selection"]["points"]
        if pts:
            cd = pts[0].get("customdata")
            if cd and len(cd)>0:
                selected = cd[0]
    if not selected and len(country_sel)==1:
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
            region_lbl = schemes["region"].iloc[0] if not schemes.empty else "—"
            st.markdown(f"""
            <div style="background:linear-gradient(135deg,#1a3a5e 0%,#457b9d 100%);
                        border-radius:14px;padding:20px 24px;margin-bottom:16px;color:white;">
                <div style="font-size:24px;font-weight:900;letter-spacing:1px;margin-bottom:4px;">{selected.upper()}</div>
                <div style="font-size:12px;opacity:0.8;margin-bottom:10px;">{region_lbl}</div>
                <div style="display:inline-block;background:rgba(255,255,255,0.2);border-radius:6px;
                            padding:4px 12px;font-size:11px;font-weight:700;">{len(schemes)} ETS Scheme(s)</div>
            </div>
            """, unsafe_allow_html=True)

            for scheme_idx, (_, r) in enumerate(schemes.iterrows()):
                if len(schemes) > 1:
                    st.markdown(f'<div style="background:#457b9d;color:white;font-size:12px;font-weight:800;border-radius:8px;padding:7px 14px;margin-bottom:10px;">Scheme {scheme_idx+1}: {r["name"]}</div>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<div style="font-size:15px;font-weight:800;color:#457b9d;margin-bottom:12px;">{r["name"]}</div>', unsafe_allow_html=True)

                section_title("Key Metrics")
                price_num = r.get("price_num")
                share_num = r.get("share")
                all_prices_v = f_ets["price_num"].dropna()
                max_p = all_prices_v.max() if len(all_prices_v) else 100
                pv = fval(r.get("price"))
                sv = int(r["start_date"]) if pd.notna(r.get("start_date")) else "—"
                rv = fval(r.get("revenue"))
                st.markdown(
                    f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;margin-bottom:8px;">'
                    f'<div style="background:#ddeef8;border-radius:7px;padding:9px 10px;text-align:center;">'
                    f'<div style="font-size:9px;font-weight:700;color:#457b9d;text-transform:uppercase;letter-spacing:1px;margin-bottom:3px;">Price Rate</div>'
                    f'<div style="font-size:12px;font-weight:900;color:#1a3a5e;">{pv}</div></div>'
                    f'<div style="background:#e8f0fe;border-radius:7px;padding:9px 10px;text-align:center;">'
                    f'<div style="font-size:9px;font-weight:700;color:#3a5a9e;text-transform:uppercase;letter-spacing:1px;margin-bottom:3px;">Start Date</div>'
                    f'<div style="font-size:12px;font-weight:900;color:#1a2a5e;">{sv}</div></div>'
                    f'<div style="background:#e8f5e9;border-radius:7px;padding:9px 10px;text-align:center;grid-column:span 2;">'
                    f'<div style="font-size:9px;font-weight:700;color:#3a7a3a;text-transform:uppercase;letter-spacing:1px;margin-bottom:3px;">Gov. Revenue (2024)</div>'
                    f'<div style="font-size:12px;font-weight:900;color:#1a4a1a;">{rv}</div></div>'
                    f'</div>',
                    unsafe_allow_html=True
                )
                if pd.notna(share_num):
                    try: bar_visual("Share of Jurisdiction", float(share_num), f"{float(share_num)*100:.0f}%", "#457b9d")
                    except Exception: pass
                if pd.notna(price_num) and max_p > 0:
                    try: bar_visual("Price vs Max ETS", float(price_num)/float(max_p), f"USD {float(price_num):.2f}", "#2a9d8f")
                    except Exception: pass

                section_title("Coverage")
                text_field("GHG Coverage", fval(r.get("ghg")))
                text_field("Sector Coverage", fval(r.get("sectors")))

                t1 = fval(r.get("threshold"))
                t2 = fval(r.get("description"))
                if t1 != "—" or t2 != "—":
                    section_title("Threshold")
                    text_field("Threshold", t1)
                    text_field("Description", t2)

                section_title("Cap & Allocation")
                text_field("Cap Emissions", fval(r.get("cap")))
                text_field("Tightening Rate", fval(r.get("tightening_rate")))
                text_field("Allocation Method", fval(r.get("allocation")))

                section_title("Revenue & Funding")
                text_field("Revenue Recycling", fval(r.get("revenue_recycling")))
                text_field("Funding Program", fval(r.get("funding_program")))

                ai = fval(r.get("additional_info"))
                if ai != "—":
                    section_title("Additional Information")
                    text_field("", ai)

                src = fval(r.get("source"))
                if src != "—":
                    section_title("Source")
                    for lnk in [s.strip() for s in src.split(";") if s.strip()]:
                        if lnk.startswith("http"):
                            st.markdown(f'<a href="{lnk}" target="_blank" style="font-size:10px;color:#457b9d;word-break:break-all;display:block;margin-bottom:3px;">{lnk}</a>', unsafe_allow_html=True)
                        else:
                            st.markdown(f'<div style="font-size:11px;color:#555;">{lnk}</div>', unsafe_allow_html=True)

                if scheme_idx < len(schemes) - 1:
                    st.divider()

    st.divider()

    # ── Summary Charts ────────────────────────────────────────────
    st.markdown("""
    <div style="font-size:28px;font-weight:900;color:#1a1a2e;margin-bottom:20px;">Summary</div>
    """, unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Schemes by Region")
        by_region = f_ets.groupby("region")["name"].count().reset_index(name="count")
        fig_r = go.Figure(go.Bar(
            x=by_region["region"], y=by_region["count"],
            marker_color=[REGION_COLORS_ETS.get(r,"#888") for r in by_region["region"]],
            marker_line_color="#222", marker_line_width=1,
            text=by_region["count"], textposition="outside",
            hovertemplate="%{x}: <b>%{y} schemes</b><extra></extra>",
        ))
        fig_r.update_layout(margin=dict(l=0,r=0,t=10,b=0), paper_bgcolor="white",
                            plot_bgcolor="white", showlegend=False,
                            xaxis=dict(tickfont=dict(size=10), showgrid=False),
                            yaxis=dict(showgrid=True, gridcolor="#f0f0f0"))
        st.plotly_chart(fig_r, use_container_width=True, key="ets_region_bar", config={"displayModeBar":False})
    with c2:
        st.subheader("Carbon Price Distribution")
        price_df = f_ets[f_ets["price_num"].notna()].copy().sort_values("price_num", ascending=False)
        fig_p = go.Figure(go.Bar(
            x=price_df["name"], y=price_df["price_num"],
            marker_color=[REGION_COLORS_ETS.get(r,"#888") for r in price_df["region"]],
            marker_line_color="#222", marker_line_width=1,
            text=price_df["price"].fillna("N/A"), textposition="outside", textfont=dict(size=8),
            hovertemplate="<b>%{x}</b><br>%{text}<extra></extra>",
        ))
        fig_p.update_layout(margin=dict(l=0,r=0,t=10,b=0), paper_bgcolor="white",
                            plot_bgcolor="white", showlegend=False,
                            xaxis=dict(tickfont=dict(size=8), tickangle=-45, showgrid=False),
                            yaxis=dict(title="USD", showgrid=True, gridcolor="#f0f0f0"))
        st.plotly_chart(fig_p, use_container_width=True, key="ets_price_bar", config={"displayModeBar":False})

    st.divider()

    # ── Timeline ──────────────────────────────────────────────────
    st.markdown("""
    <div style="font-size:28px;font-weight:900;color:#1a1a2e;margin-bottom:4px;">ETS Timeline</div>
    <div style="font-size:13px;color:#999;margin-bottom:16px;">Year each ETS scheme was established.</div>
    """, unsafe_allow_html=True)

    timeline_df = ets[ets["start_date"].notna()].sort_values("start_date").copy()
    fig_tl = go.Figure()
    for region, color in REGION_COLORS_ETS.items():
        sub = timeline_df[timeline_df["region"] == region]
        if sub.empty: continue
        fig_tl.add_trace(go.Scatter(
            x=sub["start_date"], y=sub["name"], mode="markers+text",
            marker=dict(size=12, color=color, line=dict(width=1, color="#222")),
            text=sub["price"].fillna("N/A"),
            textposition="middle right", textfont=dict(size=9, color="#555"),
            name=region,
            hovertemplate="<b>%{y}</b><br>%{x}<br>Price: %{text}<extra></extra>",
        ))
    fig_tl.update_layout(
        height=520, margin=dict(l=0,r=120,t=10,b=0),
        paper_bgcolor="white", plot_bgcolor="white",
        xaxis=dict(title="Year", showgrid=True, gridcolor="#f0f0f0", dtick=2),
        yaxis=dict(showgrid=False, tickfont=dict(size=10)),
        legend=dict(bgcolor="rgba(255,255,255,0.9)", bordercolor="#e0e0e0", borderwidth=1, font=dict(size=11)),
        hoverlabel=dict(bgcolor="white", bordercolor="#ccc", font=dict(size=12), align="left"),
    )
    st.plotly_chart(fig_tl, use_container_width=True, key="ets_timeline", config={"displayModeBar":False})

    st.divider()

    # ── Full Table ────────────────────────────────────────────────
    st.markdown("""
    <div style="font-size:28px;font-weight:900;color:#1a1a2e;margin-bottom:4px;">All ETS Schemes</div>
    <div style="font-size:13px;color:#999;margin-bottom:16px;">Complete list of tracked ETS schemes worldwide.</div>
    """, unsafe_allow_html=True)

    ts1, ts2 = st.columns([2,2])
    with ts1:
        search_q = st.text_input("Search by scheme or country name", placeholder="e.g. EU ETS, China...", key="ets_search")
    with ts2:
        region_tbl = st.multiselect("Filter by region", regions_all, key="ets_tbl_region", placeholder="All regions")

    display_cols = {
        "name":"Scheme","country":"Jurisdiction","region":"Region",
        "start_date":"Est.","price":"Price Rate","share":"Share",
        "revenue":"Revenue (2024)","ghg":"GHG","sectors":"Sectors",
        "allocation":"Allocation","cap":"Cap","revenue_recycling":"Rev. Recycling",
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
    if "Est." in tbl_show.columns:
        tbl_show["Est."] = tbl_show["Est."].apply(lambda x: int(x) if pd.notna(x) else "—")
    st.dataframe(tbl_show, use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════════════
#  Placeholders
# ══════════════════════════════════════════════════════════════
def page_placeholder(title, icon=""):
    st.title(f"{icon} {title}".strip())
    st.info("🚧 This page is under construction.")


# ── Router ─────────────────────────────────────────────────────
if page == "mbm":
    page_mbm()
elif page == "ets":
    page_ets()
elif page == "cbam":
    page_placeholder("CBAM")
else:
    page_mbm()
