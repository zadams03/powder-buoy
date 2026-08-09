# STATUS.md — Powder Buoy

**Spec version: 0.6**
**Last updated: Session 5a, 2026-08-09**

This file holds current state. It changes every session.
Stable specification lives in `SPEC.md`. Open questions and findings live in
`DECISIONS.md`.

---

## 1. Current state

Repo scaffold, NDBC buoy ingest, SNOTEL snow ingest, climate index ingest,
`analysis_daily`, and the season split are all complete. Phases 0–4 are done, and Phase 5
Stages 1–2 (contingency tables and the lag scan) have now run on the exploration winters.
Stage 3 (modelling) is **gated** and was not started. Next is the **gate review** — a
planning conversation, not a session.

| Item | State |
| --- | --- |
| Repo scaffold | **Done (0A)** |
| NDBC ingest | **Done (0A)** — `buoy_daily.parquet`, stations 51001 and 51101 |
| SNOTEL ingest | **Done (0B)** — `snow_daily.parquet`, 5 Wasatch stations |
| Climate index ingest | **Done (0C)** — `climate_daily.parquet`, MJO/ENSO/PDO |
| `analysis_daily` join | **Done (0C)** — `analysis_daily.parquet`, dumb full outer join |
| Season split (exploration vs held-out) | **Done (0D)** — see `DECISIONS.md` Q13 |
| Phase 5 Stage 1 — contingency tables | **Done (5a)** — `src/powderbuoy/events.py`, all EXPLORATORY |
| Phase 5 Stage 2 — lag scan 0–30 | **Done (5a)** — all EXPLORATORY |
| Phase 5 Stage 3 — modelling | **GATED, not started** — pending the joint gate review |
| Evaluation protocol (SPEC Section 8) | Empty — locked in Phase 6 |
| Models | Not started (gated) |
| Experiment register | Not created — no model run has happened yet |

**Phase 5a outputs:** `outputs/phase5a_counting_report.txt`, and four figures under
`outputs/figures/` — `storm_detector_check_2016.png`, `dose_response_curve.png`,
`lag_scan_pss.png`, `lag_scan_pss_zscore.png`. Every number in them is EXPLORATORY
(rule 2.3) and none may be reported as a conclusion.

**Data on disk:** `data/processed/buoy_daily.parquet` (22,919 rows, stations 51001 and
51101); `data/processed/snow_daily.parquet` (65,618 rows, 5 Wasatch SNOTEL stations);
`data/processed/climate_daily.parquet` (18,166 rows, 1974-06-01 to 2024-02-24);
`data/processed/analysis_daily.parquet` (19,060 rows, 1974-06-01 to 2026-08-06). Raw
archive/response files under `data/raw/` (gitignored).

**Held-out seal: SEALED, 2026-08-08.** Six winters sealed as the held-out (test) set:
**2004, 2005, 2006, 2008, 2021, 2022**. Sixteen winters form the exploration set: 1989,
1990, 1992, 1994, 1996, 1998, 1999, 2000, 2001, 2003, 2015, 2016, 2017, 2018, 2019, 2020.
Three winters (2023, 2024, 2025) are set aside as folklore-only (no complete MJO
coverage) and are never part of the split. Full reasoning in `DECISIONS.md` Q13. Enforced
in code by `powderbuoy.seasons.load_analysis_data`, which excludes held-out winters by
default (`include_holdout=False`).

---

## 2. Next session

### The gate review — a planning conversation, not a session

Stages 1 and 2 have run. The next step is **not** a Claude Code session. It is a joint
review of what the counting showed, which decides one thing:

**Is Stage 3 (modelling) warranted?** SPEC 6.1's gate condition is that Stage 2 must show
positive skill at some lag, in a coherent band of adjacent lags, surviving sensitivity to
pop definition and SWE threshold.

- **If the gate opens:** Phase 5b (modelling) follows, with its own session prompt.
- **If it does not:** Phase 5 ends at Stage 2, and Phase 6 locks a protocol that expects
  a null result — which SPEC Section 1 states plainly is a complete and successful
  outcome.

