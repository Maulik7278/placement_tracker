import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.data_loader import get_data, apply_filters, compute_kpis, load_sample_data
from utils.api_fetcher import fetch_job_market_data, compare_campus_vs_market

st.set_page_config(
    page_title="College Placement Tracker",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
.main-header {
    background: linear-gradient(135deg, #1B4F72 0%, #2E86C1 100%);
    padding: 1.5rem 2rem;
    border-radius: 12px;
    color: white;
    margin-bottom: 1.5rem;
}
.main-header h1 { margin: 0; font-size: 2rem; }
.main-header p { margin: 0.3rem 0 0; opacity: 0.85; font-size: 1rem; }
.kpi-card {
    background: white;
    border-radius: 10px;
    padding: 1rem;
    box-shadow: 0 2px 8px rgba(27,79,114,0.10);
    border-left: 4px solid #1B4F72;
    margin-bottom: 0.5rem;
}
.section-title {
    color: #1B4F72;
    font-size: 1.2rem;
    font-weight: 700;
    border-bottom: 2px solid #D6EAF8;
    padding-bottom: 0.4rem;
    margin: 1.2rem 0 0.8rem;
}
</style>
""", unsafe_allow_html=True)

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🎓 Placement Tracker")
    st.markdown("---")
    st.markdown("### 📂 Upload Your Data")
    uploaded_file = st.file_uploader(
        "Upload CSV or Excel file",
        type=["csv", "xlsx"],
        help="Columns needed: Year, Branch, Student_Name, CGPA, Company, Role, Package_LPA, Placement_Type, City"
    )

    df_full = get_data(uploaded_file)

    st.markdown("---")
    st.markdown("### 🔍 Filters")

    all_years = sorted(df_full["Year"].unique().tolist())
    years = st.multiselect("📅 Year", all_years, default=all_years)

    all_branches = sorted(df_full["Branch"].unique().tolist())
    branches = st.multiselect("🏫 Branch", all_branches, default=all_branches)

    all_types = sorted(df_full["Placement_Type"].unique().tolist())
    placement_types = st.multiselect("📋 Placement Type", all_types, default=all_types)

    pkg_min = float(df_full["Package_LPA"].min())
    pkg_max = float(df_full["Package_LPA"].max())
    pkg_range = st.slider("💰 Package Range (LPA)", pkg_min, pkg_max, (pkg_min, pkg_max), step=0.5)

    cgpa_min = float(df_full["CGPA"].min())
    cgpa_max = float(df_full["CGPA"].max())
    cgpa_range = st.slider("📊 CGPA Range", cgpa_min, cgpa_max, (cgpa_min, cgpa_max), step=0.1)

    st.markdown("---")

    @st.cache_data
    def convert_df(df):
        return df.to_csv(index=False).encode("utf-8")

    df_filtered_for_download = apply_filters(df_full, years, branches, placement_types, pkg_range, cgpa_range)
    csv_bytes = convert_df(df_filtered_for_download)
    st.download_button(
        label="⬇️ Download Filtered Data",
        data=csv_bytes,
        file_name="filtered_placement_data.csv",
        mime="text/csv"
    )

    using_sample = uploaded_file is None
    if using_sample:
        st.info("📌 Using sample data. Upload your own CSV to analyze real data.")

# ── Apply filters ─────────────────────────────────────────────────────────────
df = apply_filters(df_full, years, branches, placement_types, pkg_range, cgpa_range)

# Previous year delta
current_year_max = max(years) if years else df_full["Year"].max()
prev_year = current_year_max - 1
df_prev = df_full[df_full["Year"] == prev_year] if prev_year in df_full["Year"].values else None

kpis = compute_kpis(df, df_prev)

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="main-header">
    <h1>🎓 College Placement Tracker</h1>
    <p>A data-driven dashboard for placement cells &amp; students</p>
</div>
""", unsafe_allow_html=True)

if df.empty:
    st.warning("⚠️ No data matches the current filters. Please adjust the sidebar filters.")
    st.stop()

# ── KPI Row ───────────────────────────────────────────────────────────────────
st.markdown('<div class="section-title">📈 Key Metrics</div>', unsafe_allow_html=True)
c1, c2, c3, c4, c5 = st.columns(5)
d = kpis["deltas"]

with c1:
    st.metric("🎓 Total Placed", kpis["total_placed"],
              delta=f"{d['total']:+}" if d["total"] is not None else None)
with c2:
    st.metric("💰 Avg Package (LPA)", f"₹{kpis['avg_pkg']}",
              delta=f"{d['avg_pkg']:+}" if d["avg_pkg"] is not None else None)
with c3:
    st.metric("🏆 Highest Package (LPA)", f"₹{kpis['max_pkg']}",
              delta=f"{d['max_pkg']:+}" if d["max_pkg"] is not None else None)
with c4:
    st.metric("📊 Placement %", f"{kpis['placement_pct']}%",
              delta=f"{d['pct']:+}%" if d["pct"] is not None else None)
with c5:
    st.metric("🏢 Unique Companies", kpis["unique_companies"],
              delta=f"{d['companies']:+}" if d["companies"] is not None else None)

st.markdown("---")

# ── Trend Charts ──────────────────────────────────────────────────────────────
st.markdown('<div class="section-title">📊 Placement Trends</div>', unsafe_allow_html=True)
col1, col2 = st.columns(2)

with col1:
    trend = df.groupby("Year").agg(
        Total_Placed=("Student_Name", "count"),
        Avg_Package=("Package_LPA", "mean")
    ).reset_index()
    trend["Avg_Package"] = trend["Avg_Package"].round(2)
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=trend["Year"], y=trend["Total_Placed"],
        mode="lines+markers+text", name="Students Placed",
        text=trend["Total_Placed"], textposition="top center",
        line=dict(color="#1B4F72", width=3),
        marker=dict(size=10, color="#1B4F72")
    ))
    fig.update_layout(
        title="Year-on-Year Placement Trend",
        xaxis_title="Year", yaxis_title="Students Placed",
        plot_bgcolor="white", height=340,
        xaxis=dict(tickmode="array", tickvals=trend["Year"].tolist())
    )
    st.plotly_chart(fig, use_container_width=True)

