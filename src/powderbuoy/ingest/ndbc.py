"""Download, parse, and aggregate NOAA NDBC buoy standard meteorological data.

Produces `data/processed/buoy_daily.parquet` — the predictor side of the
project. Historical archive files come in three header formats across the
record; the header of each file is parsed to detect which one applies, never
assumed from the year.
"""

from __future__ import annotations

import argparse
import datetime as dt
import gzip
import io
import logging
import time
from pathlib import Path

import numpy as np
import pandas as pd
import requests

from powderbuoy.config import load_config

logger = logging.getLogger(__name__)

HISTORICAL_URL = "https://www.ndbc.noaa.gov/data/historical/stdmet/{station}h{year}.txt.gz"
STATION_TABLE_URL = "https://www.ndbc.noaa.gov/data/stations/station_table.txt"
USER_AGENT = "powderbuoy-research-script/0.1"

DEFAULT_REQUEST_DELAY_SECONDS = 0.5
DEFAULT_REQUEST_TIMEOUT_SECONDS = 30
DEFAULT_MAX_RETRIES = 3

# An all-nines value in a field is missing, not data. BAR is the pre-2007 name
# for the field renamed PRES from 2007 onward; both share PRES's sentinel.
SENTINELS = {
    "WVHT": 99.00, "DPD": 99.00, "APD": 99.00,
    "MWD": 999, "WDIR": 999,
    "WSPD": 99.0, "GST": 99.0,
    "PRES": 9999.0, "BAR": 9999.0,
    "ATMP": 999.0, "WTMP": 999.0, "DEWP": 999.0,
}

KEEP_FIELDS = ["WVHT", "DPD", "APD", "MWD", "WSPD", "PRES"]

DAILY_COLUMNS = [
    "date", "station",
    "wvht_mean", "wvht_max", "wvht_min",
    "dpd_mean", "dpd_max",
    "apd_mean",
    "mwd_mean",
    "wspd_mean", "wspd_max",
    "pres_mean", "pres_min",
    "n_obs",
]


def circular_mean_deg(degrees):
    """Mean of directions in degrees. Returns None if no valid values."""
    d = np.asarray([x for x in degrees if x is not None and not np.isnan(x)])
    if d.size == 0:
        return None
    rad = np.deg2rad(d)
    mean = np.arctan2(np.sin(rad).mean(), np.cos(rad).mean())
    return float(np.rad2deg(mean) % 360)


def _expand_two_digit_year(year: int) -> int:
    """NDBC convention: values >= 70 are 19xx, else 20xx."""
    return 1900 + year if year >= 70 else 2000 + year


def apply_sentinels(df: pd.DataFrame) -> pd.DataFrame:
    """Convert NDBC sentinel missing-value codes to NaN in any recognised column.

    Applied before any aggregation touches the numbers — a single unconverted
    sentinel in a daily mean silently ruins that day (SPEC rule 2.5).
    """
    df = df.copy()
    for field, sentinel in SENTINELS.items():
        if field in df.columns:
            values = pd.to_numeric(df[field], errors="coerce")
            df[field] = values.where(~np.isclose(values, sentinel, atol=1e-6), np.nan)
    return df


