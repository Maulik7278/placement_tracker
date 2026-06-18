import pandas as pd
import numpy as np
import streamlit as st
import os

SAMPLE_DATA_PATH = os.path.join(os.path.dirname(__file__), "../assets/sample_data.csv")

REQUIRED_COLUMNS = ["Year", "Branch", "Student_Name", "CGPA", "Company", "Role",
                    "Package_LPA", "Placement_Type", "City"]

@st.cache_data
def load_sample_data():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../assets/sample_data.csv")
    df = pd.read_csv(path)
    df["Year"] = df["Year"].astype(int)
    return df

def load_uploaded_data(uploaded_file):
    try:
        if uploaded_file.name.endswith(".csv"):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
        missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
        if missing:
            st.error(f"Missing columns: {', '.join(missing)}")
            return None
        df["Year"] = df["Year"].astype(int)
        df["Package_LPA"] = pd.to_numeric(df["Package_LPA"], errors="coerce")
        df["CGPA"] = pd.to_numeric(df["CGPA"], errors="coerce")
        df = df.dropna(subset=["Package_LPA", "CGPA"])
        st.success(f"✅ Loaded {len(df)} records successfully!")
        return df
    except Exception as e:
        st.error(f"Error reading file: {e}")
        return None

def get_data(uploaded_file=None):
    if uploaded_file is not None:
        df = load_uploaded_data(uploaded_file)
        if df is not None:
            return df
    return load_sample_data()

def apply_filters(df, years, branches, placement_types, pkg_range, cgpa_range):
    filtered = df.copy()
    if years:
        filtered = filtered[filtered["Year"].isin(years)]
    if branches:
        filtered = filtered[filtered["Branch"].isin(branches)]
    if placement_types:
        filtered = filtered[filtered["Placement_Type"].isin(placement_types)]
    filtered = filtered[
        (filtered["Package_LPA"] >= pkg_range[0]) &
        (filtered["Package_LPA"] <= pkg_range[1])
    ]
    filtered = filtered[
        (filtered["CGPA"] >= cgpa_range[0]) &
        (filtered["CGPA"] <= cgpa_range[1])
    ]
    return filtered

def compute_kpis(df, df_prev=None):
    total_placed = len(df)
    avg_pkg = round(df["Package_LPA"].mean(), 2) if total_placed > 0 else 0
    max_pkg = round(df["Package_LPA"].max(), 2) if total_placed > 0 else 0
    unique_companies = df["Company"].nunique() if total_placed > 0 else 0

    total_students_estimate = total_placed / 0.80
    placement_pct = round((total_placed / total_students_estimate) * 100, 1) if total_students_estimate > 0 else 0

    deltas = {"total": None, "avg_pkg": None, "max_pkg": None, "pct": None, "companies": None}
    if df_prev is not None and len(df_prev) > 0:
        prev_placed = len(df_prev)
        prev_avg = round(df_prev["Package_LPA"].mean(), 2)
        prev_max = round(df_prev["Package_LPA"].max(), 2)
        prev_companies = df_prev["Company"].nunique()
        prev_pct = round((prev_placed / (prev_placed / 0.80)) * 100, 1)
        deltas = {
            "total": total_placed - prev_placed,
            "avg_pkg": round(avg_pkg - prev_avg, 2),
            "max_pkg": round(max_pkg - prev_max, 2),
            "pct": round(placement_pct - prev_pct, 1),
            "companies": unique_companies - prev_companies
        }
    return {
        "total_placed": total_placed,
        "avg_pkg": avg_pkg,
        "max_pkg": max_pkg,
        "placement_pct": placement_pct,
        "unique_companies": unique_companies,
        "deltas": deltas
    }
