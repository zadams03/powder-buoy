# SPEC.md — Powder Buoy

**Version: 0.9**
**Status: Phases 0–4 complete; Phase 5 Stages 1–2 (counting) run on the exploration
winters (Session 5a); the MJO mechanism check run on the same winters (Session 5b);
Phase 6 complete — Section 8, the evaluation protocol, is written and LOCKED (Session 6);
and Phase 7 complete — the held-out set was OPENED ONCE, 2026-08-09, and the locked
folklore rule scored on it against Section 8 as frozen at spec version 0.8. The seal is
now spent: it cannot be re-sealed and the six held-out winters are never scored again.
Stage 3 (modelling) is GATED and the gate did not open, so no model exists and none was
tested. Next is Phase 8, the write-up.**

This file is the stable specification. It describes what the project is, what data it
uses, how it must be built, and how it will be judged. It changes rarely.

Current state and next actions live in `STATUS.md`.
Open questions and findings live in `DECISIONS.md`.

Claude Code must read this file in full, and `STATUS.md` in full, before every session.

---

## 1. What this project is

A study, not a product.

**The question:** does a Pacific Ocean buoy tell us anything useful about Utah snow,
that we did not already know from established climate signals?

**The output:** an honest, quantified answer, plus the code that produced it.

A result of "no, the buoy adds nothing" is a complete and successful outcome. This is
stated here deliberately so that no later session feels pressure to find a signal.

### 1.1 Background — the folklore

Since the mid-2000s, a community of Utah skiers has tracked NOAA buoy 51101, a
3-metre discus buoy a few hundred kilometres northwest of Kauai. The rule they use is:

> When wave height spikes ("a buoy pop"), the Wasatch mountains get a storm about two
> weeks later. Bigger pop, bigger storm.

Claimed accuracy is around 80%, self-reported, over small samples, with no baseline
quoted. No published study of the claim exists.

**Caveat on the buoy the folklore names (added 0.7).** 51101's archive begins 2008-02-21
(Section 3.1), so it did not exist for most of this study's exploration winters — 10 of
the 16 (1989–2003) predate it entirely. For those winters the pop signal necessarily
comes from 51001, validated as a stand-in by the 0.98 cross-buoy correlation where the
two overlap (`DECISIONS.md` Q1, Q21). The date above is deliberately vague because the
community's own start date is not documented; what is documented is when the data begins.

### 1.2 Why the folklore mechanism cannot be right as stated

The stated explanation is that a low-pressure system passes the buoy and later reaches
Utah. The timing does not work.

Long-period ocean swell travels roughly 2,000 km per day. A storm near the Aleutians
sends swell to Hawaii within 1–2 days. That same storm would reach Utah in 3–5 days,
not 14.

So the buoy is not tracking the storm that later hits Utah.

### 1.3 The hypothesis we are actually testing

If a real signal exists, the buoy is a **proxy for a large-scale atmospheric regime**,
not a tracker of individual storms.

The Madden–Julian Oscillation (MJO) is a band of tropical convection that moves
eastward around the globe on a 30–60 day cycle. It is an established source of
subseasonal predictability. It modulates the North Pacific jet stream, which in turn
drives atmospheric rivers into the western United States. When the MJO sits in its
western Pacific phases during winter, extreme precipitation across the western US
becomes more frequent.

An active North Pacific storm track produces both bigger swell at Hawaii and, on a lag
of one to three weeks, more storms over Utah. The buoy would be a symptom, not a cause.

**This gives the project its central experiment:** if the buoy has skill, is that skill
anything more than a crude, free MJO index?

---

## 2. Critical rules

These apply to every session. Every session prompt must state "apply all critical
rules". Violating one invalidates the result it touches.

### 2.1 CRITICAL — Never split data randomly

Daily weather is heavily autocorrelated. If it snowed today it probably snowed
yesterday.

A random train/test split lets the model see near-copies of test days during training.
The score comes out high and means nothing.

**Rule:** all train/test splits are by whole winter season. A season runs 1 November to
30 April and is labelled by its starting year (season 2015 = Nov 2015 to Apr 2016).
Never split by individual day, week, or month.

Cross-validation is leave-one-season-out or blocked by contiguous groups of seasons.
Never `KFold` with `shuffle=True`.

### 2.2 CRITICAL — No baseline, no claim

No accuracy, hit rate, or score may be reported without the corresponding baseline
number next to it in the same table or sentence.

The folklore's "83% accurate" is the failure mode this rule prevents. In a Wasatch
winter, most two-week windows contain a storm anyway, so a high hit rate may be
entirely base rate.

### 2.3 CRITICAL — The held-out seasons are sealed

**The problem this solves.** The folklore claims a 14-day lag. We do not know the true
lag, so we want to test many. But if you test 31 lags on noise, one of them will look
good by chance. Report that one and you have fooled yourself. The same applies to
thresholds, station combinations, and every other choice.

**The mechanism.** Winters are split into two sets at the start of the project, before
any analysis. They are never mixed.

- **Exploration seasons.** Roughly the first 70% of winters. Anything is permitted
  here. Scan every lag. Try every threshold. Plot freely. Change your mind. No rules.
- **Held-out seasons.** Roughly the last 30%. Sealed. No code reads them and no human
  looks at them until the Section 8 protocol is written and locked.

**The sequence.**

1. Split the seasons (Phase 4). Record the split in `DECISIONS.md`.
2. Explore on the exploration seasons only (Phase 5). Choose the lag, thresholds, and
   feature set here.
3. Write and lock Section 8 (Phase 6), using what exploration found.
4. Unseal. Run once on the held-out seasons (Phase 7).
5. That number is the answer.

The choices in step 2 were made using data that step 4 never saw. That is what makes
the final number honest.

**One shot.** The held-out set is evaluated once. If the result is disappointing and
something is then tweaked and re-run, the seal is broken and every subsequent number is
EXPLORATORY. It cannot be re-sealed. Record every unsealing in `DECISIONS.md`,
including failed or abandoned ones.

**Enforcement in code, not just in intent.** The data loader must accept an explicit
argument to include held-out seasons, defaulting to exclusion. Something like
`load_analysis_data(include_holdout=False)`. Any script that passes `True` must state
why in a comment referencing the protocol version. Accidental leakage should require
someone to type the word "holdout", not merely to forget a filter.

**Labelling.** Any result produced on exploration seasons is EXPLORATORY in
`DECISIONS.md` and may not be reported as a conclusion. Only the single held-out
evaluation produces CONFIRMED findings.

### 2.4 CRITICAL — Raw data is never modified in place

Downloaded files land in `data/raw/` and are never edited. All cleaning writes new
files to `data/processed/`. Any pipeline stage must be re-runnable from raw with no
manual steps.

### 2.5 CRITICAL — Missing data is never silently filled

Buoys go offline for weeks or months. SNOTEL sensors fail.

