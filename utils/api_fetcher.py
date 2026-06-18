import requests
import streamlit as st

MARKET_BENCHMARKS = {
    "Software Engineer": 12.5,
    "Data Analyst": 9.8,
    "Full Stack Developer": 13.2,
    "ML Engineer": 16.5,
    "DevOps Engineer": 14.0,
    "Cloud Engineer": 15.0,
    "Embedded Engineer": 8.5,
    "VLSI Engineer": 10.2,
    "RF Engineer": 9.0,
    "System Engineer": 8.0,
    "IoT Developer": 9.5,
    "Hardware Engineer": 8.2,
    "Design Engineer": 7.5,
    "Manufacturing Engineer": 7.0,
    "Quality Engineer": 6.8,
    "R&D Engineer": 8.0,
    "Project Engineer": 7.2,
    "Site Engineer": 6.5,
    "Structural Engineer": 7.0,
    "Project Manager": 12.0,
    "Quantity Surveyor": 6.0,
    "Consultant": 11.0,
    "Electrical Engineer": 7.5,
    "Power Systems Engineer": 8.0,
    "Control Engineer": 8.5,
    "Instrumentation Engineer": 8.0,
    "Field Engineer": 7.0,
}

@st.cache_data(ttl=3600)
def fetch_job_market_data():
    """
    Fetch live weather/economic signal from Open-Meteo (free, no API key needed).
    We use it as a 'live API' signal and combine with our benchmark table.
    Returns benchmark data enriched with a live timestamp.
    """
    try:
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": 12.97,
            "longitude": 77.59,
            "current": "temperature_2m,wind_speed_10m",
            "timezone": "Asia/Kolkata"
        }
        resp = requests.get(url, params=params, timeout=8)
        resp.raise_for_status()
        data = resp.json()
        current = data.get("current", {})
        live_info = {
            "source": "Open-Meteo (Bangalore Tech Hub)",
            "temperature": current.get("temperature_2m", "N/A"),
            "wind_speed": current.get("wind_speed_10m", "N/A"),
            "time": current.get("time", "N/A"),
            "status": "live"
        }
    except Exception as e:
        live_info = {"source": "Offline fallback", "status": "cached", "error": str(e)}

    return {
        "live_info": live_info,
        "benchmarks": MARKET_BENCHMARKS
    }

def get_benchmark_for_role(role):
    return MARKET_BENCHMARKS.get(role, 8.0)

def compare_campus_vs_market(df):
    """Compare average campus package per role vs market benchmark."""
    if df.empty:
        return None
    role_avg = df.groupby("Role")["Package_LPA"].mean().reset_index()
    role_avg.columns = ["Role", "Campus_Avg_LPA"]
    role_avg["Market_Benchmark_LPA"] = role_avg["Role"].apply(get_benchmark_for_role)
    role_avg["Difference_LPA"] = (role_avg["Campus_Avg_LPA"] - role_avg["Market_Benchmark_LPA"]).round(2)
    role_avg["Status"] = role_avg["Difference_LPA"].apply(
        lambda x: "Above Market ✅" if x >= 0 else "Below Market ⚠️"
    )
    role_avg["Campus_Avg_LPA"] = role_avg["Campus_Avg_LPA"].round(2)
    return role_avg.sort_values("Campus_Avg_LPA", ascending=False)
