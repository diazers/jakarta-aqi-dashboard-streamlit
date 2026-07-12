"""
db.py — Database query functions for Jakarta AQI Dashboard
All queries use air_quality_pm25_combined for consistency.

Table schema:
    timestamp_wib   TIMESTAMP    WIB local time (no tz)
    timestamp_utc   TIMESTAMPTZ  UTC with tz
    measurement_time
    station         TEXT
    source          TEXT         'iqair_readings' | 'aqicn_readings' | 'udara_readings'
    aqi_pm25_us_epa INTEGER      US EPA AQI — comparable across all 3 sources
    category        TEXT         US EPA category label
    density_ugm3    NUMERIC      PM2.5 µg/m³
    temperature_c   NUMERIC      IQAir only (NULL for others)
    humidity_pct    NUMERIC      IQAir only
    wind_speed_kmh  NUMERIC      IQAir only
    pressure_mbar   NUMERIC      IQAir only
"""

import streamlit as st
import pandas as pd

# Source display labels
SOURCE_LABELS = {
    "iqair_readings":  "IQAir",
    "aqicn_readings":  "AQICN",
    "udara_readings":  "Udara Jakarta",
}

# ─────────────────────────────────────────────
# AQI COLOR & CATEGORY HELPERS
# ─────────────────────────────────────────────

def aqi_color(aqi) -> str:
    """Return hex color based on US EPA AQI value."""
    if aqi is None or pd.isna(aqi):
        return "#888888"
    aqi = float(aqi)
    if aqi <= 50:   return "#00e400"
    if aqi <= 100:  return "#ffff00"
    if aqi <= 150:  return "#ff7e00"
    if aqi <= 200:  return "#ff0000"
    if aqi <= 300:  return "#8f3f97"
    return "#7e0023"


def aqi_category(aqi) -> str:
    """Return US EPA AQI category label."""
    if aqi is None or pd.isna(aqi):
        return "Unknown"
    aqi = float(aqi)
    if aqi <= 50:   return "Good"
    if aqi <= 100:  return "Moderate"
    if aqi <= 150:  return "Unhealthy for Sensitive Groups"
    if aqi <= 200:  return "Unhealthy"
    if aqi <= 300:  return "Very Unhealthy"
    return "Hazardous"


# ─────────────────────────────────────────────
# CONNECTION
# ─────────────────────────────────────────────
# Version 1 in local run
# def get_conn():
    # return st.connection("postgresql", type="sql")
    
# Version 2 run in postit connect cloud
import os
import streamlit as st

def get_conn():
    if os.getenv("connections_postgresql_host"):
        # Posit Cloud / production — use environment variables
        return st.connection(
            "postgresql",
            type="sql",
            dialect="postgresql+psycopg2",
            host=os.getenv("connections_postgresql_host"),
            port=os.getenv("connections_postgresql_port", "5432"),
            database=os.getenv("connections_postgresql_database"),
            username=os.getenv("connections_postgresql_username"),
            password=os.getenv("connections_postgresql_password"),
        )
    else:
        # Local — use secrets.toml
        return st.connection("postgresql", type="sql")



# #check connection
# import streamlit as st
# # Temporary debug check
# if "connections" in st.secrets and "postgresql" in st.secrets["connections"]:
    # st.write("✅ Secrets loaded:", {
        # "dialect": st.secrets["connections"]["postgresql"].get("dialect"),
        # "host": st.secrets["connections"]["postgresql"].get("host"),
        # "port": st.secrets["connections"]["postgresql"].get("port"),
        # "database": st.secrets["connections"]["postgresql"].get("database"),
        # "username": st.secrets["connections"]["postgresql"].get("username"),
    # })
# else:
    # st.error("❌ PostgreSQL secrets not found in environment")


# ─────────────────────────────────────────────
# LATEST DATA QUERIES
# ─────────────────────────────────────────────

# @st.cache_data(ttl=600)
def get_latest_all_sources() -> pd.DataFrame:
    """
    Latest AQI reading per station per source.
    Used for: Live Overview map, KPI cards, rankings.
    """
    query = """
        SELECT DISTINCT ON (station, source)
            timestamp_wib, timestamp_utc, measurement_time_ts, station, source,
            aqi_pm25_us_epa, category, density_ugm3,
            temperature_c, humidity_pct, wind_speed_kmh, pressure_mbar
        FROM air_quality_pm25_combined
        WHERE aqi_pm25_us_epa IS NOT NULL
        ORDER BY station, source, timestamp_utc DESC
    """
    df = get_conn().query(query, ttl=0)
    df["source_label"] = df["source"].map(SOURCE_LABELS)
    return df


# @st.cache_data(ttl=600)
def get_latest_by_source(source: str) -> pd.DataFrame:
    """
    Latest AQI per station for a single source.
    source: 'iqair_readings' | 'aqicn_readings' | 'udara_readings'
    """
    query = f"""
        SELECT DISTINCT ON (station)
            timestamp_wib, station, aqi_pm25_us_epa,
            category, density_ugm3,
            temperature_c, humidity_pct, wind_speed_kmh, pressure_mbar,
            measurement_time_ts
        FROM air_quality_pm25_combined
        WHERE source = '{source}'
          AND aqi_pm25_us_epa IS NOT NULL
        ORDER BY station, measurement_time_ts DESC
    """
    return get_conn().query(query, ttl=0)


# ─────────────────────────────────────────────
# HISTORICAL QUERIES
# ─────────────────────────────────────────────

