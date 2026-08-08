# STATUS.md — Powder Buoy

**Spec version: 0.5**
**Last updated: Session 0D, 2026-08-08**

This file holds current state. It changes every session.
Stable specification lives in `SPEC.md`. Open questions and findings live in
`DECISIONS.md`.

---

## 1. Current state

Repo scaffold, NDBC buoy ingest, SNOTEL snow ingest, climate index ingest,
`analysis_daily`, and the season split are all complete. Phases 0–4 are done. Next is
Phase 5, exploration — needs its own planning first.

| Item | State |
| --- | --- |
| Repo scaffold | **Done (0A)** |
| NDBC ingest | **Done (0A)** — `buoy_daily.parquet`, stations 51001 and 51101 |
| SNOTEL ingest | **Done (0B)** — `snow_daily.parquet`, 5 Wasatch stations |
| Climate index ingest | **Done (0C)** — `climate_daily.parquet`, MJO/ENSO/PDO |
| `analysis_daily` join | **Done (0C)** — `analysis_daily.parquet`, dumb full outer join |
| Season split (exploration vs held-out) | **Done (0D)** — see `DECISIONS.md` Q13 |
| Evaluation protocol (SPEC Section 8) | Empty — locked in Phase 6 |
| Models | Not started |
| Experiment register | Not created |

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

### Phase 5 — Exploration (SPEC Section 6.1)

**Needs its own planning session first**, same as Phase 4 did. Runs on exploration
winters only (`load_analysis_data(include_holdout=False)` — the default), never on the
six sealed held-out winters or on values from them.

Runs in three gated stages, in this order (SPEC 6.1):

1. **Contingency tables** at the folklore's 14-day lag — POD, false alarm rate, storm
   rate given a pop versus base rate, Peirce skill score.
2. **Lag scan**, 0–30 days, across a small declared set of pop definitions and SWE
   thresholds (`DECISIONS.md` Q6, Q16).
3. **Modelling, gated** — only if Stage 2 shows a coherent band of positive skill that
   survives sensitivity checks. If not, Phase 5 ends at Stage 2 and Phase 6 locks a
   protocol expecting a null result.

Open questions already flagged for this phase: Q5, Q6, Q8, Q16, Q18, Q19, Q20, Q23 (see
`DECISIONS.md`). Every number produced is EXPLORATORY (rule 2.3) — none of it may be
reported as a conclusion.

**Explicitly not in that session:** reading, printing, or scoring anything from the six
held-out winters; filling SPEC Section 8 (that is Phase 6).

---

## 3. Build log

Newest entry at the top. One row per completed session.

| Session | Spec version | Date | Summary |
| --- | --- | --- | --- |
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

---

## 5. Blockers

None. One risk carried forward: 51001's 2010–2014 archive gap shortens the usable
continuous record materially below the "~40 winters" planning assumption — see
`DECISIONS.md` Q21 and SPEC Section 6.0. Not a blocker for data-engineering sessions, but
a live decision point when Phase 4 splits seasons.

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
| 0D | **New.** H2 reworded SPEC Section 7 to state the two-era, 22-usable-winter picture, but Section 11.1 still reads only "at most around 40 winters, confirmed in Session 0A" with no mention of the gap or the two eras — the two sections again describe the same fact differently, one level less starkly than the 0C finding above (both are now past-tense, but only 7 has the nuance). Session prompt's H2 scope named Section 7 only, not 11.1. | Open — owner to decide whether 11.1 should gain the same two-era phrasing or stay a short pointer to Section 7. |
| 0D | **New.** SPEC Section 6.0 ("Dependency on Session 0A — the record-length risk") still frames Plan B as a live, unmade decision — "If we land here, **that is a decision point**... either accept weaker conclusions... or pause and reconsider scope" — but Phase 4 has now made exactly that call (Q13/Q21: proceed with a two-era, 22-winter record and a 6-winter held-out set, accepting the limitation rather than pausing). Section 6.0 was not in this session's file-update scope. | Open — owner to decide whether Section 6.0 should be updated to record that the decision point was reached and resolved (pointing to Q13/Q21), or left as the standing description of the risk for future readers. |
| 0D | **New.** This file's own Section 5 (Blockers) still reads "...a live decision point when Phase 4 splits seasons" — but Phase 4 is now the session that just ran; the decision is made, not live. Same pattern as the 0B→0C staleness already resolved once in this section. Section 5 was not in this session's file-update scope (only 1, 2, 3, 6 were). | Open — owner to decide the reword; likely "...was the live decision point Phase 4 resolved (see Section 1 and `DECISIONS.md` Q13/Q21)." |
