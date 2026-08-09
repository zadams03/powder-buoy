# Phase 7 — Open the Held-Out Set, Run the Locked Rule Once
**Spec version going in: 0.8 | Version to bump to: 0.9**

---

## READ THIS FIRST — this session is different from every other

Read `SPEC.md` in full (**especially the frozen Section 8**), `STATUS.md` in full, and
`DECISIONS.md` in full before doing anything. Then read this prompt in full before writing
any code.

**This is the one session in the entire project that opens the sealed box.** It calls
`load_analysis_data(include_holdout=True)` — the single authorised use of that argument in
the project (SPEC 8.5). It runs the rule frozen in Section 8, exactly as written, once, on
the six held-out winters, and reports whatever comes out.

**The rule is already decided. This session does not choose anything.** Every parameter —
the pop threshold, the storm definition, the window, the matching variants, the verdict
criteria — is fixed in SPEC Section 8. Your job is to execute it faithfully, not to
interpret, improve, or adjust it.

### The one-shot rule, stated plainly

- The held-out set is scored **exactly once**, against Section 8 as it is currently
  written (spec version 0.8).
- If any result looks disappointing and *anything* is then changed and re-run — threshold,
  window, storm definition, matching, station set, or the winters — **the seal is burned
  and every subsequent number is EXPLORATORY forever** (rule 2.3, SPEC 8.5). It cannot be
  re-sealed.
- If Section 8 turns out to contain an ambiguity, **do not resolve it by editing Section 8
  to match what you did.** Record the ambiguity and the reading you took in `DECISIONS.md`,
  alongside the result. Section 8 is frozen; it is a historical record of what was promised
  before the box opened.

### CRITICAL — scope discipline

- Do NOT change, tune, or recompute any value in Section 8. The pop threshold is the fixed
  **3.9530 m**, not the 90th percentile of the held-out data.
- Do NOT run any model, lag scan, threshold sweep, or MJO feature. Section 8.1 forbids all
  of these.
- Do NOT test the mechanism links (F4–F6) on held-out data.
- Do NOT add the folklore-only winters (2023–2025) to the run.
- Do NOT re-run for any reason after seeing the result. One shot.

Do NOT commit — prepare changes, output the commit message, and stop.

---

## Part 1 — Housekeeping (do first, before opening the box)

Clear the contradictions Phase 6's consistency check surfaced. Do these **before** the
held-out run so the files are clean when the result lands. All owner-approved. None touch
held-out data.

**H1 — SPEC Section 6 Phase 7 description (the substantive one).** Section 6's phase table
still says Phase 7 is "Folklore rule and four models, run once", and the prose says "Both
the folklore rule and the four-model comparison are scored here." Both contradict the
frozen Section 8.1 (folklore rule only, no model). Correct Section 6's table row and prose
to: **Phase 7 runs the locked folklore rule once on the held-out set; the four-model
comparison is not run (gate closed) — see Section 8.1.** Section 8 is the authority.

**H2 — Close settled DECISIONS entries.** Mark Resolved, pointing at Section 8:
- **Q5, Q6, Q26** — storm definition settled as 0.5-inch `any2` (SPEC 8.2).
- **Q16's operating-threshold note** — settled as abs_p90 / 3.9530 m (SPEC 8.2).
- **Q24** — moot; the z-score pop definition is not in the locked rule.

**H3 — Section 9 framing.** SPEC Section 9 opens "Every model run appends one row"; SPEC 8.5
requires a register row for this run, which has no model. Widen Section 9's framing to
"every scored run (model or rule-based)" so the Phase 7 row is not an exception. (Section 9
is not frozen; Section 8 is, so Section 9 is the one that moves.)

**H4 — Stale pointers.** STATUS 4.1 still says "No single operating threshold is chosen —
that is a Phase 6 decision"; update to note Phase 6 chose abs_p90 / 3.9530 m (SPEC 8.2).
SPEC 3.1's pointer "DECISIONS.md Q1 and Q17" should read Q1 and Q21. Minor; fix while here.

Confirm all three headers read 0.9 after the bump.

---

## Part 2 — Open the box and run the locked rule

