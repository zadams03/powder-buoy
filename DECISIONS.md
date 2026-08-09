# DECISIONS.md — Powder Buoy

**Spec version: 0.9**

Append-only. Entries are never deleted. A resolved question has its status changed and
the resolution appended — the original text stays.

Two sections: open questions (Section 1) and findings (Section 2).

---

## 1. Open questions

Questions deliberately deferred. Each has a status and a plan for when it gets answered.

| # | Question | Status | Notes / plan |
| --- | --- | --- | --- |
| Q1 | Which NDBC station is primary — 51001 or 51101? | **Resolved** | 51001. It sits ~13 km from 51101 in similar deep water, and its record starts ~1981 versus ~2008 — a longer record — roughly two usable decades, though with a five-year gap (2010–2014, see Q21) — matters more than using the exact buoy the folklore names. 51101 is ingested too, and Session 1 will check the two agree where they overlap. If they diverge materially, reopen. |
| Q2 | Has 51001 been repositioned across its record? | Open — could not be checked as planned | NDBC buoys are moved, replaced, and occasionally go adrift. A position change could shift the wave climate. Session 0A attempted to check this by logging distinct lat/lon values per year, but the NDBC historical stdmet archive files do not embed per-observation station coordinates — there is nothing to extract per file. The only thing available is NDBC's current station table, a single present-day listing (51001: 24.475 N 162.030 W; 51101: 24.359 N 162.081 W), which says nothing about the past. Left Open. If this needs answering, it requires a different source — e.g. NDBC's per-station deployment history page — not attempted here as out of scope for 0A. Direct check is not possible from the stdmet archive files, which carry no per-observation coordinates. The 0.98 cross-buoy correlation makes a disruptive reposition unlikely, so this is not pursued further. If it ever matters, NDBC publishes a per-station deployment-history page that would answer it. Left Open, low priority. |
| Q3 | Exact SNOTEL station identifiers for the Wasatch sites | **Resolved** | SPEC 3.2 lists candidate stations by name only. IDs must be looked up against the NRCS station list during the SNOTEL session and recorded here. Do not hardcode unverified IDs. Resolved in Session 0B by querying `GET /services/v1/stations?stationTriplets=*:UT:SNTL` (140 Utah SNTL stations returned) and matching by name. All five SPEC 3.2 candidates found: **Snowbird** `766:UT:SNTL`, install 1989-08-23, elevation 9,170 ft, Salt Lake Co. **Brighton** `366:UT:SNTL`, install 1986-09-24, elevation 8,790 ft, Salt Lake Co. **Mill-D North** `628:UT:SNTL`, install 1988-10-01, elevation 8,940 ft, Salt Lake Co. **Thaynes Canyon** `814:UT:SNTL`, install 1988-06-20, elevation 9,260 ft, Summit Co. **Louis Meadow** `972:UT:SNTL`, install 1999-10-01, elevation 6,740 ft, Salt Lake Co. Elevations differ slightly from SPEC 3.2's approximate figures (e.g. Snowbird 9,170 ft actual vs ~9,600 ft listed) — the NRCS figures above are authoritative. All five written to `config/regions/utah.yaml`. One additional well-placed candidate turned up in the same query and is **not** added to config pending owner sign-off: **Mill Creek Canyon** `1321:UT:SNTL`, Salt Lake Co., elevation 6,960 ft — but its install date is 2024-06-18, so it has essentially no winters of record yet and is not useful for this study regardless. |
| Q4 | Which NRCS endpoint to use for SNOTEL | **Resolved** | NRCS AWDB REST API, confirmed live in Session 0B against its own OpenAPI spec at `https://wcc.sc.egov.usda.gov/awdbRestApi/v3/api-docs`. Base URL: `https://wcc.sc.egov.usda.gov/awdbRestApi`. No API key required. Station metadata: `GET /services/v1/stations?stationTriplets={id}:{state}:SNTL` (also supports wildcards, e.g. `*:UT:SNTL` to list all Utah SNOTEL stations — used to confirm Q3). Daily data: `GET /services/v1/data?stationTriplets={triplet}&elements={codes}&duration=DAILY&beginDate=yyyy-MM-dd&endDate=yyyy-MM-dd&returnFlags=true`. Element codes: `WTEQ` (SWE, inches), `PREC` (accumulated precipitation, inches), `TAVG` (mean air temp, °F) — all three can be requested in one call, comma-separated; confirmed working together. `periodRef` defaults to `END` (interval-ending — the value is dated to the day that just ended), matching the SPEC 3.2 convention; passed explicitly in code for clarity rather than relied on implicitly. Worked example, tested live: `curl "https://wcc.sc.egov.usda.gov/awdbRestApi/services/v1/data?stationTriplets=766:UT:SNTL&elements=WTEQ,PREC,TAVG&duration=DAILY&beginDate=2019-01-01&endDate=2019-01-05&returnFlags=true"` — returned three per-element series with per-day `qcFlag` values (`V`=validated, `E`=estimated), matching what `snotel.py` parses. |
| Q5 | How to combine multiple SNOTEL stations into one storm signal | **Resolved (Phase 6, recorded Session 7, 2026-08-09) — `any2`, fixed in SPEC 8.2** | Options: mean SWE gain across stations, max across stations, or "any station exceeded threshold". Each gives a different storm count. Must be fixed in the Phase 6 protocol, before the held-out set is unsealed. See also Q20 on whether combining hides real signal. **Resolved: the locked rule uses `any2` — at least 2 of the stations actually reporting that day gained ≥ 0.5 in (SPEC 8.2).** The choice was made on definitional grounds, not on which combination scored best: `any2` at 0.5 in yields the event count a Wasatch winter plausibly contains (15.4 per winter, F1/Q26), while `mean` runs tighter at 13.5 and no combination showed a signal to protect (Q20). A station not reporting contributes nothing and is not filled in (rule 2.5). Closed here as a status correction only — the substance was decided in Phase 6 and the label lagged behind it. |
| Q6 | SWE threshold for "a storm day" | **Resolved (Phase 6, recorded Session 7, 2026-08-09) — 0.5 inch, fixed in SPEC 8.2** | Must be fixed in the Phase 6 protocol. Likely a small set of thresholds tested as a sensitivity check rather than one value, but the set must be declared in advance. **Phase 5a:** the declared set **0.5 / 1.0 / 1.5 inches** of `swe_gain_in` was carried through unchanged — fixed by planning, not calibrated, and every Stage 1 configuration was run at all three. No single value is chosen here. Phase 5a's detector validation is direct evidence for the Phase 6 choice and should be read alongside it: at 0.5 in the combined `any2` definition yields 15.4 storm events per winter, squarely inside the 15–30 a Wasatch winter plausibly contains, while 1.0 in yields 6.9 and 1.5 in yields 2.3 — both implausibly few (see Q26). The three thresholds are not equally defensible as "a storm day", and Phase 6 should not assume the 1.0-in convention. **Resolved: 0.5 inch, and it is the single value in the locked rule (SPEC 8.2), paired with `any2` (Q5).** Phase 6 did not assume the 1.0-in convention: it chose 0.5 in on the detector argument this entry sets out, before the box was opened — 15.4 events per winter against 6.9 at 1.0 in and 2.3 at 1.5 in (F1, Q26) — and explicitly not because 0.5 in flattered the folklore, since exploration was flat at both 1.0 in and 0.5 in (F2). The other two thresholds are not carried into Phase 7; no sensitivity sweep is run on held-out data (SPEC 8.1). Closed here as a status correction only. |
| Q7 | Lag window under test | **Resolved** | The original spec (v0.1) had a contradiction: it required the protocol to be locked before any result was seen, while also requiring a scan across lags 0–30. Both cannot happen in that order on the same data — locking first means guessing the lag, looking first makes the lock meaningless. Resolved by splitting the winters into an exploration set and a sealed held-out set (SPEC rule 2.3). The lag is chosen freely on exploration seasons in Phase 5, committed in Phase 6, and tested once on held-out seasons in Phase 7. Phase order corrected accordingly. |
| Q13 | Exploration / held-out split ratio and which seasons | **Resolved (Phase 4, Session 0D, 2026-08-08)** | Decided in planning, executed without revisiting in Session 0D. **Usable-winter accounting:** the four-model comparison (SPEC Section 7) needs buoy, snow, and MJO all present across the winter. Both-good winters (buoy + ≥2 snow stations, from 0B): 25. The MJO series ends 2024-02-24 (0C), so winters 2023, 2024, 2025 lack complete MJO coverage and cannot join the four-model comparison — set aside as **folklore-only** (usable later for buoy-vs-snow counting in Phase 5, which needs no MJO, but never part of the sealed split). That leaves **22 winters** for the split, in two eras either side of the 51001 buoy gap (Q21): pre-gap (14) — 1989, 1990, 1992, 1994, 1996, 1998, 1999, 2000, 2001, 2003, 2004, 2005, 2006, 2008; post-gap (8) — 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022. **Chosen split — Option D, chronological within each era:** the held-out (test) set takes the latest winters from each era. This keeps a genuine hindcast property (within each era every test winter is later than every training winter) while ensuring both climate eras appear in the test set — a pure chronological split across the whole 22 would have put the entire test set in the modern era and starved training of modern winters. **The exact lists, sealed:** HELD-OUT (test), 6 winters — 2004, 2005, 2006, 2008, 2021, 2022. EXPLORATION (train + cross-validation), 16 winters — 1989, 1990, 1992, 1994, 1996, 1998, 1999, 2000, 2001, 2003, 2015, 2016, 2017, 2018, 2019, 2020. FOLKLORE-ONLY (set aside, not in the split), 3 winters — 2023, 2024, 2025. Written into `config/regions/utah.yaml` under a `seasons` block as explicit lists (not ranges or rules), enforced in code by `powderbuoy.seasons.load_analysis_data` (held-out excluded by default). **Accepted limitation:** the held-out set leans older (four of six are 2004–2008) and the modern era is represented by only two winters (2021, 2022), because the buoy gap left only 8 modern winters to draw from. The final test rests on these six specific winters and cannot be reshuffled — accepted knowingly during planning. See also Q21. |
| Q14 | What happens if the held-out result is disappointing | **Resolved (Phase 7, Session 7, 2026-08-09) — the position held: write up and stop** | The seal is one-shot (SPEC rule 2.3). Owner's stated position: likely write up the null result and stop, but the decision is taken at the time rather than pre-committed. Recorded here before Phase 4 so the intent is on record while no result exists to create pressure. If the decision at the time differs from this, log the reasoning alongside it. **What actually happened: the result is NULL CONFIRMED (F7) — storm rate given a pop 0.6818 against a base rate of 0.6339, ratio 1.0755 against a bar of 1.20, under both matching variants.** "Disappointing" is the wrong word for it and the project said so in advance (SPEC Section 1: a result of "no, the buoy adds nothing" is a complete and successful outcome), but this is the branch the question was written for, and the pre-registered position is the one taken: **write up the null and stop.** Concretely — the rule was run once and not re-run; nothing was tweaked after the number was seen; the seal is spent and no second held-out evaluation exists to be had; and the next phase is **Phase 8, the write-up**, not a fresh model, a different swell variable (Q27), a different storm definition (Q26's multi-day idea), or a re-opened Stage 3. Two things did tug in the other direction and are recorded so the decision is visible rather than assumed: the held-out ratio came out slightly **above** 1.0 where exploration was below it, and PSS was fractionally positive — half of S. Neither was treated as a reason to look again, because SPEC 8.4 stated before unsealing that a ratio near 1.0 is indistinguishable from 1.15 on six winters, and re-running to chase the gap is exactly what burns the seal. If anyone ever wants to pursue that sliver, it needs a fresh study with its own sealed winters, not an addendum to this one. |
| Q15 | Does the folklore rule need the held-out set at all? | **Resolved (Phase 6, Session 6, 2026-08-09)** | The folklore's 14-day lag was specified by someone else, years ago, without reference to our data. So testing exactly 14 days is arguably a genuine out-of-sample test that could run on all seasons. Tempting, but it opens a door. Current position: run it on held-out like everything else. Revisit in Phase 6 only if there is a clear argument. **Resolved: yes — the folklore rule IS tested on the held-out set, and it is now the ONLY thing tested there.** No clear argument to the contrary appeared, and the gate's closure made the question sharper rather than moot: with the four-model comparison not run (SPEC 8.1), the held-out set has exactly one job left, which is the confirmatory one-shot test of the folklore rule (SPEC 8.2). The "test it on all seasons instead" option was rejected for the reason originally recorded — the door it opens is that every subsequent choice becomes arguable as "also specified elsewhere", and the seal's value is that nobody has to adjudicate that. One shot, six winters, Section 8 as written. |
| Q8 | Is DPD/MWD filtering worth it? | **Parked — possible future work (Phase 6, Session 6)** | A long-period swell from the northwest indicates a distant, energetic North Pacific storm. Short-period swell is local wind chop. Filtering for the former may sharpen the signal considerably. Adds complexity. ~~Decide in Phase 5, Stage 2.~~ Stage 2 did not take it up (the lag scan swept pop thresholds, not swell variables). **Parked in Phase 6: not part of the locked folklore rule (SPEC 8.2), which uses `wvht_mean` alone, and not pursued.** The reason is not that the idea is bad — Q27 argues it is the most physically motivated of the untested alternatives — but that testing it now would be searching for a variable that clears a bar after the declared one failed, which is precisely the multiple-comparisons trap (rule 2.3). It would need a fresh study with its own sealed set, not a Phase 7 addendum. |
| Q16 | Which pop definitions to test in Phase 5, Stage 1 | **Resolved (Phase 5a, 2026-08-09) — declared and frozen before any matching** | Candidates: absolute WVHT threshold, rolling z-score above N, day-over-day rate of rise, and sustained elevation for N days. The set must be small and declared before Stage 1 runs, not expanded when early ones disappoint. Record the declared set here before running. **Resolved: two definitions, each a declared SWEEP rather than a single line.** Sweeping rather than picking turns the threshold from a decision we could get wrong into a result we observe — every level is reported at once, so no shape can be produced by a lucky choice. Two of the four candidates (day-over-day rate of rise, sustained elevation for N days) were NOT taken up; the set was fixed at two and not expanded. **(1) Absolute — percentile sweep** on daily `buoy_51001_wvht_mean`, flagging days at or above the 50th / 75th / 85th / 90th / 95th percentile of the exploration-winter distribution. Resolved metre values, computed from marginal distribution only (n = 2,840 defined winter days, mean 2.862 m, sd 0.870 m): **p50 = 2.7333 m, p75 = 3.3111 m, p85 = 3.6718 m, p90 = 3.9530 m, p95 = 4.4862 m.** **(2) Z-score — sd sweep** at **0.5 / 1.0 / 1.5 / 2.0** sd above the trailing 30-day rolling mean (window shifted one day, so a day is never compared against a mean containing itself). Flagged fractions of defined days: 0.2648 / 0.1527 / 0.0855 / 0.0457. The rolling window is computed **within each winter**, not across the calendar year — reaching back into October would mean loading days the season loader deliberately does not return, and reaching across a summer risks a window touching a sealed winter. Cost: the first ~20 days of each winter have no z-score (2,515 of 2,900 winter days defined); those days are excluded from the sample and counted, never read as "no pop" (see Q24). Both sweeps, and the resolved metre values, were written here **before** any pop-storm matching was run (`uv run python -m powderbuoy.events --calibrate-only`, then the full run). **No "best" threshold is chosen in this session.** **NOTE FOR PHASE 6:** locking the protocol requires committing to ONE operating threshold to test on the held-out set. That choice must be made by a **rule declared in advance** — e.g. "the point of steepest slope in the exploration curve" or "the strictest threshold retaining at least N pop events" — and **never** by picking whichever threshold gave the highest exploration skill. Choosing the operating point to maximise the exploration result would be fishing. The sweep informs that choice; it does not license cherry-picking it. **The NOTE FOR PHASE 6 is now discharged (Phase 6, recorded Session 7, 2026-08-09): the operating threshold is `abs_p90` at the fixed 3.9530 m (SPEC 8.2), chosen by a rule declared in advance and not by score.** The declared rule was the one this note asks for, in two parts: abs_p90 was Phase 5a's **pre-declared primary configuration** (`PRIMARY_POP_PERCENTILE = 90`, fixed in `events.py` before any matching ran), and it is the strictest level leaving a workable event count on six winters (142 usable occasions over 16 exploration winters, against 87 at p95). It is emphatically not the best-scoring level — all nine swept thresholds came in below their own base rate (F2), so there was no best to pick. **The metre value carries over fixed; the percentile is never recomputed on the held-out distribution**, which would let the test set set its own threshold. The sweep table itself stays as the frozen calibration record. |
| Q9 | Should GEFS Reforecast v12 be added as a comparison forecast? | Deferred | Free on AWS Open Data. Would let us compare against a real operational week-2 forecast, which is the strongest possible baseline. Heavy: large downloads, complex format. Revisit only if Phase 7 shows the buoy has skill. |
| Q10 | Monthly indices (ENSO, PDO) joined to daily data | **Resolved** | Resolved in Session 0C. A month's value is treated as available from the **first day of the following month** — January's ONI/PDO value populates daily rows from 1 February onward, until superseded by February's value (available 1 March), and so on. Never interpolated between months; the last available value is held flat (a step function), matching the general "no silent fill" spirit of rule 2.5 while being an explicit, declared exception for this specific, session-specified convention. `climate_daily` carries a boolean `nino34_is_ffilled` / `pdo_is_ffilled` column, always true, marking every daily value as a carried monthly figure rather than a daily measurement. Implemented in `_lag_monthly_to_daily` (`src/powderbuoy/ingest/climate.py`): a monthly value at month M is re-labelled onto month M+1's key (the first point at which it is knowable), then held flat forward across any genuinely missing months. Verified in `tests/test_climate.py` — January's ONI value appears from 1 February, never within January, and 15 February reads January's value because February's own figure is not yet available until 1 March. If a later phase wants a different convention (e.g. a shorter or longer lag), that is a recorded protocol change, not a silent edit. |
| Q11 | Snow quality versus storm occurrence | Deferred | SWE says how much water fell, not whether it was good skiing. Adding temperature would allow a powder-quality target. Out of scope for now (SPEC Section 11). Revisit only after the core question is answered. |
| Q12 | Timezone alignment between buoy and snow data | **Resolved** | Buoy timestamps are UTC. SNOTEL observation dates are local. At lead times of one to two weeks a one-day offset is immaterial, but it must be documented rather than assumed away. Record the convention during the SNOTEL session. Resolved in Session 0B: SNOTEL records in Pacific Standard Time (UTC−8, fixed, no daylight saving). The daily WTEQ/PREC/TAVG value is the midnight-PST reading, assigned to the day that just ended (interval-ending convention — confirmed as the AWDB API's default `periodRef=END` behaviour, Q4). Buoy data is aggregated on UTC calendar days (`buoy_daily`, Session 0A). The two day-definitions differ by 8 hours. Neither series is shifted to match the other — `snow_daily.date` stays a native PST day, `buoy_daily.date` stays a native UTC day. At the one-to-two-week lag under study this offset is immaterial, but any code that joins the two tables must treat `date` as "the calendar day in that table's own native timezone," not as a globally aligned instant. |
| Q17 | Statistical power — can the models even be told apart? | **Closed as moot for the model (Phase 6, Session 6) — the underlying point carried into SPEC 8.4** | Raised in the pre-build review (item 6). Originally framed around "at most ~40 winters"; **the confirmed figure is 22 usable winters, 16 of them exploration and 6 held-out** (Q13/Q21, SPEC Section 7 and 11.1) — roughly half what the question was written around, which strengthens the concern rather than weakening it. With 16 exploration winters and leave-one-season-out CV, the difference in skill between models A/B/C/D may be smaller than the error bars. A concrete instance is already on record: Phase 5a's counting rests on **dozens** of independent events, not thousands — 87–265 pop events per definition and 111 storm events at 1.0 in `any2` over the 16 winters (F2). Phase 5b adds a second instance from the other direction: requiring MJO amplitude > 1 and a defined buoy day leaves a few hundred days per phase group, not thousands. "We cannot distinguish them" is a third kind of null, alongside "no signal" and "signal present". The Phase 6 protocol must state, before unsealing, what size of skill difference counts as meaningful — not just its sign. Otherwise a tiny, meaningless edge gets over-read. ~~**Still open** — the question is what threshold of difference counts, and that is Phase 6's to answer.~~ **Closed in Phase 6 (Session 6, 2026-08-09), in two halves.** (1) **Moot as asked.** The question is "can models A/B/C/D be told apart" — and the four-model comparison is not run at all, because the Stage 3 gate did not open (SPEC 8.1, F3). There are no models to tell apart, so the concern cannot bind. (2) **The underlying small-sample point still applies, and is answered where it now lands** — the folklore held-out test. SPEC 8.4 states the size bar before unsealing (ratio ≥ 1.20 with positive PSS, under both matching variants) and records the honest limit in the same breath: six winters give a directional answer, not a precise one, with roughly 50 pop occasions and roughly 90 storm events expected from exploration's own rates — dozens of autocorrelated events, not thousands. A ratio near 1.0 cannot be told from 1.15 on this sample, and SPEC 8.4 says so in advance rather than after the fact. If MJO modelling is ever revived, this question reopens with it. |
| Q18 | Does buoy swell actually correlate with MJO phase? | **Resolved (Phase 5b, Session 5b, 2026-08-09)** | Raised in the review (item 8). The entire "is it just a crude MJO index" framing assumes buoy wave height and MJO state are related. Plausible but unchecked. This is cheap to look at early, on exploration seasons only, and if they turn out unrelated the central experiment's framing needs rethinking. ~~Schedule a quick look in Phase 5, Stage 1.~~ Stage 1 ran without it — the Phase 5a prompt scoped MJO out entirely — so the quick look moved to **Phase 5b**, this session, as its Link A. **Answered: see finding F4.** In short: **not at a useful strength.** Swell at 51001 is higher on favourable-phase days (6–8, amplitude > 1) than on unfavourable-phase days (2–4, amplitude > 1) — mean 2.9798 m against 2.8204 m, a difference of +0.1594 m — but that is only **0.18 of a pooled sd**, below the 0.2 sd bar declared before the run. The direction matches the hypothesis; the magnitude does not support the framing. **What this changes:** the central experiment's "is the buoy just a crude MJO index?" question (SPEC 1.3, Section 7 model D) now has a measured answer to its premise — the buoy is a *very* crude MJO index, crude enough that models C and D would be unlikely to separate on MJO content even if the sample allowed it (Q17). Phase 6 should frame the four-model comparison knowing this rather than assuming the buoy↔MJO relationship is strong. Reopen only if a different buoy variable (DPD/MWD filtering, Q8) or a multi-day swell aggregate turns out to track MJO state materially better — neither was tested here, and testing them would be a fresh question, not a re-run of this one. |
| Q19 | Is the Nov 1 – Apr 30 season definition right? | **Resolved (Phase 6, Session 6, 2026-08-09) — keep Nov–Apr** | Raised in the review (item 9). The Wasatch gets snow in October and May, so the cutoff is somewhat arbitrary, yet it defines the unit that everything splits and scores on. Sensitivity to widening it (e.g. Oct 15 – May 15) should be checked once data is in. Load-bearing enough to write down; probably not worth changing. **Status note (5b):** the Nov–Apr window is still an assumption, and it has now been load-bearing for every number in Phases 4, 5a and 5b — it defines the split unit, bounds the z-score's trailing window (Q24), and bounds every contingency window (a window that would run past 30 April is dropped rather than followed into May). **Phase 6 must decide it explicitly** — keep Nov–Apr, or widen it — because Section 8 freezes the unit everything is scored on. Not changed in 5b; that would be scope creep and would invalidate the Phase 5a numbers it shares winters with. **Decided in Phase 6: KEEP Nov 1 – Apr 30, unchanged, written into SPEC 8.2.** The reasoning is the one the question itself anticipated: the window is somewhat arbitrary at its edges, but it is load-bearing for every number in Phases 4, 5a and 5b, and the held-out result's whole meaning is that it is compared against an exploration baseline built on the same unit. Widening it now would change the comparison, not improve it — the sensitivity check the question asks for would have to be run on exploration data *and* would then require re-running Phase 5 to keep the baseline comparable, which is a different project. The cost is stated plainly rather than assumed away: October and May storms are outside the study entirely, and any occasion whose 10–18 day window would run past 30 April is dropped rather than followed into May, so late-April pops are systematically under-sampled. Both apply identically to exploration and held-out winters, so they bias the comparison in neither direction. If a future study wants Oct 15 – May 15, that is a fresh split and a fresh seal, not an amendment. |
| Q20 | Might combining SNOTEL stations hide real signal? | **Parked — possible future work (Phase 6, Session 6); the combination rule itself is now fixed in SPEC 8.2** | Raised in the review (item 7). Little Cottonwood and Big Cottonwood can get very different snowfall from the same system. Averaging or maxing across canyons (Q5) could blur a signal that is sharp at one site. Worth checking per-station behaviour in Phase 5 before committing to a combination rule in Phase 6. **Phase 5a result (EXPLORATORY):** checked at a high level, three ways — per-station, `any2` (≥2 of the reporting stations over threshold that day) and `mean` (cross-station mean over threshold). **Combining did not blur a signal that is sharp at one site, because no site shows a signal to blur.** Across all 45 per-station configurations at 1.0 in (9 pop definitions × 5 stations), storm-rate-given-pop sits below its own base rate in 44, and the single exception is Louis Meadow at z_1.5sd with PSS = +0.00005 — indistinguishable from zero. The stations do differ markedly in how many storms they record (at 1.0 in: Snowbird 10.2 events/winter, Mill-D North 4.8, Brighton and Thaynes Canyon 4.1, Louis Meadow 5.5 over its 10 measured winters), so the base rate a combination produces varies a lot — `any2` runs consistently looser than `mean` (at 1.0 in, 111 storm events vs 75). That matters for how a rate is read, but it did not change the direction of any result. Nothing here argues for or against a particular combination rule on signal grounds; Phase 6 should choose on definitional grounds (which is the more honest description of "a Wasatch storm") together with Q5 and Q6. **Phase 6 outcome, in two parts.** (1) The combination rule *is* now chosen, on the definitional grounds this question asked for: **`any2` at 0.5 in** (SPEC 8.2), because it produces the event count a Wasatch winter plausibly contains (Q26/F1) — not because of anything in the per-station table above. (2) The question as asked — *might* combining hide a canyon-sharp signal — is **parked as possible future work, not pursued.** Nothing beyond `any2` and `mean` is tested in the locked rule, and a per-station or per-canyon variant of the folklore test would be a fresh set of comparisons on the same six winters, which the seal exists to prevent (rule 2.3). Phase 5a's evidence is that there is no site-level signal to blur, so the expected value of pursuing it is low; that is a judgement, not a proof, and it is recorded as parked rather than answered. |
| Q21 | Primary buoy record-length risk | **Resolved (Phase 4, Session 0D, 2026-08-08)** | Raised in the review (item 5), written into SPEC Section 6.0 with a Plan B. Session 0A measured it: 51001's historical archive has no station-year files at all for 2010–2014, a 2,068-day (5.7-year) continuous gap from 2009-12-25 to 2015-08-23, on top of scattered smaller gaps (22.2% of days null overall). The two-buoy correlation is strong where they overlap (0.98, well above the 0.9 bar), so 51001 remains the right primary station — this is not a Q1 reversal. But the true continuous record is shorter than "~40 winters" implied: excluding the 2010–2014 hole, 51001 usefully covers roughly winters 1981–2009 (~28 winters) plus 2015–2025 (~10 winters), not one unbroken 40-winter span. Whether to treat this as one record with a hole, split it into two eras, or drop the shorter post-gap era is a Phase 4 decision, not a Session 0A one — Phase 4 is where seasons get chosen. Recorded here so it isn't lost before then. Linked to Q1. **Resolved by the Phase 4 split (Q13):** treated as two eras, split chronologically within each era (Option D) rather than as one record with a hole or by dropping the shorter post-gap era. 22 winters usable once MJO coverage is also required; 14 pre-gap, 8 post-gap. Neither era is dropped — both are represented in both the exploration and held-out sets. This is Plan B's decision point (SPEC 6.0), landed on: proceed with a shorter, two-era record and a correspondingly smaller (6-winter) held-out set, rather than pausing to reconsider scope — accepted as the recorded limitation in Q13. |
| Q22 | Should `apd_mean` be added to SPEC Section 5.1's `buoy_daily` schema? | **Resolved** | Surfaced in Session 0A's consistency check. SPEC 5.1 lists `wvht_*`, `dpd_*`, `mwd_mean`, `wspd_*`, `pres_*`, and `n_obs` for `buoy_daily`, but not `apd_mean`. The Session 0A prompt's Step 5 output-schema table — captioned "matching SPEC Section 5.1" — includes `apd_mean` (mean of valid APD) anyway. `buoy_daily.parquet` was built with `apd_mean` included, following the session prompt. SPEC.md is the stable document; it should either gain `apd_mean` or the column should be dropped. Owner to decide. Added to SPEC 5.1 in Session 0B. Spec now matches the built table. |
| Q23 | The BoM MJO calculation-method seam, end of 2013 | **Resolved (Phase 6, Session 6, 2026-08-09) — checked, not adjusted; outcome mixed and recorded** | Raised by the session prompt for 0C, written into SPEC 3.3's Session 0C addendum. BoM changed its RMM calculation method at the end of 2013 — original Wheeler–Hendon (2004) through 2013, a modified method (the file's own label calls it `Gottschalk10_method`) from 2014 onward. This study's usable winters straddle that boundary. Same class of hazard as the buoy's file-format eras (Q2-adjacent) — an artificial seam that could masquerade as a real change in the underlying signal. Not corrected or adjusted for in Session 0C, per instruction. `climate_daily.mjo_method` marks every row `WH2004` (date ≤ 2013-12-31) or `modified2014` (date ≥ 2014-01-01), computed from the date rather than trusted from the source file's own per-row label (confirmed in Session 0C to switch at exactly that boundary, matching the date-based computation). Whether the seam matters — e.g. whether lag-scan or modelling results differ materially before vs. after 2014 — is a Phase 5 question, not decided here. **Phase 5a: does not affect this session, and remains open for Phase 6.** Stages 1–2 are pure counting of buoy wave height against SNOTEL SWE; no MJO column is read at any point, so the RMM method seam cannot touch any number in the Phase 5a report. The seam becomes live again the moment the four-model comparison uses MJO features (models B and D, SPEC Section 7), which straddle the 2013/2014 boundary — 10 of the 16 exploration winters are pre-seam and 6 post-seam. Still to be decided in Phase 6: whether to adjust for it, restrict to one side, or carry `mjo_method` as a flag and report sensitivity. **RESOLVED IN PHASE 6, by the third option: carry the flag, run the sensitivity split, adjust nothing.** The seam went live in Phase 5b (one phase earlier than this entry anticipated), so Phase 6 re-ran the Phase 5b declared Link A and Link B tests, unchanged, separately on the 10 pre-seam exploration winters (1989–2003, `WH2004`) and the 6 post-seam ones (2015–2020, `modified2014`), reported beside the pooled numbers. No winter straddles the seam — measured from the dates, not assumed; the 51001 archive hole removed winters 2009–2014, and winter 2013 is the only winter that could have straddled it. Exploration winters only; no held-out winter was touched. Full output in `outputs/phase6_seam_check_report.txt` and `outputs/figures/mjo_seam_check.png`. **The outcome is mixed, and both halves are recorded rather than the convenient one.** *(a) Link A — the seam does not change the story.* Effect size pooled +0.1785 sd, pre-seam +0.2347, post-seam +0.0911. Both eras point the same way (swell higher in favourable phases) and both sit far below the declared "clear" mark of 0.5 sd; they straddle the declared "present" mark of 0.2, so the verdict *label* differs between eras while the substance does not — a +0.215 m difference against a 0.915 m within-group spread pre-seam, and +0.077 m against 0.845 m post-seam. Neither era makes wave height a usable read on MJO state. **F4 stands.** *(b) Link B — the eras disagree, and the pooled numbers are method-blended.* The two eras fall on the same side of the 1.10 ratio bar in 2 of the 4 declared cells and on opposite sides in the other 2, both of them lagged: at 1.0 in the ratio is 0.906 pre-seam against 1.507 post-seam, and at 0.5 in it is 0.916 against 1.129. **The pooled Phase 5b Link B figures (F5) must therefore be read as blending two calculation methods**, and this is a caveat for the write-up. *(c) F6's ordering.* F6 read the chain as "Link A weaker than Link B in every framing". That holds pooled and post-seam, and **reverses pre-seam**, where Link A is "present but small" while lagged Link B runs contrary at 0.906. So the chain read is era-dependent in its ordering even though the Link A conclusion is not. **What this does and does not touch.** It does not touch the locked protocol at all: SPEC Section 8 uses no MJO feature — the folklore rule is buoy → snow — so the seam cannot reach any Phase 7 number. It touches the *mechanism* narrative only, which is EXPLORATORY throughout. Note the arithmetic limit honestly: the seam is perfectly confounded with era here (pre-seam = 1989–2003, post-seam = 2015–2020), so nothing in this check can separate a method artefact from a genuine two-decade difference in the atmosphere or in the buoy record, and no attempt is made to. Sub-samples of 10 and 6 winters, EXPLORATORY, not findings. |
| Q24 | Should the trailing z-score window warm up from October, rather than starting cold each winter? | **Closed as moot (Phase 6, recorded Session 7, 2026-08-09) — the z-score pop definition is not in the locked rule** | The z-score pop definition (Q16) scores each day against the trailing 30-day mean of `wvht_mean`. Phase 5a computes that window **within each winter**, so the first ~20 days of every winter have no z-score at all: 2,515 of 2,900 exploration winter days are defined, 385 are not. Those days are excluded from the sample and counted, never read as "no pop" (rule 2.5). The alternative — warming the window up from October — was deliberately not taken, for two reasons: `load_analysis_data` returns winter days only, so October days would have to be loaded outside the sanctioned loader, and a window reaching across a summer is one step closer to a window touching a sealed winter. Neither risk was worth taking for ~13% of the sample in an exploratory session. The cost is real, though: early-winter pops are invisible to the z-score definition and November is systematically under-represented in it, while the absolute/percentile definition covers the whole winter. Phase 6 should decide explicitly — warm up from a declared pre-season window, keep the cold start, or drop the z-score definition — and if it warms up, the mechanism must be auditable against rule 2.3. **Decided by the third option, which makes the warm-up question moot: SPEC 8.2's pop definition is the absolute threshold `buoy_51001_wvht_mean` ≥ 3.9530 m, and no z-score is computed on held-out data at all.** So no day in Phase 7 is excluded for want of a trailing window, and the cold-start cost recorded above applies only to the Phase 5a exploratory tables, where it stays on record. This reopens only if a future study revives the z-score definition, and then it must be answered before the run, not after. |
| Q25 | The occasion and comparison-window construction behind the 2×2 must be locked in Phase 6 | **Resolved for the locked rule (Phase 6, Session 6, 2026-08-09)** | Phase 5a had to invent the counting frame, and the choices are consequential enough that Phase 6 must adopt or replace them deliberately rather than inherit them by default. Three, all documented in `contingency_from_flags`: **(1) The unit is an anchor day.** Pop occasions are pop-event first days (one per event, so a five-day swell is one forecast); non-pop comparison occasions are every other day of the same winters lying outside any pop event; days inside a pop event after its first day belong to neither row. Both rows require a defined pop flag and a window fitting inside the same winter. **(2) One-to-one claiming is applied to the pop row only** — pops in date order each claim the earliest unclaimed storm in their window — while the non-pop base-rate row scores every window independently. This is deliberately conservative for the pop row, but it is **not** a small effect: at 1.0 in `any2` the primary configuration's storm-rate-given-pop is 0.2676 with claiming and 0.3239 without, against a base rate of 0.3331. Across all 54 configurations, storm-rate-given-pop falls below the base rate in 54 with claiming and in only 32 without. Phase 6 must decide whether the locked protocol claims, and must apply whatever it decides to both rows or justify the asymmetry. **(3) PSS is bounded by pop rarity here**, because the pop row holds dozens of occasions and the comparison row thousands, so POD is small by construction and PSS magnitudes are not comparable across thresholds — only the sign is, and the row-conditional storm-rate-versus-base-rate comparison is the readable one. If Phase 6 wants comparable PSS magnitudes it needs a balanced occasion design (e.g. matched sampling of non-pop anchors), declared in advance. **RESOLVED: the Phase 5a construction is ADOPTED, deliberately and item by item, into SPEC 8.2 — not inherited by default.** (1) **The anchor-day occasion is kept**, unchanged: pop occasions are pop-event first days, non-pop comparison occasions are every other day of the same winters outside every pop event, days inside a pop event after its first day belong to neither row, and both rows require a defined pop flag and a window fitting inside the same winter. Kept because it is the construction every exploration number was built on, and the held-out result is only interpretable beside those numbers. (2) **The claiming question is settled by reporting BOTH variants** — one-to-one claiming and without-claiming — declared now, with neither designated "the answer". This is the honest resolution of the asymmetry the question flags: on exploration data the choice moved storm-rate-given-a-pop by about 0.06 and flipped 22 of 54 configurations from below-base-rate to at-base-rate, which is far too large to settle by preference after seeing the held-out number. The comparison row stays unclaimed in both variants, and SPEC 8.2 states that asymmetry and its direction (conservative for the pop row) rather than burying it. SPEC 8.4's verdict requires the *same* answer under both variants before anything is called skill, which is what makes reporting both a decision rather than a hedge. (3) **PSS magnitude is not made comparable**, and no balanced occasion design is adopted: SPEC 8.3 records that PSS magnitude is bounded by pop rarity in this design and that only its **sign** is used, with the row-conditional storm-rate-versus-base-rate comparison carrying the verdict. Introducing matched sampling now would produce a table with no exploration counterpart. |
| Q26 | The 1.0-inch storm threshold detects far fewer storms per winter than a Wasatch winter plausibly contains | **Resolved (Phase 6, recorded Session 7, 2026-08-09) — acted on: the locked rule uses 0.5 in `any2` (SPEC 8.2)** | Phase 5a's detector validation (4a) counted storm events per winter across the declared thresholds on the 16 exploration winters. Against the ~15–30 meaningful storms a Wasatch winter roughly contains: **0.5 in** gives `any2` 15.4 events/winter (min 12, max 19) and `mean` 13.5 — plausible. **1.0 in** gives `any2` 6.9 (min 2, max 13) and `mean` 4.7; **1.5 in** gives `any2` 2.3 and `mean` 1.4 — both implausibly few, and flagged in the report rather than silently fixed. The eyeball check (4b) shows the same thing from the other side: at 1.0 in every mark lands on a real step-up in the 2016 SWE curve, but a clear multi-day accumulation in early February 2017 (roughly 22.4 → 25.2 in over about a week, at 0.4–0.75 in/day) carries no mark at all, because no single day reached 1 inch at two stations. The threshold is not detecting a storm; it is detecting a storm's biggest single day. This is not a bug in `detect_events` — the independent precipitation cross-check (4c) put SWE-detected storms at 111 of 111 coincident with gauge precipitation, so what the detector finds is real weather. It is a definitional problem with what "a storm day" means. Two things follow for Phase 6 (Q6): 0.5 in has the better claim to being the storm definition, and a threshold on a *multi-day* accumulation rather than a single day's gain would match the physical event better than any single-day threshold does. Not acted on in Phase 5a — out of scope, and changing the threshold after seeing results would be exactly the fishing rule 2.2 forbids. **Acted on in Phase 6, in the first of the two ways this entry suggests:** SPEC 8.2 fixes the storm definition at **0.5 in `any2`**, taking the threshold this entry says has the better claim, and states the reasoning as a detector argument made before the box was opened. **The second suggestion — a multi-day accumulation threshold — was NOT taken**, and deliberately so: it is a new detector with no exploration counterpart, so a held-out number produced with it could not be compared against anything (SPEC 8.1). It remains the better physical description of a storm and is on record here for any future study. Closed as a status correction; the substance was decided in Phase 6. |
| Q27 | Would a different swell variable track the MJO better than daily mean wave height? | Open — raised in Phase 5b | Link A (F4) tested exactly one variable: `buoy_51001_wvht_mean`, a single day's mean significant wave height. It came out at 0.18 sd — right direction, too weak to use. That is a result about *that variable*, not about the buoy in general. Untested and plausible alternatives: long-period swell only (DPD/MWD filtering — this is Q8, and SPEC 3.1 argues a long-period NW swell is the actual signature of a distant North Pacific storm while short-period swell is local chop); a multi-day swell aggregate rather than a single day, since MJO state persists for weeks and a daily value is mostly noise around it; or 51101 over its shorter record. Any of these could plausibly move 0.18 sd upward. **This must not be run as a search.** Testing variables until one clears the bar is the multiple-comparisons trap the seal exists to prevent (rule 2.3), and Q18 is resolved on the variable that was declared. If Phase 6 wants a different swell variable it should pick one on physical grounds, declare it, and accept the result. |
| Q28 | Phase 6 must declare the MJO lag/window by rule, not by scan | **Closed as moot (Phase 6, Session 6) — no MJO is scored in the locked protocol** | Phase 5b ran Link B at exactly two framings, same-day (0–0) and lagged (1–14), **both declared before the run** specifically so that no framing could be chosen after seeing which flattered the result. That was the right discipline for a mechanism check, but it means the MJO's own best lag into the Wasatch is genuinely unknown here — 1–14 days is a reasonable reading of the subseasonal literature, not a measured optimum for this record. If the Phase 6 protocol scores anything on MJO state it must fix the window **by a rule declared in advance** (e.g. "the subseasonal 1–14 day window as used in the literature"), exactly as Q16 requires for the pop threshold. A lag scan over MJO framings would carry the same multiple-comparisons hazard that made the buoy lag scan (F3) uninterpretable without the seal, and would burn exploration freedom for very little. **Closed as moot: the locked protocol scores nothing on MJO state.** SPEC 8.1 records that the four-model comparison is not run (the gate did not open) and SPEC 8.2's rule is buoy → snow with no climate feature at all, so there is no MJO window for Phase 6 to declare. The discipline the question asks for was in any case already met where it mattered — Phase 5b's 1–14 day window was declared before the run, from the subseasonal literature, and was not moved afterwards; Phase 6's seam check re-used it unchanged rather than re-choosing it. This reopens only if MJO modelling is ever revived, and then it must be answered before, not after. |
| Q29 | Is amplitude > 1.0 the right coherence bar, and what is lost by excluding a third of the sample? | **Closed as moot (Phase 6, Session 6) — no MJO feature is used in the locked protocol** | The declared test follows the standard convention that amplitude below 1.0 means "no coherent MJO" (SPEC 3.3). Measured cost on the exploration winters: **942 of 2,900 winter days (32.5%) are excluded** by that condition alone — far more than either the buoy gap or the MJO record's end costs this project. Those days are not missing data; they are days with a real but weak MJO, dropped by a convention. Two things for Phase 6 if it uses MJO features (models B and D, SPEC Section 7): a model does not need the binary phase-group frame at all — it can take RMM1/RMM2 or amplitude as continuous inputs and use every day — and if a threshold *is* used, whether it is 1.0 must be declared rather than inherited. Not varied in 5b: sweeping the amplitude bar to see which value looks best is precisely the fishing rule 2.2 forbids. **Closed as moot for the same reason as Q28:** models B and D are not built (SPEC 8.1) and the locked folklore rule uses no MJO column, so no amplitude bar is applied to anything Phase 7 scores. The measured cost stays on record as a fact about Phase 5b's exploratory numbers — 942 of 2,900 exploration winter days (32.5%) excluded by the convention, not by missing data — and Phase 6's seam check inherited the same bar unchanged rather than re-choosing it, so its sub-samples carry the same exclusion. This would matter again only if MJO modelling were revived, in which case the advice above stands: a model can take RMM1/RMM2 or amplitude as continuous inputs and use every day, and any threshold must be declared rather than inherited. |
| Q30 | SPEC 8.3's "base rate" — the formula and its prose gloss are not the same quantity | **Ambiguity in the frozen Section 8, recorded not fixed (Phase 7, Session 7, 2026-08-09); reading taken: the formula** | SPEC 8.3 defines **base rate = `(a + c) / (a + b + c + d)`**, over every occasion in the table. Two paragraphs later, under "Baselines, defined precisely", it glosses climatology as "the storm rate over the **non-pop comparison occasions** drawn from the same six held-out winters" — which is `c / (c + d)`, a different quantity, because the formula's numerator and denominator both include the pop row. **The reading taken, and why: the formula, exactly as written.** It is the definition SPEC 6.1 has carried since Phase 5a, it is what `contingency_from_flags` computes, and it is what every exploration number the held-out result is compared against was built on — taking the gloss instead would produce a held-out base rate with no like-for-like exploration counterpart. **Section 8 was NOT edited to match** (rule 2.3, SPEC 8.5). **Nothing turns on it here**, which is why it is recorded as a curiosity rather than a problem: the two differ by 0.0023 on this sample (0.6339 by the formula, 0.6316 by the gloss), and the verdict is identical under either — ratio 1.0755 against the formula, 1.0795 against the gloss, both far below the 1.20 bar. Both numbers are reported in `outputs/phase7_holdout_result.txt`. A note for any future protocol: say which of the two is meant, once, in the same place. A second, smaller consequence of the same formula: because `a` appears in the base rate, the base rate is strictly a per-variant quantity rather than a shared constant, and is computed per variant here (identical on this sample, since the variants agreed on `a`). |
| Q31 | The experiment register has one `primary_value` column, but SPEC 8.2 privileges neither matching variant | **Ambiguity between Section 9 and the frozen Section 8, recorded not fixed (Phase 7, Session 7, 2026-08-09); reading taken: with-claiming in the column, both in the notes** | SPEC 8.2 declares both matching variants and states that neither is "the answer". SPEC Section 9's register schema gives a run one `primary_value` and one `baseline_value`, so writing the row forces a choice the protocol deliberately declined to make. **The reading taken:** the **with-claiming** figures go in `primary_value` / `baseline_value` (it is the conservative variant, the one that cannot manufacture hits from a busy fortnight), and **both variants' storm rates, base rates, ratios and PSS are written in full into the row's `notes`**, so the register never implies a ranking Section 8 refused to state. Section 8 is frozen and was not edited; Section 9 was widened this session only in its "every model run" framing (H3), not in its columns. **Moot in fact on this run** — the two variants came out identical (F7), so the column holds the same number either way. It would not be moot on a future run, and the right fix then is a register that can carry a variant label per row, or two rows, not a silent choice. |

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

