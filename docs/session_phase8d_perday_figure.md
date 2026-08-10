# Phase 8d — Per-day storm-onset probability after a pop
**Spec version: already at 1.0. Presentation-only; no version bump.**

---

## READ THIS FIRST

Read `README.md` in full and `STATUS.md` in full before doing anything. Then read this
prompt in full.

**This is a presentation-only session. It draws one new figure from data that already
exists. It runs no new statistical test and produces no new finding.** The figure answers a
specific, good question raised by a reader: rather than asking "did a storm begin anywhere in
the 10-18 day window", plot the probability that a storm *begins on each individual day* after
a pop, out to 30 days, against the matching per-day baseline, so any sharp bump around the
commonly cited 12-14 day range would be visible.

**Apply all critical rules** (SPEC Section 2). Two bind here:
- **Rule 2.3, the seal.** Exploration winters only. Do NOT load, plot, or touch the six
  held-out winters (2004, 2005, 2006, 2008, 2021, 2022). `load_analysis_data` defaults to
  exploration-only; do not pass `include_holdout=True`.
- **Consistency with the locked rule.** Use the same pop and storm definitions the study
  locked: pop = daily `buoy_51001_wvht_mean` >= 3.9530 m, storm = 0.5-inch `any2`, events via
  the existing tested `detect_events` (bridge 1, dated by first day).

### Why this figure is worth making

Our existing lag scan (`lag_scan_pss.png`) swept lags 0-30 and found no skill at any lag. But
it is a *windowed* skill score, and a windowed test can smear out a sharp, narrowly-timed
signal by averaging the target days with neighbours that carry none. This figure is the more
direct, more legible per-day view the reader asked for. It is a stronger visual test of the
specific claim "a storm tends to begin about 12-14 days after a pop", and either outcome is
useful: a flat line strengthens the null against a sharper test; a genuine broad bump near
12-14 would be important and worth knowing. We expect flat, given the windowed scan was flat,
but we check directly rather than arguing from the windowed result.

### CRITICAL — scope discipline

- Do NOT run any new statistical test, skill score, or verdict. This is a probability-vs-lag
  plot, descriptive only.
- Do NOT recompute, alter, or restyle any existing figure, number, or finding.
- Do NOT touch SPEC.md (Section 8 frozen), DECISIONS.md findings, or any README number.
- Do NOT add this figure to the README in this session. Generate it standalone to
  `outputs/figures/`. The owner decides later whether it earns a place.
- **No em-dashes anywhere** in the figure title, axis labels, legend, caption, or any report
  text this session writes. Use commas, colons, semicolons, or full stops instead. This
  applies to every piece of text the session produces.

Do NOT commit — prepare changes, output the commit message, and stop.

---

## What to compute (descriptive counting, not a test)

Exploration winters only. Locked definitions throughout.

**Pop events:** pop days (`wvht_mean` >= 3.9530 m) collapsed by `detect_events`, bridge 1,
dated by first day. Reuse the existing code; do not reimplement.

**Storm onset:** the first day of each storm event (0.5-inch `any2`, `detect_events`, bridge
1). A "storm begins on day D" means a storm event's first day is D.

**The per-day curve (the pop line).** For each lag L from 0 to 30 days: over all pop events,
the fraction whose pop-first-day + L is the first day of a storm event, restricting to pops
whose day L still falls inside the same winter (a pop late in April cannot look 30 days ahead
into May; those pops are excluded from the lags that would run past 30 April, and the
denominator for each L counts only pops for which day L is in-season). Report the effective
denominator (number of contributing pops) at each L, because it shrinks at long lags and at
season edges.

**The per-day baseline.** Computed the same way from non-pop anchor days: for each lag L, the
fraction of non-pop anchor days whose day + L is a storm-event first day, same in-season
restriction. Non-pop anchor days are days outside every pop event (consistent with the study's
occasion construction, Q25). This baseline is a nearly flat reference: the background daily
probability that a storm begins L days after an arbitrary day. Plot it as the reference the
pop line is read against (the reader explicitly asked for "against the normal baseline").

