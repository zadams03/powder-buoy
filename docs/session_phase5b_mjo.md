# Phase 5b — MJO Mechanism Check (why the folklore fails)
**Spec version going in: 0.6 | Version to bump to: 0.7**

---

## READ THIS FIRST

Read `SPEC.md` in full, `STATUS.md` in full, and `DECISIONS.md` in full before doing
anything. Then read this prompt in full before writing any code.

**Apply all critical rules** (SPEC Section 2). Three bind this session:

- **2.3 (held-out sealed).** Exploration winters only. Never pass `include_holdout=True`.
  The six sealed winters must not be read or printed.
- **2.2 (no baseline, no claim).** Every storm rate is reported beside its base rate.
- The declared-test / descriptive-sweep discipline in Part 2 is the honesty spine of this
  session — follow it exactly.

### Why this session exists

Phase 5a falsified the folklore as people state it: a buoy wave-height spike does not raise
the odds of a Wasatch storm ~14 days later, at any threshold or lag. That result stands.

This session explains *why*, by testing the physical chain the folklore was supposed to
ride on. The original hypothesis (SPEC 1.3) was:

> MJO in a favourable phase → active North Pacific → bigger Hawaii swell → (weeks later)
> more Utah snow.

The folklore skips the middle and asserts the ends connect directly (swell → snow). That
was flat. This session tests the two **internal links** separately, to find where the
chain breaks:

- **Link A — MJO ↔ buoy swell.** Does MJO state relate to wave height at 51001 at all?
  (This resolves Q18.)
- **Link B — MJO ↔ Utah snow.** Does MJO state relate to Wasatch storms at all?

The pattern of results is the finding:

- Both links present, yet folklore flat → the regime signal is real but the buoy is too
  noisy a proxy for it.
- Link A broken → the buoy never tracked the regime; clean reason the folklore fails at
  step one.
- Link B broken → even established science does not show up at this sample size; tells us
  the 16-winter record may be too small to see known signals.

This is a **mechanism check, not another attempt to make the buoy work.** It is
correlation and counting only.

### CRITICAL — scope discipline

- Do NOT build, train, or sketch any model. Modelling stays gated (the Phase 5a gate did
  not open).
- Do NOT read held-out winters. Exploration-only.
- Do NOT fill SPEC Section 8. Phase 6.
- Do NOT promote any descriptive-sweep observation to a finding (see Part 2).
- Do NOT search across many MJO framings for one that "works" — the declared test is fixed
  in advance.

Implement exactly what is specified. Do NOT commit — prepare changes, output the commit
message, and stop.

---

## Part 1 — Housekeeping (do first, quick)

Phase 5a's consistency check left five reported-not-fixed items. These are owner-approved
to clear now. All are wording/record fixes; none touch data or results.

**H1 — Q18 relocation.** Q18's plan says "quick look in Phase 5, Stage 1", which ran
without it. Update Q18's note to point here (Phase 5b) and mark it **being answered this
session**.

**H2 — Q17 figure.** Q17 still frames power as "~40 winters". Update to the confirmed 22
usable / 16 exploration, noting Phase 5a's event counts (dozens, not thousands) as a
concrete instance. Keep the question open.

**H3 — SPEC 1.1 date.** SPEC 1.1 says the community tracked 51101 "since roughly 2004", but
51101's record starts 2008. Soften to "since the mid-2000s" (or similar) and add a
one-line caveat that 51101's archive begins 2008, so for most exploration winters the pop
signal necessarily comes from 51001 as the validated stand-in (Q1). Record as a resolved
consistency item.

**H4 — SPEC 6.1 gloss + comparison-window note.** Tighten SPEC 6.1's plain-English gloss so
POD and base rate are described in terms of storm-containing *windows/occasions*, not
"storms" (the formulas are correct; only the gloss is loose). Add a pointer that the
"did-not-pop" comparison-window construction is recorded in Q25 and will be settled in the
Phase 6 protocol.

**H5 — Q19 (season definition).** Not raised in 5a, but note it is now due: the Nov–Apr
window is still assumed. Leave open; flag that Phase 6 should decide it. (No edit beyond a
one-line status note if convenient — do not expand scope.)

Confirm all three headers read 0.7 after the bump.

---

## Part 2 — The honesty discipline (declared test vs descriptive sweep)

