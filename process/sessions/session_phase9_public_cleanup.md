# Session Phase 9 — Public repository cleanup

## Purpose

The project is complete. This session tidies the public repository so a visitor can understand it from the first screen. The main audience is meteorologists.

This is **presentation and housekeeping only**. No analysis runs. No result, number, threshold or verdict changes. The seal stays spent and untouched.

## Hard rules for this session

1. **No git writes.** Do not run `git add`, `git mv`, `git rm`, `git commit` or `git push`. Move files with plain `mv`. The owner stages and commits by hand.
2. **No analysis.** Do not run `holdout_eval`, `events`, `mjo`, `figures` or any ingest module. Do not regenerate any figure or report.
3. **Archived files stay byte-identical.** `SPEC.md`, `DECISIONS.md` and `CLAUDE.md` are moved, not edited. `SPEC.md` Section 8 is frozen (rule 2.3).
4. **`STATUS.md` gets only the two edits in Task 9.** Nothing else in it changes.
5. **README numbers.** Every number you add to the README must already appear in the README, in `STATUS.md`, or in a report in `outputs/`. Quote it exactly. Put the baseline beside every rate (rule 2.2).
6. If any task conflicts with SPEC, or looks out of scope, stop and flag it. Do not guess.

## Tasks

### Task 1 — Move the working files out of the root

Create `process/` and `process/sessions/`. Then:

- `mv SPEC.md STATUS.md DECISIONS.md CLAUDE.md process/`
- `mv docs/session_*.md process/sessions/` — but leave **this** prompt file in `docs/` until the very end of the session (Task 10).

Target root after the session:

```
README.md  LICENSE  pyproject.toml  uv.lock  .gitignore
config/  src/  tests/  outputs/  data/  process/
```

`docs/` should be gone once this prompt is moved at the end.

### Task 2 — Write `process/README.md`

A short page, roughly 30–50 lines, in plain language with short sentences. It must cover:

- How the project was run. The owner planned the work, made the decisions and wrote a prompt file for each session, with help from Claude in a chat. Claude Code wrote all the code, one session per prompt. The owner reviewed and committed every change by hand.
- What each file is: `SPEC.md` (the method and source of truth), `STATUS.md` (state and session-by-session build log), `DECISIONS.md` (open questions Q1–Q32 and findings F1–F7), `CLAUDE.md` (standing instructions to Claude Code), `sessions/` (every session prompt, in order).
- How the files enforced the method: the held-out winters were sealed in code, and the evaluation rule was written into SPEC Section 8 and frozen before the seal was opened.
- That these files are an **archive, kept exactly as they were** at the end of the project. Some lines are therefore out of date (for example, `CLAUDE.md` still refers to Section 8 as empty until Phase 6, and paths refer to the old root layout).
- A suggested reading order: SPEC Section 8, then DECISIONS F7, then F4–F6, then STATUS.

Do not oversell. Do not add any number not already in the README.

### Task 3 — Add a licence

- Add `LICENSE` with the standard MIT text, `Copyright (c) 2026 Zachary Adams`.
- Add `license = "MIT"` to `[project]` in `pyproject.toml`.

### Task 4 — Remove empty placeholder packages

`src/powderbuoy/evaluate/`, `src/powderbuoy/features/` and `src/powderbuoy/models/` each contain only an empty `__init__.py`. First confirm nothing imports them (grep `src/` and `tests/`). Then delete the three folders. If anything imports them, stop and report.

### Task 5 — Make tests skip cleanly on a fresh clone

On a fresh clone, 8 tests fail because `data/processed/analysis_daily.parquet` (or other processed files) do not exist. Make every test that needs processed data **skip** when the file is missing, with a reason like: `processed data not found — run the ingest commands in README.md`.

- Use `pytest.mark.skipif` or a shared fixture in `tests/conftest.py`. Your choice; keep it simple.
- Do not change what any test checks.

### Task 6 — Remove local absolute paths

- In the code (`events.py`, `mjo.py`, `figures.py`, and anywhere else that prints a saved-file path), print the path **relative to `REPO_ROOT`** instead of absolute.
- In the existing report files in `outputs/`, replace the prefix `/Users/zacharyadams/powder-buoy/` with nothing, so the paths become relative. Change no other character in those files.
- Check with `grep -rn "/Users/" --exclude-dir=.git --exclude-dir=.venv .` — it must return nothing.

### Task 7 — Version

- Set `version = "1.0.0"` in `pyproject.toml`.
- Run `uv lock`. Confirm the only change to `uv.lock` is the `powderbuoy` version. If anything else changes (dependency versions), stop and report.