The review reads `outputs/phase5a_counting_report.txt` and the four figures, plus the
Stage 1 / Stage 2 findings in `DECISIONS.md` Section 2. It should weigh the detector
caveats from Part 4 (the 1-inch threshold produces fewer events per winter than a Wasatch
winter plausibly contains) alongside the skill numbers, since the storm definition is
still open (Q6).

Open questions carried into Phase 6: Q5, Q6, Q8, Q15, Q17, Q18, Q19, Q20, Q23, Q24, Q25,
Q26 (see `DECISIONS.md`). Every Phase 5 number is EXPLORATORY (rule 2.3) — none of it may
be reported as a conclusion.

**Explicitly not in the next session:** reading, printing, or scoring anything from the
six held-out winters; filling SPEC Section 8 (that is Phase 6); building any model before
the gate review decides.

---

## 3. Build log

Newest entry at the top. One row per completed session.

| Session | Spec version | Date | Summary |
| --- | --- | --- | --- |
| 5a | 0.5 → 0.6 | 2026-08-09 | Phase 5 Stages 1–2 — the first look at whether the buoy carries signal, by counting. Added `src/powderbuoy/events.py`: `detect_events()` collapses an autocorrelated daily boolean series into discrete events (consecutive days are one event, a 1-day gap is bridged, each event dated by its first day, and bridging is measured in calendar days so two winters never merge); `contingency_from_flags()` builds the 2×2 over anchor-day occasions and scores POD / POFD / PSS beside the base rate. Pop definitions frozen as **sweeps** in `DECISIONS.md` Q16 **before** any matching (via `--calibrate-only`): absolute percentiles 50/75/85/90/95 → 2.7333 / 3.3111 / 3.6718 / 3.9530 / 4.4862 m, and z-score 0.5/1.0/1.5/2.0 sd over a trailing 30-day within-winter mean. Storm thresholds 0.5/1.0/1.5 in, per-station and combined (`any2`, `mean`). Storm detector validated three ways: per-winter counts (0.5 in `any2` gives 15.4 events/winter, in the plausible 15–30 band; 1.0 in gives 6.9 and 1.5 in gives 2.3 — both flagged, reported not fixed, new Q26), an eyeball plot against the 2016 SWE curve (every mark on a real step-up; one slow-accumulation storm missed), and an independent precipitation cross-check (**111 of 111** SWE-detected storm events coincide within ±1 day with a positive precipitation increment at ≥2 stations = 1.0000). Stage 1: 54 configurations, plus a 45-row per-station view for Q20. Stage 2: lag scan 0–30 for all 9 pop definitions. Four figures written. **No model built** — Stage 3 stays gated. Exploration winters only (16); `include_holdout` never set True; folklore-only winters deliberately not used, so every number rests on the same 16 winters. `tests/test_events.py` added (15 tests): event collapse, bridging, no cross-winter merging, one-to-one claiming both ways, window-fits-in-winter, noise → PSS ≈ 0, a perfect predictor → PSS > 0, percentile sweep resolution, NA-not-False, and no look-ahead in the trailing z-score. All 38 tests pass. Housekeeping: SPEC 11.1 two-era nuance (H1), SPEC 6.0 decision-resolved note (H2), STATUS Section 5 blockers past tense (H3); all three headers bumped to 0.6. |
| 0D | 0.4 → 0.5 | 2026-08-08 | Phase 4, the season split — a decision session, not a build session. The exploration/held-out/folklore-only winter lists (decided in planning, Option D — chronological within each era) written into `config/regions/utah.yaml` as explicit lists. Added `src/powderbuoy/seasons.py`: `winter_of()` labels a date's winter start-year, and `load_analysis_data()` loads `analysis_daily` filtered to configured winters with the held-out set **excluded by default** — the seal enforced in code (rule 2.3), not just intent. Held-out (test) winters **SEALED**: 2004, 2005, 2006, 2008, 2021, 2022. Exploration: 1989, 1990, 1992, 1994, 1996, 1998, 1999, 2000, 2001, 2003, 2015–2020 (16 winters). Folklore-only (no complete MJO, never part of the split): 2023–2025. `tests/test_seasons.py` added (8 tests): winter labelling, default excludes held-out, `include_holdout=True` reveals exactly those six, no double-labelling, and loader/config agreement. No correlation, lag scan, contingency table, or model was run; no held-out values were read at any point — only year labels and row counts. Housekeeping: `DECISIONS.md` header bumped to 0.5 (H1); SPEC Section 7 tense fixed and folded in the two-era/22-usable-winters nuance from Q21 (H2). |
| 0C | 0.3 → 0.4 | 2026-08-07 | Climate index ingest (`src/powderbuoy/ingest/climate.py`) — BoM RMM MJO (daily), NOAA CPC ONI/Niño 3.4 and NOAA NCEI PDO (monthly) → `climate_daily.parquet` (18,166 rows, 1974-06-01 to 2024-02-24). Monthly ENSO/PDO attached with a one-month availability lag and `_is_ffilled` flags — no within-month look-ahead (`DECISIONS.md` Q10 resolved). `mjo_method` column flags the BoM 2013/2014 calculation-method seam (new `DECISIONS.md` Q23), computed from date, not trusted from the source file's own per-row label. Built `analysis_daily.parquet` (19,060 rows, 1974-06-01 to 2026-08-06) — a dumb full outer join of buoy, all 5 snow stations (kept separate), and climate on `date`; buoy's 2010–2014 gap confirmed fully preserved (1,826 of 1,826 window-days null), no snow combination, no storm/target column. This completes Phases 0–3 (all data engineering); next is Phase 4. Housekeeping: SPEC Section 6 phases table's dead Status column removed (tracked in STATUS.md instead); SPEC Section 5's opening timezone line reworded to state each table's native timezone explicitly; SPEC 5.3/5.4 updated to match the tables actually built. |
| 0B | 0.2 → 0.3 | 2026-08-07 | SNOTEL snow ingest via the NRCS AWDB REST API for 5 confirmed Wasatch stations (Snowbird, Brighton, Mill-D North, Thaynes Canyon, Louis Meadow) → `snow_daily.parquet` (65,618 rows). All validation checks passed. Every station's daily record is 100% complete from its install date to present — no gaps at all in this source, unlike the buoy. 25 winters have both buoy (51001) and snow (≥2 stations) at `good` coverage — the usable-sample preview for Phase 4. Housekeeping: `apd_mean` added to SPEC 5.1 (Q22), Q1 wording softened, Q2 closing note added. |
| 0A | 0.1 → 0.2 | 2026-08-07 | Repo scaffold, uv environment, config system, NDBC ingest for 51001 and 51101 → `buoy_daily.parquet` (22,919 rows). All validation checks passed; cross-buoy correlation 0.98. Discovered a 2010–2014 gap in 51001's archive (5+ winters with no data) — see `DECISIONS.md` Q21. |