Gaps must be represented as null, counted, and reported. Forward-filling, interpolating,
or zero-filling a gap is only permitted where a session prompt explicitly specifies the
method and the reason. Never as a default.

---

## 3. Data

### 3.1 Predictor — NDBC buoys

Source: NOAA National Data Buoy Center. Free, no key required.

| Station | Location | Record starts | Role |
| --- | --- | --- | --- |
| 51001 | NW of Kauai | ~1981 | **Primary.** Long record |
| 51101 | NW of Kauai | ~2008 | The famous "Powder Buoy". Near 51001 |
| 51002, 51003, 51004 | Hawaii region | varies | Reserve / robustness checks |
| 46001, 46005, 46006 | N Pacific / offshore US | varies | Reserve / later regions |

51001 and 51101 both sit in deep water northwest of Kauai, close enough that they should
measure near-identical swell. We use 51001 as primary because its record is roughly two
decades longer. 51101 is used to confirm the two agree.

The exact separation between them and the exact usable record length of each are
**not asserted here** — they are measured in Session 0A. If the two buoys do not
correlate tightly over their overlap, the choice of 51001 is reconsidered (see
`DECISIONS.md` Q1 and Q21).

**Measured in Session 0A (2026-08-07):**

- **51001:** historical archive covers 1981-02-11 to 2025-12-31 (1980 is a 404 —
  the record genuinely starts in Feb 1981). **The archive has no station-year
  files at all for 2010–2014.** Daily-table gaps total 3,633 of 16,395 days
  (22.2%), and the single longest continuous gap is 2,068 days, 2009-12-25 to
  2015-08-23 — a five-plus-year hole, not scattered outages. This materially
  affects the "~40 winters" assumption in Section 6.0 and Section 7 — winters
  2009 through 2014 have no 51001 predictor data at all. See `DECISIONS.md` Q21.
- **51101:** historical archive covers 2008-02-21 to 2025-12-31 (nothing before
  2008, as expected; 2026 not yet published). Daily-table gaps total 651 of
  6,524 days (10.0%), longest continuous gap 409 days, 2008-03-08 to
  2009-04-20 (early commissioning period).
- **Cross-buoy agreement, where both report:** same-day correlation of
  `wvht_mean` = 0.9799 (n = 3,738 overlapping days, mean diff −0.0094 m, sd
  0.1631 m); correlation of the 3-day rolling mean = 0.9825 (n = 3,754, mean
  diff −0.0093 m, sd 0.1350 m). Well above the 0.9 bar — 51001 is confirmed as
  a valid stand-in for 51101 where they overlap (`DECISIONS.md` Q1, Q21).
- **File-format boundaries actually observed** (not the same as the three eras
  assumed going in — detection is by header content, never by year):
  - Through 1998: single header line, 2-digit year under a `YY` column, no
    `TIDE` column, pressure column named `BAR`, wind direction named `WD`.
  - 1999–2004: single header line, 4-digit year under a `YYYY` column; `TIDE`
    column present from 2000 on.
  - 2005–2006: single header line, `mm` (minute) column added, still `YYYY`,
    still `BAR`/`WD` naming — this is a fourth, transitional format not called
    out in the original three-era table.
  - 2007 onward: **two** header lines (column names, then units), both
    prefixed `#`. Pressure renamed `PRES`, wind direction renamed `WDIR` — but
    the year column is again labelled `YY`, this time holding **4-digit**
    values (e.g. `2007`), not 2-digit. Column name alone does not indicate
    digit width in this record; the parser detects 2- vs 4-digit years by
    magnitude (`< 100` ⇒ 2-digit), not by column label.

The NDBC historical stdmet archive does not embed per-observation station
coordinates, so per-year repositioning (`DECISIONS.md` Q2) could not be
checked from file content. See the Session 0A ingest report and `DECISIONS.md`
Q2 for what was checked instead.

**Historical archive:** yearly gzipped text files, one per station per year, at
`https://www.ndbc.noaa.gov/data/historical/stdmet/{station}h{year}.txt.gz`

**Recent data:** rolling 45-day file at
`https://www.ndbc.noaa.gov/data/realtime2/{station}.txt`

**Fields used:**

| Column | Meaning | Unit |
| --- | --- | --- |
| WVHT | Significant wave height. Average height of the highest third of waves | metres |
| DPD | Dominant wave period. Period of the most energetic waves | seconds |
| APD | Average wave period | seconds |
| MWD | Mean wave direction, the direction waves are coming from | degrees |
| WSPD | Wind speed | m/s |
| PRES | Air pressure at sea level | hPa |

WVHT is the field the folklore uses. DPD and MWD matter because a long-period swell
from the northwest indicates a distant, energetic North Pacific storm, while a
short-period swell is local wind chop. Distinguishing the two may be where the real
signal lives.

**Known format hazards:**

- File layout changed over the years. Pre-2000 files use a 2-digit year column. Files
  from 2000–2004 use `YYYY MM DD hh`. From 2005 onward a minute column `mm` is added.
  Column count and header lines differ.
- Missing values are sentinel numbers, not blanks. WVHT missing is `99.00`. DPD and APD
  missing is `99.00`. MWD and WDIR missing is `999`. PRES missing is `9999.0`. Air and
  water temperature missing is `999.0`. Rule of thumb: a value that is all nines is
  missing. These must become null, not be treated as data.
- Sampling interval changed over time (hourly, then more frequent). Aggregate to daily.
- Buoys are repositioned and go adrift. Position changes across the record must be
  checked and logged.

### 3.2 Target — SNOTEL snow water equivalent

Source: USDA Natural Resources Conservation Service (NRCS). Free.

SNOTEL is a network of automated snow stations across the western US. Each has a
pressure pillow that weighs the snow sitting on it.

**Snow water equivalent (SWE)** is the depth of water you would get if you melted the
snowpack. Measured in inches. A daily SWE increase of 1 inch means roughly 10 inches of
snow fell, depending on how light the snow was.

We use daily SWE gain as the storm signal.

**Why SWE and not snowfall or snow depth:**

- *Snowfall* (inches per day) is what skiers care about but is measured inconsistently,
  sometimes by hand, sometimes with a marketing incentive, and has gaps.
- *Snow depth* settles overnight. Twelve inches of new snow reads as eight by morning,
  so depth change understates snowfall by a variable amount.
- *SWE* is automated, physically meaningful, consistently measured, and available daily
  back to the 1980s.

**Limitation, accepted:** SWE does not describe snow quality. One inch of SWE could be
eight inches of heavy wet snow or twenty inches of powder. If the project later wants to
predict "good powder day" rather than "storm", temperature must be added.

**Wasatch stations** (IDs confirmed in Session 0B against the live NRCS station list;
see `DECISIONS.md` Q3):