### F7 — The held-out test: the folklore rule does not clear its own pre-declared bar (Phase 7, Session 7, 2026-08-09) — **the project's first and only CONFIRMED finding**

- **Hypothesis.** The folklore's own claim, as specified by other people years before this
  study: a buoy pop is followed by a Wasatch storm about two weeks later, more often than
  chance. Tested as "a storm event *begins* 10–18 days after the pop event's first day",
  on six winters no choice in this study was tuned on.
- **Method.** SPEC Section 8, executed literally and once, frozen at spec version 0.8 and
  written before any held-out winter was read. `load_analysis_data(include_holdout=True)`
  called once — the project's single authorised unsealing (SPEC 8.2, 8.5) — over the six
  held-out winters **scored on their own** (2004, 2005, 2006, 2008, 2021, 2022; 1,086
  winter days). Pop day = `buoy_51001_wvht_mean` ≥ the **fixed 3.9530 m** (the percentile
  was **not** recomputed on held-out data); storm day = `swe_gain_in` ≥ 0.5 in at ≥ 2 of
  the reporting stations (`any2`); events by `detect_events`, bridge = 1, dated by first
  day; occasions by `contingency_from_flags`, `lag_lo=10`, `lag_hi=18`, grouped by winter —
  the same tested machinery every exploration number came from, so the comparison is
  like-for-like. Both matching variants reported, neither privileged. The verdict bar,
  **S = (ratio ≥ 1.20 AND PSS > 0)**, was fixed in SPEC 8.4 before unsealing and was not
  moved afterwards. `src/powderbuoy/holdout_eval.py`,
  `outputs/phase7_holdout_result.txt`.
