# streamlit_app.py
# ------------------------------------------------------------
# IMO Dashboard (from IMO.xlsx)
# - Parses a "combined" IMO table sheet into a clean long table
# - Pages: Overview, Fuel (Table 2), CII & EEXI (Table 4), Explorer
#
# Run:
#   streamlit run streamlit_app.py
#
# Assumes your Excel is at ./IMO.xlsx
# ------------------------------------------------------------

from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st


# =========================
# Configuration
# =========================
APP_TITLE = "IMO Database Dashboard"
DEFAULT_EXCEL_PATH = "IMO.xlsx"  # put IMO.xlsx beside this script

st.set_page_config(page_title=APP_TITLE, layout="wide")


# =========================
# Helpers
# =========================
def _is_nan(x) -> bool:
    return x is None or (isinstance(x, float) and np.isnan(x))


def _to_str(x) -> str:
    if _is_nan(x):
        return ""
    return str(x).strip()


def _safe_float(x) -> float:
    """
    Convert Excel cell to float. Handles:
    - '-', '—', '' => NaN
    - strings with commas
    """
    if _is_nan(x):
        return np.nan
    if isinstance(x, (int, float, np.integer, np.floating)):
        return float(x)
    s = str(x).strip()
    if s in {"", "-", "—", "–"}:
        return np.nan
    s = s.replace(",", "")
    try:
        return float(s)
    except Exception:
        return np.nan


def _normalize_label(s: str) -> str:
    # normalize whitespace/newlines
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _is_size_category(label: str) -> bool:
    """
    Detect sub-rows like:
    - Less than 10,000 DWT
    - 10,000 ≤ DWT < 20,000
    - 20,000 DWT and above
    - Less than 5,000 GT
    - etc.
    """
    s = _normalize_label(label).lower()
    if not s:
        return False
    patterns = [
        r"^less than",
        r"≤",
        r"\band above\b",
        r"\bgt\b",
        r"\bdwt\b",
        r"<",
        r">",
    ]
    return any(re.search(p, s) for p in patterns)


def _clean_colname(x) -> str:
    s = _normalize_label(_to_str(x))
    return s


@st.cache_data(show_spinner=False)
def load_raw_excel(path: str) -> Tuple[str, pd.DataFrame]:
    """
    Loads the first sheet as raw (header=None).
    Returns (sheet_name, df_raw)
    """
    xl = pd.ExcelFile(path)
    sheet = xl.sheet_names[0]
    df_raw = pd.read_excel(path, sheet_name=sheet, header=None)
    return sheet, df_raw


def _extract_header_row(df_raw: pd.DataFrame) -> Dict[int, str]:
    """
    Strategy:
    - Take row 1 as main header reference for numeric columns
    - Patch known column positions based on observed structure.
    """
    row1 = df_raw.iloc[1].tolist() if len(df_raw) > 1 else []
    headers = {}
    for c in range(df_raw.shape[1]):
        headers[c] = _clean_colname(row1[c]) if c < len(row1) else f"col_{c}"

    # Patch known columns
    headers[0] = "Label"
    if headers.get(16, "") == "":
        headers[16] = "CO2 emissions"

    for idx, name in zip(range(17, 22), ["CII A", "CII B", "CII C", "CII D", "CII E"]):
        if headers.get(idx, "") in {"A", "B", "C", "D", "E", ""}:
            headers[idx] = name

    if headers.get(22, "") == "":
        headers[22] = "No reported CII"
    if headers.get(23, "") == "":
        headers[23] = "CII reporting rate"
    if headers.get(24, "") == "":
        headers[24] = "EEXI number of ships"
    if headers.get(25, "") == "":
        headers[25] = "EEXI reporting rate"

    for c in range(1, 16):
        if headers.get(c, "") == "":
            headers[c] = f"Fuel col {c}"

    return headers