| Station | Triplet ID | Elevation | Install date | Notes |
| --- | --- | --- | --- | --- |
| Snowbird | `766:UT:SNTL` | 9,170 ft | 1989-08-23 | Little Cottonwood Canyon |
| Brighton | `366:UT:SNTL` | 8,790 ft | 1986-09-24 | Big Cottonwood Canyon |
| Mill-D North | `628:UT:SNTL` | 8,940 ft | 1988-10-01 | Big Cottonwood Canyon |
| Thaynes Canyon | `814:UT:SNTL` | 9,260 ft | 1988-06-20 | Park City side |
| Louis Meadow | `972:UT:SNTL` | 6,740 ft | 1999-10-01 | Lower elevation reference |

Elevations are the NRCS-reported figures and differ slightly from the approximate
figures originally listed here; the NRCS figures are authoritative. Station identifiers
use a triplet format `{id}:{state}:SNTL`. IDs live in `config/regions/utah.yaml`, never
hardcoded in a module.

**Access method, confirmed in Session 0B:** NRCS AWDB REST API, base URL
`https://wcc.sc.egov.usda.gov/awdbRestApi`, no API key required. Station metadata via
`GET /services/v1/stations`; daily data via `GET /services/v1/data` with
`elements=WTEQ,PREC,TAVG&duration=DAILY&periodRef=END`. Full parameters and a worked
example are recorded in `DECISIONS.md` Q4.

**Day definition, confirmed in Session 0B:** SNOTEL records on a fixed Pacific Standard
Time day (UTC−8, no daylight saving), interval-ending — the daily value is dated to the
day that just ended. This differs from `buoy_daily`'s UTC calendar day by up to 8 hours.
Neither table is shifted to match the other; each keeps its native day definition, and
any code joining them must account for the offset. See `DECISIONS.md` Q12.

### 3.3 Control variables — known climate signals

These exist so we can test whether the buoy adds anything beyond established science.

| Signal | What it is | Source | Resolution |
| --- | --- | --- | --- |
| MJO (RMM1, RMM2, phase, amplitude) | Tropical convection cycle, 30–60 days | Australian Bureau of Meteorology | Daily, 1974– |
| ENSO (Niño 3.4 / ONI) | El Niño / La Niña state | NOAA CPC | Monthly |
| PDO | Pacific Decadal Oscillation | NOAA | Monthly |

The MJO index used is the Wheeler–Hendon Real-time Multivariate MJO index. It gives two
numbers per day (RMM1, RMM2) which convert to a phase from 1 to 8 and an amplitude.
Phase says where the convection currently is around the globe. Amplitude says how strong
it is. Amplitude below 1.0 is conventionally treated as "no coherent MJO".

**Sources confirmed live in Session 0C (2026-08-07):**

- **MJO — RMM index.** Australian Bureau of Meteorology, daily text file at
  `http://www.bom.gov.au/climate/mjo/graphics/rmm.74toRealtime.txt`. Whitespace-delimited,
  two header lines, columns `year month day RMM1 RMM2 phase amplitude method`. Missing
  values are sentinel `1.E36` or `999`, declared in the file's own header. Returned range
  at fetch time: 1974-06-01 to 2024-02-24. The file carries its own per-row method label,
  which switches from `WH04_method` to `Gottschalk10_method` exactly at the 2013-12-31 /
  2014-01-01 boundary — confirming the known method seam (Q23) but not used directly;
  `mjo_method` is computed from the date, not trusted from this label.
- **ENSO — ONI.** NOAA Climate Prediction Center, monthly ascii table at
  `https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt`. Columns `SEAS YR TOTAL
  ANOM` — a 3-month running Niño 3.4 SST anomaly, one row per overlapping season (`DJF`,
  `JFM`, ... `NDJ`), filed under the year of the season's middle month (the standard NOAA
  convention). `ANOM` is used as `nino34`. Returned range at fetch time: 1950 (`DJF`)
  onward, no sentinel observed in the live record (anomalies run roughly −3 to +3).
- **PDO.** NOAA NCEI ERSSTv5 index, monthly fixed-width table at
  `https://www.ncei.noaa.gov/pub/data/cmb/ersst/v5/index/ersst.v5.pdo.dat`. One row per
  year, one column per month. Missing/not-yet-occurred months are sentinel `99.99`.
  Returned range at fetch time: 1854 onward.

### 3.4 Comparison forecasts — deferred

GEFS Reforecast v12 is available free on AWS Open Data and would let us compare against
a real operational week-2 forecast. This is powerful but heavy. Deferred to a later
phase. Tracked in `DECISIONS.md`.

---

## 4. Repository structure

```
powder-buoy/
├── SPEC.md                      # this file — stable
├── STATUS.md                    # current state, changes every session
├── DECISIONS.md                 # open questions + findings log, append-only
├── README.md
├── pyproject.toml
├── config/
│   ├── settings.yaml            # paths, global defaults
│   └── regions/
│       └── utah.yaml            # buoy ids, snotel ids, season definition
├── src/powderbuoy/
│   ├── config.py                # loads and validates config
│   ├── ingest/
│   │   ├── ndbc.py
│   │   ├── snotel.py
│   │   └── climate.py           # MJO, ENSO, PDO
│   ├── features/
│   ├── models/
│   └── evaluate/
├── data/
│   ├── raw/                     # downloads, never modified (gitignored)
│   └── processed/               # cleaned parquet (gitignored)
├── docs/                        # session prompt files
├── notebooks/                   # exploration only, never the source of a finding
├── outputs/
│   ├── figures/
│   └── experiments/             # experiment register + run artefacts
└── tests/
```

### 4.1 Region config

All station identifiers live in `config/regions/{region}.yaml`. No station ID is ever
hardcoded in a module. Adding a new region later must be a config change, not a code
change, even though only Utah is in scope now.

Example shape:

```yaml
region: utah
buoys:
  primary: "51001"
  secondary: ["51101"]
snow_stations:
  - id: "766:UT:SNTL"
    name: "Snowbird"
season:
  start_month_day: "11-01"
  end_month_day: "04-30"
```

### 4.2 Environment and tooling

- Python 3.11+
- `uv` for dependency management
- Storage: Parquet files on disk. DuckDB for querying. No database server.
- Core libraries: pandas, pyarrow, duckdb, requests, pyyaml, matplotlib
- Modelling (added later): scikit-learn, lightgbm
- Testing: pytest

Rationale: this is a study run by one person on one machine. A database server is
unnecessary overhead. Parquet plus DuckDB gives fast queries with zero infrastructure.

### 4.3 Determinism

Every script accepts a `--seed` argument defaulting to 42. Any run that produces a
number must be reproducible from raw data with a single command. Every experiment run
records its git commit hash.

---

## 5. Canonical data model

All processed tables are daily, indexed by date. Each table's `date` is a calendar day
in that table's own native timezone, documented per table — `buoy_daily` in UTC,
`snow_daily` in PST (see Q12). `date` is not a globally aligned instant.

### 5.1 `buoy_daily`

One row per station per day.