- **Result, with its baseline.** The two matching variants came out **identical**:

  | variant | a | b | c | d | storm rate given a pop | base rate | ratio | POD | POFD | PSS |
  | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
  | with one-to-one claiming | 30 | 14 | 564 | 329 | **0.6818** | **0.6339** | 1.0755 | 0.0505 | 0.0408 | +0.0097 |
  | without claiming | 30 | 14 | 564 | 329 | **0.6818** | **0.6339** | 1.0755 | 0.0505 | 0.0408 | +0.0097 |

  Counts: **44 pop events, 44 usable pop occasions, 893 non-pop occasions, 97 storm
  events, 0 days with an undefined pop flag** (51001 reported on all 1,086 held-out winter
  days, and all five SNOTEL stations reported on every one of them). Storm rate over the
  non-pop comparison occasions alone, `c/(c+d)` = 0.6316 (see Q30).
  **Verdict, applied mechanically: S is false for both variants (ratio 1.0755 < 1.20), so
  the result is NULL CONFIRMED** — SPEC 8.4's expected outcome, and the one it defines as a
  complete, successful result.
  **The exploration comparison, quoted from Phase 5a at the same configuration** (abs_p90
  pop, 0.5 in `any2`, window 10–18, 16 winters), not recomputed: storm rate given a pop
  **0.5563 against a base rate of 0.6308** (ratio 0.8819) with claiming, and **0.6197
  against 0.6308** (ratio 0.9824) without.
