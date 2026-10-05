# How this project was run

This folder is the working record behind the study. The answer itself is in the
[main README](../README.md).

## The way of working

The owner planned the work and made every decision. For each session the owner wrote a
prompt file, with help from Claude in a chat. Claude Code then wrote all the code, one
session per prompt, and did nothing outside that prompt's scope. The owner reviewed every
change and committed it by hand.

## What each file is

| File | What it is |
| --- | --- |
| [`SPEC.md`](SPEC.md) | The method and the source of truth: the question, the data, the critical rules, and the evaluation protocol |
| [`STATUS.md`](STATUS.md) | The state of the project and a session-by-session build log |
| [`DECISIONS.md`](DECISIONS.md) | Open questions Q1–Q32 and the findings log F1–F7 |
| [`CLAUDE.md`](CLAUDE.md) | Standing instructions to Claude Code, read at the start of every session |
| [`sessions/`](sessions/) | Every session prompt, in the order they were run |

## How the files enforced the method

The held-out winters were sealed in code. The data loader leaves them out unless a caller
asks for them by name, so they could not be read by accident.

The evaluation rule was written into SPEC Section 8 and frozen before the seal was opened.
It fixed the pop threshold, the storm definition, the window and the pass mark in advance.
The held-out run then executed that section once, as written.

## These files are an archive

They are kept exactly as they were at the end of the project. Nothing has been edited to
bring them up to date, so some lines are out of date. For example, `CLAUDE.md` still says
SPEC Section 8 is empty until Phase 6. Paths in all of them refer to the old layout, when
these files sat in the repository root and the session prompts sat in `docs/`.

## Suggested reading order

1. [`SPEC.md`](SPEC.md) Section 8: the rule, written down before the answer was known.
2. [`DECISIONS.md`](DECISIONS.md) F7: the held-out result.
3. [`DECISIONS.md`](DECISIONS.md) F4–F6: why the folklore fails.
4. [`STATUS.md`](STATUS.md): how the work unfolded, session by session.
