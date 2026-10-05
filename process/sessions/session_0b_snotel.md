# Session 0B — SNOTEL Snow Ingest
**Spec version going in: 0.2 | Version to bump to: 0.3**

---

## READ THIS FIRST

Read `SPEC.md` in full, `STATUS.md` in full, and `DECISIONS.md` in full before doing
anything. Then read this prompt in full before writing any code.

**Apply all critical rules** (SPEC Section 2). The ones that bind this session are 2.2
(no baseline, no claim — though no claims are made here), 2.4 (raw data never modified
in place), and 2.5 (missing data never silently filled). Rule 2.5 matters more here than
in 0A: snow gaps directly shrink the usable sample, so every gap must be visible, not
patched.

### Why this session exists

Session 0A built the predictor side (buoy). This session builds the target side (snow).

SNOTEL is the USDA network of automated snow stations. Each weighs the snow sitting on
a pressure pillow. The daily rise in that weight — snow water equivalent gain — is our
"a storm happened" signal (SPEC 3.2).

The output is `data/processed/snow_daily.parquet`, one row per station per day, plus a
per-winter coverage report that shows how complete each station's record is. That
coverage report matters as much as the data: it is the first look at how many winters
are actually usable, which the 2010–2014 buoy gap (Q21) has already made uncertain.

### CRITICAL — scope discipline

- Do NOT ingest climate indices (MJO, ENSO, PDO). That is Session 0C.
- Do NOT join buoy and snow data. Do NOT compute any correlation between them.
- Do NOT do any analysis, lag scan, or modelling.
- Do NOT hardcode any station ID inside a module. All IDs come from config.
- Do NOT fill, interpolate, or zero-fill any gap in the snow record.

Implement exactly what is specified. Do NOT commit — prepare changes, output the commit
message, and stop.

---

## Part 1 — Housekeeping (do this first, it is quick)

These are spec-file corrections the owner has approved, carried over from 0A's
consistency check. Make these edits before the main work.

**H1 — Add `apd_mean` to SPEC Section 5.1.** The `buoy_daily` schema table in SPEC 5.1
does not list `apd_mean`, but `buoy_daily.parquet` was built with it (following the 0A
prompt). Add a row to the SPEC 5.1 table:

```
| apd_mean | float | seconds. Mean of valid APD |
```

Place it after the `dpd_*` rows. Then in DECISIONS.md, mark Q22 Resolved: "Added to
SPEC 5.1 in Session 0B. Spec now matches the built table."

**H2 — Confirm SPEC 3.1 file-era description.** 0A already updated SPEC 3.1 with the
observed four-format reality. No further edit needed. In DECISIONS.md, append to the
Q-tracking note that the owner has accepted the corrected 3.1 text as final. (This is
the consistency-log item 2 from 0A; mark it resolved in STATUS Section 6.)

**H3 — Soften Q1 wording in DECISIONS.md.** Q1's resolution says 51001 gives "the extra
27 years." Replace that phrase with: "a longer record — roughly two usable decades,
though with a five-year gap (2010–2014, see Q21)." The decision itself is unchanged; only
the reasoning is made accurate. Mark the 0A consistency-log item 3 resolved in STATUS.

**H4 — Add a closing note to Q2.** Append to Q2: "Direct check is not possible from the
stdmet archive files, which carry no per-observation coordinates. The 0.98 cross-buoy
correlation makes a disruptive reposition unlikely, so this is not pursued further. If it
ever matters, NDBC publishes a per-station deployment-history page that would answer it.
Left Open, low priority." Keep status Open.

None of H1–H4 change any data or code. They align the spec files with reality.

---

## Part 2 — Establish the NRCS access method (record before coding)

**Do not assume the endpoint. Establish it, test it on one station, then record it in
DECISIONS.md Q4 before building the full loader.**

Background facts established during planning (do not re-derive):

- NRCS runs the AWDB (Air and Water Database). Two access paths exist: a legacy SOAP
  web service, and a newer **REST API**. Prefer the REST API.
- The REST API base is documented at
  `https://wcc.sc.egov.usda.gov/awdbRestApi/swagger-ui.html` — use the Swagger page to
  confirm the exact current path and parameter names. Endpoints have changed before, so
  verify against the live Swagger UI rather than trusting any hardcoded example.