| Column | Type | Notes |
| --- | --- | --- |
| date | date | UTC |
| station | text | e.g. "51001" |
| wvht_mean, wvht_max, wvht_min | float | metres. Null if no observations that day |
| dpd_mean, dpd_max | float | seconds |
| apd_mean | float | seconds. Mean of valid APD |
| mwd_mean | float | degrees. Circular mean, not arithmetic |
| wspd_mean, wspd_max | float | m/s |
| pres_mean, pres_min | float | hPa |
| n_obs | int | observations that contributed. 0 means a gap |

`mwd_mean` must use a circular mean. Averaging 350° and 10° arithmetically gives 180°,
which is the opposite direction and completely wrong.

### 5.2 `snow_daily`

One row per station per day.

| Column | Type | Notes |
| --- | --- | --- |
| date | date | Local observation date |
| station | text | Triplet ID |
| swe_in | float | Snow water equivalent, inches |
| swe_gain_in | float | swe_in minus previous day. Null if previous day missing |
| precip_accum_in | float | Where available |
| temp_mean_f | float | Where available |
| is_valid | bool | Passed quality checks |

`swe_gain_in` can be negative (melting, settling, sensor drift). Negative values are
kept as-is, not clipped. Threshold logic handles them.

### 5.3 `climate_daily`

Built in Session 0C. One row per UTC calendar day, spanning the MJO source's own daily
range — the only genuinely daily source among the three.

| Column | Type | Notes |
| --- | --- | --- |
| date | date | UTC calendar day |
| rmm1, rmm2 | float | MJO components |
| mjo_phase | int (nullable) | 1–8 |
| mjo_amplitude | float | sqrt(rmm1² + rmm2²), recomputed, never trusted from source |
| mjo_method | text | `WH2004` (date ≤ 2013-12-31) or `modified2014` (date ≥ 2014-01-01) — the BoM method seam, flagged not smoothed (Q23) |
| nino34 | float | Monthly ONI, attached with a one-month availability lag and held flat (Q10) |
| nino34_is_ffilled | bool | Always true — marks the value as a carried monthly figure |
| pdo | float | Monthly, same one-month-lag treatment as `nino34` |
| pdo_is_ffilled | bool | Always true |

### 5.4 `analysis_daily`

Built in Session 0C. The dumb wide join everything downstream reads. One row per date,
full outer join of `buoy_daily`, `snow_daily`, and `climate_daily` on `date` — every date
any source has, nulled elsewhere. No station is combined, no target/storm column exists,
and no gap is filled; all of that is deferred to later phases (Q5, Q20, Phase 6).

Column naming is prefix-by-source:

| Prefix | Example | Meaning |
| --- | --- | --- |
| `buoy_{station}_` | `buoy_51001_wvht_mean` | One column group per buoy station, all of `buoy_daily`'s non-key columns |
| `snow_{station_slug}_` | `snow_snowbird_swe_gain_in` | One column group per SNOTEL station (name slugified, lowercased, spaces/hyphens to `_`), all of `snow_daily`'s non-key columns, kept separate — never combined |
| (none) | `mjo_phase`, `nino34`, `pdo_is_ffilled` | Climate columns carried through unprefixed — their names already say what they are |

`buoy_daily.date` is a native UTC day and `snow_daily.date` is a native PST day (Q12);
the join is on the calendar-date label as-is, the ~8-hour offset accepted and undisturbed
per Q12, immaterial at the 1–2 week lag under study.

---

## 6. Phases

| Phase | Goal | Reads held-out? |
| --- | --- | --- |
| 0 | Repo scaffold, config, environment | n/a |
| 1 | NDBC buoy ingest and cleaning | n/a |
| 2 | SNOTEL snow ingest and cleaning | n/a |
| 3 | Climate index ingest, build `analysis_daily` | n/a |
| 4 | **Split seasons.** Seal the held-out set | No |
| 5 | **Exploration.** Contingency tables, then lag scan, then gated modelling (6.1) | No |
| 6 | **Lock evaluation protocol** (Section 8) | No |
| 7 | **Held-out evaluation.** Folklore rule only, run once (four-model comparison not run — see 8.1) | Yes, once |
| 8 | Write-up. Dashboard decision (11.1) | — |

Live phase status is tracked in STATUS.md, not here.

Phases 0 to 3 are data engineering. No analysis happens in them, so the seal is not at
risk.

Phase 4 makes exactly one decision: which winters go in the box. Nothing else.

Phase 5 is deliberately unconstrained. Every number it produces is EXPLORATORY. Its job
is to decide what Phase 6 will commit to. See Section 6.1 for the order of work within
it, which is not optional — and for the mechanism check (Phase 5b) that was run after
Stage 2 as a documented addition to those three stages, not as one of them.

Phase 6 writes Section 8 and freezes it.

Phase 7 unseals the held-out set and runs once. It scores **the locked folklore rule
only**; the four-model comparison is **not run**, because the Stage 3 gate did not open —
see **Section 8.1**, which is the authority here.

If Phase 7 shows the buoy carries real information, a fresh planning session decides
what happens next. That is not scoped here.

### 6.0 Dependency on Session 0A — the record-length risk

Much of this plan assumes 51001 gives a long, continuous record of roughly 40 winters.
That assumption is tested in Session 0A, not before. Two ways it can fail:

- **The two buoys do not correlate tightly.** Then 51001 is not a valid stand-in for the
  buoy the folklore actually names, and we fall back to 51101's shorter record.
- **51001 was repositioned mid-record.** Then its wave climate may shift partway through,
  and the record may have to be split, shortening the usable span.

**Plan B, if the usable record is short (roughly 18 winters or fewer):** the held-out
set shrinks to around 5 winters. A five-winter held-out evaluation is weak — its
conclusions carry wide error bars and the four-model comparison may be unable to
separate the models at all. If we land here, that is a decision point, not an automatic
continue: either accept weaker conclusions and say so plainly, or pause and reconsider
scope. Recorded so the decision is faced, not stumbled into.

**The decision point was reached, and was resolved by the Phase 4 split.** Neither of the
two failure modes above is what materialised: the two buoys correlate at 0.98, and
whether 51001 was repositioned could not be checked from the stdmet archive at all
(`DECISIONS.md` Q2, still open, low priority). What Session 0A found instead was a third
thing — a 2010–2014 hole in 51001's archive — and requiring MJO coverage on top of it
left 22 usable winters, inside Plan B's range. Phase 4 took the first branch knowingly: proceed with a two-era record and a
six-winter held-out set, accepting weaker conclusions and stating them plainly, rather
than pausing to reconsider scope (`DECISIONS.md` Q13, Q21). The risk description above
is kept for future readers; it is no longer an open question.

### 6.1 Order of work inside Phase 5 — counting before modelling

Machine learning is not the default tool here. It is the last one.

Phase 5 runs in three stages, in this order. Each stage gates the next.

