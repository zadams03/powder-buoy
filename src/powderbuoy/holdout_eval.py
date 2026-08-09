"""Phase 7 — the one-shot held-out evaluation of the locked folklore rule.

**This module is the only place in the project that opens the sealed box.** It calls
`load_analysis_data(include_holdout=True)`, the single authorised use of that argument
(SPEC 8.2 "Data access", SPEC 8.5), and scores the six held-out winters exactly once
against SPEC Section 8 as frozen at spec version 0.8.

Nothing here decides anything. Every value the rule needs — the pop threshold, the storm
definition, the window, the two matching variants, the verdict bar — was fixed in Section 8
before any held-out winter was read, and is copied in below as a literal with its citation.
**No threshold is recomputed, tuned or re-derived on held-out data.** In particular the pop
threshold is the fixed 3.9530 m, NOT the 90th percentile of the held-out distribution:
letting the test set set its own threshold would break the one-shot property (SPEC 8.2).

The counting machinery is `detect_events` and `contingency_from_flags` from `events.py`,
reused unchanged — the same functions every exploration number came from, so the held-out
result and the exploration comparison are like-for-like.

One shot (rule 2.3, SPEC 8.5). This runs once. If anything is changed and re-run after the
result is seen, the seal is burned and every subsequent number is EXPLORATORY forever.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import logging
import subprocess
import uuid

import numpy as np
import pandas as pd

from powderbuoy.config import load_config
from powderbuoy.events import (
    BRIDGE_DAYS,
    build_storm_flags,
    contingency_from_flags,
    snow_gain_columns,
)
from powderbuoy.seasons import load_analysis_data

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------
# The locked rule, copied from SPEC Section 8 (frozen, spec version 0.8).
# Every constant below is quoted, not computed. None is derived from held-out
# data. If one of these disagrees with Section 8, Section 8 wins.
# --------------------------------------------------------------------------

PROTOCOL_SPEC_VERSION = "0.8"

# SPEC 8.2: "A pop day is a day with buoy_51001_wvht_mean >= 3.9530 m."
# The fixed metre value carries over; the percentile is NOT recomputed here.
POP_THRESHOLD_M = 3.9530

# SPEC 8.2: storm day = swe_gain_in >= 0.5 in at >= 2 of the reporting stations.
STORM_THRESHOLD_IN = 0.5
STORM_COMBINATION = "any2"

# SPEC 8.2: "The window is 10 to 18 days after the pop event's first day, inclusive."
LAG_LO = 10
LAG_HI = 18

# SPEC 8.5: the six sealed winters, restated from DECISIONS.md Q13.
HELD_OUT_WINTERS = (2004, 2005, 2006, 2008, 2021, 2022)

# SPEC 8.4: S = (ratio >= 1.20 AND PSS > 0), computed per matching variant.
VERDICT_RATIO_BAR = 1.20

# SPEC 9 register row (SPEC 8.5).
REGISTER_COLUMNS = [
    "run_id",
    "timestamp",
    "git_commit",
    "model_name",
    "features",
    "train_seasons",
    "test_seasons",
    "used_holdout",
    "target_definition",
    "primary_metric",
    "primary_value",
    "baseline_value",
    "status",
    "notes",
]
MODEL_NAME = "folklore_rule_locked_v0.8"

# The exploration comparison, QUOTED from outputs/phase5a_counting_report.txt at the
# same configuration the rule locks (abs_p90 pop, 0.5 in any2, window 10-18, 16
# exploration winters). Nothing here is recomputed — these are Phase 5a's own numbers,
# read off its report, so the comparison is like-for-like and the exploration side is
# not re-derived in a session that has the held-out answer in front of it.
EXPLORATION_COMPARISON = {
    "config": "abs_p90 (3.9530 m) pop, storm 0.5 in any2, window 10-18, 16 exploration winters",
    "a": 79,
    "b": 63,
    "c": 1438,
    "d": 825,
    "storm_rate_pop_claim": 0.5563,
    "storm_rate_pop_noclaim": 0.6197,
    "base_rate": 0.6308,
    "nonpop_rate": 0.6354,
    "pod": 0.0521,
    "pofd": 0.0709,
    "pss": -0.0189,
    "n_pop_occasions": 142,
    "n_storm_events": 246,
}


def _ratio(numerator: float, denominator: float) -> float:
    """SPEC 8.3's formulas are all simple ratios; a zero denominator is not a zero rate."""
    return float(numerator) / float(denominator) if denominator else np.nan