- **Implication.** The folklore rule does not clear the bar it was given, on winters it was
  never fitted to. Four things belong with that, none of them buried.
  **(1) The direction differs from exploration, the magnitude does not.** On the held-out
  winters the pop row sits slightly *above* its base rate (ratio 1.0755) where exploration
  had it slightly *below* (0.8819 / 0.9824), and PSS is fractionally positive (+0.0097)
  where exploration was negative (−0.0189). SPEC 8.4 anticipated exactly this trap and
  disarmed it in advance: six winters give a **directional** answer, and a ratio near 1.0
  cannot be distinguished from a ratio of 1.15 on this sample. Half of S holding (PSS > 0)
  while the other half fails by a wide margin is what a null looks like at this sample
  size, not a signal. The honest statement is that the held-out winters are **consistent
  with the exploration null**; it is not that the buoy has a small positive skill, and no
  effect size may be read off 1.0755.
  **(2) The two variants agreeing is a real property of these winters, not a bug.** With
  claiming, a pop can lose a storm to an earlier pop; here none did — the 30 hits claimed
  30 distinct storm events, so no collision occurred among 44 pops across six winters. On
  exploration the same rule cost 9 of 142 pops a hit (0.5563 against 0.6197). The claiming
  question that SPEC 8.2 refused to settle by preference therefore turned out not to bind
  on this sample, which is the strongest form the "both variants" requirement could have
  taken: the verdict is the same under either matching rule.
  **(3) The base rate is high and the window is wide.** At 0.5-inch `any2` a Wasatch winter
  contains ~16 storm events, so about 63% of all nine-day windows contain a storm start
  anyway. This is precisely the failure mode rule 2.2 exists to prevent: a folklore claim of
  "68% accurate" is true here and means nothing, because 63% is what you get for free. The
  held-out set delivers that sentence with a number attached.
  **(4) The sample landed where SPEC 8.4 said it would.** 44 usable pop occasions against a
  predicted "roughly 50", and 97 storm events against "roughly 90" — the advance
  expectation, derived from exploration's own rates, was accurate, so the limitation
  accepted at Phase 4 (Q13/Q17/Q21) is the one that actually applies.
  **What it changes.** Nothing downstream is now gated on a signal: the buoy is not a
  usable predictor of Wasatch storms at the folklore's own lag, out of sample, and Phase 5b
  already recorded *why* (Link A is the break, F4). The project's question is answered, and
  the answer is "no, the buoy adds nothing" — which SPEC Section 1 declares a complete and
  successful outcome. Next is the write-up (Phase 8); see Q14 for the decision taken.