@st.cache_data(show_spinner=False)
def parse_imo_master(path: str) -> pd.DataFrame:
    """
    Parse combined IMO sheet into a single clean long dataframe.
    """
    _, df_raw = load_raw_excel(path)
    headers = _extract_header_row(df_raw)

    records: List[Dict] = []
    current_ship_type: Optional[str] = None

    # Data starts at row 2 (row 0 narrative, row 1 header)
    for r in range(2, df_raw.shape[0]):
        label = _normalize_label(_to_str(df_raw.iat[r, 0]))
        if not label:
            continue

        if not _is_size_category(label):
            current_ship_type = label
            size_category = "All"
        else:
            if not current_ship_type:
                continue
            size_category = label

        row = {"ship_type": current_ship_type, "size_category": size_category}

        for c in range(1, df_raw.shape[1]):
            colname = headers.get(c, f"col_{c}")
            if colname == "":
                continue
            val = _safe_float(df_raw.iat[r, c])
            row[colname] = val

        records.append(row)

    df = pd.DataFrame.from_records(records)

    known_non_fuel = {
        "CO2 emissions",
        "CII A",
        "CII B",
        "CII C",
        "CII D",
        "CII E",
        "No reported CII",
        "CII reporting rate",
        "EEXI number of ships",
        "EEXI reporting rate",
    }
    value_cols = [c for c in df.columns if c not in {"ship_type", "size_category"}]
    fuel_cols = [c for c in value_cols if c not in known_non_fuel]

    if fuel_cols:
        df["Total fuel (all types)"] = df[fuel_cols].sum(axis=1, skipna=True)

    for rr in ["CII reporting rate", "EEXI reporting rate"]:
        if rr in df.columns:
            df[rr] = pd.to_numeric(df[rr], errors="coerce")
            mx = df[rr].max(skipna=True)
            if mx and mx > 1.5:
                df[rr] = df[rr] / 100.0

    for c in df.columns:
        if c not in {"ship_type", "size_category"}:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    return df


def apply_filters(df: pd.DataFrame, ship_types: List[str], size_cats: List[str]) -> pd.DataFrame:
    out = df.copy()
    if ship_types:
        out = out[out["ship_type"].isin(ship_types)]
    if size_cats:
        out = out[out["size_category"].isin(size_cats)]
    return out


def format_int(x) -> str:
    if pd.isna(x):
        return "—"
    return f"{int(round(x)):,.0f}"


def format_pct(x) -> str:
    if pd.isna(x):
        return "—"
    return f"{x:.1%}"


# =========================
# UI
# =========================
st.title(APP_TITLE)

with st.sidebar:
    st.header("Data source")
    excel_path = st.text_input(
        "Excel path",
        value=DEFAULT_EXCEL_PATH,
        help="Put IMO.xlsx beside streamlit_app.py, or enter a path.",
    )
    st.caption("Tip: keep the Excel path stable so caching works well.")

    st.divider()
    st.header("Navigation")
    page = st.radio(
        "Page",
        ["Overview", "Fuel (Table 2)", "CII & EEXI (Table 4)", "Explorer"],
        index=0,
    )

# Load + parse
try:
    df_master = parse_imo_master(excel_path)
except FileNotFoundError:
    st.error(f"File not found: {excel_path}")
    st.stop()
except Exception as e:
    st.exception(e)
    st.stop()

# Global filters
all_ship_types = sorted([x for x in df_master["ship_type"].dropna().unique().tolist() if str(x).strip() != ""])
all_size_cats = sorted([x for x in df_master["size_category"].dropna().unique().tolist() if str(x).strip() != ""])

with st.sidebar:
    st.divider()
    st.header("Global filters")
    ship_sel = st.multiselect("Ship type", options=all_ship_types, default=all_ship_types)
    size_sel = st.multiselect("Size category", options=all_size_cats, default=all_size_cats)

df_f = apply_filters(df_master, ship_sel, size_sel)

# Identify fuel columns for plots
known_non_fuel = {
    "CO2 emissions",
    "CII A",
    "CII B",
    "CII C",
    "CII D",
    "CII E",
    "No reported CII",
    "CII reporting rate",
    "EEXI number of ships",
    "EEXI reporting rate",
    "Total fuel (all types)",
}
value_cols = [c for c in df_master.columns if c not in {"ship_type", "size_category"}]
fuel_cols = [c for c in value_cols if c not in known_non_fuel]


