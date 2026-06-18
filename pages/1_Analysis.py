import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from streamlit_folium import st_folium
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from utils.data_loader import get_data, apply_filters
from utils.map_builder import build_placement_map, build_company_map

st.set_page_config(page_title="Analysis | Placement Tracker", page_icon="📊", layout="wide")

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
    st.markdown("### 📂 Upload Your Data")
    uploaded_file = st.file_uploader("Upload CSV or Excel", type=["csv", "xlsx"])
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

    df_dl = apply_filters(df_full, years, branches, placement_types, pkg_range, cgpa_range)
    st.download_button("⬇️ Download Filtered Data", convert_df(df_dl),
                       "filtered_placement_data.csv", "text/csv")

df = apply_filters(df_full, years, branches, placement_types, pkg_range, cgpa_range)

st.markdown("# 📊 Deep-Dive Analysis")
st.caption("Explore detailed charts, trends, and an interactive map of recruitment activity.")

if df.empty:
    st.warning("⚠️ No data matches the current filters.")
    st.stop()

tab1, tab2, tab3, tab4 = st.tabs(["📈 Trends", "🏢 Companies", "👨‍🎓 Student Insights", "🗺️ Map"])

# ── Tab 1: Trends ─────────────────────────────────────────────────────────────
with tab1:
    st.markdown('<div class="section-title">Year-on-Year Breakdown</div>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)

    with col1:
        year_branch = df.groupby(["Year", "Branch"])["Package_LPA"].mean().reset_index()
        year_branch["Package_LPA"] = year_branch["Package_LPA"].round(2)
        fig = px.line(
            year_branch, x="Year", y="Package_LPA", color="Branch",
            markers=True, title="Avg Package Trend by Branch (Year-wise)",
            color_discrete_sequence=px.colors.qualitative.Bold
        )
        fig.update_layout(plot_bgcolor="white", height=380, yaxis_title="Avg Package (LPA)")
        fig.update_xaxes(tickmode="array", tickvals=year_branch["Year"].unique().tolist())
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        year_type = df.groupby(["Year", "Placement_Type"]).size().reset_index(name="Count")
        fig2 = px.bar(
            year_type, x="Year", y="Count", color="Placement_Type",
            title="Placement Type Count per Year", barmode="group",
            color_discrete_sequence=["#1B4F72", "#2E86C1", "#85C1E9"]
        )
        fig2.update_layout(plot_bgcolor="white", height=380)
        fig2.update_xaxes(tickmode="array", tickvals=year_type["Year"].unique().tolist())
        st.plotly_chart(fig2, use_container_width=True)

    col3, col4 = st.columns(2)
    with col3:
        branch_year_count = df.groupby(["Year", "Branch"]).size().reset_index(name="Placed")
        fig3 = px.area(
            branch_year_count, x="Year", y="Placed", color="Branch",
            title="Placement Volume by Branch Over Years",
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        fig3.update_layout(plot_bgcolor="white", height=350)
        fig3.update_xaxes(tickmode="array", tickvals=branch_year_count["Year"].unique().tolist())
        st.plotly_chart(fig3, use_container_width=True)

    with col4:
        branch_pct = df.groupby("Branch")["Package_LPA"].agg(["mean","max","min"]).reset_index()
        branch_pct.columns = ["Branch","Avg","Max","Min"]
        branch_pct = branch_pct.round(2)
        fig4 = go.Figure()
        fig4.add_trace(go.Bar(name="Avg", x=branch_pct["Branch"], y=branch_pct["Avg"],
                              marker_color="#2E86C1"))
        fig4.add_trace(go.Bar(name="Max", x=branch_pct["Branch"], y=branch_pct["Max"],
                              marker_color="#1B4F72"))
        fig4.add_trace(go.Bar(name="Min", x=branch_pct["Branch"], y=branch_pct["Min"],
                              marker_color="#85C1E9"))
        fig4.update_layout(barmode="group", title="Min / Avg / Max Package by Branch",
                           plot_bgcolor="white", height=350, yaxis_title="LPA")
        st.plotly_chart(fig4, use_container_width=True)

# ── Tab 2: Companies ──────────────────────────────────────────────────────────
with tab2:
    st.markdown('<div class="section-title">Company-Level Analysis</div>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)

    with col1:
        top20 = df.groupby("Company")["Package_LPA"].agg(["mean","count"]).reset_index()
        top20.columns = ["Company","Avg_Package","Offers"]
        top20 = top20.sort_values("Offers", ascending=False).head(15)
        top20["Avg_Package"] = top20["Avg_Package"].round(2)
        fig = px.scatter(
            top20, x="Offers", y="Avg_Package", size="Offers",
            text="Company", title="Companies: Offer Count vs Avg Package",
            color="Avg_Package", color_continuous_scale="Blues", size_max=40
        )
        fig.update_traces(textposition="top center", textfont_size=9)
        fig.update_layout(plot_bgcolor="white", height=420,
                          xaxis_title="Number of Offers", yaxis_title="Avg Package (LPA)")
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        top_pkg = df.groupby("Company")["Package_LPA"].mean().reset_index()
        top_pkg.columns = ["Company","Avg_Package"]
        top_pkg = top_pkg.sort_values("Avg_Package", ascending=False).head(10)
        top_pkg["Avg_Package"] = top_pkg["Avg_Package"].round(2)
        fig2 = px.bar(
            top_pkg, x="Avg_Package", y="Company", orientation="h",
            title="Top 10 Companies by Avg Package",
            color="Avg_Package", color_continuous_scale="Blues", text="Avg_Package"
        )
        fig2.update_traces(texttemplate="₹%{text} LPA", textposition="outside")
        fig2.update_layout(plot_bgcolor="white", height=420, coloraxis_showscale=False,
                           yaxis=dict(autorange="reversed"), xaxis_title="Avg Package (LPA)")
        st.plotly_chart(fig2, use_container_width=True)

    st.markdown('<div class="section-title">Role Distribution</div>', unsafe_allow_html=True)
    col3, col4 = st.columns(2)
    with col3:
        role_count = df["Role"].value_counts().reset_index()
        role_count.columns = ["Role","Count"]
        fig3 = px.pie(role_count, names="Role", values="Count",
                      title="Role Distribution", hole=0.35,
                      color_discrete_sequence=px.colors.qualitative.Bold)
        fig3.update_traces(textposition="inside", textinfo="percent+label")
        fig3.update_layout(height=380, showlegend=False)
        st.plotly_chart(fig3, use_container_width=True)

    with col4:
        role_pkg = df.groupby("Role")["Package_LPA"].mean().reset_index().sort_values("Package_LPA", ascending=True)
        role_pkg["Package_LPA"] = role_pkg["Package_LPA"].round(2)
        fig4 = px.bar(role_pkg, x="Package_LPA", y="Role", orientation="h",
                      title="Avg Package by Role",
                      color="Package_LPA", color_continuous_scale="Blues", text="Package_LPA")
        fig4.update_traces(texttemplate="₹%{text}", textposition="outside")
        fig4.update_layout(plot_bgcolor="white", height=380, coloraxis_showscale=False,
                           yaxis_title="", xaxis_title="Avg Package (LPA)")
        st.plotly_chart(fig4, use_container_width=True)

# ── Tab 3: Student Insights ────────────────────────────────────────────────────
with tab3:
    st.markdown('<div class="section-title">Student-Level Insights</div>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)

    with col1:
        fig = px.scatter(
            df, x="CGPA", y="Package_LPA", color="Branch",
            size="Package_LPA", hover_data=["Student_Name","Company","Role","Year"],
            title="CGPA vs Package — All Students",
            color_discrete_sequence=px.colors.qualitative.Bold, size_max=18, opacity=0.75
        )
        fig.update_layout(plot_bgcolor="white", height=420)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        cgpa_bins = pd.cut(df["CGPA"], bins=[6,7,7.5,8,8.5,9,10],
                           labels=["6-7","7-7.5","7.5-8","8-8.5","8.5-9","9-10"])
        df2 = df.copy()
        df2["CGPA_Band"] = cgpa_bins
        band_pkg = df2.groupby("CGPA_Band", observed=True)["Package_LPA"].mean().reset_index()
        band_pkg["Package_LPA"] = band_pkg["Package_LPA"].round(2)
        fig2 = px.bar(band_pkg, x="CGPA_Band", y="Package_LPA",
                      title="Avg Package by CGPA Band",
                      color="Package_LPA", color_continuous_scale="Blues", text="Package_LPA")
        fig2.update_traces(texttemplate="₹%{text}", textposition="outside")
        fig2.update_layout(plot_bgcolor="white", height=420, coloraxis_showscale=False,
                           xaxis_title="CGPA Band", yaxis_title="Avg Package (LPA)")
        st.plotly_chart(fig2, use_container_width=True)

    st.markdown('<div class="section-title">Top Performers</div>', unsafe_allow_html=True)
    top_students = df.nlargest(15, "Package_LPA")[
        ["Student_Name","Branch","Company","Role","Package_LPA","CGPA","Year","Placement_Type"]
    ].reset_index(drop=True)
    top_students.index += 1
    top_students["Package_LPA"] = top_students["Package_LPA"].apply(lambda x: f"₹{x} LPA")
    st.dataframe(top_students, use_container_width=True)

# ── Tab 4: Map ────────────────────────────────────────────────────────────────
with tab4:
    st.markdown('<div class="section-title">🗺️ Recruiting Company Locations</div>', unsafe_allow_html=True)
    st.caption("Marker size reflects number of offers. Click markers for details.")

    show_heatmap = st.toggle("🌡️ Show Heatmap Layer", value=False)

    col_map, col_stats = st.columns([3, 1])

    with col_map:
        with st.spinner("Building map..."):
            m = build_placement_map(df, show_heatmap=show_heatmap)
            st_folium(m, width=750, height=500, returned_objects=[])

    with col_stats:
        st.markdown("**Offers by City**")
        city_count = df.groupby("City").agg(
            Offers=("Company","count"),
            Avg_Pkg=("Package_LPA","mean")
        ).reset_index().sort_values("Offers", ascending=False)
        city_count["Avg_Pkg"] = city_count["Avg_Pkg"].round(2)
        city_count.columns = ["City","Offers","Avg LPA"]
        st.dataframe(city_count, use_container_width=True, height=440)
