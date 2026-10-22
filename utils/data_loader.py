import io
import json
import os
import re

import numpy as np
import pandas as pd
import requests
import streamlit as st

API_URL = os.environ.get(
    "STUDENT_DATA_API_URL",
    "https://gist.githubusercontent.com/Maulik7278/577f73f18ea8f3dd584e0e8210ac9bcb/raw/gistfile1.txt",
)

REQUIRED_COLUMNS = ["Year", "Branch", "Student_Name", "CGPA", "Company", "Role",
                    "Package_LPA", "Placement_Type", "City"]

# Alternative header names the API might use -> our canonical column names
_COLUMN_ALIASES = {
    "year": "Year", "batch": "Year", "passing_year": "Year", "placement_year": "Year",
    "branch": "Branch", "department": "Branch", "dept": "Branch", "stream": "Branch",
    "student_name": "Student_Name", "studentname": "Student_Name", "name": "Student_Name", "student": "Student_Name",
    "cgpa": "CGPA", "gpa": "CGPA",
    "company": "Company", "company_name": "Company", "recruiter": "Company",
    "role": "Role", "job_role": "Role", "designation": "Role", "position": "Role",
    "package_lpa": "Package_LPA", "package": "Package_LPA", "lpa": "Package_LPA", "ctc": "Package_LPA",
    "placement_type": "Placement_Type", "type": "Placement_Type", "placementtype": "Placement_Type",
    "city": "City", "location": "City",
}


class DataLoadError(Exception):
    """Raised when student data cannot be fetched or parsed from the API."""


def _to_dataframe(resp):
    """Turn an HTTP response into a DataFrame. Supports JSON (list or wrapped list) and CSV text."""
    text = resp.text.strip()
    if not text:
        raise DataLoadError("The API returned an empty response.")

    # 1) JSON
    try:
        payload = json.loads(text.lstrip("\ufeff"))
    except ValueError:
        payload = None

    if payload is not None:
        if isinstance(payload, dict):
            # {"data": [...]} / {"students": [...]} / etc. -> first list value
            lists = [v for v in payload.values() if isinstance(v, list)]
            if lists:
                payload = lists[0]
            else:
                payload = [payload]
        if not isinstance(payload, list) or not payload:
            raise DataLoadError("The API returned JSON, but it contains no student records.")
        return pd.json_normalize(payload)

    # 2) CSV text
    try:
        return pd.read_csv(io.StringIO(text.lstrip("\ufeff")), sep=None, engine="python")
    except Exception as e:
        raise DataLoadError(f"Could not parse the API response as JSON or CSV: {e}")


def _normalize(df):
    """Rename columns to canonical names, validate, and fix dtypes."""
    renamed = {}
    for col in df.columns:
        key = re.sub(r"[\s\-]+", "_", str(col).strip().lower())
        renamed[col] = _COLUMN_ALIASES.get(key, str(col).strip())
    df = df.rename(columns=renamed)

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise DataLoadError(
            f"API data is missing columns: {', '.join(missing)}. "
            f"Found: {', '.join(map(str, df.columns))}"
        )

    df = df[REQUIRED_COLUMNS].copy()
    for c in ["Year", "Package_LPA", "CGPA"]:
        df[c] = pd.to_numeric(
            df[c].astype(str).str.replace(r"[^0-9.\-]", "", regex=True), errors="coerce"
        )
    df = df.dropna(subset=["Year", "Package_LPA", "CGPA"])
    if df.empty:
        raise DataLoadError("No valid student records found after cleaning the API data.")
    df["Year"] = df["Year"].astype(int)
    for c in ["Branch", "Student_Name", "Company", "Role", "Placement_Type", "City"]:
        df[c] = df[c].astype(str).str.strip()
    return df.reset_index(drop=True)


@st.cache_data(ttl=600, show_spinner="Fetching student data from API...")
def fetch_student_data(url=API_URL):
    """Fetch student placement data from the API (cached for 10 minutes)."""
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as e:
        raise DataLoadError(f"Could not reach the student data API: {e}")
    return _normalize(_to_dataframe(resp))


def get_data():
    """Load student data from the API. Shows an error with a retry button and stops the page on failure."""
    try:
        return fetch_student_data()
    except DataLoadError as e:
        st.error(f"❌ Failed to load student data from the API.\n\n{e}")
        if st.button("🔄 Retry"):
            st.cache_data.clear()
            st.rerun()
        st.stop()

def range_slider(label, series, step):
    """Range slider that doesn't crash when min == max (e.g. tiny or uniform data)."""
    lo, hi = float(series.min()), float(series.max())
    if lo >= hi:
        st.caption(f"{label}: all values are {lo:g}")
        return (lo, hi)
    return st.slider(label, lo, hi, (lo, hi), step=step)


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
