import re
import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px

# =========================
# CONFIG
# =========================
st.set_page_config(page_title="Fleet Fuel & Emissions Dashboard", layout="wide")

st.markdown(
    """
    <style>
      .block-container {padding-top: 1.2rem; padding-bottom: 2rem;}
      .kpi-card {border: 1px solid rgba(0,0,0,0.08); border-radius: 14px; padding: 12px 14px;}
      .muted {color: rgba(0,0,0,0.55); font-size: 0.9rem;}
      .title {font-size: 1.35rem; font-weight: 700; margin-bottom: 0.25rem;}
    </style>
    """,
    unsafe_allow_html=True
)

# =========================
# LOAD & CLEAN
# =========================
@st.cache_data(show_spinner=False)
def load_data(path: str) -> pd.DataFrame:
    df = pd.read_excel(path)

    # Rename first col
    first_col = df.columns[0]
    df = df.rename(columns={first_col: "Category"})

    # Normalize column names
    df.columns = [c.replace("\n", " ").strip() for c in df.columns]

    # Identify hierarchy: ship type row vs size category row
    # Size category rows typically contain "DWT"
    def is_size_row(x: str) -> bool:
        if not isinstance(x, str):
            return False
        return bool(re.search(r"\bDWT\b", x)) or x.lower().startswith("less than")

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

    # Coerce numeric columns (everything except Category/Ship type/Size category)
    non_num = {"Category", "Ship type", "Size category"}
    for c in df.columns:
        if c not in non_num:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    # Tidy: drop fully empty ship types (just in case)
    df = df.dropna(subset=["Ship type"]).copy()

    return df

DATA_PATH = "data fuel.xlsx"
df_raw = load_data(DATA_PATH)

# Detect fuel columns (everything that is NOT obvious fleet activity / counts)
KNOWN_NON_FUEL = {
    "Number of ships", "Gross tonnage", "Deadweight tonnage",
    "Distance travelled", "Hours under way", "CO2 emissions"
}

# Some sheets might keep "CO2 emissions" as "CO2 emissions" with spaces
# Make sure we map it robustly
col_map = {c.lower(): c for c in df_raw.columns}
co2_col = None
for k in ["co2 emissions", "co2  emissions", "co2 emissions ", "co2 emissions  "]:
    if k in col_map:
        co2_col = col_map[k]
        break
# fallback: find any column containing "co2" and "emission"
if co2_col is None:
    for c in df_raw.columns:
        if "co2" in c.lower() and "emission" in c.lower():
            co2_col = c
            break

if co2_col is None:
    st.error("Tidak ketemu kolom CO2 emissions di file. Cek header kolomnya.")
    st.stop()

# Standardize to a single name
df_raw = df_raw.rename(columns={co2_col: "CO2 emissions"})
if "CO2 emissions" not in KNOWN_NON_FUEL:
    KNOWN_NON_FUEL.add("CO2 emissions")

fuel_cols = [c for c in df_raw.columns
             if c not in {"Category", "Ship type", "Size category"}
             and c not in KNOWN_NON_FUEL]

# =========================
# SIDEBAR FILTERS
# =========================
st.sidebar.markdown("### Filters")
all_ship_types = sorted([x for x in df_raw["Ship type"].dropna().unique().tolist() if x.strip() != ""])
all_sizes = ["All sizes"] + sorted([x for x in df_raw["Size category"].dropna().unique().tolist() if x != "All sizes"])

sel_ship_types = st.sidebar.multiselect(
    "Ship type",
    options=all_ship_types,
    default=all_ship_types
)

sel_sizes = st.sidebar.multiselect(
    "Size category",
    options=all_sizes,
    default=["All sizes"]
)

metric_mode = st.sidebar.radio(
    "Fuel chart mode",
    ["Total fuel (all types)", "Fuel mix share (%)"],
    index=0
)

top_n = st.sidebar.slider("Top N ship types", 5, 30, 15)

# Filter dataframe
df = df_raw[df_raw["Ship type"].isin(sel_ship_types)].copy()
df = df[df["Size category"].isin(sel_sizes)].copy()

# =========================
# AGGREGATIONS
# =========================
# 1) Aggregated by ship type (for professional overview)
agg_cols = ["Number of ships", "CO2 emissions"] + fuel_cols + [
    c for c in ["Gross tonnage", "Deadweight tonnage", "Distance travelled", "Hours under way"]
    if c in df.columns
]

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

# Overall fuel totals
fuel_totals = df_by_type[fuel_cols].sum().sort_values(ascending=False)
top_fuel = fuel_totals.index[0] if len(fuel_totals) else "-"

# =========================
# HEADER
# =========================
st.markdown('<div class="title">Fleet Fuel & Emissions Dashboard</div>', unsafe_allow_html=True)
st.markdown(
    f'<div class="muted">Highlight utama: <b>jumlah kapal per ship type</b> + <b>fuel used</b> + <b>CO₂ emissions</b>. '
    f'Data lain ditampilkan sebagai info pendukung.</div>',
    unsafe_allow_html=True
)

