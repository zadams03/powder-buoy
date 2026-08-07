# Session 0C — Climate Index Ingest & analysis_daily
**Spec version going in: 0.3 | Version to bump to: 0.4**

---

## READ THIS FIRST

Read `SPEC.md` in full, `STATUS.md` in full, and `DECISIONS.md` in full before doing
anything. Then read this prompt in full before writing any code.

**Apply all critical rules** (SPEC Section 2). The ones that bind this session are 2.3
(the held-out set is sealed — this session must NOT split, seal, or peek), 2.4 (raw data
never modified in place), and 2.5 (missing data never silently filled). This session also
sits one step before Phase 4, so it must not make any Phase 4 or Phase 6 decision.

### Why this session exists

This is the last data-engineering session. It adds the third data source — the known
climate signals — and then glues all three sources into one wide table that Phase 5 will
read.

The climate signals are the control variables (SPEC 3.3). They exist so that later we can
ask whether the buoy adds anything beyond what established science already provides. Three
of them: the MJO (a tropical convection cycle), ENSO (El Niño / La Niña), and the PDO
(Pacific Decadal Oscillation).

The final output, `analysis_daily`, is a deliberately **dumb** join. It commits to
nothing. Every real analytical choice — how to combine snow stations, what counts as a
storm, how to handle the buoy gap — stays open for later phases.

### CRITICAL — scope discipline

- Do NOT split seasons, seal the held-out set, or read any held-out data. That is Phase 4.
- Do NOT combine the five snow stations in any way. No mean, no max, no "any station".
- Do NOT create a "storm day" flag or any target column. That is Phase 6.
- Do NOT fill the buoy's 2010–2014 gap. Leave it null.
- Do NOT compute any correlation, lag, or model. No analysis of any kind.
- Do NOT hardcode data-source URLs inside a module in a way that can't be seen and
  changed; put them in config or a clearly-marked constants block.

Implement exactly what is specified. Do NOT commit — prepare changes, output the commit
message, and stop.

---

## Part 1 — Housekeeping (do this first, it is quick)

Two SPEC corrections and one STATUS cleanup, all owner-approved, carried from 0B's
consistency check. These fix contradictions in the source of truth.

**H1 — Remove the Status column from SPEC Section 6's phases table.** The table lists
phases 0–8 with a "Status" column that no session updates, so it still shows completed
phases as "Not started" — contradicting STATUS.md. Phase status belongs in STATUS.md, not
in the stable spec. Edit SPEC Section 6: keep the phase list and the "Reads held-out?"
column, delete the "Status" column entirely. Add a one-line note under the table: "Live
phase status is tracked in STATUS.md, not here." Then mark the corresponding 0B
consistency item Resolved in STATUS Section 6.

**H2 — Reword SPEC Section 5's opening timezone line.** It currently reads "All processed
tables are daily, indexed by date, in UTC." That contradicts `snow_daily`, which is
deliberately on Pacific Standard Time (Q12). Change it to: "All processed tables are
daily, indexed by date. Each table's `date` is a calendar day in that table's own native
timezone, documented per table — `buoy_daily` in UTC, `snow_daily` in PST (see Q12).
`date` is not a globally aligned instant." Then mark the corresponding 0B consistency item
Resolved in STATUS Section 6.

**H3 — Trivial STATUS cleanup.** STATUS Section 5 (Blockers) still says the buoy-gap risk
is "Not a blocker for Session 0B." Reword to refer to Phase 4 generally, since 0B is done.
Mark the cosmetic 0B consistency item Resolved.

None of H1–H3 touch data or code.

---

## Part 2 — Establish the climate data sources (record before coding)

Do not assume any URL is live. Confirm each source resolves and returns the expected
columns before building the full loader. Record the confirmed URLs and formats in
DECISIONS.md as part of resolving Q10.

Background facts established during planning (do not re-derive):

**MJO — Wheeler–Hendon RMM index.** Source: Australian Bureau of Meteorology. Daily,
back to 1 June 1974 — covers every winter in this study. Provides RMM1 and RMM2 (two
numbers per day). From these: phase = 1–8 (which region the convection sits over),
amplitude = sqrt(RMM1² + RMM2²) (how strong the MJO is; below 1.0 is conventionally
"no coherent MJO"). The BoM page is `http://www.bom.gov.au/climate/mjo/` and the raw
RMM text file is linked from there; confirm the current direct file URL rather than
guessing it.

