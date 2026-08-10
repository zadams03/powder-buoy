# Phase 8 (finish) — STATUS completion + the README
**Spec version going in: SPEC & DECISIONS already at 1.0; STATUS at 0.9 → bring to 1.0**

---

## READ THIS FIRST — and read the context, this is a resumption

Read `SPEC.md` in full, `STATUS.md` in full, and `DECISIONS.md` in full before doing
anything. Then read this prompt in full before writing.

**This is a resumption of Phase 8, not a fresh run.** An earlier Phase 8 attempt was
stopped part-way and `STATUS.md` was reverted to its clean end-of-Phase-7 state. The
result:

- **SPEC.md is already at v1.0 and its Phase 8 edits are COMPLETE and CORRECT.** The
  dashboard decision (11.1), the Section 8 pre-registration note, and the completion banner
  are all in place. **Do not redo them. Do not re-edit Section 8 (frozen, rule 2.3).**
- **DECISIONS.md is already at v1.0 and its Phase 8 closures are COMPLETE and CORRECT.**
  Q9, Q11, Q27, Q32, Q8, Q20 are all properly closed/parked. **Do not redo them.**
- **STATUS.md is at v0.9, clean, end-of-Phase-7. It is the ONLY file needing the Phase 8
  treatment**, plus the README which was never written.

So this session does three things and no more: (1) bring STATUS.md to v1.0 / project
complete, (2) write `README.md`, (3) validate, consistency-check, and prepare the commit.

**Apply all critical rules** (SPEC Section 2). Rule 2.2 (no number without its baseline)
governs the README's central claim. Rule 2.3 forbids touching frozen Section 8 or re-running
any analysis.

### CRITICAL — scope discipline

- Do NOT re-edit SPEC.md or DECISIONS.md's already-complete Phase 8 content. The only
  permitted SPEC/DECISIONS touches are the two tiny stale-pointer fixes in Part 1 H1, and
  only if trivial and safe; if either looks risky, LOG it in the STATUS consistency table
  instead of editing.
- Do NOT re-run, recompute, or recreate any analysis, number, test result, or figure. This
  is writing and status-closing only. 63 tests already pass; confirm, do not regenerate.
- Do NOT edit the frozen SPEC Section 8.
- Every number in the README must be quoted from an existing file (F7, a Q entry, an
  `outputs/` report). If it is not already on record, it does not go in.

Do NOT commit — prepare changes, output the commit message, and stop.

---

## Part 1 — Bring STATUS.md to v1.0 / project complete

STATUS.md is currently the clean Phase-7 version (header v0.9, "Session 7"). Update it to
reflect that Phase 8 is done and the project is complete.

**Header:** bump to spec version 1.0, last updated Session 8 / Phase 8, today's date.

**Section 1 (Current state):** rewrite to "all phases 0–8 complete; project at v1.0; the
deliverable is `README.md`; the seal is spent; one CONFIRMED finding (F7)." Update the item
table so every phase including Phase 8 (write-up) reads done. Keep the held-out-seal line
accurate: OPENED ONCE 2026-08-09, spent, cannot be re-sealed.

**Section 2 (Next session):** replace with **"None — the project is complete."** Write it
as a clean closing statement, NOT a to-do list. It should contain:
- A one-line statement that there is no next session; Phase 8 was the last.
- **Owner-only future work, explicitly out of scope and not planned:** the owner's own
  write-ups (blog/article/explainer/talk — Option A meant the README is the deliverable and
  the owner writes anything further); and the parked future *directions*, none planned, each
  needing a fresh study with its own sealed set because this seal is spent — swell
  period/direction (Q8, Q27), other ranges/buoys (SPEC 11), per-canyon snow (Q20), multi-day
  storm definition (Q26), snow quality (Q11), GEFS baseline (Q9).
- A short "material of record" pointer: the answer is F7; why it fails is F4–F6; the
  exploratory measurements are F1–F3; the caveats that travel with the numbers (Q23 seam,
  six-winter limit Q13/Q17/Q21, detector definitional point Q26, and the base-rate point).