# --------------------------------------------------------------------------
# Opening the box
# --------------------------------------------------------------------------


def load_holdout_frame(region: str = "utah") -> pd.DataFrame:
    """The six held-out winters, on their own, sorted by date.

    **This is the project's single authorised unsealing.** SPEC 8.2 ("Data access") and
    SPEC 8.5 authorise exactly one call to `load_analysis_data(include_holdout=True)`,
    made by Phase 7, against Section 8 as frozen at spec version 0.8.
    """
    # AUTHORISED BY SPEC Section 8 (LOCKED, spec version 0.8) — 8.2 "Data access" and
    # 8.5. The single authorised use of include_holdout=True in this project.
    df = load_analysis_data(region=region, include_holdout=True)

    # Scored on their own: exploration winters are NOT pooled into the held-out tables
    # (SPEC 8.2). Folklore-only winters (2023-2025) are in no split and are not used
    # (SPEC 8.5).
    df = df[df["season_set"] == "held_out"].copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)

    winters = tuple(sorted(int(w) for w in df["winter"].unique()))
    if winters != HELD_OUT_WINTERS:
        raise ValueError(
            f"Held-out winters loaded {winters}, expected {HELD_OUT_WINTERS} "
            "(SPEC 8.5). Refusing to score."
        )
    return df


def build_locked_pop_flags(df: pd.DataFrame, wvht_column: str) -> pd.Series:
    """The pop flag exactly as SPEC 8.2 defines it: wvht_mean >= the FIXED 3.9530 m.

    Deliberately not `events.build_pop_flags`, which resolves its thresholds from the
    percentiles of whatever frame it is handed — on held-out data that would let the test
    set choose its own threshold, which SPEC 8.2 forbids in as many words.

    Returns a nullable boolean series. A day where the buoy did not report is pd.NA: it
    has no pop flag, is an occasion on neither row, and is counted and reported rather
    than read as "no pop" (SPEC 8.2, rule 2.5).
    """
    wvht = pd.Series(df[wvht_column].to_numpy(), index=pd.DatetimeIndex(df["date"]))
    flag = pd.Series(pd.NA, index=wvht.index, dtype="boolean")
    defined = wvht.notna()
    flag[defined] = wvht[defined] >= POP_THRESHOLD_M
    return flag


# --------------------------------------------------------------------------
# Scoring — one call to the shared machinery, read out under both variants
# --------------------------------------------------------------------------


def score_locked_rule(df: pd.DataFrame, gain_columns: dict[str, str], wvht_column: str) -> dict:
    """Run the locked rule once and return both matching variants' tables and metrics.

    `contingency_from_flags` builds the occasions, the windows and the claimed pop row in
    one pass (SPEC 8.2's "Occasion construction"). Both variants come out of that single
    pass rather than two: SPEC 8.3 states that the comparison row is identical in both and
    that the pop row differs only in how `a` is counted — with claiming, pops in date
    order each claim the earliest unclaimed storm start; without claiming, `a` counts pops
    whose window contains any storm start, which is exactly `storm_rate_pop_noclaim` x
    (usable pop occasions). `b` = usable pop occasions - `a` in both.
    """
    pop_flags = build_locked_pop_flags(df, wvht_column)
    storm_flags = build_storm_flags(df, gain_columns, STORM_THRESHOLD_IN)[STORM_COMBINATION]
    winters = pd.Series(df["winter"].to_numpy(), index=pd.DatetimeIndex(df["date"]))

    result = contingency_from_flags(
        pop_flags,
        storm_flags,
        LAG_LO,
        LAG_HI,
        bridge=BRIDGE_DAYS,
        groups=winters,
    )

    n_pop = int(result["n_pop_occasions"])
    a_noclaim_exact = result["storm_rate_pop_noclaim"] * n_pop
    a_noclaim = int(round(a_noclaim_exact))
    if not np.isnan(a_noclaim_exact) and abs(a_noclaim_exact - a_noclaim) > 1e-6:
        raise ValueError(
            "Without-claiming hit count is not integral — the 2x2 cannot be read out "
            f"({a_noclaim_exact})."
        )

    variants = {
        "with_claiming": _metrics(result["a"], result["b"], result["c"], result["d"]),
        "without_claiming": _metrics(
            a_noclaim, n_pop - a_noclaim, result["c"], result["d"]
        ),
    }
    return {"counts": result, "variants": variants}


