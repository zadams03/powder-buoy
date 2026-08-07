# STATUS.md — Powder Buoy

**Spec version: 0.2**
**Last updated: Session 0A, 2026-08-07**

This file holds current state. It changes every session.
Stable specification lives in `SPEC.md`. Open questions and findings live in
`DECISIONS.md`.

---

## 1. Current state

Repo scaffold and NDBC buoy ingest complete. Nothing else built yet.

| Item | State |
| --- | --- |
| Repo scaffold | **Done (0A)** |
| NDBC ingest | **Done (0A)** — `buoy_daily.parquet`, stations 51001 and 51101 |
| SNOTEL ingest | Not started |
| Climate index ingest | Not started |
| Season split (exploration vs held-out) | Not made — Phase 4 |
| Evaluation protocol (SPEC Section 8) | Empty — locked in Phase 6 |
| Models | Not started |
| Experiment register | Not created |

**Data on disk:** `data/processed/buoy_daily.parquet` (22,919 rows, stations 51001 and
51101). Raw archive files under `data/raw/` (gitignored).

**Held-out seal:** not yet applicable. The split does not exist. Once Phase 4 runs, this
line records SEALED or UNSEALED, and if unsealed, the date and reason.

---

## 2. Next session

### Session 0B — SNOTEL snow ingest

**Scope (per SPEC Phase 2 and Section 3.2):**

- Look up and confirm exact NRCS SNOTEL station IDs for the candidate Wasatch stations
  (SPEC 3.2); record them in `DECISIONS.md` Q3. Do not hardcode unverified IDs.
- Decide and record the NRCS AWDB access method/endpoint (`DECISIONS.md` Q4).
- Write `src/powderbuoy/ingest/snotel.py` — download, parse, clean SNOTEL SWE data.
- Produce `data/processed/snow_daily.parquet` per SPEC Section 5.2.
- Decide and record the buoy/snow timezone convention (`DECISIONS.md` Q12).

**Explicitly not in that session:** climate indices, any analysis, any correlation
between buoy and snow, any modelling.

---

## 3. Build log

Newest entry at the top. One row per completed session.

| Session | Spec version | Date | Summary |
| --- | --- | --- | --- |
| 0A | 0.1 → 0.2 | 2026-08-07 | Repo scaffold, uv environment, config system, NDBC ingest for 51001 and 51101 → `buoy_daily.parquet` (22,919 rows). All validation checks passed; cross-buoy correlation 0.98. Discovered a 2010–2014 gap in 51001's archive (5+ winters with no data) — see `DECISIONS.md` Q21. |

---

## 4. Known data state

Filled in as ingest sessions complete.

| Table | Rows | Date range | Gaps | Last refreshed |
| --- | --- | --- | --- | --- |
| buoy_daily | 22,919 (51001: 16,395; 51101: 6,524) | 51001: 1981-02-11 to 2025-12-31; 51101: 2008-02-21 to 2025-12-31 | 51001: 3,633 gap days (22.2%), longest 2,068 days (2009-12-25 to 2015-08-23); 51101: 651 gap days (10.0%), longest 409 days (2008-03-08 to 2009-04-20) | 2026-08-07 |
| snow_daily | — | — | — | — |
| climate_daily | — | — | — | — |
| analysis_daily | — | — | — | — |

---

## 5. Blockers

None. One risk carried forward: 51001's 2010–2014 archive gap shortens the usable
continuous record materially below the "~40 winters" planning assumption — see
`DECISIONS.md` Q21 and SPEC Section 6.0. Not a blocker for Session 0B, but relevant when
Phase 4 splits seasons.

---

## 6. Consistency check log

Every session reports contradictions found across the three files. Logged here,
resolved by the owner.

| Session | Contradiction found | Resolution |
| --- | --- | --- |
| 0A | SPEC.md Section 5.1 `buoy_daily` schema does not list an `apd_mean` column, but the Session 0A prompt's Step 5 output-schema table — which states it is "matching SPEC Section 5.1" — includes one. Implemented with `apd_mean` included, following the more detailed session-prompt table. | Open — owner to decide whether to add `apd_mean` to SPEC 5.1 or drop it from `buoy_daily`. |
| 0A | SPEC 3.1 and the Session 0A prompt's file-era table describe three formats, with "2005 onward" given two header lines and `WDIR`/`PRES` naming. Actual NDBC files show a fourth, transitional format for 2005–2006 (minute column added, but still one header line, still `WD`/`BAR` naming) — the two-header-line/`WDIR`/`PRES` format only starts in 2007. Additionally, the year column is labelled `YY` both pre-2000 (true 2-digit) and from 2007 onward (already 4-digit) — the column name does not indicate digit width. The parser detects both by content (header line count, `#` prefix, year magnitude), so results are unaffected, but the planning documents' description of the eras was incomplete. | Open — owner to decide whether to correct the file-era table in future session prompts; SPEC.md 3.1 has been updated with what was actually observed. |
| 0A | `DECISIONS.md` Q1's resolution reasons that 51001 gives "the extra 27 years" over 51101. With the newly discovered 2010–2014 archive gap, a meaningful slice of that extra span has no data, so the "27 years" framing overstates the continuous-record advantage even though the underlying decision (51001 as primary) is unaffected — the 0.98 correlation check still confirms it. | Open — owner to decide whether to soften the Q1 wording. |
