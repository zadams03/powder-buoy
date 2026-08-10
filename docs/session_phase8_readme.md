# Phase 8 — Write-Up: the README as deliverable
**Spec version going in: 0.9 | Version to bump to: 1.0**

---

## READ THIS FIRST

Read `SPEC.md` in full, `STATUS.md` in full, and `DECISIONS.md` in full before doing
anything. Then read this prompt in full before writing.

**Apply all critical rules** (SPEC Section 2). The one that binds this session hardest is
**2.2 — no number without its baseline.** The write-up's central number is 68% vs 63%, and
the 63% must never appear more than a few words from the 68%. A README that quotes the hit
rate without the base rate beside it would reproduce the exact error this whole project
exists to expose.

### Why this session exists

The investigation is complete and the answer is in: the folklore does not hold (F7, NULL
CONFIRMED). This session turns the repository into something a person can read and trust —
a strong README that states the question, the method, the finding, and the base-rate lesson
at its heart.

The owner has chosen **Option A**: the README is the deliverable. No separate report, no
explainer, no dashboard. The owner will write any further pieces themselves. This session
produces the README and closes the project cleanly. Do not create a report document, a blog
post, or a dashboard — just the README and the housekeeping to reach v1.0.

### This is the version 1.0 session

After this, the project is done. SPEC bumps to 1.0. The write-up must be accurate, honest,
and free of overselling.

### CRITICAL — accuracy and restraint

- Every number in the README must be traceable to a finding in DECISIONS.md or a report in
  `outputs/`. Do not round loosely, invent, or recall from memory — quote the recorded
  values. If a number is not in the files, do not put it in the README.