> **KNOWN SEAM — flag, do not smooth.** The BoM changed its RMM calculation method at the
> end of 2013: the original Wheeler–Hendon (2004) method through 2013, then a modified
> method from 2014 onward. This study's usable winters straddle that boundary. This is
> the same class of hazard as the buoy's file-format eras — an artificial seam that could
> masquerade as a real change in the data. Do NOT correct or adjust for it in this
> session. Record it in DECISIONS.md as a new open question (see Part 5), add a
> `mjo_method` column to `climate_daily` marking each row "WH2004" (≤2013) or
> "modified2014" (≥2014), so the seam is visible and any later phase can decide whether it
> matters. Recording it is the whole job here.

**ENSO — Niño 3.4 / ONI.** Source: NOAA Climate Prediction Center. Monthly. The Oceanic
Niño Index (ONI) is a 3-month running mean of Niño 3.4 sea-surface-temperature anomalies.
Confirm the current CPC data URL.

**PDO — Pacific Decadal Oscillation.** Source: NOAA. Monthly. Confirm the current URL
(NOAA NCEI or PSL both publish it).

For each source: fetch, confirm it parses, note the format and the date range returned.

---

## Part 3 — Build the climate loader

In `src/powderbuoy/ingest/climate.py`. Same quality bar as `ndbc.py` and `snotel.py`:
pure testable functions, idempotent raw caching to `data/raw/`, raw never modified.

```python
def fetch_mjo(raw_dir: Path, session: requests.Session) -> Path | None:
    """Fetch the BoM RMM index file. Idempotent. Never raises."""

def parse_mjo(path: Path) -> pd.DataFrame:
    """Parse RMM. Returns: date, rmm1, rmm2, mjo_phase, mjo_amplitude, mjo_method.
    Missing values (BoM uses a sentinel such as 1e36 / 999) become NaN, not data.
    mjo_amplitude is recomputed as sqrt(rmm1^2 + rmm2^2), not trusted from the file.
    mjo_method is 'WH2004' for dates <= 2013-12-31, else 'modified2014'.
    """

def fetch_enso(raw_dir: Path, session: requests.Session) -> Path | None: ...
def parse_enso(path: Path) -> pd.DataFrame:
    """Returns: year, month, nino34 (or ONI). Monthly rows."""

def fetch_pdo(raw_dir: Path, session: requests.Session) -> Path | None: ...
def parse_pdo(path: Path) -> pd.DataFrame:
    """Returns: year, month, pdo. Monthly rows."""
```

Watch for sentinel missing values in all three — these government files use large
placeholder numbers (e.g. 1e36, -999, 99.9) for missing months. Convert to NaN before
anything else, exactly as the buoy loader does.

---

## Part 4 — Build climate_daily, with correct monthly handling (resolves Q10)

This is the one subtle part of the session. The MJO is daily and drops straight in. ENSO
and PDO are monthly, and attaching a monthly number to daily rows is where look-ahead can
sneak in.

**The problem.** A monthly index value for, say, January is only *known* after January
ends. If you stamp January's value onto 1 January, a model reading that row on 1 January
is seeing information from the end of the month — the future. That is leakage (SPEC 2.1's
cousin: not a bad split, but a bad join).

**The rule for this session.** Attach monthly values with an explicit availability lag and
a flag, so no daily row ever contains a monthly value that wasn't yet knowable on that day:

- A month's value is treated as available from the **first day of the following month**.
  So January's ONI populates daily rows from 1 February onward, until superseded by
  February's value (available 1 March), and so on.
- Add a boolean column per monthly index — `nino34_is_ffilled`, `pdo_is_ffilled` — set
  true on every daily row (because every daily value is carried from a monthly figure).
  This makes it explicit in the data that these are held-constant monthly values, not
  daily measurements.
- Do NOT interpolate between months. Hold the last available monthly value flat. A step
  function is honest; a smooth interpolation invents data.

Record this whole convention in DECISIONS.md Q10 and mark it Resolved. State plainly: the
one-month availability lag is deliberate and prevents within-month look-ahead; if a later
phase wants a different convention it must be a recorded protocol change.

`climate_daily` schema (extends SPEC 5.3 — note the additions):

| Column | Notes |
| --- | --- |
| date | UTC calendar day |
| rmm1, rmm2 | MJO components |
| mjo_phase | 1–8 |
| mjo_amplitude | sqrt(rmm1²+rmm2²) |
| mjo_method | 'WH2004' or 'modified2014' — the known seam |
| nino34 | monthly ONI, held flat, lagged one month |
| nino34_is_ffilled | always true; marks the value as a carried monthly figure |
| pdo | monthly, held flat, lagged one month |
| pdo_is_ffilled | always true |

