"""
pages/4_Station_Detail.py — Deep dive into a single station
Uses air_quality_pm25_combined for all queries
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.db import get_station_list, get_history, aqi_color, aqi_category

st.set_page_config(page_title="Station Detail", page_icon="📡", layout="wide")

st.title("📡 Station Detail")
st.caption("Deep dive into a single monitoring station")

SOURCE_MAP = {
    "IQAir":         "iqair_readings",
    "AQICN":         "aqicn_readings",
    "Udara Jakarta": "udara_readings",
}

# ── Filters ───────────────────────────────────────────────────
col1, col2, col3 = st.columns([1, 2, 1])

with col1:
    source_label = st.selectbox("Source", list(SOURCE_MAP.keys()))
    source       = SOURCE_MAP[source_label]

with col2:
    stations = get_station_list(source)
    station  = st.selectbox("Station", stations)

with col3:
    hours = st.selectbox(
        "Time Range",
        [24, 48, 72, 168],
        index=1,
        format_func=lambda x: f"Last {x}h",
    )

st.divider()

# ── Load Data ─────────────────────────────────────────────────
df = get_history(station, source, hours)

if df.empty:
    st.warning("No data found for this station in the selected time range.")
    st.stop()

latest = df.iloc[-1]

# ── Station Info Cards ────────────────────────────────────────
c1, c2, c3, c4, c5 = st.columns(5)

with c1:
    aqi_val = int(latest["aqi_pm25_us_epa"]) if pd.notna(latest["aqi_pm25_us_epa"]) else None
    st.metric("Latest AQI", aqi_val or "N/A",
              delta=aqi_category(aqi_val) if aqi_val else "",
              delta_color="off")
with c2:
    d = latest.get("density_ugm3")
    st.metric("PM2.5", f"{d:.1f} µg/m³" if pd.notna(d) else "N/A")
with c3:
    t = latest.get("temperature_c")
    st.metric("Temperature", f"{t:.0f}°C" if pd.notna(t) else "N/A")
with c4:
    h = latest.get("humidity_pct")
    st.metric("Humidity", f"{h:.0f}%" if pd.notna(h) else "N/A")
with c5:
    w = latest.get("wind_speed_kmh")
    st.metric("Wind", f"{w:.0f} km/h" if pd.notna(w) else "N/A")

st.caption(f"Last reading: {latest['timestamp_wib']} WIB · Source: {source_label}")

st.divider()

# ── AQI Time Series ───────────────────────────────────────────
st.subheader("📉 AQI Over Time")

# ── Chart Control ─────────────────────────────────────────────
chart_type = st.radio("Select Chart Type", ["Line Chart", "Histogram (Bar)"], horizontal=True)

fig_aqi = go.Figure()

if chart_type == "Line Chart":
    fig_aqi.add_trace(go.Scatter(
        x=df["timestamp_wib"], y=df["aqi_pm25_us_epa"],
        name="AQI (US EPA)",
        line=dict(color="#4fc3f7", width=2),
        fill="tozeroy", fillcolor="rgba(79,195,247,0.05)",
    ))
else:
    fig_aqi.add_trace(go.Bar(
        x=df["timestamp_wib"], y=df["aqi_pm25_us_epa"],
        name="AQI (US EPA)",
        marker_color=[aqi_color(v) if pd.notna(v) else "#888888" for v in df["aqi_pm25_us_epa"]],
    ))

# AQI threshold lines
for level, color, label in [
    (50,  "#00e400", "Good"),
    (100, "#ffff00", "Moderate"),
    (150, "#ff7e00", "Sensitive"),
    (200, "#ff0000", "Unhealthy"),
    (300, "#8e24aa", "Very Unhealthy"),
]:
    fig_aqi.add_hline(
        y=level,
        line_dash="dot",
        line_color=color,
        opacity=0.35,
        annotation_text=label,
        annotation_position="bottom left",
        annotation_font=dict(color=color, size=10)
    )

fig_aqi.update_yaxes(
    title_text="AQI (US EPA)",
    gridcolor="#2a2a2a",
    color="#f0f0f0",
    ticklabelposition="outside left"
)
        
fig_aqi.update_layout(
    height=350,
    plot_bgcolor="#0e1117", paper_bgcolor="#0e1117",
    font_color="#f0f0f0",
    xaxis=dict(gridcolor="#2a2a2a", title="Time (WIB)"),
    showlegend=False,
    hovermode="x unified",
)
st.plotly_chart(fig_aqi, use_container_width=True)


# ── PM2.5 Time Series ─────────────────────────────────────────
st.subheader("📉 PM2.5 Over Time")

fig_pm25 = go.Figure()

if chart_type == "Line Chart":
    fig_pm25.add_trace(go.Scatter(
        x=df["timestamp_wib"], y=df["density_ugm3"],
        name="PM2.5 µg/m³",
        line=dict(color="#ffa726", width=2, dash="dot"),
    ))
else:
    fig_pm25.add_trace(go.Bar(
        x=df["timestamp_wib"], y=df["density_ugm3"],
        name="PM2.5 µg/m³",
        # Color PM2.5 by its corresponding AQI tier color for visual consistency
        marker_color=[aqi_color(v) if pd.notna(v) else "#888888" for v in df["aqi_pm25_us_epa"]],
    ))

fig_pm25.update_yaxes(
    title_text="PM2.5 µg/m³",
    gridcolor="#2a2a2a",
    color="#f0f0f0",
    ticklabelposition="outside left",
    showline=True,
    linecolor="#f0f0f0"
)
        
fig_pm25.update_layout(
    height=350,
    plot_bgcolor="#0e1117", paper_bgcolor="#0e1117",
    font_color="#f0f0f0",
    xaxis=dict(gridcolor="#2a2a2a", title="Time (WIB)"),
    showlegend=False,
    hovermode="x unified",
)
st.plotly_chart(fig_pm25, use_container_width=True)

# ── Weather (IQAir only) ──────────────────────────────────────
has_weather = df["temperature_c"].notna().any()

if has_weather:
    st.subheader("🌡️ Weather Conditions")
    w1, w2 = st.columns(2)
    with w1:
        fig_t = px.line(df, x="timestamp_wib", y="temperature_c",
                        labels={"temperature_c": "°C", "timestamp_wib": "Time"},
                        height=250, color_discrete_sequence=["#ef5350"])
        fig_t.update_layout(plot_bgcolor="#0e1117", paper_bgcolor="#0e1117",
                            font_color="#f0f0f0", xaxis=dict(gridcolor="#2a2a2a"),
                            yaxis=dict(gridcolor="#2a2a2a"), title="Temperature (°C)")
        st.plotly_chart(fig_t, use_container_width=True)
    with w2:
        fig_h = px.line(df, x="timestamp_wib", y="humidity_pct",
                        labels={"humidity_pct": "%", "timestamp_wib": "Time"},
                        height=250, color_discrete_sequence=["#42a5f5"])
        fig_h.update_layout(plot_bgcolor="#0e1117", paper_bgcolor="#0e1117",
                            font_color="#f0f0f0", xaxis=dict(gridcolor="#2a2a2a"),
                            yaxis=dict(gridcolor="#2a2a2a"), title="Humidity (%)")
        st.plotly_chart(fig_h, use_container_width=True)

st.divider()

# ── Hour-of-Day Pattern ───────────────────────────────────────
st.subheader("⏰ Average AQI by Hour of Day")
st.caption("Identifies daily pollution cycles — rush hours, industrial patterns")

df["hour"] = pd.to_datetime(df["measurement_time_ts"]).dt.hour
hourly     = df.groupby("hour")["aqi_pm25_us_epa"].agg(["mean", "min", "max"]).reset_index()
hourly.columns = ["hour", "avg", "min", "max"]

fig_hr = go.Figure()
fig_hr.add_trace(go.Bar(
    x=hourly["hour"], y=hourly["avg"],
    marker_color=[aqi_color(v) for v in hourly["avg"]],
    name="Avg AQI",
    error_y=dict(
        type="data",
        symmetric=False,
        array=hourly["max"] - hourly["avg"],
        arrayminus=hourly["avg"] - hourly["min"],
        color="#888",
    ),
))
fig_hr.update_layout(
    height=320,
    plot_bgcolor="#0e1117", paper_bgcolor="#0e1117",
    font_color="#f0f0f0",
    xaxis=dict(gridcolor="#2a2a2a", title="Hour of Day (WIB)", tickmode="linear"),
    yaxis=dict(gridcolor="#2a2a2a", title="AQI"),
    showlegend=False,
)
st.plotly_chart(fig_hr, use_container_width=True)

st.divider()

# ── Raw Data Table ────────────────────────────────────────────
st.subheader("📋 Raw Data")

display_df = df.sort_values("timestamp_wib", ascending=False).copy()
display_df.columns = [c.replace("_", " ").title() for c in display_df.columns]

st.dataframe(display_df, hide_index=True, height=300)
st.download_button(
    "⬇️ Download CSV",
    df.to_csv(index=False),
    file_name=f"{station.replace(' ', '_')}_{source_label.lower().replace(' ', '_')}.csv",
    mime="text/csv",
)