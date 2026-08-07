# Session 0A — Repo Scaffold & NDBC Buoy Ingest
**Spec version going in: 0.1 | Version to bump to: 0.2**

---

## READ THIS FIRST

Read `SPEC.md` in full and `STATUS.md` in full before doing anything. Then read this
prompt in full before writing a single line of code. Do not begin implementation until
you have done both.

**Apply all critical rules** (SPEC Section 2). The two that bind this session are 2.4
(raw data is never modified in place) and 2.5 (missing data is never silently filled).

### Why this session exists

Nothing has been built. This session creates the repository, the environment, the
config system, and the first data loader.

The loader downloads NOAA buoy data for stations 51001 and 51101 near Hawaii, parses it
correctly across three different historical file formats, converts sentinel missing
values to nulls, aggregates to daily, and writes a clean Parquet table.

That table is the predictor side of the whole project. Everything downstream reads it.
If it is wrong, every later result is wrong, so validation in this session is
deliberately heavy.

### CRITICAL — scope discipline

- Do NOT write any analysis, correlation, plot of relationships, or model.
- Do NOT ingest SNOTEL snow data. That is Session 0B.
- Do NOT ingest MJO, ENSO, or PDO. That is Session 0C.
- Do NOT hardcode any station ID inside a module. All IDs come from config.
- Do NOT interpolate, forward-fill, or zero-fill any gap in the buoy record.

Implement exactly what is specified — no more, no less. Do NOT commit — prepare all
changes, output the commit message, and leave git add/commit/push to the owner.

---

## Background facts established during planning (do not re-derive)

**Historical archive URL pattern:**
`https://www.ndbc.noaa.gov/data/historical/stdmet/{station}h{year}.txt.gz`

Example: `https://www.ndbc.noaa.gov/data/historical/stdmet/51001h2015.txt.gz`

**Recent rolling 45-day file:**
`https://www.ndbc.noaa.gov/data/realtime2/{station}.txt`

**Three file formats exist across the record.** Detect from the header, do not assume
from the year:

| Era | Date columns | Header lines |
| --- | --- | --- |
| Pre-2000 | `YY MM DD hh` (2-digit year) | 1 |
| 2000–2004 | `YYYY MM DD hh` | 1 |
| 2005 onward | `#YY MM DD hh mm` | 2 (second line is units) |

Parse the header row to determine which columns are present. Do not hardcode column
positions by year.

**Fields we keep:** WVHT, DPD, APD, MWD, WSPD, PRES. Ignore the rest.

**Sentinel missing values — these are NOT data:**

| Field | Missing sentinel |
| --- | --- |
| WVHT, DPD, APD | `99.00` |
| MWD, WDIR | `999` |
| WSPD, GST | `99.0` |
| PRES | `9999.0` |
| ATMP, WTMP, DEWP | `999.0` |

General rule: an all-nines value in a field is missing. Convert to null before any
aggregation. A single unconverted `99.00` in a daily mean will silently ruin that day.

**Some station-years do not exist.** A 404 is normal and expected, not an error.
Log it and continue.

**MWD requires a circular mean.** Averaging 350° and 10° arithmetically gives 180°,
which is the exact opposite direction. Use:

```python
import numpy as np

def circular_mean_deg(degrees):
    """Mean of directions in degrees. Returns None if no valid values."""
    d = np.asarray([x for x in degrees if x is not None and not np.isnan(x)])
    if d.size == 0:
        return None
    rad = np.deg2rad(d)
    mean = np.arctan2(np.sin(rad).mean(), np.cos(rad).mean())
    return float(np.rad2deg(mean) % 360)
```

**Station 51001 record starts around 1981. Station 51101 starts around 2008.**
Treat these as approximate — discover the true first year by probing.

---

## Step 1 — Repository scaffold

Create the structure from SPEC Section 4. Empty packages get an `__init__.py`.

```
powder-buoy/
├── SPEC.md                  (already exists — do not overwrite)
├── STATUS.md                (already exists — do not overwrite)
├── DECISIONS.md             (already exists — do not overwrite)
├── README.md                (create — short, points at SPEC.md)
├── pyproject.toml
├── .gitignore
├── config/
│   ├── settings.yaml
│   └── regions/utah.yaml
├── src/powderbuoy/
│   ├── __init__.py
│   ├── config.py
│   └── ingest/
│       ├── __init__.py
│       └── ndbc.py
├── data/raw/.gitkeep
├── data/processed/.gitkeep
├── docs/
├── notebooks/
├── outputs/figures/.gitkeep
├── outputs/experiments/.gitkeep
└── tests/
    ├── __init__.py
    └── test_ndbc.py
```