def download_station_year(
    station: str, year: int, raw_dir: Path, session: requests.Session
) -> Path | None:
    """Download one station-year archive to raw_dir. Never raises.

    Skips the download if the file already exists (idempotent re-runs).
    Returns the path, or None if the station-year does not exist (404) or the
    download failed after retries. Logs the reason at INFO for 404, WARNING otherwise.
    """
    try:
        raw_dir.mkdir(parents=True, exist_ok=True)
        out_path = raw_dir / f"{station}h{year}.txt.gz"
        if out_path.exists():
            logger.info("%s %d: already downloaded, skipping", station, year)
            return out_path

        url = HISTORICAL_URL.format(station=station, year=year)
        for attempt in range(1, DEFAULT_MAX_RETRIES + 1):
            try:
                resp = session.get(url, timeout=DEFAULT_REQUEST_TIMEOUT_SECONDS)
            except requests.RequestException as exc:
                logger.warning(
                    "%s %d: request error on attempt %d/%d: %s",
                    station, year, attempt, DEFAULT_MAX_RETRIES, exc,
                )
                continue
            if resp.status_code == 404:
                logger.info("%s %d: no data at this URL (404)", station, year)
                return None
            if resp.status_code != 200:
                logger.warning(
                    "%s %d: HTTP %d on attempt %d/%d",
                    station, year, resp.status_code, attempt, DEFAULT_MAX_RETRIES,
                )
                continue
            out_path.write_bytes(resp.content)
            return out_path

        logger.warning("%s %d: giving up after %d attempts", station, year, DEFAULT_MAX_RETRIES)
        return None
    except Exception:
        logger.exception("%s %d: unexpected error downloading", station, year)
        return None


def download_station_history(
    station: str, start_year: int, end_year: int, raw_dir: Path
) -> list[Path]:
    """Download all available years. Applies request_delay_seconds between calls."""
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    paths = []
    for year in range(start_year, end_year + 1):
        path = download_station_year(station, year, raw_dir, session)
        if path is not None:
            paths.append(path)
        time.sleep(DEFAULT_REQUEST_DELAY_SECONDS)
    return paths


def parse_station_year(path: Path) -> pd.DataFrame:
    """Parse one gzipped NDBC standard meteorological file.

    Detects the file era from the header row, not from the year.
    Returns a DataFrame with a UTC 'timestamp' column plus KEEP_FIELDS.
    Sentinel values are converted to NaN.
    Two-digit years are expanded (values >= 70 map to 19xx, else 20xx).
    """
    empty = pd.DataFrame(columns=["timestamp", *KEEP_FIELDS])

    with gzip.open(path, "rt", encoding="latin-1", errors="replace") as f:
        lines = f.readlines()
    if not lines:
        return empty

    header_cols = lines[0].lstrip("#").strip().split()

    # 2007 onward carries a second header line (units) also starting with '#'.
    # 2005-2006 add a minute column but keep a single header line, so presence
    # of 'mm' alone does not indicate a units line to skip.
    data_start = 2 if len(lines) > 1 and lines[1].lstrip().startswith("#") else 1

    data_text = "".join(lines[data_start:]).strip()
    if not data_text:
        return empty

    raw = pd.read_csv(
        io.StringIO(data_text),
        sep=r"\s+",
        header=None,
        names=header_cols,
        engine="python",
    )

    # BAR (pre-2007) and PRES (2007 onward) name the same field.
    if "BAR" in raw.columns and "PRES" not in raw.columns:
        raw = raw.rename(columns={"BAR": "PRES"})

    # The year column is labelled "YY" both pre-2000 (genuinely 2-digit, e.g.
    # 85) and from 2007 onward (already 4-digit, e.g. 2007) — the column name
    # does not reliably indicate which. Detect by magnitude instead.
    year_col = "YY" if "YY" in raw.columns else "YYYY"
    year = pd.to_numeric(raw[year_col], errors="coerce").astype(int)
    year = year.apply(lambda y: _expand_two_digit_year(y) if y < 100 else y)

    month = pd.to_numeric(raw["MM"], errors="coerce").astype(int)
    day = pd.to_numeric(raw["DD"], errors="coerce").astype(int)
    hour = pd.to_numeric(raw["hh"], errors="coerce").astype(int)
    minute = pd.to_numeric(raw["mm"], errors="coerce").astype(int) if "mm" in raw.columns else 0

    timestamp = pd.to_datetime(
        {"year": year, "month": month, "day": day, "hour": hour, "minute": minute},
        utc=True,
    )

    out = pd.DataFrame({"timestamp": timestamp})
    for field in KEEP_FIELDS:
        out[field] = pd.to_numeric(raw[field], errors="coerce") if field in raw.columns else np.nan

    out = apply_sentinels(out)
    return out


