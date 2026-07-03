"""
run_forecast.py — Generates PM2.5 forecasts using TabPFN-TS and writes
them to the pm25_forecasts table in the same Postgres database the
Streamlit app reads from.

Run by .github/workflows/pm25-forecast.yml on a schedule (and/or
externally triggered via workflow_dispatch, e.g. from cronjob.org).

Schema confirmed against real predict_df() output:
  item_id, timestamp, target (== 0.5 quantile exactly), 0.1, 0.3, 0.7, 0.9 (quantiles)
  -> only q30, q50, q70 are written to pm25_forecasts (q10/q90 intentionally dropped)
"""

import os
import pandas as pd
from sqlalchemy import create_engine
from tabpfn_time_series import TabPFNTSPipeline

HISTORY_HOURS = 24 * 30   # 30 days of context per series
PREDICTION_LENGTH = 6      # forecast next 6 hours
ID_SEP = "||"              # separator used to pack station+source into item_id
MIN_HISTORY_DAYS = 30      # skip a series with less span than this, even if individual points exist
MAX_GAP_HOURS = 48         # skip a series if any single continuous gap exceeds this --
                           # gaps up to this length get a seasonal (same-hour-yesterday)
                           # fill, not a flat line, so this can be more generous than
                           # a pure-interpolation approach would allow

# Curated station list, eligible only orr pass the thresshold-
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


def get_engine():
    user = os.environ["PGUSER"]
    pwd = os.environ["PGPASSWORD"]
    host = os.environ["PGHOST"]
    port = os.environ.get("PGPORT", "5432")
    db = os.environ["PGDATABASE"]
    return create_engine(f"postgresql+psycopg2://{user}:{pwd}@{host}:{port}/{db}")


def fetch_history(engine) -> pd.DataFrame:
    query = f"""
        SELECT
            station || '{ID_SEP}' || source AS item_id,
            measurement_time_ts               AS timestamp,
            density_ugm3                       AS target
        FROM air_quality_pm25_combined
        WHERE measurement_time_ts >= NOW() - INTERVAL '{HISTORY_HOURS} hours'
          AND density_ugm3 IS NOT NULL
        ORDER BY item_id, timestamp
    """
    return pd.read_sql(query, engine)


def filter_to_target_stations(history: pd.DataFrame) -> pd.DataFrame:
    """
    Restrict to the curated pilot list above. Run this before
    select_valid_series() so the span/gap checks (and their printed
    skip reasons) only ever talk about the ~20 stations that actually
    matter, not all stations sitting in the wider DB.
    """
    target_item_ids = {f"{station}{ID_SEP}{source}" for station, source in TARGET_STATIONS}
    filtered = history[history["item_id"].isin(target_item_ids)]

    found_ids = set(filtered["item_id"].unique())
    missing = target_item_ids - found_ids
    if missing:
        print(f"No data at all for {len(missing)} target station(s) "
              f"(check spelling, or they may just be outside the {HISTORY_HOURS}h window):")
        for m in sorted(missing):
            print(f"  - {m}")

    return filtered


def select_valid_series(history: pd.DataFrame) -> pd.DataFrame:
    """
    Keep a series only if it has at least MIN_HISTORY_DAYS of span AND no
    single continuous gap longer than MAX_GAP_HOURS. Checked on the raw
    fetched rows, before fill_gaps() runs -- a series with a 10-day blind
    spot can still "have enough points" on paper, but interpolating across
    10 days is fabricating data, not filling a gap, so it gets dropped
    here instead of silently smoothed over.
    """
    keep_ids = []
    dropped = []

    for item_id, g in history.groupby("item_id"):
        g = g.sort_values("timestamp")
        span_days = (g["timestamp"].max() - g["timestamp"].min()).total_seconds() / 86400
        if span_days < MIN_HISTORY_DAYS:
            dropped.append((item_id, f"only {span_days:.1f} days of span"))
            continue

        gaps = g["timestamp"].diff().dropna()
        max_gap_hours = gaps.max().total_seconds() / 3600 if not gaps.empty else 0
        if max_gap_hours > MAX_GAP_HOURS:
            dropped.append((item_id, f"largest gap is {max_gap_hours:.1f}h"))
            continue

        keep_ids.append(item_id)

    if dropped:
        print(f"Skipped {len(dropped)} series:")
        for item_id, reason in dropped:
            print(f"  - {item_id}: {reason}")

    return history[history["item_id"].isin(keep_ids)]


