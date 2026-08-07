# DECISIONS.md — Powder Buoy

**Spec version: 0.2**

Append-only. Entries are never deleted. A resolved question has its status changed and
the resolution appended — the original text stays.

Two sections: open questions (Section 1) and findings (Section 2).

---

## 1. Open questions

Questions deliberately deferred. Each has a status and a plan for when it gets answered.

| # | Question | Status | Notes / plan |
| --- | --- | --- | --- |
| Q1 | Which NDBC station is primary — 51001 or 51101? | **Resolved** | 51001. It sits ~13 km from 51101 in similar deep water, and its record starts ~1981 versus ~2008. The extra 27 years matter more than using the exact buoy the folklore names. 51101 is ingested too, and Session 1 will check the two agree where they overlap. If they diverge materially, reopen. |
| Q2 | Has 51001 been repositioned across its record? | Open — could not be checked as planned | NDBC buoys are moved, replaced, and occasionally go adrift. A position change could shift the wave climate. Session 0A attempted to check this by logging distinct lat/lon values per year, but the NDBC historical stdmet archive files do not embed per-observation station coordinates — there is nothing to extract per file. The only thing available is NDBC's current station table, a single present-day listing (51001: 24.475 N 162.030 W; 51101: 24.359 N 162.081 W), which says nothing about the past. Left Open. If this needs answering, it requires a different source — e.g. NDBC's per-station deployment history page — not attempted here as out of scope for 0A. |
| Q3 | Exact SNOTEL station identifiers for the Wasatch sites | Open | SPEC 3.2 lists candidate stations by name only. IDs must be looked up against the NRCS station list during the SNOTEL session and recorded here. Do not hardcode unverified IDs. |
| Q4 | Which NRCS endpoint to use for SNOTEL | Open | NRCS offers a legacy SOAP service and a newer REST API, plus a CSV report generator. Whichever is chosen must be recorded here with the exact URL pattern, so a future session does not have to rediscover it. |
| Q5 | How to combine multiple SNOTEL stations into one storm signal | Open | Options: mean SWE gain across stations, max across stations, or "any station exceeded threshold". Each gives a different storm count. Must be fixed in the Phase 6 protocol, before the held-out set is unsealed. See also Q20 on whether combining hides real signal. |
| Q6 | SWE threshold for "a storm day" | Open | Must be fixed in the Phase 6 protocol. Likely a small set of thresholds tested as a sensitivity check rather than one value, but the set must be declared in advance. |
| Q7 | Lag window under test | **Resolved** | The original spec (v0.1) had a contradiction: it required the protocol to be locked before any result was seen, while also requiring a scan across lags 0–30. Both cannot happen in that order on the same data — locking first means guessing the lag, looking first makes the lock meaningless. Resolved by splitting the winters into an exploration set and a sealed held-out set (SPEC rule 2.3). The lag is chosen freely on exploration seasons in Phase 5, committed in Phase 6, and tested once on held-out seasons in Phase 7. Phase order corrected accordingly. |
| Q13 | Exploration / held-out split ratio and which seasons | Open | Roughly 70/30 is the working assumption. Two options: chronological (last 30% of winters held out) or random selection of whole winters. Chronological is more honest about real forecasting but risks the held-out set landing on an unusual climate period. Random spreads the risk but is less realistic. Decide in Phase 4, before looking at anything, and record the exact season list here. |
| Q14 | What happens if the held-out result is disappointing | **Position agreed, final call deferred** | The seal is one-shot (SPEC rule 2.3). Owner's stated position: likely write up the null result and stop, but the decision is taken at the time rather than pre-committed. Recorded here before Phase 4 so the intent is on record while no result exists to create pressure. If the decision at the time differs from this, log the reasoning alongside it. |
| Q15 | Does the folklore rule need the held-out set at all? | Open | The folklore's 14-day lag was specified by someone else, years ago, without reference to our data. So testing exactly 14 days is arguably a genuine out-of-sample test that could run on all seasons. Tempting, but it opens a door. Current position: run it on held-out like everything else. Revisit in Phase 6 only if there is a clear argument. |
| Q8 | Is DPD/MWD filtering worth it? | Open | A long-period swell from the northwest indicates a distant, energetic North Pacific storm. Short-period swell is local wind chop. Filtering for the former may sharpen the signal considerably. Adds complexity. Decide in Phase 5, Stage 2. |
| Q16 | Which pop definitions to test in Phase 5, Stage 1 | Open | Candidates: absolute WVHT threshold, rolling z-score above N, day-over-day rate of rise, and sustained elevation for N days. The set must be small and declared before Stage 1 runs, not expanded when early ones disappoint. Record the declared set here before running. |
| Q9 | Should GEFS Reforecast v12 be added as a comparison forecast? | Deferred | Free on AWS Open Data. Would let us compare against a real operational week-2 forecast, which is the strongest possible baseline. Heavy: large downloads, complex format. Revisit only if Phase 7 shows the buoy has skill. |
| Q10 | Monthly indices (ENSO, PDO) joined to daily data | Open | Forward-filling a monthly value across a month creates artificial step changes and mild look-ahead within the month. Must be flagged in the data model and the approach recorded before Phase 7. |
| Q11 | Snow quality versus storm occurrence | Deferred | SWE says how much water fell, not whether it was good skiing. Adding temperature would allow a powder-quality target. Out of scope for now (SPEC Section 11). Revisit only after the core question is answered. |
| Q12 | Timezone alignment between buoy and snow data | Open | Buoy timestamps are UTC. SNOTEL observation dates are local. At lead times of one to two weeks a one-day offset is immaterial, but it must be documented rather than assumed away. Record the convention during the SNOTEL session. |
| Q17 | Statistical power — can the models even be told apart? | Open | Raised in the pre-build review (item 6). With at most ~40 winters and leave-one-season-out CV, the difference in skill between models A/B/C/D may be smaller than the error bars. "We cannot distinguish them" is a third kind of null, alongside "no signal" and "signal present". The Phase 6 protocol must state, before unsealing, what size of skill difference counts as meaningful — not just its sign. Otherwise a tiny, meaningless edge gets over-read. |
| Q18 | Does buoy swell actually correlate with MJO phase? | Open | Raised in the review (item 8). The entire "is it just a crude MJO index" framing assumes buoy wave height and MJO state are related. Plausible but unchecked. This is cheap to look at early, on exploration seasons only, and if they turn out unrelated the central experiment's framing needs rethinking. Schedule a quick look in Phase 5, Stage 1. |
| Q19 | Is the Nov 1 – Apr 30 season definition right? | Open | Raised in the review (item 9). The Wasatch gets snow in October and May, so the cutoff is somewhat arbitrary, yet it defines the unit that everything splits and scores on. Sensitivity to widening it (e.g. Oct 15 – May 15) should be checked once data is in. Load-bearing enough to write down; probably not worth changing. |
| Q20 | Might combining SNOTEL stations hide real signal? | Open | Raised in the review (item 7). Little Cottonwood and Big Cottonwood can get very different snowfall from the same system. Averaging or maxing across canyons (Q5) could blur a signal that is sharp at one site. Worth checking per-station behaviour in Phase 5 before committing to a combination rule in Phase 6. |
| Q21 | Primary buoy record-length risk | **Partially resolved — risk confirmed real, decision deferred to Phase 4** | Raised in the review (item 5), written into SPEC Section 6.0 with a Plan B. Session 0A measured it: 51001's historical archive has no station-year files at all for 2010–2014, a 2,068-day (5.7-year) continuous gap from 2009-12-25 to 2015-08-23, on top of scattered smaller gaps (22.2% of days null overall). The two-buoy correlation is strong where they overlap (0.98, well above the 0.9 bar), so 51001 remains the right primary station — this is not a Q1 reversal. But the true continuous record is shorter than "~40 winters" implied: excluding the 2010–2014 hole, 51001 usefully covers roughly winters 1981–2009 (~28 winters) plus 2015–2025 (~10 winters), not one unbroken 40-winter span. Whether to treat this as one record with a hole, split it into two eras, or drop the shorter post-gap era is a Phase 4 decision, not a Session 0A one — Phase 4 is where seasons get chosen. Recorded here so it isn't lost before then. Linked to Q1. |
| Q22 | Should `apd_mean` be added to SPEC Section 5.1's `buoy_daily` schema? | Open | Surfaced in Session 0A's consistency check. SPEC 5.1 lists `wvht_*`, `dpd_*`, `mwd_mean`, `wspd_*`, `pres_*`, and `n_obs` for `buoy_daily`, but not `apd_mean`. The Session 0A prompt's Step 5 output-schema table — captioned "matching SPEC Section 5.1" — includes `apd_mean` (mean of valid APD) anyway. `buoy_daily.parquet` was built with `apd_mean` included, following the session prompt. SPEC.md is the stable document; it should either gain `apd_mean` or the column should be dropped. Owner to decide. |

---

## 2. Findings log

Newest entry at the top. Every finding follows the same shape.

Each entry must record:

- **Hypothesis** — what was being tested
- **Method** — how, in one or two sentences
- **Result** — the number, with its baseline alongside (SPEC rule 2.2)
- **Implication** — what it changes
- **Status** — CONFIRMED or EXPLORATORY

A finding produced under a protocol adjusted after the result was seen is EXPLORATORY
and may not be reported as a conclusion (SPEC rule 2.3).

---

*(No findings recorded yet.)*
