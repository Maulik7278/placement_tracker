import folium
from folium.plugins import HeatMap
import pandas as pd

CITY_COORDS = {
    "Bangalore": (12.9716, 77.5946),
    "Mumbai": (19.0760, 72.8777),
    "Hyderabad": (17.3850, 78.4867),
    "Pune": (18.5204, 73.8567),
    "Chennai": (13.0827, 80.2707),
    "Delhi": (28.7041, 77.1025),
    "Noida": (28.5355, 77.3910),
    "Gurgaon": (28.4595, 77.0266),
    "Kolkata": (22.5726, 88.3639),
    "Ahmedabad": (23.0225, 72.5714),
    "Jaipur": (26.9124, 75.7873),
    "Kochi": (9.9312, 76.2673),
    "Coimbatore": (11.0168, 76.9558),
    "Chandigarh": (30.7333, 76.7794),
    "Indore": (22.7196, 75.8577),
    "Nagpur": (21.1458, 79.0882),
    "Lucknow": (26.8467, 80.9462),
    "Thiruvananthapuram": (8.5241, 76.9366),
    "Mysore": (12.2958, 76.6394),
    "Surat": (21.1702, 72.8311),
    "Vadodara": (22.3072, 73.1812),
    "Bhubaneswar": (20.2961, 85.8245),
    "Visakhapatnam": (17.6868, 83.2185),
}

_CITY_ALIASES = {
    "bengaluru": "Bangalore", "gurugram": "Gurgaon",
    "new delhi": "Delhi", "delhi ncr": "Delhi", "ncr": "Delhi",
    "bombay": "Mumbai", "navi mumbai": "Mumbai", "madras": "Chennai",
    "calcutta": "Kolkata", "mysuru": "Mysore", "trivandrum": "Thiruvananthapuram",
    "vizag": "Visakhapatnam", "cochin": "Kochi",
}


def get_coords(city):
    """Return (lat, lon) for a city name (case-insensitive, with common aliases), or None."""
    key = str(city).strip().lower()
    name = _CITY_ALIASES.get(key) or next((c for c in CITY_COORDS if c.lower() == key), None)
    return CITY_COORDS.get(name) if name else None


def build_placement_map(df, show_heatmap=False):
    """Build a Folium map with company HQ markers and optional heatmap."""
    m = folium.Map(
        location=[20.5937, 78.9629],
        zoom_start=5,
        tiles="OpenStreetMap"      # was "CartoDB positron"
    )

    if df.empty:
        return m

    city_stats = df.groupby("City").agg(
        offer_count=("Company", "count"),
        avg_package=("Package_LPA", "mean"),
        companies=("Company", lambda x: ", ".join(sorted(x.unique()[:5])))
    ).reset_index()

    max_offers = city_stats["offer_count"].max()

    for _, row in city_stats.iterrows():
        city = row["City"]
        coords = get_coords(city)
        if coords is None:
            continue
        lat, lon = coords
        offers = row["offer_count"]
        avg_pkg = round(row["avg_package"], 2)
        companies_str = row["companies"]

        radius = 8 + (offers / max_offers) * 22

        if avg_pkg >= 15:
            color = "#1a237e"
        elif avg_pkg >= 8:
            color = "#1B4F72"
        elif avg_pkg >= 5:
            color = "#2E86C1"
        else:
            color = "#85C1E9"

        popup_html = f"""
        <div style="font-family:Arial; min-width:180px;">
            <b style="color:#1B4F72;font-size:14px;">📍 {city}</b><br>
            <hr style="margin:4px 0;">
            <b>Total Offers:</b> {offers}<br>
            <b>Avg Package:</b> ₹{avg_pkg} LPA<br>
            <b>Companies:</b><br>
            <small>{companies_str}</small>
        </div>
        """
        folium.CircleMarker(
            location=[lat, lon],
            radius=radius,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.75,
            popup=folium.Popup(popup_html, max_width=220),
            tooltip=f"{city}: {offers} offers | Avg ₹{avg_pkg} LPA"
        ).add_to(m)

        folium.Marker(
            location=[lat, lon],
            icon=folium.DivIcon(
                html=f'<div style="font-size:10px;color:#fff;font-weight:bold;'
                     f'background:{color};padding:2px 5px;border-radius:3px;'
                     f'white-space:nowrap;">{city}</div>',
                icon_size=(80, 20),
                icon_anchor=(40, -5)
            )
        ).add_to(m)

    if show_heatmap:
        heat_data = []
        for _, row in city_stats.iterrows():
            city = row["City"]
            coords = get_coords(city)
            if coords is not None:
                lat, lon = coords
                heat_data.append([lat, lon, row["offer_count"]])
        if heat_data:
            HeatMap(heat_data, radius=40, blur=25, min_opacity=0.4).add_to(m)

    return m

def build_company_map(df):
    """Build a map showing top companies per city."""
    m = folium.Map(
        location=[20.5937, 78.9629],
        zoom_start=5,
        tiles="OpenStreetMap"      # was "CartoDB positron"
    )
    if df.empty:
        return m

    company_city = df.groupby(["Company", "City"]).agg(
        count=("Student_Name", "count"),
        avg_pkg=("Package_LPA", "mean")
    ).reset_index()

    top = company_city.sort_values("count", ascending=False).head(20)

    for _, row in top.iterrows():
        city = row["City"]
        coords = get_coords(city)
        if coords is None:
            continue
        lat, lon = coords
        lat += (hash(row["Company"]) % 10 - 5) * 0.05
        lon += (hash(row["Company"]) % 7 - 3) * 0.05

        folium.Marker(
            location=[lat, lon],
            popup=folium.Popup(
                f"<b>{row['Company']}</b><br>Offers: {row['count']}<br>Avg: ₹{round(row['avg_pkg'],2)} LPA",
                max_width=180
            ),
            tooltip=f"{row['Company']} ({row['count']} offers)",
            icon=folium.Icon(color="blue", icon="briefcase", prefix="fa")
        ).add_to(m)

    return m
