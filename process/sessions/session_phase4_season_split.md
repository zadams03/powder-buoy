# Phase 4 — Season Split & Seal the Held-Out Set
**Spec version going in: 0.4 | Version to bump to: 0.5**

---

## READ THIS FIRST

Read `SPEC.md` in full, `STATUS.md` in full, and `DECISIONS.md` in full before doing
anything. Then read this prompt in full before writing any code.

**Apply all critical rules** (SPEC Section 2). This session is governed above all by rule
2.3 — the held-out set is sealed. This is the session that *creates* that seal. Get it
right.

### Why this session exists — and why it is different

Every session so far has built things. This one barely builds anything. It makes one
irreversible decision: which winters are locked away as the final test set, untouched
until the evaluation protocol is written and frozen.

Once sealed, looking at the held-out winters burns them (rule 2.3). So the entire point of
this session is to draw the line correctly, write it down precisely, and put a guard in
the code so the sealed winters cannot be read by accident.

**The split was decided during planning. This session executes that decision — it does not
revisit it, and it does not look at any data to inform it.** Choosing a split by inspecting
the data would defeat the seal.

### CRITICAL — scope discipline

- Do NOT compute any correlation, lag scan, contingency table, or model. No analysis of
  any kind. That is Phase 5.
- Do NOT read, print, plot, or summarise the *values* in any held-out winter. You may
  reference held-out winters by their year label only.
- Do NOT fill Section 8 of SPEC. It stays empty until Phase 6.
- Do NOT change the chosen split. The winter lists below are fixed.

Implement exactly what is specified. Do NOT commit — prepare changes, output the commit
message, and stop.

---

## Part 1 — Housekeeping (do first, quick)

Two stale-wording fixes carried from 0C's consistency check, owner-approved.

**H1 — Bump DECISIONS.md header.** Its header still reads "Spec version: 0.3". This
session bumps to 0.5. Update the DECISIONS.md header to "Spec version: 0.5". Going
forward, treat "bump all three file headers" as a standard step — note this in STATUS
Section 6 so it isn't missed again.

**H2 — Fix SPEC Section 7 tense.** Section 7 reads "the usable record is at most around 40
winters (to be confirmed in Session 0A...)" — future tense, now stale. Reword to align
with Section 11.1 and 3.1: state that Session 0A measured it, and fold in the Q21 nuance —
the confirmed record is not one unbroken ~40-winter span but two eras either side of the
2010–2014 buoy gap, giving 22 winters usable for the four-model comparison once MJO
coverage is required (see Part 2 background). Keep it to two or three sentences.

Neither touches data or code.

---

## Part 2 — Background: the split, and how it was derived (do not re-derive)

This is recorded so the session and the files carry the full reasoning. These numbers were
worked out during planning from the coverage reports of 0B and 0C. **Do not recompute them
from the data — take them as given.**

**Usable-winter accounting.** A winter is labelled by its starting year and runs Nov–Apr
(SPEC 2.1). The four-model comparison (SPEC Section 7) needs buoy, snow, and MJO all
present across the winter. Applying that:

- Both-good winters (buoy + ≥2 snow stations), from 0B: 25 winters.
- The MJO series ends 2024-02-24 (0C). Winters 2023, 2024, 2025 therefore lack complete
  MJO coverage and cannot join the four-model comparison. They are set aside as
  **folklore-only** — usable later for the simpler buoy-vs-snow counting (Phase 5, which
  needs no MJO), but never part of the sealed split.
- That leaves **22 winters** usable for the split, in two eras either side of the buoy gap:
  - **Pre-gap (14):** 1989, 1990, 1992, 1994, 1996, 1998, 1999, 2000, 2001, 2003, 2004,
    2005, 2006, 2008
  - **Post-gap (8):** 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022

**The chosen split — Option D, chronological within each era.** The held-out (test) set
takes the *latest* winters from each era. This keeps a genuine hindcast property — within
each era, every test winter is later than every training winter, so the method never
trains on a future winter to score a past one — while ensuring both climate eras appear in
the test set (a pure chronological split would have put the entire test set in the modern
era and starved training of modern winters).