**Stage 1 — Contingency tables.** Does a buoy pop precede a storm more often than a
non-pop does?

Build the 2×2 table at the folklore lag:

|  | Storm followed | No storm followed |
| --- | --- | --- |
| Buoy popped | a | b |
| Buoy did not pop | c | d |

The unit being counted is an **occasion** — one anchor day, asking whether a storm
occurs in the window that follows it. The four cells count occasions, not storms, and
the glosses below are written in those terms (tightened in 0.7; the formulas are
unchanged). One storm can fall inside the windows of many overlapping occasions, and a
storm falling inside no window is counted by none of them.

Two rates matter, and they must not be confused:

- **Probability of detection (POD)** = `a/(a+c)` — of all storm-containing occasions,
  the fraction that followed a pop. This is the "hit rate" in the forecast-verification
  sense.
- **False alarm rate (POFD)** = `b/(b+d)` — of all storm-free occasions, the fraction
  that followed a pop, i.e. false alarms.

Also report, next to each other and always (rule 2.2):

- **Storm rate given a pop** = `a/(a+b)` — of all pop occasions, the fraction actually
  followed by a storm.
- **Base rate** = `(a+c)/(a+b+c+d)` — the fraction of all occasions that contain a storm
  in their window, with no prediction involved.

The buoy has skill only if the storm rate given a pop clearly exceeds the base rate.

**How the "did not pop" comparison occasions are drawn is not specified here**, and it is
the single most consequential choice in the table. Phase 5a had to construct it to make
these formulas computable; that construction — the anchor-day occasion, one-to-one
claiming on the pop row, and what it does to PSS magnitudes — is recorded in
`DECISIONS.md` Q25 and is **settled in the Phase 6 protocol (Section 8)**, which must
adopt or replace it deliberately rather than inherit it.

Score with the Peirce skill score, also called the Hanssen–Kuipers discriminant:

```
PSS = POD - POFD = a/(a+c) - b/(b+d)
```

PSS of 0 means no better than chance. 1 is perfect. Negative means worse than chance.

This is a real forecast verification method, not a lesser substitute for a model.
Meteorologists have used it for a century, and for a binary event with one predictor it
is the right tool.

**Stage 2 — Lag scan.** Repeat Stage 1 at every lag from 0 to 30 days. Plot skill
against lag. A genuine signal should show a broad bump, not a single isolated spike —
atmospheric regimes persist for days, so if lag 14 works and lags 12, 13, 15 and 16 do
not, that is noise, not physics.

Repeat across a small declared set of pop definitions and SWE thresholds, so we can see
whether any apparent signal survives reasonable changes to the definitions.

**Stage 3 — Modelling, GATED.** Models are only built if Stages 1 and 2 show something
worth separating out.

**Gate condition:** Stage 2 must show positive skill at some lag, in a coherent band of
adjacent lags, that survives sensitivity to pop definition and SWE threshold. If it does
not, Phase 5 ends here and Phase 6 locks a protocol that expects a null result.

If contingency tables show nothing, a model will not find a signal that is absent. It
will find a more elaborate way to overfit.

**Phase 5b — the mechanism check. A documented addition, not a fourth stage (added 0.8).**
Stage 2 closed the gate, so Phase 5 ended at counting. A further session was then run on
the exploration winters, labelled **Phase 5b**, which asked a different question: not
"does the buoy predict snow" but "*why* does it not". It tested the two internal links of
the chain the folklore skips (Section 1.3) — MJO ↔ buoy swell (Link A) and MJO ↔ Utah snow
(Link B) — by correlation and counting only. **It is not one of the three stages above and
does not gate anything.** It built no model, did not reopen Stage 3, and read no held-out
winter. It is recorded here so that a reader of this file alone can see that it happened
and where it sits: after Stage 2, outside the gate, on exploration data. Its results are
findings F4–F6 in `DECISIONS.md`, all EXPLORATORY. A pre/post-seam robustness check on the
same two links was run in Phase 6 (`DECISIONS.md` Q23), also on exploration data only.

### 6.2 What modelling adds, when it is justified

Recorded so no session builds a model for the wrong reason.

Counting handles "is there a signal" and "at what lag" better than a model does. It is
transparent, needs no tuning, and cannot silently leak.

Counting struggles with the project's actual question — does the buoy add anything
beyond the MJO? Answering that by counting means holding the MJO fixed and comparing
within each phase. With on the order of a few thousand winter days (exact count
confirmed after ingest) split across 8 MJO phases, then by pop and by storm, each cell
holds a handful of days and nothing can be concluded.

A model uses all days at once and estimates each input's contribution while the others
vary. That is the specific job it is here to do.

Three secondary benefits:

- **No arbitrary pop threshold.** Counting forces a definition of "a pop" — 3 metres,
  4 metres, a 1-metre rise over two days. Every choice is a fork, and testing many is
  the multiple-comparisons trap. A model takes wave height as a continuous number.
- **Probabilities, not yes/no.** A calibrated probability can be scored properly and is
  more useful. Binary forecasts hide how confident the method actually is.
- **Interactions.** A pop may only matter when the swell is long-period and from the
  northwest, or only in La Niña winters. Counting cannot test that without slicing the
  sample into nothing.

---

## 7. The central experiment (Phase 7)

**Conditional on the Phase 5 gate** (Section 6.1, Stage 3). If contingency tables show
no signal, this experiment is not run. Phase 7 instead reports the null result from the
folklore rule alone, scored once on the held-out seasons.

> **NOT RUN (settled in Phase 6, spec version 0.8).** The gate did not open — the lag scan
> showed no coherent band of positive skill at any lag (`DECISIONS.md` F3) — so the
> four-model comparison described in the rest of this section **is not executed**, and no
> model of any kind is scored on the held-out set. Everything below is retained as the
> design that would have been used. See **Section 8.1** for the decision and **Section 8.6**
> for what this comparison would have tested.

Four models, identical data, identical splits, identical scoring. Only the input
features differ.

| Model | Features | Question it answers |
| --- | --- | --- |
| A | Day of year only | The floor. Climatology |
| B | MJO + ENSO + day of year | What established science already gives |
| C | Buoy + day of year | Does the folklore contain anything? |
| D | Buoy + MJO + ENSO + day of year | Does the buoy add anything new? |

**Reading the outcome:**

| Result | Meaning |
| --- | --- |
| C > A and D > B | The buoy carries information beyond known signals. Strongest case |
| C > A and D ≈ B | The buoy is a crude proxy for the MJO. Interesting, and the most likely outcome |
| C ≈ A | The folklore is noise |
| Nothing > A | Everything is base rate. Still a result |

All four are valid conclusions. The project succeeds by answering the question, not by
finding a signal.

**Model choice:** start with logistic regression, the simplest model that outputs a
probability. Then gradient boosting (LightGBM). No neural networks — Session 0A measured
the usable record at two eras either side of the 2010–2014 buoy gap, not one unbroken
~40-winter span, and once MJO coverage is required for the four-model comparison this
leaves 22 usable winters (Phase 4, `DECISIONS.md` Q13/Q21). Far too little for a neural
network either way, and interpretability matters more than raw fit here.

