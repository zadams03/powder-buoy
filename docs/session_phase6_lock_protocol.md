# Phase 6 — Lock the Evaluation Protocol (SPEC Section 8)
**Spec version going in: 0.7 | Version to bump to: 0.8**

---

## READ THIS FIRST

Read `SPEC.md` in full, `STATUS.md` in full, and `DECISIONS.md` in full before doing
anything. Then read this prompt in full before writing any code.

**Apply all critical rules** (SPEC Section 2). This session is governed by rule 2.3: it
*writes and freezes* the evaluation protocol that the held-out set will be tested against.

### Why this session exists — and its hard boundary

This session locks the rule. It does **not** open the box.

The whole value of the held-out test depends on the rule being fixed, in writing,
committed to git, **before** the sealed winters are ever read. This session fills SPEC
Section 8 and stops. Phase 7 — a separate, later session — opens the box and runs the
locked rule once.

**ABSOLUTE PROHIBITION:** this session must not read, load, print, summarise, or in any
way access data from the six held-out winters (2004, 2005, 2006, 2008, 2021, 2022).
`include_holdout` stays False everywhere. No exploratory run, no "quick check", nothing.
If any step seems to require held-out data, stop — it belongs in Phase 7, not here.

This session writes almost no code. It is a specification-writing session plus a small,
declared seam-robustness check on exploration data (Part 3). Do NOT commit — prepare
changes, output the commit message, and stop.

### The result so far, for context

Phase 5a: the folklore fails on exploration data — no skill at any pop threshold or lag
(F1–F3). The gate for Stage 3 modelling did NOT open. Phase 5b: the physical chain is
weak, Link A (buoy↔MJO) the clearest break (F4–F5). So the protocol locked here is a
**null-expecting** protocol, and — because the gate never opened — it tests the **folklore
rule only**, not a four-model comparison.

---

## Part 1 — Housekeeping (do first)

Clear the loose ends Phase 5b's consistency check surfaced, plus the structural gap. All
owner-approved.

**H1 — SPEC 6.1 reconciliation (the structural one).** SPEC 6.1 defines Phase 5 as exactly
three stages and Section 6's phase table has no sub-phase rows, so the mechanism check
(Phase 5b) does not exist anywhere in SPEC. Add a short note to SPEC 6.1 (or Section 6)
recording that a mechanism check was run as Phase 5b after Stage 2, on exploration data,
to explain the null physically — and that it is not one of the three original stages but a
documented addition. The point is that a reader of SPEC alone can see Phase 5b happened.

**H2 — Q23 seam decision.** The BoM MJO method seam (2013/2014) was flagged as "becomes
live when MJO features are used." Phase 5b used MJO features. Part 3 below runs the
pre/post-seam robustness check; record its outcome against Q23 and mark Q23 resolved
(the seam either does or does not change the weak-link conclusion).

**H3 — Park the remaining open questions explicitly.** Several questions were "decide in
Phase 6." Since there is no model, some are now moot and should be closed as such rather
than left dangling:
- **Q17** (can models be told apart): the four-model comparison is not run (gate closed),
  so this concern is moot for the model — but record that the underlying small-sample point
  still applies to the folklore held-out test (six winters → directional, not precise).
- **Q29** (amplitude bar): moot for a model that never runs; note it would matter only if
  MJO modelling were revived.
- **Q28** (MJO lag by rule): moot for the same reason; the mechanism check already used a
  pre-declared window.
- **Q19** (season definition): **must be decided now** — Section 8 freezes the scoring
  unit. Recommend keeping Nov–Apr (every Phase 4/5 number uses it; changing it now would
  invalidate the exploration baseline the held-out test is compared against) and recording
  that decision. Do not widen it.
- **Q25** (occasion / comparison-window construction): **must be decided now** — it is part
  of the locked rule. Adopt the Phase 5a construction (anchor-day occasions, non-pop
  comparison windows drawn from the same winters), declared in Section 8.
- **Q8** (DPD/MWD filtering), **Q20** (station combination beyond any2/mean): park as
  "not pursued; possible future work" — neither is part of the locked folklore rule.

Confirm all three headers read 0.8 after the bump.

---

## Part 2 — Write and freeze SPEC Section 8 (the core task)

Replace the Section 8 placeholder with the locked protocol below. Once written, it is
frozen (rule 2.3). Write it precisely — Phase 7 will execute it literally.

Section 8 must state, unambiguously:

**8.1 — Scope and what is NOT tested.**
- State plainly: the Stage 3 modelling gate (SPEC 6.1) did not open, so the four-model
  comparison (Section 7) is **not run**. The held-out set is used once, to test the
  **folklore rule** as a confirmatory out-of-sample check of the Phase 5 null.
- Record why: no configuration showed a coherent band of positive skill on exploration
  data (F1–F3), so there is no model to validate. Testing a model here would be testing
  something exploration gave no reason to build.

**8.2 — The locked folklore rule** (this is what Phase 7 runs):
- **Pop definition:** absolute threshold on `buoy_51001_wvht_mean`, at the **90th
  percentile value frozen from exploration in Q16 — 3.9530 m**. State explicitly: this
  fixed metre value is used; the threshold is **not** recomputed on held-out data. Pop
  events formed by `detect_events` with bridge = 1, dated by first day (as Phase 5a).
- **Storm definition:** **0.5-inch `any2`** — a storm day is `swe_gain_in ≥ 0.5` at **at
  least 2 of the 5 stations**; storm events by `detect_events`, bridge = 1. Justification:
  Phase 5a proved 1.0-inch under-counts real storms (Q26); 0.5-inch `any2` gives the
  plausible ~15 events/winter and is the honest storm definition. Chosen on detector
  grounds, before opening the box — not because it flattered the folklore.
- **Window:** a pop is a hit if a storm event begins **10–18 days** after the pop's first
  day — the folklore's own ~14-day claim, tested on its own terms. **One window only. No
  lag scan on held-out data.**
- **Matching:** report **both** — one-to-one claiming (conservative, pops in date order
  each claim the earliest unclaimed storm) **and** without-claiming (each pop scored
  independently). Both declared now; neither is "the answer." (Resolves the Q25 claiming
  question for the locked rule.)
- **Comparison / base rate:** non-pop comparison windows drawn from the same held-out
  winters, exactly as constructed in Phase 5a (`contingency_from_flags`), so the base rate
  reflects the same seasons and calendar.

**8.3 — Metrics**, with formulas written out:
- Storm-rate-given-pop = a/(a+b), reported **beside** the base rate = (a+c)/(a+b+c+d)
  (rule 2.2), for both matching variants.
- POD = a/(a+c), POFD = b/(b+d), PSS = POD − POFD.
- Event counts (pop events, storm events) reported alongside every table.

**8.4 — The verdict criteria, stated as numbers BEFORE unsealing:**
- **Null confirmed** if storm-rate-given-pop is at or below the base rate (within noise) on
  the held-out winters, under both matching variants. This is the expected outcome and
  would confirm the exploration null out-of-sample.
- **Surprising** if storm-rate-given-pop is meaningfully above the base rate (state a
  concrete bar, e.g. a ratio ≥ 1.2 AND a positive PSS, under both variants). If this
  occurs, it is **flagged as unexpected and NOT reported as vindication** — six winters
  against a flat exploration is more likely small-sample noise than a signal exploration
  missed; it would be recorded as a discrepancy warranting caution, not a reversal.
- State the honest limit: six held-out winters give a **directional** result, not a precise
  one. This is written in before the number is seen so it cannot be rationalised after.

**8.5 — The exact held-out winters**, restated from Q13: 2004, 2005, 2006, 2008, 2021,
2022. And the one-shot rule: the set is evaluated exactly once; any re-run after seeing the
result burns the seal and every subsequent number is EXPLORATORY.

**8.6 — What would have been the model protocol (recorded, not executed).** Briefly note,
for the write-up's sake, what the four-model comparison *would* have tested had the gate
opened (models A–D, leave-one-season-out CV, Brier/PSS skill vs climatology), and that it
is deliberately not run. This closes Section 7 honestly rather than leaving it looking
unfinished.

---

## Part 3 — Seam-robustness check (small, exploration-only, resolves Q23)

The one piece of actual analysis this session runs, and it touches **no held-out data**.

Phase 5b read MJO across the 2013/2014 method seam (10 exploration winters pre-seam, 6
post). Confirm the weak-link conclusion (F4/F5) is not an artefact of the seam.

Re-run the Phase 5b Link A and Link B **declared tests** (favourable vs unfavourable,
amplitude > 1) **separately for pre-seam winters (≤2013) and post-seam winters (≥2014)**,
on exploration winters only. Report both sub-samples beside the pooled result. The
sub-samples are tiny (10 and 6 winters), so this is a qualitative check: do both eras point
the same weak direction, or do they wildly disagree?

