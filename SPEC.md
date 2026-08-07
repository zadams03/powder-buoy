# SPEC.md — Powder Buoy

**Version: 0.3**
**Status: Phase 0 in progress — repo scaffold, NDBC ingest, and SNOTEL ingest complete (Session 0B)**

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

Since roughly 2004, a community of Utah skiers has tracked NOAA buoy 51101, a
3-metre discus buoy a few hundred kilometres northwest of Kauai. The rule they use is:

> When wave height spikes ("a buoy pop"), the Wasatch mountains get a storm about two
> weeks later. Bigger pop, bigger storm.

Claimed accuracy is around 80%, self-reported, over small samples, with no baseline
quoted. No published study of the claim exists.

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
`DECISIONS.md` Q1 and Q17).

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

All processed tables are daily, indexed by date, in UTC.

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

| Column | Type | Notes |
| --- | --- | --- |
| date | date | |
| rmm1, rmm2 | float | MJO components |
| mjo_phase | int | 1–8 |
| mjo_amplitude | float | sqrt(rmm1² + rmm2²) |
| nino34 | float | Monthly value, forward-filled within the month, flagged as such |
| pdo | float | Monthly, same treatment |

### 5.4 `analysis_daily`

The joined table everything downstream reads. One row per day. Buoy columns, snow
columns aggregated across stations, climate columns, and derived features.

---

## 6. Phases

| Phase | Goal | Reads held-out? | Status |
| --- | --- | --- | --- |
| 0 | Repo scaffold, config, environment | n/a | Not started |
| 1 | NDBC buoy ingest and cleaning | n/a | Not started |
| 2 | SNOTEL snow ingest and cleaning | n/a | Not started |
| 3 | Climate index ingest, build `analysis_daily` | n/a | Not started |
| 4 | **Split seasons.** Seal the held-out set | No | Not started |
| 5 | **Exploration.** Contingency tables, then lag scan, then gated modelling (6.1) | No | Not started |
| 6 | **Lock evaluation protocol** (Section 8) | No | Not started |
| 7 | **Held-out evaluation.** Folklore rule and four models, run once | Yes, once | Not started |
| 8 | Write-up. Dashboard decision (11.1) | — | Not started |

Phases 0 to 3 are data engineering. No analysis happens in them, so the seal is not at
risk.

Phase 4 makes exactly one decision: which winters go in the box. Nothing else.

Phase 5 is deliberately unconstrained. Every number it produces is EXPLORATORY. Its job
is to decide what Phase 6 will commit to. See Section 6.1 for the order of work within
it, which is not optional.

Phase 6 writes Section 8 and freezes it.

Phase 7 unseals the held-out set and runs once. Both the folklore rule and the
four-model comparison are scored here, against the same locked protocol.

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

Two rates matter, and they must not be confused:

- **Probability of detection (POD)** = `a/(a+c)` — of all storms, how many followed a
  pop. This is the "hit rate" in the forecast-verification sense.
- **False alarm rate (POFD)** = `b/(b+d)` — of all non-storm outcomes, how many were
  preceded by a pop, i.e. false alarms.

Also report, next to each other and always (rule 2.2):

- **Storm rate given a pop** = `a/(a+b)` — how often a pop is actually followed by a
  storm.
- **Base rate** = `(a+c)/(a+b+c+d)` — how often a storm happens at all.

The buoy has skill only if the storm rate given a pop clearly exceeds the base rate.

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
probability. Then gradient boosting (LightGBM). No neural networks — the usable record
is at most around 40 winters (to be confirmed in Session 0A, and fewer if 51001 proves
unusable), far too little for a neural network, and interpretability matters more than
raw fit here.

---

## 8. Evaluation protocol — LOCKED IN PHASE 6

> **This section is empty by design.**
>
> It is filled during Phase 6, after exploration (Phase 5) and before the held-out set
> is unsealed (Phase 7). Once filled it is frozen (see rule 2.3).
>
> A session that tries to fill this section before Phase 6 is a red flag. Stop and
> raise it with the owner.
>
> It must define, with no ambiguity:
>
> - The target. Exact definition of "a storm day", including the SWE threshold, how
>   stations are combined, and how missing stations are handled
> - The prediction task. What is predicted, at what lead time, over what window
> - The single primary lag window, and the justification drawn from Phase 5
> - Any secondary lags reported, declared here rather than chosen later
> - Baselines. Climatology and persistence, defined precisely
> - Metrics. Primary and secondary, with the skill score formula written out
> - The exact held-out seasons, restated from the Phase 4 split
> - Cross-validation scheme within the exploration seasons
> - What result would count as the buoy having skill, and what would count as it not
>   having skill. Both stated as numbers, before unsealing

---

## 9. Experiment register

Every model run appends one row to `outputs/experiments/register.csv`. No exceptions.

| Column | Notes |
| --- | --- |
| run_id | UUID |
| timestamp | UTC |
| git_commit | Hash of the working tree |
| model_name | A, B, C, D, or a variant label |
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
- **Neural networks.** Not justified at the data volume available here — at most around
  40 winters, confirmed in Session 0A — and interpretability matters more than raw fit.
  Would need a specific argument to revisit.

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
