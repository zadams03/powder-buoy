# Powder Buoy — Claude Code instructions

These are standing instructions for every Claude Code session in this project. They are
read automatically at the start of each session, before the session prompt.

## Before any work in a session

- Read `SPEC.md` in full, then `STATUS.md` in full, then `DECISIONS.md` in full.
- Apply all critical rules in `SPEC.md` Section 2. These are non-negotiable and apply to
  every session, whether or not the session prompt restates them.

## Session discipline

- Do exactly what the session prompt file in `docs/` defines. Nothing beyond its scope.
- One session, one scope. If something outside that scope looks broken, missing, or worth
  doing, log it in `DECISIONS.md` as an open question — do not fix it in this session.
- If the session prompt and a spec file disagree, stop and flag it rather than guessing
  which to follow.

## Source of truth

- `SPEC.md` is the source of truth for how the project should work. When code and SPEC
  disagree, SPEC wins.
- `STATUS.md` and `DECISIONS.md` record what has happened and what has been decided.
- Never edit any spec file from memory or from your own assumptions. Edit them only where
  the session prompt or the owner explicitly specifies, and only with content grounded in
  this session's work.
- `SPEC.md` Section 8 (evaluation protocol) is intentionally empty until Phase 6. A
  session that tries to fill it before Phase 6 is a red flag — stop and raise it.

## Git

- Never commit, add, or push. Prepare all changes, output the commit message, and stop.
  The owner reviews and commits by hand.

## Data handling (from SPEC Section 2)

- Raw downloads land in `data/raw/` and are never modified in place.
- Missing data is never silently filled. Gaps become null rows, are counted, and are
  reported. Any fill or interpolation must be explicitly specified in the session prompt.

## End of every session

- Run the session's validation steps and paste the real output — actual numbers, not a
  description.
- Run the consistency check: re-read `SPEC.md`, `STATUS.md`, and `DECISIONS.md` and
  report any place where two entries disagree, any duplicated heading, and any
  findings-log entry out of order. Report only — do not fix silently. The owner decides.
