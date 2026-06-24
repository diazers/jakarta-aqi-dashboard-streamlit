"""
pages/3_Source_Comparison.py — IQAir vs AQICN vs Udara Jakarta
Uses air_quality_pm25_combined — all values on same US EPA scale
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import os
import sys
from datetime import datetime, timedelta

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.db import (
    get_latest_by_source, get_comparison_history,
    get_station_list, aqi_color
)

st.set_page_config(page_title="Source Comparison", page_icon="🔬", layout="wide")

st.title("🔬 Source Comparison")
st.caption("IQAir vs AQICN vs Udara Jakarta — all values converted to US EPA PM2.5 AQI scale")

st.info("""
**Why this matters:** Each source uses different sensors, calibration methods, and station placements.
This dashboard converts all 3 to the same US EPA PM2.5 AQI scale using:
- **IQAir** → AQI reported directly
- **AQICN** → PM2.5 value converted via `pm25_to_us_epa_aqi()`
- **Udara Jakarta** → ISPU converted via `ispu_to_epa()` (Indonesian standard → US EPA)

Disagreements between sources can indicate sensor drift, localized pollution, or calibration differences.
""")

st.divider()

# ── Freshness Filter ──────────────────────────────────────────
freshness_hours = st.selectbox(
    "Show only stations updated within",
    [1, 2, 3, 6, 12, 24],
    index=1,
    format_func=lambda x: f"Last {x} hour{'s' if x > 1 else ''}",
)

now    = datetime.now()
cutoff = now - timedelta(hours=freshness_hours)

st.divider()

# ── Current Snapshot ──────────────────────────────────────────
st.subheader("📸 Current Snapshot — All Sources Side by Side")

col1, col2, col3 = st.columns(3)

def render_source_table(source_key: str, label: str):
    df = get_latest_by_source(source_key)
    st.markdown(f"#### {label}")

    if df.empty:
        st.info("No data available.")
        return

    # Apply freshness filter
    df["ts_dt"] = pd.to_datetime(df["timestamp_wib"])
    df = df[df["ts_dt"] >= pd.Timestamp(cutoff)]

    if df.empty:
        st.info(f"No stations updated within last {freshness_hours}h.")
        return

    df = df.dropna(subset=["aqi_pm25_us_epa"]).sort_values("aqi_pm25_us_epa", ascending=False)

    # Format timestamp_wib for display — show only HH:MM
    df["Updated (WIB)"] = pd.to_datetime(df["timestamp_wib"]).dt.strftime("%Y-%m-%d %H:%M")

    # Build display dataframe
    display_df = df[["station", "aqi_pm25_us_epa", "category", "density_ugm3", "Updated (WIB)"]].copy()
    display_df.columns = ["Station", "AQI", "Category", "PM2.5 µg/m³", "Updated (WIB)"]

    st.dataframe(display_df, hide_index=True, height=300)

    avg = df["aqi_pm25_us_epa"].mean()
    worst_station = df.loc[df["aqi_pm25_us_epa"].idxmax(), "station"]
    st.metric(
        "Network Average",
        f"{avg:.0f} AQI",
        delta=worst_station,
        delta_color="inverse",
        help="Worst station shown as delta"
    )
    st.caption(f"{len(df)} stations · updated within last {freshness_hours}h")

with col1:
    render_source_table("iqair_readings", "🔵 IQAir")
with col2:
    render_source_table("aqicn_readings", "🟢 AQICN")
with col3:
    render_source_table("udara_readings", "🟠 Udara Jakarta")

st.divider()

# ── Historical Overlay ────────────────────────────────────────
st.subheader("📉 Historical Overlay — Same Time Axis")
st.caption("Select one station from each source to compare trends")

col1, col2, col3, col4 = st.columns([2, 2, 2, 1])

with col1:
    iqair_stations = get_station_list("iqair_readings")
    iqair_sel = st.selectbox(
        "IQAir station", iqair_stations,
        index=iqair_stations.index("Semanggi") if "Semanggi" in iqair_stations else 0
    )

with col2:
    aqicn_stations = get_station_list("aqicn_readings")
    aqicn_sel = st.selectbox("AQICN station", aqicn_stations)

with col3:
    udara_stations = get_station_list("udara_readings")
    udara_sel = st.selectbox(
        "Udara Jakarta station", udara_stations,
        index=udara_stations.index("DKJ01 Bundaran HI") if "DKJ01 Bundaran HI" in udara_stations else 0
    )

with col4:
    hist_hours = st.selectbox(
        "Range", [24, 48, 72, 168], index=1,
        format_func=lambda x: f"{x}h"
    )

comp_df = get_comparison_history(iqair_sel, aqicn_sel, udara_sel, hist_hours)

if not comp_df.empty:
    color_map = {
        "IQAir":         "#4fc3f7",
        "AQICN":         "#66bb6a",
        "Udara Jakarta": "#ffa726",
    }

    fig = go.Figure()
    for source_label, color in color_map.items():
        src_df = comp_df[comp_df["source_label"] == source_label]
        if src_df.empty:
            continue
        station_name = src_df["station"].iloc[0]
        fig.add_trace(go.Scatter(
            x=src_df["timestamp_wib"],
            y=src_df["aqi_pm25_us_epa"],
            name=f"{source_label} — {station_name}",
            line=dict(color=color, width=2),
            mode="lines+markers",
            marker=dict(size=4),
        ))

    for level, color, label in [
        (50,  "#00e400", "Good"),
        (100, "#ffff00", "Moderate"),
        (150, "#ff7e00", "Sensitive"),
        (200, "#ff0000", "Unhealthy"),
    ]:
        fig.add_hline(
            y=level, line_dash="dot", line_color=color,
            opacity=0.3, annotation_text=label,
            annotation_position="right"
        )

    fig.update_layout(
        height=460,
        plot_bgcolor="#0e1117",
        paper_bgcolor="#0e1117",
        font_color="#f0f0f0",
        xaxis=dict(gridcolor="#2a2a2a", title="Time (WIB)"),
        yaxis=dict(gridcolor="#2a2a2a", title="AQI PM2.5 (US EPA)"),
        legend=dict(bgcolor="#1a1a2e"),
        hovermode="x unified",
        title=f"Source Comparison — Last {hist_hours}h",
    )
    st.plotly_chart(fig, use_container_width=True)

    # ── Agreement Analysis ─────────────────────────────────────
    st.subheader("📊 Agreement Analysis")
    st.caption("How much do sources agree at each hour?")

    pivot = comp_df.pivot_table(
        index="timestamp_wib",
        columns="source_label",
        values="aqi_pm25_us_epa",
        aggfunc="mean"
    )

    if pivot.shape[1] >= 2:
        pivot["spread"] = pivot.max(axis=1) - pivot.min(axis=1)
        pivot["agreement"] = pivot["spread"].apply(
            lambda x: "High" if x <= 25 else "Medium" if x <= 50 else "Low"
        )
        agree_counts = pivot["agreement"].value_counts()

        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("🟢 High Agreement", f"{agree_counts.get('High', 0)} hours",
                      help="Sources within 25 AQI of each other")
        with c2:
            st.metric("🟡 Medium Agreement", f"{agree_counts.get('Medium', 0)} hours",
                      help="Sources within 25–50 AQI of each other")
        with c3:
            st.metric("🔴 Low Agreement", f"{agree_counts.get('Low', 0)} hours",
                      help="Sources differ by more than 50 AQI")

        fig_spread = px.area(
            pivot.reset_index(),
            x="timestamp_wib", y="spread",
            labels={"spread": "AQI Spread (Max−Min)", "timestamp_wib": "Time (WIB)"},
            color_discrete_sequence=["#ff7e00"],
            height=250,
        )
        fig_spread.update_layout(
            plot_bgcolor="#0e1117", paper_bgcolor="#0e1117",
            font_color="#f0f0f0",
            xaxis=dict(gridcolor="#2a2a2a"),
            yaxis=dict(gridcolor="#2a2a2a"),
        )
        st.plotly_chart(fig_spread, use_container_width=True)
        st.caption("Lower spread = higher agreement · Spikes = measurement discrepancies between sources")
else:
    st.info("No overlapping data found for selected stations and time range.")