---

## 8. Evaluation protocol — LOCKED (Phase 6, spec version 0.8, 2026-08-09)

> **This section is FROZEN (rule 2.3).** It was written in Phase 6, after exploration and
> **before the held-out winters were unsealed**. Phase 7 executes it literally and does not
> amend it. If Phase 7 finds any instruction here ambiguous, it records the ambiguity and
> the reading it took in `DECISIONS.md`, alongside the result — it does not edit this
> section to match what it did. Any change to this section after Phase 7 has run makes
> every number downstream of it EXPLORATORY.

### 8.1 Scope — and what is deliberately NOT tested

**The four-model comparison (Section 7) is NOT run.** The Stage 3 gate in Section 6.1
required "positive skill at some lag, in a coherent band of adjacent lags, that survives
sensitivity to pop definition and SWE threshold". Exploration produced the opposite: of
279 lag × pop-threshold combinations in the lag scan, one had a PSS above zero, at
+0.00066, and the longest run of consecutive positive lags at any threshold was one
(`DECISIONS.md` F3); at the folklore lag itself, storm-rate-given-a-pop was below its own
base rate in all 54 configurations (F2). The joint gate review did not open the gate.
There is therefore no model to validate, and building one here to score would be testing
something exploration gave no reason to build.

**What the held-out set is spent on instead.** One thing: a confirmatory out-of-sample
test of the **folklore rule** as defined in 8.2, run once, expecting a null. This is worth
the seal because the folklore's claim is a claim about the world, not about our exploration
winters — it was specified by other people, years before this study, and it deserves to be
tested on winters no choice here was tuned on.

**Not tested, stated so no reader assumes otherwise:** no model of any kind; no MJO,
ENSO or PDO feature; no lag scan; no threshold sweep; no alternative swell variable
(`DECISIONS.md` Q27); no alternative station-combination rule (Q5, Q20). The mechanism
check's links (F4–F6) are **not** re-tested on held-out data either — they were exploratory
diagnostics and remain so.

### 8.2 The locked folklore rule

This is exactly what Phase 7 runs. Every value below is fixed here and none is recomputed,
tuned, or re-derived on held-out data.

**Predictor and pop definition.**

- Series: `buoy_51001_wvht_mean` from `analysis_daily` — the daily mean significant wave
  height at 51001. 51001, not 51101, for consistency with every exploration number and
  because 51101 does not exist for most of the record (Section 1.1, `DECISIONS.md` Q1/Q21),
  even though it does report in some held-out winters.
- **A pop day is a day with `buoy_51001_wvht_mean ≥ 3.9530 m`.** This is the 90th
  percentile of the exploration-winter distribution, frozen in `DECISIONS.md` Q16 before
  any pop–storm matching was run. **The fixed metre value is what carries over. The
  percentile is NOT recomputed on the held-out winters** — doing so would let the held-out
  distribution set its own threshold and would break the one-shot property.
- Why the 90th percentile and not another level of the sweep, by a rule declared in advance
  as Q16 requires: **abs_p90 was Phase 5a's pre-declared primary configuration**, fixed in
  `events.py` (`PRIMARY_POP_PERCENTILE = 90`) before any pop–storm matching ran, so choosing
  it now selects nothing new. It is also the strictest level that leaves a workable event
  count on a six-winter sample — 142 usable pop occasions over the 16 exploration winters
  against 87 at the 95th percentile, which would scale to roughly 30 on six winters. It is
  emphatically **not** the level that scored best: all nine swept thresholds came in below
  their own base rate (F2), so there was no best to pick.
- Undefined days: a day where the buoy did not report has **no pop flag** and is not an
  occasion on either row. Such days are counted and reported, never read as "no pop"
  (rule 2.5).
- **Pop events:** the daily pop flags are collapsed by `detect_events` with **bridge = 1
  day**, and each event is dated by its **first day**. A five-day swell is one pop, not
  five.

**Target and storm definition.**

- **A storm day is a day with `swe_gain_in ≥ 0.5` inches at at least 2 of the 5 Wasatch
  SNOTEL stations** — the `any2` combination rule at the **0.5-inch** threshold.
- Justification, and it is a detector argument made before the box was opened: Phase 5a
  measured 0.5-inch `any2` at 15.4 storm events per winter, inside the 15–30 a Wasatch
  winter plausibly contains, while 1.0 inch gives 6.9 and 1.5 inch gives 2.3 — both
  implausibly few (F1, Q26). The 1.0-inch convention detects a storm's biggest single day,
  not the storm. 0.5-inch `any2` is chosen because it is the honest description of a
  Wasatch storm, **not** because it flattered the folklore: at 1.0 inch the exploration
  result was flat, and at 0.5 inch it was flat too (F2).
- Missing stations: a station that is not reporting contributes nothing and is **not**
  filled in (rule 2.5). "At least 2 stations" means at least 2 of the stations actually
  reporting that day. All five stations were installed before the earliest held-out winter
  (Section 3.2 install dates, which are station metadata, not held-out data), so no
  held-out winter is expected to be short a station — but if any day is, it is handled by
  this rule and the count is reported.
- **Storm events:** the daily storm flags are collapsed by `detect_events` with **bridge =
  1 day**, each event dated by its **first day**.

**The prediction task, lead time and window.**

- The rule predicts a **binary event**: does a storm event *begin* in the window that
  follows a pop?
- **The window is 10 to 18 days after the pop event's first day, inclusive.** One window
  only. This is the folklore's own ~14-day claim, tested on its own terms with the same
  ±4-day tolerance Phase 5a used.
- **Secondary lags: none.** No lag scan, no neighbouring window, no "we also looked at".
  Exploration already scanned 0–30 days and found nothing (F3); re-scanning on six winters
  would be the multiple-comparisons trap the seal exists to prevent.

**The occasion and the comparison row** (this resolves `DECISIONS.md` Q25 for the locked
rule — the Phase 5a construction is **adopted deliberately**, not inherited):

- The unit is an **anchor day**. Every anchor asks the same question: does a storm event
  begin in [anchor + 10, anchor + 18]?
- **Pop occasions** are pop-event first days — one occasion per event.
- **Non-pop comparison occasions** are every other day of the same held-out winters lying
  outside every pop event. Days inside a pop event after its first day belong to neither
  row.
- Both rows require a defined pop flag and a window that fits inside the same winter. An
  occasion whose window would run past 30 April is dropped, not followed into May.
- Implementation: `contingency_from_flags` in `src/powderbuoy/events.py`, with
  `lag_lo = 10`, `lag_hi = 18`, `bridge = 1`, grouped by winter.

**Matching — both variants reported, neither privileged.**

