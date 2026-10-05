"""Download, parse, and clean NRCS SNOTEL daily snow water equivalent data.

Produces `data/processed/snow_daily.parquet` — the target side of the
project. Source is the NRCS AWDB REST API (DECISIONS.md Q4); no API key
required. SNOTEL records on a Pacific Standard Time day, interval-ending
(the value is dated to the day that just ended, DECISIONS.md Q12) — this
module never shifts dates to align with the buoy's UTC day.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import logging
import time
from pathlib import Path

import numpy as np
import pandas as pd
import requests

from powderbuoy.config import load_config, repo_relative

logger = logging.getLogger(__name__)

AWDB_BASE_URL = "https://wcc.sc.egov.usda.gov/awdbRestApi"
AWDB_DATA_URL = f"{AWDB_BASE_URL}/services/v1/data"
AWDB_STATIONS_URL = f"{AWDB_BASE_URL}/services/v1/stations"
USER_AGENT = "powderbuoy-research-script/0.1"

ELEMENTS = "WTEQ,PREC,TAVG"
DURATION = "DAILY"
# Interval-ending: the daily value is dated to the day that just ended.
# Confirmed as the API's own default, and matches SPEC 3.2 / DECISIONS Q12.
PERIOD_REF = "END"

DEFAULT_REQUEST_TIMEOUT_SECONDS = 30
DEFAULT_MAX_RETRIES = 3

# Declared sanity bound for a single-day SWE change (inches), either
# direction. A large storm can add a few inches of SWE in a day; a jump far
# beyond that, or an equally large drop, is more likely a sensor reset or
# unit error than real snowfall or melt. Flagged, never dropped.
MAX_PLAUSIBLE_DAILY_SWE_JUMP_IN = 8.0

COVERAGE_GOOD_THRESHOLD = 0.90
COVERAGE_THIN_THRESHOLD = 0.50

DAILY_COLUMNS = [
    "date", "station",
    "swe_in", "swe_gain_in",
    "precip_accum_in", "temp_mean_f",
    "is_valid",
]


def fetch_station_swe(
    station_triplet: str, start_date: str, end_date: str,
    raw_dir: Path, session: requests.Session,
) -> Path | None:
    """Fetch daily WTEQ (and PREC/TAVG where available) for one station over a date range.

    Caches the raw response to raw_dir. Idempotent — skips if already
    present. Never raises. Returns the path, or None if the station returned
    no data or the request failed after retries. Logs the reason.
    """
    try:
        raw_dir.mkdir(parents=True, exist_ok=True)
        safe_name = station_triplet.replace(":", "_")
        out_path = raw_dir / f"snotel_{safe_name}.json"
        if out_path.exists():
            logger.info("%s: already downloaded, skipping", station_triplet)
            return out_path

        params = {
            "stationTriplets": station_triplet,
            "elements": ELEMENTS,
            "duration": DURATION,
            "beginDate": start_date,
            "endDate": end_date,
            "periodRef": PERIOD_REF,
            "returnFlags": "true",
        }
        for attempt in range(1, DEFAULT_MAX_RETRIES + 1):
            try:
                resp = session.get(
                    AWDB_DATA_URL, params=params, timeout=DEFAULT_REQUEST_TIMEOUT_SECONDS
                )
            except requests.RequestException as exc:
                logger.warning(
                    "%s: request error on attempt %d/%d: %s",
                    station_triplet, attempt, DEFAULT_MAX_RETRIES, exc,
                )
                continue
            if resp.status_code != 200:
                logger.warning(
                    "%s: HTTP %d on attempt %d/%d",
                    station_triplet, resp.status_code, attempt, DEFAULT_MAX_RETRIES,
                )
                continue
            payload = resp.json()
            if not payload or not payload[0].get("data"):
                logger.info("%s: API returned no data for this range", station_triplet)
                return None
            out_path.write_text(json.dumps(payload))
            return out_path

        logger.warning("%s: giving up after %d attempts", station_triplet, DEFAULT_MAX_RETRIES)
        return None
    except Exception:
        logger.exception("%s: unexpected error downloading", station_triplet)
        return None


def parse_station_swe(path: Path, station_triplet: str) -> pd.DataFrame:
    """Parse a cached SNOTEL response into a tidy frame.

    Returns columns: date, station, swe_in, precip_accum_in, temp_mean_f
    (where available). Missing values become NaN, not sentinels or zeros.
    Not yet reindexed onto a complete calendar — see build_daily_table.
    """
    empty = pd.DataFrame(columns=["date", "station", "swe_in", "precip_accum_in", "temp_mean_f"])
    payload = json.loads(path.read_text())
    if not payload or not payload[0].get("data"):
        return empty

    element_frames = {}
    for element in payload[0]["data"]:
        code = element["stationElement"]["elementCode"]
        values = element.get("values", [])
        if not values:
            continue
        frame = pd.DataFrame(values)[["date", "value"]].rename(columns={"value": code})
        frame[code] = pd.to_numeric(frame[code], errors="coerce")
        element_frames[code] = frame

    if not element_frames:
        return empty

    merged = None
    for frame in element_frames.values():
        merged = frame if merged is None else merged.merge(frame, on="date", how="outer")

    merged["date"] = pd.to_datetime(merged["date"]).dt.date
    merged = merged.sort_values("date").reset_index(drop=True)

    out = pd.DataFrame({"date": merged["date"]})
    out["station"] = station_triplet
    out["swe_in"] = merged["WTEQ"] if "WTEQ" in merged.columns else np.nan
    out["precip_accum_in"] = merged["PREC"] if "PREC" in merged.columns else np.nan
    out["temp_mean_f"] = merged["TAVG"] if "TAVG" in merged.columns else np.nan
    return out


def compute_is_valid(swe_in: pd.Series, swe_gain_in: pd.Series) -> pd.Series:
    """Quality flag for each day. NA where there is no swe_in to assess.

    Flags False for negative SWE or a single-day jump beyond
    MAX_PLAUSIBLE_DAILY_SWE_JUMP_IN. Rows are never dropped for this.
    """
    valid = pd.Series(pd.NA, index=swe_in.index, dtype="boolean")
    has_obs = swe_in.notna()
    negative = (swe_in < 0).fillna(False)
    big_jump = (swe_gain_in.abs() > MAX_PLAUSIBLE_DAILY_SWE_JUMP_IN).fillna(False)
    implausible = negative | big_jump
    valid[has_obs] = ~implausible[has_obs]
    return valid


def build_daily_table(df: pd.DataFrame, station: str) -> pd.DataFrame:
    """Reindex one station's parsed frame onto a complete daily calendar.

    Gap days appear as rows with null values (SPEC rule 2.5), not absent
    rows, spanning the station's first to last observed date. swe_gain_in is
    the day-over-day difference; it is null wherever the previous calendar
    day's swe_in is null, so a change is never smeared across a gap.
    """
    if df.empty:
        return pd.DataFrame(columns=DAILY_COLUMNS)

    work = df.sort_values("date").copy()
    work["date"] = pd.to_datetime(work["date"])
    work = work.set_index("date")

    full_index = pd.date_range(work.index.min(), work.index.max(), freq="D", name="date")
    work = work.reindex(full_index)

    swe_gain = work["swe_in"].diff()
    is_valid = compute_is_valid(work["swe_in"], swe_gain)

    daily = pd.DataFrame({
        "date": full_index,
        "station": station,
        "swe_in": work["swe_in"].to_numpy(),
        "swe_gain_in": swe_gain.to_numpy(),
        "precip_accum_in": work["precip_accum_in"].to_numpy(),
        "temp_mean_f": work["temp_mean_f"].to_numpy(),
        "is_valid": is_valid.to_numpy(),
    })
    daily["date"] = daily["date"].dt.date
    return daily[DAILY_COLUMNS]


def fetch_station_metadata(station_triplet: str, session: requests.Session) -> dict | None:
    """Look up a station's install date and elevation from the AWDB metadata endpoint.

    Never raises. Returns None on failure or if the station is not found.
    """
    try:
        resp = session.get(
            AWDB_STATIONS_URL,
            params={"stationTriplets": station_triplet},
            timeout=DEFAULT_REQUEST_TIMEOUT_SECONDS,
        )
        resp.raise_for_status()
        payload = resp.json()
        return payload[0] if payload else None
    except requests.RequestException as exc:
        logger.warning("Could not fetch metadata for %s: %s", station_triplet, exc)
        return None
    except Exception:
        logger.exception("Unexpected error fetching metadata for %s", station_triplet)
        return None


def _season_start_year(date: dt.date, start_md: str, end_md: str) -> int | None:
    """The winter's start year (SPEC rule 2.1) for a date, or None if outside season."""
    start_month, start_day = (int(x) for x in start_md.split("-"))
    end_month, end_day = (int(x) for x in end_md.split("-"))
    key = (date.month, date.day)
    if key >= (start_month, start_day):
        return date.year
    if key <= (end_month, end_day):
        return date.year - 1
    return None


