# pages/4_IMO.py
from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

# =========================
# PAGE CONFIG
# =========================
st.set_page_config(page_title="IMO – Fleet Fuel & Emissions", layout="wide")

st.markdown(
    """
    <style>
      .block-container {padding-top: 1.1rem; padding-bottom: 2rem;}
      .kpi-card {
        border: 1px solid rgba(0,0,0,0.08);
        border-radius: 14px;
        padding: 12px 14px;
        background: rgba(255,255,255,0.02);
      }
      .muted {color: rgba(0,0,0,0.55); font-size: 0.92rem;}
      .title {font-size: 1.35rem; font-weight: 750; margin-bottom: 0.25rem;}
      .subtitle {margin-top: -0.2rem; margin-bottom: 0.6rem;}
      .small-note {font-size: 0.88rem; color: rgba(0,0,0,0.55);}
      .mono {font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;}
    </style>
    """,
    unsafe_allow_html=True,
)

# =========================
# CONSTANTS
# =========================
WKEY = "imo4_"  # ✅ unique key prefix to avoid DuplicateElementId across multipage app

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_XLSX = REPO_ROOT / "data" / "IMO.xlsx"

TOTAL_PAT = re.compile(
    r"(^|\b)(total|grand\s*total|sub\s*total|subtotal|overall\s*total)\b",
    re.IGNORECASE,
)

# =========================
# HELPERS
# =========================
def normalize_colname(c: str) -> str:
    c = str(c).strip()
    c = re.sub(r"\s+", " ", c)
    return c


def to_numeric_series(x: pd.Series) -> pd.Series:
    y = x.astype(str)
    y = y.str.replace(",", "", regex=False)
    y = y.str.replace(" ", "", regex=False)
    y = y.str.replace(r"[^\d\.\-eE+]", "", regex=True)
    return pd.to_numeric(y, errors="coerce")


def pick_first_existing_col(df: pd.DataFrame, candidates: list[str]) -> Optional[str]:
    cols = {normalize_colname(c).lower(): c for c in df.columns}
    for want in candidates:
        key = normalize_colname(want).lower()
        if key in cols:
            return cols[key]
    return None


def remove_total_rows_any_cell(df: pd.DataFrame) -> pd.DataFrame:
    """Remove any row if ANY cell contains total-ish string. Also remove fully blank rows."""
    if df.empty:
        return df
    s = df.astype(str)
    mask_total = s.apply(lambda row: row.str.contains(TOTAL_PAT, na=False).any(), axis=1)
    mask_blank = df.isna().all(axis=1) | s.apply(lambda r: (r.str.strip() == "").all(), axis=1)
    return df.loc[~(mask_total | mask_blank)].copy()