def fill_gaps(history: pd.DataFrame) -> pd.DataFrame:
    """
    Reindex each station's series to a regular hourly grid and interpolate
    missing values.

    IMPORTANT: raw readings are floored to their containing clock hour
    (15:07 -> 15:00, 15:52 -> 15:00) *before* building the hourly grid.
    That silently discarded most or all real recent readings (including the most-recent one) and replaced
    them with the seasonal/interpolated fill, producing forecasts that started from a fabricated value instead of the true last reading. This
    was most visible on the DKI (udara_readings) stations, whose reporting cadence drifts further from an arbitrary grid than IQAir's.
    """
    filled = []
    for item_id, g in history.groupby("item_id"):
        g = g.set_index("timestamp").sort_index()

        # Bucket every raw reading into its containing clock hour instead of
        # reindexing to a grid offset from the first raw timestamp.
        g.index = g.index.floor("h")

        # Some sources occasionally log more than one reading for the same
        # hour -- collapse duplicates into a single averaged value before
        # building the regular grid, since reindex() requires a unique index.
        g = g.groupby(level=0)["target"].mean().to_frame()
        full_idx = pd.date_range(g.index.min(), g.index.max(), freq="h")
        g = g.reindex(full_idx)

        # Seasonal fill: for each missing hour, first borrow the value from
        # the same hour the day before, then the day after, before falling
        # back to plain interpolation. This preserves the daily PM2.5 cycle
        # through a multi-hour gap instead of flattening it into a straight
        # line -- important now that MAX_GAP_HOURS allows gaps up to 2 days.
        g["target"] = g["target"].fillna(g["target"].shift(24))
        g["target"] = g["target"].fillna(g["target"].shift(-24))
        g["target"] = g["target"].interpolate(limit_direction="both")

        g["item_id"] = item_id
        g.index.name = "timestamp"
        filled.append(g.reset_index())
    return pd.concat(filled, ignore_index=True)


def main():
    engine = get_engine()
    history = fetch_history(engine)

    if history.empty:
        print("No history available — skipping this run.")
        return

    history = filter_to_target_stations(history)

    if history.empty:
        print("None of the target stations had any data — skipping this run.")
        return

    # Drop series with too little history or a gap too long to safely interpolate
    history = select_valid_series(history)

    if history.empty:
        print("No series passed the history/gap checks — skipping this run.")
        return

    n_series = history["item_id"].nunique()
    history = fill_gaps(history)

    pipeline = TabPFNTSPipeline()
    forecast = pipeline.predict_df(history, prediction_length=PREDICTION_LENGTH)

    if "item_id" not in forecast.columns or "timestamp" not in forecast.columns:
        forecast = forecast.reset_index()

    forecast[["station", "source"]] = forecast["item_id"].str.split(
        ID_SEP, n=1, expand=True, regex=False
    )
    forecast["generated_at"] = pd.Timestamp.utcnow()

    # target == the 0.5 quantile exactly (confirmed: (fdf[0.5]-fdf['target']).abs().max() == 0.0)
    # so it's renamed straight to q50 rather than kept as a separate "median" column.
    # Only q30/q50/q70 are kept -- q10/q90 dropped on purpose (storage + a simpler
    # band for a 6-hour-ahead chart; see chat for the trade-off if you want them back).
    out = forecast.rename(columns={
        "target": "q50",
        0.3: "q30",
        0.7: "q70",
    })
    keep_cols = [c for c in
                 ["station", "source", "timestamp", "q30", "q50", "q70", "generated_at"]
                 if c in out.columns]
    out = out[keep_cols]

    out.to_sql("pm25_forecasts", engine, if_exists="append", index=False)
    print(f"Wrote {len(out)} forecast rows for {n_series} series.")


if __name__ == "__main__":
    main()