def _metrics(a: int, b: int, c: int, d: int) -> dict:
    """Every metric in SPEC 8.3, computed from one 2x2."""
    total = a + b + c + d
    storm_rate_pop = _ratio(a, a + b)
    base_rate = _ratio(a + c, total)
    pod = _ratio(a, a + c)
    pofd = _ratio(b, b + d)
    return {
        "a": int(a),
        "b": int(b),
        "c": int(c),
        "d": int(d),
        "storm_rate_pop": storm_rate_pop,
        "base_rate": base_rate,
        "ratio": _ratio(storm_rate_pop, base_rate),
        "nonpop_rate": _ratio(c, c + d),
        "pod": pod,
        "pofd": pofd,
        "pss": pod - pofd,
    }


def verdict(variants: dict) -> dict:
    """SPEC 8.4, applied mechanically. S = (ratio >= 1.20 AND PSS > 0), per variant."""
    s = {
        name: bool(m["ratio"] >= VERDICT_RATIO_BAR and m["pss"] > 0)
        for name, m in variants.items()
    }
    held = sum(s.values())
    if held == 0:
        label = "NULL CONFIRMED"
    elif held == len(s):
        label = "SURPRISING"
    else:
        label = "SPLIT / inconclusive"
    return {"s": s, "label": label}


# --------------------------------------------------------------------------
# Data-state counts reported alongside the tables (SPEC 8.3, rule 2.5)
# --------------------------------------------------------------------------


def station_reporting_counts(df: pd.DataFrame, gain_columns: dict[str, str]) -> dict:
    """How many stations actually reported a SWE gain each day.

    SPEC 8.2 expects all five to report in every held-out winter (all were installed
    before the earliest one) but requires the count to be reported either way, because
    "at least 2 stations" means at least 2 of the stations actually reporting.
    """
    reporting = df[list(gain_columns.values())].notna().sum(axis=1)
    return {
        "days": int(len(df)),
        "days_all_five_reporting": int((reporting == len(gain_columns)).sum()),
        "days_fewer_than_two_reporting": int((reporting < 2).sum()),
        "min_stations_reporting": int(reporting.min()) if len(df) else 0,
    }


# --------------------------------------------------------------------------
# Experiment register (SPEC Section 9, required by SPEC 8.5)
# --------------------------------------------------------------------------


def git_commit() -> str:
    """The commit this run was made from, plus a dirty marker (SPEC 4.3)."""
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        dirty = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        return f"{commit}-dirty" if dirty else commit
    except (subprocess.CalledProcessError, FileNotFoundError):  # pragma: no cover
        return "unknown"


def append_register_row(register_path, row: dict) -> None:
    """Append one row, writing the header first if the register does not exist yet."""
    register_path.parent.mkdir(parents=True, exist_ok=True)
    exists = register_path.exists()
    with open(register_path, "a", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=REGISTER_COLUMNS)
        if not exists:
            writer.writeheader()
        writer.writerow(row)


# --------------------------------------------------------------------------
# Report
# --------------------------------------------------------------------------


def format_2x2(title: str, m: dict, counts: dict) -> list[str]:
    return [
        f"  {title}",
        "                          storm began in window   no storm in window",
        f"    pop occasion          {m['a']:>21d}   {m['b']:>18d}",
        f"    non-pop occasion      {m['c']:>21d}   {m['d']:>18d}",
        "",
        f"    storm rate given a pop = {m['storm_rate_pop']:.4f}   "
        f"BASE RATE = {m['base_rate']:.4f}   "
        f"ratio = {m['ratio']:.4f}",
        f"      (non-pop comparison occasions alone: {m['nonpop_rate']:.4f})",
        f"    POD = {m['pod']:.4f}   POFD = {m['pofd']:.4f}   PSS = {m['pss']:+.4f}",
        f"    counts: pop events = {counts['n_pop_events']}, "
        f"usable pop occasions = {counts['n_pop_occasions']}, "
        f"non-pop occasions = {counts['n_nonpop_occasions']}, "
        f"storm events = {counts['n_storm_events']}, "
        f"days with an undefined pop flag = {counts['n_days_undefined']}",
    ]


