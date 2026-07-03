"""
pages/5_Station_Map.py — Interactive map of monitoring stations.

- Loads station coordinates from data/stations.csv
- Marks a station as "eligible" (green) if it has rows in pm25_forecasts
  from the most recent forecast run, otherwise "ineligible" (gray)
- Click a dot -> shows a line chart of actual PM2.5 (last 30 days) plus
  the forecast median (q50) with a shaded q30-q70 band, matching the
  style of your existing multi-panel forecast chart.

Assumes stations.csv has at minimum: station, lat, lon
Optionally: source  (needed if the same station name appears under more
than one source, e.g. "Kemayoran" in both iqair_readings and aqicn_readings)

Requires: streamlit-folium, folium  (add to requirements.txt)
    pip install streamlit-folium folium
"""

import os
import pandas as pd
import folium
from streamlit_folium import st_folium
import matplotlib.pyplot as plt
import streamlit as st
from sqlalchemy import create_engine

ID_SEP = "||"
HISTORY_DAYS_TO_SHOW = 30
 
# Keep this in sync with scripts/run_forecast.py's TARGET_STATIONS -- this is
# the same curated pilot list, used here to restrict the map to stations we
# actually forecast for (everything else in stations.csv is out of scope and
# would just show up permanently gray).
TARGET_STATIONS = [
    ("Kemayoran", "iqair_readings"),
    ("Semanggi", "iqair_readings"),
    ("Agung Sedayu Group - WTP Ebony (BGM)", "iqair_readings"),
    ("pasir putih", "iqair_readings"),
    ("Duitku PG, Kebon Jeruk", "iqair_readings"),
    ("TANGKAS SPORTS CENTRE", "iqair_readings"),
    ("Cilandak Barat", "iqair_readings"),
    ("Kemang Timur V", "iqair_readings"),
    ("Rambutan, Ciracas", "iqair_readings"),
    ("Shinano, Jakarta Garden City", "iqair_readings"),
    ("DKI01 Bundaran HI", "udara_readings"),
    ("DKI02 Kelapa Gading", "udara_readings"),
    ("DKI03 Jagakarsa", "udara_readings"),
    ("DKI04 Lubang Buaya", "udara_readings"),
    ("DKI05 Kebun Jeruk", "udara_readings"),
    ("Jakarta GBK Gelora", "aqicn_readings"),
    ("Kedoya Utara Nafas", "aqicn_readings"),
    ("Kemayoran", "aqicn_readings"),
    ("Krukut", "aqicn_readings"),
    ("Pakubuwono 3 Nafas", "aqicn_readings"),
    ("Pakubuwono Menteng", "aqicn_readings"),
]
TARGET_STATION_NAMES = {name for name, _source in TARGET_STATIONS}
 
st.set_page_config(page_title="Station Map", layout="wide")
st.title("Station Map — Click a station for its forecast")


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

st.cache_resource
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
 
 
def get_engine():
    return get_conn().engine


@st.cache_data(ttl=300)
def load_stations() -> pd.DataFrame:
    bad_rows = []

    def _on_bad_line(bad_line):
        bad_rows.append(bad_line)
        return None  # drop the row instead of raising

    try:
        df = pd.read_csv("data/stations.csv")
    except pd.errors.ParserError:
        df = pd.read_csv(
            "data/stations.csv",
            engine="python",
            on_bad_lines=_on_bad_line,
        )

    if bad_rows:
        st.warning(
            f"Skipped {len(bad_rows)} malformed row(s) in stations.csv "
            f"(likely a station name containing an unquoted comma, e.g. "
            f"'Rambutan, Ciracas'). These stations won't appear on the map "
            f"until fixed in the CSV: {bad_rows}"
        )

    df.columns = [c.strip().lower() for c in df.columns]

    rename_map = {}
    if "latitude" in df.columns:
        rename_map["latitude"] = "lat"
    if "longitude" in df.columns:
        rename_map["longitude"] = "lon"
    if "station_name" in df.columns and "station" not in df.columns:
        rename_map["station_name"] = "station"
    elif "name" in df.columns and "station" not in df.columns:
        rename_map["name"] = "station"
    df = df.rename(columns=rename_map)
    missing = {"station", "lat", "lon"} - set(df.columns)
    if missing:
        st.error(f"stations.csv is missing expected column(s): {missing}. "
                  f"Found columns: {list(df.columns)}")
        st.stop()

    if "source" in df.columns:
        df["source"] = df["source"].apply(normalize_source)

    return df



def normalize_source(raw: str) -> str:
    """
    stations.csv uses short labels (e.g. "UDARA JKT") while pm25_forecasts /
    air_quality_pm25_combined use "*_readings" identifiers (e.g.
    "udara_readings"). Match by keyword rather than exact string so this
    survives minor label variations.
    """
    if pd.isna(raw):
        return raw
    text = str(raw).strip().lower()
    if "udara" in text:
        return "udara_readings"
    if "iqair" in text:
        return "iqair_readings"
    if "aqicn" in text:
        return "aqicn_readings"
    # unrecognized label -- leave as-is so it's visible rather than silently dropped
    return text


@st.cache_data(ttl=300)
def load_latest_forecasts(_engine) -> pd.DataFrame:
    """Latest forecast run only, keyed by station+source."""
    query = """
        WITH latest AS (
            SELECT MAX(generated_at) AS max_gen FROM pm25_forecasts
        )
        SELECT f.station, f.source, f.timestamp, f.q30, f.q50, f.q70, f.generated_at
        FROM pm25_forecasts f, latest
        WHERE f.generated_at = latest.max_gen
        ORDER BY f.station, f.source, f.timestamp
    """
    return pd.read_sql(query, _engine)