- The network code for SNOTEL stations is `SNTL`. Station triplets have the form
  `{id}:{state}:SNTL`, e.g. a Utah station is `{id}:UT:SNTL`.
- The element code for snow water equivalent is `WTEQ`. For accumulated precipitation it
  is `PREC`. For daily values use the daily duration.
- A reference/metadata table of stations (coordinates, elevation, **installation date**)
  is available at `https://nwcc-apps.sc.egov.usda.gov/ref-data/`. Use installation date
  to inform the coverage report — a station cannot have data before it existed.

**Timezone / day-definition fact (this resolves Q12):** SNOTEL records in Pacific
Standard Time (UTC−8, fixed, no daylight saving). The daily WTEQ value is the
midnight-PST reading, assigned to the day that just ended (interval-ending convention).
Our buoy data is aggregated on UTC calendar days. The two day-definitions differ by 8
hours. At a forecast lead of one to two weeks this offset is immaterial, but it must be
recorded, not silently aligned. **Do not shift either series to "match" the other.** Keep
snow on its native PST-day and buoy on its native UTC-day, and record the convention.

Step 2 output: in DECISIONS.md Q4, record the exact REST base URL, the endpoint path
used for daily data, the parameter names, and one working example request. Mark Q4
Resolved. In Q12, record the timezone convention above and mark it Resolved.

---

## Part 3 — Confirm station IDs (record before coding)

SPEC 3.2 lists candidate Wasatch stations by name only. Look each up against the NRCS
reference table and confirm its triplet ID, installation date, and elevation.

Candidates (SPEC 3.2): Snowbird, Brighton, Mill-D North, Thaynes Canyon, Louis Meadow.

For each, record in DECISIONS.md Q3: name, confirmed triplet ID, install date, elevation,
and whether it was found. If a candidate cannot be found under that name, note it and do
not substitute a guess. If additional well-placed Wasatch SNOTEL stations turn up during
the lookup, list them as candidates in Q3 but do not add them to config without owner
sign-off — note them for a later decision.

Write the confirmed IDs into `config/regions/utah.yaml` under `snow_stations`, each with
`id` and `name`. This is the only place station IDs live (SPEC 4.1).

---

## Part 4 — Build the SNOTEL loader

In `src/powderbuoy/ingest/snotel.py`. Mirror the structure and quality bar of
`ndbc.py`: pure, testable functions; idempotent downloads cached to `data/raw/`; raw
files never modified.

```python
def fetch_station_swe(station_triplet: str, start_date: str, end_date: str,
                      raw_dir: Path, session: requests.Session) -> Path | None:
    """Fetch daily WTEQ (and PREC where available) for one station over a date range.

    Caches the raw response to raw_dir. Idempotent — skips if already present.
    Never raises. Returns the path, or None if the station returned no data or the
    request failed after retries. Logs the reason.
    """


def parse_station_swe(path: Path, station_triplet: str) -> pd.DataFrame:
    """Parse a cached SNOTEL response into a tidy frame.

    Returns columns: date, station, swe_in, precip_accum_in, temp_mean_f (where
    available). Missing values become NaN, not sentinels or zeros.
    """
```

Fetch daily SWE (`WTEQ`) as the core field. Also fetch accumulated precipitation
(`PREC`) and mean air temperature where the API returns them — SPEC 5.2 has columns for
both, and they cost nothing to store now and may matter later. If temperature is awkward
to get in the same call, it is optional this session; SWE and precip are not.

Request each station over its full available range (install date to present). Respect a
polite delay between requests, reusing the `request_delay_seconds` setting from config.

---

## Part 5 — Daily table and SWE gain

Build `data/processed/snow_daily.parquet` per SPEC Section 5.2:

| Column | Notes |
| --- | --- |
| date | PST observation day (record this convention; see Q12) |
| station | triplet ID |
| swe_in | snow water equivalent, inches |
| swe_gain_in | swe_in minus previous day's swe_in. Null if previous day missing |
| precip_accum_in | where available |
| temp_mean_f | where available |
| is_valid | passed quality checks (see below) |

Rules:

- Reindex each station onto a complete daily calendar from its first to last observed
  date, so gaps appear as rows with null values, not as absent rows (mirrors the buoy
  treatment, SPEC 5.2 and rule 2.5).
- `swe_gain_in` is the day-over-day difference. If the previous day is missing, the gain
  is null — do not compute a gain across a gap, as that would smear a multi-day change
  into one day.
- `swe_gain_in` may be negative (melt, settling, sensor drift). Keep negatives as-is; do
  not clip (SPEC 5.2).
- `is_valid`: a simple, documented quality flag. At minimum, flag as invalid any day
  where `swe_in` is implausible — negative SWE, or a single-day jump larger than a
  declared sanity bound. State the bound you use in a comment and in the report. Do NOT
  drop these rows; flag them and keep them, so the owner can see them.

---

## Part 6 — Coverage report (the important deliverable)

Write `outputs/snow_coverage_report.txt`. This is the first real look at how many winters
are usable, which the buoy gap (Q21) has thrown into question.

Two parts:

**6a — Per-station summary.** For each station: triplet ID, install date, first and last
observed date, total days, days with null `swe_in`, percentage null, and count of
`is_valid = false` days.

**6b — Per-winter coverage matrix.** A table with one row per winter (labelled by start
year, Nov–Apr per SPEC 2.1) and one column per station. Each cell holds a coverage flag
for that station-winter:

- `good` — 90% or more of winter days have non-null `swe_in`
- `thin` — between 50% and 90%
- `missing` — below 50%, or the station did not exist yet

State the exact thresholds in the report header. Then add a final column, **all-station
coverage**, flagging each winter `good` if at least two stations are `good`, else `thin`
or `missing` by the same logic.

This matrix is what Phase 4 will lay the buoy and climate coverage beside. Do not draw
conclusions from it in this session — just produce it. Its job is to make the usable
overlap visible later, not to decide anything now.

---

## Part 7 — Tests

`tests/test_snotel.py`. Small and specific. No network access in tests.

1. SWE gain across a gap is null: given SWE on day 1 and day 3 with day 2 missing, the
   gain on day 3 is null, not the two-day difference.
2. Negative gain is preserved, not clipped: a drop from 10.0 to 9.5 gives −0.5.
3. Missing values parse to NaN, not to 0 or a sentinel.
4. Gap rows exist: a station observed on day 1 and day 3 produces three daily rows.
5. Coverage flag logic: a winter with 95% coverage flags `good`, 70% flags `thin`, 30%
   flags `missing`, and a winter before install date flags `missing`.

---

## Validation

Run all of these and paste the real output.

**1. Tests pass**

```
pytest tests/ -v
```

Both `test_ndbc.py` and `test_snotel.py` should pass — confirm 0A's tests still pass too.

**2. Full ingest**

```
python -m powderbuoy.ingest.snotel --region utah
```

**3. Paste the full contents of both reports:**

`outputs/snow_coverage_report.txt` in full — both the per-station summary and the
per-winter matrix.

**4. Sanity on the output table**

```python
import duckdb
con = duckdb.connect()
con.sql("""
  SELECT station,
         MIN(date) AS first_date, MAX(date) AS last_date,
         COUNT(*) AS n_days,
         SUM(CASE WHEN swe_in IS NULL THEN 1 ELSE 0 END) AS null_swe_days,
         ROUND(AVG(swe_in), 2) AS mean_swe,
         ROUND(MAX(swe_in), 2) AS max_swe,
         ROUND(MIN(swe_gain_in), 2) AS min_gain,
         ROUND(MAX(swe_gain_in), 2) AS max_gain
  FROM 'data/processed/snow_daily.parquet'
  GROUP BY station ORDER BY station
""").show()
```

Plausibility checks — flag anything that fails:

- `mean_swe` positive; Wasatch peak-season SWE commonly reaches 15–40 inches, so
  `max_swe` in that rough range is expected. A `max_swe` of 0 or a negative mean means
  something is wrong.
- `max_gain` positive and physically sane — a big storm might add a few inches of SWE in
  a day. A max gain of tens of inches suggests a unit error or a gap-smear.
- `min_gain` negative (melt) is fine and expected in spring.