- **With one-to-one claiming:** pops in date order each claim the earliest unclaimed storm
  event starting in their window; a claimed storm cannot count for a later pop. Conservative
  — one busy fortnight cannot manufacture several hits.
- **Without claiming:** each pop is scored independently.
- **Both are declared now and both are reported.** Neither is "the answer": the choice moved
  storm-rate-given-a-pop by roughly 0.06 on exploration data (Q25), which is too large a
  swing to settle by preference after seeing the result. The comparison row is scored
  without claiming in both variants — it is a base-rate reference, not a set of competing
  forecasts — and that asymmetry is stated here rather than hidden.

**Season definition** (this resolves `DECISIONS.md` Q19): **1 November to 30 April**,
each winter labelled by its starting year, unchanged. Every number in Phases 4, 5a and 5b
rests on this window; widening it now would change the unit the held-out result is compared
against and invalidate the exploration baseline. Not widened.

**Data access.** Phase 7 calls `load_analysis_data(include_holdout=True)`, the single
authorised use of that argument in the project, with an inline comment citing this
section and spec version 0.8. The six held-out winters are scored **on their own**: the
exploration winters are not pooled into the held-out tables, and their Phase 5a numbers are
quoted alongside only as the exploration comparison.

### 8.3 Metrics

Computed for the held-out winters, for **both** matching variants, from the 2×2:

|  | Storm began in window | No storm in window |
| --- | --- | --- |
| Pop occasion | a | b |
| Non-pop occasion | c | d |

**How the two variants fill that table, stated so Phase 7 has nothing to interpret.** The
comparison row is identical in both: `c` = non-pop occasions whose window contains at least
one storm start, `d` = the rest. The pop row differs only in how `a` is counted. *With
claiming:* `a` = pops that successfully claim a storm, taking pops in date order, each
claiming the earliest storm start in its window that no earlier pop has claimed. *Without
claiming:* `a` = pops whose window contains at least one storm start, regardless of any
other pop. In both variants `b` = (usable pop occasions) − `a`. Every metric below is then
computed twice, once from each table.

- **Storm rate given a pop** = `a / (a + b)` — the folklore's own claim.
- **Base rate** = `(a + c) / (a + b + c + d)` — reported **beside it, in the same table and
  the same sentence, always** (rule 2.2). No hit rate appears anywhere without it.
- **Ratio** = storm-rate-given-a-pop ÷ base rate. This is the number the verdict in 8.4 is
  read from.
- **POD** (probability of detection) = `a / (a + c)`.
- **POFD** (false alarm rate) = `b / (b + d)`.
- **PSS** (Peirce skill score / Hanssen–Kuipers) = `POD − POFD` = `a/(a+c) − b/(b+d)`.
  0 is chance, 1 perfect, negative worse than chance. Its **magnitude** is bounded by how
  rare pops are in this occasion design (Q25) and is not comparable across studies; its
  **sign** is what 8.4 uses.
- **Counts reported alongside every table, without exception:** number of pop events,
  number of usable pop occasions, number of non-pop occasions, number of storm events, and
  the number of days with an undefined pop flag (buoy not reporting).

**Baselines, defined precisely.**

- **Climatology** is the base rate above: the storm rate over the non-pop comparison
  occasions drawn from the *same six held-out winters*, so the comparison holds season,
  calendar and storm definition fixed and varies only whether a pop preceded the window.
  This is the only baseline the verdict uses.
- **Persistence** is **not applicable and is not reported.** A persistence forecast repeats
  the current state; at a 10–18 day lead over a binary event with no autocorrelation at that
  range it degenerates to climatology, and the folklore rule issues no probability to
  compare against. Recorded as a deliberate omission so its absence is not read as an
  oversight.
- **Cross-validation is not applicable.** Nothing is fitted: the rule has no free parameters
  left — the threshold, the window, the storm definition and the matching variants are all
  fixed in 8.2. There is no in-sample tuning for cross-validation to protect against. (The
  leave-one-season-out scheme that *would* have applied to the models is recorded in 8.6.)

### 8.4 The verdict, stated as numbers before unsealing

Let **R** = storm-rate-given-a-pop ÷ base rate, and **PSS** as defined above, each computed
under both matching variants. Define, per variant, the condition
**S = (R ≥ 1.20 AND PSS > 0)**.

- **NULL CONFIRMED — the expected outcome.** S holds for **neither** variant. The buoy pop
  does not raise the odds of a Wasatch storm 10–18 days later beyond the base rate on
  winters no choice in this study was tuned on. This confirms the Phase 5 null out of
  sample and is a complete, successful result (Section 1).
- **SURPRISING — flagged, not celebrated.** S holds for **both** variants. This would be
  recorded as a **discrepancy warranting caution, and explicitly NOT as vindication of the
  folklore.** Six winters standing against a flat 16-winter exploration is more likely
  small-sample noise than a signal exploration missed, and the honest reading would be "the
  held-out winters disagree with exploration and we do not know why". It would license a
  fresh, separately-designed study — never a re-run of this one (8.5).
- **SPLIT — inconclusive, leaning null.** S holds for exactly one variant. Reported as
  inconclusive with both variants' numbers shown; **not** reported as skill. If the two
  matching rules disagree, the result is a statement about the matching rule, not about the
  buoy.

These three cases are exhaustive and mutually exclusive. Whichever occurs, the numbers are
reported in full.

**The honest limit, written down before the number is seen so it cannot be rationalised
afterwards.** Six winters give a **directional** answer, not a precise one. Scaling
exploration's own rates forward, six winters should yield roughly 50 usable pop occasions
(abs_p90 gave 142 over 16 winters) and roughly 90 storm events (0.5-inch `any2` gave 15.4
per winter) — dozens of events, not thousands, and autocorrelated ones at that
(`DECISIONS.md` Q17). Those figures are an expectation derived from exploration, not a
measurement of the held-out set. **Consequences, accepted in advance:** no confidence
interval computed on this sample will be narrow; a ratio near 1.0 cannot be distinguished
from a ratio of 1.15; and the result must be reported as "consistent with / inconsistent
with the exploration null", never as a precise effect size. The held-out set was sized by
the buoy's archive gap (Q13/Q21), and this limitation was accepted knowingly at Phase 4.

### 8.5 The held-out winters, and the one-shot rule

**The six held-out winters, restated from `DECISIONS.md` Q13 and unchanged:**

> **2004, 2005, 2006, 2008, 2021, 2022**

(Winters are labelled by starting year: winter 2004 is Nov 2004 – Apr 2005.) The sixteen
exploration winters are 1989, 1990, 1992, 1994, 1996, 1998, 1999, 2000, 2001, 2003, 2015,
2016, 2017, 2018, 2019, 2020. The three folklore-only winters (2023, 2024, 2025) are in no
split and are **not** used in Phase 7 — adding them would mix a differently-constituted
sample into the one-shot result.