def drop_total_labels(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    """Extra safety right before groupby/plot: remove rows where specific label columns contain total-ish."""
    out = df.copy()
    for c in cols:
        if c in out.columns:
            out = out[~out[c].astype(str).str.contains(TOTAL_PAT, na=False)]
    return out


def format_compact_number(v: float) -> str:
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "—"
    abs_v = abs(float(v))
    if abs_v >= 1e12:
        return f"{v/1e12:.2f}T"
    if abs_v >= 1e9:
        return f"{v/1e9:.2f}B"
    if abs_v >= 1e6:
        return f"{v/1e6:.2f}M"
    if abs_v >= 1e3:
        return f"{v/1e3:.2f}K"
    return f"{v:,.0f}"


def add_bar_value_labels(fig, *, value_fmt: str = ",.2f", orientation: str = "v"):
    """Add numeric labels on bars."""
    if orientation == "h":
        fig.update_traces(
            texttemplate=f"%{{x:{value_fmt}}}",
            textposition="outside",
            cliponaxis=False,
        )
    else:
        fig.update_traces(
            texttemplate=f"%{{y:{value_fmt}}}",
            textposition="outside",
            cliponaxis=False,
        )
    fig.update_layout(uniformtext_minsize=10, uniformtext_mode="hide")
    return fig


@st.cache_data(show_spinner=False)
def load_sheet(path: Path, sheet_name: Optional[str]) -> pd.DataFrame:
    df = pd.read_excel(path, sheet_name=sheet_name)
    df.columns = [normalize_colname(c) for c in df.columns]
    df = remove_total_rows_any_cell(df)  # ✅ remove "Total" rows early
    return df


# =========================
# HEADER
# =========================
st.markdown('<div class="title">IMO – Fleet Fuel & Emissions</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="muted subtitle">Baris berlabel <b>Total/Grand Total/Subtotal</b> akan dibuang (termasuk “Total (… )”).</div>',
    unsafe_allow_html=True,
)

# =========================
# SIDEBAR
# =========================
with st.sidebar:
    st.header("Data source")

    use_default = st.checkbox("Use default path", value=True, key=WKEY + "use_default")
    if use_default:
        xlsx_path = DEFAULT_XLSX
        st.caption(f"Default: `{xlsx_path.as_posix()}`")
    else:
        manual_path = st.text_input("Excel path", value=str(DEFAULT_XLSX), key=WKEY + "manual_path")
        xlsx_path = Path(manual_path)

    if not xlsx_path.exists():
        st.error("File tidak ditemukan. Pastikan Excel ada di path tersebut.")
        st.stop()

    try:
        xl = pd.ExcelFile(xlsx_path)
        sheets = xl.sheet_names
    except Exception as e:
        st.error(f"Gagal baca Excel: {e}")
        st.stop()

    sheet_name = st.selectbox("Sheet", options=sheets, index=0, key=WKEY + "sheet_name")

    st.divider()
    st.subheader("Chart options")
    top_n = st.slider("Top-N (bar chart)", 5, 40, 15, key=WKEY + "top_n")
    label_decimals = st.selectbox("Decimals on labels", [0, 1, 2, 3], index=2, key=WKEY + "label_decimals")
    show_table = st.checkbox("Show cleaned table", value=False, key=WKEY + "show_table")

# =========================
# LOAD
# =========================
with st.spinner("Loading & cleaning data (remove Total rows)…"):
    df = load_sheet(xlsx_path, sheet_name)

if df.empty:
    st.warning("Sheet kosong setelah cleaning. Bisa jadi isinya hanya baris Total/Subtotal.")
    st.stop()

# =========================
# DETECT COLUMNS
# =========================
fuel_col = pick_first_existing_col(df, ["Fuel", "Fuel type", "Fuel Type", "Fuel Category"])
ship_col = pick_first_existing_col(df, ["Ship type", "Ship Type", "Vessel type", "Vessel Type"])
year_col = pick_first_existing_col(df, ["Year", "Reporting year", "Reporting Year"])

value_col = pick_first_existing_col(
    df,
    ["CO2 emissions", "CO₂ emissions", "CO2", "CO2e", "Emissions", "Fuel consumption", "Consumption", "Amount", "Value"],
)
ships_count_col = pick_first_existing_col(df, ["Number of ships", "No. of ships", "Ships", "Ship count", "Count"])

if value_col is None:
    numeric_candidates = []
    for c in df.columns:
        s = to_numeric_series(df[c])
        if s.notna().mean() > 0.6:
            numeric_candidates.append(c)
    if numeric_candidates:
        value_col = numeric_candidates[0]

# =========================
# FILTERS
# =========================
df_f = df.copy()
fcols = st.columns(4)

with fcols[0]:
    if year_col:
        years = sorted([y for y in pd.unique(df_f[year_col]) if str(y).strip() != ""])
        default_years = years[-1:] if years else []
        sel_years = st.multiselect("Year", years, default=default_years, key=WKEY + "sel_years")
        if sel_years:
            df_f = df_f[df_f[year_col].isin(sel_years)]
    else:
        st.caption("Year: (kolom tidak terdeteksi)")

with fcols[1]:
    if ship_col:
        ships = sorted([s for s in pd.unique(df_f[ship_col]) if str(s).strip() != ""])
        sel_ships = st.multiselect("Ship type", ships, default=[], key=WKEY + "sel_ships")
        if sel_ships:
            df_f = df_f[df_f[ship_col].isin(sel_ships)]
    else:
        st.caption("Ship type: (kolom tidak terdeteksi)")

with fcols[2]:
    if fuel_col:
        fuels = sorted([f for f in pd.unique(df_f[fuel_col]) if str(f).strip() != ""])
        sel_fuels = st.multiselect("Fuel", fuels, default=[], key=WKEY + "sel_fuels")
        if sel_fuels:
            df_f = df_f[df_f[fuel_col].isin(sel_fuels)]
    else:
        st.caption("Fuel: (kolom tidak terdeteksi)")

with fcols[3]:
    st.caption("Detected columns")
    st.write(
        {
            "ship_col": ship_col or "—",
            "fuel_col": fuel_col or "—",
            "year_col": year_col or "—",
            "value_col": value_col or "—",
            "ships_count_col": ships_count_col or "—",
        }
    )

# =========================
# PREVIEW
# =========================
st.markdown("### Data preview (cleaned)")
st.caption("Baris yang mengandung 'total' (di kolom mana pun) sudah dibuang.")
st.dataframe(df_f.head(25), use_container_width=True)

# =========================
# KPIs
# =========================
st.markdown("### KPIs")
kcols = st.columns(4)

kcols[1].markdown(
    f'<div class="kpi-card"><div class="muted">Rows (after cleaning)</div>'
    f'<div class="mono" style="font-size:1.45rem;font-weight:800;">{len(df_f):,}</div></div>',
    unsafe_allow_html=True,
)

if value_col:
    vv = to_numeric_series(df_f[value_col])
    total_value = float(np.nansum(vv.values)) if vv.notna().any() else np.nan
    kcols[0].markdown(
        f'<div class="kpi-card"><div class="muted">Total ({value_col})</div>'
        f'<div class="mono" style="font-size:1.45rem;font-weight:800;">{format_compact_number(total_value)}</div></div>',
        unsafe_allow_html=True,
    )
else:
    kcols[0].info("Total (value): —")

if fuel_col:
    kcols[2].markdown(
        f'<div class="kpi-card"><div class="muted">Unique fuels</div>'
        f'<div class="mono" style="font-size:1.45rem;font-weight:800;">{df_f[fuel_col].nunique():,}</div></div>',
        unsafe_allow_html=True,
    )
else:
    kcols[2].info("Unique fuels: —")

if ship_col:
    kcols[3].markdown(
        f'<div class="kpi-card"><div class="muted">Unique ship types</div>'
        f'<div class="mono" style="font-size:1.45rem;font-weight:800;">{df_f[ship_col].nunique():,}</div></div>',
        unsafe_allow_html=True,
    )
else:
    kcols[3].info("Unique ship types: —")

st.divider()

# =========================
# CHARTS
# =========================
st.markdown("### Charts")

dec = int(label_decimals)
value_fmt = f",.{dec}f"

# Chart 1: Top ship types by emissions/value
if ship_col and value_col:
    st.markdown(f"#### Top {top_n} ship types by {value_col}")

    df_plot = drop_total_labels(df_f, [ship_col])
    df_plot["_value"] = to_numeric_series(df_plot[value_col])
    df_plot = df_plot[df_plot["_value"].notna()]

    agg = df_plot.groupby(ship_col, dropna=False)["_value"].sum().reset_index()
    agg = drop_total_labels(agg, [ship_col])  # ✅ guarantee no Total (xxx)
    agg = agg.sort_values("_value", ascending=False).head(top_n)
    agg = agg.sort_values("_value", ascending=True)

    fig = px.bar(
        agg,
        x="_value",
        y=ship_col,
        orientation="h",
        title=f"Top {top_n} ship types by {value_col}",
    )
    fig.update_layout(xaxis_title=value_col, yaxis_title="Ship type")
    add_bar_value_labels(fig, value_fmt=value_fmt, orientation="h")
    st.plotly_chart(fig, use_container_width=True, key=WKEY + "fig_ship_value")

# Chart 2: Top fuels by emissions/value
if fuel_col and value_col:
    st.markdown(f"#### Top {top_n} fuels by {value_col}")

    df_plot = drop_total_labels(df_f, [fuel_col])
    df_plot["_value"] = to_numeric_series(df_plot[value_col])
    df_plot = df_plot[df_plot["_value"].notna()]

    agg = df_plot.groupby(fuel_col, dropna=False)["_value"].sum().reset_index()
    agg = drop_total_labels(agg, [fuel_col])
    agg = agg.sort_values("_value", ascending=False).head(top_n)

    fig = px.bar(agg, x=fuel_col, y="_value", title=f"Top {top_n} fuels by {value_col}")
    fig.update_layout(xaxis_title="Fuel", yaxis_title=value_col)
    add_bar_value_labels(fig, value_fmt=value_fmt, orientation="v")
    st.plotly_chart(fig, use_container_width=True, key=WKEY + "fig_fuel_value")

# Chart 3: Top ship types by number of ships
if ship_col and ships_count_col:
    st.markdown(f"#### Top {top_n} ship types by {ships_count_col}")

    df_plot = drop_total_labels(df_f, [ship_col])
    df_plot["_ships"] = to_numeric_series(df_plot[ships_count_col])
    df_plot = df_plot[df_plot["_ships"].notna()]

    agg = df_plot.groupby(ship_col, dropna=False)["_ships"].sum().reset_index()
    agg = drop_total_labels(agg, [ship_col])
    agg = agg.sort_values("_ships", ascending=False).head(top_n)
    agg = agg.sort_values("_ships", ascending=True)

    fig = px.bar(
        agg,
        x="_ships",
        y=ship_col,
        orientation="h",
        title=f"Top {top_n} ship types by {ships_count_col}",
    )
    fig.update_layout(xaxis_title=ships_count_col, yaxis_title="Ship type")
    add_bar_value_labels(fig, value_fmt=",.0f", orientation="h")
    st.plotly_chart(fig, use_container_width=True, key=WKEY + "fig_ship_count")

# Chart 4: Trend over time
if year_col and value_col:
    st.markdown(f"#### Trend: {value_col} over time")

    df_plot = df_f.copy()
    cols_to_clean = [c for c in [ship_col, fuel_col, year_col] if c]
    df_plot = drop_total_labels(df_plot, cols_to_clean)

    df_plot["_value"] = to_numeric_series(df_plot[value_col])
    df_plot = df_plot[df_plot["_value"].notna()]

    yy = df_plot[year_col].astype(str).str.extract(r"(\d{4})")[0]
    df_plot["_year"] = pd.to_numeric(yy, errors="coerce")
    df_plot = df_plot[df_plot["_year"].notna()]

    trend = df_plot.groupby("_year")["_value"].sum().sort_index().reset_index()

    if trend.empty:
        st.info("Tidak ada year valid (4-digit) untuk bikin trend.")
    else:
        fig = px.line(trend, x="_year", y="_value", markers=True, title=f"{value_col} over time")
        fig.update_layout(xaxis_title="Year", yaxis_title=value_col)
        st.plotly_chart(fig, use_container_width=True, key=WKEY + "fig_trend")

# =========================
# OPTIONAL TABLE
# =========================
if show_table:
    st.divider()
    st.markdown("### Full cleaned table")
    st.caption("Sudah termasuk removal baris 'Total/Grand Total/Subtotal' otomatis.")
    st.dataframe(df_f, use_container_width=True)

# =========================
# FOOTNOTE
# =========================
st.markdown(
    """
<div class="small-note">
<b>Why “Total” can leak?</b> Kadang “Total (… )” ada di kolom kategori (mis. Ship type), jadi meskipun data dibersihkan awal,
label itu bisa muncul lagi saat agregasi. File ini melakukan 2 layer cleaning: <span class="mono">remove_total_rows_any_cell</span> saat load
+ <span class="mono">drop_total_labels</span> tepat sebelum groupby/plot.
</div>
""",
    unsafe_allow_html=True,
)
# =========================
# CONSTANTS
# =========================
REPO_ROOT = Path(__file__).resolve().parents[1]  # .../pages/ -> repo root
DEFAULT_XLSX = REPO_ROOT / "data" / "IMO.xlsx"

# Detect any "total-ish" label. This catches: "Total", "Total (...)", "Grand Total", "Subtotal", etc.
TOTAL_PAT = re.compile(r"(^|\b)(total|grand\s*total|sub\s*total|subtotal|overall\s*total)\b", re.IGNORECASE)

# =========================
# HELPERS
# =========================
def normalize_colname(c: str) -> str:
    c = str(c).strip()
    c = re.sub(r"\s+", " ", c)
    return c

def to_numeric_series(x: pd.Series) -> pd.Series:
    """
    Robust numeric conversion: strips commas/spaces, keeps digits, dot, minus, exponent.
    """
    y = x.astype(str)
    y = y.str.replace(",", "", regex=False)
    y = y.str.replace(" ", "", regex=False)
    y = y.str.replace(r"[^\d\.\-eE+]", "", regex=True)
    return pd.to_numeric(y, errors="coerce")

def pick_first_existing_col(df: pd.DataFrame, candidates: list[str]) -> Optional[str]:
    cols = {normalize_colname(c).lower(): c for c in df.columns}
    for want in candidates:
        key = normalize_colname(want).lower()
        if key in cols:
            return cols[key]
    return None

def remove_total_rows_any_cell(df: pd.DataFrame) -> pd.DataFrame:
    """
    Removes any row if ANY cell contains 'total-ish' (case-insensitive).
    Also removes fully blank rows.
    """
    if df.empty:
        return df
    s = df.astype(str)

    mask_total = s.apply(lambda row: row.str.contains(TOTAL_PAT, na=False).any(), axis=1)
    mask_blank = df.isna().all(axis=1) | s.apply(lambda r: (r.str.strip() == "").all(), axis=1)

    return df.loc[~(mask_total | mask_blank)].copy()

def drop_total_labels(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    """
    Extra safety: remove rows where specified label columns contain 'total-ish'.
    Use this right before groupby/plot so 'Total (...)' never leaks into charts.
    """
    out = df.copy()
    for c in cols:
        if c in out.columns:
            out = out[~out[c].astype(str).str.contains(TOTAL_PAT, na=False)]
    return out

def format_compact_number(v: float) -> str:
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "—"
    abs_v = abs(float(v))
    if abs_v >= 1e12:
        return f"{v/1e12:.2f}T"
    if abs_v >= 1e9:
        return f"{v/1e9:.2f}B"
    if abs_v >= 1e6:
        return f"{v/1e6:.2f}M"
    if abs_v >= 1e3:
        return f"{v/1e3:.2f}K"
    return f"{v:,.0f}"

def add_bar_value_labels(fig, *, value_fmt: str = ",.2f", orientation: str = "v"):
    """
    Adds numeric labels on bars.
    - orientation='h' for horizontal, 'v' for vertical.
    """
    if orientation == "h":
        fig.update_traces(
            texttemplate=f"%{{x:{value_fmt}}}",
            textposition="outside",
            cliponaxis=False,
        )
    else:
        fig.update_traces(
            texttemplate=f"%{{y:{value_fmt}}}",
            textposition="outside",
            cliponaxis=False,
        )
    fig.update_layout(uniformtext_minsize=10, uniformtext_mode="hide")
    return fig

@st.cache_data(show_spinner=False)
def load_sheet(path: Path, sheet_name: Optional[str]) -> pd.DataFrame:
    df = pd.read_excel(path, sheet_name=sheet_name)
    df.columns = [normalize_colname(c) for c in df.columns]
    df = remove_total_rows_any_cell(df)  # ✅ remove Total rows early
    return df

# =========================
# UI: HEADER
# =========================
st.markdown('<div class="title">IMO – Fleet Fuel & Emissions</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="muted subtitle">Semua baris berlabel <b>Total / Grand Total / Subtotal</b> akan dibuang (termasuk “Total (… )”).</div>',
    unsafe_allow_html=True,
)

# =========================
# SIDEBAR
# =========================
with st.sidebar:
    st.header("Data source")

    use_default = st.checkbox("Use default path", value=True)
    if use_default:
        xlsx_path = DEFAULT_XLSX
        st.caption(f"Default: `{xlsx_path.as_posix()}`")
    else:
        manual_path = st.text_input("Excel path", value=str(DEFAULT_XLSX))
        xlsx_path = Path(manual_path)

    if not xlsx_path.exists():
        st.error("File tidak ditemukan. Pastikan Excel ada di path tersebut.")
        st.stop()

    try:
        xl = pd.ExcelFile(xlsx_path)
        sheets = xl.sheet_names
    except Exception as e:
        st.error(f"Gagal baca Excel: {e}")
        st.stop()

    sheet_name = st.selectbox("Sheet", options=sheets, index=0)

    st.divider()
    st.subheader("Chart options")
    top_n = st.slider("Top-N (bar chart)", 5, 40, 15)
    label_decimals = st.selectbox("Decimals on labels", [0, 1, 2, 3], index=2)
    show_table = st.checkbox("Show cleaned table", value=False)

# =========================
# LOAD
# =========================
with st.spinner("Loading & cleaning data (remove Total rows)…"):
    df = load_sheet(xlsx_path, sheet_name)

if df.empty:
    st.warning("Sheet kosong setelah cleaning. Bisa jadi isinya hanya baris Total/Subtotal.")
    st.stop()

# =========================
# AUTO-DETECT COLUMNS
# =========================
fuel_col = pick_first_existing_col(df, ["Fuel", "Fuel type", "Fuel Type", "Fuel Category"])
ship_col = pick_first_existing_col(df, ["Ship type", "Ship Type", "Vessel type", "Vessel Type"])
year_col = pick_first_existing_col(df, ["Year", "Reporting year", "Reporting Year"])

# Try detect common numeric columns (emissions, number of ships, consumption, etc.)
value_col = pick_first_existing_col(df, ["CO2 emissions", "CO₂ emissions", "CO2", "CO2e", "Emissions", "Fuel consumption", "Consumption", "Amount", "Value"])
ships_count_col = pick_first_existing_col(df, ["Number of ships", "No. of ships", "Ships", "Ship count", "Count"])

if value_col is None:
    # fallback: find first mostly numeric column
    numeric_candidates = []
    for c in df.columns:
        s = to_numeric_series(df[c])
        if s.notna().mean() > 0.6:
            numeric_candidates.append(c)
    if numeric_candidates:
        value_col = numeric_candidates[0]

# =========================
# FILTERS
# =========================
df_f = df.copy()
fcols = st.columns(4)

with fcols[0]:
    if year_col:
        years = sorted([y for y in pd.unique(df_f[year_col]) if str(y).strip() != ""])
        sel_years = st.multiselect("Year", years, default=years[-1:] if years else [])
        if sel_years:
            df_f = df_f[df_f[year_col].isin(sel_years)]
    else:
        st.caption("Year: (kolom tidak terdeteksi)")

with fcols[1]:
    if ship_col:
        ships = sorted([s for s in pd.unique(df_f[ship_col]) if str(s).strip() != ""])
        sel_ships = st.multiselect("Ship type", ships, default=[])
        if sel_ships:
            df_f = df_f[df_f[ship_col].isin(sel_ships)]
    else:
        st.caption("Ship type: (kolom tidak terdeteksi)")

with fcols[2]:
    if fuel_col:
        fuels = sorted([f for f in pd.unique(df_f[fuel_col]) if str(f).strip() != ""])
        sel_fuels = st.multiselect("Fuel", fuels, default=[])
        if sel_fuels:
            df_f = df_f[df_f[fuel_col].isin(sel_fuels)]
    else:
        st.caption("Fuel: (kolom tidak terdeteksi)")

with fcols[3]:
    st.caption("Detected columns")
    st.write(
        {
            "ship_col": ship_col or "—",
            "fuel_col": fuel_col or "—",
            "year_col": year_col or "—",
            "value_col": value_col or "—",
            "ships_count_col": ships_count_col or "—",
        }
    )

# =========================
# PREVIEW
# =========================
st.markdown("### Data preview (cleaned)")
st.caption("Baris yang mengandung 'total' (di kolom mana pun) sudah dibuang.")
st.dataframe(df_f.head(25), use_container_width=True)

# =========================
# KPIs
# =========================
st.markdown("### KPIs")
kcols = st.columns(4)

n_rows = int(len(df_f))
kcols[1].markdown(
    f'<div class="kpi-card"><div class="muted">Rows (after cleaning)</div>'
    f'<div class="mono" style="font-size:1.45rem;font-weight:800;">{n_rows:,}</div></div>',
    unsafe_allow_html=True,
)

if fuel_col:
    kcols[2].markdown(
        f'<div class="kpi-card"><div class="muted">Unique fuels</div>'
        f'<div class="mono" style="font-size:1.45rem;font-weight:800;">{df_f[fuel_col].nunique():,}</div></div>',
        unsafe_allow_html=True,
    )
else:
    kcols[2].info("Unique fuels: —")

if ship_col:
    kcols[3].markdown(
        f'<div class="kpi-card"><div class="muted">Unique ship types</div>'
        f'<div class="mono" style="font-size:1.45rem;font-weight:800;">{df_f[ship_col].nunique():,}</div></div>',
        unsafe_allow_html=True,
    )
else:
    kcols[3].info("Unique ship types: —")

if value_col:
    vv = to_numeric_series(df_f[value_col])
    total_value = float(np.nansum(vv.values)) if vv.notna().any() else np.nan
    kcols[0].markdown(
        f'<div class="kpi-card"><div class="muted">Total ({value_col})</div>'
        f'<div class="mono" style="font-size:1.45rem;font-weight:800;">{format_compact_number(total_value)}</div></div>',
        unsafe_allow_html=True,
    )
else:
    kcols[0].info("Total (value): —")

st.divider()

# =========================
# CHARTS
# =========================
st.markdown("### Charts")

dec = int(label_decimals)
value_fmt = f",.{dec}f"

# --- Chart A: Top ship types by emissions/value (horizontal bar + labels)
if ship_col and value_col:
    st.markdown(f"#### Top {top_n} ship types by {value_col}")

    df_plot = df_f.copy()
    df_plot = drop_total_labels(df_plot, [ship_col])  # ✅ safety
    df_plot["_value"] = to_numeric_series(df_plot[value_col])
    df_plot = df_plot[df_plot["_value"].notna()]

    agg = (
        df_plot.groupby(ship_col, dropna=False)["_value"]
        .sum()
        .reset_index()
    )
    agg = drop_total_labels(agg, [ship_col])  # ✅ safety again
    agg = agg.sort_values("_value", ascending=False).head(top_n)
    agg = agg.sort_values("_value", ascending=True)  # for nicer horizontal order

    fig = px.bar(
        agg,
        x="_value",
        y=ship_col,
        orientation="h",
        title=f"Top {top_n} ship types by {value_col}",
    )
    fig.update_layout(xaxis_title=value_col, yaxis_title="Ship type")
    add_bar_value_labels(fig, value_fmt=value_fmt, orientation="h")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Chart ship types: butuh kolom Ship type + numeric (mis. CO2 emissions).")

# --- Chart B: Top fuels by emissions/value (vertical bar + labels)
if fuel_col and value_col:
    st.markdown(f"#### Top {top_n} fuels by {value_col}")

    df_plot = df_f.copy()
    df_plot = drop_total_labels(df_plot, [fuel_col])  # ✅ safety
    df_plot["_value"] = to_numeric_series(df_plot[value_col])
    df_plot = df_plot[df_plot["_value"].notna()]

    agg = (
        df_plot.groupby(fuel_col, dropna=False)["_value"]
        .sum()
        .reset_index()
    )
    agg = drop_total_labels(agg, [fuel_col])  # ✅ safety
    agg = agg.sort_values("_value", ascending=False).head(top_n)

    fig = px.bar(
        agg,
        x=fuel_col,
        y="_value",
        title=f"Top {top_n} fuels by {value_col}",
    )
    fig.update_layout(xaxis_title="Fuel", yaxis_title=value_col)
    add_bar_value_labels(fig, value_fmt=value_fmt, orientation="v")
    st.plotly_chart(fig, use_container_width=True)

# --- Chart C: Number of ships by ship type (if available)
if ship_col and ships_count_col:
    st.markdown(f"#### Top {top_n} ship types by {ships_count_col}")

    df_plot = df_f.copy()
    df_plot = drop_total_labels(df_plot, [ship_col])  # ✅ safety
    df_plot["_ships"] = to_numeric_series(df_plot[ships_count_col])
    df_plot = df_plot[df_plot["_ships"].notna()]

    agg = (
        df_plot.groupby(ship_col, dropna=False)["_ships"]
        .sum()
        .reset_index()
    )
    agg = drop_total_labels(agg, [ship_col])  # ✅ safety
    agg = agg.sort_values("_ships", ascending=False).head(top_n)
    agg = agg.sort_values("_ships", ascending=True)

    fig = px.bar(
        agg,
        x="_ships",
        y=ship_col,
        orientation="h",
        title=f"Top {top_n} ship types by {ships_count_col}",
    )
    fig.update_layout(xaxis_title=ships_count_col, yaxis_title="Ship type")
    add_bar_value_labels(fig, value_fmt=",.0f", orientation="h")
    st.plotly_chart(fig, use_container_width=True)

# --- Chart D: Trend by year (if year exists and value exists)
if year_col and value_col:
    st.markdown(f"#### Trend: {value_col} over time")

    df_plot = df_f.copy()
    # remove totals just in case year column is weird; also remove label cols if exist
    cols_to_clean = [c for c in [ship_col, fuel_col, year_col] if c]
    df_plot = drop_total_labels(df_plot, cols_to_clean)

    df_plot["_value"] = to_numeric_series(df_plot[value_col])
    df_plot = df_plot[df_plot["_value"].notna()]

    yy = df_plot[year_col].astype(str).str.extract(r"(\d{4})")[0]
    df_plot["_year"] = pd.to_numeric(yy, errors="coerce")
    df_plot = df_plot[df_plot["_year"].notna()]

    trend = (
        df_plot.groupby("_year")["_value"]
        .sum()
        .sort_index()
        .reset_index()
    )

    if trend.empty:
        st.info("Tidak ada year valid (4-digit) untuk bikin trend.")
    else:
        fig = px.line(trend, x="_year", y="_value", markers=True, title=f"{value_col} over time")
        fig.update_layout(xaxis_title="Year", yaxis_title=value_col)
        st.plotly_chart(fig, use_container_width=True)

# =========================
# OPTIONAL TABLE
# =========================
if show_table:
    st.divider()
    st.markdown("### Full cleaned table")
    st.caption("Sudah termasuk removal baris 'Total/Grand Total/Subtotal' otomatis.")
    st.dataframe(df_f, use_container_width=True)

# =========================
# FOOTNOTE
# =========================
st.markdown(
    """
<div class="small-note">
<b>Anti-Total Guarantee:</b>
1) Saat load: buang baris jika <i>sel mana pun</i> mengandung <span class="mono">total</span>/<span class="mono">grand total</span>/<span class="mono">subtotal</span>.
2) Saat chart: buang lagi jika label kolom kategori (Ship type / Fuel) mengandung <span class="mono">Total (…)</span>.
Jadi bar “Total (211,137,491)” tidak akan muncul lagi.
</div>
""",
    unsafe_allow_html=True,
)
# =========================
# CONSTANTS
# =========================
REPO_ROOT = Path(__file__).resolve().parents[1]  # .../pages/ -> repo root
DEFAULT_XLSX = REPO_ROOT / "data" / "IMO.xlsx"

TOTAL_REGEX = re.compile(r"(^|\b)(total|grand total|subtotal|overall total|all\s*total)\b", re.IGNORECASE)

# =========================
# HELPERS
# =========================
def normalize_colname(c: str) -> str:
    c = str(c).strip()
    c = re.sub(r"\s+", " ", c)
    return c

def remove_total_rows(df: pd.DataFrame) -> pd.DataFrame:
    """
    Removes any row that contains a 'total-ish' label in ANY cell.
    This prevents double counting in charts/tables.
    """
    if df.empty:
        return df

    # Convert to string (safe) and scan row-wise
    s = df.astype(str)
    mask_total = s.apply(lambda row: row.str.contains(TOTAL_REGEX, na=False).any(), axis=1)

    # Also remove rows that are entirely NaN/blank
    mask_blank = df.isna().all(axis=1) | (s.apply(lambda r: (r.str.strip() == "").all(), axis=1))

    cleaned = df.loc[~(mask_total | mask_blank)].copy()
    return cleaned

def to_numeric_series(x: pd.Series) -> pd.Series:
    """
    Robust numeric conversion: strips commas, spaces, non-numeric suffixes.
    """
    if x is None:
        return x
    y = x.astype(str)
    y = y.str.replace(",", "", regex=False)
    y = y.str.replace(" ", "", regex=False)
    y = y.str.replace(r"[^\d\.\-eE+]", "", regex=True)
    return pd.to_numeric(y, errors="coerce")

def pick_first_existing_col(df: pd.DataFrame, candidates: list[str]) -> Optional[str]:
    cols = {normalize_colname(c).lower(): c for c in df.columns}
    for want in candidates:
        key = normalize_colname(want).lower()
        if key in cols:
            return cols[key]
    return None

@st.cache_data(show_spinner=False)
def load_sheet(path: Path, sheet_name: Optional[str]) -> pd.DataFrame:
    df = pd.read_excel(path, sheet_name=sheet_name)
    df.columns = [normalize_colname(c) for c in df.columns]
    df = remove_total_rows(df)  # ✅ IMPORTANT: remove Total rows everywhere
    return df

def format_compact_number(v: float) -> str:
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "—"
    abs_v = abs(float(v))
    if abs_v >= 1e12:
        return f"{v/1e12:.2f}T"
    if abs_v >= 1e9:
        return f"{v/1e9:.2f}B"
    if abs_v >= 1e6:
        return f"{v/1e6:.2f}M"
    if abs_v >= 1e3:
        return f"{v/1e3:.2f}K"
    return f"{v:,.0f}"

# =========================
# UI: HEADER
# =========================
st.markdown('<div class="title">IMO – Fleet Fuel & Emissions</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="muted subtitle">Halaman ini otomatis <b>menghapus semua baris berlabel Total/Grand Total/Subtotal</b> supaya tidak double-count.</div>',
    unsafe_allow_html=True,
)

# =========================
# SIDEBAR: FILE + SHEET
# =========================
with st.sidebar:
    st.header("Data source")

    # Let user override file path if needed
    use_default = st.checkbox("Use default path", value=True)
    if use_default:
        xlsx_path = DEFAULT_XLSX
        st.caption(f"Default: `{xlsx_path.as_posix()}`")
    else:
        manual_path = st.text_input("Excel path", value=str(DEFAULT_XLSX))
        xlsx_path = Path(manual_path)

    if not xlsx_path.exists():
        st.error("File tidak ditemukan. Pastikan Excel ada di path tersebut.")
        st.stop()

    # List sheets
    try:
        xl = pd.ExcelFile(xlsx_path)
        sheets = xl.sheet_names
    except Exception as e:
        st.error(f"Gagal baca Excel: {e}")
        st.stop()

    sheet_name = st.selectbox("Sheet", options=sheets, index=0)
    st.divider()

    st.subheader("Chart options")
    top_n = st.slider("Top-N categories (untuk bar chart)", 5, 40, 15)
    show_table = st.checkbox("Show cleaned data table", value=False)

# =========================
# LOAD DATA
# =========================
with st.spinner("Loading & cleaning data (remove Total rows)…"):
    df = load_sheet(xlsx_path, sheet_name)

# =========================
# QUICK DATA HEALTH + PREVIEW
# =========================
st.markdown("### Data preview (cleaned)")
st.caption("Catatan: Baris yang mengandung kata 'total' di kolom mana pun sudah dibuang.")
st.dataframe(df.head(30), use_container_width=True)

if df.empty:
    st.warning("Sheet ini kosong setelah cleaning. Bisa jadi isinya hanya baris Total/Subtotal.")
    st.stop()

# =========================
# TRY TO AUTO-DETECT COMMON COLUMNS
# =========================
# We’ll try to detect common fields. If not found, we’ll still show a generic explorer.
fuel_col = pick_first_existing_col(df, ["Fuel", "Fuel type", "Fuel Type", "Fuel Category"])
ship_col = pick_first_existing_col(df, ["Ship type", "Ship Type", "Vessel type", "Vessel Type"])
year_col = pick_first_existing_col(df, ["Year", "Reporting year", "Reporting Year"])
value_col = pick_first_existing_col(df, ["Value", "Amount", "Consumption", "Fuel consumption", "Emissions", "CO2", "CO2e", "Tonnes"])

# If there are multiple numeric columns and value_col not found, pick the first numeric-like column
if value_col is None:
    numeric_candidates = []
    for c in df.columns:
        s = to_numeric_series(df[c])
        if s.notna().mean() > 0.6:  # mostly numeric
            numeric_candidates.append(c)
    if numeric_candidates:
        value_col = numeric_candidates[0]

# =========================
# FILTERS (ONLY IF COLUMNS EXIST)
# =========================
filters = st.columns(4)
df_f = df.copy()

with filters[0]:
    if year_col:
        years = sorted([y for y in pd.unique(df_f[year_col]) if str(y).strip() != ""])
        sel_years = st.multiselect("Year", years, default=years[-1:] if years else [])
        if sel_years:
            df_f = df_f[df_f[year_col].isin(sel_years)]
    else:
        st.caption("Year: (kolom tidak terdeteksi)")

with filters[1]:
    if ship_col:
        ships = sorted([s for s in pd.unique(df_f[ship_col]) if str(s).strip() != ""])
        sel_ships = st.multiselect("Ship type", ships, default=[])
        if sel_ships:
            df_f = df_f[df_f[ship_col].isin(sel_ships)]
    else:
        st.caption("Ship type: (kolom tidak terdeteksi)")

with filters[2]:
    if fuel_col:
        fuels = sorted([f for f in pd.unique(df_f[fuel_col]) if str(f).strip() != ""])
        sel_fuels = st.multiselect("Fuel", fuels, default=[])
        if sel_fuels:
            df_f = df_f[df_f[fuel_col].isin(sel_fuels)]
    else:
        st.caption("Fuel: (kolom tidak terdeteksi)")

with filters[3]:
    if value_col:
        st.caption(f"Value column: `{value_col}`")
    else:
        st.warning("Tidak ada kolom numeric/value yang terdeteksi. Grafik akan dinonaktifkan.")

# =========================
# KPIs (IF VALUE AVAILABLE)
# =========================
st.markdown("### KPIs")
kcols = st.columns(4)

if value_col:
    v = to_numeric_series(df_f[value_col])
    total_value = float(np.nansum(v.values)) if v.notna().any() else np.nan
    n_rows = int(len(df_f))
    n_fuels = int(df_f[fuel_col].nunique()) if fuel_col else np.nan
    n_ships = int(df_f[ship_col].nunique()) if ship_col else np.nan

    kcols[0].markdown(
        f'<div class="kpi-card"><div class="muted">Total ({value_col})</div>'
        f'<div class="mono" style="font-size:1.45rem;font-weight:800;">{format_compact_number(total_value)}</div></div>',
        unsafe_allow_html=True,
    )
    kcols[1].markdown(
        f'<div class="kpi-card"><div class="muted">Rows (after cleaning)</div>'
        f'<div class="mono" style="font-size:1.45rem;font-weight:800;">{n_rows:,}</div></div>',
        unsafe_allow_html=True,
    )
    kcols[2].markdown(
        f'<div class="kpi-card"><div class="muted">Unique fuels</div>'
        f'<div class="mono" style="font-size:1.45rem;font-weight:800;">{("—" if np.isnan(n_fuels) else f"{n_fuels:,}")}</div></div>',
        unsafe_allow_html=True,
    )
    kcols[3].markdown(
        f'<div class="kpi-card"><div class="muted">Unique ship types</div>'
        f'<div class="mono" style="font-size:1.45rem;font-weight:800;">{("—" if np.isnan(n_ships) else f"{n_ships:,}")}</div></div>',
        unsafe_allow_html=True,
    )
else:
    for c in kcols:
        c.info("KPI dinonaktifkan (kolom numeric/value tidak ditemukan).")

st.divider()

# =========================
# CHARTS (IF WE CAN)
# =========================
st.markdown("### Charts")

if not value_col:
    st.warning("Tidak bisa bikin grafik karena tidak ada kolom numeric/value yang terdeteksi.")
else:
    # Make a working numeric column
    df_plot = df_f.copy()
    df_plot["_value"] = to_numeric_series(df_plot[value_col])

    # Drop rows with NaN values
    df_plot = df_plot[df_plot["_value"].notna()].copy()
    if df_plot.empty:
        st.warning("Setelah filter & numeric coercion, tidak ada data numeric untuk diplot.")
    else:
        c1, c2 = st.columns(2)

        # 1) Fuel share (if fuel column exists)
        with c1:
            if fuel_col:
                agg = (
                    df_plot.groupby(fuel_col, dropna=False)["_value"]
                    .sum()
                    .sort_values(ascending=False)
                    .head(top_n)
                    .reset_index()
                )
                fig = px.bar(agg, x=fuel_col, y="_value", title=f"Top fuels by {value_col}")
                fig.update_layout(xaxis_title=None, yaxis_title=value_col)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Fuel chart: kolom Fuel tidak terdeteksi.")

        # 2) Ship type share (if ship column exists)
        with c2:
            if ship_col:
                agg = (
                    df_plot.groupby(ship_col, dropna=False)["_value"]
                    .sum()
                    .sort_values(ascending=False)
                    .head(top_n)
                    .reset_index()
                )
                fig = px.bar(agg, x=ship_col, y="_value", title=f"Top ship types by {value_col}")
                fig.update_layout(xaxis_title=None, yaxis_title=value_col)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Ship-type chart: kolom Ship Type tidak terdeteksi.")

        # 3) Trend by year (if year exists)
        if year_col:
            st.markdown("#### Trend by year")
            # Coerce year to int-ish if possible
            yy = df_plot[year_col].astype(str).str.extract(r"(\d{4})")[0]
            df_plot["_year"] = pd.to_numeric(yy, errors="coerce")
            trend = (
                df_plot.dropna(subset=["_year"])
                .groupby("_year")["_value"]
                .sum()
                .sort_index()
                .reset_index()
            )
            if trend.empty:
                st.info("Tidak ada year valid (4-digit) untuk bikin trend.")
            else:
                fig = px.line(trend, x="_year", y="_value", markers=True, title=f"{value_col} over time")
                fig.update_layout(xaxis_title="Year", yaxis_title=value_col)
                st.plotly_chart(fig, use_container_width=True)

# =========================
# OPTIONAL: SHOW FULL CLEANED TABLE
# =========================
if show_table:
    st.divider()
    st.markdown("### Full cleaned table")
    st.caption("Ini sudah termasuk removal baris 'Total/Grand Total/Subtotal' otomatis.")
    st.dataframe(df_f, use_container_width=True)

# =========================
# FOOTNOTE
# =========================
st.markdown(
    """
<div class="small-note">
<b>Cleaning rule:</b> Sistem akan menghapus baris jika ada sel mana pun yang mengandung kata
<span class="mono">total</span>/<span class="mono">grand total</span>/<span class="mono">subtotal</span> (case-insensitive).
Kalau Anda punya label agregat lain yang ingin dibuang, bilang saja keyword-nya.
</div>
""",
    unsafe_allow_html=True,
)# PATH FIX (WORKS ON STREAMLIT CLOUD)
# =========================
REPO_ROOT = Path(__file__).resolve().parents[1]  # from pages/ -> repo root
DATA_PATH = REPO_ROOT / "data" / "data fuel.xlsx"

# Optional quick debug (comment if not needed)
# st.write("DATA_PATH:", str(DATA_PATH))
# st.write("Exists:", DATA_PATH.exists())

if not DATA_PATH.exists():
    st.error(
        f"File tidak ketemu: {DATA_PATH}\n\n"
        "Pastikan file `data fuel.xlsx` ada di folder `data/` dan namanya persis sama (termasuk spasi)."
    )
    st.stop()

# =========================
# LOAD & CLEAN
# =========================
@st.cache_data(show_spinner=False)
def load_data(path: Path) -> pd.DataFrame:
    df = pd.read_excel(path)

    # Rename first column to Category if needed
    first_col = df.columns[0]
    if first_col != "Category":
        df = df.rename(columns={first_col: "Category"})

    # Normalize column names
    df.columns = [str(c).replace("\n", " ").strip() for c in df.columns]

    # Detect CO2 column robustly
    col_map = {c.lower().strip(): c for c in df.columns}
    co2_col = None
    candidates = ["co2 emissions", "co2 emission", "co2 (tonnes)", "co2"]
    for key in candidates:
        if key in col_map:
            co2_col = col_map[key]
            break
    if co2_col is None:
        # fallback contains
        for c in df.columns:
            lc = c.lower()
            if "co2" in lc and "emiss" in lc:
                co2_col = c
                break

    if co2_col is None:
        raise ValueError("Kolom CO2 emissions tidak ditemukan. Cek header di Excel.")

    df = df.rename(columns={co2_col: "CO2 emissions"})

    # Build hierarchy: rows alternate between ship type and size categories
    def is_size_row(x: str) -> bool:
        if not isinstance(x, str):
            return False
        t = x.strip().lower()
        return ("dwt" in t) or t.startswith("less than") or ("≤" in t) or ("<" in t)

    ship_type = []
    size_cat = []
    current_ship = None

    for v in df["Category"].astype(str).tolist():
        if is_size_row(v):
            ship_type.append(current_ship)
            size_cat.append(v.strip())
        else:
            current_ship = v.strip()
            ship_type.append(current_ship)
            size_cat.append("All sizes")

    df["Ship type"] = ship_type
    df["Size category"] = size_cat

    # Coerce numeric columns
    non_num = {"Category", "Ship type", "Size category"}
    for c in df.columns:
        if c not in non_num:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    # Drop rows without ship type (safety)
    df = df.dropna(subset=["Ship type"]).copy()

    return df


df_raw = load_data(DATA_PATH)

# =========================
# IDENTIFY FUEL COLUMNS
# =========================
KNOWN_NON_FUEL = {
    "Number of ships",
    "Gross tonnage",
    "Deadweight tonnage",
    "Distance travelled",
    "Hours under way",
    "CO2 emissions",
}

fuel_cols = [
    c
    for c in df_raw.columns
    if c not in {"Category", "Ship type", "Size category"} and c not in KNOWN_NON_FUEL
]

# =========================
# SIDEBAR FILTERS
# =========================
st.sidebar.markdown("### IMO – Filters")

all_ship_types = sorted(
    [x for x in df_raw["Ship type"].dropna().unique().tolist() if str(x).strip() != ""]
)

all_sizes_unique = sorted(
    [x for x in df_raw["Size category"].dropna().unique().tolist() if str(x).strip() != ""]
)
# Put All sizes first
all_sizes = ["All sizes"] + [s for s in all_sizes_unique if s != "All sizes"]

sel_ship_types = st.sidebar.multiselect(
    "Ship type",
    options=all_ship_types,
    default=all_ship_types,
)

sel_sizes = st.sidebar.multiselect(
    "Size category",
    options=all_sizes,
    default=["All sizes"],
)

fuel_chart_mode = st.sidebar.radio(
    "Fuel chart mode",
    ["Total fuel (absolute)", "Fuel mix share (%)"],
    index=0,
)

top_n = st.sidebar.slider("Top N ship types", min_value=5, max_value=30, value=15)

# Apply filters
df = df_raw[df_raw["Ship type"].isin(sel_ship_types)].copy()
df = df[df["Size category"].isin(sel_sizes)].copy()

# =========================
# AGGREGATIONS
# =========================
agg_cols = ["Number of ships", "CO2 emissions"] + fuel_cols
for c in ["Gross tonnage", "Deadweight tonnage", "Distance travelled", "Hours under way"]:
    if c in df.columns:
        agg_cols.append(c)

df_by_type = (
    df.groupby("Ship type", as_index=False)[agg_cols]
    .sum(numeric_only=True)
)

# Totals for KPIs
total_ships = float(df_by_type["Number of ships"].sum()) if "Number of ships" in df_by_type else np.nan
total_co2 = float(df_by_type["CO2 emissions"].sum()) if "CO2 emissions" in df_by_type else np.nan

top_ship_by_ships = (
    df_by_type.sort_values("Number of ships", ascending=False).head(1)["Ship type"].iloc[0]
    if len(df_by_type) else "-"
)

fuel_totals = df_by_type[fuel_cols].sum().sort_values(ascending=False) if len(fuel_cols) else pd.Series(dtype=float)
top_fuel = fuel_totals.index[0] if len(fuel_totals) else "-"

# =========================
# HEADER
# =========================
st.markdown('<div class="title">IMO – Fleet Fuel & Emissions Dashboard</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="muted subtitle">Highlight utama: <b>Number of ships</b> + <b>CO₂ emissions</b>. '
    'Fuel ditampilkan sebagai mix & breakdown. Variabel lain sebagai info pendukung.</div>',
    unsafe_allow_html=True,
)

# =========================
# KPI ROW
# =========================
k1, k2, k3, k4 = st.columns(4)

with k1:
    st.markdown('<div class="kpi-card">', unsafe_allow_html=True)
    st.metric("Total ships", f"{total_ships:,.0f}")
    st.markdown('</div>', unsafe_allow_html=True)

with k2:
    st.markdown('<div class="kpi-card">', unsafe_allow_html=True)
    st.metric("Total CO₂ emissions", f"{total_co2:,.0f}")
    st.markdown('</div>', unsafe_allow_html=True)

with k3:
    st.markdown('<div class="kpi-card">', unsafe_allow_html=True)
    st.metric("Largest ship type (by ships)", top_ship_by_ships)
    st.markdown('</div>', unsafe_allow_html=True)

with k4:
    st.markdown('<div class="kpi-card">', unsafe_allow_html=True)
    st.metric("Dominant fuel (by total)", top_fuel)
    st.markdown('</div>', unsafe_allow_html=True)

st.divider()

# =========================
# MAIN LAYOUT
# =========================
left, right = st.columns([1.18, 0.82], gap="large")

# ---- LEFT: highlight ships + CO2
with left:
    st.subheader("Fleet composition & emissions")

    if len(df_by_type) == 0:
        st.warning("Tidak ada data untuk filter yang dipilih.")
        st.stop()

    top_df_ships = df_by_type.sort_values("Number of ships", ascending=False).head(top_n).copy()

    fig_ships = px.bar(
        top_df_ships,
        x="Number of ships",
        y="Ship type",
        orientation="h",
        title=f"Top {top_n} ship types by number of ships",
    )
    fig_ships.update_layout(height=520, margin=dict(l=10, r=10, t=50, b=10))
    st.plotly_chart(fig_ships, use_container_width=True)

    top_df_co2 = df_by_type.sort_values("CO2 emissions", ascending=False).head(top_n).copy()
    fig_co2 = px.bar(
        top_df_co2,
        x="CO2 emissions",
        y="Ship type",
        orientation="h",
        title=f"Top {top_n} ship types by CO₂ emissions",
    )
    fig_co2.update_layout(height=520, margin=dict(l=10, r=10, t=50, b=10))
    st.plotly_chart(fig_co2, use_container_width=True)

# ---- RIGHT: fuel mix highlight + breakdown
with right:
    st.subheader("Fuel used")

    if len(fuel_cols) == 0:
        st.info("Kolom fuel tidak terdeteksi di file. Pastikan header fuel ada (MDO/MGO, HFO, LFO, Ethanol, dll).")
    else:
        fuel_df = fuel_totals.reset_index()
        fuel_df.columns = ["Fuel", "Total"]

        fig_donut = px.pie(
            fuel_df,
            names="Fuel",
            values="Total",
            hole=0.55,
            title="Overall fuel mix (all ship types)",
        )
        fig_donut.update_layout(height=420, margin=dict(l=10, r=10, t=50, b=10))
        st.plotly_chart(fig_donut, use_container_width=True)

        st.markdown("#### Fuel by ship type")
        fuel_by_type = df_by_type[["Ship type"] + fuel_cols].copy()

        # keep ship types aligned with "Top by ships" for readability
        keep_types = top_df_ships["Ship type"].tolist()
        fuel_by_type = fuel_by_type[fuel_by_type["Ship type"].isin(keep_types)].copy()

        fuel_long = fuel_by_type.melt(id_vars=["Ship type"], var_name="Fuel", value_name="Amount")
        fuel_long["Amount"] = fuel_long["Amount"].fillna(0)

        if fuel_chart_mode == "Fuel mix share (%)":
            totals = fuel_long.groupby("Ship type", as_index=False)["Amount"].sum().rename(columns={"Amount": "Total"})
            fuel_long = fuel_long.merge(totals, on="Ship type", how="left")
            fuel_long["Share (%)"] = np.where(fuel_long["Total"] > 0, 100 * fuel_long["Amount"] / fuel_long["Total"], 0.0)
            x_col = "Share (%)"
            title = "Fuel mix share by ship type (%)"
        else:
            x_col = "Amount"
            title = "Total fuel by ship type (stacked)"

        fig_stack = px.bar(
            fuel_long,
            x=x_col,
            y="Ship type",
            color="Fuel",
            orientation="h",
            title=title,
        )
        fig_stack.update_layout(
            height=640,
            margin=dict(l=10, r=10, t=50, b=10),
            legend_title_text="Fuel",
        )
        st.plotly_chart(fig_stack, use_container_width=True)

    st.markdown(
        '<div class="small-note">Note: variabel lain (Gross tonnage, Distance travelled, Hours under way, dll) '
        'ditampilkan di tabel detail sebagai supporting info.</div>',
        unsafe_allow_html=True,
    )

st.divider()

# =========================
# DETAIL TABLE (ships + CO2 highlighted)
# =========================
st.subheader("Detail table (ships & CO₂ highlighted)")

detail = df_by_type.copy()
detail = detail.sort_values(["Number of ships", "CO2 emissions"], ascending=False)

# Choose columns: highlighted first, then fuels, then supporting
show_cols = ["Ship type", "Number of ships", "CO2 emissions"]
show_cols += fuel_cols

for c in ["Gross tonnage", "Deadweight tonnage", "Distance travelled", "Hours under way"]:
    if c in detail.columns:
        show_cols.append(c)

detail_show = detail[show_cols].copy()

def _highlight_max_col(s: pd.Series):
    if s.name in ["Number of ships", "CO2 emissions"]:
        vals = pd.to_numeric(s, errors="coerce").fillna(0).values
        vmax = float(np.max(vals)) if len(vals) else 0.0
        return [
            "font-weight:700; background-color: rgba(255, 165, 0, 0.20)" if (float(v) == vmax and vmax > 0) else ""
            for v in vals
        ]
    return [""] * len(s)

fmt_map = {c: "{:,.0f}" for c in detail_show.columns if c != "Ship type"}

styled = (
    detail_show.style
    .apply(_highlight_max_col, axis=0)
    .format(fmt_map)
)

st.dataframe(styled, use_container_width=True, height=520)

# =========================
# RAW VIEW (OPTIONAL)
# =========================
with st.expander("Show raw rows (ship type + size categories)"):
    st.dataframe(df, use_container_width=True, height=420)