- **Status.** **CONFIRMED.** Held-out winters, scored once, under a protocol locked before
  they were read and not amended afterwards (rule 2.3, SPEC 8.5). Section 8 was not edited
  by this session; the two ambiguities encountered in it are recorded as Q30 and Q31, with
  the reading taken, rather than resolved by editing the frozen text. **The seal is spent
  and cannot be re-sealed. Any further number produced on these six winters is EXPLORATORY
  forever.**

---

### Seam-robustness check (Phase 6, Session 6) — **EXPLORATORY CONTEXT, NOT A FINDING**

**No new finding was produced in Phase 6, and none could be: no held-out data was read.**
This session wrote and froze SPEC Section 8; the only analysis it ran was the pre/post-seam
split recorded against Q23, on the same 16 exploration winters Phase 5b used. Every number
in `outputs/phase6_seam_check_report.txt` is EXPLORATORY context for reading F4–F6 and is
**not** a numbered finding — it is a re-run of already-recorded declared tests on two
sub-samples of 10 and 6 winters, not a new test of a new hypothesis. Recorded here so the
findings log shows what Phase 6 did and did not add.

In one line: **Link A's conclusion (F4) holds in both eras and F4 stands; Link B's (F5)
does not, so the pooled Link B numbers are method-blended; and F6's "Link A weaker than
Link B" ordering reverses in the pre-seam era.** Full numbers and the confounding caveat —
the seam is perfectly confounded with era, 1989–2003 against 2015–2020 — are in Q23. The
findings F4, F5 and F6 are **not amended**; they were correct as run, and Q23 is where the
caveat that qualifies them lives.