**The exact lists (fixed — this is what gets sealed):**

- **HELD-OUT (test), 6 winters:** 2004, 2005, 2006, 2008, 2021, 2022
- **EXPLORATION (train + cross-validation), 16 winters:** 1989, 1990, 1992, 1994, 1996,
  1998, 1999, 2000, 2001, 2003, 2015, 2016, 2017, 2018, 2019, 2020
- **FOLKLORE-ONLY (set aside, not in the split), 3 winters:** 2023, 2024, 2025

**Known, accepted limitation** (record it, do not try to fix it): the held-out set leans
older (four of six are 2004–2008) and the modern era is represented by only two winters
(2021, 2022), because the buoy gap left only 8 modern winters to draw from. The final test
therefore rests on these six specific winters and cannot be reshuffled. This was accepted
knowingly during planning.

---

## Part 3 — Write the split into config

Add a `seasons` block to `config/regions/utah.yaml`. Explicit lists, not ranges or rules —
the whole point is that the split is fixed and auditable, not regenerated by logic that
could change.

```yaml
seasons:
  # Winter labelled by starting year; runs Nov 1 – Apr 30 (see SPEC 2.1).
  # Split decided in planning (Option D, chronological within each era).
  # See DECISIONS.md Q13 and Q21 for the full reasoning.
  exploration:
    - 1989
    - 1990
    - 1992
    - 1994
    - 1996
    - 1998
    - 1999
    - 2000
    - 2001
    - 2003
    - 2015
    - 2016
    - 2017
    - 2018
    - 2019
    - 2020
  held_out:
    - 2004
    - 2005
    - 2006
    - 2008
    - 2021
    - 2022
  folklore_only:      # no complete MJO; usable for buoy-vs-snow counting only, never the split
    - 2023
    - 2024
    - 2025
```

---

## Part 4 — The code guard (the real deliverable)

Add season-aware loading to the codebase, with the seal enforced in code, not just in
intent (rule 2.3). Put this in a sensible module — e.g. `src/powderbuoy/seasons.py` plus a
loader function, matching existing structure.

```python
def winter_of(date) -> int | None:
    """Return the winter start-year label for a date, or None if outside Nov–Apr.
    Nov–Dec of year Y -> Y. Jan–Apr of year Y -> Y-1. May–Oct -> None (not winter).
    """


def load_analysis_data(region: str = "utah",
                       include_holdout: bool = False) -> pd.DataFrame:
    """Load analysis_daily, filtered to winters only, with the held-out set
    EXCLUDED BY DEFAULT.

    Adds a 'winter' column (start-year label) and a 'season_set' column
    ('exploration' / 'held_out' / 'folklore_only').

    include_holdout defaults to False: the returned frame contains only
    exploration (and, where relevant, folklore_only) winters. Held-out winters
    are dropped.

    include_holdout=True returns held-out winters too. Any caller passing True
    MUST include an inline comment citing the locked protocol version that
    authorises it. Before Phase 6 exists, no caller should pass True at all.
    """
```

Requirements:

- Default behaviour excludes the six held-out winters. This is the seal.
- The function reads the winter lists from config, never hardcoded, so config is the
  single source of truth.
- A row whose winter is not in any list (e.g. summer days, or pre-1989 winters with no
  usable data) is excluded from winter-filtered loads; the `season_set` label makes clear
  why.
- Passing `include_holdout=True` should be awkward enough to be deliberate — the docstring
  requires a protocol citation. It should not be the kind of thing done by reflex.

---

## Part 5 — Tests

`tests/test_seasons.py`. No network.

1. `winter_of`: 2015-12-15 → 2015; 2016-02-10 → 2015; 2016-11-02 → 2016; 2016-07-01 →
   None.
2. Default load excludes held-out: the returned frame contains none of 2004, 2005, 2006,
   2008, 2021, 2022.
3. `include_holdout=True` includes them: those six winters appear.
4. `season_set` labelling is correct for a sample of winters from each set.
5. Config is the source: the loader's winter lists match `utah.yaml` exactly (guard
   against drift between code and config).

---

## Validation

Run all and paste real output.

