# Phase 5a — Event Detection, Contingency Tables & Lag Scan
**Spec version going in: 0.5 | Version to bump to: 0.6**

---

## READ THIS FIRST

Read `SPEC.md` in full, `STATUS.md` in full, and `DECISIONS.md` in full before doing
anything. Then read this prompt in full before writing any code.

**Apply all critical rules** (SPEC Section 2). Three bind this session hard:

- **2.3 (held-out sealed).** This session runs on **exploration winters only**. Never
  pass `include_holdout=True`. The six sealed winters (2004, 2005, 2006, 2008, 2021,
  2022) must not be read, and no value from them printed.
- **2.2 (no baseline, no claim).** Every hit rate is reported beside its base rate, in the
  same table. No exceptions.
- **2.1 (never split randomly).** Not directly exercised here (no model yet), but the
  event-based design below exists for the same reason: daily weather is autocorrelated,
  so we count events, not days.

### Why this session exists

This is the first look at whether the buoy has any signal. Everything before was
plumbing. This session asks the actual question, by counting: does a buoy "pop" get
followed by a Wasatch storm more often than chance?

It runs the first two stages of SPEC Section 6.1, and **stops at the gate**:

- **Stage 1 — contingency tables.** Define storm events and pop events, then count.
- **Stage 2 — lag scan.** Repeat the count across lags 0–30 and plot skill vs lag.
- **STOP.** Stage 3 (modelling) is gated on what Stages 1–2 show and is **not** in this
  session. Do not build any model.

Before the counting, this session also **validates the storm detector** — confirms it is
finding real storms — because if the detector is wrong, every downstream number is
meaningless.

### CRITICAL — scope discipline

- Do NOT build, train, or sketch any model. Stage 3 is a separate, gated session.
- Do NOT read held-out winters. Exploration-only (plus folklore-only where noted).
- Do NOT tune any threshold by looking at pop–storm results. Thresholds are calibrated
  from marginal distributions only (see Part 2), then frozen before matching.
- Do NOT fill SPEC Section 8. It stays empty until Phase 6.
- Do NOT combine stations into a single locked rule — Phase 5 looks at stations several
  ways; the combination rule is a Phase 6 decision (Q5/Q20).

Implement exactly what is specified. Do NOT commit — prepare changes, output the commit
message, and stop.

---

## Part 1 — Housekeeping (do first, quick)

Three stale-wording fixes carried from 0D's consistency check, owner-approved. None touch
data or code.

**H1 — SPEC 11.1** still says "~40 winters, confirmed in Session 0A" without the two-era
nuance. Align it with Section 7 and Q21: the confirmed usable record is two eras either
side of the 2010–2014 buoy gap, 22 winters usable for the four-model comparison once MJO
coverage is required.

**H2 — SPEC Section 6.0** still frames the Plan B record-length risk as an unmade
"decision point." Phase 4 made that call. Update 6.0 to record that the decision point was
reached and resolved by the Phase 4 split (point to Q13/Q21), while keeping the risk
description for future readers.

**H3 — STATUS Section 5 (Blockers)** still calls the buoy gap "a live decision point when
Phase 4 splits seasons." Phase 4 has run. Reword to past tense, pointing to Q13/Q21 as the
resolution.

Also confirm all three file headers read the correct version after this session's bump
(0.5 → 0.6) — the "bump all three headers" step noted in STATUS Section 6.

---

## Part 2 — Calibrate thresholds from distributions (BEFORE any matching)

