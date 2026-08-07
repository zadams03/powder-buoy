"""Download, parse, and join the known-climate control signals (SPEC 3.3).

Produces `data/processed/climate_daily.parquet` — MJO (daily), ENSO/ONI and
PDO (monthly, attached with a one-month availability lag, DECISIONS.md Q10)
— and, as the final data-engineering step, `data/processed/analysis_daily.parquet`,
a dumb full outer join of buoy, snow, and climate on `date`. No analytical
choice is made here: snow stations stay separate, no storm/target column is
created, and no gap is filled (SPEC rule 2.5).
"""

from __future__ import annotations

import argparse
import datetime as dt
import io
import logging
import time
from pathlib import Path

import numpy as np
import pandas as pd
import requests

from powderbuoy.config import load_config

logger = logging.getLogger(__name__)

# Confirmed live in Session 0C (2026-08-07) — see DECISIONS.md Q10.
MJO_URL = "http://www.bom.gov.au/climate/mjo/graphics/rmm.74toRealtime.txt"
ENSO_URL = "https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt"
PDO_URL = "https://www.ncei.noaa.gov/pub/data/cmb/ersst/v5/index/ersst.v5.pdo.dat"

MJO_RAW_FILENAME = "mjo_rmm.txt"
ENSO_RAW_FILENAME = "enso_oni.txt"
PDO_RAW_FILENAME = "pdo.dat"

USER_AGENT = "powderbuoy-research-script/0.1"

DEFAULT_REQUEST_TIMEOUT_SECONDS = 30
DEFAULT_MAX_RETRIES = 3

# The BoM RMM file itself declares "Missing Value= 1.E36 or 999" in its header.
MJO_SENTINEL_MAGNITUDE = 1e30  # anything past this is the 1.E36 sentinel
MJO_SENTINEL_EXACT = 999

# ONI's ANOM column has shown no sentinel in the live record checked (SST
# anomalies run roughly -3 to +3), but CPC's convention elsewhere is -99.9 for
# an unpublished value. Guarded defensively, same policy as the buoy loader.
ENSO_SENTINEL_ABS_THRESHOLD = 90.0

# Confirmed live in Session 0C: NCEI's PDO file pads not-yet-occurred months
# with 99.99 (e.g. trailing months of the current year).
PDO_SENTINEL = 99.99

# BoM switched its RMM calculation method at the end of 2013 (DECISIONS.md
# Q23) - flagged, never smoothed over. Computed from date, not trusted from
# the file's own per-row method label, per the session prompt.
MJO_SEAM_DATE = dt.date(2013, 12, 31)

# CPC's ONI table labels each running 3-month season by the year of its
# middle month - e.g. "DJF 1950" is Dec 1949 + Jan 1950 + Feb 1950, filed
# under the Jan-1950 month. This is the standard NOAA convention, not a guess.
SEASON_TO_MONTH = {
    "DJF": 1, "JFM": 2, "FMA": 3, "MAM": 4, "AMJ": 5, "MJJ": 6,
    "JJA": 7, "JAS": 8, "ASO": 9, "SON": 10, "OND": 11, "NDJ": 12,
}

MONTH_NAME_TO_NUM = {
    "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
    "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12,
}

CLIMATE_DAILY_COLUMNS = [
    "date", "rmm1", "rmm2", "mjo_phase", "mjo_amplitude", "mjo_method",
    "nino34", "nino34_is_ffilled", "pdo", "pdo_is_ffilled",
]

BUOY_VALUE_COLUMNS = [
    "wvht_mean", "wvht_max", "wvht_min",
    "dpd_mean", "dpd_max", "apd_mean", "mwd_mean",
    "wspd_mean", "wspd_max", "pres_mean", "pres_min", "n_obs",
]

SNOW_VALUE_COLUMNS = [
    "swe_in", "swe_gain_in", "precip_accum_in", "temp_mean_f", "is_valid",
]


def _fetch_text(
    url: str, out_path: Path, session: requests.Session, label: str
) -> Path | None:
    """Shared fetch-and-cache body for the three text sources. Never raises."""
    try:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        if out_path.exists():
            logger.info("%s: already downloaded, skipping", label)
            return out_path

        for attempt in range(1, DEFAULT_MAX_RETRIES + 1):
            try:
                resp = session.get(url, timeout=DEFAULT_REQUEST_TIMEOUT_SECONDS)
            except requests.RequestException as exc:
                logger.warning(
                    "%s: request error on attempt %d/%d: %s",
                    label, attempt, DEFAULT_MAX_RETRIES, exc,
                )
                continue
            if resp.status_code != 200:
                logger.warning(
                    "%s: HTTP %d on attempt %d/%d",
                    label, resp.status_code, attempt, DEFAULT_MAX_RETRIES,
                )
                continue
            out_path.write_text(resp.text)
            return out_path

        logger.warning("%s: giving up after %d attempts", label, DEFAULT_MAX_RETRIES)
        return None
    except Exception:
        logger.exception("%s: unexpected error downloading", label)
        return None