This session looks at all 8 MJO phases, but treats two kinds of looking completely
differently. Keep them separate in the code and the report.

**The declared test (confirmatory — carries weight).** Specified here, before any run:

> Primary contrast: **MJO phases 6, 7, 8 ("favourable") vs phases 2, 3, 4 ("unfavourable")**,
> on days where **MJO amplitude > 1.0** (below that there is no coherent MJO). Phases 1 and
> 5 are transitional and excluded from the primary contrast. This grouping is grounded in
> the published association between western-US winter precipitation and MJO phases 6–8 — it
> is a physically motivated hypothesis, not a data-driven pick.

This contrast is the headline result. It may carry weight precisely because it was fixed in
advance.

**The descriptive sweep (exploratory — context only).** Show all 8 phases individually:
storm rate per phase against the base rate, buoy-swell distribution per phase, plotted.
This is *description, not a test*. Its purpose is the picture — and if the picture is flat
across all 8, that is strong, honest evidence of no signal.

**The rule that must not be broken:** no observation from the descriptive sweep may be
reported as a finding or conclusion. If a single phase looks high, it is labelled
"exploratory, would require a fresh out-of-sample test to confirm" — never "we found signal
in phase N". The sweep generates questions; only the declared test answers one.

Everything in this session is EXPLORATORY regardless (rule 2.3) — but within that, the
declared test is the weight-bearing result and the sweep is scenery.

---

## Part 3 — Link A: MJO ↔ buoy swell

Question: does MJO state relate to wave height at buoy 51001?

Data: `analysis_daily`, exploration winters only, days where both `mjo_phase`/`mjo_amplitude`
and `buoy_51001_wvht_mean` are present. Note the overlap: 51001's record and the MJO record
both have gaps, so report how many winter days actually have both.

**Declared test:** compare the distribution of `buoy_51001_wvht_mean` on favourable-phase
days (6–8, amp>1) vs unfavourable-phase days (2–4, amp>1). Report mean, median, and a simple
effect size (difference in means, and the difference as a fraction of the pooled sd). Report
the day counts behind each group.

**Descriptive sweep:** mean and median `wvht_mean` for each of the 8 phases (amp>1),
plotted against the all-day mean as a reference line. Save to
`outputs/figures/mjo_link_a_swell_by_phase.png`.

Plain-language read: is swell materially higher in favourable phases? State it without
overclaiming.

---

## Part 4 — Link B: MJO ↔ Utah snow

Question: does MJO state relate to Wasatch storms?

Reuse the storm-event definition from Phase 5a (`detect_events`, 1.0-inch `any2` as the
primary, with 0.5-inch `any2` as a sensitivity check since 1.0-inch under-counts slow
storms per Q26). Exploration winters only.

**Declared test:** storm rate on favourable-phase days (6–8, amp>1) vs unfavourable-phase
days (2–4, amp>1), each beside the overall base rate. Because the MJO's influence is
lagged, run this at two framings and declare both now: (i) same-day — storm rate on days
in each phase group; (ii) lagged — storm rate in the 1–14 days following a phase-group day.
Report POD/POFD/PSS-style numbers or a clean rate-vs-base-rate table, with day/event counts.

**Descriptive sweep:** storm rate for each of the 8 phases (amp>1) against the base rate,
plotted. Save to `outputs/figures/mjo_link_b_storms_by_phase.png`.

Plain-language read: are storms materially more common in favourable phases? State plainly.

---

## Part 5 — The chain read (the deliverable)

Combine A and B into one short plain-language section in the report: **where does the chain
break?** Use the branching logic from "Why this session exists". Be explicit and honest —
this is the paragraph the write-up will draw on. If both links are weak, say so; if one
holds and one breaks, name which.

Two honest caveats to state in this section, not bury:

- **Sample.** 16 exploration winters, and the MJO/buoy overlap is smaller still. This is a
  coarse mechanism check, not a climatology. A weak or absent link here does not overturn
  the published MJO–western-US literature; it says the signal is not clearly visible at
  this scale (Q17).
- **MJO coverage.** The MJO series ends 2024-02-24 and the buoy has its 2010–2014 gap, so
  the days with both are a subset. Report the exact overlap count.

---

## Part 6 — Tests

`tests/test_mjo.py` (or extend an existing test file). No network.

