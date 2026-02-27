import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from pathlib import Path

# ============================================================
# PAGE CONFIG
# ============================================================
st.set_page_config(page_title="CORSIA State-Pair Dashboard", layout="wide")

# ============================================================
# FILE PATHS (relative to repo root)
# IMPORTANT:
# - On Streamlit Cloud, files MUST exist in your GitHub repo
#   (or be downloaded at runtime). /mnt/data paths won't exist there.
# ============================================================
BASELINE_XLSX = "data/2019_2020_CO2_StatePairs_table_Nov2021.xlsx"  # optional
CURRENT_XLSX  = "data/2024_CO2_StatePairs_table.xlsx"              # required

AIRLINES_XLSX = "data/CORSIA_AO_to_State_Attributions_10ed_web-2_extracted.xlsx"  # optional

# If you discover mismatches between emissions country names and airlines country names, add mapping here.
COUNTRY_ALIAS = {
    # Examples:
    # "United States": "United States of America",
    # "Russia": "Russian Federation",
    # "Türkiye": "Turkey",
}

# ============================================================
# HELPERS
# ============================================================
def clean_num(x):
    """Convert numeric-like strings (with commas, asterisks) to float."""
    if pd.isna(x):
        return np.nan
    s = str(x).strip().replace(",", "").replace("*", "")
    if s in {"", "-", "—"}:
        return np.nan
    try:
        return float(s)
    except Exception:
        return np.nan

def split_pair(val, delim):
    """Split a state-pair string into (origin, destination)."""
    if pd.isna(val):
        return (None, None)
    p = str(val).split(delim)
    if len(p) == 2:
        return (p[0].strip(), p[1].strip())
    return (p[0].strip(), None)

def fmt_int(x):
    return "—" if pd.isna(x) else f"{int(round(x)):,}"

def fmt_pct(x):
    return "—" if pd.isna(x) else f"{x:.2f}%"

def safe_div(a, b):
    if b is None or b == 0 or pd.isna(b):
        return np.nan
    return a / b

def norm_country(s: str) -> str:
    if s is None or (isinstance(s, float) and np.isnan(s)):
        return ""
    s = str(s).strip()
    s = s.replace("’", "'").replace("  ", " ")
    return s

def file_exists(path_str: str) -> bool:
    return Path(path_str).exists()

# ============================================================
# LOAD DATA
# ============================================================
@st.cache_data
def load_baseline_optional(path: str) -> pd.DataFrame | None:
    """
    Optional baseline loader.
    Returns None if the file does not exist.
    """
    p = Path(path)
    if not p.exists():
        return None

    raw = pd.read_excel(p, header=None)

    # Find where country list starts (uses Afghanistan as anchor)
    idx_list = raw.index[raw[0].astype(str).str.contains("Afghanistan", na=False)]
    if len(idx_list) == 0:
        raise ValueError("Baseline file format not recognized (cannot find 'Afghanistan' anchor).")

    i = idx_list[0]
    d = raw.iloc[i:].copy()

    # Expect columns: pair | emissions | (unused)
    d.columns = ["pair", "v", "_"]
    d["emissions"] = d["v"].apply(clean_num)
    d[["o", "d"]] = d["pair"].apply(lambda x: pd.Series(split_pair(x, "-")))
    d = d[["o", "d", "emissions"]].dropna(subset=["o", "d", "emissions"])
    return d