def fetch_mjo(raw_dir: Path, session: requests.Session) -> Path | None:
    """Fetch the BoM RMM index file. Idempotent. Never raises."""
    return _fetch_text(MJO_URL, raw_dir / MJO_RAW_FILENAME, session, "MJO")


def fetch_enso(raw_dir: Path, session: requests.Session) -> Path | None:
    """Fetch the NOAA CPC ONI ascii table. Idempotent. Never raises."""
    return _fetch_text(ENSO_URL, raw_dir / ENSO_RAW_FILENAME, session, "ENSO/ONI")


def fetch_pdo(raw_dir: Path, session: requests.Session) -> Path | None:
    """Fetch the NOAA NCEI ERSST PDO index. Idempotent. Never raises."""
    return _fetch_text(PDO_URL, raw_dir / PDO_RAW_FILENAME, session, "PDO")


def _mjo_sentinel_to_nan(series: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce")
    is_missing = (numeric.abs() > MJO_SENTINEL_MAGNITUDE) | (numeric == MJO_SENTINEL_EXACT)
    return numeric.where(~is_missing, np.nan)


def parse_mjo(path: Path) -> pd.DataFrame:
    """Parse RMM. Returns: date, rmm1, rmm2, mjo_phase, mjo_amplitude, mjo_method.

    Missing values (BoM uses a sentinel such as 1e36 / 999) become NaN, not
    data. mjo_amplitude is recomputed as sqrt(rmm1^2 + rmm2^2), not trusted
    from the file. mjo_method is 'WH2004' for dates <= 2013-12-31, else
    'modified2014' - computed from the date, not from the file's own per-row
    method label (see DECISIONS.md Q23).
    """
    empty = pd.DataFrame(columns=["date", "rmm1", "rmm2", "mjo_phase", "mjo_amplitude", "mjo_method"])
    lines = path.read_text().splitlines(keepends=True)
    # Line 1 is a free-text description, line 2 names the columns - both
    # observed to start without a data row, so both are skipped unconditionally.
    if len(lines) < 3:
        return empty

    data_text = "".join(lines[2:]).strip()
    if not data_text:
        return empty

    raw = pd.read_csv(
        io.StringIO(data_text),
        sep=r"\s+",
        header=None,
        names=["year", "month", "day", "rmm1", "rmm2", "phase", "amplitude_raw", "method_raw"],
        engine="python",
    )

    rmm1 = _mjo_sentinel_to_nan(raw["rmm1"])
    rmm2 = _mjo_sentinel_to_nan(raw["rmm2"])
    phase = _mjo_sentinel_to_nan(raw["phase"])

    date = pd.to_datetime({
        "year": raw["year"].astype(int),
        "month": raw["month"].astype(int),
        "day": raw["day"].astype(int),
    })
    seam = pd.Timestamp(MJO_SEAM_DATE)

    out = pd.DataFrame({
        "date": date.dt.date,
        "rmm1": rmm1,
        "rmm2": rmm2,
        "mjo_phase": phase.astype("Int64"),
        "mjo_amplitude": np.sqrt(rmm1 ** 2 + rmm2 ** 2),
        "mjo_method": np.where(date <= seam, "WH2004", "modified2014"),
    })
    return out


def parse_enso(path: Path) -> pd.DataFrame:
    """Parse the CPC ONI ascii table. Returns: year, month, nino34. Monthly rows.

    Each row is a 3-month running SST anomaly filed under the year of its
    middle month (SEASON_TO_MONTH) - the ONI itself, used here as the
    Nino 3.4 signal per SPEC 3.3's "ENSO (Nino 3.4 / ONI)".
    """
    empty = pd.DataFrame(columns=["year", "month", "nino34"])
    raw = pd.read_csv(path, sep=r"\s+", engine="python")
    if raw.empty:
        return empty
    raw.columns = [c.strip().lower() for c in raw.columns]

    month = raw["seas"].str.upper().map(SEASON_TO_MONTH)
    anom = pd.to_numeric(raw["anom"], errors="coerce")
    anom = anom.where(anom.abs() <= ENSO_SENTINEL_ABS_THRESHOLD, np.nan)

    out = pd.DataFrame({
        "year": pd.to_numeric(raw["yr"], errors="coerce").astype("Int64"),
        "month": month.astype("Int64"),
        "nino34": anom,
    })
    return out.dropna(subset=["year", "month"])


def parse_pdo(path: Path) -> pd.DataFrame:
    """Parse the NCEI ERSST PDO index. Returns: year, month, pdo. Monthly rows."""
    empty = pd.DataFrame(columns=["year", "month", "pdo"])
    # Line 1 is a free-text title ("ERSST PDO Index:"); line 2 is the real header.
    raw = pd.read_csv(path, sep=r"\s+", skiprows=1, engine="python")
    if raw.empty:
        return empty
    raw = raw.rename(columns={raw.columns[0]: "year"})

    long = raw.melt(id_vars="year", var_name="month_name", value_name="pdo")
    long["month"] = long["month_name"].map(MONTH_NAME_TO_NUM)
    long = long.dropna(subset=["month"])

    pdo = pd.to_numeric(long["pdo"], errors="coerce")
    is_sentinel = np.isclose(pdo, PDO_SENTINEL, atol=1e-6) | (pdo.abs() > ENSO_SENTINEL_ABS_THRESHOLD)
    pdo = pdo.where(~is_sentinel, np.nan)

    out = pd.DataFrame({
        "year": pd.to_numeric(long["year"], errors="coerce").astype("Int64"),
        "month": long["month"].astype("Int64"),
        "pdo": pdo,
    })
    return out.sort_values(["year", "month"]).reset_index(drop=True)


def _lag_monthly_to_daily(daily_index: pd.DatetimeIndex, monthly_df: pd.DataFrame, value_col: str) -> pd.Series:
    """One daily value per date, using a one-month availability lag (Q10).

    A month's value becomes "known" on the first day of the following month
    and is held flat (never interpolated) until superseded. A date whose own
    month, or an earlier month with no antecedent, has no known value yet
    reads NaN - never a value computed from a month that hadn't ended.
    """
    if monthly_df.empty:
        return pd.Series(np.nan, index=daily_index)

    m = monthly_df.dropna(subset=["year", "month"]).copy()
    m["key"] = m["year"].astype(int) * 12 + m["month"].astype(int)
    m = m.drop_duplicates(subset="key", keep="last").set_index("key")[value_col].sort_index()
    if m.empty:
        return pd.Series(np.nan, index=daily_index)

    full_key_range = pd.RangeIndex(int(m.index.min()), int(m.index.max()) + 1)
    monthly = m.reindex(full_key_range)

    # Re-label each month's value onto the following month's key - that is
    # the first key at which it is actually known.
    shifted = monthly.copy()
    shifted.index = shifted.index + 1

    daily_keys = daily_index.year * 12 + daily_index.month
    end_key = max(int(daily_keys.max()) if len(daily_keys) else shifted.index.max(), shifted.index.max())
    shifted = shifted.reindex(pd.RangeIndex(shifted.index.min(), end_key + 1)).ffill()

    values = shifted.reindex(daily_keys)
    return pd.Series(values.to_numpy(), index=daily_index)


def build_climate_daily(mjo_df: pd.DataFrame, enso_monthly: pd.DataFrame, pdo_monthly: pd.DataFrame) -> pd.DataFrame:
    """Assemble climate_daily (SPEC 5.3): daily MJO plus monthly ENSO/PDO,
    the latter attached with the one-month availability lag from
    _lag_monthly_to_daily. The daily calendar spans MJO's own date range
    (reindexed onto every day, gap days null, SPEC rule 2.5) since MJO is
    the study's only genuinely daily climate source.
    """
    if mjo_df.empty:
        return pd.DataFrame(columns=CLIMATE_DAILY_COLUMNS)

    work = mjo_df.sort_values("date").copy()
    work["date"] = pd.to_datetime(work["date"])
    work = work.set_index("date")

    full_index = pd.date_range(work.index.min(), work.index.max(), freq="D", name="date")
    work = work.reindex(full_index)

    seam = pd.Timestamp(MJO_SEAM_DATE)
    mjo_method = np.where(full_index <= seam, "WH2004", "modified2014")

    daily = pd.DataFrame(index=full_index)
    daily["rmm1"] = work["rmm1"]
    daily["rmm2"] = work["rmm2"]
    daily["mjo_phase"] = work["mjo_phase"]
    daily["mjo_amplitude"] = work["mjo_amplitude"]
    daily["mjo_method"] = mjo_method
    daily["nino34"] = _lag_monthly_to_daily(full_index, enso_monthly, "nino34")
    daily["nino34_is_ffilled"] = True
    daily["pdo"] = _lag_monthly_to_daily(full_index, pdo_monthly, "pdo")
    daily["pdo_is_ffilled"] = True

    daily = daily.reset_index().rename(columns={"index": "date"})
    daily["date"] = pd.to_datetime(daily["date"]).dt.date
    return daily[CLIMATE_DAILY_COLUMNS]


def _slugify_station_name(name: str) -> str:
    return name.strip().lower().replace(" ", "_").replace("-", "_")


def build_analysis_daily(
    buoy_daily: pd.DataFrame,
    snow_daily: pd.DataFrame,
    climate_daily: pd.DataFrame,
    snow_stations_cfg: list[dict],
) -> pd.DataFrame:
    """The dumb wide join (SPEC 5.4) that Phase 5 reads. One row per date.

    Full outer join on `date` - every date any source has, nulls elsewhere.
    Column naming is prefix-by-source: `buoy_{station}_{col}` (e.g.
    `buoy_51001_wvht_mean`), `snow_{station_slug}_{col}` (e.g.
    `snow_snowbird_swe_gain_in`, station name slugified, spaces/hyphens to
    underscores), and climate columns unprefixed (`mjo_phase`, `nino34`, ...)
    since their names already say what they are. No station is combined, no
    target column is created, and no gap is filled.

    `buoy_daily.date` is a native UTC calendar day; `snow_daily.date` is a
    native PST calendar day (DECISIONS.md Q12). They are joined on the
    calendar-date label as-is - the ~8-hour offset between the two native
    timezones is a conscious, recorded choice, not an accident, and is
    immaterial at the 1-2 week lag this study operates on.
    """
    wide_buoy = None
    for station in sorted(buoy_daily["station"].unique()):
        sub = buoy_daily[buoy_daily["station"] == station].set_index("date")[BUOY_VALUE_COLUMNS]
        sub = sub.add_prefix(f"buoy_{station}_")
        wide_buoy = sub if wide_buoy is None else wide_buoy.join(sub, how="outer")

    name_by_id = {s["id"]: s["name"] for s in snow_stations_cfg}
    wide_snow = None
    for station in sorted(snow_daily["station"].unique()):
        slug = _slugify_station_name(name_by_id.get(station, station))
        sub = snow_daily[snow_daily["station"] == station].set_index("date")[SNOW_VALUE_COLUMNS]
        sub = sub.add_prefix(f"snow_{slug}_")
        wide_snow = sub if wide_snow is None else wide_snow.join(sub, how="outer")

    climate_indexed = climate_daily.set_index("date")

    frames = [f for f in (wide_buoy, wide_snow, climate_indexed) if f is not None]
    wide = frames[0]
    for frame in frames[1:]:
        wide = wide.join(frame, how="outer")

    wide = wide.sort_index()
    wide.index.name = "date"
    return wide.reset_index()


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Download climate indices and build analysis_daily.")
    parser.add_argument("--region", default="utah")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    config = load_config(args.region)
    raw_dir = config["paths"]["raw"]
    processed_dir = config["paths"]["processed"]
    request_delay = config["defaults"]["request_delay_seconds"]

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    mjo_path = fetch_mjo(raw_dir, session)
    mjo_df = parse_mjo(mjo_path) if mjo_path else pd.DataFrame(
        columns=["date", "rmm1", "rmm2", "mjo_phase", "mjo_amplitude", "mjo_method"]
    )
    time.sleep(request_delay)

    enso_path = fetch_enso(raw_dir, session)
    enso_df = parse_enso(enso_path) if enso_path else pd.DataFrame(columns=["year", "month", "nino34"])
    time.sleep(request_delay)

    pdo_path = fetch_pdo(raw_dir, session)
    pdo_df = parse_pdo(pdo_path) if pdo_path else pd.DataFrame(columns=["year", "month", "pdo"])

    climate_daily = build_climate_daily(mjo_df, enso_df, pdo_df)

    if args.dry_run:
        print(f"--- DRY RUN: would write data/processed/climate_daily.parquet with {len(climate_daily)} rows ---")
        return

    processed_dir.mkdir(parents=True, exist_ok=True)
    climate_out = processed_dir / "climate_daily.parquet"
    climate_daily.to_parquet(climate_out, index=False)
    logger.info("Wrote %s (%d rows)", climate_out, len(climate_daily))

    buoy_path = processed_dir / "buoy_daily.parquet"
    snow_path = processed_dir / "snow_daily.parquet"
    if not buoy_path.exists() or not snow_path.exists():
        logger.warning(
            "buoy_daily.parquet or snow_daily.parquet not found in %s; "
            "skipping analysis_daily build", processed_dir,
        )
        return

    buoy_daily = pd.read_parquet(buoy_path)
    snow_daily = pd.read_parquet(snow_path)
    analysis_daily = build_analysis_daily(buoy_daily, snow_daily, climate_daily, config["snow_stations"])

    analysis_out = processed_dir / "analysis_daily.parquet"
    analysis_daily.to_parquet(analysis_out, index=False)
    logger.info("Wrote %s (%d rows)", analysis_out, len(analysis_daily))


if __name__ == "__main__":
    main()