# =========================
# Overview
# =========================
if page == "Overview":
    st.subheader("Overview")

    total_co2 = df_f["CO2 emissions"].sum(skipna=True) if "CO2 emissions" in df_f.columns else np.nan
    total_fuel = df_f["Total fuel (all types)"].sum(skipna=True) if "Total fuel (all types)" in df_f.columns else np.nan

    cii_rr_mean = df_f["CII reporting rate"].mean(skipna=True) if "CII reporting rate" in df_f.columns else np.nan
    eexi_rr_mean = df_f["EEXI reporting rate"].mean(skipna=True) if "EEXI reporting rate" in df_f.columns else np.nan

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total CO₂ (t)", format_int(total_co2))
    c2.metric("Total fuel (all types)", format_int(total_fuel))
    c3.metric("Avg CII reporting rate", format_pct(cii_rr_mean))
    c4.metric("Avg EEXI reporting rate", format_pct(eexi_rr_mean))

    st.divider()

    # NEW: Fuel consumption per ship type (TOTAL)
    if "Total fuel (all types)" in df_f.columns:
        st.markdown("### Fuel consumption per ship type (total)")
        fuel_by_ship = (
            df_f.groupby("ship_type", as_index=False)["Total fuel (all types)"]
            .sum(min_count=1)
            .sort_values("Total fuel (all types)", ascending=False)
        )
        fig_total_fuel = px.bar(
            fuel_by_ship,
            x="ship_type",
            y="Total fuel (all types)",
            title="Total fuel consumption by ship type",
        )
        fig_total_fuel.update_layout(xaxis_title="", yaxis_title="Total fuel (as in source units)")
        st.plotly_chart(fig_total_fuel, use_container_width=True)
    else:
        st.info("Total fuel column not available (no fuel columns detected to sum).")

    st.divider()

    left, right = st.columns([1.15, 1])

    with left:
        if "CO2 emissions" in df_f.columns:
            agg = (
                df_f.groupby("ship_type", as_index=False)["CO2 emissions"]
                .sum(min_count=1)
                .sort_values("CO2 emissions", ascending=False)
            )
            fig = px.bar(agg, x="ship_type", y="CO2 emissions", title="CO₂ emissions by ship type")
            fig.update_layout(xaxis_title="", yaxis_title="CO₂ emissions (t)")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No CO₂ column detected.")

    with right:
        if fuel_cols:
            agg = df_f.groupby("ship_type", as_index=False)[fuel_cols].sum(min_count=1)
            long = agg.melt(id_vars=["ship_type"], var_name="fuel", value_name="amount").dropna()

            top_fuels = (
                long.groupby("fuel", as_index=False)["amount"].sum(min_count=1)
                .sort_values("amount", ascending=False)
                .head(8)["fuel"]
                .tolist()
            )
            long = long[long["fuel"].isin(top_fuels)]
            fig2 = px.bar(long, x="ship_type", y="amount", color="fuel", title="Fuel consumption mix (top fuels) by ship type")
            fig2.update_layout(xaxis_title="", yaxis_title="Fuel consumption (as in source units)")
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("No fuel columns detected.")

    st.divider()

    st.markdown("### Detail table (filtered)")
    show_cols = ["ship_type", "size_category"]
    for c in ["CO2 emissions", "Total fuel (all types)", "CII reporting rate", "EEXI number of ships", "EEXI reporting rate"]:
        if c in df_f.columns:
            show_cols.append(c)
    st.dataframe(df_f[show_cols].sort_values(["ship_type", "size_category"]), use_container_width=True, hide_index=True)

    csv = df_f.to_csv(index=False).encode("utf-8")
    st.download_button("Download filtered data (CSV)", data=csv, file_name="imo_filtered.csv", mime="text/csv")