`.gitignore` must exclude `data/raw/`, `data/processed/`, `.venv/`, `__pycache__/`,
`*.pyc`, and `.ipynb_checkpoints/`.

`pyproject.toml` — Python 3.11+, uv-managed. Dependencies for this session only:
`pandas`, `pyarrow`, `duckdb`, `requests`, `pyyaml`, `numpy`, `matplotlib`.
Dev dependency: `pytest`. Do not add scikit-learn or lightgbm yet.

---

## Step 2 — Config

`config/settings.yaml`:

```yaml
paths:
  raw: data/raw
  processed: data/processed
  outputs: outputs
defaults:
  seed: 42
  request_delay_seconds: 0.5
  request_timeout_seconds: 30
  max_retries: 3
```

`config/regions/utah.yaml`:

```yaml
region: utah
buoys:
  primary: "51001"
  secondary: ["51101"]
snow_stations: []          # populated in Session 0B
season:
  start_month_day: "11-01"
  end_month_day: "04-30"
```

`src/powderbuoy/config.py` exposes:

```python
def load_config(region: str = "utah") -> dict:
    """Load settings.yaml merged with the named region file.

    Raises ValueError with a clear message if a required key is missing.
    Resolves relative paths against the repo root.
    """
```

The region name is the only thing a caller passes. No station ID may appear anywhere
outside `config/regions/`.

---

## Step 3 — NDBC downloader

In `src/powderbuoy/ingest/ndbc.py`. Pure functions where possible, so they are testable.

```python
def download_station_year(station: str, year: int, raw_dir: Path,
                          session: requests.Session) -> Path | None:
    """Download one station-year archive to raw_dir. Never raises.

    Skips the download if the file already exists (idempotent re-runs).
    Returns the path, or None if the station-year does not exist (404) or the
    download failed after retries. Logs the reason at INFO for 404, WARNING otherwise.
    """


def download_station_history(station: str, start_year: int, end_year: int,
                             raw_dir: Path) -> list[Path]:
    """Download all available years. Applies request_delay_seconds between calls."""
```

Raw files keep their original names and are never modified (SPEC rule 2.4).

Apply the configured delay between requests. This is a public NOAA server.

---

## Step 4 — Parser

```python
SENTINELS = {
    "WVHT": 99.00, "DPD": 99.00, "APD": 99.00,
    "MWD": 999, "WDIR": 999,
    "WSPD": 99.0, "GST": 99.0,
    "PRES": 9999.0,
    "ATMP": 999.0, "WTMP": 999.0, "DEWP": 999.0,
}

KEEP_FIELDS = ["WVHT", "DPD", "APD", "MWD", "WSPD", "PRES"]


def parse_station_year(path: Path) -> pd.DataFrame:
    """Parse one gzipped NDBC standard meteorological file.

    Detects the file era from the header row, not from the year.
    Returns a DataFrame with a UTC 'timestamp' column plus KEEP_FIELDS.
    Sentinel values are converted to NaN.
    Two-digit years are expanded (values >= 70 map to 19xx, else 20xx).
    """
```

Detection logic: read the first line. If it contains `mm` as a standalone column it is
the 2005+ format with a units line to skip. If the year column header is `YY` the years
are two-digit. Build the column list from the header, then select `KEEP_FIELDS` by name.

Sentinel conversion happens immediately after parsing, before anything else touches
the numbers.

---

## Step 5 — Daily aggregation

```python
def aggregate_daily(df: pd.DataFrame, station: str) -> pd.DataFrame:
    """Aggregate sub-daily observations to one row per UTC calendar day."""
```

Output schema, matching SPEC Section 5.1:

| Column | Aggregation |
| --- | --- |
| date | UTC calendar date |
| station | passed in |
| wvht_mean, wvht_max, wvht_min | mean / max / min of valid WVHT |
| dpd_mean, dpd_max | mean / max of valid DPD |
| apd_mean | mean of valid APD |
| mwd_mean | **circular** mean of valid MWD |
| wspd_mean, wspd_max | mean / max of valid WSPD |
| pres_mean, pres_min | mean / min of valid PRES |
| n_obs | count of rows contributing to that day |

Rules:

- Days with no observations must appear as rows with all values null and `n_obs = 0`.
  Reindex onto a complete daily calendar from first to last observed date. A gap must
  be visible as a row, not an absent row.
- Do not fill, interpolate, or carry forward (SPEC rule 2.5).
- `n_obs` counts rows present in the source file for that day, regardless of whether
  individual fields were sentinel.

---

## Step 6 — Build script

`src/powderbuoy/ingest/ndbc.py` gets a `main()` runnable as:

```
python -m powderbuoy.ingest.ndbc --region utah [--start-year 1980] [--end-year 2026] [--dry-run]
```

Behaviour:

1. Load config for the region.
2. For each buoy (primary plus secondary), download all available years.
3. Parse each file, aggregate to daily, concatenate.
4. Write `data/processed/buoy_daily.parquet`.
5. Write `outputs/buoy_ingest_report.txt` containing, per station: first and last date,
   total days, days with `n_obs = 0`, longest continuous gap with its dates, percentage
   of days where `wvht_mean` is null, and the count of distinct reported positions.

`--dry-run` does everything except writing the Parquet file, and prints what it would
write.

**Station position check (SPEC open question Q2):** while parsing, extract the
station's reported latitude and longitude if present in the file header or accompanying
metadata. Log the distinct positions found per year. Do not act on the result — just
record it in the report so the owner can decide.

---

## Step 7 — Tests

`tests/test_ndbc.py`. Small and specific.

1. `circular_mean_deg([350, 10])` returns approximately 0 (or 360), not 180.
2. Sentinel conversion: a frame containing WVHT `99.00` and MWD `999` becomes NaN in
   both, while a legitimate WVHT of `9.90` survives untouched.
3. Two-digit year expansion: `85` maps to 1985, `03` maps to 2003.
4. Gap rows: aggregating a frame with observations on day 1 and day 3 produces three
   rows, with day 2 having `n_obs = 0` and null values.

Use small inline fixtures. Do not hit the network in tests.

---

## Validation

Run all of these and paste the real output. Not a description — the actual numbers.

**1. Tests pass**

```
pytest tests/ -v
```

**2. Dry run completes**

```
python -m powderbuoy.ingest.ndbc --region utah --dry-run
```

**3. Full ingest**

```
python -m powderbuoy.ingest.ndbc --region utah
```

Paste the full contents of `outputs/buoy_ingest_report.txt`.

**4. Sanity checks on the output table**

```python
import duckdb
con = duckdb.connect()
con.sql("""
  SELECT station,
         MIN(date) AS first_date,
         MAX(date) AS last_date,
         COUNT(*) AS n_days,
         SUM(CASE WHEN n_obs = 0 THEN 1 ELSE 0 END) AS empty_days,
         ROUND(AVG(wvht_mean), 3) AS mean_wvht,
         ROUND(MIN(wvht_mean), 3) AS min_wvht,
         ROUND(MAX(wvht_mean), 3) AS max_wvht
  FROM 'data/processed/buoy_daily.parquet'
  GROUP BY station ORDER BY station
""").show()
```

Expected, as a physical plausibility check — flag anything that fails:

- `min_wvht` above 0 and below about 1 metre
- `max_wvht` somewhere between roughly 6 and 14 metres
- `mean_wvht` roughly 2 to 3 metres
- 51001 first date around 1981; 51101 first date around 2008

A `max_wvht` near 99 means sentinel handling is broken. Stop and fix.

**5. No sentinels survived**

```python
con.sql("""
  SELECT COUNT(*) FROM 'data/processed/buoy_daily.parquet'
  WHERE wvht_mean > 50 OR dpd_mean > 50 OR pres_mean > 2000 OR mwd_mean > 361
""").show()
```

Must return 0.

**6. Circular mean is not broken**

```python
con.sql("""
  SELECT ROUND(MIN(mwd_mean),1) AS min_dir, ROUND(MAX(mwd_mean),1) AS max_dir
  FROM 'data/processed/buoy_daily.parquet' WHERE mwd_mean IS NOT NULL
""").show()
```