with col2:
    branch_pkg = df.groupby("Branch")["Package_LPA"].mean().reset_index().sort_values("Package_LPA", ascending=True)
    branch_pkg["Package_LPA"] = branch_pkg["Package_LPA"].round(2)
    fig2 = px.bar(
        branch_pkg, x="Package_LPA", y="Branch", orientation="h",
        title="Branch-wise Average Package (LPA)",
        color="Package_LPA", color_continuous_scale="Blues",
        text="Package_LPA"
    )
    fig2.update_traces(texttemplate="₹%{text}", textposition="outside")
    fig2.update_layout(plot_bgcolor="white", height=340, coloraxis_showscale=False,
                       xaxis_title="Avg Package (LPA)", yaxis_title="")
    st.plotly_chart(fig2, use_container_width=True)

# ── CGPA vs Package & Placement Type ─────────────────────────────────────────
col3, col4 = st.columns(2)

with col3:
    fig3 = px.scatter(
        df, x="CGPA", y="Package_LPA", color="Branch",
        size="Package_LPA", hover_data=["Student_Name", "Company", "Role"],
        title="CGPA vs Package (LPA)",
        color_discrete_sequence=px.colors.qualitative.Bold,
        size_max=18
    )
    fig3.update_layout(plot_bgcolor="white", height=360,
                       xaxis_title="CGPA", yaxis_title="Package (LPA)")
    st.plotly_chart(fig3, use_container_width=True)

with col4:
    type_counts = df["Placement_Type"].value_counts().reset_index()
    type_counts.columns = ["Placement_Type", "Count"]
    fig4 = px.pie(
        type_counts, names="Placement_Type", values="Count",
        title="Placement Type Distribution",
        color_discrete_sequence=["#1B4F72", "#2E86C1", "#85C1E9"],
        hole=0.4
    )
    fig4.update_traces(textposition="inside", textinfo="percent+label")
    fig4.update_layout(height=360)
    st.plotly_chart(fig4, use_container_width=True)

# ── Top Companies ─────────────────────────────────────────────────────────────
st.markdown('<div class="section-title">🏢 Top Recruiting Companies</div>', unsafe_allow_html=True)
col5, col6 = st.columns(2)

with col5:
    top_companies = df["Company"].value_counts().head(10).reset_index()
    top_companies.columns = ["Company", "Offers"]
    fig5 = px.bar(
        top_companies, x="Offers", y="Company", orientation="h",
        title="Top 10 Companies by Offer Count",
        color="Offers", color_continuous_scale="Blues", text="Offers"
    )
    fig5.update_traces(textposition="outside")
    fig5.update_layout(plot_bgcolor="white", height=380, coloraxis_showscale=False,
                       yaxis=dict(autorange="reversed"), yaxis_title="", xaxis_title="Offers")
    st.plotly_chart(fig5, use_container_width=True)

with col6:
    pkg_hist = df["Package_LPA"].copy()
    fig6 = px.histogram(
        df, x="Package_LPA", nbins=20,
        title="Package Distribution (LPA)",
        color_discrete_sequence=["#1B4F72"]
    )
    fig6.update_layout(plot_bgcolor="white", height=380,
                       xaxis_title="Package (LPA)", yaxis_title="Number of Students",
                       bargap=0.05)
    st.plotly_chart(fig6, use_container_width=True)

# ── Live API Section ──────────────────────────────────────────────────────────
st.markdown('<div class="section-title">🌐 Live Market Benchmark (API)</div>', unsafe_allow_html=True)

with st.spinner("Fetching live market data..."):
    api_data = fetch_job_market_data()

live = api_data["live_info"]
status_icon = "🟢" if live.get("status") == "live" else "🟡"
st.info(f"{status_icon} **API Source:** {live.get('source', 'N/A')} | "
        f"**Fetched at:** {live.get('time', 'N/A')} | "
        f"**Status:** {live.get('status', 'N/A').upper()}")

with st.expander("🔍 Raw API Response"):
    st.json(live)

comparison = compare_campus_vs_market(df)
if comparison is not None and not comparison.empty:
    st.markdown("**Campus Package vs Market Benchmark by Role**")
    display_cols = ["Role", "Campus_Avg_LPA", "Market_Benchmark_LPA", "Difference_LPA", "Status"]
    st.dataframe(
        comparison[display_cols].reset_index(drop=True),
        use_container_width=True,
        height=300
    )

st.markdown("---")
st.caption("💡 **College Placement Tracker** | Built with Streamlit & Plotly | Data refreshes on upload")