# =========================
# Fuel (Table 2)
# =========================
elif page == "Fuel (Table 2)":
    st.subheader("Fuel (Table 2-style view)")

    if not fuel_cols:
        st.warning("No fuel columns detected from this sheet.")
        st.stop()

    with st.sidebar:
        st.divider()
        st.header("Fuel options")
        fuel_sel = st.multiselect("Fuel types", options=fuel_cols, default=fuel_cols)
        view_mode = st.radio("View", ["Absolute", "Share (%)"], index=0)

        # NEW: aggregation level (ship type only vs ship type+size)
        group_level = st.radio(
            "Group by",
            ["Ship type only", "Ship type + size category"],
            index=1,
            help="Kalau pilih 'Ship type only', maka fuel consumption diakumulasi untuk semua size category.",
        )

    df_ff = df_f.copy()
    fuel_sel = fuel_sel or fuel_cols

    # Aggregate
    if group_level == "Ship type only":
        group_cols = ["ship_type"]
    else:
        group_cols = ["ship_type", "size_category"]

    agg = df_ff.groupby(group_cols, as_index=False)[fuel_sel].sum(min_count=1)

    # NEW: total fuel per ship type (berdasarkan fuel_sel)
    agg["Total selected fuels"] = agg[fuel_sel].sum(axis=1, skipna=True)

    # Chart
    long = agg.melt(id_vars=group_cols, var_name="fuel", value_name="amount").dropna()

    if view_mode == "Share (%)":
        denom = long.groupby(group_cols)["amount"].transform(lambda s: s.sum(skipna=True))
        long["share"] = np.where(denom > 0, long["amount"] / denom, np.nan)

        if group_level == "Ship type only":
            fig = px.bar(
                long,
                x="ship_type",
                y="share",
                color="fuel",
                title="Fuel share by ship type",
            )
            fig.update_layout(xaxis_title="", yaxis_title="Share")
            st.plotly_chart(fig, use_container_width=True)
        else:
            fig = px.bar(
                long,
                x="ship_type",
                y="share",
                color="fuel",
                facet_col="size_category",
                facet_col_wrap=2,
                title="Fuel share by ship type and size category",
            )
            fig.update_layout(xaxis_title="", yaxis_title="Share")
            st.plotly_chart(fig, use_container_width=True)
    else:
        if group_level == "Ship type only":
            fig = px.bar(
                long,
                x="ship_type",
                y="amount",
                color="fuel",
                title="Fuel consumption by ship type",
            )
            fig.update_layout(xaxis_title="", yaxis_title="Fuel consumption (as in source units)")
            st.plotly_chart(fig, use_container_width=True)
        else:
            fig = px.bar(
                long,
                x="ship_type",
                y="amount",
                color="fuel",
                facet_col="size_category",
                facet_col_wrap=2,
                title="Fuel consumption by ship type and size category",
            )
            fig.update_layout(xaxis_title="", yaxis_title="Fuel consumption (as in source units)")
            st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # NEW: simple bar for "total fuel consumption per jenis kapal" (selected fuels)
    if group_level == "Ship type only":
        st.markdown("### Total fuel consumption per ship type (selected fuels)")
        fig_total_sel = px.bar(
            agg.sort_values("Total selected fuels", ascending=False),
            x="ship_type",
            y="Total selected fuels",
            title="Total fuel (selected fuels) by ship type",
        )
        fig_total_sel.update_layout(xaxis_title="", yaxis_title="Total (as in source units)")
        st.plotly_chart(fig_total_sel, use_container_width=True)

    st.divider()
    st.markdown("### Fuel table (filtered)")
    cols = group_cols + fuel_sel + ["Total selected fuels"]
    st.dataframe(agg[cols], use_container_width=True, hide_index=True)

    csv = agg[cols].to_csv(index=False).encode("utf-8")
    st.download_button("Download fuel view (CSV)", data=csv, file_name="imo_fuel_filtered.csv", mime="text/csv")