**1. Tests pass**

```
pytest tests/ -v
```

All prior tests plus the new season tests.

**2. The seal holds — default load excludes held-out winters**

```python
from powderbuoy.seasons import load_analysis_data  # adjust import to actual location
df = load_analysis_data(region="utah")  # default: exploration only
print("Winters present (default load):", sorted(df['winter'].unique()))
print("Any held-out winter present?",
      any(w in df['winter'].values for w in [2004,2005,2006,2008,2021,2022]))
```

Expected: the printed winters are exactly the 16 exploration winters (and possibly
folklore-only, if you include those in the default — state which you did and why). The
held-out check must print **False**.

**3. The flag works — held-out winters appear only when explicitly requested**

```python
df_all = load_analysis_data(region="utah", include_holdout=True)
held = sorted(set(df_all['winter'].unique()) - set(df['winter'].unique()))
print("Winters revealed only by include_holdout=True:", held)
```

Expected: exactly [2004, 2005, 2006, 2008, 2021, 2022].

**4. Config/code agreement**

Confirm the loader's lists come from `utah.yaml`, e.g. by showing that editing a winter in
config changes the load (describe or demonstrate). No hardcoded winter list anywhere
except config.

**5. Season labelling spot check**

```python
print(df_all[['winter','season_set']].drop_duplicates().sort_values('winter').to_string())
```

Confirm each winter carries the right label and no winter is double-labelled.

**Do NOT** print any wave, snow, or climate *values* from held-out winters in any
validation step. Year labels and row counts only.

---

## Consistency check

Before the commit message, re-read all three files and report any contradiction,
duplicated heading, or findings-log ordering issue. Report only — do not fix. (H1–H2 are
pre-approved, not new contradictions.)

Confirm specifically that STATUS Section 1's held-out seal line and DECISIONS Q13 now
agree on the exact winter lists.

---

## File updates

### SPEC.md
- Version bump 0.4 → 0.5.
- H2: fix Section 7 tense and fold in the 22-usable-winters / two-era nuance.
- Section 8 stays empty.

### STATUS.md
- Section 1: set the held-out seal line to **SEALED**, with today's date, and list the six
  held-out winters. Mark the season split done.
- Section 2: replace with Phase 5 — the exploration phase (contingency tables → lag scan →
  gated modelling, SPEC 6.1). Note it needs its own planning first, and that it runs on
  exploration winters only.
- Section 3: add build-log row.
- Section 6: log the consistency result; mark 0C's two items resolved; add the "bump all
  three headers each session" note.

### DECISIONS.md
- Header to 0.5 (H1).
- Q13 Resolved: record the exact exploration / held-out / folklore-only winter lists, the
  Option D reasoning, and the accepted limitation (older-leaning test set, only two modern
  test winters). This is the permanent record of the split.
- Q21 Resolved: the record-length risk is now settled by the split — two eras handled by
  chronological-within-era, folklore-only winters set aside. Reference Q13.
- Append any new open questions surfaced.
- No findings entry.

---

## Commit message

Do not commit — prepare and output only.

```
feat(seasons): season split and held-out seal (Phase 4)

- config/regions/utah.yaml: explicit exploration / held_out / folklore_only
  winter lists (Option D — chronological within each era)
- src/powderbuoy/seasons.py: winter_of() and load_analysis_data() with the
  held-out set EXCLUDED BY DEFAULT; include_holdout=True required (and a
  protocol citation) to reveal it — the seal enforced in code, not just intent
- Held-out (test) winters SEALED: 2004, 2005, 2006, 2008, 2021, 2022
- Exploration winters: 1989, 1990, 1992, 1994, 1996, 1998, 1999, 2000, 2001,
  2003, 2015-2020 (16 winters); folklore-only 2023-2025 set aside (no MJO)
- tests/test_seasons.py: winter labelling, default excludes held-out, flag
  reveals it, config/code agreement
- Housekeeping: DECISIONS header bumped to 0.5; SPEC Section 7 tense fixed
- No analysis, no correlation, no modelling; no held-out values read

SPEC.md: v0.5 — HELD-OUT SET SEALED
```
