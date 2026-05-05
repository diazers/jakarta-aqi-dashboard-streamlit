"""
pages/1_Live_Overview.py — Real-time AQI map and rankings
Uses air_quality_pm25_combined for all queries
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.db import (
    get_latest_all_sources, get_city_kpis,
    get_latest_by_source, aqi_color, aqi_category
)

st.set_page_config(page_title="Live Overview", page_icon="🗺️", layout="wide")

st.title("🗺️ Live Overview")
st.caption("Latest PM2.5 AQI readings from all active stations · Auto-refreshes every 10 minutes")

# ── Load Data ─────────────────────────────────────────────────
@st.cache_data(ttl=600)
def load_stations():
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return pd.read_csv(os.path.join(base, "data", "stations.csv"))

stations_geo = load_stations()
latest_all   = get_latest_all_sources()
kpis         = get_city_kpis()

# ── KPI Cards ─────────────────────────────────────────────────
st.subheader("📊 Current Summary")
k1, k2, k3, k4 = st.columns(4)

with k1:
    st.metric("🏙️ Avg AQI Jakarta",
              f"{kpis.get('avg_aqi', 'N/A')}",
              help="Average across all active stations from all sources")
with k2:
    st.metric("😷 Worst Station",
              f"AQI {kpis.get('worst_aqi', 'N/A')}",
              delta=f"{kpis.get('worst_station', '')} · {kpis.get('worst_source', '')}",
              delta_color="inverse")
with k3:
    st.metric("✅ Best Station",
              f"AQI {kpis.get('best_aqi', 'N/A')}",
              delta=f"{kpis.get('best_station', '')} · {kpis.get('best_source', '')}",
              delta_color="normal")
with k4:
    st.metric("📡 Active Stations",
              kpis.get("total_stations", 0),
              delta=f"From {kpis.get('total_sources', 0)} sources")

st.divider()

# ── Source Filter ─────────────────────────────────────────────
st.subheader("🗺️ Station Map")

source_options = {
    "IQAir":          "iqair_readings",
    "AQICN":          "aqicn_readings",
    "Udara Jakarta":  "udara_readings",
}
sources_sel = st.multiselect(
    "Show sources:",
    list(source_options.keys()),
    default=list(source_options.keys()),
)

selected_sources = [source_options[s] for s in sources_sel]
map_data = latest_all[latest_all["source"].isin(selected_sources)].copy()

# Merge with coordinates
map_data["station_key"] = map_data["station"].str.strip().str.lower()
stations_geo["station_key"] = stations_geo["station_name"].str.strip().str.lower()
map_data = map_data.merge(
    stations_geo[["station_key", "lat", "lon"]],
    on="station_key", how="left"
).dropna(subset=["lat", "lon", "aqi_pm25_us_epa"])

if not map_data.empty:
    map_data["color"]    = map_data["aqi_pm25_us_epa"].apply(aqi_color)
    map_data["category"] = map_data["aqi_pm25_us_epa"].apply(aqi_category)
    map_data["size"]     = 12

    fig_map = px.scatter_mapbox(
        map_data,
        lat="lat", lon="lon",
        color="aqi_pm25_us_epa",
        size="size",
        hover_name="station",
        hover_data={
            "aqi_pm25_us_epa": True,
            "category":        True,
            "source_label":    True,
            "density_ugm3":    True,
            "size":            False,
        },
        color_continuous_scale=[
            [0,    "#00e400"],
            [0.17, "#ffff00"],
            [0.33, "#ff7e00"],
            [0.50, "#ff0000"],
            [0.67, "#8f3f97"],
            [1.0,  "#7e0023"],
        ],
        range_color=[0, 300],
        mapbox_style="carto-darkmatter",
        zoom=10,
        center={"lat": -6.21, "lon": 106.82},
        height=520,
        labels={
            "aqi_pm25_us_epa": "AQI",
            "source_label":    "Source",
            "density_ugm3":    "PM2.5 µg/m³",
        }
    )
    fig_map.update_layout(
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
        coloraxis_colorbar=dict(title="AQI (PM2.5)"),
    )
    st.plotly_chart(fig_map, use_container_width=True)
else:
    st.info("No station coordinates matched. Check stations.csv.")

st.divider()

# ── Rankings per source ───────────────────────────────────────
st.subheader("📊 Current AQI Rankings")
tab1, tab2, tab3 = st.tabs(["🔵 IQAir", "🟢 AQICN", "🟠 Udara Jakarta"])

def render_ranking(source_key: str):
    df = get_latest_by_source(source_key)
    if df.empty:
        st.info("No data available.")
        return
    df = df.dropna(subset=["aqi_pm25_us_epa"]).sort_values("aqi_pm25_us_epa", ascending=True)
    df["color"] = df["aqi_pm25_us_epa"].apply(aqi_color)

    fig = go.Figure(go.Bar(
        x=df["aqi_pm25_us_epa"],
        y=df["station"],
        orientation="h",
        marker_color=df["color"],
        hovertemplate="<b>%{y}</b><br>AQI: %{x}<extra></extra>",
    ))
    fig.update_layout(
        height=max(350, len(df) * 22),
        xaxis_title="AQI (PM2.5 US EPA)",
        yaxis_title="",
        plot_bgcolor="#0e1117",
        paper_bgcolor="#0e1117",
        font_color="#f0f0f0",
        margin=dict(l=10, r=30, t=10, b=10),
        xaxis=dict(gridcolor="#2a2a2a"),
    )
    st.plotly_chart(fig, use_container_width=True)

with tab1:
    render_ranking("iqair_readings")
with tab2:
    render_ranking("aqicn_readings")
with tab3:
    render_ranking("udara_readings")

# ── Legend ────────────────────────────────────────────────────
st.divider()
st.caption("**AQI Scale (US EPA PM2.5):** 🟢 0-50 Good · 🟡 51-100 Moderate · 🟠 101-150 Unhealthy for Sensitive · 🔴 151-200 Unhealthy · 🟣 201-300 Very Unhealthy · ⚫ 300+ Hazardous")
st.caption("All values normalized to US EPA PM2.5 AQI scale using `pm25_to_us_epa_aqi()` and `ispu_to_epa()` conversion functions.")
