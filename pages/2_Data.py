import streamlit as st
import pandas as pd
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from utils.data_loader import get_data, apply_filters, range_slider

st.set_page_config(page_title="Data | Placement Tracker", page_icon="📋", layout="wide")

st.markdown("""
<style>
.section-title {
    color: #1B4F72; font-size: 1.2rem; font-weight: 700;
    border-bottom: 2px solid #D6EAF8; padding-bottom: 0.4rem; margin: 1.2rem 0 0.8rem;
}
</style>
""", unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🎓 Placement Tracker")
    st.markdown("---")
    st.markdown("### 🌐 Data Source")
    df_full = get_data()
    st.caption(f"Live from API · {len(df_full)} student records")
    if st.button("🔄 Refresh data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    st.markdown("---")
    st.markdown("### 🔍 Filters")
    all_years = sorted(df_full["Year"].unique().tolist())
    years = st.multiselect("📅 Year", all_years, default=all_years)
    all_branches = sorted(df_full["Branch"].unique().tolist())
    branches = st.multiselect("🏫 Branch", all_branches, default=all_branches)
    all_types = sorted(df_full["Placement_Type"].unique().tolist())
    placement_types = st.multiselect("📋 Placement Type", all_types, default=all_types)
    pkg_range = range_slider("💰 Package Range (LPA)", df_full["Package_LPA"], 0.5)
    cgpa_range = range_slider("📊 CGPA Range", df_full["CGPA"], 0.1)
    st.markdown("---")

df = apply_filters(df_full, years, branches, placement_types, pkg_range, cgpa_range)

st.markdown("# 📋 Raw Data & Export")
st.caption("Browse, search, and download the filtered placement dataset.")

if df.empty:
    st.warning("⚠️ No data matches the current filters.")
    st.stop()

# ── Download buttons ──────────────────────────────────────────────────────────
@st.cache_data
def to_csv(data):
    return data.to_csv(index=False).encode("utf-8")

col_a, col_b, col_c = st.columns([2, 1, 1])
with col_a:
    st.info(f"📊 Showing **{len(df)}** records out of **{len(df_full)}** total")
with col_b:
    st.download_button(
        "⬇️ Download Filtered CSV", to_csv(df),
        "filtered_placement_data.csv", "text/csv", use_container_width=True
    )
with col_c:
    st.download_button(
        "⬇️ Download Full Dataset", to_csv(df_full),
        "full_placement_data.csv", "text/csv", use_container_width=True
    )

st.markdown('<div class="section-title">📄 Filtered Data Table</div>', unsafe_allow_html=True)
st.dataframe(
    df.reset_index(drop=True),
    use_container_width=True,
    height=420,
    column_config={
        "Package_LPA": st.column_config.NumberColumn("Package (LPA)", format="₹%.2f"),
        "CGPA": st.column_config.NumberColumn("CGPA", format="%.2f"),
        "Year": st.column_config.NumberColumn("Year", format="%d"),
    }
)

# ── Summary Stats ─────────────────────────────────────────────────────────────
st.markdown('<div class="section-title">📊 Summary Statistics</div>', unsafe_allow_html=True)
col1, col2 = st.columns(2)

with col1:
    st.markdown("**Numerical Columns**")
    num_stats = df[["CGPA","Package_LPA"]].describe().round(2)
    num_stats.columns = ["CGPA","Package (LPA)"]
    st.table(num_stats)

with col2:
    st.markdown("**Categorical Breakdown**")
    cat_summary = pd.DataFrame({
        "Column": ["Branch","Placement Type","Company","City","Role"],
        "Unique Values": [
            df["Branch"].nunique(), df["Placement_Type"].nunique(),
            df["Company"].nunique(), df["City"].nunique(), df["Role"].nunique()
        ],
        "Most Common": [
            df["Branch"].mode()[0] if len(df) > 0 else "-",
            df["Placement_Type"].mode()[0] if len(df) > 0 else "-",
            df["Company"].mode()[0] if len(df) > 0 else "-",
            df["City"].mode()[0] if len(df) > 0 else "-",
            df["Role"].mode()[0] if len(df) > 0 else "-",
        ]
    })
    st.table(cat_summary)

# ── Branch Summary Table ──────────────────────────────────────────────────────
st.markdown('<div class="section-title">🏫 Branch-wise Summary</div>', unsafe_allow_html=True)
branch_summary = df.groupby("Branch").agg(
    Total_Placed=("Student_Name","count"),
    Avg_Package=("Package_LPA","mean"),
    Max_Package=("Package_LPA","max"),
    Min_Package=("Package_LPA","min"),
    Avg_CGPA=("CGPA","mean"),
    Unique_Companies=("Company","nunique")
).reset_index()
branch_summary = branch_summary.round(2)
branch_summary.columns = ["Branch","Total Placed","Avg Pkg (LPA)","Max Pkg (LPA)",
                           "Min Pkg (LPA)","Avg CGPA","Unique Companies"]
st.dataframe(branch_summary, use_container_width=True)

# ── Company Summary Table ─────────────────────────────────────────────────────
st.markdown('<div class="section-title">🏢 Company-wise Summary</div>', unsafe_allow_html=True)
company_summary = df.groupby(["Company","City"]).agg(
    Offers=("Student_Name","count"),
    Avg_Package=("Package_LPA","mean"),
    Max_Package=("Package_LPA","max")
).reset_index().sort_values("Offers", ascending=False)
company_summary = company_summary.round(2)
company_summary.columns = ["Company","City","Offers","Avg Pkg (LPA)","Max Pkg (LPA)"]
st.dataframe(company_summary, use_container_width=True, height=320)

st.markdown("---")
st.caption("📌 Tip: Use sidebar filters to narrow down data. Download buttons export the currently visible filtered data.")