@st.cache_data
def load_current_required(path: str) -> pd.DataFrame:
    """
    Required current-year loader.
    Expects table where:
      - column 0 = state-pair (Origin/Destination)
      - column 1 = subject emissions
      - column 2 = not-subject emissions
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(
            f"Current dataset not found: {p.resolve()}\n"
            "Fix: Put the Excel file in your repo at the specified path, or update CURRENT_XLSX."
        )

    raw = pd.read_excel(p, header=None)

    idx_list = raw.index[raw[0].astype(str).str.contains("Afghanistan", na=False)]
    if len(idx_list) == 0:
        raise ValueError("Current file format not recognized (cannot find 'Afghanistan' anchor).")

    i = idx_list[0]
    d = raw.iloc[i:].copy()
    d.columns = ["pair", "sub", "nsub"]

    d["sub"] = d["sub"].apply(clean_num)
    d["nsub"] = d["nsub"].apply(clean_num)
    d[["o", "d"]] = d["pair"].apply(lambda x: pd.Series(split_pair(x, "/")))

    rows = []
    for _, r in d.iterrows():
        if pd.notna(r["sub"]):
            rows.append((r["o"], r["d"], r["sub"], True))
        if pd.notna(r["nsub"]):
            rows.append((r["o"], r["d"], r["nsub"], False))

    cur = pd.DataFrame(rows, columns=["o", "d", "emissions", "subject"])
    cur = cur.dropna(subset=["o", "d", "emissions"])
    return cur

@st.cache_data
def load_airlines_optional(path: str):
    """
    Optional airlines directory loader.
    Expected columns:
      - 'State'
      - 'Aeroplane Operator Name'
    Returns (airlines_df, airlines_by_country_dict) or (None, {}) if missing.
    """
    p = Path(path)
    if not p.exists():
        return None, {}

    adf = pd.read_excel(p)

    cols = {c.strip(): c for c in adf.columns}
    state_col = cols.get("State")
    ao_col = cols.get("Aeroplane Operator Name")

    if state_col is None or ao_col is None:
        raise ValueError(
            "Airlines file missing required columns. Expected: 'State' and 'Aeroplane Operator Name'."
        )

    adf = adf.rename(columns={state_col: "country", ao_col: "airline"}).copy()
    adf["country"] = adf["country"].map(norm_country).replace(COUNTRY_ALIAS)
    adf["airline"] = adf["airline"].astype(str).str.strip()

    airlines_by_country = (
        adf.groupby("country")["airline"]
           .apply(lambda s: sorted(set([x for x in s if x and x.lower() != "nan"])))
           .to_dict()
    )
    return adf, airlines_by_country

@st.cache_data
def build_rankings(cur: pd.DataFrame):
    """
    Build rankings from the current dataset:
      - Top directed pairs (o->d)
      - Top countries by involvement (origin+destination)
      - Top origins
      - Top destinations
    Both for all emissions and subject-only.
    """
    df = cur.copy()

    pair_all = (
        df.groupby(["o", "d"], as_index=False)["emissions"]
          .sum()
          .sort_values("emissions", ascending=False)
    )
    pair_sub = (
        df[df["subject"]]
        .groupby(["o", "d"], as_index=False)["emissions"]
        .sum()
        .sort_values("emissions", ascending=False)
    )

    o_all = df.groupby("o", as_index=False)["emissions"].sum().rename(columns={"o": "country"})
    d_all = df.groupby("d", as_index=False)["emissions"].sum().rename(columns={"d": "country"})
    o_sub = df[df["subject"]].groupby("o", as_index=False)["emissions"].sum().rename(columns={"o": "country"})
    d_sub = df[df["subject"]].groupby("d", as_index=False)["emissions"].sum().rename(columns={"d": "country"})

    c_all = (
        pd.concat([o_all, d_all], ignore_index=True)
          .groupby("country", as_index=False)["emissions"].sum()
          .sort_values("emissions", ascending=False)
    )
    c_sub = (
        pd.concat([o_sub, d_sub], ignore_index=True)
          .groupby("country", as_index=False)["emissions"].sum()
          .sort_values("emissions", ascending=False)
    )

    o_all = o_all.sort_values("emissions", ascending=False)
    d_all = d_all.sort_values("emissions", ascending=False)
    o_sub = o_sub.sort_values("emissions", ascending=False)
    d_sub = d_sub.sort_values("emissions", ascending=False)

    return pair_all, pair_sub, c_all, c_sub, o_all, d_all, o_sub, d_sub

# ============================================================
# LOAD ONCE
# ============================================================
baseline = load_baseline_optional(BASELINE_XLSX)  # optional (can be None)
current = load_current_required(CURRENT_XLSX)     # required
airlines_df, AIRLINES_BY_COUNTRY = load_airlines_optional(AIRLINES_XLSX)

pair_all, pair_sub, c_all, c_sub, o_all, d_all, o_sub, d_sub = build_rankings(current)

countries = sorted(set(current["o"]).union(set(current["d"])))

# ============================================================
# SESSION STATE
# ============================================================
if "A" not in st.session_state:
    st.session_state.A = None
if "B" not in st.session_state:
    st.session_state.B = None

# ============================================================
# HEADER
# ============================================================
st.title("CORSIA State-Pair Emissions Dashboard")
st.caption(
    "Click two countries on the map (A then B), or select via sidebar. "
    "Includes All vs CORSIA-subject modes, rankings, and an optional airlines directory (info only)."
)

# ============================================================
# SIDEBAR CONTROLS
# ============================================================
with st.sidebar:
    st.header("Controls")

    mode = st.radio(
        "Dataset mode",
        ["All emissions", "CORSIA-subject only"],
        index=0,
        key="mode_radio",
    )

    topn = st.slider(
        "Top N (rankings)",
        min_value=5,
        max_value=30,
        value=15,
        key="topn_slider",
    )

    st.divider()
    st.subheader("Select a route (A → B)")

    A_sel = st.selectbox(
        "Origin (A)",
        options=["—"] + countries,
        index=(countries.index(st.session_state.A) + 1) if st.session_state.A in countries else 0,
        key="origin_select",
    )

    B_sel = st.selectbox(
        "Destination (B)",
        options=["—"] + countries,
        index=(countries.index(st.session_state.B) + 1) if st.session_state.B in countries else 0,
        key="dest_select",
    )

    b1, b2, b3 = st.columns(3)
    with b1:
        if st.button("Apply", use_container_width=True, key="apply_btn"):
            st.session_state.A = None if A_sel == "—" else A_sel
            st.session_state.B = None if B_sel == "—" else B_sel
            st.rerun()
    with b2:
        if st.button("Swap", use_container_width=True, key="swap_btn"):
            st.session_state.A, st.session_state.B = st.session_state.B, st.session_state.A
            st.rerun()
    with b3:
        if st.button("Reset", use_container_width=True, key="reset_btn"):
            st.session_state.A = None
            st.session_state.B = None
            st.rerun()

    st.divider()
    st.subheader("Country view")
    country_focus = st.selectbox(
        "Focus country",
        options=["—"] + countries,
        index=0,
        key="country_focus_select",
    )

    st.divider()
    st.subheader("Data availability")
    st.write(f"Current file: {'✅' if file_exists(CURRENT_XLSX) else '❌'} `{CURRENT_XLSX}`")
    st.write(f"Baseline file: {'✅' if file_exists(BASELINE_XLSX) else '⚠️ (optional)'} `{BASELINE_XLSX}`")
    st.write(f"Airlines file: {'✅' if file_exists(AIRLINES_XLSX) else '⚠️ (optional)'} `{AIRLINES_XLSX}`")

# ============================================================
# MODE FILTERS + GLOBAL TOTALS
# ============================================================
df_mode = current.copy()
if mode == "CORSIA-subject only":
    df_mode = df_mode[df_mode["subject"]].copy()

GLOBAL_TOTAL_MODE = df_mode["emissions"].sum()
GLOBAL_TOTAL_ALL = current["emissions"].sum()
GLOBAL_SUBJECT_TOTAL_ALL = current.loc[current["subject"], "emissions"].sum()

# ============================================================
# LAYOUT
# ============================================================
map_col, panel_col = st.columns([1.2, 1], gap="large")

# ============================================================
# MAP
# ============================================================
with map_col:
    dfm = pd.DataFrame({"country": countries})
    dfm["role"] = dfm["country"].apply(
        lambda c: "A" if c == st.session_state.A else "B" if c == st.session_state.B else "Other"
    )

    fig_map = px.scatter_geo(
        dfm,
        locations="country",
        locationmode="country names",
        color="role",
        hover_name="country",
        custom_data=["country"],
    )
    fig_map.update_traces(marker=dict(size=7))
    fig_map.update_layout(height=560, margin=dict(l=10, r=10, t=10, b=10))

    ev_map = st.plotly_chart(
        fig_map,
        on_select="rerun",
        selection_mode="points",
        use_container_width=True,
        key="map_chart",
    )

    # Streamlit returns a dict selection payload when on_select is enabled
    if isinstance(ev_map, dict) and ev_map.get("selection") and ev_map["selection"].get("points"):
        c = ev_map["selection"]["points"][0]["customdata"][0]
        if st.session_state.A is None:
            st.session_state.A = c
        elif st.session_state.B is None and c != st.session_state.A:
            st.session_state.B = c
        else:
            st.session_state.A = c
            st.session_state.B = None
        st.rerun()

    st.markdown(f"**Selected route:** {st.session_state.A or '—'} → {st.session_state.B or '—'}")
    st.caption(
        f"Mode: **{mode}** • Global total (mode): **{fmt_int(GLOBAL_TOTAL_MODE)} tCO₂** • "
        f"Global total (all): **{fmt_int(GLOBAL_TOTAL_ALL)} tCO₂**"
    )

# ============================================================
# RIGHT PANEL (TABS)
# ============================================================
with panel_col:
    tabs = st.tabs(["Selected Pair", "Rankings", "Country view"])

    # ---------------- TAB 1: Selected Pair ----------------
    with tabs[0]:
        if not st.session_state.A or not st.session_state.B:
            st.info("Select two countries on the map (A then B), or use the sidebar dropdowns.")
        else:
            A, B = st.session_state.A, st.session_state.B

            sel_full = current[(current["o"] == A) & (current["d"] == B)].copy()
            total = sel_full["emissions"].sum()
            subject = sel_full.loc[sel_full["subject"], "emissions"].sum()
            nsubject = total - subject

            if mode == "All emissions":
                share_universe = safe_div(total, GLOBAL_TOTAL_ALL) * 100
                universe_total = GLOBAL_TOTAL_ALL
                selected_value = total
                donut_title = "Contribution to global emissions (All)"
            else:
                share_universe = safe_div(subject, GLOBAL_SUBJECT_TOTAL_ALL) * 100
                universe_total = GLOBAL_SUBJECT_TOTAL_ALL
                selected_value = subject
                donut_title = "Contribution to global emissions (Subject-only)"

            subject_share_within_pair = safe_div(subject, total) * 100
            share_subject_global = safe_div(subject, GLOBAL_SUBJECT_TOTAL_ALL) * 100

            st.caption("KPIs (2024). Shares depend on the selected mode.")
            k1, k2, k3, k4 = st.columns(4)
            k1.metric("Pair emissions (total)", f"{fmt_int(total)} tCO₂")
            k2.metric("Pair subject emissions", f"{fmt_int(subject)} tCO₂")
            k3.metric("Share of universe", fmt_pct(share_universe))
            k4.metric("Subject share (within pair)", fmt_pct(subject_share_within_pair))

            fig_donut = px.pie(
                names=["Selected", "Rest of world"],
                values=[selected_value, max(universe_total - selected_value, 0)],
                hole=0.6,
                title=donut_title,
            )
            st.plotly_chart(fig_donut, use_container_width=True, key="donut_selected")

            fig_bar = px.bar(
                pd.DataFrame({"Category": ["Subject", "Not subject"], "Emissions": [subject, nsubject]}),
                x="Category",
                y="Emissions",
                title="Subject vs not subject (selected pair)",
                labels={"Emissions": "tCO₂"},
            )
            st.plotly_chart(fig_bar, use_container_width=True, key="bar_subject_split")

            st.markdown(
                f"""
