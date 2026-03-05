# pages/4_IMO.py
from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px

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
    </style>
    """,
    unsafe_allow_html=True,
)

# =========================
# PATH FIX (WORKS ON STREAMLIT CLOUD)
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