---

## 4. Known data state

Filled in as ingest sessions complete.

| Table | Rows | Date range | Gaps | Last refreshed |
| --- | --- | --- | --- | --- |
| buoy_daily | 22,919 (51001: 16,395; 51101: 6,524) | 51001: 1981-02-11 to 2025-12-31; 51101: 2008-02-21 to 2025-12-31 | 51001: 3,633 gap days (22.2%), longest 2,068 days (2009-12-25 to 2015-08-23); 51101: 651 gap days (10.0%), longest 409 days (2008-03-08 to 2009-04-20) | 2026-08-07 |
| snow_daily | 65,618 (Snowbird 13,498; Brighton 14,562; Mill-D North 13,824; Thaynes Canyon 13,927; Louis Meadow 9,807) | Per station, install date to 2026-08-06 (see SPEC 3.2 for install dates) | 0 null `swe_in` days at any of the 5 stations — full record complete from install to present | 2026-08-07 |
| climate_daily | 18,166 | 1974-06-01 to 2024-02-24 | 290 null `rmm1`/`rmm2`/`mjo_phase` days (1.6%) within the daily MJO calendar; 0 null `nino34` or `pdo` days across this range (both monthly sources cover it comfortably once the one-month lag is applied) | 2026-08-07 |
| analysis_daily | 19,060 | 1974-06-01 to 2026-08-06 | Ragged by source, as intended: buoy 51001 present 12,432 of 19,060 days (incl. the 2010–2014 gap, fully preserved — 1,826 of 1,826 window-days null); snow (Snowbird) present 13,498 of 19,060; MJO present 17,876 of 19,060. No gap filled | 2026-08-07 |