@st.cache_data(ttl=600)
def get_history(station: str, source: str, hours: int = 48) -> pd.DataFrame:
    """
    Historical AQI for a single station + source.
    Used for: Historical Trends, Station Detail, Source Comparison.
    """
    query = f"""
        SELECT
            timestamp_wib, aqi_pm25_us_epa, category,
            density_ugm3, temperature_c, humidity_pct,
            wind_speed_kmh, pressure_mbar,
            measurement_time_ts
        FROM air_quality_pm25_combined
        WHERE station = '{station}'
          AND source  = '{source}'
          AND timestamp_utc >= NOW() - INTERVAL '{hours} hours'
          AND aqi_pm25_us_epa IS NOT NULL
        ORDER BY timestamp_utc ASC
    """
    return get_conn().query(query, ttl=600)


@st.cache_data(ttl=600)
def get_history_multi_station(stations: list, source: str, hours: int = 48) -> pd.DataFrame:
    """
    Historical AQI for multiple stations from same source.
    Used for: Historical Trends line chart.
    """
    station_list = "', '".join(stations)
    query = f"""
        SELECT
            timestamp_wib, measurement_time_ts, station, aqi_pm25_us_epa, density_ugm3
        FROM air_quality_pm25_combined
        WHERE station IN ('{station_list}')
          AND source = '{source}'
          AND timestamp_utc >= NOW() - INTERVAL '{hours} hours'
          AND aqi_pm25_us_epa IS NOT NULL
        ORDER BY timestamp_utc ASC
    """
    return get_conn().query(query, ttl=600)


@st.cache_data(ttl=600)
def get_hourly_city_avg(hours: int = 48) -> pd.DataFrame:
    """
    Hourly average/min/max AQI across all IQAir stations.
    Used for: Historical Trends city average chart.
    """
    query = f"""
        SELECT
            date_trunc('hour', timestamp_utc) AS hour,
            ROUND(AVG(aqi_pm25_us_epa))       AS avg_aqi,
            MIN(aqi_pm25_us_epa)               AS min_aqi,
            MAX(aqi_pm25_us_epa)               AS max_aqi,
            COUNT(DISTINCT station)            AS station_count
        FROM air_quality_pm25_combined
        WHERE source = 'iqair_readings'
          AND timestamp_utc >= NOW() - INTERVAL '{hours} hours'
          AND aqi_pm25_us_epa IS NOT NULL
        GROUP BY date_trunc('hour', timestamp_utc)
        ORDER BY hour ASC
    """
    return get_conn().query(query, ttl=600)


# ─────────────────────────────────────────────
# SOURCE COMPARISON QUERIES
# ─────────────────────────────────────────────

@st.cache_data(ttl=600)
def get_comparison_history(
    iqair_station: str,
    aqicn_station: str,
    udara_station: str,
    hours: int = 48
) -> pd.DataFrame:
    """
    Hourly AQI from all 3 sources in one query.
    Used for: Source Comparison overlay chart.
    Returns long-format DataFrame with source column.
    """
    query = f"""
        SELECT timestamp_wib, measurement_time_ts, station, source, aqi_pm25_us_epa
        FROM air_quality_pm25_combined
        WHERE timestamp_utc >= NOW() - INTERVAL '{hours} hours'
          AND aqi_pm25_us_epa IS NOT NULL
          AND (
              (source = 'iqair_readings'  AND station = '{iqair_station}')  OR
              (source = 'aqicn_readings'  AND station = '{aqicn_station}')  OR
              (source = 'udara_readings'  AND station = '{udara_station}')
          )
        ORDER BY timestamp_utc ASC
    """
    df = get_conn().query(query, ttl=600)
    df["source_label"] = df["source"].map(SOURCE_LABELS)
    return df


# ─────────────────────────────────────────────
# STATION LIST QUERIES
# ─────────────────────────────────────────────

@st.cache_data(ttl=3600)  # cache 1 hour — station list rarely changes
def get_station_list(source: str) -> list:
    """
    List of stations for a given source.
    source: 'iqair_readings' | 'aqicn_readings' | 'udara_readings'
    """
    query = f"""
        SELECT DISTINCT station
        FROM air_quality_pm25_combined
        WHERE source = '{source}'
        ORDER BY station
    """
    df = get_conn().query(query, ttl=3600)
    return df["station"].tolist()


@st.cache_data(ttl=3600)
def get_all_sources() -> list:
    return ["iqair_readings", "aqicn_readings", "udara_readings"]


# ─────────────────────────────────────────────
# KPI QUERIES
# ─────────────────────────────────────────────

# @st.cache_data(ttl=600)
def get_city_kpis() -> dict:
    """
    Summary KPIs for the Live Overview page.
    Returns dict with avg, worst, best station info.
    """
    df = get_latest_all_sources()
    if df.empty:
        return {}

    df = df.dropna(subset=["aqi_pm25_us_epa"])
    worst = df.loc[df["aqi_pm25_us_epa"].idxmax()]
    best  = df.loc[df["aqi_pm25_us_epa"].idxmin()]

    return {
        "avg_aqi":       round(df["aqi_pm25_us_epa"].mean(), 1),
        "worst_station": worst["station"],
        "worst_aqi":     int(worst["aqi_pm25_us_epa"]),
        "worst_source":  SOURCE_LABELS.get(worst["source"], worst["source"]),
        "best_station":  best["station"],
        "best_aqi":      int(best["aqi_pm25_us_epa"]),
        "best_source":   SOURCE_LABELS.get(best["source"], best["source"]),
        "total_stations": df["station"].nunique(),
        "total_sources":  df["source"].nunique(),
    }