Nothing here touches the locked protocol: SPEC Section 8 scores no MJO feature, so the seam
cannot reach any Phase 7 number.

---

### Descriptive-sweep observations (Phase 5b, Session 5b) — **NOT FINDINGS**

This block is deliberately outside the numbered findings and must never be cited as one.
Phase 5b looked at all 8 MJO phases individually as *description*, alongside its declared
2-group test. The declared test (F4, F5) is confirmatory and carries weight because it was
fixed in advance. **Nothing below was pre-specified, nothing below is a test, and nothing
below may be promoted to a finding or a conclusion.** Anything here that looks like a
pattern would need a fresh out-of-sample test to mean anything at all, and this project has
exactly one such test left to spend (rule 2.3). Recorded only so the picture is on record.

- **Link A, swell per phase (amplitude > 1).** Per-phase means span 2.666 m (phase 2) to
  3.015 m (phase 8), a spread of 0.349 m ≈ 0.39 sd, around an all-day mean of 2.862 m. The
  picture is close to flat, and a flat picture across all 8 phases is the honest support for
  the declared test's weak result — not a separate result of its own.
- **Link B, storm rate per phase (amplitude > 1, lagged 1–14).** Rates span 0.3022
  (phase 3) to 0.5078 (phase 1) against a base rate of 0.4525; 3 of 8 phases sit above the
  base rate. Two of the phases sitting highest are **transitional phases (1 and 5),
  excluded from the declared contrast by design** — which is a reminder of exactly why
  single-phase readings at n ≈ 130–280 autocorrelated days are not interpretable.