### 4.1 Resolved pop thresholds (Phase 5a — frozen, `DECISIONS.md` Q16)

Calibrated from marginal distributions only, on the 16 exploration winters (2,900 winter
days, of which 2,840 have a defined `buoy_51001_wvht_mean`; mean 2.862 m, sd 0.870 m).
Written to `DECISIONS.md` **before** any pop–storm matching was run. No single operating
threshold is chosen — that is a Phase 6 decision, and must be made by a rule declared in
advance rather than by picking the highest-skill point.

| Pop definition | Threshold | Resolved value | Flagged share of defined days | Defined days |
| --- | --- | --- | --- | --- |
| Absolute | 50th percentile | **2.7333 m** | 0.5007 | 2,840 |
| Absolute | 75th percentile | **3.3111 m** | 0.2500 | 2,840 |
| Absolute | 85th percentile | **3.6718 m** | 0.1500 | 2,840 |
| Absolute | 90th percentile | **3.9530 m** | 0.1000 | 2,840 |
| Absolute | 95th percentile | **4.4862 m** | 0.0500 | 2,840 |
| Z-score | 0.5 sd | 0.5 sd over trailing 30-day mean | 0.2648 | 2,515 |
| Z-score | 1.0 sd | 1.0 sd over trailing 30-day mean | 0.1527 | 2,515 |
| Z-score | 1.5 sd | 1.5 sd over trailing 30-day mean | 0.0855 | 2,515 |
| Z-score | 2.0 sd | 2.0 sd over trailing 30-day mean | 0.0457 | 2,515 |

The z-score rows have 2,515 defined days rather than 2,840 because the trailing window is
computed within each winter, so the first ~20 days of every winter have no z-score. Those
days are excluded from the sample and counted, never read as "no pop" (Q24).

---

## 5. Blockers

None. One limitation carried forward: 51001's 2010–2014 archive gap shortened the usable
continuous record materially below the "~40 winters" planning assumption — see
`DECISIONS.md` Q21 and SPEC Section 6.0. This was the decision point Phase 4 faced and
resolved: the record is treated as two eras either side of the gap, 22 winters are usable
once MJO coverage is required, and the held-out set is six winters rather than a larger
one (`DECISIONS.md` Q13/Q21). It is now a recorded, accepted limitation on the strength
of the Phase 7 conclusion, not an open decision.

---

## 6. Consistency check log

Every session reports contradictions found across the three files. Logged here,
resolved by the owner.

**Standing practice, effective this session (0D):** every session bumps all three file
headers (`SPEC.md`, `STATUS.md`, `DECISIONS.md`) to match whenever `SPEC.md`'s version
changes, as one of its routine file updates — not something that has to be re-requested
in each session prompt.