def build_report(
    df: pd.DataFrame,
    scored: dict,
    call: dict,
    wvht_column: str,
    reporting: dict,
    register_row: dict,
) -> str:
    counts = scored["counts"]
    variants = scored["variants"]
    claim = variants["with_claiming"]
    noclaim = variants["without_claiming"]
    call_result = call
    winters = sorted(int(w) for w in df["winter"].unique())

    out: list[str] = []
    out.append("PHASE 7 — HELD-OUT EVALUATION OF THE LOCKED FOLKLORE RULE")
    out.append("=" * 78)
    out.append("")
    out.append(
        "THE PROJECT'S SINGLE AUTHORISED USE OF THE HELD-OUT SET. This run called "
        "load_analysis_data(include_holdout=True) once, authorised by SPEC Section 8 "
        f"(LOCKED, spec version {PROTOCOL_SPEC_VERSION}), sections 8.2 and 8.5. The seal "
        "is now spent and cannot be re-sealed (rule 2.3)."
    )
    out.append("")
    out.append(f"Held-out winters scored ({len(winters)}): {winters}")
    out.append(
        "  Scored ON THEIR OWN. No exploration winter is pooled into any table below; "
        "the exploration numbers quoted at the end are Phase 5a's own, not recomputed "
        "here (SPEC 8.2). The folklore-only winters 2023-2025 are not used (SPEC 8.5)."
    )
    out.append(f"  Winter days in the held-out sample: {len(df)}")
    out.append(f"  Predictor column: {wvht_column}")
    out.append("")

    out.append("THE RULE AS EXECUTED — every value quoted from SPEC 8.2, none recomputed")
    out.append(f"  Pop day        : {wvht_column} >= {POP_THRESHOLD_M:.4f} m (FIXED metre value;")
    out.append("                   the 90th percentile was NOT recomputed on held-out data)")
    out.append(f"  Pop events     : detect_events, bridge = {BRIDGE_DAYS} day, dated by first day")
    out.append(
        f"  Storm day      : swe_gain_in >= {STORM_THRESHOLD_IN:g} in at >= 2 of the 5 "
        f"reporting Wasatch stations ({STORM_COMBINATION})"
    )
    out.append(f"  Storm events   : detect_events, bridge = {BRIDGE_DAYS} day, dated by first day")
    out.append(
        f"  Window         : storm event begins in [pop first day + {LAG_LO}, "
        f"pop first day + {LAG_HI}], inclusive. One window. No lag scan."
    )
    out.append(
        "  Occasions      : contingency_from_flags, grouped by winter — pop occasions are "
        "pop-event first days; non-pop comparison occasions are every other day of the "
        "same held-out winters outside every pop event; both rows require a defined pop "
        "flag and a window fitting inside the same winter (SPEC 8.2, Q25)."
    )
    out.append("  Matching       : BOTH variants reported, neither privileged (SPEC 8.2).")
    out.append("")
    out.append(
        "  Not run, per SPEC 8.1: no model, no MJO/ENSO/PDO feature, no lag scan, no "
        "threshold sweep, no alternative swell variable, no alternative station rule, and "
        "no re-test of the mechanism links F4-F6."
    )
    out.append("")

    out.append("DATA STATE OF THE HELD-OUT WINTERS")
    out.append(
        f"  Days with an undefined pop flag (buoy 51001 not reporting): "
        f"{counts['n_days_undefined']} of {len(df)}. These are on neither row and are "
        "never read as 'no pop' (rule 2.5)."
    )
    out.append(
        f"  Days with all 5 SNOTEL stations reporting: "
        f"{reporting['days_all_five_reporting']} of {reporting['days']}; days with fewer "
        f"than 2 reporting: {reporting['days_fewer_than_two_reporting']}; fewest stations "
        f"reporting on any day: {reporting['min_stations_reporting']}."
    )
    out.append("")

    out.append("RESULT — THE 2x2 UNDER BOTH MATCHING VARIANTS (SPEC 8.3)")
    out.append("")
    out.extend(
        format_2x2(
            "VARIANT 1 — WITH one-to-one claiming (pops in date order claim the earliest "
            "unclaimed storm start in their window)",
            claim,
            counts,
        )
    )
    out.append("")
    out.extend(
        format_2x2(
            "VARIANT 2 — WITHOUT claiming (each pop scored independently; a = pops whose "
            "window contains any storm start)",
            noclaim,
            counts,
        )
    )
    out.append("")
    out.append(
        "  The comparison row (c, d) is identical in both variants by construction: it is "
        "a base-rate reference, not a set of competing forecasts, and is scored without "
        "claiming in both (SPEC 8.2, 8.3). Only `a` differs, and `b` with it."
    )
    out.append(
        "  PSS magnitude is bounded by how rare pops are in this occasion design and is "
        "not comparable across studies; SPEC 8.3 uses its SIGN."
    )
    out.append("")

    out.append("THE VERDICT — SPEC 8.4 APPLIED MECHANICALLY, NOT INTERPRETED")
    out.append(f"  S = (ratio >= {VERDICT_RATIO_BAR:.2f} AND PSS > 0), computed per variant.")
    out.append(
        f"    with claiming   : ratio = {claim['ratio']:.4f}, PSS = {claim['pss']:+.4f}"
        f"  ->  S = {call_result['s']['with_claiming']}"
    )
    out.append(
        f"    without claiming: ratio = {noclaim['ratio']:.4f}, PSS = {noclaim['pss']:+.4f}"
        f"  ->  S = {call_result['s']['without_claiming']}"
    )
    out.append("")
    out.append(f"  S holds for {sum(call_result['s'].values())} of 2 variants.")
    out.append(f"  >>> VERDICT: {call_result['label']} <<<")
    out.append("")
    out.append(f"  {_verdict_gloss(call_result['label'])}")
    out.append("")

    out.append("THE HONEST LIMIT (SPEC 8.4, written before the number was seen)")
    out.append(
        "  Six winters give a DIRECTIONAL answer, not a precise one. This result is "
        "reported as consistent with / inconsistent with the exploration null, and NEVER "
        "as a precise effect size. No confidence interval on this sample would be narrow, "
        "and a ratio near 1.0 cannot be distinguished from a ratio of 1.15. The events "
        "counted here are dozens, and autocorrelated (Q17)."
    )
    out.append(
        f"  SPEC 8.4's advance expectation, scaled from exploration's own rates, was "
        f"roughly 50 usable pop occasions and roughly 90 storm events. Measured: "
        f"{counts['n_pop_occasions']} usable pop occasions and "
        f"{counts['n_storm_events']} storm events."
    )
    out.append("")

    exploration = EXPLORATION_COMPARISON
    out.append("THE EXPLORATION COMPARISON (quoted from Phase 5a, NOT recomputed here)")
    out.append(f"  Configuration: {exploration['config']}")
    out.append(
        "  This is the exact configuration the rule locks, so the comparison is "
        "like-for-like. Phase 5a's headline null (F2) was reported at the 1.0-inch storm "
        "definition; the locked rule uses 0.5-inch any2, and Phase 5a ran that too — "
        "these are its numbers for that cell, read off outputs/phase5a_counting_report.txt."
    )
    out.append("")
    out.append("                              storm rate given a pop   base rate   ratio")
    out.append(
        f"    EXPLORATION, with claiming     {exploration['storm_rate_pop_claim']:.4f}"
        f"               {exploration['base_rate']:.4f}    "
        f"{exploration['storm_rate_pop_claim'] / exploration['base_rate']:.4f}"
    )
    out.append(
        f"    HELD-OUT,    with claiming     {claim['storm_rate_pop']:.4f}"
        f"               {claim['base_rate']:.4f}    {claim['ratio']:.4f}"
    )
    out.append(
        f"    EXPLORATION, without claiming  {exploration['storm_rate_pop_noclaim']:.4f}"
        f"               {exploration['base_rate']:.4f}    "
        f"{exploration['storm_rate_pop_noclaim'] / exploration['base_rate']:.4f}"
    )
    out.append(
        f"    HELD-OUT,    without claiming  {noclaim['storm_rate_pop']:.4f}"
        f"               {noclaim['base_rate']:.4f}    {noclaim['ratio']:.4f}"
    )
    out.append(
        f"  Exploration PSS at this configuration: {exploration['pss']:+.4f} (with "
        f"claiming), over {exploration['n_pop_occasions']} usable pop occasions and "
        f"{exploration['n_storm_events']} storm events across 16 winters."
    )
    out.append("")

    out.append("EXPERIMENT REGISTER (SPEC Section 9, required by SPEC 8.5)")
    out.append(f"  One row appended to outputs/experiments/register.csv — run_id "
               f"{register_row['run_id']}, git_commit {register_row['git_commit']}, "
               f"used_holdout {register_row['used_holdout']}, status "
               f"{register_row['status']}.")
    out.append("")
    out.append(
        "ONE SHOT HONOURED. The rule was run exactly once, against Section 8 as written, "
        "and was not re-run after the result was seen. Section 8 was not edited by this "
        "session; any ambiguity encountered is recorded in DECISIONS.md alongside the "
        "result, not fixed in the frozen text (rule 2.3, SPEC 8.5)."
    )
    return "\n".join(out)