- **The rule that was not broken:** no observation in this block appears in F4, F5, F6, in
  `STATUS.md`, or in `outputs/phase5b_mjo_report.txt` as a finding. The sweep generated the
  picture; only the declared test answered a question.

---

### F6 — The chain read: Link A is where the folklore breaks (Phase 5b, Session 5b, 2026-08-09)

- **Hypothesis.** Phase 5a falsified the folklore as stated (swell → snow at ~14 days).
  This asks *why*, by testing the two internal links of the chain the folklore skips
  (SPEC 1.3): MJO → swell (Link A) and MJO → snow (Link B). The pattern across the two is
  the finding, not either one alone.
- **Method.** F4 and F5, read together against the branching logic fixed in the session
  prompt before either was run. Link A's verdict comes from the declared effect-size bar
  (0.2 sd), Link B's from the declared rate-ratio bar (1.10) at the lagged primary framing,
  with all four Link B cells reported as the robustness check.
- **Result, with its baseline.** Link A **0.18 sd** (bar 0.2). Link B lagged **ratio 1.133**
  (bar 1.10), against a base rate of 0.4525 — clearing its bar, but failing it at the
  0.5-inch sensitivity threshold (ratio 1.002). **Link A is weaker than Link B in every
  framing tested.**
- **Implication.** **Link A is the break.** The buoy does not track the MJO closely enough
  to be read as a proxy for it, so the folklore fails at its first step and everything
  downstream is moot. Two qualifications belong with that, not after it. First, the Link A
  difference is *in the hypothesised direction* — swell genuinely is higher in phases 6–8 —
  so the physical story in SPEC 1.3 is not refuted; the buoy is simply far too weak an
  instrument for reading it, which is a different and more interesting result than "the
  mechanism is wrong". Second, Link B is the weaker half of the claim and must not be
  over-read: it clears its bar on the primary storm definition and fails on the definition
  Q26 says has the better claim to being "a Wasatch storm". So the honest statement is
  "the MJO→snow link is present at best weakly in this record", not "it is established
  here". Under either reading of Link B, Link A is still the break.
  **Caveats, stated not buried:** (1) **Sample** — 16 exploration winters; the declared
  contrast rests on 736 favourable / 767 unfavourable days for Link A and 694 / 740 for
  Link B lagged, and those days are not independent observations (winter weather is
  autocorrelated and MJO phases persist for days), so the effective sample is much smaller
  than the counts suggest. A weak or absent link here does **not** overturn the published
  MJO/western-US literature — it says the signal is not clearly visible at this scale
  (Q17). (2) **Coverage** — checked rather than assumed, and the assumption was wrong in
  this direction: neither the MJO record's 2024-02-24 end nor 51001's 2010–2014 hole costs
  this session any days, because the exploration winters end 2021-04-30 and the gap winters
  were never in the split. What shrinks the sample is the declared test's own amplitude
  condition — 942 of 2,900 winter days have amplitude ≤ 1.0 and are excluded.
- **Status.** **EXPLORATORY.** Exploration winters only, protocol not yet locked
  (rule 2.3). Not a conclusion.

### F5 — Link B: MJO phase relates to Wasatch storms only weakly, and not robustly (Phase 5b, Session 5b, 2026-08-09)

- **Hypothesis.** Declared before the run: Wasatch storms are more common on
  favourable-phase days (MJO 6/7/8, amplitude > 1) than on unfavourable-phase days
  (2/3/4, amplitude > 1). Grounded in the published western-US precipitation literature.
- **Method.** Storm events reuse the Phase 5a detector unchanged (`detect_events`, 1.0-inch
  `any2` primary, 0.5-inch `any2` as the Q26 sensitivity check). The occasion is a day;
  the outcome is "a storm event *begins* in the window". Two framings, **both declared in
  advance** because the MJO's influence is lagged: same-day (window 0–0) and lagged
  (window 1–14 days). No one-to-one claiming — nothing is being issued as a forecast — and
  both rows are treated identically, so these numbers are comparable to each other but not
  to Phase 5a's pop tables (Q25). 16 exploration winters.
- **Result, with its baseline.** All four declared cells, favourable vs unfavourable vs
  base rate:

  | storm def | window | favourable | unfavourable | base rate | ratio | PSS | days (fav/unfav) |
  | --- | --- | --- | --- | --- | --- | --- | --- |
  | 1.0 in `any2` | 0–0 | 0.0417 | 0.0277 | 0.0383 | **1.506** | +0.1051 | 743 / 794 |
  | 1.0 in `any2` | 1–14 | 0.4164 | 0.3676 | 0.4525 | **1.133** | +0.0512 | 694 / 740 |
  | 0.5 in `any2` | 0–0 | 0.0754 | 0.0894 | 0.0848 | **0.843** | −0.0463 | 743 / 794 |
  | 0.5 in `any2` | 1–14 | 0.7680 | 0.7662 | 0.7922 | **1.002** | +0.0025 | 694 / 740 |

  111 storm events at 1.0 in, 246 at 0.5 in. Against the declared bar (ratio ≥ 1.10),
  Link B holds in **2 of the 4 cells** — both of them the 1.0-inch cells.
- **Implication.** Link B is present at the primary storm definition and vanishes at the
  sensitivity one, so it is **not robust**, and the direction of that failure matters:
  Q26 established that 0.5 in has the *better* claim to being "a Wasatch storm" (15.4
  events per winter, inside the plausible band) while 1.0 in under-counts at 6.9. The cell
  where Link B looks strongest is the cell built on the weaker storm definition, so the
  result must be read as the whole row, not its best entry. Note also that the eye-catching
  same-day ratio of 1.506 rests on **31 versus 22 storm-start days** — a difference of 9
  events — and carries no weight at that count. Phase 6 should not treat "the MJO is
  established as a Wasatch storm predictor in this record" as an available premise.
- **Status.** **EXPLORATORY.** Exploration winters only, protocol not yet locked
  (rule 2.3). Not a conclusion.

### F4 — Link A: buoy swell tracks the MJO in the right direction, too weakly to be a proxy (Phase 5b, Session 5b, 2026-08-09; resolves Q18)

- **Hypothesis.** Declared before the run: wave height at 51001 is higher on
  favourable-phase days (MJO 6/7/8, amplitude > 1) than on unfavourable-phase days
  (2/3/4, amplitude > 1). This is the premise the entire "is the buoy just a crude MJO
  index?" framing rests on (SPEC 1.3, Section 7 model D) — plausible but, until now,
  unchecked (Q18).
- **Method.** `analysis_daily`, exploration winters only, days carrying both a coherent
  MJO (phase and amplitude present, amplitude > 1.0) and a defined
  `buoy_51001_wvht_mean`. Distributions compared on mean, median, and the difference in
  means as a fraction of the pooled sd. Phases 1 and 5 excluded as transitional. The 0.2 /
  0.5 sd reading bars were fixed in the module before the run, and were not moved after it.