| Session | Contradiction found | Resolution |
| --- | --- | --- |
| 0A | SPEC.md Section 5.1 `buoy_daily` schema does not list an `apd_mean` column, but the Session 0A prompt's Step 5 output-schema table — which states it is "matching SPEC Section 5.1" — includes one. Implemented with `apd_mean` included, following the more detailed session-prompt table. | **Resolved (0B, H1).** `apd_mean` added to SPEC 5.1. DECISIONS.md Q22 marked Resolved. |
| 0A | SPEC 3.1 and the Session 0A prompt's file-era table describe three formats, with "2005 onward" given two header lines and `WDIR`/`PRES` naming. Actual NDBC files show a fourth, transitional format for 2005–2006 (minute column added, but still one header line, still `WD`/`BAR` naming) — the two-header-line/`WDIR`/`PRES` format only starts in 2007. Additionally, the year column is labelled `YY` both pre-2000 (true 2-digit) and from 2007 onward (already 4-digit) — the column name does not indicate digit width. The parser detects both by content (header line count, `#` prefix, year magnitude), so results are unaffected, but the planning documents' description of the eras was incomplete. | **Resolved (0B, H2).** Owner has accepted 0A's corrected SPEC 3.1 text as final; no further edit needed. |
| 0A | `DECISIONS.md` Q1's resolution reasons that 51001 gives "the extra 27 years" over 51101. With the newly discovered 2010–2014 archive gap, a meaningful slice of that extra span has no data, so the "27 years" framing overstates the continuous-record advantage even though the underlying decision (51001 as primary) is unaffected — the 0.98 correlation check still confirms it. | **Resolved (0B, H3).** Q1 wording softened to "a longer record — roughly two usable decades, though with a five-year gap (2010–2014, see Q21)." Decision itself unchanged. |
| 0B | SPEC Section 6's phases table still shows Phases 0, 1, and 2 as "Not started" in the Status column, even though this file's Section 1 confirms all three are done (repo scaffold, NDBC ingest, SNOTEL ingest). SPEC's own top-of-file status line is updated each session, but the Section 6 table's per-phase Status column is not — neither 0A nor 0B's instructions asked for it. | **Resolved (0C, H1).** Status column removed from SPEC Section 6's phases table entirely; a note now points to STATUS.md as the single place phase status is tracked. |
| 0B | SPEC Section 5's opening line states "All processed tables are daily, indexed by date, in UTC," but Section 5.2's own `snow_daily` row says `date` is the "Local observation date," and `DECISIONS.md` Q12 (resolved this session) confirms `snow_daily.date` is deliberately kept on its native Pacific Standard Time day and never shifted to UTC. The opening line is inaccurate for `snow_daily`. | **Resolved (0C, H2).** Opening line reworded to state each table keeps its own native timezone, documented per table, and that `date` is not a globally aligned instant. |
| 0B | Minor, not a contradiction: `STATUS.md` Section 5 (Blockers) still frames the 51001 2010–2014 gap risk as "Not a blocker for Session 0B" — phrasing now stale since 0B is complete and the next session is 0C. Left as-is per the instruction to report, not fix, outside this session's listed file-update scope. | **Resolved (0C, H3).** Reworded to refer to "data-engineering sessions" generally rather than naming 0B specifically. |
| 0C | `DECISIONS.md`'s own header still reads "Spec version: 0.3" after this session bumped `SPEC.md` to 0.4 (and `STATUS.md`'s header to match). The Session 0C prompt's File-updates checklist for `DECISIONS.md` listed Q10/Q23 and new open questions but did not mention this header line, so it was not touched, and now disagrees with the other two files' headers. | **Resolved (0D, H1).** `DECISIONS.md` header bumped to 0.5, matching `SPEC.md` and `STATUS.md`. Going forward, "bump all three file headers" is a standard step every session takes, not something each session prompt must separately remember to ask for — noted below. |
| 0C | Pre-existing, not introduced this session: SPEC Section 7 still reads "the usable record is at most around 40 winters (**to be confirmed** in Session 0A...)" — future tense — while Section 11.1 reads "at most around 40 winters, **confirmed** in Session 0A" — past tense, for the same fact. Session 0A ran and did measure this (with the 2010–2014 gap complication, `DECISIONS.md` Q21), so Section 7's phrasing is stale relative to Section 11.1 and to SPEC 3.1's own "Measured in Session 0A" text. Neither Section 7 nor 11.1 was in this session's file-update scope. | **Resolved (0D, H2).** Section 7 reworded to past tense, aligned with 11.1 and 3.1, and now folds in the Q21 nuance directly: the confirmed record is two eras either side of the 2010–2014 gap, giving 22 usable winters once MJO coverage is required (Phase 4's split, Q13/Q21). |
| 0D | **New.** H2 reworded SPEC Section 7 to state the two-era, 22-usable-winter picture, but Section 11.1 still reads only "at most around 40 winters, confirmed in Session 0A" with no mention of the gap or the two eras — the two sections again describe the same fact differently, one level less starkly than the 0C finding above (both are now past-tense, but only 7 has the nuance). Session prompt's H2 scope named Section 7 only, not 11.1. | **Resolved (5a, H1).** SPEC 11.1's neural-networks bullet reworded to carry the same two-era, 22-usable-winter picture as Section 7, pointing to Q13/Q21, and no longer states "at most around 40 winters". |
| 0D | **New.** SPEC Section 6.0 ("Dependency on Session 0A — the record-length risk") still frames Plan B as a live, unmade decision — "If we land here, **that is a decision point**... either accept weaker conclusions... or pause and reconsider scope" — but Phase 4 has now made exactly that call (Q13/Q21: proceed with a two-era, 22-winter record and a 6-winter held-out set, accepting the limitation rather than pausing). Section 6.0 was not in this session's file-update scope. | **Resolved (5a, H2).** SPEC 6.0 keeps the risk description for future readers and gains a closing paragraph recording that the decision point was reached and resolved by the Phase 4 split (Q13/Q21) — and that neither of the two stated failure modes is what materialised (correlation held at 0.98; the reposition question could not be checked at all, Q2). |
| 0D | **New.** This file's own Section 5 (Blockers) still reads "...a live decision point when Phase 4 splits seasons" — but Phase 4 is now the session that just ran; the decision is made, not live. Same pattern as the 0B→0C staleness already resolved once in this section. Section 5 was not in this session's file-update scope (only 1, 2, 3, 6 were). | **Resolved (5a, H3).** Section 5 reworded to past tense: the gap "was the decision point Phase 4 faced and resolved", now a recorded, accepted limitation on the strength of the Phase 7 conclusion rather than an open decision. |
| 5a | **New.** `DECISIONS.md` Q18 ("Does buoy swell actually correlate with MJO phase?") carries the plan "Schedule a quick look in Phase 5, Stage 1." Stage 1 has now run and did not look, because the Phase 5a session prompt scoped MJO out entirely (counting needs no MJO, and folklore-only winters without MJO coverage were explicitly permitted for the storm side). Q18's stated plan now points at a stage that has been completed without it. The question itself is untouched and still cheap to answer on exploration winters. | Open — owner to decide where Q18's quick look now belongs: Phase 5b if the gate opens, or the Phase 6 protocol work if it does not. Not fixed here — outside this session's scope. |
| 5a | **New.** `DECISIONS.md` Q17 (statistical power) still reads "With at most ~40 winters and leave-one-season-out CV..." — the pre-0A planning figure. The confirmed usable count is 22 winters for the four-model comparison, 16 of them exploration (Q13/Q21, SPEC Section 7, and now SPEC 11.1 after H1). This does not weaken Q17's concern, it strengthens it: the sample is roughly half what the question was originally framed around, and Phase 5a's own event counts (dozens of independent events, not thousands) are a concrete instance of it. Q17 was not in this session's file-update scope. | Open — owner to decide whether Q17's framing figure should be updated to 22/16 winters. Reported, not fixed. |
| 5a | **New.** SPEC 1.1 states "Since roughly 2004, a community of Utah skiers has tracked NOAA buoy 51101", but SPEC 3.1 gives 51101's record as starting ~2008, and Session 0A measured its archive as beginning 2008-02-21 with nothing before. The folklore cannot have been tracking 51101's data in 2004 — either the start date is approximate/wrong, or the community began on a different buoy. This is background text, not a data-handling rule, so nothing downstream is wrong. It does bear on interpretation, though: 10 of the 16 exploration winters (1989–2003) predate 51101 entirely, so Phase 5a's pop signal necessarily comes from 51001 as the stand-in (Q1, correlation 0.98 where they overlap) rather than from the buoy the folklore actually names. | Open — owner to decide whether SPEC 1.1's date should be softened, and whether the "folklore's own buoy did not exist for most exploration winters" caveat belongs in the Phase 6 protocol's framing. |
| 5a | **New, minor — wording, not a numerical disagreement.** SPEC 6.1 glosses `POD = a/(a+c)` as "of all storms, how many followed a pop" and `base rate = (a+c)/(a+b+c+d)` as "how often a storm happens at all". In the frame Phase 5a had to build to make those formulas computable, the unit is an anchor day and `a+c` counts *windows that contain a storm start*, not storms — one storm can fall inside many overlapping non-pop windows, and a storm outside every window is counted by neither. The formulas are implemented exactly as SPEC writes them and the skill scores are standard; only the plain-English gloss is loose. Related: SPEC 6.1 specifies the 2×2's rows but never says how the "buoy did not pop" comparison windows are drawn, which is the single most consequential choice in the table — Phase 5a had to invent it and recorded the construction as Q25. | Open — owner to decide whether SPEC 6.1's gloss should be tightened and whether the comparison-window construction (Q25) should be written into SPEC 6.1 or left for the Phase 6 protocol in Section 8. |