Must be within 0 to 360.

**7. Cross-check the two buoys agree — DECISION POINT, not a formality**

51001 and 51101 both sit in deep water northwest of Kauai, close enough that where both
report they should track each other closely. This check decides whether the project runs
on 51001's long record. Treat the result as evidence to report, not a box to tick.

Because daily aggregation already removes sub-daily timing differences, same-date
matching is fine here. But also report the correlation on a 3-day rolling mean of
`wvht_mean`, so a one-day offset in coverage cannot masquerade as disagreement.

```python
con.sql("""
  SELECT ROUND(CORR(a.wvht_mean, b.wvht_mean), 4) AS corr_daily,
         COUNT(*) AS overlapping_days,
         ROUND(AVG(a.wvht_mean - b.wvht_mean), 4) AS mean_diff,
         ROUND(STDDEV(a.wvht_mean - b.wvht_mean), 4) AS sd_diff
  FROM 'data/processed/buoy_daily.parquet' a
  JOIN 'data/processed/buoy_daily.parquet' b USING (date)
  WHERE a.station='51001' AND b.station='51101'
    AND a.wvht_mean IS NOT NULL AND b.wvht_mean IS NOT NULL
""").show()
```

Expectation: correlation well above 0.9, mean difference near zero.

**If correlation is high:** record in DECISIONS.md Q1 that 51001 is confirmed as a valid
long-record stand-in, and proceed.

**If correlation is not high:** do not paper over it. Report the numbers, flag that the
long-record assumption (SPEC 6.0) is now in doubt, and stop for an owner decision. This
is the record-length risk described in SPEC Section 6.0 — it is expected to be possible,
and finding it here is the check working, not a failure of the session.

**8. One winter plotted**

Plot `wvht_mean` for station 51001, 1 November 2015 to 30 April 2016. Save to
`outputs/figures/wvht_51001_winter_2015.png`. Confirm it looks like a wave record —
a noisy baseline with sharp spikes — and not a flat line or a saw pattern.

**9. Idempotency**

Re-run the full ingest. Confirm no files are re-downloaded and the output Parquet is
byte-identical or has identical row counts and summary statistics.

---

## Consistency check

Before writing the commit message, re-read `SPEC.md`, `STATUS.md` and `DECISIONS.md`
and report:

- Any two entries that contradict each other
- Any duplicated section heading
- Any findings-log entry out of version order
- Anything this session did that the spec does not describe

**Report only. Do not fix silently.** The owner decides.

---

## File updates

### SPEC.md
- Version bump 0.1 → 0.2.
- Section 3.1: record the true first and last available year discovered for each
  station, and note the actual file-format boundaries encountered.
- No other changes. Section 8 stays empty.

### STATUS.md
- Section 1: mark repo scaffold and NDBC ingest complete.
- Section 2: replace with Session 0B (SNOTEL ingest).
- Section 3: add build log row.
- Section 4: fill in the `buoy_daily` row — rows, date range, gaps, refresh date.
- Section 6: log the consistency check result.

### DECISIONS.md
- Q2 (station repositioning): append what the position check found. If 51001 moved
  materially, leave Open with the evidence recorded. If it did not, mark Resolved.
- Append any new open questions this session surfaced.
- No findings entry — this session produces no findings, only data.

---

## Commit message

Do not commit — prepare changes and output this message only.

```
feat(ingest): repo scaffold and NDBC buoy ingest (0A)

- Repo structure, uv environment, .gitignore, pyproject per SPEC Section 4
- config/settings.yaml and config/regions/utah.yaml; no station ID is
  hardcoded outside config
- src/powderbuoy/config.py: region config loader with validation
- src/powderbuoy/ingest/ndbc.py: downloader, three-era parser, sentinel
  handling, circular-mean wave direction, daily aggregation with gap rows
  preserved as n_obs=0
- Produces data/processed/buoy_daily.parquet for stations 51001 and 51101
- outputs/buoy_ingest_report.txt: coverage, gaps, position history
- tests/test_ndbc.py: circular mean, sentinel conversion, two-digit year
  expansion, gap-row preservation
- No analysis, no snow data, no modelling

SPEC.md: v0.2
```