def _verdict_gloss(label: str) -> str:
    if label == "NULL CONFIRMED":
        return (
            "S holds for neither variant. The buoy pop does not raise the odds of a "
            "Wasatch storm 10-18 days later beyond the base rate, on winters no choice in "
            "this study was tuned on. This confirms the Phase 5 null out of sample and is "
            "a complete, successful result (SPEC 8.4, Section 1)."
        )
    if label == "SURPRISING":
        return (
            "S holds for both variants. Recorded as a DISCREPANCY WARRANTING CAUTION and "
            "explicitly NOT as vindication of the folklore (SPEC 8.4): six winters "
            "standing against a flat 16-winter exploration is more likely small-sample "
            "noise than a signal exploration missed. It licenses a fresh, separately "
            "designed study — never a re-run of this one."
        )
    return (
        "S holds for exactly one variant. Reported as INCONCLUSIVE, leaning null, with "
        "both variants' numbers shown, and NOT as skill: if the two matching rules "
        "disagree, the result is a statement about the matching rule, not about the buoy "
        "(SPEC 8.4)."
    )


# --------------------------------------------------------------------------
# Entry point
# --------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Phase 7: open the sealed held-out set and score the locked folklore rule "
            "once (SPEC Section 8, frozen at spec version 0.8). ONE SHOT."
        )
    )
    parser.add_argument("--region", default="utah")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    np.random.seed(args.seed)

    config = load_config(args.region)
    outputs_dir = config["paths"]["outputs"]
    wvht_column = f"buoy_{config['buoys']['primary']}_wvht_mean"
    gain_columns = snow_gain_columns(config)

    df = load_holdout_frame(args.region)
    scored = score_locked_rule(df, gain_columns, wvht_column)
    call = verdict(scored["variants"])
    reporting = station_reporting_counts(df, gain_columns)

    claim = scored["variants"]["with_claiming"]
    noclaim = scored["variants"]["without_claiming"]
    register_row = {
        "run_id": str(uuid.uuid4()),
        "timestamp": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "git_commit": git_commit(),
        "model_name": MODEL_NAME,
        "features": f"buoy_51001_wvht_mean pop >= {POP_THRESHOLD_M:.4f}m",
        "train_seasons": "n/a (no fit)",
        "test_seasons": " ".join(str(w) for w in HELD_OUT_WINTERS),
        "used_holdout": True,
        "target_definition": f"SPEC Section 8 @ spec {PROTOCOL_SPEC_VERSION}",
        "primary_metric": "storm_rate_given_pop_vs_base_rate",
        # SPEC 8.2 privileges neither matching variant, but Section 9 gives one
        # primary_value column. The with-claiming figure is recorded here as the
        # conservative one and BOTH are written into notes, so the register never
        # implies a choice the protocol declined to make.
        "primary_value": round(claim["storm_rate_pop"], 4),
        "baseline_value": round(claim["base_rate"], 4),
        "status": "CONFIRMED",
        "notes": (
            f"Phase 7 one-shot held-out run; verdict {call['label']}. "
            f"With claiming: storm rate {claim['storm_rate_pop']:.4f} vs base rate "
            f"{claim['base_rate']:.4f}, ratio {claim['ratio']:.4f}, PSS {claim['pss']:+.4f}. "
            f"Without claiming: storm rate {noclaim['storm_rate_pop']:.4f} vs base rate "
            f"{noclaim['base_rate']:.4f}, ratio {noclaim['ratio']:.4f}, PSS "
            f"{noclaim['pss']:+.4f}. Storm 0.5in any2, window 10-18d. "
            f"{scored['counts']['n_pop_occasions']} usable pop occasions, "
            f"{scored['counts']['n_storm_events']} storm events. Seal spent, one shot."
        ),
    }

    text = build_report(df, scored, call, wvht_column, reporting, register_row)
    print(text)

    report_path = outputs_dir / "phase7_holdout_result.txt"
    report_path.write_text(text)
    logger.info("Wrote %s", report_path)

    register_path = outputs_dir / "experiments" / "register.csv"
    append_register_row(register_path, register_row)
    logger.info("Appended register row to %s", register_path)


if __name__ == "__main__":
    main()