@st.cache_data(ttl=300)
def load_history(_engine, station: str, source: str) -> pd.DataFrame:
    query = """
        SELECT measurement_time_ts AS timestamp, density_ugm3 AS value
        FROM air_quality_pm25_combined
        WHERE station = %(station)s
          AND source = %(source)s
          AND measurement_time_ts >= NOW() - INTERVAL '%(days)s days'
          AND density_ugm3 IS NOT NULL
        ORDER BY measurement_time_ts
    """ % {"station": "%(station)s", "source": "%(source)s", "days": HISTORY_DAYS_TO_SHOW}
    return pd.read_sql(
        query, _engine,
        params={"station": station, "source": source},
    )


engine = get_engine()
stations = load_stations()
 
# folium crashes on NaN coordinates -- drop and warn instead of failing the page
missing_coords = stations[stations["lat"].isna() | stations["lon"].isna()]
if not missing_coords.empty:
    st.warning(
        f"{len(missing_coords)} station(s) have missing lat/lon and won't be "
        f"shown on the map: {missing_coords['station'].tolist()}"
    )
stations = stations.dropna(subset=["lat", "lon"])
 
# Restrict the map to the curated pilot list only -- match on (station, source)
# when source is available, otherwise fall back to station name alone.
if has_source_col := ("source" in stations.columns):
    target_pairs = set(TARGET_STATIONS)
    in_target = stations.apply(
        lambda r: (r["station"], r["source"]) in target_pairs, axis=1
    )
else:
    in_target = stations["station"].isin(TARGET_STATION_NAMES)
 
stations = stations[in_target]
forecasts = load_latest_forecasts(engine)
 
# which station+source combos are eligible (have a forecast this run)
eligible_keys = set(
    (forecasts["station"] + ID_SEP + forecasts["source"]).unique()
) if not forecasts.empty else set()


# ---------------------------------------------------------------------------
# Build the map
# ---------------------------------------------------------------------------

center_lat = stations["lat"].mean()
center_lon = stations["lon"].mean()
m = folium.Map(location=[center_lat, center_lon], zoom_start=11, tiles="CartoDB positron")

for _, row in stations.iterrows():
    station_name = row["station"]

    if has_source_col and pd.notna(row.get("source")):
        sources_here = [row["source"]]
    else:
        # figure out which sources this station name has in the forecast table
        sources_here = sorted(forecasts.loc[forecasts["station"] == station_name, "source"].unique())
        if not sources_here:
            sources_here = ["unknown"]

    is_eligible = any(f"{station_name}{ID_SEP}{s}" in eligible_keys for s in sources_here)
    color = "green" if is_eligible else "gray"

    tooltip_text = station_name if len(sources_here) <= 1 else f"{station_name} ({'/'.join(sources_here)})"

    folium.CircleMarker(
        location=[row["lat"], row["lon"]],
        radius=8,
        color=color,
        fill=True,
        fill_color=color,
        fill_opacity=0.85,
        tooltip=tooltip_text,
        popup=station_name,
    ).add_to(m)

st.caption("🟢 green = has a forecast from the latest run   🔘 gray = not eligible (insufficient history/gap this run)")

map_data = st_folium(m, height=520, use_container_width=True)


# ---------------------------------------------------------------------------
# Handle click -> resolve station (+ source if ambiguous) -> plot
# ---------------------------------------------------------------------------

clicked_name = map_data.get("last_object_clicked_tooltip") if map_data else None
# tooltip may include "(source1/source2)" suffix -- strip it back to plain station name
clicked_station = clicked_name.split(" (")[0] if clicked_name else None

if not clicked_station:
    st.info("Click a station dot on the map to see its forecast.")
    st.stop()

st.subheader(clicked_station)

candidate_sources = sorted(forecasts.loc[forecasts["station"] == clicked_station, "source"].unique())

if len(candidate_sources) == 0:
    st.warning("This station has no forecast from the latest run (not eligible this time).")
    st.stop()
elif len(candidate_sources) > 1:
    source = st.selectbox("Source", candidate_sources)
else:
    source = candidate_sources[0]

station_forecast = forecasts[
    (forecasts["station"] == clicked_station) & (forecasts["source"] == source)
].sort_values("timestamp")

history = load_history(engine, clicked_station, source)

fig, ax = plt.subplots(figsize=(10, 4))

if not history.empty:
    ax.plot(history["timestamp"], history["value"], color="tab:blue", label="Actual")

if not station_forecast.empty:
    ax.fill_between(
        station_forecast["timestamp"], station_forecast["q30"], station_forecast["q70"],
        color="orange", alpha=0.3, label="30-70% interval",
    )
    ax.plot(
        station_forecast["timestamp"], station_forecast["q50"],
        color="darkorange", linewidth=2, label="Forecast (median)",
    )
    ax.axvline(station_forecast["timestamp"].min(), color="red", linestyle="--", linewidth=1)

ax.set_ylabel("AQI PM2.5")
ax.set_title(f"{clicked_station} ({source})")
ax.legend(loc="upper left")
fig.autofmt_xdate()

st.pyplot(fig)

with st.expander("Latest forecast values"):
    st.dataframe(station_forecast[["timestamp", "q30", "q50", "q70"]], use_container_width=True)
