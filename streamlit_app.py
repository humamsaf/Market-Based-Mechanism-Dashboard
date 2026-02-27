import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import datetime
from utils.paths import data_path, repo_root

st.set_page_config(
    page_title="Global Market-Based Mechanism Dashboard",
    page_icon="🌍",
    layout="wide",
)

# -----------------------------
# CONFIG
# -----------------------------
PAGES = {
    "MBM National": "pages/1_MBM_National.py",
    "CORSIA": "pages/2_CORSIA.py",
    "CDM": "pages/3_CDM.py",
    "About / Methods": "pages/4_About.py",
}

required_files = {
    "MBM master": "Global Market Based Mechanism.xlsx",
    "CORSIA baseline (2019–2020)": "2019_2020_CO2_StatePairs_table_Nov2021.xlsx",
    "CORSIA current (2024)": "2024_CO2_StatePairs_table.xlsx",
    "CORSIA airlines attribution": "CORSIA_AO_to_State_Attributions_10ed_web-2_extracted.xlsx",
    "CDM": "CDM.xlsx",
}

# -----------------------------
# HELPERS
# -----------------------------
def file_info(path: Path):
    if not path.exists():
        return {"exists": False}
    stat = path.stat()
    return {
        "exists": True,
        "size_mb": stat.st_size / (1024 * 1024),
        "modified": datetime.fromtimestamp(stat.st_mtime),
    }

@st.cache_data(show_spinner=False)
def load_light_stats():
    """
    Jangan load data berat di landing page.
    Cuma hitung statistik ringan yang cepat.
    """
    stats = {}

    # MBM
    mbm_p = Path(data_path(required_files["MBM master"]))
    if mbm_p.exists():
        try:
            df = pd.read_excel(mbm_p, sheet_name=0)
            # Sesuaikan nama kolom kalau berbeda
            stats["mbm_instruments"] = df["Instrument name"].nunique() if "Instrument name" in df.columns else len(df)
            stats["mbm_jurisdictions"] = df["Jurisdiction"].nunique() if "Jurisdiction" in df.columns else None
        except Exception:
            stats["mbm_instruments"] = None
            stats["mbm_jurisdictions"] = None

    # CORSIA current
    corsia_cur = Path(data_path(required_files["CORSIA current (2024)"]))
    if corsia_cur.exists():
        try:
            df = pd.read_excel(corsia_cur, sheet_name=0)
            # sesuaikan: misal ada kolom "CO2 emissions (tonnes)"
            co2_col = None
            for c in df.columns:
                if "CO2" in str(c) and "ton" in str(c).lower():
                    co2_col = c
                    break
            stats["corsia_pairs_2024"] = len(df)
            stats["corsia_total_2024"] = float(df[co2_col].sum()) if co2_col else None
        except Exception:
            stats["corsia_pairs_2024"] = None
            stats["corsia_total_2024"] = None

    # CDM
    cdm_p = Path(data_path(required_files["CDM"]))
    if cdm_p.exists():
        try:
            df = pd.read_excel(cdm_p, sheet_name=0)
            stats["cdm_rows"] = len(df)
            # kalau ada kolom host party / sector, bisa tambahkan
            stats["cdm_hosts"] = df["Host Party"].nunique() if "Host Party" in df.columns else None
        except Exception:
            stats["cdm_rows"] = None
            stats["cdm_hosts"] = None

    return stats

def fmt_int(x):
    return "—" if x is None else f"{int(x):,}"

def fmt_float(x):
    return "—" if x is None else f"{x:,.0f}"

# -----------------------------
# HEADER
# -----------------------------
st.title("🌍 Global Market-Based Mechanism Dashboard")
st.caption("Landing page (summary hub) untuk 4 halaman utama: MBM National • CORSIA • CDM • About/Methods")

# -----------------------------
# DATA HEALTH SUMMARY
# -----------------------------
info = {k: file_info(Path(data_path(v))) for k, v in required_files.items()}
present = sum(1 for v in info.values() if v.get("exists"))
total = len(required_files)

left, right = st.columns([2, 1])
with left:
    st.markdown("### ✅ Data readiness")
    st.progress(present / total)
    st.write(f"Files present: **{present}/{total}**")
with right:
    st.markdown("### 📁 Repo")
    st.code(str(repo_root()))

# Expandable detail
with st.expander("Lihat detail status file"):
    for label, fname in required_files.items():
        p = Path(data_path(fname))
        fi = info[label]
        if not fi.get("exists"):
            st.error(f"Missing: {label} — {fname}")
        else:
            st.success(f"OK: {label} — {fname}")
            st.write(f"- Size: {fi['size_mb']:.2f} MB")
            st.write(f"- Modified: {fi['modified']}")

# -----------------------------
# KPI CARDS
# -----------------------------
stats = load_light_stats()

c1, c2, c3, c4 = st.columns(4)
c1.metric("MBM instruments", fmt_int(stats.get("mbm_instruments")))
c1.metric("MBM jurisdictions", fmt_int(stats.get("mbm_jurisdictions")))

c2.metric("CORSIA pairs (2024)", fmt_int(stats.get("corsia_pairs_2024")))
c2.metric("CORSIA CO₂ total (2024, t)", fmt_float(stats.get("corsia_total_2024")))

c3.metric("CDM rows", fmt_int(stats.get("cdm_rows")))
c3.metric("CDM host parties", fmt_int(stats.get("cdm_hosts")))

c4.metric("Files present", f"{present}/{total}")
c4.caption("Landing page hanya hitung statistik ringan (fast).")

st.divider()

# -----------------------------
# NAVIGATION TILES
# -----------------------------
st.subheader("🚀 Quick navigation")

nav_cols = st.columns(4)
for i, (title, path) in enumerate(PAGES.items()):
    with nav_cols[i]:
        st.markdown(f"#### {title}")
        st.caption("Open the module")
        if st.button(f"Open {title}", use_container_width=True, key=f"nav_{i}"):
            st.switch_page(path)

st.divider()

# -----------------------------
# OPTIONAL: Quick notes / changelog
# -----------------------------
st.subheader("📝 Notes")
sst.info(
    "Saran: taruh ringkasan metodologi..."
)

st.divider()
st.info("Buka menu di sidebar untuk masuk ke masing-masing dashboard: MBM National / CORSIA / CDM.")