**One shot.** This set is evaluated **exactly once**, against this section as written. If
the result is disappointing and anything is then changed and re-run — threshold, window,
storm definition, matching rule, station set, or the winters themselves — **the seal is
burned and every subsequent number is EXPLORATORY and may never be reported as a
conclusion** (rule 2.3). It cannot be re-sealed. Every unsealing, including failed or
abandoned ones, is recorded in `DECISIONS.md`.

Phase 7 must also: write one row to the experiment register (Section 9) with
`used_holdout = True`, `target_definition` citing this section at spec version 0.8, and
`status = CONFIRMED`; record the git commit the run was made from; and state in its report
that the run is the project's single authorised use of the held-out set.

### 8.6 What the model protocol would have been — recorded, not executed

Kept so that Section 7 closes honestly rather than looking unfinished, and so a future
reader can see the comparison was designed and then deliberately declined, not forgotten.

Had the Stage 3 gate opened, Phase 7 would have scored four models — **A** day-of-year only
(climatology floor), **B** MJO + ENSO + day-of-year, **C** buoy + day-of-year, **D** buoy +
MJO + ENSO + day-of-year (Section 7) — on identical data, identical splits and identical
scoring, differing only in features. Fitting and selection would have run inside the 16
exploration winters under **leave-one-season-out** cross-validation (never `KFold` with
`shuffle=True`, rule 2.1), with the held-out winters scored once at the end. Scoring would
have been the **Brier score** for the probability forecasts, plus PSS at a declared
operating threshold, each reported against model A as the climatology baseline (rule 2.2),
and calibration inspected before any skill claim. Model choice would have started at
logistic regression and stopped at gradient boosting; no neural network, at 22 usable
winters (Section 11.1).

**It is not run.** Two independent reasons, both on record before this section was written:
the gate condition was not met (F3), and the premise behind model D was measured and found
weak — buoy swell tracks MJO phase in the right direction but at only 0.18 sd, so C-vs-D
separation on MJO content was never plausible at this sample size (F4, Q17). Reviving this
comparison would require a fresh planning decision and a new sealed set; it is not something
Phase 7 may reach for if the folklore result is dull.

---

## 9. Experiment register

Every **scored run — model or rule-based** — appends one row to
`outputs/experiments/register.csv`. No exceptions. The Phase 7 folklore-rule run has no
model and is not an exception to this: it is a scored run, it touched the held-out set, and
the register is the only audit trail of what did (SPEC 8.5).

| Column | Notes |
| --- | --- |
| run_id | UUID |
| timestamp | UTC |
| git_commit | Hash of the working tree |
| model_name | A, B, C, D, a variant label, or the name of a scored rule |
| features | Explicit list |
| train_seasons, test_seasons | Explicit lists, not ranges |
| used_holdout | Boolean. True only for the single Phase 7 run |
| target_definition | Reference to the Section 8 protocol version, or "exploratory" |
| primary_metric, primary_value | |
| baseline_value | Never null (rule 2.2) |
| status | EXPLORATORY or CONFIRMED |
| notes | |

This is the equivalent of a trade log. It exists so that six months later nobody has to
remember which run produced which number.

---

## 10. Working practices

### 10.1 Division of work

Planning, analysis, research, and session prompt files are produced in conversation
with the owner. All code is written directly into the project by Claude Code, working
from a session prompt file. Nothing is drafted in chat and pasted in.

### 10.2 Session discipline

One session, one scope. Claude Code implements exactly what the session prompt defines
and nothing more. If something outside scope looks broken or worth doing, it is logged
in `DECISIONS.md` as an open question, not fixed.

### 10.3 Git

Claude Code never commits. It prepares changes, outputs the commit message, and the
owner reviews and commits by hand.

### 10.4 Validation

Every session ends by running its validation steps and pasting real output. Not a
description of what would happen. Actual numbers.

### 10.5 Consistency check

Before writing the commit message, every session must re-read `SPEC.md`, `STATUS.md`
and `DECISIONS.md` and report any place where two entries disagree, any duplicated
section heading, and any findings-log entry out of version order.

**Report only. Do not fix silently.** The owner decides.

### 10.6 Notebooks

Notebooks are for exploration. A number that appears in a finding must come from a
script, not a notebook.

---

## 11. Out of scope

Recorded so that no session drifts into these.

- Regions other than Utah
- Live or real-time forecasting
- Notifications or alerting
- Any European or non-NDBC data source
- Snow quality or powder-quality prediction
- Avalanche forecasting of any kind

### 11.1 Deferred, not excluded

- **Dashboard or web app.** Decided after Phase 7. Only worth building if the answer is
  interesting. A dashboard that displays "this does not work" is not worth the time.
- **Neural networks.** Not justified at the data volume available here, and
  interpretability matters more than raw fit. Session 0A measured the record as two eras
  either side of the 2010–2014 buoy gap rather than one unbroken ~40-winter span, and
  once MJO coverage is required for the four-model comparison only 22 winters are usable
  (Section 7; `DECISIONS.md` Q13/Q21) — an order of magnitude short of what a neural
  network would need. Would take a specific argument to revisit.

---

## 12. Glossary

| Term | Meaning |
| --- | --- |
| SWE | Snow water equivalent. Water depth if the snowpack were melted |
| SNOTEL | USDA network of automated snow measurement stations |
| NDBC | NOAA National Data Buoy Center |
| WVHT | Significant wave height. Mean height of the highest third of waves |
| DPD | Dominant wave period. Seconds between the most energetic waves |
| MWD | Mean wave direction. Direction waves come from, in degrees |
| MJO | Madden–Julian Oscillation. Eastward-moving tropical convection, 30–60 day cycle |
| RMM | Real-time Multivariate MJO index. Two daily numbers describing MJO state |
| ENSO | El Niño Southern Oscillation |
| Base rate | How often the thing happens anyway, with no prediction |
| Skill score | How much better than a baseline, on a scale where 0 is no better |
| Brier score | Mean squared error of probability forecasts. Lower is better |
| Leakage | Test information reaching the model during training. Produces fake scores |
| Buoy pop | Folklore term for a sudden rise in wave height |
| Target | The thing the model predicts, and the thing we score against |
| Held-out set | Winters sealed away, untouched until the protocol is locked |
| Exploration set | Winters you may look at freely. All choices are made here |
| Multiple comparisons | Testing many options until one looks good by chance. The trap the held-out set prevents |
| Contingency table | A 2×2 count of predicted versus observed. The simplest honest forecast test |
| Probability of detection (POD) | Of all storms, the fraction preceded by a pop. Also called hit rate |
| False alarm rate (POFD) | Of all non-storm outcomes, the fraction preceded by a pop |
| Storm rate given a pop | Of all pops, the fraction actually followed by a storm |
| Peirce skill score | POD minus false alarm rate. 0 is chance, 1 is perfect, negative is worse than chance |
| Calibration | Whether a "70% chance" forecast is right about 70% of the time |
