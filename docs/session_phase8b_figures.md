# Phase 8b — Embed existing figures into the README
**Spec version: already at 1.0. This is a presentation-only follow-up; no version bump unless a header sync is needed.**

---

## READ THIS FIRST

Read `README.md` in full and `STATUS.md` in full before doing anything. Then read this
prompt in full.

**This is a presentation-only session. No new analysis, no new numbers, no regenerated
figures.** The figures already exist in `outputs/figures/` and were validated when they were
made. This session embeds a chosen four of them into the existing README, with captions, at
specified points. Nothing analytical changes.

**Apply all critical rules** (SPEC Section 2). The one that binds here is the spirit of 2.2
and the project's whole credibility model: **a figure must match the recorded analysis
exactly. Do NOT regenerate, restyle, or recompute any figure** — that risks a figure
drifting from its recorded numbers. Embed the existing PNGs as-is. Polish comes from
captions, not re-rendering.

### CRITICAL — scope discipline

- Do NOT run, recompute, or regenerate any analysis or figure. Embed existing files only.
- Do NOT edit any number in the README. Only add images and their captions.
- Do NOT touch SPEC.md Section 8, or any analytical content anywhere.
- Do NOT invent a figure that does not exist in `outputs/figures/`. The four filenames are
  given below; confirm each exists before referencing it. If one is missing, report it and
  skip that embed rather than substituting another.

Do NOT commit — prepare changes, output the commit message, and stop.

---

## Part 0 — Housekeeping (quick, optional-if-safe)

- Move the two stray session-prompt files into `docs/` for tidiness (SPEC 4 keeps prompts
  in `docs/`): `git mv session_phase8_finish.md docs/` if it is tracked; the older
  `session_phase8_readme.md` (superseded, never the final version) may be moved to `docs/`
  or deleted — owner's preference, default to moving it. If either is untracked, a plain
  `mv` is fine. Do not agonise over this; if it is awkward, leave them and note it.
- No spec version bump is required for a presentation change. If the README is considered
  part of the v1.0 deliverable, leave all headers at 1.0. Do not introduce a new version
  for embedding images.

---

## Part 1 — Confirm the figures exist

The four figures to embed, by exact filename in `outputs/figures/`:

1. `dose_response_curve.png`
2. `lag_scan_pss.png`
3. `storm_detector_check_2016.png`
4. `mjo_link_a_swell_by_phase.png`

Confirm each is present (`ls outputs/figures/`). If any is missing, report it and skip only
that one — do not substitute a different figure to fill the slot.

**Image paths in the README** must be relative, so they render on GitHub:
`outputs/figures/dose_response_curve.png` (the README is at the repo root, so this relative
path resolves directly). Use standard Markdown image syntax with meaningful alt text:
`![alt text](outputs/figures/dose_response_curve.png)`.

---

## Part 2 — Place the four figures, each at its point in the argument

Insert each figure at the location described, with the caption given. Captions go
immediately under the image in *italic* prose. Do not alter the surrounding text beyond
inserting the image + caption block. Keep each caption to one or two sentences and, where a
caption states a number, that number must already appear in the README or its source files
(rule 2.2 — if a caption gives a rate, give its baseline too).

**Figure 1 — the dose-response curve. THE headline figure.**
Location: in **## The finding**, immediately after the 2×2 table (after the line ending
"...so no day had to be guessed at.", i.e. after the table and its following paragraph — place
it right after the 2×2 table block, before the PSS paragraph).
Embed `dose_response_curve.png`.
Caption (adapt to match the actual axes of the figure; keep the meaning):
*Storm likelihood after a pop, swept across pop thresholds, against the base rate (horizontal
reference). The line does not climb as the threshold tightens and does not separate from the
base rate — the visual form of the null. Exploration winters; the held-out test confirmed the
same flat picture.*