- **Result, with its baseline.** Favourable: **mean 2.9798 m, median 2.8023 m, n = 736
  days.** Unfavourable: **mean 2.8204 m, median 2.7225 m, n = 767 days.** Difference in
  means **+0.1594 m**; pooled sd 0.8931 m; **effect size +0.1785 sd** — in the hypothesised
  direction but below the declared 0.2 sd "present" bar. Reference: the all-day mean over
  2,840 defined winter days is 2.8624 m, so the favourable group sits 0.117 m above the
  all-day mean and the unfavourable group 0.042 m below it. Overlap: **1,911 of 2,900**
  exploration winter days carry both a coherent MJO and a reporting buoy.
- **Implication.** **Resolves Q18.** The relationship exists and points the right way, and
  it is far too weak to make wave height a usable read on MJO state — a difference of 16 cm
  against a within-group spread of 89 cm is invisible on any given day. The buoy is a very
  crude MJO index indeed. This is a clean reason the folklore fails at step one, and it
  reframes SPEC Section 7's model D: the buoy's MJO content is small enough that C-vs-D
  separation was always going to be hard, independent of sample size (Q17). It does not
  refute SPEC 1.3's physical story — the sign is right — only its usefulness.
- **Status.** **EXPLORATORY.** Exploration winters only, protocol not yet locked
  (rule 2.3). Not a conclusion.

### F3 — Lag scan 0–30 days: no coherent band of positive skill (Phase 5a, Session 5a, 2026-08-09)

- **Hypothesis.** If the buoy is a proxy for a large-scale atmospheric regime (SPEC 1.3),
  skill should appear as a *broad bump* across adjacent lags, because atmospheric patterns
  persist for days. A lone spike at one lag would be noise, not physics.
- **Method.** Stage 2 of SPEC 6.1. The Stage 1 matching was repeated at every lag from 0
  to 30 days, using the same 9-day-wide window slid across lags (`[lag−4, lag+4]`, so
  lag 14 reproduces the folklore 10–18 window exactly), for all nine swept pop definitions
  against the 1.0-inch `any2` storm definition, on the 16 exploration winters. Every swept
  threshold is plotted, so no lag and no threshold is selected by its own result.
  `outputs/figures/lag_scan_pss.png` and `lag_scan_pss_zscore.png`.
- **Result, with its baseline.** Of 279 lag × pop-threshold combinations, **1 has PSS
  above zero**: abs_p50 at lag 1, PSS = **+0.00066** (storm rate given a pop 0.2205 against
  a base rate of 0.2199). Every other combination is negative, and the longest run of
  consecutive positive lags at any threshold is **1**. For the declared primary
  configuration (abs_p90, 1.0 in `any2`) PSS runs from −0.0224 to −0.0012 across all 31
  lags, with no bump at or near the folklore lag: PSS at lag 14 is −0.0174, against
  −0.0097 at lag 10 and −0.0189 at lag 18. The folklore window is not distinguishable
  from its neighbours.
- **Implication.** The scan shows no band of positive skill at any lag, coherent or
  otherwise — so there is no candidate lag for Phase 6 to lock, and no lag was crowned.
  SPEC 6.1's Stage 3 gate condition ("positive skill at some lag, in a coherent band of
  adjacent lags, surviving sensitivity to pop definition and SWE threshold") is not met on
  its face. Whether that closes the gate is the joint gate review's call, not this
  session's, and it must be read against F1's caveat that the 1.0-inch storm definition is
  itself questionable (Q26).
- **Status.** **EXPLORATORY.** Exploration winters only, under a protocol not yet locked
  (rule 2.3). Not a conclusion.

### F2 — Stage 1 contingency tables: storm likelihood given a pop does not exceed the base rate at any swept threshold (Phase 5a, Session 5a, 2026-08-09)

- **Hypothesis.** The folklore claim: a buoy pop is followed by a Wasatch storm about two
  weeks later, more often than chance. Tested as "a storm event begins 10–18 days after
  the pop's first day".
- **Method.** Stage 1 of SPEC 6.1, on the 16 exploration winters. Daily flags collapsed
  into events (`detect_events`, bridge = 1 day, each event dated by its first day) so
  autocorrelated multi-day swells and storms count once. 54 configurations: 9 pop
  definitions (percentiles 50/75/85/90/95 and z-scores 0.5/1.0/1.5/2.0 sd, all frozen in
  Q16 before any matching) × 3 SWE thresholds × 2 combination rules. Pop occasions are
  pop-event first days; the comparison row is every other day of the same winters outside
  any pop event; one-to-one claiming on the pop row (Q25).
- **Result, with its baseline.** **In all 54 configurations, storm-rate-given-a-pop is
  below its own base rate, and PSS is negative** (PSS from −0.0034 to −0.0654). At the
  primary configuration (1.0 in `any2`, window 10–18): abs_p50 0.2857 vs base rate 0.3380;
  abs_p90 0.2676 vs 0.3331; abs_p95 0.2644 vs 0.3321; z_2sd 0.2805 vs 0.3279. The
  dose-response curve does **not** rise as the threshold tightens — across the percentile
  sweep it runs 0.264–0.286 against a base rate of 0.334, drifting −0.021 from loosest to
  strictest; across the z-score sweep it runs 0.250–0.280 against 0.328, drifting +0.030.
  Both curves are flat within about 0.08 of the base rate and neither crosses it at any of
  the nine thresholds. **Important qualifier:** much of the deficit is the conservative
  one-to-one claiming rule. Without claiming, storm-rate-given-a-pop at 1.0 in `any2` runs
  0.287–0.341 against base rates of 0.327–0.338 — flat *at* the base rate rather than
  below it — and falls below the base rate in 32 of 54 configurations rather than 54.
  Read either way, no threshold shows the rise a dose-response signal would produce.
  `outputs/figures/dose_response_curve.png`.
- **Event counts behind the tables (rule 2.2 / Q17).** 87–265 pop events per definition
  (142 usable occasions at abs_p90, 87 at abs_p95) and 111 storm events at 1.0 in `any2`,
  over 16 winters. This is a sample of dozens of independent events, not thousands; the
  strict end of each sweep is the thinnest and noisiest part of every curve. No table here
  supports a fine distinction.
- **Implication.** No pop threshold in either declared sweep, at any of the three SWE
  thresholds or either combination rule, makes a storm more likely than the base rate at
  the folklore lag. Because the whole sweep is shown at once, no threshold could have been
  cherry-picked to produce a different shape. Feeds the gate review; carries no conclusion
  on its own.
- **Status.** **EXPLORATORY.** Exploration winters only, protocol not yet locked
  (rule 2.3). Not a conclusion.

### F1 — The storm detector finds real weather, but the 1.0-inch threshold under-counts storms (Phase 5a, Session 5a, 2026-08-09)

- **Hypothesis.** If the storm detector is wrong, every downstream number is meaningless.
  Checked before any pop–storm matching was trusted.
- **Method.** Three checks on the 16 exploration winters. (4a) storm events per winter for
  every threshold and definition, against the ~15–30 a Wasatch winter roughly contains;
  (4b) the 2016 combined SWE curve plotted with detected events marked, inspected by eye;
  (4c) the fraction of SWE-detected storm events (1.0 in `any2`) coinciding within ±1 day
  with a positive daily precipitation increment at 2 or more stations — the gauge is a
  physically separate instrument from the SWE pillow at the same sites, so this is
  independent corroboration, not circularity.
- **Result, with its baseline.** (4c) **111 of 111 storm events coincide = 1.0000**,
  against a null expectation well below 1 for a detector firing on pillow artefacts —
  what the detector finds is real precipitation. (4a) Against the plausible 15–30 band:
  0.5 in `any2` = **15.4 events/winter** (min 12, max 19) and `mean` = 13.5, both
  plausible; 1.0 in `any2` = **6.9** (min 2, max 13) and `mean` = 4.7; 1.5 in `any2` =
  **2.3** and `mean` = 1.4 — the 1.0 and 1.5 in configurations are implausibly few and
  were flagged in the report rather than adjusted. (4b) Every marked band in winter 2016
  sits on a visible step-up in the SWE curve — no mark on flat or melting snow — but a
  clear multi-day accumulation in early February 2017 (roughly 22.4 → 25.2 in over about a
  week, at 0.4–0.75 in/day) carries no mark, because no single day reached 1 inch at two
  stations.
- **Implication.** `detect_events` and the SWE signal are sound; the problem is
  definitional. A single-day threshold detects a storm's biggest day, not the storm. The
  0.5-inch threshold has the better claim to being "a storm day", and a multi-day
  accumulation threshold would match the physical event better than any single-day one.
  Recorded as Q26 for Phase 6 (Q6); deliberately not acted on here, since changing a
  threshold after seeing results is the fishing rule 2.2 forbids. Every Stage 1 and Stage 2
  number must be read knowing the 1.0-inch definition under-counts storms.
- **Status.** **EXPLORATORY.** Exploration winters only, protocol not yet locked
  (rule 2.3). Not a conclusion.