- Keep this concise. It is a closing note, not a second copy of the findings log.

**H1 — stale-pointer fixes (only if trivial and safe):**
- SPEC 3.4 still calls GEFS "deferred to a later phase" — Q9 is now closed as not-pursued.
  If a one-word/one-line fix, make it; if it risks disturbing surrounding text, log it in
  the STATUS consistency table instead.
- STATUS 4.2's own MJO-end / buoy-gap "live for Phase 7" wording (if present in this clean
  version) → past tense, since neither bound in Phase 7. Fix in STATUS freely (it is this
  file).

**Section 3 (Build log):** add the top row for Phase 8 (this session): STATUS brought to
v1.0, README written, project complete. Summarise faithfully.

**Section 4:** any small data-state note if relevant (likely none — no data changed).

**Section 6 (Consistency check log):** record this session's consistency result, and mark
Phase 7's reported items resolved where this/earlier Phase 8 work resolved them.

---

## Part 2 — Write `README.md` (the deliverable)

Replace the stub `README.md` at the repo root. Plain, honest, readable by someone who has
never heard of the powder buoy. Prose over tables. Structure is a guide, not a rigid
template — write it well and accurately.

**Title + one-line summary.** What the project is, in a sentence — a rigorous test of
whether a Pacific buoy near Hawaii predicts Wasatch snowstorms two weeks out; it doesn't,
and here's how we know.

**The claim.** The folklore: a "pop" (wave-height spike) at NOAA buoy 51101 is said to
precede a Wasatch storm by ~2 weeks, with a self-reported ~80% accuracy and a real skier
following — but no baseline was ever attached.

**Why it can't work as described.** The travel-time argument (SPEC 1.2): swell reaches
Hawaii in 1–2 days and Utah in 3–5, not 14, so the buoy cannot be tracking the storm
itself. Any real signal would need the buoy to be a proxy for a large-scale pattern (the
MJO). This is why the study exists.

**What we did.** In plain terms: ~40 years of buoy data (NOAA 51001, the long-record
neighbour of 51101, validated as a stand-in at 0.98 correlation); Wasatch snow-water-
equivalent from five SNOTEL stations; "pops" and "storms" defined as discrete **events** so
one weather system is not counted many times; winters split into an exploration set and a
**sealed** held-out set not looked at until the rule was locked; then a test of whether
pops are followed by storms more often than chance. Name the two disciplines that make it
trustworthy: **the base rate** and **the sealed set**.

**The headline finding — base rate beside it (rule 2.2).** The heart of the README. Use
this phrasing, with the exact recorded numbers:

> After a buoy pop, a storm followed within 10–18 days **68%** of the time on the held-out
> winters (storm-rate-given-pop 0.6818). But on days with no pop, a storm *also* followed
> within 10–18 days **63%** of the time (base rate 0.6339). The pop moved the odds from 63%
> to 68% — a ratio of 1.08, far below the 1.20 bar set before the data was seen, and well
> within noise on six winters. **Verdict: NULL CONFIRMED.** The buoy tells you almost
> nothing you didn't already know from the fact that it's winter in Utah.

Add that both matching variants agreed exactly, that the exploration set showed the same
flat picture first (this was not a surprise sprung by the held-out set), and that PSS was
+0.0097 — fractionally positive but nowhere near skill, and explicitly disarmed in advance
by the six-winter directional limit.

**Why so many people believe it.** The base-rate illusion, plainly: Utah is snowy enough
that a storm follows most such windows anyway; people notice the hits ("pop, then snow!")
and never tally the misses — storms with no pop, pops with no storm. The 68% feels
impressive until the 63% behind it is shown. Write this section with care; it is what makes
the project interesting rather than merely negative.