def _winter_window(winter_year: int, start_md: str, end_md: str) -> tuple[dt.date, dt.date]:
    start_month, start_day = (int(x) for x in start_md.split("-"))
    end_month, end_day = (int(x) for x in end_md.split("-"))
    start = dt.date(winter_year, start_month, start_day)
    end = dt.date(winter_year + 1, end_month, end_day)
    return start, end


def coverage_flag(pct_present: float) -> str:
    if pct_present >= COVERAGE_GOOD_THRESHOLD:
        return "good"
    if pct_present >= COVERAGE_THIN_THRESHOLD:
        return "thin"
    return "missing"


def _all_station_flag(station_flags: list[str]) -> str:
    """good if >=2 stations good; else thin if >=2 stations thin-or-better; else missing."""
    n_good = sum(f == "good" for f in station_flags)
    n_at_least_thin = sum(f in ("good", "thin") for f in station_flags)
    if n_good >= 2:
        return "good"
    if n_at_least_thin >= 2:
        return "thin"
    return "missing"


def compute_winter_coverage(
    snow_daily: pd.DataFrame, station_ids: list[str], start_md: str, end_md: str
) -> pd.DataFrame:
    """One row per winter, one coverage-percent/flag column pair per station.

    A winter's denominator is the full Nov-to-Apr calendar window regardless
    of whether the station has any rows there — a station with no rows in a
    winter (never installed yet, or past its last observation) scores 0%
    for that winter, which is 'missing' by the same threshold as a thin
    interior-gap winter. No separate before-install branch is needed.
    """
    if snow_daily.empty:
        min_year, max_year = dt.date.today().year, dt.date.today().year
    else:
        all_dates = pd.to_datetime(snow_daily["date"])
        winters = [
            y for y in (
                _season_start_year(d.date(), start_md, end_md) for d in all_dates
            ) if y is not None
        ]
        if not winters:
            min_year, max_year = dt.date.today().year, dt.date.today().year
        else:
            min_year, max_year = min(winters), max(winters)

    station_series = {}
    for station in station_ids:
        sub = snow_daily[snow_daily["station"] == station]
        if sub.empty:
            station_series[station] = pd.Series(dtype=float)
        else:
            s = sub.set_index(pd.to_datetime(sub["date"]))["swe_in"]
            station_series[station] = s

    records = []
    for winter_year in range(min_year, max_year + 1):
        start, end = _winter_window(winter_year, start_md, end_md)
        window_dates = pd.date_range(start, end, freq="D")
        total_days = len(window_dates)

        row = {"winter": winter_year}
        flags = []
        for station in station_ids:
            series = station_series[station]
            present = series.reindex(window_dates).notna().sum() if len(series) else 0
            pct = present / total_days if total_days else 0.0
            flag = coverage_flag(pct)
            flags.append(flag)
            row[f"{station}_pct"] = pct
            row[f"{station}_flag"] = flag
        row["all_station_flag"] = _all_station_flag(flags)
        records.append(row)

    return pd.DataFrame.from_records(records)


