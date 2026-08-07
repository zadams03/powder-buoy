# STATUS.md — Powder Buoy

**Spec version: 0.3**
**Last updated: Session 0B, 2026-08-07**

This file holds current state. It changes every session.
Stable specification lives in `SPEC.md`. Open questions and findings live in
`DECISIONS.md`.

---

## 1. Current state

Repo scaffold, NDBC buoy ingest, and SNOTEL snow ingest complete. Climate indices not
started.

| Item | State |
| --- | --- |
| Repo scaffold | **Done (0A)** |
| NDBC ingest | **Done (0A)** — `buoy_daily.parquet`, stations 51001 and 51101 |
| SNOTEL ingest | **Done (0B)** — `snow_daily.parquet`, 5 Wasatch stations |
| Climate index ingest | Not started |
| Season split (exploration vs held-out) | Not made — Phase 4 |
| Evaluation protocol (SPEC Section 8) | Empty — locked in Phase 6 |
| Models | Not started |
| Experiment register | Not created |

**Data on disk:** `data/processed/buoy_daily.parquet` (22,919 rows, stations 51001 and
51101); `data/processed/snow_daily.parquet` (65,618 rows, 5 Wasatch SNOTEL stations).
Raw archive/response files under `data/raw/` (gitignored).

**Held-out seal:** not yet applicable. The split does not exist. Once Phase 4 runs, this
line records SEALED or UNSEALED, and if unsealed, the date and reason.

---

## 2. Next session

### Session 0C — Climate index ingest (MJO, ENSO, PDO)

**Scope (per SPEC Phase 3 and Section 3.3):**

- Write `src/powderbuoy/ingest/climate.py` — download and parse the Wheeler–Hendon
  RMM MJO index (RMM1, RMM2, phase, amplitude), ENSO (Niño 3.4 / ONI), and PDO.
- Produce `data/processed/climate_daily.parquet` per SPEC Section 5.3.
- Resolve `DECISIONS.md` Q10 — how monthly indices (ENSO, PDO) are joined to daily
  data without creating look-ahead within the month; flag forward-filled values.
- Build `analysis_daily` (SPEC Section 5.4) joining buoy, snow, and climate columns —
  this is the last data-engineering step before Phase 4 (season split).

**Explicitly not in that session:** any correlation, lag scan, or modelling; the
season split (Phase 4); anything that reads or seals the held-out set.

---

## 3. Build log

Newest entry at the top. One row per completed session.

| Session | Spec version | Date | Summary |
| --- | --- | --- | --- |
| 0B | 0.2 → 0.3 | 2026-08-07 | SNOTEL snow ingest via the NRCS AWDB REST API for 5 confirmed Wasatch stations (Snowbird, Brighton, Mill-D North, Thaynes Canyon, Louis Meadow) → `snow_daily.parquet` (65,618 rows). All validation checks passed. Every station's daily record is 100% complete from its install date to present — no gaps at all in this source, unlike the buoy. 25 winters have both buoy (51001) and snow (≥2 stations) at `good` coverage — the usable-sample preview for Phase 4. Housekeeping: `apd_mean` added to SPEC 5.1 (Q22), Q1 wording softened, Q2 closing note added. |
| 0A | 0.1 → 0.2 | 2026-08-07 | Repo scaffold, uv environment, config system, NDBC ingest for 51001 and 51101 → `buoy_daily.parquet` (22,919 rows). All validation checks passed; cross-buoy correlation 0.98. Discovered a 2010–2014 gap in 51001's archive (5+ winters with no data) — see `DECISIONS.md` Q21. |

---

## 4. Known data state

Filled in as ingest sessions complete.

| Table | Rows | Date range | Gaps | Last refreshed |
| --- | --- | --- | --- | --- |
| buoy_daily | 22,919 (51001: 16,395; 51101: 6,524) | 51001: 1981-02-11 to 2025-12-31; 51101: 2008-02-21 to 2025-12-31 | 51001: 3,633 gap days (22.2%), longest 2,068 days (2009-12-25 to 2015-08-23); 51101: 651 gap days (10.0%), longest 409 days (2008-03-08 to 2009-04-20) | 2026-08-07 |
| snow_daily | 65,618 (Snowbird 13,498; Brighton 14,562; Mill-D North 13,824; Thaynes Canyon 13,927; Louis Meadow 9,807) | Per station, install date to 2026-08-06 (see SPEC 3.2 for install dates) | 0 null `swe_in` days at any of the 5 stations — full record complete from install to present | 2026-08-07 |
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
| 0A | SPEC.md Section 5.1 `buoy_daily` schema does not list an `apd_mean` column, but the Session 0A prompt's Step 5 output-schema table — which states it is "matching SPEC Section 5.1" — includes one. Implemented with `apd_mean` included, following the more detailed session-prompt table. | **Resolved (0B, H1).** `apd_mean` added to SPEC 5.1. DECISIONS.md Q22 marked Resolved. |
| 0A | SPEC 3.1 and the Session 0A prompt's file-era table describe three formats, with "2005 onward" given two header lines and `WDIR`/`PRES` naming. Actual NDBC files show a fourth, transitional format for 2005–2006 (minute column added, but still one header line, still `WD`/`BAR` naming) — the two-header-line/`WDIR`/`PRES` format only starts in 2007. Additionally, the year column is labelled `YY` both pre-2000 (true 2-digit) and from 2007 onward (already 4-digit) — the column name does not indicate digit width. The parser detects both by content (header line count, `#` prefix, year magnitude), so results are unaffected, but the planning documents' description of the eras was incomplete. | **Resolved (0B, H2).** Owner has accepted 0A's corrected SPEC 3.1 text as final; no further edit needed. |
| 0A | `DECISIONS.md` Q1's resolution reasons that 51001 gives "the extra 27 years" over 51101. With the newly discovered 2010–2014 archive gap, a meaningful slice of that extra span has no data, so the "27 years" framing overstates the continuous-record advantage even though the underlying decision (51001 as primary) is unaffected — the 0.98 correlation check still confirms it. | **Resolved (0B, H3).** Q1 wording softened to "a longer record — roughly two usable decades, though with a five-year gap (2010–2014, see Q21)." Decision itself unchanged. |
| 0B | SPEC Section 6's phases table still shows Phases 0, 1, and 2 as "Not started" in the Status column, even though this file's Section 1 confirms all three are done (repo scaffold, NDBC ingest, SNOTEL ingest). SPEC's own top-of-file status line is updated each session, but the Section 6 table's per-phase Status column is not — neither 0A nor 0B's instructions asked for it. | Open — owner to decide whether the Section 6 table should be kept current each session or left as a static template with phase tracking living solely in `STATUS.md`. |
| 0B | SPEC Section 5's opening line states "All processed tables are daily, indexed by date, in UTC," but Section 5.2's own `snow_daily` row says `date` is the "Local observation date," and `DECISIONS.md` Q12 (resolved this session) confirms `snow_daily.date` is deliberately kept on its native Pacific Standard Time day and never shifted to UTC. The opening line is inaccurate for `snow_daily`. | Open — owner to decide whether to soften Section 5's opening line (e.g. "in each table's own native timezone, documented per table") or something else. |
| 0B | Minor, not a contradiction: `STATUS.md` Section 5 (Blockers) still frames the 51001 2010–2014 gap risk as "Not a blocker for Session 0B" — phrasing now stale since 0B is complete and the next session is 0C. Left as-is per the instruction to report, not fix, outside this session's listed file-update scope. | Open — owner to reword or leave; cosmetic only. |