**What we did NOT test (the honesty section).** Explicit, so no one over-reads the null:
wave *height* only, not swell period/direction (though popular accounts describe height
spikes, which is what we tested); one buoy, one range, ~22 usable winters; the MJO mechanism
itself is weak AND its snow link disagreed between the pre-2014 and post-2014 eras,
confounded with a change in how the MJO index is calculated (Q23), which we could not
cleanly separate; six held-out winters give a directional, not precise, answer.

**Honest conclusion.** The folklore as actually stated and tested here does not hold; the
most likely truth is that it is mostly the base-rate illusion with no clear mechanism. A
null, cleanly demonstrated — an accepted outcome from the start.

**Repo layout + reproducing it.** Brief pointer to SPEC (method/source of truth), STATUS,
DECISIONS (open questions + findings), the ingest/analysis code, `outputs/`. Note data is
gitignored and how to regenerate. Give the uv setup + pipeline commands, accurate to how the
project runs.

**A note on method (recommended).** One short paragraph on the transferable disciplines:
baseline beside every rate; sealed held-out data; pre-registered decision rules; counting
events not autocorrelated days; the gate that stops you modelling a signal the simple test
says isn't there.

**Tone:** thorough, not bloated. Prose over tables (one small 2×2 or exploration-vs-held-out
table is fine). No emoji, no hype, no "debunked."

---

## Part 3 — Validation

No code changes, so no new tests. Confirm:

1. **Existing tests still pass** — `pytest tests/ -v` (expect 63 passed; confirm nothing
   broke).
2. **Every README number is sourced** — produce a checklist mapping each quantitative claim
   in the README to its origin (F7, a Q entry, or an `outputs/` file). Remove any number
   without a source.
3. **Rule 2.2 self-check** — no hit rate anywhere in the README without its base rate in the
   same sentence or immediately adjacent.
4. **No-overselling self-check** — the "what we did not test" section is present and the
   conclusion claims no more than the data shows.

---

## Consistency check

Before the commit message, re-read SPEC, STATUS, DECISIONS and the new README, and report
any contradiction, duplicated heading, or findings-log ordering issue. Report only.

Confirm: the README's numbers match F7 and `outputs/phase7_holdout_result.txt` exactly;
STATUS now reads coherently as project-complete at v1.0 with no leftover to-do framing; and
SPEC/DECISIONS were not disturbed beyond (at most) the two trivial H1 pointer fixes.

---

## File updates

### STATUS.md — the main file this session edits
- Header to v1.0 / Session 8.
- Section 1 project-complete rewrite; Section 2 clean closing statement; Section 3 build-log
  row; Section 6 consistency result; H1 fixes where trivial.

### README.md
- Written per Part 2.

### SPEC.md / DECISIONS.md
- **Left as-is** except, at most, the two trivial H1 stale-pointer fixes — and only if safe.
  If not trivially safe, log them in STATUS instead. Do NOT touch frozen Section 8. Do NOT
  redo the already-complete Phase 8 housekeeping.

---

## Commit message

Do not commit — prepare and output only.

```
docs(readme): project write-up and v1.0 — the folklore does not hold (Phase 8)

- README.md written: the deliverable. States the claim, the travel-time
  reason it cannot work as described, the method (event-based counting,
  base rates, a sealed held-out set), and the finding
- Headline with baseline beside it (rule 2.2): after a pop, a storm followed
  within 10-18 days 68% of the time on the held-out winters; after a non-pop
  day, 63% — the buoy moves the odds 63->68% (ratio 1.0755), within noise.
  NULL CONFIRMED (F7)
- Explains the base-rate illusion and states plainly what was NOT tested
  (wave height only; one buoy, one range, ~22 winters; MJO mechanism weak and
  era-confounded; six held-out winters are directional). No overselling
- STATUS.md brought to v1.0 / project complete: no next session; owner-only
  future work recorded as out of scope
- SPEC.md and DECISIONS.md Phase 8 edits were already complete (dashboard
  closed, Q9/Q11/Q27/Q32 closed, Section 8 note); left intact this session
- Project COMPLETE at v1.0; seal spent; one CONFIRMED finding

SPEC.md: v1.0 — PROJECT COMPLETE
```