- If both eras show the same weak/absent links → the seam does not change the story; record
  Q23 resolved, conclusion robust.
- If they disagree sharply → record it as a caveat for the write-up; the pooled Phase 5b
  numbers should then be read as method-blended.

Do NOT adjust or correct the data. This is a split-and-compare sanity check, reported not
fixed. Save any figure to `outputs/figures/mjo_seam_check.png`.

---

## Part 4 — Tests

No new detector code, so no new logic to test heavily. If Part 3 adds a small helper (e.g.
a pre/post-seam splitter), add one test that it partitions winters at the 2013/2014
boundary correctly. Confirm all existing tests still pass.

---

## Validation

1. **Tests pass** — `pytest tests/ -v`, all prior plus any Part 3 helper test.
2. **Section 8 written** — paste the full locked Section 8 as written into SPEC.md. This is
   the session's main deliverable; it must be complete and unambiguous.
3. **Seam check** — paste the pre-seam vs post-seam vs pooled comparison for Link A and
   Link B; state in words whether the conclusion holds in both eras.
4. **Seal intact** — confirm `include_holdout` was never set True this session; confirm no
   held-out winter was read. Print the winters touched by Part 3 (should be exploration
   only, and only the pre-2014 / post-2014 exploration subsets).
5. **Section 8 frozen** — confirm Section 8 no longer contains the placeholder text and now
   contains the locked protocol.

**Do NOT** access held-out winters anywhere in this session.

---

## Consistency check

Before the commit message, re-read all three files and report any contradiction,
duplicated heading, or findings-log ordering issue. Report only. (H1–H3 pre-approved.)

Confirm specifically: Section 8 is now filled and internally consistent with the Phase 5
findings it rests on; the held-out winter list in Section 8 matches Q13 and STATUS exactly;
and nothing in Section 8 references a model being run.

---

## File updates

### SPEC.md
- Version bump 0.7 → 0.8.
- **Section 8: replace the placeholder with the full locked protocol (Part 2).** This is
  the core change.
- H1: SPEC 6.1 / Section 6 note recording Phase 5b's existence.
- Section 7: add a one-line pointer that the four-model comparison is not run (gate closed),
  see Section 8.1.

### STATUS.md
- Section 1: mark Phase 6 done; Section 8 LOCKED. Note the seal is still intact and will be
  opened once, in Phase 7.
- Section 2: next is **Phase 7 — open the held-out set and run the locked folklore rule
  once**. Note it is the one-shot confirmatory test and its own session.
- Section 3: build-log row. Section 6: consistency result; mark Phase 5b's items resolved.

### DECISIONS.md
- Header to 0.8.
- Q23 Resolved (seam check outcome). Q19 Resolved (keep Nov–Apr). Q25 Resolved for the
  locked rule (adopt Phase 5a construction, both matching variants).
- Q17, Q28, Q29 closed as moot (no model), with the small-sample note carried to the
  folklore held-out test.
- Q8, Q20 parked as possible future work.
- Q15 Resolved: the folklore rule IS tested on the held-out set (Section 8), one shot.
- No new findings (no held-out data read). The seam check is EXPLORATORY context, recorded
  as such.

---

## Commit message

Do not commit — prepare and output only.

```
spec(protocol): lock held-out evaluation protocol, Section 8 frozen (Phase 6)

- SPEC Section 8 written and FROZEN: the locked folklore rule to be run
  once on the six held-out winters in Phase 7
  - pop = absolute 90th-pct wvht_mean = 3.9530 m (frozen from exploration,
    not recomputed on held-out)
  - storm = 0.5-in any2 (chosen on detector grounds, Q26)
  - window = 10-18 days (the folklore's own claim)
  - matching = both one-to-one claiming and without-claiming
  - verdict criteria stated as numbers before unsealing; six winters give a
    directional not precise result
- Gate did not open: four-model comparison NOT run; held-out used only to
  confirm the Phase 5 null out-of-sample (Section 8.1)
- Seam-robustness check (exploration-only): Link A/B weak conclusion holds
  pre- and post-2013/2014 MJO method seam (Q23 resolved)
- Housekeeping: SPEC 6.1 records Phase 5b's existence (H1); Q19 keep Nov-Apr,
  Q25 adopt Phase 5a construction; Q17/Q28/Q29 closed as moot (no model);
  Q8/Q20 parked
- Box NOT opened this session; include_holdout never True; no held-out data read

SPEC.md: v0.8 — SECTION 8 LOCKED
```