**5. No silent zero-filling**

```python
con.sql("""
  SELECT COUNT(*) AS suspicious_zero_runs
  FROM (
    SELECT station, date, swe_in,
           LAG(swe_in) OVER (PARTITION BY station ORDER BY date) AS prev
    FROM 'data/processed/snow_daily.parquet'
  )
  WHERE swe_in = 0 AND prev IS NULL
""").show()
```

This is a soft check, not a hard zero. Summer SWE is legitimately 0. The point is to
confirm gaps became null rows, not 0 rows — spot-check a known gap by eye if the number
looks off.

**6. One station, one winter plotted**

Plot `swe_in` for one confirmed station across one winter (e.g. Snowbird, Nov 2018 –
Apr 2019). Save to `outputs/figures/swe_<station>_winter_2018.png`. Confirm it looks like
a snowpack curve — rising through winter, sharp steps up at storms, a melt-off in spring
— not a flat line or noise.

**7. Coverage overlap preview (buoy vs snow, winters only)**

This is a coverage comparison, NOT an analysis — it counts data presence, not
relationships. For each winter, report whether the buoy (51001) has `good` coverage and
whether at least two snow stations have `good` coverage. Just the counts:

```python
# Winters where BOTH buoy and snow are 'good' — the usable set forming up.
# Report: n winters buoy-good, n winters snow-good, n winters both-good.
```

Report the three counts and list the both-good winters. This previews the usable sample
without touching Phase 4's decision. Do not choose a split here.

---

## Consistency check

Before writing the commit message, re-read `SPEC.md`, `STATUS.md` and `DECISIONS.md` and
report:

- Any two entries that contradict each other
- Any duplicated section heading
- Any findings-log entry out of version order
- Anything this session did that the spec does not describe

**Report only. Do not fix silently.** The owner decides. (Note: H1–H4 above are
pre-approved fixes, not new contradictions — do not re-flag them.)

---

## File updates

### SPEC.md
- Version bump 0.2 → 0.3.
- H1: add `apd_mean` row to Section 5.1.
- Section 3.2: record the confirmed NRCS access method and the SNOTEL PST day-definition,
  so the source of truth carries them.
- No other changes. Section 8 stays empty.

### STATUS.md
- Section 1: mark SNOTEL ingest done.
- Section 2: replace with Session 0C (climate index ingest — MJO, ENSO, PDO).
- Section 3: add build-log row.
- Section 4: fill in the `snow_daily` row.
- Section 6: log this session's consistency result, and mark 0A's three consistency
  items resolved (H1, H2, H3).

### DECISIONS.md
- Q3 Resolved: confirmed station IDs, install dates, elevations.
- Q4 Resolved: NRCS REST access method with a working example.
- Q12 Resolved: PST day-definition convention, offset from buoy UTC noted.
- Q22 Resolved: `apd_mean` added to SPEC 5.1.
- Q1: soften wording per H3.
- Q2: append closing note per H4.
- Append any new open questions this session surfaces (e.g. if a candidate station is
  missing, or coverage is thinner than expected).
- No findings entry — this session produces data, not findings.

---

## Commit message

Do not commit — prepare and output only.

```
feat(ingest): SNOTEL snow ingest and coverage report (0B)

- src/powderbuoy/ingest/snotel.py: NRCS AWDB REST loader for daily SWE
  (WTEQ) and precipitation, idempotent raw caching, gap rows preserved
  as null, SWE gain nulled across gaps, negatives kept
- Confirmed Wasatch station IDs written to config/regions/utah.yaml
- Produces data/processed/snow_daily.parquet per SPEC 5.2
- outputs/snow_coverage_report.txt: per-station summary and per-winter
  coverage matrix (first look at usable-winter overlap)
- tests/test_snotel.py: gap-null gain, negative preservation, NaN parsing,
  gap rows, coverage-flag logic
- Housekeeping: apd_mean added to SPEC 5.1 (Q22); NRCS method (Q4),
  SNOTEL PST day-definition (Q12), station IDs (Q3) recorded; Q1 wording
  softened; Q2 closing note added
- No climate indices, no buoy/snow correlation, no analysis, no modelling

SPEC.md: v0.3
```