# =========================
# CII & EEXI (Table 4)
# =========================
elif page == "CII & EEXI (Table 4)":
    st.subheader("CII & EEXI (Table 4-style view)")

    needed = ["CII A", "CII B", "CII C", "CII D", "CII E", "No reported CII"]
    missing = [c for c in needed if c not in df_f.columns]
    if missing:
        st.warning(f"Missing columns for CII distribution: {missing}")
        st.stop()

    with st.sidebar:
        st.divider()
        st.header("CII options")
        normalize = st.toggle("Normalize A–E to 100% (exclude 'No reported')", value=True)

    cii_cols = ["CII A", "CII B", "CII C", "CII D", "CII E", "No reported CII"]
    agg = df_f.groupby(["ship_type", "size_category"], as_index=False)[cii_cols].sum(min_count=1)

    long = agg.melt(id_vars=["ship_type", "size_category"], var_name="rating", value_name="count").dropna()

    if normalize:
        is_ae = long["rating"].isin(["CII A", "CII B", "CII C", "CII D", "CII E"])
        denom = long[is_ae].groupby(["ship_type", "size_category"])["count"].transform(lambda s: s.sum(skipna=True))
        long.loc[is_ae, "share"] = np.where(denom > 0, long.loc[is_ae, "count"] / denom, np.nan)
        chart = long[is_ae].copy()
        fig = px.bar(
            chart,
            x="ship_type",
            y="share",
            color="rating",
            facet_col="size_category",
            facet_col_wrap=2,
            title="CII distribution (A–E) by ship type and size category",
        )
        fig.update_layout(xaxis_title="", yaxis_title="Share")
        st.plotly_chart(fig, use_container_width=True)
    else:
        fig = px.bar(
            long,
            x="ship_type",
            y="count",
            color="rating",
            facet_col="size_category",
            facet_col_wrap=2,
            title="CII distribution (A–E + No reported) by ship type and size category",
        )
        fig.update_layout(xaxis_title="", yaxis_title="Number of ships (as in source)")
        st.plotly_chart(fig, use_container_width=True)

    st.divider()

    eexi_cols = [c for c in ["EEXI number of ships", "EEXI reporting rate"] if c in df_f.columns]
    if eexi_cols:
        st.markdown("### EEXI summary (filtered)")
        eexi_agg = df_f.groupby(["ship_type", "size_category"], as_index=False)[eexi_cols].sum(min_count=1)
        st.dataframe(eexi_agg, use_container_width=True, hide_index=True)
        csv = eexi_agg.to_csv(index=False).encode("utf-8")
        st.download_button("Download EEXI summary (CSV)", data=csv, file_name="imo_eexi_filtered.csv", mime="text/csv")

    st.markdown("### Raw CII table (filtered)")
    st.dataframe(agg, use_container_width=True, hide_index=True)
    csv = agg.to_csv(index=False).encode("utf-8")
    st.download_button("Download CII table (CSV)", data=csv, file_name="imo_cii_filtered.csv", mime="text/csv")


# =========================
# Explorer
# =========================
else:
    st.subheader("Explorer")
    st.caption("Search + inspect the fully parsed table (already filtered by sidebar).")

    q = st.text_input("Search (ship type / size category contains)", value="")
    df_x = df_f.copy()
    if q.strip():
        qq = q.strip().lower()
        mask = (
            df_x["ship_type"].astype(str).str.lower().str.contains(qq, na=False)
            | df_x["size_category"].astype(str).str.lower().str.contains(qq, na=False)
        )
        df_x = df_x[mask]

    all_cols = df_x.columns.tolist()
    default_cols = ["ship_type", "size_category"]
    for c in ["CO2 emissions", "Total fuel (all types)", "CII reporting rate", "EEXI number of ships", "EEXI reporting rate"]:
        if c in all_cols and c not in default_cols:
            default_cols.append(c)

    cols_sel = st.multiselect("Columns", options=all_cols, default=default_cols)
    if not cols_sel:
        cols_sel = default_cols

    st.dataframe(df_x[cols_sel], use_container_width=True, hide_index=True)

    csv = df_x[cols_sel].to_csv(index=False).encode("utf-8")
    st.download_button("Download explorer view (CSV)", data=csv, file_name="imo_explorer.csv", mime="text/csv")


# =========================
# Footer: units note
# =========================
with st.expander("Notes (units & interpretation)", expanded=False):
    st.write(
        """
- App ini mem-parse sheet kamu jadi satu tabel long dengan mendeteksi **ship type rows** dan **size-category sub-rows**.
- Fuel columns dianggap **as-is unit** dari sumber tabel (seringnya tonnes/year di ringkasan IMO, tapi tolong konfirmasi di report).
- Reporting rates dianggap fraksi (0–1). Kalau di sheet kamu 0–100, app ini otomatis bagi 100.
- Kalau kamu mau output “Table 2 / Table 3 / Table 4” dipisah persis seperti format IMO, parser bisa kita kunci lagi jadi 3 dataframe terpisah.
"""
    )