**The principle.** Looking at "how big are waves here typically" calibrates the ruler.
Looking at "does a pop predict a storm" is the measurement. We do the first, write the
numbers down, freeze them, then do the second once. Adjusting a threshold after seeing a
pop–storm result would be fishing (rule 2.2's cousin).

All calibration uses **exploration winters only** (folklore-only winters 2023–2025 may be
included for the storm side, since counting needs no MJO; state which you used).

**Storm thresholds — already declared, fixed:** test storm-day thresholds of
**0.5, 1.0, 1.5 inches** of `swe_gain_in`. These are fixed by planning; do not calibrate
them, just use all three.

**Pop thresholds — a declared SWEEP, not a single line.** This is the key design choice
for this session. Rather than pick one pop threshold and defend it, sweep across a
declared set of increasingly strict thresholds and report the storm likelihood at each.
This turns the threshold from a *decision we could get wrong* into a *result we observe*.

Two pop definitions, each swept:

1. **Absolute (percentile sweep):** flag pop days where `wvht_mean` is at or above each of
   the **50th, 75th, 85th, 90th, 95th** percentiles of daily `wvht_mean` across
   exploration winters. Report the metre value each percentile resolves to. (50th ≈ "any
   above-median wave day", 95th ≈ "top 5% of wave days".)
2. **Z-score (threshold sweep):** flag pop days where `wvht_mean` is at or above each of
   **0.5, 1.0, 1.5, 2.0** standard deviations over its trailing 30-day rolling mean
   (trailing, so no look-ahead).

**Why a sweep resolves the strictness dilemma.** Too strict a threshold catches few storms
(the indicator is too rare to matter); too loose a threshold fires so often that a storm
follows at roughly the base rate anyway (the signal is diluted to noise). You cannot know
the right point by reasoning — it depends where the real signal lives. The sweep sidesteps
the choice: we report storm-likelihood at every level and read the *shape*.

- If storm likelihood **rises as the threshold tightens** (bigger waves → more storms),
  that is a genuine dose-response signal — the buoy carrying information.
- If storm likelihood is **flat at the base rate across all thresholds**, the buoy is
  noise at every level, and no cherry-picked threshold can rescue it. A clean null.

Neither shape can be faked by picking a lucky threshold, because all thresholds are shown
at once.

**Freeze the sweep set, not a winner.** Write the swept threshold sets (and the resolved
metre values for the percentiles) into `DECISIONS.md` (resolving Q16) and the report,
before any matching. Do NOT pick a "best" threshold in this session.

> **NOTE FOR PHASE 6 (record in DECISIONS.md Q16, do not act on it now).** When Phase 6
> locks the protocol, it must commit to ONE operating threshold to test on the held-out
> set. That choice must be made by a **rule declared in advance** — e.g. "the point of
> steepest slope in the exploration curve" or "the strictest threshold retaining at least
> N pop events" — NOT by picking whichever threshold gave the highest skill. Choosing the
> operating point to maximise the exploration result would be fishing. The sweep informs
> that choice; it does not license cherry-picking it.

---

## Part 3 — Event detection

Turn daily series into discrete events. This is the core of the honest-counting design:
consecutive qualifying days are ONE event, so a single multi-day storm or swell is not
counted many times (the autocorrelation problem).

```python
def detect_events(daily_flags: pd.Series, bridge: int = 1) -> pd.DataFrame:
    """Collapse a boolean daily series into events.

    Consecutive True days form one event. A gap of up to `bridge` days between
    True runs is bridged into a single event (one dry day inside a storm does not
    split it). Each event is dated by its FIRST day.

    Returns: event_start, event_end, duration_days, peak_value (if a value series
    is supplied alongside).
    """
```

Apply it to:

**Storm events**, per threshold (0.5, 1.0, 1.5) — both per-station and combined:
- Per-station: a storm day at station S = `swe_gain_in[S] >= threshold`.
- Combined: two variants, because Q20 warns averaging may blur a canyon-sharp signal —
  compute both and report both:
  - `any2`: a storm day = at least 2 of the 5 stations exceed the threshold that day.
  - `mean`: a storm day = the cross-station mean `swe_gain_in` exceeds the threshold.
- Bridge = 1 day.

**Pop events**, per pop definition and per swept threshold, on buoy 51001 `wvht_mean`:
- Absolute: one set of pop events per percentile (50, 75, 85, 90, 95).
- Z-score: one set per sd level (0.5, 1.0, 1.5, 2.0).
- Bridge = 1 day. Date each pop by its first day.
- Report the pop-event count at each threshold — the strict end will have few events and a
  noisier storm-likelihood estimate (Q17). This is expected; surface it, do not hide it.

---

## Part 4 — Validate the storm detector (before trusting it)

If the detector is wrong, everything downstream is noise. Two checks, both cheap.

**4a — Count sanity.** For each threshold and each combination variant, report storm
events per winter (mean, min, max across exploration winters). A Wasatch winter has very
roughly 15–30 meaningful storms. Flag any configuration that yields implausibly few (e.g.
under ~8) or implausibly many (e.g. over ~50) — too few means the threshold misses real
storms, too many means it is fragmenting single storms or catching noise. Do not silently
"fix" it; report it so the owner can judge which threshold behaves sensibly.

**4b — Eyeball against the SWE curve.** For one exploration winter (pick a data-rich one,
e.g. 2016) and the 1.0-inch `any2` combined definition, plot the raw combined SWE signal
across the winter and mark each detected storm event on it. Save to
`outputs/figures/storm_detector_check_2016.png`. Confirm by eye that marks land on the big
step-ups and that no obvious big jump is unmarked. State the result in the report.

**4c — Independent cross-check against precipitation.** The SWE pillow and the
precipitation gauge are physically separate instruments at the same sites
(`precip_accum_in` is already in the data). For exploration winters, compute the fraction
of SWE-detected storm events (1.0-inch `any2`) that coincide (within ±1 day) with a
positive daily precipitation increment at 2 or more stations. A high coincidence rate
means the detector is finding real weather, not pillow artefacts. Report the fraction.
Note in the report that precipitation is an independent sensor, so this is corroboration,
not circularity.

---

## Part 5 — Stage 1: contingency tables

For each (pop definition × storm threshold × storm combination) configuration, at the
folklore-centred window, build the 2×2 table and the skill scores.

**Matching rule (fixed):**
- A pop event is a **hit** if at least one storm event begins **10–18 days** after the
  pop's start date.
- **One-to-one:** each pop matches at most one storm; each storm is claimed by at most one
  pop. Once a storm is claimed, it cannot count for another pop. (Prevents one busy
  fortnight inflating the count.) Use a greedy nearest-match within the window; document
  the tie-break.

**The 2×2 table** (per SPEC 6.1):

|  | Storm followed | No storm followed |
| --- | --- | --- |
| Pop | a | b |
| No pop (comparable non-pop windows) | c | d |

For the "No pop" row, draw comparison windows from pop-free periods within the same
exploration winters, so the base rate reflects the same seasons and calendar. Document
exactly how the non-pop comparison windows are constructed — this is where the base rate
comes from and it must be defensible.

**Report, side by side (rule 2.2):**
- Storm rate given a pop = a/(a+b)
- Base rate = overall storm-window frequency
- Probability of detection POD = a/(a+c)
- False alarm rate POFD = b/(b+d)
- Peirce skill score PSS = POD − POFD

One table per configuration. A compact summary table across all configurations, so we can
see whether any apparent signal survives across thresholds and definitions or exists only
at one lucky setting.

**The headline output — the dose-response curve.** For a fixed storm definition (suggest
1.0-inch `any2`) and the folklore-centred window, plot **storm-likelihood-given-pop
against pop threshold**, across the swept thresholds, with the base rate drawn as a
horizontal reference line. Do this for both pop definitions (percentile and z-score). Save
to `outputs/figures/dose_response_curve.png`. Overlay or annotate the pop-event count at
each threshold so the reader sees where the curve is solid (loose end, many events) and
where it is thin (strict end, few events).

This curve is the single most informative result of the session. Its shape — rising toward
the strict end, or flat at the base rate throughout — is what the gate review will read.
Describe the shape in words in the report; do not declare a verdict (that is the joint
review).

**Event-count caveat (rule 2.2 / Q17).** Report the number of pop events and storm events
behind each table. With ~16 exploration winters and a handful of events each, the
independent sample is small (dozens, not thousands). State the counts plainly so no table
is over-read.

---

## Part 6 — Stage 2: lag scan

Repeat the matching across every lag offset from 0 to 30 days. For a chosen primary
configuration (state which — suggest absolute pop, 1.0-inch `any2` storm), compute PSS at
each lag and plot PSS vs lag. Save to `outputs/figures/lag_scan_pss.png`.

**Reading guide, stated in the report (do not overclaim):**
- A genuine regime signal should show a **broad bump** across adjacent lags, because
  atmospheric patterns persist for days. If PSS is high at lag 14 but near zero at 12, 13,
  15, 16, that isolated spike is noise, not physics.
- Also plot the scan for the z-score pop definition, so we see whether any bump is robust
  to how a pop is defined.

Do NOT pick "the best lag" and report it as the answer. The scan is exploratory (it
informs Phase 6's locked protocol). Describe the shape; do not crown a winner.

---

## Part 7 — Tests

`tests/test_events.py`. No network.

1. `detect_events`: three consecutive True days → one event dated by day 1, duration 3.
2. Bridge: True, False, True (1-day gap) → one event with bridge=1; two events with
   bridge=0.
3. Matching one-to-one: one pop with two storms in its window claims only one; two pops
   competing for one storm — only one gets it.
4. Base-rate sanity: a fully-random flag series yields POD ≈ POFD (PSS ≈ 0) — confirms the
   scorer does not manufacture skill from noise.
5. Percentile sweep: the 95th-percentile absolute threshold flags ~5% of qualifying days
   and the 50th ~50%, confirming the sweep resolves percentiles correctly.

---

## Validation

Run all and paste real output.

1. **Tests pass** — `pytest tests/ -v`, all prior plus new.
2. **Frozen thresholds** — paste the resolved absolute pop threshold (in metres), the
   z-score flag fraction, and confirm they were written to DECISIONS.md before matching.
3. **Detector validation** — paste 4a's per-winter storm counts table, 4c's precipitation
   coincidence fraction, and confirm 4b's plot was saved and looks right (describe it).
4. **Stage 1 summary** — paste the compact cross-configuration table: for each config,
   storm-rate-given-pop, base rate, PSS, and the pop/storm event counts. Base rate beside
   every rate. Confirm the dose-response curve plot saved, and **describe its shape in
   words** — does storm-likelihood rise as the pop threshold tightens, or stay flat at the
   base rate? This description is the main input to the gate review. Do not declare a
   verdict.
5. **Lag scan** — confirm both plots saved; describe the shape in words (broad bump? lone
   spike? flat?). Do not declare a conclusion — that is for the joint review.
6. **Seal intact** — confirm no held-out winter was loaded at any point (the loader
   defaulted to exploration; `include_holdout` never set True). Print the winters actually
   used.

**Do NOT** print held-out values anywhere.

---

## Consistency check

Before the commit message, re-read all three files and report any contradiction,
duplicated heading, or findings-log ordering issue. Report only. (H1–H3 are pre-approved.)

This session produces the **first findings-log candidates**. Any Stage 1 / Stage 2 result
recorded in DECISIONS.md Section 2 must be marked **EXPLORATORY** (rule 2.3 — it is on
exploration data, under a protocol not yet locked). Confirm the EXPLORATORY label is
present on every result entry.

---

## File updates

### SPEC.md
- Version bump 0.5 → 0.6.
- H1: SPEC 11.1 two-era nuance. H2: SPEC 6.0 decision-resolved note.
- Section 8 stays empty.

### STATUS.md
- Section 1: mark Phase 5 Stages 1–2 done; note Stage 3 (modelling) is gated and pending
  joint review.
- Section 2: next is the **gate review** — a planning conversation, not a session — to
  decide whether Stage 3 (modelling) is warranted. If it is, Phase 5b (modelling) follows;
  if not, Phase 6 locks a null-expecting protocol.
- Section 3: build-log row. Section 6: consistency result; mark 0D's items resolved. H3.
- Section 4 or a new sub-note: record resolved pop thresholds.

### DECISIONS.md
- Header to 0.6.
- Q16 Resolved: the two pop definitions and their **swept** threshold sets (percentiles
  50/75/85/90/95 with resolved metre values; z-score sd 0.5/1.0/1.5/2.0). Include the
  Phase 6 note: the single operating threshold must be chosen by a rule declared in
  advance, never by picking the highest-skill point.
- Q6: note the three storm thresholds are carried into Phase 5 as declared; final single
  choice still deferred to Phase 6.
- Q20: record what per-station vs combined (`any2` vs `mean`) showed at a high level
  (EXPLORATORY) — informs the Phase 6 combination decision.
- Q23 (MJO method seam): note it does not affect Phase 5 (counting uses no MJO); still open
  for Phase 6.
- **Findings log (Section 2):** add the Stage 1 / Stage 2 results as the first entries,
  each marked **EXPLORATORY**, in the required shape (hypothesis, method, result-with-
  baseline, implication, status).
- Append any new open questions.

---

## Commit message

Do not commit — prepare and output only.

```
feat(analysis): event detection, detector validation, contingency tables, lag scan (Phase 5a)

- src/powderbuoy/events.py: detect_events() collapses autocorrelated daily
  flags into discrete events (bridge=1, dated by first day); pop and storm
  event detection on exploration winters only
- Pop definitions frozen as SWEEPS (Q16): absolute over percentiles
  50/75/85/90/95 (report metre values); z-score over sd 0.5/1.0/1.5/2.0
- Storm thresholds 0.5/1.0/1.5 in, per-station and combined (any2, mean)
- Storm detector validated: per-winter counts, SWE-curve eyeball plot,
  independent precipitation cross-check
- Stage 1 contingency tables + dose-response curve (storm-likelihood vs pop
  threshold, base rate reference): storm-rate beside base rate, POD, POFD,
  PSS, pop/storm event counts (small-sample caveat, Q17)
- Stage 2 lag scan 0-30, PSS vs lag, both pop definitions; broad-bump vs
  lone-spike reading guide
- tests/test_events.py: event collapse, bridge, one-to-one matching,
  noise->PSS~0, percentile threshold
- Gated: no model built; Stage 3 pending joint gate review
- Exploration-only; seal intact; all results marked EXPLORATORY
- Housekeeping: SPEC 11.1, 6.0, STATUS blockers updated

SPEC.md: v0.6
```