# =========================
# KPI ROW (ships + emissions highlighted)
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
left, right = st.columns([1.15, 0.85], gap="large")

# ---- LEFT: Ships + Emissions (highlight)
with left:
    st.subheader("Fleet composition & emissions (highlight)")

    # Top N ship types by number of ships
    top_df = df_by_type.sort_values("Number of ships", ascending=False).head(top_n).copy()

    fig_ships = px.bar(
        top_df,
        x="Number of ships",
        y="Ship type",
        orientation="h",
        title=f"Top {top_n} ship types by number of ships"
    )
    fig_ships.update_layout(height=520, margin=dict(l=10, r=10, t=50, b=10))
    st.plotly_chart(fig_ships, use_container_width=True)

    # Emissions bar (top N) — separate chart to keep emissions clearly highlighted
    fig_co2 = px.bar(
        top_df.sort_values("CO2 emissions", ascending=False),
        x="CO2 emissions",
        y="Ship type",
        orientation="h",
        title=f"Top {top_n} ship types by CO₂ emissions"
    )
    fig_co2.update_layout(height=520, margin=dict(l=10, r=10, t=50, b=10))
    st.plotly_chart(fig_co2, use_container_width=True)

# ---- RIGHT: Fuel mix + supporting info
with right:
    st.subheader("Fuel used (highlight)")

    # Fuel donut overall
    fuel_df = fuel_totals.reset_index()
    fuel_df.columns = ["Fuel", "Total"]

    fig_donut = px.pie(
        fuel_df,
        names="Fuel",
        values="Total",
        hole=0.55,
        title="Overall fuel mix (all ship types)"
    )
    fig_donut.update_layout(height=420, margin=dict(l=10, r=10, t=50, b=10))
    st.plotly_chart(fig_donut, use_container_width=True)

    # Fuel by ship type: stacked bar
    st.markdown("#### Fuel by ship type")

    fuel_by_type = df_by_type[["Ship type"] + fuel_cols].copy()
    # keep only top N ship types to stay readable
    fuel_by_type = fuel_by_type.merge(top_df[["Ship type"]], on="Ship type", how="inner")

    fuel_long = fuel_by_type.melt(id_vars=["Ship type"], var_name="Fuel", value_name="Amount").copy()
    fuel_long["Amount"] = fuel_long["Amount"].fillna(0)

    if metric_mode == "Fuel mix share (%)":
        # convert within each ship type to share
        totals = fuel_long.groupby("Ship type", as_index=False)["Amount"].sum().rename(columns={"Amount": "Total"})
        fuel_long = fuel_long.merge(totals, on="Ship type", how="left")
        fuel_long["Share (%)"] = np.where(fuel_long["Total"] > 0, 100 * fuel_long["Amount"] / fuel_long["Total"], 0.0)
        y_col = "Share (%)"
        title = "Fuel mix share by ship type (%)"
    else:
        y_col = "Amount"
        title = "Total fuel amounts by ship type (stacked)"

    fig_stack = px.bar(
        fuel_long,
        x=y_col,
        y="Ship type",
        color="Fuel",
        orientation="h",
        title=title
    )
    fig_stack.update_layout(height=620, margin=dict(l=10, r=10, t=50, b=10), legend_title_text="Fuel")
    st.plotly_chart(fig_stack, use_container_width=True)

    st.info(
        "Catatan: metric lain (Gross tonnage, Distance travelled, Hours under way, dll) ditampilkan di tabel detail sebagai info pendukung."
    )

st.divider()

# =========================
# DETAIL TABLE (professional + highlighted emissions)
# =========================
st.subheader("Detail table (with emissions highlight)")

detail = df_by_type.copy()
detail = detail.sort_values(["Number of ships", "CO2 emissions"], ascending=False)

# Choose columns to show: highlight ships + emissions, then fuels, then other info
show_cols = ["Ship type", "Number of ships", "CO2 emissions"] + fuel_cols
for c in ["Gross tonnage", "Deadweight tonnage", "Distance travelled", "Hours under way"]:
    if c in detail.columns:
        show_cols.append(c)

detail_show = detail[show_cols].copy()

# Format and style: highlight CO2 + ships
def _style_highlight(s: pd.Series):
    # highlight top values (ships & CO2)
    if s.name in ["Number of ships", "CO2 emissions"]:
        vmax = np.nanmax(s.values.astype(float)) if len(s) else 0
        return ["font-weight:700; background-color: rgba(255, 165, 0, 0.18)" if (v == vmax and vmax > 0) else "" for v in s]
    return [""] * len(s)

styled = (
    detail_show.style
    .apply(_style_highlight, axis=0)
    .format({c: "{:,.0f}" for c in detail_show.columns if c not in ["Ship type"]})
)

st.dataframe(styled, use_container_width=True, height=520)

# =========================
# OPTIONAL: RAW LEVEL VIEW
# =========================
with st.expander("Show raw rows (ship type + size categories)"):
    st.dataframe(df, use_container_width=True, height=420)