**Interpretation**  
The state-pair **{A} → {B}** has **{fmt_int(total)} tCO₂** total emissions (subject: **{fmt_int(subject)} tCO₂**).  
Subject share within the pair is **{fmt_pct(subject_share_within_pair)}**.  
Share of global **subject-only** total is **{fmt_pct(share_subject_global)}**.
"""
            )

            st.divider()
            st.subheader("Airlines directory (info only; not linked to emissions)")

            if not AIRLINES_BY_COUNTRY:
                st.info("Airlines file not provided. Add it to enable airline listings.")
            else:
                c1, c2 = st.columns(2)
                with c1:
                    st.caption(f"Attributed to **{A}**")
                    a_list = AIRLINES_BY_COUNTRY.get(A, [])
                    st.metric("Airline count", len(a_list))
                    if a_list:
                        st.dataframe(pd.DataFrame({"Airline": a_list}), use_container_width=True, height=260)
                    else:
                        st.warning("No airlines found for this country name. Add an alias in COUNTRY_ALIAS if needed.")
                with c2:
                    st.caption(f"Attributed to **{B}**")
                    b_list = AIRLINES_BY_COUNTRY.get(B, [])
                    st.metric("Airline count", len(b_list))
                    if b_list:
                        st.dataframe(pd.DataFrame({"Airline": b_list}), use_container_width=True, height=260)
                    else:
                        st.warning("No airlines found for this country name. Add an alias in COUNTRY_ALIAS if needed.")

    # ---------------- TAB 2: Rankings ----------------
    with tabs[1]:
        st.subheader("Rankings (2024)")

        if mode == "All emissions":
            pairs = pair_all.head(topn).copy()
            countries_rank = c_all.head(topn).copy()
            origins_rank = o_all.head(topn).copy()
            dests_rank = d_all.head(topn).copy()
            universe_label = "All emissions"
        else:
            pairs = pair_sub.head(topn).copy()
            countries_rank = c_sub.head(topn).copy()
            origins_rank = o_sub.head(topn).copy()
            dests_rank = d_sub.head(topn).copy()
            universe_label = "CORSIA-subject only"

        pairs["pair"] = pairs["o"] + " → " + pairs["d"]

        plot_pairs = pairs.sort_values("emissions").reset_index(drop=True)
        fig_pairs = px.bar(
            plot_pairs,
            x="emissions",
            y="pair",
            orientation="h",
            title=f"Top {topn} directed state-pairs by emissions ({universe_label})",
            labels={"emissions": "tCO₂", "pair": "State-pair"},
            custom_data=["o", "d"],
        )
        fig_pairs.update_layout(height=520, margin=dict(l=10, r=10, t=60, b=10))

        ev_pairs = st.plotly_chart(
            fig_pairs,
            on_select="rerun",
            selection_mode="points",
            use_container_width=True,
            key="rank_pairs_chart",
        )

        # Click bar to set A/B
        if isinstance(ev_pairs, dict) and ev_pairs.get("selection") and ev_pairs["selection"].get("points"):
            idx = ev_pairs["selection"]["points"][0]["pointIndex"]
            row = plot_pairs.iloc[idx]
            st.session_state.A = row["o"]
            st.session_state.B = row["d"]
            st.rerun()

        plot_c = countries_rank.sort_values("emissions").reset_index(drop=True)
        fig_c = px.bar(
            plot_c,
            x="emissions",
            y="country",
            orientation="h",
            title=f"Top {topn} countries by involvement (origin + destination) ({universe_label})",
            labels={"emissions": "tCO₂", "country": "Country"},
        )
        fig_c.update_layout(height=520, margin=dict(l=10, r=10, t=60, b=10))
        st.plotly_chart(fig_c, use_container_width=True, key="rank_countries_chart")

        with st.expander("Origin-only and destination-only rankings"):
            cc1, cc2 = st.columns(2)
            with cc1:
                plot_o = origins_rank.sort_values("emissions").reset_index(drop=True)
                fig_o = px.bar(
                    plot_o,
                    x="emissions",
                    y="country",
                    orientation="h",
                    title=f"Top {topn} origins ({universe_label})",
                    labels={"emissions": "tCO₂"},
                )
                fig_o.update_layout(height=420, margin=dict(l=10, r=10, t=60, b=10))
                st.plotly_chart(fig_o, use_container_width=True, key="rank_origins_chart")

            with cc2:
                plot_d = dests_rank.sort_values("emissions").reset_index(drop=True)
                fig_d = px.bar(
                    plot_d,
                    x="emissions",
                    y="country",
                    orientation="h",
                    title=f"Top {topn} destinations ({universe_label})",
                    labels={"emissions": "tCO₂"},
                )
                fig_d.update_layout(height=420, margin=dict(l=10, r=10, t=60, b=10))
                st.plotly_chart(fig_d, use_container_width=True, key="rank_dests_chart")

        st.divider()
        st.subheader("Airlines directory stats (info only)")

        if airlines_df is None or airlines_df.empty:
            st.info("Airlines file not provided. Add it to enable airline stats.")
        else:
            air_ct = (
                airlines_df.groupby("country")["airline"]
                  .nunique()
                  .reset_index(name="airline_count")
                  .sort_values("airline_count", ascending=False)
                  .head(topn)
            )

            fig_air = px.bar(
                air_ct.sort_values("airline_count"),
                x="airline_count",
                y="country",
                orientation="h",
                title=f"Top {topn} countries by airline count (NOT emissions)",
                labels={"airline_count": "Number of airlines", "country": "Country"},
            )
            fig_air.update_layout(height=520, margin=dict(l=10, r=10, t=60, b=10))
            st.plotly_chart(fig_air, use_container_width=True, key="rank_airlines_count_chart")

    # ---------------- TAB 3: Country view ----------------
    with tabs[2]:
        if country_focus == "—":
            st.info("Select one country in the sidebar to see top outgoing/incoming routes and optional airline listings.")
        else:
            C = country_focus

            outgoing = (
                df_mode[df_mode["o"] == C]
                .groupby(["o", "d"], as_index=False)["emissions"].sum()
                .sort_values("emissions", ascending=False)
                .head(topn)
            )
            incoming = (
                df_mode[df_mode["d"] == C]
                .groupby(["o", "d"], as_index=False)["emissions"].sum()
                .sort_values("emissions", ascending=False)
                .head(topn)
            )

            out_total = df_mode[df_mode["o"] == C]["emissions"].sum()
            in_total = df_mode[df_mode["d"] == C]["emissions"].sum()
            involvement = out_total + in_total
            share_universe = safe_div(involvement, GLOBAL_TOTAL_MODE) * 100

            k1, k2, k3, k4 = st.columns(4)
            k1.metric("Outgoing total", f"{fmt_int(out_total)} tCO₂")
            k2.metric("Incoming total", f"{fmt_int(in_total)} tCO₂")
            k3.metric("Involvement (out + in)", f"{fmt_int(involvement)} tCO₂")
            k4.metric("Share of universe", fmt_pct(share_universe))

            col1, col2 = st.columns(2)

            with col1:
                st.subheader("Top outgoing routes")
                if outgoing.empty:
                    st.warning("No outgoing routes found in this mode.")
                else:
                    outgoing = outgoing.copy()
                    outgoing["pair"] = outgoing["o"] + " → " + outgoing["d"]
                    plot_out = outgoing.sort_values("emissions").reset_index(drop=True)

                    fig_out = px.bar(
                        plot_out,
                        x="emissions",
                        y="pair",
                        orientation="h",
                        title=f"Top outgoing routes from {C} ({mode})",
                        labels={"emissions": "tCO₂", "pair": "Route"},
                        custom_data=["o", "d"],
                    )
                    fig_out.update_layout(height=520, margin=dict(l=10, r=10, t=60, b=10))

                    ev_out = st.plotly_chart(
                        fig_out,
                        on_select="rerun",
                        selection_mode="points",
                        use_container_width=True,
                        key="country_out_chart",
                    )

                    if isinstance(ev_out, dict) and ev_out.get("selection") and ev_out["selection"].get("points"):
                        idx = ev_out["selection"]["points"][0]["pointIndex"]
                        row = plot_out.iloc[idx]
                        st.session_state.A = row["o"]
                        st.session_state.B = row["d"]
                        st.rerun()

            with col2:
                st.subheader("Top incoming routes")
                if incoming.empty:
                    st.warning("No incoming routes found in this mode.")
                else:
                    incoming = incoming.copy()
                    incoming["pair"] = incoming["o"] + " → " + incoming["d"]
                    plot_in = incoming.sort_values("emissions").reset_index(drop=True)

                    fig_in = px.bar(
                        plot_in,
                        x="emissions",
                        y="pair",
                        orientation="h",
                        title=f"Top incoming routes to {C} ({mode})",
                        labels={"emissions": "tCO₂", "pair": "Route"},
                        custom_data=["o", "d"],
                    )
                    fig_in.update_layout(height=520, margin=dict(l=10, r=10, t=60, b=10))

                    ev_in = st.plotly_chart(
                        fig_in,
                        on_select="rerun",
                        selection_mode="points",
                        use_container_width=True,
                        key="country_in_chart",
                    )

                    if isinstance(ev_in, dict) and ev_in.get("selection") and ev_in["selection"].get("points"):
                        idx = ev_in["selection"]["points"][0]["pointIndex"]
                        row = plot_in.iloc[idx]
                        st.session_state.A = row["o"]
                        st.session_state.B = row["d"]
                        st.rerun()

            st.divider()
            st.subheader("Airlines attributed to this country (info only; not linked to emissions)")

            if not AIRLINES_BY_COUNTRY:
                st.info("Airlines file not provided. Add it to enable airline listings.")
            else:
                alist = AIRLINES_BY_COUNTRY.get(C, [])
                st.metric("Airline count", len(alist))

                q = st.text_input(
                    "Search airline name",
                    value="",
                    placeholder="Type to filter airlines…",
                    key="airline_search_country",
                )

                filtered = [x for x in alist if q.lower() in x.lower()] if q.strip() else alist

                if filtered:
                    st.dataframe(pd.DataFrame({"Airline": filtered}), use_container_width=True, height=360)
                else:
                    st.info("No airlines found (or no match). Add COUNTRY_ALIAS mappings if country names differ.")

# ============================================================
# FOOTER NOTES
# ============================================================
with st.expander("Notes / Definitions"):
    st.write(
        """
- **All emissions**: subject + not subject (total international aviation CO₂ in the dataset).
- **CORSIA-subject only**: includes only rows where `subject=True`.
- **Country involvement**: outgoing + incoming (origin + destination). Useful to identify dominant countries in the network.
- **Airlines directory**: a separate attribution list shown for context only; it is **not** claimed to cause the emissions shown.
- Click bars in Rankings/Country view to auto-select a route (A → B).
- If a country appears in emissions but not in airlines, add a name mapping in `COUNTRY_ALIAS`.
"""
    )
