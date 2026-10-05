# Phase 8c — Hypothesis-visualisation figure: buoy pops over the SWE curve
**Spec version: already at 1.0. Presentation-only; no version bump.**

---

## READ THIS FIRST

Read `README.md` in full and `STATUS.md` in full before doing anything. Then read this
prompt in full.

**This is a presentation-only session. It draws a new figure from data that already
exists — it runs no new analysis and computes no new finding.** The figure visualises the
folklore's hypothesis so a reader can see it succeed or fail by eye: buoy "pops" and the
window in which they claim a storm, overlaid on the actual snowpack curve.

**Apply all critical rules** (SPEC Section 2). Two bind here:
- **Rule 2.3 — the seal.** Use **exploration winters only**. Do NOT load, plot, or touch
  the six held-out winters (2004, 2005, 2006, 2008, 2021, 2022). The seal is spent, but
  making fresh visualisations on held-out data is post-hoc exploration and is not done.
  `load_analysis_data` defaults to exploration-only; do not pass `include_holdout=True`.
- **Consistency with the locked rule.** Use the *same* pop and storm definitions the study
  locked, so the figure matches the test — pop ≥ 3.9530 m, storm 0.5-inch `any2`, window
  10–18 days. This is a drawing of the real rule, not a new variant.

### CRITICAL — scope discipline

- Do NOT run, recompute, or alter any analysis, number, finding, or existing figure.
- Do NOT touch SPEC.md (Section 8 is frozen), DECISIONS.md findings, or any README number.
- Do NOT add this figure to the README in this session — it is generated to
  `outputs/figures/` as a standalone. The owner decides later whether it earns a place.
- Do NOT hand-pick the four winters to flatter the result. They are chosen by the declared
  neutral rule below, not by what they show.

Do NOT commit — prepare changes, output the commit message, and stop.

---

## What the figure shows — the hypothesis, drawn

A 2×2 grid of four exploration winters. Each panel shares the same design:

- **The SWE curve** for the winter — the cross-station combined snow-water-equivalent signal
  (use the same combined signal the detector uses; the `any2` construction's underlying mean
  or the per-winter combined SWE, whichever the existing code exposes — match the detector
  plot `storm_detector_check_2016.png` in construction so the two are consistent).
- **Detected storm events** marked on the curve — the step-ups — exactly as the detector
  defines them (0.5-inch `any2`, `detect_events`, bridge 1). Shade or mark each storm event
  the same way the existing detector-check figure does, for visual consistency.
- **Buoy pops** for that winter: each pop event (pop day ≥ 3.9530 m, `detect_events`,
  bridge 1, dated by first day) drawn as a marker at the pop's first day.
- **The folklore's prediction window as a whisker/band.** From each pop, draw a translucent
  horizontal band spanning **pop_first_day + 10 to pop_first_day + 18** — the exact window
  the locked rule uses. This band *is* the folklore's claim: "a storm should begin somewhere
  in here." A light shaded rectangle reads more clearly than a thin line when pops cluster;
  prefer the band. Position it so it is clearly associated with its pop (e.g. a small
  triangle marker at the pop date on or just above the SWE curve, with the band extending
  rightward from it).

**The point of the figure, stated in its own caption:** where a pop's 10–18-day band overlaps
a storm step-up, the folklore "hit"; where a band points at flat or melting snowpack, it
missed; and storms that rise with no band pointing at them are storms the buoy never called.
A true signal would show bands landing on step-ups consistently. The figure lets the reader
see that they do not.

---

## Winter selection — declared rule, not hand-picked

Choose **four exploration winters: two from the pre-gap era (≤ 2009) and two from the
post-gap era (≥ 2015)**, so both climate eras are visible and no single period is doing the
arguing. Within each era, pick by a neutral rule stated in the report — **the two most
data-complete winters in that era** (fewest missing buoy days, so the pops are fully drawn),
breaking ties by earliest. Record which four were chosen and why in the figure's report note.
Do not choose winters by how well or badly the pops line up with storms.

Order the 2×2 grid chronologically (earliest top-left) for readability.

---

## Implementation notes

- Add a small plotting entry point (e.g. `--hypothesis-grid` mode on an existing analysis
  module, or a short script `src/powderbuoy/figures.py`) that reads existing processed data
  and the config winter lists, applies the already-tested `detect_events` for both pops and
  storms, and renders the grid. Reuse the existing detector/event code — do not reimplement
  pop or storm detection.
- Shared, readable axes per panel: date on x (Nov–Apr), SWE (inches) on y. Label the panel
  with the winter (e.g. "Winter 2016 — Nov 2016 to Apr 2017"). A single shared legend for the
  whole figure (SWE curve, storm event, pop, 10–18-day window) rather than one per panel.
- Keep it legible: four panels, translucent bands, thin curve. If pops are dense in a winter
  the bands may overlap — that is fine and honest (it shows how often the buoy pops), but keep
  the alpha low enough that overlaps do not become a solid block.
- Save to `outputs/figures/hypothesis_pops_over_swe_grid.png` at a resolution that stays sharp
  (e.g. 150+ dpi).
- This is exploration-winter data only. Print, in the run output, the four winters used and
  confirm none is a held-out winter.

---

## Validation

1. **Tests still pass** — `pytest tests/ -v` (expect 63; nothing analytical changed). If a
   small plotting helper is added, an optional light test that it selects four winters, two
   per era, none held-out, is welcome but not required.
2. **Seal intact** — confirm the figure used exploration winters only; print the four winters
   chosen; confirm none of 2004, 2005, 2006, 2008, 2021, 2022 appears and that
   `include_holdout` was never set True.
3. **Definitions match the locked rule** — confirm pops use ≥ 3.9530 m and storms use
   0.5-inch `any2`, the same as SPEC 8.2, so the figure is consistent with the test.
4. **Figure saved** — confirm `outputs/figures/hypothesis_pops_over_swe_grid.png` exists and
   describe it in words: are the bands visibly failing to line up with the step-ups (the
   expected picture, given the null)?

---

## Consistency check

Re-read the README and STATUS. Confirm no analytical content, number, or existing figure was
changed; the new figure is standalone in `outputs/figures/` and not yet in the README; and the
project remains coherent at v1.0. Report only.

---

## File updates

### STATUS.md
- Add a brief build-log row: a hypothesis-visualisation figure (buoy pops with their 10–18
  day windows over the SWE curve, four exploration winters two-per-era) generated to
  `outputs/figures/` — presentation only, no analysis, seal untouched. Project stays at v1.0.

### Everything else
- New figure file, and the small plotting entry point. No changes to SPEC, DECISIONS, the
  README, or any analytical code or number.

---

## Commit message

Do not commit — prepare and output only.

```
docs(figures): hypothesis-visualisation grid — buoy pops over the SWE curve

- New standalone figure outputs/figures/hypothesis_pops_over_swe_grid.png: a
  2x2 grid of four exploration winters (two pre-gap, two post-gap, chosen as
  the most data-complete in each era), each showing the SWE curve with
  detected storms, the buoy pops, and each pop's 10-18 day prediction window
  drawn as a translucent band — the folklore's claim, drawn so it can be seen
  to hit or miss
- Uses the locked definitions (pop >= 3.9530 m, storm 0.5-in any2, window
  10-18 d) so the picture matches the test; reuses existing detect_events
- Exploration winters only; seal intact; include_holdout never True
- Presentation only: no analysis re-run, no number changed, not added to the
  README (standalone in outputs/figures/); 63 tests still pass
- Project remains COMPLETE at v1.0

SPEC.md: v1.0 — PROJECT COMPLETE (figure follow-up)
```