**Figure 2 — the lag scan.**
Location: in **## The finding**, in the paragraph about the lag scan, immediately after the
sentence "There was no bump." (around line 130).
Embed `lag_scan_pss.png`.
Caption:
*Peirce skill score against lag, 0–30 days. A real regime signal would show a broad bump
across neighbouring lags; instead the curve is flat and slightly negative throughout, with
nothing at the folklore's own 14 days. Exploration winters, EXPLORATORY.*

**Figure 3 — the detector validation.**
Location: in **## What we did**, after the sentence explaining the independent precipitation
cross-check (the sentence ending "...so this is corroboration rather than circularity.").
Embed `storm_detector_check_2016.png`.
Caption:
*The storm detector checked by eye for one winter (2016): each detected storm event marked on
the raw combined SWE curve. The marks land on the genuine step-ups, not on flat or melting
stretches — evidence the flat result reflects the buoy, not a broken detector.*

**Figure 4 — the MJO mechanism (Link A).**
Location: in **## What was not tested**, within the MJO bullet, after the sentence about
swell being higher in the predicted phases "...2.98 m against 2.82 m..." / "too crude to read."
Place the figure at the end of that bullet.
Embed `mjo_link_a_swell_by_phase.png`.
Caption:
*Mean wave height at 51001 by MJO phase (amplitude > 1), against the all-day mean. Swell is
marginally higher in the phases the hypothesis predicts, but by only ~0.18 of a standard
deviation — the buoy is a real but far too crude an index of the MJO to be read as a
forecast. Exploration winters, EXPLORATORY.*

If a figure's actual axes or content differ from what the caption assumes, adjust the caption
to describe what the figure truly shows — never change the figure, and never state a number a
caption cannot support from the files.

---

## Part 3 — Add a short "Figures" note to the repo map (optional, light)

In **## The repository** table, the `outputs/` row already mentions figures. Optionally add
one clause noting that the key figures are embedded above and the full set (including the
z-score lag scan, the MJO snow-link, the seam check, and raw-data winter plots) lives in
`outputs/figures/`. Keep it to one clause; do not add a new table or list.

---

## Validation

1. **Tests still pass** — `pytest tests/ -v` (expect 63; nothing analytical changed).
2. **All four image links resolve** — confirm each referenced PNG exists at the path written,
   and that paths are relative to the repo root so they render on GitHub.
3. **No number changed** — confirm the only README edits are inserted image+caption blocks
   (and the optional one-clause repo-map note); every pre-existing number is untouched.
4. **Caption self-check (rule 2.2)** — confirm no caption states a rate without its baseline,
   and no caption asserts a number absent from the README or its sources.

---

## Consistency check

Re-read the README and STATUS. Confirm: the four figures are placed at the described points,
captions match what the figures actually show, no analytical text or number was altered, and
STATUS still reads coherently as project-complete at v1.0. Report only.

---

## File updates

### README.md
- Four image + caption blocks inserted at the specified points.
- Optional one-clause note in the repository table's `outputs/` row.
- No other changes.

### STATUS.md
- Add a brief build-log row (or extend the Phase 8 row) noting the README gained its four
  embedded figures — a presentation follow-up, no analysis. Keep the project at v1.0 /
  complete.

### Housekeeping
- Session-prompt files moved to `docs/` if trivial (Part 0).

---

## Commit message

Do not commit — prepare and output only.

```
docs(readme): embed the four key figures into the write-up

- README.md: embedded existing, already-validated figures at the points they
  illustrate — dose-response curve (the null, in The Finding), lag scan (no
  bump at any lag), storm-detector check (detector validated against the raw
  SWE curve), MJO Link A (swell barely tracks the MJO). Captions carry the
  baseline with every rate (rule 2.2)
- Figures embedded as-is, not regenerated or restyled — they match the
  recorded analysis exactly; polish is in captions, not re-rendering
- No analysis re-run, no number changed; 63 tests still pass
- Housekeeping: session-prompt files moved into docs/
- Project remains COMPLETE at v1.0

SPEC.md: v1.0 — PROJECT COMPLETE (presentation follow-up)
```