- **No overselling.** The finding is a clean null on 16 exploration + 6 held-out Wasatch
  winters, using wave height alone. It is NOT "the powder buoy is debunked." State exactly
  what was tested and — just as important — what was not (period, direction, other buoys,
  other ranges, the MJO mechanism's own ambiguity).
- Do NOT reopen or re-run any analysis. This is a writing session. No new numbers are
  computed. If the README needs a number that was never computed, leave it out rather than
  computing it now.
- Do NOT edit the frozen SPEC Section 8.

Do NOT commit — prepare changes, output the commit message, and stop.

---

## Part 1 — Housekeeping (do first)

Close the loose ends Phase 7's consistency check surfaced, plus the deferred product
questions. All owner-approved.

**H1 — Close the deferred product questions.**
- **Q9 (GEFS reforecast):** its condition was "revisit only if Phase 7 shows the buoy has
  skill." Phase 7 showed no skill. Resolve Q9 as "not pursued — condition resolved to no."
- **SPEC 11.1 (dashboard):** the deferred decision is now due. The result is null, so a
  live dashboard has nothing to show. Record the decision: **not built — a null result does
  not warrant a live dashboard** (this matches the owner's Option A choice). Update SPEC
  11.1 accordingly.

**H2 — Note Section 8's frozen present tense.** Phase 7 flagged that Section 8 reads in the
present tense ("this is exactly what Phase 7 runs") although Phase 7 has now run. This is
deliberate — Section 8 is the frozen record of what was promised before the box opened. Add
a one-line note at the top of Section 8's surrounding context (NOT inside the frozen text)
or in Section 6, stating that Section 8 is a pre-registration written before Phase 7 and is
intentionally preserved in its original tense.

**H3 — Stale-pointer cleanup.**
- STATUS 4.2: the MJO-end and buoy-gap constraints described as "live for Phase 7" did not
  bind (the locked rule read no MJO; 51001 reported on all 1,086 held-out days). Reword to
  past tense / resolved.
- Optionally tidy the DECISIONS open-questions table into numeric order if trivial; if not
  trivial, leave it and note it. Do not risk introducing errors for a cosmetic sort.

Confirm all three headers read 1.0 after the bump.

---

## Part 2 — Write the README

Create (or replace) `README.md` at the repo root. Plain, honest, readable by someone who
has never heard of the powder buoy. Prose, not a wall of tables. The structure below is a
guide, not a rigid template — write it well.

**Suggested structure:**

**Title and one-line summary.** What the project is, in a sentence. E.g. "A rigorous test
of whether a Pacific Ocean buoy near Hawaii can predict snowstorms in Utah's Wasatch
mountains two weeks in advance. It can't — and here's how we know."

**The claim.** What the folklore says: a buoy "pop" (wave-height spike) at NOAA station
51101 is said to precede a Wasatch storm by about two weeks. Note it has a real following
among skiers and a self-reported ~80% accuracy, but no proper baseline was ever attached.

**Why it can't work the way people say.** The travel-time argument (SPEC 1.2): swell
reaches Hawaii in 1-2 days and Utah in 3-5 days, not 14 — so the buoy cannot be tracking
the storm itself. If there were signal, it would have to be the buoy acting as a proxy for
a large-scale pattern (the MJO). State this plainly; it is why the study exists.

**What we did.** In plain terms: pulled ~40 years of buoy data (NOAA 51001, the long-record
neighbour of 51101) and Wasatch snow-water-equivalent from SNOTEL; defined a "pop" and a
"storm" as discrete events (so one weather system is not counted many times); split the
winters into an exploration set and a **sealed** held-out set that was not looked at until
the rule was locked; tested whether pops are followed by storms more often than chance.
Emphasise the two disciplines that make the result trustworthy: **the base rate** (every
hit rate compared against how often storms happen anyway) and **the sealed set** (the final
test run once, on winters no choice was tuned on).

**The headline finding — with the base rate beside it (rule 2.2).** This is the heart of
the README. State it as the owner phrased it, corrected and exact:

> After a buoy pop, a storm followed within 10-18 days **68%** of the time on the held-out
> winters. But on days with no pop, a storm *also* followed within 10-18 days **63%** of
> the time. The pop moved the odds from 63% to 68% — a gap far too small to matter, and
> well within noise on six winters. The buoy tells you almost nothing you didn't already
> know from the fact that it's winter in Utah.

Quote the exact numbers from F7 / `outputs/phase7_holdout_result.txt`: storm-rate-given-pop
0.6818, base rate 0.6339, ratio 1.0755, PSS +0.0097, verdict NULL CONFIRMED, and that both
matching variants agreed. Note the exploration set gave the same flat picture first (this
was not a surprise sprung by the held-out set).

**Why so many people believe it.** The base-rate illusion, explained simply: Utah is snowy
enough that a storm follows most two-week windows anyway. People notice the hits ("pop, then
snow — it works!") and never tally the misses — storms with no pop, and pops with no storm.
The 68% feels impressive until you see the 63% sitting behind it. This section is what makes
the project interesting rather than just negative; write it with care.

**What we did NOT test (the honesty section).** Be explicit, so no reader over-reads the
null:
- Wave *height* only — not swell *period* or *direction*, which sophisticated buoy-watchers
  may use (though the popular articles describe height-spikes, which is what we tested).
- One buoy (51001/51101), one mountain range (Wasatch), ~22 usable winters.
- The MJO mechanism was checked and is itself weak/ambiguous in this data — and the
  MJO↔snow link even disagreed between the pre-2014 and post-2014 eras, confounded with a
  change in how the MJO index is calculated (Q23). We could not cleanly separate a data
  artefact from a real shift.
- Small sample: six held-out winters give a directional answer, not a precise one.

**Honest conclusion.** The powder-buoy folklore, as it is actually stated and tested here,
does not hold: a wave-height spike does not raise the odds of a Wasatch storm beyond the
base rate. The most likely truth is that the folklore is mostly the base-rate illusion, with
no clear physical mechanism to support it. A null result, cleanly demonstrated, is the
finding — and was an accepted outcome from the project's start.

**How the repo is organised.** Brief pointer to SPEC.md (method/source of truth),
STATUS.md, DECISIONS.md (open questions + findings log), the ingest/analysis code, and the
`outputs/` reports and figures. Mention the data is not committed (gitignored) and how to
regenerate it.

**Reproducing it.** The commands to set up the environment (uv) and re-run the pipeline
end to end. Keep it accurate to how the project actually runs.

**A note on method (optional but recommended).** One short paragraph naming the disciplines
that a reader could carry to any similar investigation: baseline beside every rate; sealed
held-out data; pre-registered decision rules; counting events not autocorrelated days; the
gate that stops you building a model to chase a signal the simple test says isn't there.
This is the transferable lesson.

**Length and tone:** thorough but not bloated. Prose over tables, though one small results
table (the 2×2 or the exploration-vs-held-out comparison) is welcome. No emoji, no hype, no
"debunked". Write for an intelligent reader who is not a specialist.

---

## Part 3 — Validation

No code, so no tests to add. Confirm:

1. **Existing tests still pass** — `pytest tests/ -v` (nothing should have changed, but
   confirm the write-up session broke nothing).
2. **Every number in the README is sourced** — produce a short checklist mapping each
   quantitative claim in the README to its origin (F7, a Q entry, or an `outputs/` file).
   Any number without a source is removed.
3. **Rule 2.2 self-check** — confirm no hit rate appears in the README without its base rate
   in the same sentence or immediately adjacent.
4. **No overselling self-check** — confirm the "what we did not test" section is present and
   the conclusion does not claim more than the data shows.

---

## Consistency check

Before the commit message, re-read all three files plus the new README and report any
contradiction, duplicated heading, or findings-log ordering issue. Report only.

Confirm: the README's numbers match F7 and `outputs/phase7_holdout_result.txt` exactly; the
README does not contradict SPEC or DECISIONS anywhere; and the project's status is coherent
at v1.0 (all phases complete, seal spent, one CONFIRMED finding).

---

## File updates

### SPEC.md
- Version bump 0.9 → 1.0.
- H1: SPEC 11.1 dashboard decision recorded (not built).
- H2: Section 8 pre-registration note (outside the frozen text).
- Status banner at the top: mark the project complete.

### STATUS.md
- Section 1: all phases complete; project at v1.0; seal spent; one CONFIRMED finding.
- Section 2: **none — project complete.** Note any owner-only future work (the owner's own
  write-ups, possible future directions like swell period/direction or other ranges) as
  explicitly out of scope and not planned.
- Section 3: final build-log row. Section 6: consistency result; mark Phase 7's items
  resolved.

### DECISIONS.md
- Header to 1.0.
- H1: Q9 resolved (not pursued); dashboard decision recorded.
- Q11 (snow quality), Q8 (DPD/MWD), Q20 (station combination), Q27 (alt swell variable):
  confirm all are parked as "future work, not pursued" — these are the honest "what we
  didn't test" list and should be discoverable in DECISIONS for anyone reading.
- No new findings (no analysis run).

---

## Commit message

Do not commit — prepare and output only.

```
docs(readme): project write-up and v1.0 — the folklore does not hold (Phase 8)

- README.md: the deliverable. States the claim, the travel-time reason it
  cannot work as described, the method (event-based counting, base rates,
  sealed held-out set), and the finding
- Headline, with baseline beside it (rule 2.2): after a pop, a storm followed
  within 10-18 days 68% of the time on held-out winters; after a non-pop day,
  63% — the buoy moves the odds 63->68%, within noise. NULL CONFIRMED (F7)
- Explains the base-rate illusion (why people believe it) and states plainly
  what was NOT tested (wave height only; one buoy, one range, ~22 winters; MJO
  mechanism weak and era-confounded; six held-out winters are directional)
- No overselling: a clean null, not a debunking
- Housekeeping: Q9 + dashboard closed (null does not warrant one, SPEC 11.1);
  Section 8 pre-registration note; stale pointers fixed
- Project COMPLETE at v1.0; seal spent; one CONFIRMED finding

SPEC.md: v1.0 — PROJECT COMPLETE
```