def build_coverage_report(
    snow_daily: pd.DataFrame,
    station_meta: dict[str, dict | None],
    stations_cfg: list[dict],
    start_md: str,
    end_md: str,
) -> str:
    lines = ["SNOTEL snow coverage report", "=" * 40, ""]

    lines.append("Part 6a — Per-station summary")
    lines.append("-" * 40)
    station_ids = [s["id"] for s in stations_cfg]
    for st in stations_cfg:
        station = st["id"]
        name = st["name"]
        meta = station_meta.get(station) or {}
        install_date = meta.get("beginDate", "unknown")
        sub = snow_daily[snow_daily["station"] == station]
        lines.append(f"{name} ({station})")
        if sub.empty:
            lines.append("  No data retrieved.")
            lines.append("")
            continue
        total_days = len(sub)
        null_days = int(sub["swe_in"].isna().sum())
        pct_null = 100.0 * null_days / total_days if total_days else float("nan")
        invalid_days = int((sub["is_valid"] == False).sum())  # noqa: E712 (nullable boolean)
        lines.append(f"  Install date: {install_date}")
        lines.append(f"  First observed date: {sub['date'].min()}")
        lines.append(f"  Last observed date: {sub['date'].max()}")
        lines.append(f"  Total days: {total_days}")
        lines.append(f"  Days with null swe_in: {null_days} ({pct_null:.2f}%)")
        lines.append(f"  Days flagged is_valid = false: {invalid_days}")
        lines.append("")

    lines.append("")
    lines.append("Part 6b — Per-winter coverage matrix")
    lines.append("-" * 40)
    lines.append(
        f"Thresholds: good >= {COVERAGE_GOOD_THRESHOLD:.0%} of winter days non-null; "
        f"thin >= {COVERAGE_THIN_THRESHOLD:.0%}; missing below {COVERAGE_THIN_THRESHOLD:.0%} "
        "or station did not exist yet."
    )
    lines.append(
        "all_station column: 'good' if at least two stations are 'good'; else 'thin' if "
        "at least two stations are 'thin' or better; else 'missing'."
    )
    lines.append("")

    coverage = compute_winter_coverage(snow_daily, station_ids, start_md, end_md)
    name_by_id = {s["id"]: s["name"] for s in stations_cfg}
    header = ["winter"] + [name_by_id[s] for s in station_ids] + ["all_station"]
    lines.append("  ".join(f"{h:<16}" for h in header))
    for _, row in coverage.iterrows():
        cells = [str(int(row["winter"]))]
        for station in station_ids:
            cells.append(f"{row[f'{station}_flag']} ({row[f'{station}_pct']:.0%})")
        cells.append(row["all_station_flag"])
        lines.append("  ".join(f"{c:<16}" for c in cells))

    return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Download and clean NRCS SNOTEL SWE data.")
    parser.add_argument("--region", default="utah")
    parser.add_argument("--end-date", default=dt.date.today().isoformat())
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    config = load_config(args.region)
    raw_dir = config["paths"]["raw"]
    processed_dir = config["paths"]["processed"]
    outputs_dir = config["paths"]["outputs"]
    request_delay = config["defaults"]["request_delay_seconds"]

    stations_cfg = config["snow_stations"]

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    station_daily: dict[str, pd.DataFrame] = {}
    station_meta: dict[str, dict | None] = {}
    for st in stations_cfg:
        triplet = st["id"]
        logger.info("=== Station %s (%s) ===", triplet, st.get("name"))
        meta = fetch_station_metadata(triplet, session)
        station_meta[triplet] = meta
        begin_date_raw = (meta or {}).get("beginDate")
        start_date = begin_date_raw.split(" ")[0] if begin_date_raw else "1970-01-01"

        path = fetch_station_swe(triplet, start_date, args.end_date, raw_dir, session)
        if path is None:
            station_daily[triplet] = pd.DataFrame(columns=DAILY_COLUMNS)
        else:
            parsed = parse_station_swe(path, triplet)
            station_daily[triplet] = build_daily_table(parsed, triplet)
        time.sleep(request_delay)

    snow_daily = (
        pd.concat(station_daily.values(), ignore_index=True)
        if station_daily
        else pd.DataFrame(columns=DAILY_COLUMNS)
    )

    season_start_md = config["season"]["start_month_day"]
    season_end_md = config["season"]["end_month_day"]
    report = build_coverage_report(snow_daily, station_meta, stations_cfg, season_start_md, season_end_md)

    if args.dry_run:
        print(f"--- DRY RUN: would write data/processed/snow_daily.parquet with {len(snow_daily)} rows ---")
        print(report)
        return

    processed_dir.mkdir(parents=True, exist_ok=True)
    out_parquet = processed_dir / "snow_daily.parquet"
    snow_daily.to_parquet(out_parquet, index=False)
    logger.info("Wrote %s (%d rows)", repo_relative(out_parquet), len(snow_daily))

    outputs_dir.mkdir(parents=True, exist_ok=True)
    report_path = outputs_dir / "snow_coverage_report.txt"
    report_path.write_text(report)
    logger.info("Wrote %s", repo_relative(report_path))


if __name__ == "__main__":
    main()