**Optional light smoothing, shown alongside not instead of raw.** Per-day counts are small
(there are only tens of pop events across the exploration winters), so the raw pop line will
be noisy. In ADDITION to the raw per-day line, draw a 3-day centred rolling mean of the pop
line so a broad bump is easier to see. Show BOTH the raw and the smoothed pop line, clearly
distinguished in the legend, so the smoothing hides nothing and invents nothing. Do not smooth
the baseline beyond what it naturally is.

---

## The figure

- X-axis: lag in days after a pop, 0 to 30.
- Y-axis: probability a storm begins on that day.
- Lines: raw per-day pop probability; 3-day smoothed pop probability; the per-day baseline.
- Mark the commonly cited 12-14 day region lightly (for example a faint vertical band), so the
  reader can look exactly where the folklore predicts a bump. Label it as the folklore's cited
  range, not as anything the data privileges.
- A clear legend. Readable axes. No em-dashes in any text element.
- Save to `outputs/figures/per_day_storm_onset_after_pop.png` at 150+ dpi.

**Caption (write it into the report and, if the figure supports a caption, onto the figure),
no em-dashes:**

*Probability that a storm begins on each day after a buoy pop, out to 30 days, on the
exploration winters, against the per-day baseline (the background chance a storm begins that
many days after any non-pop day). The folklore predicts a bump around 12 to 14 days. The
per-day pop line stays close to the baseline across the whole range, with no coherent bump in
the cited region; isolated single-day wiggles are expected because each day rests on only tens
of pop events. This is a descriptive visualisation, not a test, and adds no finding: the
study's answer remains F7. A true signal would show a broad rise above the baseline sustained
across several adjacent days near the cited lag, not a lone spike.*

Adjust the caption only to match what the figure actually shows; never state a bump that is not
there, and never explain away one that is (if a genuine broad bump appears near 12-14, report
it plainly as unexpected and worth a closer, properly-tested look, exactly as SPEC 8.4's
"surprising" branch would require for a real test; but note it is exploratory and on the
exploration set).

---

## Validation

1. **Tests still pass** — `pytest tests/ -v` (expect 63; nothing analytical changed).
2. **Seal intact** — confirm exploration winters only; print the winters used; confirm none of
   the six held-out winters appears and `include_holdout` was never True.
3. **Definitions match the locked rule** — pop >= 3.9530 m, storm 0.5-inch `any2`.
4. **Denominators reported** — confirm the per-lag contributing-pop counts are recorded (they
   shrink at long lags), so the noisiness of the tail is visible and honest.
5. **Figure saved** — confirm `outputs/figures/per_day_storm_onset_after_pop.png` exists;
   describe in words whether the pop line stays near the baseline or shows a bump near 12-14.
6. **No em-dashes** — confirm no em-dash appears in the figure text or the report note.

---

## Consistency check

Re-read README and STATUS. Confirm no analytical content, number, or existing figure changed;
the new figure is standalone in `outputs/figures/` and not in the README; the project stays
coherent at v1.0. Report only.

---

## File updates

### STATUS.md
- Add a brief build-log row: a per-day storm-onset-after-pop figure was generated to
  `outputs/figures/` in response to a reader's question, showing per-day storm probability
  after a pop against the per-day baseline, out to 30 days. Presentation only, exploration
  winters, no new test, no finding, seal untouched. Project stays at v1.0.

### Everything else
- New figure file and a small plotting entry point. No changes to SPEC, DECISIONS, the README,
  or any analytical number.

---

## Commit message

Do not commit — prepare and output only. No em-dashes in the message either.

```
docs(figures): per-day storm-onset probability after a pop

- New standalone figure outputs/figures/per_day_storm_onset_after_pop.png,
  answering a reader's question: instead of the windowed 10-18 day test,
  plot the probability a storm begins on each individual day after a pop,
  lags 0 to 30, against the per-day baseline, with the folklore's cited
  12-14 day range marked
- Raw per-day line plus a 3-day smoothed line, both shown; per-lag pop
  denominators recorded since they shrink at long lags
- Locked definitions (pop >= 3.9530 m, storm 0.5-in any2); reuses
  detect_events; exploration winters only; seal intact
- Presentation only: no new test, no number changed, no finding added;
  the study's answer remains F7; 63 tests still pass
- Project remains COMPLETE at v1.0

SPEC.md: v1.0 — PROJECT COMPLETE (figure follow-up)
```