SPEC 5.3 should be updated to match this (the `mjo_method` and `_is_ffilled` columns are
additions beyond the original 5.3 sketch — update the spec so it matches what is built,
and note the change).

---

## Part 5 — Build analysis_daily (the dumb wide join)

This is the table Phase 5 reads. It must be **dumb**: a wide outer join on `date`, with
every source's columns carried through unchanged, and **no analytical decision baked in**.

**Explicit prohibitions for this table** (each corresponds to a deferred decision):

- Keep all five snow stations as **separate columns**. Do NOT average, max, or otherwise
  combine them (that is Q5 / Q20, a Phase 6 decision).
- Do NOT create any `storm` / `is_storm` / target column (Phase 6).
- Do NOT fill the buoy's 2010–2014 gap or any other gap. Nulls stay null (Q21, Phase 4).
- Do NOT drop any date for being incomplete.

**Join type: full outer join on `date`.** Keep every date that any source has, and null
the columns from sources that don't cover it. This preserves the ragged edges — the buoy
gap, the pre-install snow years — so Phase 4 sees the true shape rather than a
pre-trimmed table.

**Timezone note for the join (Q12).** `buoy_daily.date` is a UTC day and `snow_daily.date`
is a PST day. They are joined on the calendar-date label as-is, accepting the documented
~8-hour offset (immaterial at the 1–2 week lag under study). Add a one-line comment in the
join code pointing to Q12 so this is a conscious, recorded choice, not an accident.

Column naming: prefix by source to keep it readable — `buoy_51001_wvht_mean`,
`snow_snowbird_swe_gain_in`, `mjo_phase`, etc. Pick a consistent scheme and document it in
a short docstring. One row per date.

Write to `data/processed/analysis_daily.parquet`.

Add `analysis_daily` to SPEC 5.4 with the actual column scheme produced (5.4 is currently
only a sketch — make it match what is built).

---

## Part 6 — Tests

`tests/test_climate.py`. Small, specific, no network.

1. `mjo_amplitude` is recomputed correctly: rmm1=3, rmm2=4 gives amplitude 5.0.
2. `mjo_method` seam: a 2013-12-31 row is 'WH2004', a 2014-01-01 row is 'modified2014'.
3. Sentinel handling: a placeholder missing value (e.g. 1e36) parses to NaN.
4. Monthly availability lag: January's ONI value appears on 1 February's daily row, and
   is NOT present on any January daily row.
5. Monthly hold-flat: with only January and February monthly values, 15 February reads
   January's value (February not yet available until 1 March).

---

## Validation

Run all of these and paste the real output.

**1. Tests pass**

```
pytest tests/ -v
```

All prior tests plus the new climate tests. Confirm the 0A and 0B tests still pass.

**2. Full build**

```
python -m powderbuoy.ingest.climate --region utah
```

**3. climate_daily sanity**

```python
import duckdb
con = duckdb.connect()
con.sql("""
  SELECT MIN(date) AS first, MAX(date) AS last, COUNT(*) AS n,
         ROUND(AVG(mjo_amplitude),3) AS mean_amp,
         SUM(CASE WHEN mjo_method='WH2004' THEN 1 ELSE 0 END) AS wh2004_days,
         SUM(CASE WHEN mjo_method='modified2014' THEN 1 ELSE 0 END) AS modified_days,
         ROUND(MIN(nino34),2) AS min_nino, ROUND(MAX(nino34),2) AS max_nino,
         ROUND(MIN(pdo),2) AS min_pdo, ROUND(MAX(pdo),2) AS max_pdo
  FROM 'data/processed/climate_daily.parquet'
""").show()
```

Plausibility — flag anything failing:

- `mjo_phase` only ever 1–8; `mjo_amplitude` mostly 0–3.
- `nino34` roughly −3 to +3 (it's a temperature anomaly in °C); a strong El Niño peaks
  near +2.5. Values in the tens mean a sentinel survived.
- `pdo` roughly −4 to +4.
- Both method eras present, seam at 2013/2014.

**4. Monthly lag check — no within-month look-ahead**

```python
# Pick a month with a known ONI value. Confirm that value does NOT appear on any daily
# row within that month, and DOES appear from the first of the next month.
con.sql("""
  SELECT date, nino34, nino34_is_ffilled
  FROM 'data/processed/climate_daily.parquet'
  WHERE date BETWEEN '2016-01-28' AND '2016-02-03'
  ORDER BY date
""").show()
```

Confirm the value changes on 1 February, not during January, and `is_ffilled` is true.

**5. analysis_daily shape**

```python
con.sql("""
  SELECT COUNT(*) AS n_rows, MIN(date) AS first, MAX(date) AS last,
         COUNT(buoy_51001_wvht_mean) AS buoy_present,
         COUNT(snow_snowbird_swe_in) AS snow_present,
         COUNT(mjo_phase) AS mjo_present
  FROM 'data/processed/analysis_daily.parquet'
""").show()
```

Expected shape checks:

- `n_rows` equals the count of distinct dates across all sources (full outer join).
- `buoy_present` is materially less than `n_rows` — the 2010–2014 gap and pre-1981 /
  scattered gaps show as nulls. Confirm the gap is visible.
- `mjo_present` covers essentially the whole range (MJO back to 1974).
- No date is dropped for incompleteness.

**6. Confirm no forbidden columns exist**

```python
con.sql("PRAGMA table_info('data/processed/analysis_daily.parquet')").show()
```

Confirm: five separate snow-station column groups (no combined/mean/max snow column), and
NO column named like `storm`, `is_storm`, `target`, or any single combined snow signal.
If any exists, it was added in error — remove it.

**7. Buoy gap is preserved, not filled**

```python
con.sql("""
  SELECT COUNT(*) AS gap_days_with_null_buoy
  FROM 'data/processed/analysis_daily.parquet'
  WHERE date BETWEEN '2010-01-01' AND '2014-12-31'
    AND buoy_51001_wvht_mean IS NULL
""").show()
```

Should be a large number (most of the 2010–2014 window). If it's near zero, the gap was
filled — stop and fix.

---

## Consistency check

Before writing the commit message, re-read `SPEC.md`, `STATUS.md`, and `DECISIONS.md` and
report any contradiction, duplicated heading, or findings-log ordering problem. Report
only — do not fix silently. (H1–H3 above are pre-approved fixes, not new contradictions —
do not re-flag them.)

Pay particular attention to whether SPEC 5.3 and 5.4 now match what was actually built,
since this session extended both.

---

## File updates

### SPEC.md
- Version bump 0.3 → 0.4.
- H1: remove Status column from Section 6 phases table; add the "status tracked in
  STATUS.md" note.
- H2: reword Section 5's opening timezone line.
- Section 3.3: record the confirmed climate data sources and URLs.
- Section 5.3: update to match the built `climate_daily` (add `mjo_method`,
  `nino34_is_ffilled`, `pdo_is_ffilled`).
- Section 5.4: replace the sketch with the actual `analysis_daily` column scheme.
- Section 8 stays empty.

### STATUS.md
- Section 1: mark climate ingest and analysis_daily done. This completes Phases 0–3.
- Section 2: replace with Phase 4 (season split) as the next session — but note it is a
  decision session, not a build session, and will need its own planning first.
- Section 3: add build-log row.
- Section 4: fill in `climate_daily` and `analysis_daily` rows.
- Section 6: log this session's consistency result; mark 0B's three items resolved.

### DECISIONS.md
- Q10 Resolved: the monthly availability-lag + hold-flat + flag convention.
- New open question (call it Q23): the MJO 2013/2014 method seam — recorded, flagged in
  data via `mjo_method`, decision on whether it matters deferred to Phase 5.
- Append any other new open questions surfaced.
- No findings entry — this session produces data, not findings.

---

## Commit message

Do not commit — prepare and output only.

```
feat(ingest): climate indices and dumb analysis_daily join (0C)

- src/powderbuoy/ingest/climate.py: loaders for BoM RMM MJO (daily),
  NOAA ONI/Nino3.4 and PDO (monthly); idempotent raw caching; sentinel
  handling; amplitude recomputed; mjo_method column marks the BoM
  2013/2014 method seam
- climate_daily.parquet: daily MJO plus monthly ENSO/PDO attached with a
  one-month availability lag and is_ffilled flags — no within-month
  look-ahead (Q10 resolved)
- analysis_daily.parquet: full outer join of buoy, all five snow stations
  (kept separate), and climate on date; ragged edges and buoy gap left as
  nulls; no snow combination, no storm/target column, nothing filled
- tests/test_climate.py: amplitude, method seam, sentinel, monthly lag,
  hold-flat
- Housekeeping: SPEC Section 6 status column removed (tracked in STATUS);
  SPEC Section 5 timezone line reworded; SPEC 5.3/5.4 updated to match
  built tables
- Completes data engineering (Phases 0-3). Next is Phase 4 (season split),
  a decision session requiring its own planning
- No correlation, no lag scan, no modelling, no season split

SPEC.md: v0.4
```
