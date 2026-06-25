"""
pages/1_Live_Overview.py — Real-time AQI map and rankings
Features:
  - Circle size slider
  - Freshness filter (only show stations updated within N hours)
  - Station filter
  - KPIs calculated from fresh data only
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
import sys
from datetime import datetime, timedelta
import requests

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.db import (
    get_latest_all_sources, get_city_kpis,
    get_latest_by_source, aqi_color, aqi_category
)

st.set_page_config(page_title="Live Overview", page_icon="🗺️", layout="wide")

# Automated Auto-Refresh Check (Every 15 minutes / 900 seconds)
# This snippet uses an HTML meta-refresh injection to gently force a rerun every 15 mins
# even if nobody is clicking anything.
REFRESH_INTERVAL = 900 
st.components.v1.html(
    f"""
    <script>
        setTimeout(function(){{
            window.parent.location.reload();
        }}, {REFRESH_INTERVAL * 1000});
    </script>
    """,
    height=0,
)

# ── Load Data ─────────────────────────────────────────────────
@st.cache_data(ttl=900)
def load_stations():
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    #return pd.read_csv(os.path.join(base, "data", "stations.csv"))
    path = os.path.join(base, "data", "stations.csv")

    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            # unify delimiters
            parts = line.replace(";", ",").split(",")

            # last 4 fields are lat, lon, province, source
            if len(parts) >= 5:
                station = ",".join(parts[:-4]).strip()
                lat, lon, province, source = parts[-4:]
                rows.append([station, lat, lon, province, source])

    return pd.DataFrame(rows, columns=["station_name", "lat", "lon", "province", "source"])
    
@st.cache_data(ttl=900)
def fetch_live_data():
    data = get_latest_all_sources()
    fetched_at = pd.Timestamp.now(tz="Asia/Jakarta").strftime("%H:%M:%S")
    return data, fetched_at

@st.cache_data(ttl=900)
def fetch_source_ranking(source_key):
    return get_latest_by_source(source_key)

# 4. FETCH THE DATA HERE (Crucial step: defines the variables)
stations_geo = load_stations()
latest_all, last_refresh_time = fetch_live_data()

st.write(f"Cache check: {pd.Timestamp.now(tz='Asia/Jakarta').strftime('%Y-%m-%d %H:%M:%S')}")
st.title("🗺️ Live Overview")
st.caption("Latest PM2.5 AQI readings from all active stations · Auto-refreshes every 15 minutes")

# This will now stay static when users interact with map filters/sliders!
st.markdown(f"⏱️ **Last automatic refresh:** `{last_refresh_time}`")

# ── Add refresh button here ─────────────────────────────────── deactivate afraid of spam call request
# col_title, col_refresh = st.columns([6, 1])
# with col_refresh:
    # if st.button("🔄 Refresh data"):
        # st.cache_data.clear()
        # st.rerun()


# ── Map Controls ──────────────────────────────────────────────
st.subheader("🗺️ Station Map")

with st.expander("⚙️ Map Filters & Settings", expanded=True):
    ctrl1, ctrl2, ctrl3 = st.columns([1, 1, 1])

    with ctrl1:
        source_options = {
            "IQAir":         "iqair_readings",
            "AQICN":         "aqicn_readings",
            "Udara Jakarta": "udara_readings",
        }
        sources_sel = st.multiselect(
            "Sources",
            list(source_options.keys()),
            default=list(source_options.keys()),
        )
        
        map_style = st.selectbox(
        "Map style",
        options=[
            "carto-darkmatter",
            "carto-positron",
            "open-street-map",
            "esri-satellite",
            "esri-street",
            "topo",
        ],
        format_func=lambda x: {
            "carto-darkmatter":  "🌑 Dark (default)",
            "carto-positron":    "⬜ Light",
            "open-street-map":   "🗺️ Street View",
            "esri-satellite":   "🛰️ Satellite (ESRI)",
            "esri-street":      "🛣️ Street Detail (ESRI)",
            "topo":             "🏙️ Topographic",
        }[x],index=0,
        )

    with ctrl2:
        freshness_hours = st.selectbox(
            "Show only stations updated within",
            [1, 2, 3, 6, 12, 24],
            index=1,
            format_func=lambda x: f"Last {x} hour{'s' if x > 1 else ''}",

        )
        show_all_stations = st.checkbox("Show all stations (grey = stale)", value=False)

    with ctrl3:
        map_type = st.radio(
            "Map type",
            ["Scatter", "Heatmap"],
            horizontal=True,
        )
        if map_type == "Scatter":
            circle_size = st.slider(
                "Circle size",
                min_value=5,
                max_value=30,
                value=12,
                step=1,
            )
            radius = 30  # default, not used in scatter
        else:  # Heatmap
            radius = st.slider(
                "Heatmap radius",
                min_value=10,
                max_value=50,
                value=30,
                step=5,
            )
            circle_size = 12  # default, not used in heatmap
        
        # ── New row ──────────────────────────────
        #st.divider()
        # map_type = st.radio(
            # "Map type",
            # ["Scatter", "Heatmap"],
            # horizontal=True,
        # )
        
        # map_style = st.selectbox(
        # "Map style",
        # options=[
            # "carto-darkmatter",
            # "carto-positron",
            # "open-street-map",
            # "esri-satellite",
            # "esri-street",
            # "topo",
        # ],
        # format_func=lambda x: {
            # "carto-darkmatter":  "🌑 Dark (default)",
            # "carto-positron":    "⬜ Light",
            # "open-street-map":   "🗺️ Street View",
            # "esri-satellite":   "🛰️ Satellite (ESRI)",
            # "esri-street":      "🛣️ Street Detail (ESRI)",
            # "topo":             "🏙️ Topographic",
        # }
        # [x],index=0,
    


# ── Apply Source Filter ───────────────────────────────────────
selected_sources = [source_options[s] for s in sources_sel]
map_data = latest_all[latest_all["source"].isin(selected_sources)].copy()

# ── Apply Freshness Filter ────────────────────────────────────
if not map_data.empty:     
    now = datetime.utcnow()
    cutoff = now - timedelta(hours=freshness_hours)
    map_data["meas_time_dt"] = pd.to_datetime(map_data["measurement_time_ts"], utc=True).dt.tz_localize(None)
    map_data["is_fresh"] = map_data["meas_time_dt"] >= cutoff
    stale_count = (~map_data["is_fresh"]).sum()

    if not show_all_stations:
        map_data = map_data[map_data["is_fresh"]]
        if stale_count > 0:
            st.caption(f"ℹ️ {stale_count} stations hidden — not updated in the last {freshness_hours} hour(s)")
    else:
        st.caption(f"ℹ️ Showing all stations · {stale_count} stale stations shown in grey · {len(map_data) - stale_count} fresh stations")

# ── Station Filter ────────────────────────────────────────────
if not map_data.empty:
    all_stations = sorted(map_data["station"].unique().tolist())
    station_filter = st.multiselect(
        "Filter specific stations (leave empty to show all)",
        all_stations,
        default=[],
        placeholder="Search station name...",
    )
    if station_filter:
        map_data = map_data[map_data["station"].isin(station_filter)]

# ── KPIs from fresh data only ─────────────────────────────────
# ── KPIs ──────────────────────────────────────────────────────
left, k2, k3, k4 = st.columns([2, 1.5, 1.5, 1.5])

with left:
    st.subheader("📊 Current Summary")
    st.caption(f"Based on stations updated within the last {freshness_hours} hour(s)")

if not map_data.empty:
    fresh_df = map_data.dropna(subset=["aqi_pm25_us_epa"])
    fresh_df = fresh_df[fresh_df["aqi_pm25_us_epa"] > 0]
    avg_aqi  = fresh_df["aqi_pm25_us_epa"].mean()
    worst    = fresh_df.loc[fresh_df["aqi_pm25_us_epa"].idxmax()]
    best     = fresh_df.loc[fresh_df["aqi_pm25_us_epa"].idxmin()]

    with left:
        st.metric("🏙️ Avg AQI Jakarta",
                  f"{avg_aqi:.0f}",
                  delta=f"· {len(fresh_df)} stations averaged",
                  delta_color="off")
    with k2:
        st.metric("😷 Worst Station",
                  f"AQI {int(worst['aqi_pm25_us_epa'])}",
                  delta=f"{worst['station']} · {worst['source_label']}",
                  delta_color="inverse")
    with k3:
        st.metric("✅ Best Station",
                  f"AQI {int(best['aqi_pm25_us_epa'])}",
                  delta=f"{best['station']} · {best['source_label']}",
                  delta_color="normal")
    with k4:
        st.metric("📡 Fresh Stations",
                  len(fresh_df),
                  delta=f"From {fresh_df['source'].nunique()} sources")
else:
    with k2:
        st.metric("😷 Worst Station", "N/A")
    with k3:
        st.metric("✅ Best Station", "N/A")
    with k4:
        st.metric("📡 Fresh Stations", 0)

st.divider()

# ── Map ───────────────────────────────────────────────────────
if not map_data.empty:
    # Merge with coordinates
    map_data["station_key"] = map_data["station"].str.strip().str.lower()
    stations_geo["station_key"] = stations_geo["station_name"].str.strip().str.lower()
    
    # Map DB source to CSV source
    source_map = {
        "iqair_readings":  "iqair",
        "aqicn_readings":  "aqicn",
        "udara_readings":  "udara jkt",
    }
    map_data["source_key"]    = map_data["source"].map(source_map)
    stations_geo["source_key"] = stations_geo["source"].str.strip().str.lower()
    
    map_data = map_data.merge(
        stations_geo[["station_key", "source_key", "lat", "lon"]],
        on=["station_key", "source_key"], 
        how="left"
    ).dropna(subset=["lat", "lon", "aqi_pm25_us_epa"])
    map_data = map_data[map_data["aqi_pm25_us_epa"] > 0]

    if not map_data.empty:
        map_data["color"] = map_data.apply(
                                            lambda r: aqi_color(r["aqi_pm25_us_epa"]) if r["is_fresh"] else "#555555",axis=1
                                            )
        map_data["category"] = map_data["aqi_pm25_us_epa"].apply(aqi_category)
        map_data["size"]     = 1  # ← user controlled size
        
        # Custom tile override for non-native styles
        CUSTOM_TILES = {
            "esri-satellite": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
            "esri-street":    "https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}",
            "topo":           "https://tile.opentopomap.org/{z}/{x}/{y}.png",
        }
        
        if map_type == "Scatter":
            fig_map = px.scatter_mapbox(
                map_data,
                lat="lat", lon="lon",
                #color="aqi_pm25_us_epa",
                color="color",                # use your hex column
                color_discrete_map="identity", # respect hex codes
                size="size",
                size_max=circle_size,  # ← this controls actual pixel size
                hover_name="station",
                hover_data={
                    "aqi_pm25_us_epa":    True,
                    "category":           True,
                    "source_label":       True,
                    "density_ugm3":       True,
                    #"timestamp_wib":      True,
                    "measurement_time_ts": True,
                    "is_fresh":           True,
                    "size":               False,
                    "station_key":        False,
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
                mapbox_style=map_style,
                zoom=10,
                center={"lat": -6.21, "lon": 106.82},
                height=540,
                labels={
                    "aqi_pm25_us_epa":    "AQI",
                    "source_label":       "Source",
                    "density_ugm3":       "PM2.5 µg/m³",
                    #"timestamp_wib":      "Scraped at (WIB)",
                    "measurement_time_ts": "Measured at",
                    "is_fresh": "Fresh data",
                }
            )
            
        else:  # Heatmap
            fig_map = px.density_mapbox(
                map_data,
                lat="lat", lon="lon",
                z="aqi_pm25_us_epa",
                radius=radius,
                center={"lat": -6.21, "lon": 106.82},
                zoom=10,
                mapbox_style=map_style if map_style not in CUSTOM_TILES else "white-bg",
                color_continuous_scale=[
                    [0,    "#00e400"],
                    [0.17, "#ffff00"],
                    [0.33, "#ff7e00"],
                    [0.50, "#ff0000"],
                    [0.67, "#8f3f97"],
                    [1.0,  "#7e0023"],
                ],
                range_color=[0, 300],
                height=540,
                labels={"aqi_pm25_us_epa": "AQI (PM2.5)"},
                title="",
            )
            
        fig_map.update_layout(
            margin={"r": 0, "t": 0, "l": 0, "b": 0},
            coloraxis_colorbar=dict(title="AQI (PM2.5)"),
        )
        # Custom tile override for non-native styles
        # CUSTOM_TILES = {
            # "esri-satellite": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
            # "esri-street":    "https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}",
            # "topo":           "https://tile.opentopomap.org/{z}/{x}/{y}.png",
        # }

        if map_style in CUSTOM_TILES:
            fig_map.update_layout(
                mapbox=dict(
                    style="white-bg",
                    zoom=10,
                    center={"lat": -6.21, "lon": 106.82},
                    layers=[{
                        "below": "traces",
                        "sourcetype": "raster",
                        "source": [CUSTOM_TILES[map_style]]
                    }]
                )
            )
           
        fig_map.update_layout(
            margin={"r": 0, "t": 0, "l": 0, "b": 0},
            coloraxis_colorbar=dict(title="AQI (PM2.5)"),
        )
        # ── Jakarta boundary overlay ──────────────────────────────────
        show_boundaries = st.toggle("Show Jakarta city boundaries", value=True)

        if show_boundaries:
            # City colors for each region
            city_colors = {
                "Jakarta Pusat":  "#ffffff",
                "Jakarta Selatan": "#aaffaa",
                "Jakarta Utara":  "#aaaaff",
                "Jakarta Timur":  "#ffaaaa",
                "Jakarta Barat":  "#ffddaa",
            }

            # Use a simpler approach with predefined GeoJSON from GitHub
            geojson_url = "https://raw.githubusercontent.com/dmxsan/indonesia-admin-boundaries/refs/heads/main/processed-data/02-provinces/with-districts/DKI_Jakarta.geojson"
            
            try:
                resp = requests.get(geojson_url, timeout=10)
                if resp.status_code == 200:
                    jakarta_geojson = resp.json()
                    
                    fig_map.update_layout(
                        mapbox={
                            "layers": [{
                                "source": jakarta_geojson,
                                "type": "line",
                                "color": "orange",
                                "line": {"width": 1},
                                "opacity": 0.4,
                            }]
                        }
                    )
            except Exception:
                pass  # silently skip if boundary fetch fails
        st.plotly_chart(fig_map, use_container_width=True)
    else:
        st.info("No stations with coordinates found for selected filters.")
else:
    st.warning(f"No stations updated within the last {freshness_hours} hour(s). Try increasing the freshness window.")

st.divider()

# ── Rankings per source ───────────────────────────────────────
st.subheader("📊 Current AQI Rankings")
tab1, tab2, tab3 = st.tabs(["🔵 IQAir", "🟢 AQICN", "🟠 Udara Jakarta"])

def render_ranking(source_key: str):
    df = get_latest_by_source(source_key)
    if df.empty:
        st.info("No data available.")
        return

    # Apply freshness filter to rankings too
    now    = datetime.utcnow()
    cutoff = now - timedelta(hours=freshness_hours)
    
    df["meas_dt"] = pd.to_datetime(df["measurement_time_ts"])
    df = df[df["meas_dt"] >= pd.Timestamp(cutoff)]

    if df.empty:
        st.info(f"No stations updated within last {freshness_hours}h.")
        return

    df = df[df["aqi_pm25_us_epa"] > 0]  # filter out AQI=0
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
    st.caption(f"Showing {len(df)} stations updated within last {freshness_hours}h")

with tab1:
    render_ranking("iqair_readings")
with tab2:
    render_ranking("aqicn_readings")
with tab3:
    render_ranking("udara_readings")

# ── Legend ────────────────────────────────────────────────────
st.divider()
st.caption("**AQI Scale (US EPA PM2.5):** 🟢 0-50 Good · 🟡 51-100 Moderate · 🟠 101-150 Unhealthy for Sensitive · 🔴 151-200 Unhealthy · 🟣 201-300 Very Unhealthy · ⚫ 300+ Hazardous")
st.caption("All values normalized to US EPA PM2.5 AQI scale · Freshness filter removes stale stations from all calculations")