Now, and only now, unseal. Add a script (e.g. `src/powderbuoy/holdout_eval.py`) or a
clearly-marked entry point that:

1. Calls `load_analysis_data(region="utah", include_holdout=True)` with an inline comment
   citing SPEC Section 8 at spec version 0.8 as the authorisation (SPEC 8.2 "Data access").
   This is the project's single authorised `include_holdout=True`.
2. **Scores the six held-out winters on their own** — 2004, 2005, 2006, 2008, 2021, 2022.
   Do NOT pool exploration winters into the held-out tables. Exploration numbers are quoted
   only as the comparison, from their existing Phase 5a values, not recomputed here.
3. Applies the locked rule from Section 8.2 **exactly**:
   - Pop day: `buoy_51001_wvht_mean ≥ 3.9530 m` (the fixed metre value).
   - Pop events: `detect_events`, bridge = 1, dated by first day.
   - Storm day: `swe_gain_in ≥ 0.5` at ≥ 2 of the 5 stations (`any2`).
   - Storm events: `detect_events`, bridge = 1.
   - Window: storm event begins in [pop_first_day + 10, pop_first_day + 18].
   - Occasion construction: `contingency_from_flags`, `lag_lo=10`, `lag_hi=18`, bridge=1,
     grouped by winter, comparison windows from the same held-out winters (SPEC 8.2 / Q25).
   - Compute the 2×2 and all metrics (8.3) for **both** matching variants: with one-to-one
     claiming and without claiming.

Reuse the **existing, tested** `detect_events` and `contingency_from_flags` from
`events.py` — do not reimplement them. This run must use the identical machinery the
exploration numbers came from, or the comparison is not like-for-like.

---

## Part 3 — Report the result against the pre-declared verdict

Produce `outputs/phase7_holdout_result.txt`. For **both** matching variants, report (8.3):

- The 2×2 table (a, b, c, d).
- Storm-rate-given-a-pop = a/(a+b), **beside** the base rate = (a+c)/(a+b+c+d) — in the
  same line (rule 2.2).
- Ratio = storm-rate ÷ base rate.
- POD, POFD, PSS.
- Counts: pop events, usable pop occasions, non-pop occasions, storm events, and days with
  an undefined pop flag (buoy not reporting).

Then apply the **verdict from SPEC 8.4 mechanically** — do not editorialise, just apply the
declared rule:

- Let S = (ratio ≥ 1.20 AND PSS > 0), computed per variant.
- **NULL CONFIRMED** if S holds for neither variant.
- **SURPRISING** if S holds for both — flagged as a discrepancy warranting caution,
  explicitly NOT vindication (8.4).
- **SPLIT / inconclusive** if S holds for exactly one variant.

State which of the three the result is, by the numbers. Then state the honest limit from
8.4 in the report: six winters give a **directional** result, not a precise one; report it
as "consistent with / inconsistent with the exploration null", never as a precise effect
size.

Quote the exploration comparison beside it: Phase 5a's abs_p90 / 1.0-in was flat, and the
locked storm definition is 0.5-in `any2` — so state the held-out storm-rate-vs-base-rate
next to the exploration storm-rate-vs-base-rate for the closest available exploration
configuration, clearly labelled, so the reader sees whether held-out and exploration agree.

---

## Part 4 — Experiment register (SPEC Section 9)

Create `outputs/experiments/register.csv` if it does not exist, and append **one row** for
this run (SPEC 8.5, 9):

- `run_id` (uuid), `timestamp`, `git_commit` (the commit this run is made from),
  `model_name` = "folklore_rule_locked_v0.8" (or similar), `features` = "buoy_51001_wvht
  pop >= 3.9530m", `train_seasons` = "n/a (no fit)", `test_seasons` = the six held-out
  winters, `used_holdout` = True, `target_definition` = "SPEC Section 8 @ spec 0.8",
  `primary_metric` = "storm_rate_given_pop_vs_base_rate", `primary_value` and
  `baseline_value` (never null, rule 2.2), `status` = CONFIRMED, `notes`.

This is the first and only register row for the project.

---

## Part 5 — Tests

No new analytical logic (the machinery is reused and already tested). Add only:

1. A test that the held-out evaluation calls `load_analysis_data` with
   `include_holdout=True` and scores exactly the six held-out winters (not the exploration
   winters, not the folklore-only winters).
2. Confirm all prior tests still pass.

---

## Validation

Run all and paste real output.

1. **Tests pass** — `pytest tests/ -v`, all prior plus new.
2. **The box was opened correctly** — confirm the run used `include_holdout=True` and that
   the winters scored were exactly 2004, 2005, 2006, 2008, 2021, 2022, and no others.
3. **The result** — paste `outputs/phase7_holdout_result.txt` in full: both matching
   variants' 2×2 tables, storm-rate beside base rate, ratio, POD/POFD/PSS, all counts, and
   the mechanical verdict (NULL CONFIRMED / SURPRISING / SPLIT).
4. **Register row** — paste the single register row.
5. **Section 8 untouched** — confirm SPEC Section 8 was NOT edited this session (it is
   frozen); any ambiguity encountered is recorded in DECISIONS.md, not fixed in Section 8.
6. **One shot honoured** — confirm the rule was run exactly once and not re-run after the
   result was seen.

---

## Consistency check

Before the commit message, re-read all three files and report any contradiction,
duplicated heading, or findings-log ordering issue. Report only. (H1–H4 pre-approved.)

Confirm: the held-out finding is recorded in DECISIONS.md Section 2 as the project's first
**CONFIRMED** finding (not EXPLORATORY — this is the one out-of-sample result the whole
design was built to produce), in the standard shape (hypothesis, method, result-with-
baseline, implication, status), and that its numbers match `outputs/phase7_holdout_result.txt`
exactly.

---

## File updates

### SPEC.md
- Version bump 0.8 → 0.9.
- **Section 8 is NOT edited** — it is frozen. Only the surrounding sections move.
- H1: Section 6 Phase 7 description corrected. H3: Section 9 framing widened.
- H4: SPEC 3.1 pointer fix.

### STATUS.md
- Section 1: mark Phase 7 done; the held-out set is now UNSEALED and spent (record the
  date). The seal line changes from SEALED to "opened once, [date], Phase 7".
- Section 2: next is **Phase 8 — the write-up** (README, plain-language findings, the repo
  as deliverable). Note it needs its own planning.
- Section 3: build-log row. Section 4: H4 threshold note. Section 6: consistency result;
  mark Phase 6's items resolved.

### DECISIONS.md
- Header to 0.9.
- H2: close Q5, Q6, Q24, Q26, Q16 note as resolved.
- **Findings log: add the held-out result as the project's first CONFIRMED finding**, both
  matching variants, with the verdict. This is the capstone finding.
- Q14 (what happens if held-out is disappointing): record what actually happened and the
  decision taken (per the owner's Phase-4 position: likely write up and stop).

---

## Commit message

Do not commit — prepare and output only. Fill in the bracketed result before presenting.

```
feat(holdout): open the sealed set and run the locked folklore rule once (Phase 7)

- THE ONE-SHOT TEST. load_analysis_data(include_holdout=True) used once —
  the project's single authorised unsealing — scoring the six held-out
  winters (2004, 2005, 2006, 2008, 2021, 2022) against the frozen SPEC
  Section 8 rule, spec v0.8
- Rule run exactly as locked: pop >= 3.9530 m, storm 0.5-in any2, window
  10-18 days, both matching variants; nothing recomputed on held-out data
- RESULT: [NULL CONFIRMED / SURPRISING / SPLIT] — storm-rate-given-pop
  [X] vs base rate [Y] (ratio [R]) with claiming, [X2] vs [Y2] (ratio
  [R2]) without; both [below/above] base rate. [Consistent with / against]
  the Phase 5 exploration null
- First and only experiment-register row (used_holdout=True, status
  CONFIRMED); first CONFIRMED finding in DECISIONS.md
- Section 8 frozen and untouched; seal now spent, one shot honoured
- Housekeeping: SPEC 6 Phase 7 description corrected to folklore-only (H1);
  Section 9 framing widened (H3); Q5/Q6/Q16/Q24/Q26 closed; pointer fixes
- Next: Phase 8 write-up

SPEC.md: v0.9 — HELD-OUT SET OPENED, ONE SHOT SPENT
```