def aggregate_daily(df: pd.DataFrame, station: str) -> pd.DataFrame:
    """Aggregate sub-daily observations to one row per UTC calendar day.

    Days with no observations appear as rows with all values null and
    n_obs = 0 (SPEC rule 2.5) — reindexed onto a complete daily calendar from
    the first to the last observed date. Nothing is filled, interpolated, or
    carried forward.
    """
    if df.empty:
        return pd.DataFrame(columns=DAILY_COLUMNS)

    work = df.copy()
    work["date"] = pd.to_datetime(work["timestamp"], utc=True).dt.date

    records = []
    for date, group in work.groupby("date"):
        wvht = group["WVHT"].dropna()
        dpd = group["DPD"].dropna()
        apd = group["APD"].dropna()
        wspd = group["WSPD"].dropna()
        pres = group["PRES"].dropna()
        records.append({
            "date": date,
            "wvht_mean": wvht.mean() if len(wvht) else np.nan,
            "wvht_max": wvht.max() if len(wvht) else np.nan,
            "wvht_min": wvht.min() if len(wvht) else np.nan,
            "dpd_mean": dpd.mean() if len(dpd) else np.nan,
            "dpd_max": dpd.max() if len(dpd) else np.nan,
            "apd_mean": apd.mean() if len(apd) else np.nan,
            "mwd_mean": circular_mean_deg(group["MWD"].dropna().tolist()),
            "wspd_mean": wspd.mean() if len(wspd) else np.nan,
            "wspd_max": wspd.max() if len(wspd) else np.nan,
            "pres_mean": pres.mean() if len(pres) else np.nan,
            "pres_min": pres.min() if len(pres) else np.nan,
            "n_obs": len(group),
        })

    daily = pd.DataFrame.from_records(records).set_index("date").sort_index()
    daily.index = pd.to_datetime(daily.index)

    full_index = pd.date_range(daily.index.min(), daily.index.max(), freq="D", name="date")
    daily = daily.reindex(full_index)
    daily["n_obs"] = daily["n_obs"].fillna(0).astype(int)

    daily = daily.reset_index()
    daily["date"] = daily["date"].dt.date
    daily["station"] = station
    return daily[DAILY_COLUMNS]


def fetch_current_station_position(station: str, session: requests.Session) -> str | None:
    """Best-effort lookup of the station's currently listed lat/lon.

    Historical stdmet archive files do not embed per-observation coordinates,
    so per-year repositioning cannot be checked from file content. This gives
    only the single present-day listing, for context in the report. Never
    raises.
    """
    try:
        resp = session.get(STATION_TABLE_URL, timeout=DEFAULT_REQUEST_TIMEOUT_SECONDS)
        resp.raise_for_status()
    except requests.RequestException as exc:
        logger.warning("Could not fetch station table for %s: %s", station, exc)
        return None
    for line in resp.text.splitlines():
        if line.startswith(f"{station}|"):
            fields = line.split("|")
            if len(fields) >= 7:
                return fields[6].split(" (")[0].strip()
    return None


def _longest_gap(daily: pd.DataFrame) -> tuple[int, str, str] | None:
    """Longest run of consecutive n_obs == 0 days. Returns (length, start, end)."""
    gap_mask = daily["n_obs"] == 0
    if not gap_mask.any():
        return None
    run_id = (gap_mask != gap_mask.shift()).cumsum()
    best = None
    for _, run_id_value in run_id[gap_mask].groupby(run_id[gap_mask]):
        grp = daily.loc[run_id_value.index]
        length = len(grp)
        if best is None or length > best[0]:
            best = (length, str(grp["date"].iloc[0]), str(grp["date"].iloc[-1]))
    return best