### Task 8 — README

Edit `README.md` as follows. Change nothing else.

**a. Summary at the top.** Directly under the `# Powder Buoy` title, add a short "In brief" block of 4–6 sentences:
- the question (does a wave-height spike at buoy 51001 near Hawaii predict a Wasatch storm 10–18 days later?);
- why a meteorologist would care (if anything works, the buoy must be a proxy for the MJO and the North Pacific storm track, not a storm tracker);
- the method (16 exploration winters, 6 held-out winters sealed until the rule was locked, run once);
- the result with its baseline (storm rate after a pop 0.6818 against a base rate of 0.6339, ratio 1.0755 against a pre-declared bar of 1.20: null confirmed);
- where the chain breaks (swell is higher in the favourable MJO phases by only 0.18 of a standard deviation).

**b. Headline figure.** Directly below the summary, embed `outputs/figures/hypothesis_pops_over_swe_grid.png`. Write its caption only from the Phase 8c row of `STATUS.md`: what the bars and bands mean, how the four winters were chosen by a declared rule, and that it uses the locked definitions. End the caption `Exploration winters, EXPLORATORY.` like the other captions. If the 8c row's winter labels look inconsistent (it names 1989, 1990, 2015, 2016 but gives last-pop dates in 1990, 1991, 2016, 2017), check the figure's own labels and the winter-naming convention in SPEC, use whatever the figure shows, and report what you found.

**c. Per-day figure.** In *The finding*, directly after the lag-scan figure and its caption, embed `outputs/figures/per_day_storm_onset_after_pop.png`. Caption from the Phase 8d row of `STATUS.md` and `outputs/phase8d_per_day_onset_note.txt`: what it plots, that it is flat, and the cited-range average **0.0794 against a baseline of 0.0864**. End it `Exploration winters, EXPLORATORY.` only if that is what the 8d row says it uses; otherwise label it as the 8d row does.

**d. Paths and counts.**
- Update every mention of `SPEC.md`, `STATUS.md` and `DECISIONS.md` to `process/SPEC.md` etc. Make them working relative links where they are not inside code formatting that should stay plain.
- In *The repository* table: update those three rows' paths; add a row for `process/` ("how the project was run: spec, status, decisions log and every session prompt, archived as-is"); add a row for `LICENSE`; update the `outputs/` row, which says four figures are embedded, to the new count.
- Update the test count ("63 tests", twice) to the real count after Task 5.

**e. How this was built.** Just before *A note on method*, add a short section of 3–5 sentences: the owner designed the study and directed it through written session prompts; Claude Code wrote the code; every rule and decision is recorded in `process/`. Link to `process/README.md`.

### Task 9 — `process/STATUS.md`

Only these two edits:
- Change the **Last updated** line to Session 9 and today's date, "(repository cleanup for public release; presentation only)".
- Add a build-log row for **9** at the top of the build-log table (the table is newest first), spec version `1.0 (no change)`. Record what each task did, in the same factual style as the 8b–8d rows. Say plainly that the files were moved and that the report files had only their path prefix stripped.

Do not change the Status line, Section 2 or anything else, even though "no next session" is now out of date. Report that in the consistency check instead.

### Task 10 — Last step

Move this prompt into the archive: `mv docs/session_phase9_public_cleanup.md process/sessions/`, then remove the empty `docs/` folder.

## Validation — paste real output for each

1. `uv run pytest tests/ -q` with data present: all pass. State the count.
2. Fresh-clone check: copy the working tree to a temporary folder **excluding `data/processed/`**, run pytest there, and show 0 failed with the skips listed. Delete the temporary folder after.
3. `grep -rn "/Users/" --exclude-dir=.git --exclude-dir=.venv .` returns nothing.
4. Byte-identical check, each must print nothing:
   `cmp process/SPEC.md <(git show HEAD:SPEC.md)`
   `cmp process/DECISIONS.md <(git show HEAD:DECISIONS.md)`
   `cmp process/CLAUDE.md <(git show HEAD:CLAUDE.md)`
5. Every image path and relative link in `README.md` and `process/README.md` resolves to a real file. Show the list.
6. `ls -a` of the root, and `git status`.
7. `git diff --stat` and the `uv.lock` diff.
8. `git diff outputs/` — show that the only changed lines are path lines.

## End of session

- Run the consistency check from `CLAUDE.md` (now `process/CLAUDE.md`). Report only; fix nothing.
- List any question or doubt for the owner.
- Output a suggested commit message, then stop. Suggested shape:
  `chore(repo): tidy for public release — process/ archive, LICENSE, clean test skips (Phase 9)`
