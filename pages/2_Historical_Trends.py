"""
pages/2_Historical_Trends.py — Time-series, heatmap, distribution
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
    get_station_list, get_history_multi_station,
    get_history, get_hourly_city_avg
)

st.set_page_config(page_title="Historical Trends", page_icon="📈", layout="wide")

st.title("📈 Historical Trends")
st.caption("Explore PM2.5 AQI patterns over time · All values on US EPA scale")

# ── Filters ───────────────────────────────────────────────────
col1, col2, col3, col4 = st.columns([1, 2, 2, 1])

SOURCE_MAP = {
    "IQAir":         "iqair_readings",
    "AQICN":         "aqicn_readings",
    "Udara Jakarta": "udara_readings",
}

with col1:
    source_label = st.selectbox("Source", list(SOURCE_MAP.keys()))
    source       = SOURCE_MAP[source_label]

with col2:
    all_stations = get_station_list(source)
    stations_sel = st.multiselect(
        "Stations (max 5)",
        all_stations,
        default=all_stations[:3] if len(all_stations) >= 3 else all_stations,
        max_selections=5,
    )

with col3:
    hours_sel = st.selectbox(
        "Time Range",
        [24, 48, 72, 168],
        index=1,
        format_func=lambda x: f"Last {x}h ({'1 day' if x==24 else '2 days' if x==48 else '3 days' if x==72 else '7 days'})",
    )

with col4:
    show_pm25 = st.checkbox("Show PM2.5 µg/m³", value=False)

st.divider()

# ── Multi-station Line Chart ───────────────────────────────────
st.subheader("📉 AQI Over Time")

if stations_sel:
    hist_df = get_history_multi_station(stations_sel, source, hours_sel)

    if not hist_df.empty:
        y_col = "density_ugm3" if show_pm25 else "aqi_pm25_us_epa"
        y_label = "PM2.5 µg/m³" if show_pm25 else "AQI (US EPA)"
        
        # Ensure missing values are NaN
        hist_df[y_col] = pd.to_numeric(hist_df[y_col], errors="coerce")
        
        # --- create the short-name c
        hist_df["station_short"] = hist_df["station"].str.split(" - ").str[0]

        # --- let the user pick which labels to use ---
        compact_legend = st.checkbox("Compact legend (for mobile)", value=False)
        label_col = "station_short" if compact_legend else "station"

        fig_line = px.line(
            hist_df, 
            x="measurement_time_ts", y=y_col,
            color="station",
            labels={y_col: y_label, "measurement_time_ts": "Time (WIB)", "station": "Station"},
            height=420,
        )
        
        # Break lines at missing values
        fig_line.update_traces(connectgaps=False, mode="lines+markers")
        
        # AQI threshold lines (only when showing AQI)
        if not show_pm25:
            for level, color, label in [
                (50,  "#00e400", "Good"),
                (100, "#ffff00", "Moderate"),
                (150, "#ff7e00", "Sensitive"),
                (200, "#ff0000", "Unhealthy"),
            ]:
                fig_line.add_hline(
                    y=level, line_dash="dot",
                    line_color=color, opacity=0.4,
                    annotation_text=label,
                    annotation_position="right",
                )
        fig_line.update_layout(
            hovermode="x unified",
            plot_bgcolor="#0e1117",
            paper_bgcolor="#0e1117",
            font_color="#f0f0f0",
            xaxis=dict(gridcolor="#2a2a2a"),
            yaxis=dict(gridcolor="#2a2a2a"),
            legend=dict(
                orientation="h",       # horizontal layout, wraps as needed
                yanchor="top",
                y=-0.25,                # push below the x-axis labels
                xanchor="center",
                x=0.5,
                bgcolor="#1a1a2e",
                font=dict(size=10),
            ),
            margin=dict(t=40, b=80, l=40, r=20),  # give the bottom legend room, reclaim right side
        )
        st.plotly_chart(fig_line, use_container_width=True)
    else:
        st.info("No data found for selected stations and time range.")
else:
    st.info("Please select at least one station.")

st.divider()

# ── City Average (IQAir) ──────────────────────────────────────
st.subheader("🏙️ Jakarta Hourly Average AQI — IQAir Network")
avg_df = get_hourly_city_avg(hours_sel)

if not avg_df.empty:
    fig_avg = go.Figure()
    fig_avg.add_trace(go.Scatter(
        x=avg_df["hour"], y=avg_df["max_aqi"],
        fill=None, mode="lines",
        line_color="rgba(255,100,100,0.3)",
        name="Max AQI",
    ))
    fig_avg.add_trace(go.Scatter(
        x=avg_df["hour"], y=avg_df["min_aqi"],
        fill="tonexty", mode="lines",
        line_color="rgba(100,200,100,0.3)",
        fillcolor="rgba(150,150,255,0.08)",
        name="Min AQI",
    ))
    fig_avg.add_trace(go.Scatter(
        x=avg_df["hour"], y=avg_df["avg_aqi"],
        mode="lines+markers",
        line=dict(color="#4fc3f7", width=2),
        marker=dict(size=4),
        name="Avg AQI",
        customdata=avg_df["station_count"],
        hovertemplate="<b>Avg AQI: %{y}</b><br>Stations: %{customdata}<extra></extra>",
    ))
    fig_avg.update_layout(
        height=350,
        plot_bgcolor="#0e1117",
        paper_bgcolor="#0e1117",
        font_color="#f0f0f0",
        xaxis=dict(gridcolor="#2a2a2a", title="Time (WIB)"),
        yaxis=dict(gridcolor="#2a2a2a", title="AQI"),
        legend=dict(bgcolor="#1a1a2e"),
        hovermode="x unified",
    )
    st.plotly_chart(fig_avg, use_container_width=True)

st.divider()

# ── Heatmap ───────────────────────────────────────────────────
st.subheader("🌡️ Hour-of-Day Heatmap")

if stations_sel:
    heatmap_station = st.selectbox("Select station for heatmap", stations_sel)
    hm_df = get_history(heatmap_station, source, hours=168)

    if not hm_df.empty:
        hm_df["hour"] = pd.to_datetime(hm_df["timestamp_wib"]).dt.hour
        hm_df["date"] = pd.to_datetime(hm_df["timestamp_wib"]).dt.date
        pivot = hm_df.pivot_table(
            index="hour", columns="date",
            values="aqi_pm25_us_epa", aggfunc="mean"
        )
        fig_hm = px.imshow(
            pivot,
            color_continuous_scale=[
                [0,    "#00e400"],
                [0.17, "#ffff00"],
                [0.33, "#ff7e00"],
                [0.5,  "#ff0000"],
                [0.67, "#8f3f97"],
                [1.0,  "#7e0023"],
            ],
            range_color=[0, 200],
            labels=dict(x="Date", y="Hour of Day (WIB)", color="AQI"),
            height=420,
        )
        fig_hm.update_layout(
            plot_bgcolor="#0e1117",
            paper_bgcolor="#0e1117",
            font_color="#f0f0f0",
        )
        st.plotly_chart(fig_hm, use_container_width=True)
        st.caption("Rows = hour of day 0–23 WIB · Columns = date · Color = average AQI")

st.divider()

# ── Box Plot ──────────────────────────────────────────────────
st.subheader("📦 AQI Distribution by Station")

if stations_sel:
    box_df = get_history_multi_station(stations_sel, source, hours_sel)
    if not box_df.empty:
        fig_box = px.box(
            box_df, x="station", y="aqi_pm25_us_epa",
            color="station",
            labels={"aqi_pm25_us_epa": "AQI (US EPA)", "station": "Station"},
            height=380,
        )
        fig_box.update_layout(
            plot_bgcolor="#0e1117",
            paper_bgcolor="#0e1117",
            font_color="#f0f0f0",
            xaxis=dict(gridcolor="#2a2a2a"),
            yaxis=dict(gridcolor="#2a2a2a"),
            showlegend=False,
        )
        st.plotly_chart(fig_box, use_container_width=True)