def _load_all_years(paths: list[Path]) -> pd.DataFrame:
    frames = [parse_station_year(p) for p in paths]
    frames = [f for f in frames if not f.empty]
    if not frames:
        return pd.DataFrame(columns=["timestamp", *KEEP_FIELDS])
    return pd.concat(frames, ignore_index=True).sort_values("timestamp").reset_index(drop=True)


def build_report(
    station_daily: dict[str, pd.DataFrame],
    station_positions: dict[str, str | None],
) -> str:
    lines = ["NDBC buoy ingest report", "=" * 40, ""]
    for station, daily in station_daily.items():
        lines.append(f"Station {station}")
        lines.append("-" * 20)
        if daily.empty:
            lines.append("No data retrieved.")
            lines.append("")
            continue

        total_days = len(daily)
        empty_days = int((daily["n_obs"] == 0).sum())
        gap = _longest_gap(daily)
        pct_wvht_null = 100.0 * daily["wvht_mean"].isna().sum() / total_days if total_days else float("nan")

        lines.append(f"First date: {daily['date'].min()}")
        lines.append(f"Last date: {daily['date'].max()}")
        lines.append(f"Total days: {total_days}")
        lines.append(f"Days with n_obs = 0 (gap days): {empty_days}")
        if gap:
            length, start, end = gap
            lines.append(f"Longest continuous gap: {length} days ({start} to {end})")
        else:
            lines.append("Longest continuous gap: none")
        lines.append(f"Percent of days with wvht_mean null: {pct_wvht_null:.2f}%")
        lines.append(
            "Distinct positions found in source files: 0 (NDBC historical stdmet "
            "archives do not embed per-observation station coordinates; per-year "
            "repositioning cannot be checked from file content alone)"
        )
        lines.append(
            "Current listed position (NDBC station table, single present-day "
            f"value, not a per-year history): {station_positions.get(station) or 'unavailable'}"
        )
        lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Download and aggregate NDBC buoy data.")
    parser.add_argument("--region", default="utah")
    parser.add_argument("--start-year", type=int, default=1980)
    parser.add_argument("--end-year", type=int, default=dt.date.today().year)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    config = load_config(args.region)
    raw_dir = config["paths"]["raw"]
    processed_dir = config["paths"]["processed"]
    outputs_dir = config["paths"]["outputs"]

    station_ids = [config["buoys"]["primary"], *config["buoys"]["secondary"]]

    meta_session = requests.Session()
    meta_session.headers.update({"User-Agent": USER_AGENT})

    station_daily: dict[str, pd.DataFrame] = {}
    station_positions: dict[str, str | None] = {}
    for station in station_ids:
        logger.info("=== Station %s ===", station)
        paths = download_station_history(station, args.start_year, args.end_year, raw_dir)
        raw_obs = _load_all_years(paths)
        station_daily[station] = aggregate_daily(raw_obs, station)
        station_positions[station] = fetch_current_station_position(station, meta_session)

    buoy_daily = (
        pd.concat(station_daily.values(), ignore_index=True)
        if station_daily
        else pd.DataFrame(columns=DAILY_COLUMNS)
    )
    report = build_report(station_daily, station_positions)

    if args.dry_run:
        print(f"--- DRY RUN: would write data/processed/buoy_daily.parquet with {len(buoy_daily)} rows ---")
        print(report)
        return

    processed_dir.mkdir(parents=True, exist_ok=True)
    out_parquet = processed_dir / "buoy_daily.parquet"
    buoy_daily.to_parquet(out_parquet, index=False)
    logger.info("Wrote %s (%d rows)", out_parquet, len(buoy_daily))

    outputs_dir.mkdir(parents=True, exist_ok=True)
    report_path = outputs_dir / "buoy_ingest_report.txt"
    report_path.write_text(report)
    logger.info("Wrote %s", report_path)


if __name__ == "__main__":
    main()