1. Phase grouping: a day with phase 7, amp 1.4 is "favourable"; phase 3, amp 1.2 is
   "unfavourable"; phase 7, amp 0.8 is excluded (amp too low); phase 1 or 5 excluded from
   the primary contrast.
2. Base-rate sanity: on a synthetic set where storms are independent of phase, the
   favourable-vs-unfavourable storm rates come out ≈ equal (no manufactured effect).
3. Overlap counting: given series with known gaps, the both-present day count is correct.
4. Lagged framing: a storm on day D+7 is correctly attributed to a favourable day D in the
   1–14 day lagged test.

---

## Validation

Run all and paste real output.

1. **Tests pass** — `pytest tests/ -v`, all prior plus new.
2. **Overlap** — print the number of exploration winter days with both MJO and buoy present
   (Link A), and with MJO present for the snow test (Link B).
3. **Link A declared test** — favourable vs unfavourable swell: means, medians, effect
   size, day counts. Confirm the sweep plot saved.
4. **Link B declared test** — favourable vs unfavourable storm rate vs base rate, both
   same-day and lagged framings, with counts. Confirm the sweep plot saved.
5. **Chain read** — paste the plain-language "where does the chain break" section.
6. **Discipline check** — confirm in the report that no descriptive-sweep observation is
   stated as a finding; any standout phase is labelled exploratory-only.
7. **Seal intact** — confirm `include_holdout` never set True; print the winters used.

**Do NOT** print held-out values anywhere.

---

## Consistency check

Before the commit message, re-read all three files and report any contradiction,
duplicated heading, or findings-log ordering issue. Report only. (H1–H5 are pre-approved.)

Confirm every new result entry in DECISIONS.md Section 2 is marked **EXPLORATORY**, and
that the declared test and the descriptive sweep are clearly distinguished in the findings
log (the sweep entries must not read as conclusions).

---

## File updates

### SPEC.md
- Version bump 0.6 → 0.7.
- H3: SPEC 1.1 date softened + 51101 caveat. H4: SPEC 6.1 gloss tightened + Q25 pointer.
- Section 8 stays empty.

### STATUS.md
- Section 1: mark Phase 5b done; note modelling remains gated and the project is heading to
  Phase 6 (protocol) then Phase 8 (write-up), with the null result standing.
- Section 2: next is **Phase 6 planning** — lock the evaluation protocol expecting a null,
  OR, if the owner prefers, proceed toward write-up. Flag it needs a planning conversation.
- Section 3: build-log row. Section 4: note any new resolved items.
- Section 6: log consistency result; mark Phase 5a's five items resolved (H1–H5).

### DECISIONS.md
- Header to 0.7.
- Q18 Resolved: state the Link A result plainly (does buoy swell track the MJO?).
- Q17 updated figure (H2). Q19 status note (H5).
- Findings log: add Link A and Link B declared-test results (EXPLORATORY), and the chain
  read. Descriptive-sweep observations, if recorded, explicitly labelled exploratory-only,
  not findings.
- Append any new open questions.

---

## Commit message

Do not commit — prepare and output only.

```
feat(analysis): MJO mechanism check — where the folklore chain breaks (Phase 5b)

- Tests the two internal links of the MJO->swell->snow chain that the
  folklore skips: Link A (MJO<->buoy swell, resolves Q18) and Link B
  (MJO<->Utah snow)
- Declared confirmatory test (fixed in advance): MJO phases 6-8 vs 2-4 on
  amplitude>1 days, physically motivated by the western-US precipitation
  literature; carries weight because pre-specified
- Descriptive sweep of all 8 phases shown as context only, explicitly not
  promotable to a finding
- Link B run same-day and lagged (1-14 days); storm events reuse Phase 5a
  detector (1.0-in any2 primary, 0.5-in sensitivity)
- Plain-language chain read: where the chain breaks, with sample-size and
  MJO-coverage caveats stated not buried
- tests/test_mjo.py: phase grouping, no-manufactured-effect base-rate
  sanity, overlap counting, lagged attribution
- Exploration-only; seal intact; all results EXPLORATORY; no model built
- Housekeeping: Q18/Q17/Q19 updated, SPEC 1.1 date + 51101 caveat, SPEC 6.1
  gloss tightened (H1-H5 from Phase 5a's consistency check)

SPEC.md: v0.7
```
