"""MJO mechanism check — where the folklore chain breaks (Phase 5b).

Phase 5a falsified the folklore as people state it: a buoy pop does not raise the
odds of a Wasatch storm ~14 days later, at any threshold or lag. This module asks
*why*, by testing the two internal links of the chain the folklore skips over
(SPEC 1.3):

    MJO regime  ->  North Pacific swell at 51001  ->  (weeks later) Utah snow
                 |__ Link A __|                    |______ Link B ______|

The folklore asserts the two ends connect directly. They do not. If Link A is
broken, the buoy never tracked the regime and the folklore fails at step one. If
Link B is broken, even established science is invisible at this sample size.

**Two kinds of looking, kept apart deliberately.**

- The DECLARED TEST is confirmatory and fixed in advance (see the constants
  below): MJO phases 6/7/8 against phases 2/3/4, on days where amplitude > 1.0.
  Phases 1 and 5 are transitional and excluded. The grouping comes from the
  published association between western-US winter precipitation and MJO phases
  6-8 — a physically motivated hypothesis, not a data-driven pick. It carries
  weight precisely because it was chosen before any number was computed.
- The DESCRIPTIVE SWEEP shows all 8 phases individually. It is *description, not
  a test*. No observation from it may be reported as a finding. If one phase
  looks high, that is labelled exploratory and would need a fresh out-of-sample
  test to mean anything. The sweep's purpose is the picture: a flat picture
  across all 8 is strong, honest evidence of no signal.

Everything here is EXPLORATORY regardless (SPEC rule 2.3): exploration winters
only, `include_holdout` never set True, protocol not yet locked. This is a
mechanism check, not another attempt to make the buoy work — correlation and
counting only. No model is built; Stage 3 stays gated.
"""

from __future__ import annotations

import argparse
import logging

import numpy as np
import pandas as pd

from powderbuoy.config import load_config
from powderbuoy.events import (
    BRIDGE_DAYS,
    build_storm_flags,
    detect_events,
    load_exploration_frame,
    snow_gain_columns,
)

logger = logging.getLogger(__name__)

# --- The declared test, fixed BEFORE any run (session prompt Part 2) --------
FAVOURABLE_PHASES = (6, 7, 8)
UNFAVOURABLE_PHASES = (2, 3, 4)
TRANSITIONAL_PHASES = (1, 5)  # excluded from the primary contrast
MIN_AMPLITUDE = 1.0  # below this there is no coherent MJO (SPEC 3.3)

ALL_PHASES = (1, 2, 3, 4, 5, 6, 7, 8)

# Link B is run at two framings, both declared here in advance because the MJO's
# influence on western-US precipitation is lagged and we do not want to pick the
# framing that flatters the result.
SAME_DAY_WINDOW = (0, 0)
LAGGED_WINDOW = (1, 14)

# Storm definition reused unchanged from Phase 5a. 1.0 in `any2` is the primary
# for continuity with F1-F3; 0.5 in is carried as a sensitivity check because the
# 1.0-inch threshold under-counts slow storms (DECISIONS.md Q26).
PRIMARY_STORM_THRESHOLD_IN = 1.0
SENSITIVITY_STORM_THRESHOLD_IN = 0.5
STORM_COMBINATION = "any2"

# --- Reading rules, also declared in advance -------------------------------
# What counts as "the link is present" must be fixed before the numbers exist,
# or the chain read becomes a story written to fit whatever came out.
# Link A is judged on a standardised mean difference (difference in means as a
# fraction of the pooled sd); 0.2 and 0.5 are the conventional small/medium
# marks. Link B is judged on the favourable-vs-unfavourable storm rate ratio.
EFFECT_SIZE_PRESENT = 0.2
EFFECT_SIZE_CLEAR = 0.5
RATE_RATIO_PRESENT = 1.10
RATE_RATIO_CLEAR = 1.25

GROUP_FAVOURABLE = "favourable"
GROUP_UNFAVOURABLE = "unfavourable"
GROUP_EXCLUDED = "excluded"

# --- The BoM RMM method seam (DECISIONS.md Q23), used by the Phase 6 check ---
# BoM computed RMM by the original Wheeler-Hendon (2004) method through
# 2013-12-31 and by a modified method from 2014-01-01. `climate_daily.mjo_method`
# already flags every row; these constants let a winter be assigned to one side.
SEAM_DATE = pd.Timestamp("2014-01-01")  # first day computed by the new method
SEAM_LAST_PRE_WINTER = 2013  # winters labelled <= this are pre-seam
ERA_PRE_SEAM = "pre_seam"
ERA_POST_SEAM = "post_seam"
ERA_POOLED = "pooled"


# --------------------------------------------------------------------------
# Phase grouping
# --------------------------------------------------------------------------


def phase_group(phase, amplitude) -> str:
    """Classify one day into the declared contrast.

    'favourable'   — phase 6, 7 or 8 with amplitude > MIN_AMPLITUDE
    'unfavourable' — phase 2, 3 or 4 with amplitude > MIN_AMPLITUDE
    'excluded'     — everything else: amplitude at or below the threshold (no
                     coherent MJO), a transitional phase (1 or 5), or a missing
                     phase/amplitude.

    An excluded day is not evidence of anything and is never folded into either
    group (SPEC rule 2.5 — a day we cannot classify is counted and reported, not
    quietly assigned).
    """
    if phase is None or amplitude is None:
        return GROUP_EXCLUDED
    if pd.isna(phase) or pd.isna(amplitude):
        return GROUP_EXCLUDED
    if float(amplitude) <= MIN_AMPLITUDE:
        return GROUP_EXCLUDED
    phase = int(phase)
    if phase in FAVOURABLE_PHASES:
        return GROUP_FAVOURABLE
    if phase in UNFAVOURABLE_PHASES:
        return GROUP_UNFAVOURABLE
    return GROUP_EXCLUDED


def phase_groups(df: pd.DataFrame) -> pd.Series:
    """Vectorised `phase_group` over a frame carrying mjo_phase / mjo_amplitude."""
    return pd.Series(
        [
            phase_group(phase, amplitude)
            for phase, amplitude in zip(df["mjo_phase"], df["mjo_amplitude"])
        ],
        index=df.index,
        dtype="object",
    )


def coherent_mjo(df: pd.DataFrame) -> pd.Series:
    """Days with a defined phase and amplitude above the coherence threshold."""
    return (
        df["mjo_phase"].notna()
        & df["mjo_amplitude"].notna()
        & (df["mjo_amplitude"] > MIN_AMPLITUDE)
    )


# --------------------------------------------------------------------------
# The BoM method seam — splitting winters either side of it (Phase 6, Q23)
# --------------------------------------------------------------------------


def seam_era(winter) -> str:
    """Which side of the 2013/2014 BoM RMM method seam a winter sits on.

    A winter is labelled by its starting year and runs Nov of that year to Apr
    of the next (SPEC rule 2.1), so winter 2013 (Nov 2013 - Apr 2014) is the one
    winter that genuinely straddles the seam. The rule declared for this check
    is the simple one: winters <= 2013 are pre-seam, winters >= 2014 are
    post-seam. That is unambiguous for this project because winter 2013 is in no
    split at all — the 51001 archive hole (Q21) removed winters 2009-2014
    entirely — but the straddle is real in principle, so `straddling_winters`
    checks for it against the dates rather than assuming it away.
    """
    return ERA_PRE_SEAM if int(winter) <= SEAM_LAST_PRE_WINTER else ERA_POST_SEAM


def seam_eras(df: pd.DataFrame) -> pd.Series:
    """Vectorised `seam_era` over a frame carrying a `winter` column."""
    return df["winter"].map(seam_era).astype("object")


def straddling_winters(df: pd.DataFrame) -> list[int]:
    """Winters that actually hold days on both sides of the seam date.

    Measured from the dates, not assumed from the labels. A non-empty result
    means the era split below is pooling two calculation methods inside a single
    winter and the check would have to say so.
    """
    dates = pd.DatetimeIndex(df["date"])
    frame = pd.DataFrame({"winter": df["winter"].to_numpy(), "pre": dates < SEAM_DATE})
    by_winter = frame.groupby("winter")["pre"].nunique()
    return sorted(int(w) for w in by_winter[by_winter > 1].index)


def split_at_seam(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Partition a frame into pooled / pre-seam / post-seam sub-frames."""
    eras = seam_eras(df)
    return {
        ERA_POOLED: df,
        ERA_PRE_SEAM: df[eras == ERA_PRE_SEAM].reset_index(drop=True),
        ERA_POST_SEAM: df[eras == ERA_POST_SEAM].reset_index(drop=True),
    }


# --------------------------------------------------------------------------
# Overlap accounting (session prompt Parts 3 and 5)
# --------------------------------------------------------------------------


def overlap_counts(df: pd.DataFrame, wvht_column: str) -> dict:
    """How many winter days actually carry each series, and both together.

    The MJO record ends 2024-02-24 and 51001 has its 2010-2014 hole, so the days
    usable for Link A are a subset of the winter days, and the shrinkage must be
    reported rather than absorbed silently.
    """
    mjo_present = df["mjo_phase"].notna() & df["mjo_amplitude"].notna()
    buoy_present = df[wvht_column].notna()
    coherent = coherent_mjo(df)
    return {
        "n_winter_days": int(len(df)),
        "n_mjo_present": int(mjo_present.sum()),
        "n_buoy_present": int(buoy_present.sum()),
        "n_both_present": int((mjo_present & buoy_present).sum()),
        "n_mjo_coherent": int(coherent.sum()),
        "n_both_present_coherent": int((coherent & buoy_present).sum()),
    }


# --------------------------------------------------------------------------
# Link A — MJO <-> buoy swell
# --------------------------------------------------------------------------


def _pooled_sd(a: np.ndarray, b: np.ndarray) -> float:
    na, nb = len(a), len(b)
    if na + nb - 2 <= 0:
        return float("nan")
    return float(
        np.sqrt(
            ((na - 1) * np.var(a, ddof=1) + (nb - 1) * np.var(b, ddof=1)) / (na + nb - 2)
        )
    )


def link_a_declared_test(df: pd.DataFrame, wvht_column: str) -> dict:
    """The declared contrast on wave height: phases 6-8 vs 2-4, amplitude > 1.

    Days need both a coherent MJO and a reporting buoy. Reports means, medians,
    the difference in means, and that difference as a fraction of the pooled sd
    (a standardised effect size), with the day count behind each group.
    """
    groups = phase_groups(df)
    values = df[wvht_column]
    usable = values.notna()

    favourable = values[(groups == GROUP_FAVOURABLE) & usable].to_numpy(dtype=float)
    unfavourable = values[(groups == GROUP_UNFAVOURABLE) & usable].to_numpy(dtype=float)
    pooled_sd = _pooled_sd(favourable, unfavourable)
    difference = float(favourable.mean() - unfavourable.mean())

    return {
        "n_favourable_days": int(len(favourable)),
        "n_unfavourable_days": int(len(unfavourable)),
        "mean_favourable_m": float(favourable.mean()),
        "mean_unfavourable_m": float(unfavourable.mean()),
        "median_favourable_m": float(np.median(favourable)),
        "median_unfavourable_m": float(np.median(unfavourable)),
        "sd_favourable_m": float(np.std(favourable, ddof=1)),
        "sd_unfavourable_m": float(np.std(unfavourable, ddof=1)),
        "difference_in_means_m": difference,
        "pooled_sd_m": pooled_sd,
        "effect_size_sd": difference / pooled_sd if pooled_sd else float("nan"),
        "all_day_mean_m": float(values.dropna().mean()),
        "n_all_days": int(usable.sum()),
    }


def link_a_by_phase(df: pd.DataFrame, wvht_column: str) -> pd.DataFrame:
    """DESCRIPTIVE SWEEP — swell per individual phase. Context, never a finding."""
    coherent = coherent_mjo(df)
    values = df[wvht_column]
    rows = []
    for phase in ALL_PHASES:
        selection = values[coherent & (df["mjo_phase"] == phase)].dropna()
        rows.append(
            {
                "phase": phase,
                "contrast": (
                    GROUP_FAVOURABLE
                    if phase in FAVOURABLE_PHASES
                    else GROUP_UNFAVOURABLE
                    if phase in UNFAVOURABLE_PHASES
                    else "transitional"
                ),
                "n_days": int(len(selection)),
                "mean_wvht_m": float(selection.mean()) if len(selection) else np.nan,
                "median_wvht_m": float(selection.median()) if len(selection) else np.nan,
            }
        )
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------
# Link B — MJO <-> Utah snow
# --------------------------------------------------------------------------


def storm_start_flags(
    df: pd.DataFrame, gain_columns: dict[str, str], threshold: float, combination: str
) -> tuple[pd.Series, int]:
    """A daily boolean: does a storm EVENT begin on this day?

    Storm days are collapsed into events first (`detect_events`, Phase 5a), so a
    four-day storm is one storm and not four. Returns the series plus the event
    count behind it.
    """
    daily = build_storm_flags(df, gain_columns, threshold)[combination]
    events = detect_events(daily, bridge=BRIDGE_DAYS)
    starts = pd.DatetimeIndex(events["event_start"] if len(events) else [])
    index = pd.DatetimeIndex(df["date"])
    return pd.Series(index.isin(starts), index=index), int(len(events))


def _window_fits(df: pd.DataFrame, lag_hi: int) -> np.ndarray:
    """A day is only an occasion if its whole window stays inside its own winter."""
    dates = pd.DatetimeIndex(df["date"])
    frame = pd.DataFrame({"date": dates, "winter": df["winter"].to_numpy()})
    winter_end = frame.groupby("winter")["date"].transform("max")
    return ((frame["date"] + pd.Timedelta(days=lag_hi)) <= winter_end).to_numpy()


def storm_in_window(
    starts: pd.Series, dates: pd.DatetimeIndex, lag_lo: int, lag_hi: int
) -> np.ndarray:
    """For each date, does a storm event begin in [date+lag_lo, date+lag_hi]?"""
    start_dates = np.sort(dates[starts.to_numpy()].to_numpy().astype("datetime64[ns]"))
    anchors = dates.to_numpy().astype("datetime64[ns]")
    lo = anchors + np.timedelta64(lag_lo, "D")
    hi = anchors + np.timedelta64(lag_hi, "D")
    left = np.searchsorted(start_dates, lo, side="left")
    right = np.searchsorted(start_dates, hi, side="right")
    return right > left


def link_b_declared_test(
    df: pd.DataFrame,
    gain_columns: dict[str, str],
    threshold: float,
    combination: str,
    window: tuple[int, int],
) -> dict:
    """The declared contrast on storms: phases 6-8 vs 2-4, amplitude > 1.

    **The occasion is a day**, and every occasion asks the same question: does a
    storm event begin in the window that follows it? Both the same-day framing
    (window [0, 0] — does a storm begin today?) and the lagged framing (window
    [1, 14]) are declared in advance and both are reported, so neither can be
    chosen after the fact.

    Unlike Phase 5a's pop table (Q25) there is no one-to-one claiming here.
    Nothing is being *issued* as a forecast — this is a rate comparison between
    two sets of days — and both rows are treated identically, so no asymmetry
    favours either group. The two constructions are therefore not directly
    comparable to Phase 5a's numbers, only to each other.

    The base rate is computed over every occasion with a defined MJO phase,
    whatever its group, which is the natural "how often does this happen at all"
    reference (SPEC rule 2.2).
    """
    lag_lo, lag_hi = window
    dates = pd.DatetimeIndex(df["date"])
    starts, n_events = storm_start_flags(df, gain_columns, threshold, combination)
    outcome = storm_in_window(starts, dates, lag_lo, lag_hi)

    fits = _window_fits(df, lag_hi)
    groups = phase_groups(df).to_numpy()
    mjo_defined = (df["mjo_phase"].notna() & df["mjo_amplitude"].notna()).to_numpy()

    favourable = fits & (groups == GROUP_FAVOURABLE)
    unfavourable = fits & (groups == GROUP_UNFAVOURABLE)
    reference = fits & mjo_defined

    a = int((favourable & outcome).sum())
    b = int((favourable & ~outcome).sum())
    c = int((unfavourable & outcome).sum())
    d = int((unfavourable & ~outcome).sum())

    rate_favourable = _ratio(a, a + b)
    rate_unfavourable = _ratio(c, c + d)
    base_rate = _ratio(int((reference & outcome).sum()), int(reference.sum()))
    pod = _ratio(a, a + c)
    pofd = _ratio(b, b + d)

    return {
        "threshold_in": threshold,
        "combination": combination,
        "window": f"{lag_lo}-{lag_hi}",
        "a": a,
        "b": b,
        "c": c,
        "d": d,
        "n_favourable_days": a + b,
        "n_unfavourable_days": c + d,
        "n_reference_days": int(reference.sum()),
        "n_storm_events": n_events,
        "storm_rate_favourable": rate_favourable,
        "storm_rate_unfavourable": rate_unfavourable,
        "base_rate": base_rate,
        "rate_ratio": (
            rate_favourable / rate_unfavourable if rate_unfavourable else float("nan")
        ),
        "pod": pod,
        "pofd": pofd,
        "pss": pod - pofd,
    }


def link_b_by_phase(
    df: pd.DataFrame,
    gain_columns: dict[str, str],
    threshold: float,
    combination: str,
    window: tuple[int, int],
) -> pd.DataFrame:
    """DESCRIPTIVE SWEEP — storm rate per individual phase. Context, never a finding."""
    lag_lo, lag_hi = window
    dates = pd.DatetimeIndex(df["date"])
    starts, _ = storm_start_flags(df, gain_columns, threshold, combination)
    outcome = storm_in_window(starts, dates, lag_lo, lag_hi)
    fits = _window_fits(df, lag_hi)
    coherent = coherent_mjo(df).to_numpy()
    phases = df["mjo_phase"].to_numpy()

    reference = fits & (df["mjo_phase"].notna() & df["mjo_amplitude"].notna()).to_numpy()
    base_rate = _ratio(int((reference & outcome).sum()), int(reference.sum()))

    rows = []
    for phase in ALL_PHASES:
        selection = fits & coherent & (phases == phase)
        n_days = int(selection.sum())
        rows.append(
            {
                "phase": phase,
                "contrast": (
                    GROUP_FAVOURABLE
                    if phase in FAVOURABLE_PHASES
                    else GROUP_UNFAVOURABLE
                    if phase in UNFAVOURABLE_PHASES
                    else "transitional"
                ),
                "n_days": n_days,
                "storm_rate": _ratio(int((selection & outcome).sum()), n_days),
                "base_rate": base_rate,
            }
        )
    return pd.DataFrame(rows)


def _ratio(numerator: float, denominator: float) -> float:
    return float(numerator) / float(denominator) if denominator else float("nan")


# --------------------------------------------------------------------------
# Figures — descriptive sweeps only
# --------------------------------------------------------------------------


def _figure_axes(nrows=1, ncols=1, figsize=(11, 6)):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    return plt, plt.subplots(nrows, ncols, figsize=figsize)


def _phase_colour(contrast: str) -> str:
    return {
        GROUP_FAVOURABLE: "#1f4e79",
        GROUP_UNFAVOURABLE: "#c00000",
    }.get(contrast, "#9a9a9a")


def plot_link_a_sweep(sweep: pd.DataFrame, all_day_mean: float, out_path) -> None:
    plt, (fig, ax) = _figure_axes(figsize=(11, 5.5))
    x = np.arange(len(sweep))
    colours = [_phase_colour(row) for row in sweep["contrast"]]
    ax.bar(x - 0.19, sweep["mean_wvht_m"], width=0.36, color=colours, label="mean")
    ax.bar(
        x + 0.19,
        sweep["median_wvht_m"],
        width=0.36,
        color=colours,
        alpha=0.45,
        label="median",
    )
    ax.axhline(
        all_day_mean,
        color="#000000",
        ls="--",
        lw=1.3,
        label=f"all-day mean = {all_day_mean:.3f} m",
    )
    for xi, (value, n_days) in enumerate(zip(sweep["mean_wvht_m"], sweep["n_days"])):
        ax.annotate(
            f"n={int(n_days)}",
            (xi, value),
            textcoords="offset points",
            xytext=(0, 6),
            ha="center",
            fontsize=8,
            color="#444444",
        )
    ax.set_xticks(x)
    ax.set_xticklabels(
        [f"{int(p)}\n{c[:5]}" for p, c in zip(sweep["phase"], sweep["contrast"])]
    )
    ax.set_xlabel("MJO phase (amplitude > 1) — blue = favourable 6-8, red = unfavourable 2-4")
    ax.set_ylabel("buoy 51001 wvht_mean (m)")
    ax.set_ylim(0, max(sweep["mean_wvht_m"].max(), all_day_mean) * 1.25)
    ax.set_title(
        "Link A, DESCRIPTIVE SWEEP — swell by MJO phase, exploration winters\n"
        "Description, not a test. No phase here may be reported as a finding. (EXPLORATORY)",
        fontsize=10,
    )
    ax.grid(alpha=0.25, axis="y")
    ax.legend(fontsize=8, loc="lower right")
    fig.tight_layout()
    fig.savefig(out_path, dpi=130)
    plt.close(fig)


def plot_link_b_sweep(sweeps: dict[str, pd.DataFrame], out_path) -> None:
    plt, (fig, axes) = _figure_axes(ncols=len(sweeps), figsize=(13, 5.5))
    axes = np.atleast_1d(axes)
    for ax, (title, sweep) in zip(axes, sweeps.items()):
        x = np.arange(len(sweep))
        colours = [_phase_colour(row) for row in sweep["contrast"]]
        ax.bar(x, sweep["storm_rate"], width=0.62, color=colours)
        base_rate = float(sweep["base_rate"].iloc[0])
        ax.axhline(
            base_rate,
            color="#000000",
            ls="--",
            lw=1.3,
            label=f"base rate = {base_rate:.3f}",
        )
        for xi, (value, n_days) in enumerate(zip(sweep["storm_rate"], sweep["n_days"])):
            ax.annotate(
                f"n={int(n_days)}",
                (xi, value),
                textcoords="offset points",
                xytext=(0, 6),
                ha="center",
                fontsize=8,
                color="#444444",
            )
        ax.set_xticks(x)
        ax.set_xticklabels([str(int(p)) for p in sweep["phase"]])
        ax.set_xlabel("MJO phase (amplitude > 1)")
        ax.set_ylabel("P(storm event begins in window)")
        ax.set_ylim(0, min(1.0, max(sweep["storm_rate"].max(), base_rate) * 1.35))
        ax.set_title(title, fontsize=10)
        ax.grid(alpha=0.25, axis="y")
        ax.legend(fontsize=8, loc="lower right")
    fig.suptitle(
        "Link B, DESCRIPTIVE SWEEP — storm rate by MJO phase, exploration winters. "
        "Blue = favourable 6-8, red = unfavourable 2-4.\n"
        "Description, not a test. No phase here may be reported as a finding. (EXPLORATORY)",
        fontsize=10,
    )
    fig.tight_layout()
    fig.savefig(out_path, dpi=130)
    plt.close(fig)


def plot_seam_check(link_a: pd.DataFrame, link_b: pd.DataFrame, out_path) -> None:
    """Phase 6 Part 3 — the declared tests either side of the 2013/2014 seam."""
    plt, (fig, axes) = _figure_axes(ncols=2, figsize=(13, 5.5))
    era_colour = {ERA_POOLED: "#444444", ERA_PRE_SEAM: "#1f4e79", ERA_POST_SEAM: "#c00000"}

    ax = axes[0]
    x = np.arange(len(link_a))
    ax.bar(
        x,
        link_a["effect_size_sd"],
        width=0.6,
        color=[era_colour[era] for era in link_a["era"]],
    )
    ax.axhline(EFFECT_SIZE_PRESENT, color="#000000", ls="--", lw=1.3,
               label=f"declared 'present' bar = {EFFECT_SIZE_PRESENT} sd")
    ax.axhline(EFFECT_SIZE_CLEAR, color="#000000", ls=":", lw=1.1,
               label=f"declared 'clear' bar = {EFFECT_SIZE_CLEAR} sd")
    ax.axhline(0.0, color="#888888", lw=0.9)
    for xi, (value, n_fav, n_unf) in enumerate(
        zip(link_a["effect_size_sd"], link_a["n_favourable_days"], link_a["n_unfavourable_days"])
    ):
        # Value above the bar, day counts inside it — the declared-bar lines run
        # right where a two-line label above a bar would land.
        ax.annotate(f"{value:+.3f}", (xi, value), textcoords="offset points",
                    xytext=(0, -15), ha="center", fontsize=9.5, color="#ffffff")
        ax.annotate(f"n={int(n_fav)}/{int(n_unf)}", (xi, value), textcoords="offset points",
                    xytext=(0, -30), ha="center", fontsize=8, color="#ffffff")
    ax.set_xticks(x)
    ax.set_xticklabels([f"{era}\n({int(n)} winters)" for era, n in
                        zip(link_a["era"], link_a["n_winters"])])
    ax.set_ylabel("Link A effect size (sd)")
    ax.set_ylim(min(0.0, float(link_a["effect_size_sd"].min()) * 1.4), EFFECT_SIZE_CLEAR * 1.35)
    ax.set_title("Link A — swell, favourable minus unfavourable", fontsize=10)
    ax.grid(alpha=0.25, axis="y")
    ax.legend(fontsize=8, loc="upper right")

    ax = axes[1]
    cells = list(dict.fromkeys(zip(link_b["threshold_in"], link_b["window"])))
    width = 0.26
    for offset, era in enumerate((ERA_POOLED, ERA_PRE_SEAM, ERA_POST_SEAM)):
        rows = link_b[link_b["era"] == era].set_index(["threshold_in", "window"])
        values = [float(rows.loc[cell, "rate_ratio"]) for cell in cells]
        ax.bar(np.arange(len(cells)) + (offset - 1) * width, values, width=width,
               color=era_colour[era], label=era)
    ax.axhline(RATE_RATIO_PRESENT, color="#000000", ls="--", lw=1.3,
               label=f"declared 'present' bar = {RATE_RATIO_PRESENT:g}")
    ax.axhline(1.0, color="#888888", lw=0.9)
    ax.set_xticks(np.arange(len(cells)))
    ax.set_xticklabels([f"{t:g} in\n{w}" for t, w in cells])
    ax.set_ylabel("Link B rate ratio (favourable / unfavourable)")
    ax.set_title("Link B — storm rate ratio, all four declared cells", fontsize=10)
    ax.grid(alpha=0.25, axis="y")
    ax.legend(fontsize=8, ncol=2)

    fig.suptitle(
        "Seam-robustness check (Phase 6, Q23) — declared Link A / Link B tests re-run either side of the\n"
        "2013/2014 BoM RMM method seam. Exploration winters only; sub-samples are 10 and 6 winters, so this\n"
        "is a qualitative same-direction check, not a measurement. (EXPLORATORY)",
        fontsize=9,
    )
    fig.tight_layout()
    fig.savefig(out_path, dpi=130)
    plt.close(fig)


# --------------------------------------------------------------------------
# Plain-language reads
# --------------------------------------------------------------------------


def link_a_verdict(result: dict) -> tuple[str, str]:
    """Judged against EFFECT_SIZE_* — declared before the run, not after."""
    effect = result["effect_size_sd"]
    if effect < 0:
        return "contrary", (
            f"swell is {abs(result['difference_in_means_m']):.3f} m LOWER in favourable "
            f"phases ({effect:+.2f} sd) — the opposite of the hypothesised direction"
        )
    if effect >= EFFECT_SIZE_CLEAR:
        return "clearly present", (
            f"swell is {result['difference_in_means_m']:+.3f} m higher in favourable "
            f"phases, {effect:.2f} sd — at or above the declared 'clear' mark of "
            f"{EFFECT_SIZE_CLEAR}"
        )
    if effect >= EFFECT_SIZE_PRESENT:
        return "present but small", (
            f"swell is {result['difference_in_means_m']:+.3f} m higher in favourable "
            f"phases, {effect:.2f} sd — above the declared 'present' mark of "
            f"{EFFECT_SIZE_PRESENT} but below the 'clear' mark of {EFFECT_SIZE_CLEAR}"
        )
    near = " (and it lands close to that mark, so the call is a near thing, not a rout — "
    near += "the bar was set before the run and is not being moved now)"
    return "not detectable", (
        f"swell differs by only {result['difference_in_means_m']:+.3f} m between the "
        f"groups, {effect:.2f} sd — in the hypothesised direction, but below the declared "
        f"'present' mark of {EFFECT_SIZE_PRESENT}"
        + (near if effect >= EFFECT_SIZE_PRESENT - 0.05 else "")
    )


def link_b_verdict(result: dict) -> tuple[str, str]:
    """Judged against RATE_RATIO_* — declared before the run, not after."""
    ratio = result["rate_ratio"]
    favourable = result["storm_rate_favourable"]
    unfavourable = result["storm_rate_unfavourable"]
    base = result["base_rate"]
    detail = (
        f"storm rate {favourable:.4f} in favourable phases against {unfavourable:.4f} in "
        f"unfavourable phases (ratio {ratio:.3f}), beside a base rate of {base:.4f}"
    )
    if ratio < 1.0:
        return "contrary", detail + " — storms are LESS common in favourable phases"
    if ratio >= RATE_RATIO_CLEAR:
        return "clearly present", detail
    if ratio >= RATE_RATIO_PRESENT:
        return "present but small", detail
    return "not detectable", detail


def chain_read(
    link_a: dict,
    link_b_results: list[dict],
    overlap: dict,
    winters: list[int],
) -> list[str]:
    """Part 5 — the deliverable. Where does the chain break?

    The branching logic is the session prompt's, fixed before the numbers
    existed; only which branch is taken is decided by the data.

    Link B's verdict is taken from the LAGGED PRIMARY framing (1-14 days at the
    1.0-inch storm definition), because the lagged framing is the one the
    hypothesised mechanism predicts. The other three declared cells — same-day,
    and both framings at the 0.5-inch sensitivity threshold — are reported
    alongside it as the robustness check, whichever way they fall.
    """
    by_cell = {(r["threshold_in"], r["window"]): r for r in link_b_results}
    same_day = by_cell[(PRIMARY_STORM_THRESHOLD_IN, "0-0")]
    lagged = by_cell[(PRIMARY_STORM_THRESHOLD_IN, "1-14")]

    a_verdict, a_detail = link_a_verdict(link_a)
    b_same_verdict, b_same_detail = link_b_verdict(same_day)
    b_lag_verdict, b_lag_detail = link_b_verdict(lagged)

    a_holds = a_verdict in ("present but small", "clearly present")
    b_holds = b_lag_verdict in ("present but small", "clearly present")

    survives = [
        r
        for r in link_b_results
        if link_b_verdict(r)[0] in ("present but small", "clearly present")
    ]
    robust = len(survives) == len(link_b_results)

    lines = [
        "WHERE DOES THE CHAIN BREAK?",
        "",
        "The folklore asserts that the two ends of a three-part chain connect directly:",
        "MJO regime -> North Pacific swell at Hawaii -> (two weeks later) Utah snow. Phase",
        "5a tested the ends against each other and found nothing at any threshold or lag.",
        "This session tested the two internal links separately.",
        "",
        f"  Link A (MJO <-> buoy swell):  {a_verdict.upper()} — {a_detail}.",
        f"  Link B (MJO <-> Utah snow), same-day:  {b_same_verdict.upper()} — {b_same_detail}.",
        f"  Link B (MJO <-> Utah snow), lagged 1-14 days:  {b_lag_verdict.upper()} — {b_lag_detail}.",
        "",
        "ROBUSTNESS OF LINK B — all four declared cells, not just the flattering ones:",
    ]
    for result in link_b_results:
        verdict, _ = link_b_verdict(result)
        lines.append(
            f"  {result['threshold_in']:g} in {result['combination']}, window "
            f"{result['window']}: favourable {result['storm_rate_favourable']:.4f} vs "
            f"unfavourable {result['storm_rate_unfavourable']:.4f} "
            f"(ratio {result['rate_ratio']:.3f}, base rate {result['base_rate']:.4f}) "
            f"-> {verdict}"
        )
    if robust:
        lines += [
            "",
            "  Link B points the same way in every declared cell. That is the strongest form",
            "  this check can take at this sample size.",
        ]
    else:
        lines += [
            "",
            f"  Link B survives in {len(survives)} of {len(link_b_results)} declared cells. It does NOT survive the",
            "  storm-threshold sensitivity check, and that matters more than it might look:",
            "  DECISIONS.md Q26 found that the 0.5-inch definition has the BETTER claim to being",
            "  'a Wasatch storm' (15.4 events per winter, inside the plausible band) while the",
            "  1.0-inch primary under-counts at 6.9. The cell where Link B looks best is the cell",
            "  built on the weaker storm definition. Read the whole row, not the best entry in it.",
        ]
    lines.append("")

    if a_holds and b_holds:
        lines += [
            "Both links are present, yet the folklore is flat. The regime signal is real but",
            "the buoy is too noisy a proxy to carry it: a single day's wave height at 51001",
            "contains far too little information about MJO state to be worth reading as a",
            "forecast, even though the two are genuinely related in aggregate. The chain does",
            "not break at one joint — it attenuates at both, and what survives to the far end",
            "is nothing a skier could use.",
        ]
    elif not a_holds and b_holds:
        lines += [
            "Link A is the break. The buoy never tracked the regime closely enough to be read as",
            "a proxy for it, so the folklore fails at its first step and everything downstream of",
            "that is moot. This is the cleanest of the possible answers: the chain has a specific",
            "broken joint, and it is the one the folklore actually relies on. Note the shape of",
            "the Link A result, though — the difference is in the hypothesised direction (swell IS",
            "higher in phases 6-8), it is simply far too small to carry a forecast. The physical",
            "story is not wrong; the buoy is just a very weak instrument for reading it.",
        ]
        if not robust:
            lines += [
                "",
                "Link B is the weaker half of that statement and must not be over-read. It clears",
                "the declared bar at the primary storm definition and fails it at the sensitivity",
                "definition, so what this session can honestly say is 'the MJO->snow link is",
                "present at best weakly here', not 'the MJO->snow link is established in this",
                "record'. Under either reading Link A is still the break, because Link A is weaker",
                "than Link B in every framing tested.",
            ]
    elif a_holds and not b_holds:
        lines += [
            "Link B is the break, and it is the more uncomfortable result of the two. The buoy",
            "does track the MJO to some degree, but the MJO's own relationship to Wasatch storms",
            "is not visible at this sample size — and that relationship is established science.",
            "This says more about the record than about the atmosphere: 16 winters is too few to",
            "see a signal we have independent reason to believe exists (Q17). A buoy cannot be a",
            "useful proxy for a regime whose own effect we cannot resolve.",
        ]
    else:
        lines += [
            "Neither link is detectable at this scale. That is the cleanest reading of the",
            "Phase 5a null: the folklore is flat because nothing in the chain is visible here,",
            "not because one particular joint failed. It also means this record cannot arbitrate",
            "the hypothesis — a null on Link B, which is established science, is a statement",
            "about 16 winters of data and not about the physics (Q17).",
        ]

    lines += [
        "",
        "TWO CAVEATS, STATED NOT BURIED.",
        "",
        f"  1. Sample. {len(winters)} exploration winters, and the MJO/buoy overlap is smaller still:",
        f"     {overlap['n_both_present_coherent']} of {overlap['n_winter_days']} winter days carry both a coherent MJO "
        f"(amplitude > {MIN_AMPLITUDE:g})",
        f"     and a reporting buoy. The declared contrast rests on {link_a['n_favourable_days']} favourable and",
        f"     {link_a['n_unfavourable_days']} unfavourable days for Link A, and on {lagged['n_favourable_days']} and "
        f"{lagged['n_unfavourable_days']} for Link B lagged — and the",
        f"     same-day framing rests on only {same_day['a']} and {same_day['c']} storm-start days respectively, a",
        f"     difference of {abs(same_day['a'] - same_day['c'])} events. Those day counts are not independent",
        "     observations: winter weather is autocorrelated and MJO phases persist for days,",
        "     so the effective sample is far smaller than the row counts suggest. This is a",
        "     coarse mechanism check, not a climatology. A weak or absent link here does NOT",
        "     overturn the published MJO/western-US literature; it says the signal is not",
        "     clearly visible at this scale (DECISIONS.md Q17).",
        "",
        "  2. MJO coverage — and a correction to the assumption behind this caveat. The BoM",
        "     RMM series ending 2024-02-24 and 51001's 2010-2014 hole were expected to shrink",
        "     the overlap. Measured, neither of them bites inside the exploration set: the",
        "     exploration winters end 2021-04-30, well inside the MJO record, and the winters",
        "     sitting in the buoy hole (2009-2014) were never part of any split to begin with",
        f"     (Q13/Q21). MJO is present on {overlap['n_mjo_present']} of {overlap['n_winter_days']} winter days — every one — and the buoy on",
        f"     {overlap['n_buoy_present']}, so both are present on {overlap['n_both_present']}. Those two gaps constrain Phase 7 and the",
        "     folklore-only winters, not this check.",
        "",
        "     What DOES shrink the sample here is the declared test's own amplitude condition:",
        f"     {overlap['n_winter_days'] - overlap['n_mjo_coherent']} of {overlap['n_winter_days']} winter days have amplitude at or below "
        f"{MIN_AMPLITUDE:g} (no coherent MJO) and are",
        f"     excluded, leaving {overlap['n_mjo_coherent']} coherent days, of which {overlap['n_both_present_coherent']} also have a reporting buoy —",
        f"     that last figure is the pool the Link A declared test runs on. Link B needs no",
        f"     buoy, so it runs on the {overlap['n_mjo_present']} MJO-present days.",
    ]
    return lines


# --------------------------------------------------------------------------
# Phase 6 Part 3 — seam-robustness check (Q23), exploration data only
# --------------------------------------------------------------------------


def seam_check(
    df: pd.DataFrame, wvht_column: str, gain_columns: dict[str, str]
) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Re-run the declared Link A and Link B tests either side of the seam.

    Nothing is adjusted or corrected. The Phase 5b tests are run again,
    unchanged, on three samples — pooled, pre-seam winters, post-seam winters —
    and reported side by side. The sub-samples are tiny (10 and 6 winters), so
    the only question this can answer is qualitative: do both eras point the same
    weak direction, or do they disagree sharply?

    Exploration winters only. No held-out winter is loaded anywhere here.
    """
    frames = split_at_seam(df)
    link_a_rows = []
    link_b_rows = []
    for era in (ERA_POOLED, ERA_PRE_SEAM, ERA_POST_SEAM):
        frame = frames[era]
        winters = sorted(int(w) for w in frame["winter"].unique())
        result = link_a_declared_test(frame, wvht_column)
        verdict, _ = link_a_verdict(result)
        link_a_rows.append(
            {
                "era": era,
                "n_winters": len(winters),
                "winters": winters,
                "n_favourable_days": result["n_favourable_days"],
                "n_unfavourable_days": result["n_unfavourable_days"],
                "mean_favourable_m": result["mean_favourable_m"],
                "mean_unfavourable_m": result["mean_unfavourable_m"],
                "difference_in_means_m": result["difference_in_means_m"],
                "pooled_sd_m": result["pooled_sd_m"],
                "effect_size_sd": result["effect_size_sd"],
                "verdict": verdict,
            }
        )
        for threshold in (PRIMARY_STORM_THRESHOLD_IN, SENSITIVITY_STORM_THRESHOLD_IN):
            for window in (SAME_DAY_WINDOW, LAGGED_WINDOW):
                cell = link_b_declared_test(
                    frame, gain_columns, threshold, STORM_COMBINATION, window
                )
                b_verdict, _ = link_b_verdict(cell)
                link_b_rows.append({"era": era, "n_winters": len(winters), **cell,
                                    "verdict": b_verdict})

    meta = {
        "winters_pooled": sorted(int(w) for w in df["winter"].unique()),
        "winters_pre_seam": sorted(int(w) for w in frames[ERA_PRE_SEAM]["winter"].unique()),
        "winters_post_seam": sorted(int(w) for w in frames[ERA_POST_SEAM]["winter"].unique()),
        "straddling_winters": straddling_winters(df),
    }
    return pd.DataFrame(link_a_rows), pd.DataFrame(link_b_rows), meta


def seam_check_read(link_a: pd.DataFrame, link_b: pd.DataFrame) -> list[str]:
    """Do both eras point the same way? Stated from the numbers, not asserted."""
    by_era = link_a.set_index("era")
    pre = float(by_era.loc[ERA_PRE_SEAM, "effect_size_sd"])
    post = float(by_era.loc[ERA_POST_SEAM, "effect_size_sd"])
    pooled = float(by_era.loc[ERA_POOLED, "effect_size_sd"])

    same_sign = (pre > 0) == (post > 0)
    both_below_bar = max(pre, post) < EFFECT_SIZE_PRESENT
    verdicts_a = set(link_a["verdict"])

    lines = [
        "DOES THE SEAM CHANGE THE STORY?",
        "",
        f"  Link A: pooled {pooled:+.4f} sd, pre-seam {pre:+.4f} sd, post-seam {post:+.4f} sd "
        f"(declared bar {EFFECT_SIZE_PRESENT}).",
    ]
    if same_sign and both_below_bar:
        lines.append(
            "    Both eras point the same way and both sit below the declared 'present' bar, "
            "so F4's"
        )
        lines.append(
            "    weak-link conclusion is not an artefact of pooling two calculation methods."
        )
    elif same_sign:
        lines.append(
            "    Both eras point the same way (swell higher in favourable phases) and both sit "
            "far below the"
        )
        lines.append(
            f"    declared 'clear' mark of {EFFECT_SIZE_CLEAR} sd, but they straddle the "
            f"'present' mark of {EFFECT_SIZE_PRESENT}:"
        )
        lines.append(
            f"    pre-seam {float(by_era.loc[ERA_PRE_SEAM, 'difference_in_means_m']):+.3f} m and "
            f"post-seam {float(by_era.loc[ERA_POST_SEAM, 'difference_in_means_m']):+.3f} m, against "
            "within-group spreads of"
        )
        lines.append(
            f"    {float(by_era.loc[ERA_PRE_SEAM, 'pooled_sd_m']):.3f} m and "
            f"{float(by_era.loc[ERA_POST_SEAM, 'pooled_sd_m']):.3f} m. Neither era makes wave height a "
            "usable read on MJO state, so the"
        )
        lines.append(
            "    substance of F4 holds in both; the label either side of the bar does not."
        )
    else:
        lines.append(
            "    The two eras point in OPPOSITE directions. The pooled Phase 5b Link A number "
            "must be read as method-blended."
        )
    lines.append(f"    Verdicts across the three samples: {sorted(verdicts_a)}.")
    lines.append("")

    lines.append("  Link B, cell by cell (a cell 'agrees' when both eras fall the same side of "
                 f"the {RATE_RATIO_PRESENT:g} bar):")
    agreements = 0
    cells = list(dict.fromkeys(zip(link_b["threshold_in"], link_b["window"])))
    for threshold, window in cells:
        rows = link_b[
            (link_b["threshold_in"] == threshold) & (link_b["window"] == window)
        ].set_index("era")
        ratios = {era: float(rows.loc[era, "rate_ratio"]) for era in
                  (ERA_POOLED, ERA_PRE_SEAM, ERA_POST_SEAM)}
        clears = {era: ratio >= RATE_RATIO_PRESENT for era, ratio in ratios.items()}
        agree = clears[ERA_PRE_SEAM] == clears[ERA_POST_SEAM]
        agreements += int(agree)
        lines.append(
            f"    {threshold:g} in {STORM_COMBINATION}, window {window}: "
            f"pooled {ratios[ERA_POOLED]:.3f}, pre-seam {ratios[ERA_PRE_SEAM]:.3f}, "
            f"post-seam {ratios[ERA_POST_SEAM]:.3f} -> "
            f"{'same side of the bar' if agree else 'OPPOSITE sides of the bar'}"
        )
    lines.append(
        f"    Eras agree in {agreements} of {len(cells)} declared Link B cells."
    )
    lines.append("")

    # F6's actual claim was an ORDERING — Link A weaker than Link B in every
    # framing tested — so the ordering is what the eras have to be checked on,
    # not just each link separately.
    lines.append("  F6's ordering (Link A weaker than Link B) re-checked in each era, at the "
                 "primary lagged cell:")
    primary_lagged = link_b[
        (link_b["threshold_in"] == PRIMARY_STORM_THRESHOLD_IN) & (link_b["window"] == "1-14")
    ].set_index("era")
    holds = []
    for era in (ERA_POOLED, ERA_PRE_SEAM, ERA_POST_SEAM):
        a_verdict = str(by_era.loc[era, "verdict"])
        b_verdict = str(primary_lagged.loc[era, "verdict"])
        a_present = a_verdict in ("present but small", "clearly present")
        b_present = b_verdict in ("present but small", "clearly present")
        ordering = "holds" if (b_present and not a_present) else (
            "reversed" if (a_present and not b_present) else "neither link clears its bar"
        )
        holds.append(ordering)
        lines.append(
            f"    {era}: Link A '{a_verdict}', Link B '{b_verdict}' -> {ordering}"
        )
    lines.append("")
    lines.append(
        "  Sample sizes are the whole caveat: 10 pre-seam and 6 post-seam winters. This check can "
        "only"
    )
    lines.append(
        "  say whether the two eras point the same weak direction. It cannot measure the seam's "
        "size, and"
    )
    lines.append(
        "  no era-specific number here is a finding — every one is EXPLORATORY context "
        "(rule 2.3)."
    )
    return lines


def run_seam_check(argv_region: str = "utah") -> str:
    """Assemble the Part 3 report. Exploration winters only, by construction."""
    config = load_config(argv_region)
    outputs_dir = config["paths"]["outputs"]
    figures_dir = outputs_dir / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)

    df = load_exploration_frame(argv_region)
    gain_columns = snow_gain_columns(config)
    wvht_column = f"buoy_{config['buoys']['primary']}_wvht_mean"

    link_a, link_b, meta = seam_check(df, wvht_column, gain_columns)

    out: list[str] = []
    out.append("PHASE 6, PART 3 — SEAM-ROBUSTNESS CHECK (DECISIONS.md Q23)")
    out.append(
        "The Phase 5b declared tests, re-run unchanged either side of the BoM RMM method seam "
        "at"
    )
    out.append(
        "2013-12-31 / 2014-01-01. Nothing is adjusted or corrected — this is split-and-compare, "
        "reported not fixed."
    )
    out.append("EXPLORATORY — exploration winters only, and this session locks the protocol "
               "rather than testing it (rule 2.3).")
    out.append("")
    out.append("SEAL CHECK — the winters this check touched:")
    out.append(f"  pooled ({len(meta['winters_pooled'])}):    {meta['winters_pooled']}")
    out.append(f"  pre-seam ({len(meta['winters_pre_seam'])}):  {meta['winters_pre_seam']}")
    out.append(f"  post-seam ({len(meta['winters_post_seam'])}): {meta['winters_post_seam']}")
    out.append(
        "  Held-out winters (2004, 2005, 2006, 2008, 2021, 2022): NOT touched — "
        "include_holdout was never set True."
    )
    out.append(
        f"  Winters holding days on BOTH sides of the seam: {meta['straddling_winters'] or 'none'} "
        "(measured from the dates, not assumed)."
    )
    out.append("")

    out.append("LINK A — swell, favourable (6,7,8) vs unfavourable (2,3,4), amplitude > 1:")
    out.append(
        _table(
            link_a[
                ["era", "n_winters", "n_favourable_days", "n_unfavourable_days",
                 "mean_favourable_m", "mean_unfavourable_m", "difference_in_means_m",
                 "pooled_sd_m", "effect_size_sd", "verdict"]
            ]
        )
    )
    out.append("")
    out.append("LINK B — storm rate by phase group, beside the base rate (rule 2.2):")
    out.append(
        _table(
            link_b[
                ["era", "n_winters", "threshold_in", "window", "n_favourable_days",
                 "n_unfavourable_days", "n_storm_events", "storm_rate_favourable",
                 "storm_rate_unfavourable", "base_rate", "rate_ratio", "pss", "verdict"]
            ]
        )
    )
    out.append("")

    figure_path = figures_dir / "mjo_seam_check.png"
    plot_seam_check(link_a, link_b, figure_path)
    out.append(f"Figure saved: {figure_path}")
    out.append("")
    out.extend(seam_check_read(link_a, link_b))

    text = "\n".join(out)
    report_path = outputs_dir / "phase6_seam_check_report.txt"
    report_path.write_text(text)
    logger.info("Wrote %s", report_path)
    return text


# --------------------------------------------------------------------------
# Report assembly
# --------------------------------------------------------------------------


def _table(frame: pd.DataFrame, floatfmt: str = "%.4f") -> str:
    return frame.to_string(index=False, float_format=lambda v: floatfmt % v)


def _rate_table(results: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(results)[
        [
            "threshold_in",
            "combination",
            "window",
            "n_favourable_days",
            "n_unfavourable_days",
            "n_reference_days",
            "n_storm_events",
            "storm_rate_favourable",
            "storm_rate_unfavourable",
            "base_rate",
            "rate_ratio",
            "pod",
            "pofd",
            "pss",
        ]
    ]


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Phase 5b: MJO mechanism check — Link A and Link B."
    )
    parser.add_argument("--region", default="utah")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--seam-check",
        action="store_true",
        help=(
            "Phase 6 Part 3 only: re-run the declared Link A/B tests either side of the "
            "2013/2014 BoM method seam (DECISIONS.md Q23) and stop."
        ),
    )
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    np.random.seed(args.seed)

    if args.seam_check:
        print(run_seam_check(args.region))
        return

    config = load_config(args.region)
    outputs_dir = config["paths"]["outputs"]
    figures_dir = outputs_dir / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)

    df = load_exploration_frame(args.region)
    gain_columns = snow_gain_columns(config)
    wvht_column = f"buoy_{config['buoys']['primary']}_wvht_mean"
    winters = sorted(int(w) for w in df["winter"].unique())

    out: list[str] = []
    out.append("PHASE 5b — MJO MECHANISM CHECK: WHERE THE FOLKLORE CHAIN BREAKS")
    out.append(
        "Correlation and counting only. NO MODEL IS BUILT — Stage 3 stays gated (SPEC 6.1)."
    )
    out.append("EXPLORATORY — exploration winters only, protocol not yet locked (rule 2.3).")
    out.append("")
    out.append(f"Winters used ({len(winters)}): {winters}")
    out.append("Held-out winters: never loaded — include_holdout was never set True.")
    out.append(
        "Folklore-only winters (2023-2025) have no complete MJO coverage and are excluded, "
        "so every number below rests on the same 16 exploration winters as Phase 5a."
    )
    out.append("")

    # --- The declared test, restated before any number ---
    out.append("THE DECLARED TEST (confirmatory — fixed in advance, carries weight)")
    out.append(
        f"  Primary contrast: MJO phases {FAVOURABLE_PHASES} ('favourable') vs phases "
        f"{UNFAVOURABLE_PHASES} ('unfavourable'),"
    )
    out.append(
        f"  on days where MJO amplitude > {MIN_AMPLITUDE:g} (below that there is no coherent MJO). "
        f"Phases {TRANSITIONAL_PHASES}"
    )
    out.append(
        "  are transitional and excluded from the primary contrast. The grouping is grounded "
        "in the"
    )
    out.append(
        "  published association between western-US winter precipitation and MJO phases 6-8 — "
        "a physically"
    )
    out.append("  motivated hypothesis, not a data-driven pick.")
    out.append(
        f"  Link B framings, BOTH declared now: same-day (window {SAME_DAY_WINDOW[0]}-"
        f"{SAME_DAY_WINDOW[1]}) and lagged (window "
        f"{LAGGED_WINDOW[0]}-{LAGGED_WINDOW[1]} days)."
    )
    out.append(
        f"  Reading rules, also declared now: Link A is 'present' at >= {EFFECT_SIZE_PRESENT} sd and "
        f"'clear' at >= {EFFECT_SIZE_CLEAR} sd;"
    )
    out.append(
        f"  Link B is 'present' at a rate ratio >= {RATE_RATIO_PRESENT:g} and 'clear' at "
        f">= {RATE_RATIO_CLEAR:g}."
    )
    out.append("")
    out.append("THE DESCRIPTIVE SWEEP (exploratory — CONTEXT ONLY)")
    out.append(
        "  All 8 phases are shown individually below and in both figures. This is DESCRIPTION, "
        "NOT A TEST."
    )
    out.append(
        "  No observation from the sweep may be reported as a finding or a conclusion. If a "
        "single phase"
    )
    out.append(
        "  looks high or low, that is exploratory and would require a fresh out-of-sample test "
        "to confirm;"
    )
    out.append(
        "  it is never 'we found signal in phase N'. The sweep generates questions. Only the "
        "declared test"
    )
    out.append("  answers one.")
    out.append("")

    # --- Overlap ---
    overlap = overlap_counts(df, wvht_column)
    out.append("PART 1 — OVERLAP (how many winter days actually carry each series)")
    out.append(f"  Exploration winter days total:                  {overlap['n_winter_days']}")
    out.append(f"  MJO phase + amplitude present:                  {overlap['n_mjo_present']}")
    out.append(f"  Buoy 51001 wvht_mean present:                   {overlap['n_buoy_present']}")
    out.append(f"  BOTH present (the Link A pool):                 {overlap['n_both_present']}")
    out.append(
        f"  MJO coherent (amplitude > {MIN_AMPLITUDE:g}):                    "
        f"{overlap['n_mjo_coherent']}"
    )
    out.append(
        f"  BOTH present AND MJO coherent (Link A test pool): {overlap['n_both_present_coherent']}"
    )
    out.append(
        f"  Link B needs no buoy, so its pool is the {overlap['n_mjo_present']} MJO-present days."
    )
    out.append(
        "  Measured, not assumed: neither the MJO record's 2024-02-24 end nor 51001's "
        "2010-2014 hole costs this"
    )
    out.append(
        "  session any days — the exploration winters end 2021-04-30 and the gap winters were "
        "never in the split"
    )
    out.append(
        "  (Q13/Q21). The shrinkage above is almost entirely the declared test's own "
        "amplitude > 1 condition."
    )
    out.append(
        "  UNTREATED, and flagged rather than absorbed: the BoM RMM method seam at the end of "
        "2013 (Q23) runs"
    )
    out.append(
        "  straight through this pool — 10 of the 16 exploration winters are pre-seam and 6 are "
        "post-seam. Q23"
    )
    out.append(
        "  anticipated the seam going live at the four-model comparison; it is live here too, "
        "the first time"
    )
    out.append(
        "  this project has read MJO phase for analysis. No adjustment is made (that is Phase "
        "6's decision, and"
    )
    out.append(
        "  making one here would be an unrequested protocol change), but every Link A and "
        "Link B number below"
    )
    out.append("  pools two calculation methods and should be read knowing it.")
    out.append("")

    # --- Link A ---
    link_a = link_a_declared_test(df, wvht_column)
    out.append("PART 2 — LINK A: MJO <-> BUOY SWELL")
    out.append("  DECLARED TEST — wave height on favourable vs unfavourable days:")
    out.append(
        _table(
            pd.DataFrame(
                [
                    {
                        "group": "favourable (6,7,8)",
                        "n_days": link_a["n_favourable_days"],
                        "mean_m": link_a["mean_favourable_m"],
                        "median_m": link_a["median_favourable_m"],
                        "sd_m": link_a["sd_favourable_m"],
                    },
                    {
                        "group": "unfavourable (2,3,4)",
                        "n_days": link_a["n_unfavourable_days"],
                        "mean_m": link_a["mean_unfavourable_m"],
                        "median_m": link_a["median_unfavourable_m"],
                        "sd_m": link_a["sd_unfavourable_m"],
                    },
                ]
            )
        )
    )
    out.append(
        f"  Difference in means = {link_a['difference_in_means_m']:+.4f} m "
        f"(favourable minus unfavourable)"
    )
    out.append(
        f"  Pooled sd = {link_a['pooled_sd_m']:.4f} m  ->  effect size = "
        f"{link_a['effect_size_sd']:+.4f} sd"
    )
    out.append(
        f"  Reference: all-day mean over {link_a['n_all_days']} defined winter days = "
        f"{link_a['all_day_mean_m']:.4f} m"
    )
    a_verdict, a_detail = link_a_verdict(link_a)
    out.append(f"  READ: {a_verdict.upper()} — {a_detail}.")
    out.append("")

    sweep_a = link_a_by_phase(df, wvht_column)
    out.append("  DESCRIPTIVE SWEEP (context only, not a finding) — swell by phase:")
    out.append(_table(sweep_a))
    link_a_path = figures_dir / "mjo_link_a_swell_by_phase.png"
    plot_link_a_sweep(sweep_a, link_a["all_day_mean_m"], link_a_path)
    out.append(f"  Sweep plot saved: {link_a_path}")
    spread = float(sweep_a["mean_wvht_m"].max() - sweep_a["mean_wvht_m"].min())
    out.append(
        f"  Sweep shape: per-phase means span {sweep_a['mean_wvht_m'].min():.3f} to "
        f"{sweep_a['mean_wvht_m'].max():.3f} m (spread {spread:.3f} m, "
        f"{spread / link_a['pooled_sd_m']:.2f} sd) around an all-day mean of "
        f"{link_a['all_day_mean_m']:.3f} m."
    )
    out.append(
        "  Any phase standing out here is EXPLORATORY ONLY and would require a fresh "
        "out-of-sample test to confirm."
    )
    out.append("")

    # --- Link B ---
    out.append("PART 3 — LINK B: MJO <-> UTAH SNOW")
    out.append(
        f"  Storm events reuse the Phase 5a detector unchanged: {PRIMARY_STORM_THRESHOLD_IN:g} in "
        f"`{STORM_COMBINATION}` as primary,"
    )
    out.append(
        f"  {SENSITIVITY_STORM_THRESHOLD_IN:g} in `{STORM_COMBINATION}` as a sensitivity check "
        "because the 1.0-inch threshold under-counts"
    )
    out.append("  slow storms (DECISIONS.md Q26). Occasion = one day; outcome = a storm EVENT begins")
    out.append(
        "  in the window. No one-to-one claiming (nothing is being issued as a forecast), and "
        "both rows"
    )
    out.append("  are treated identically — so these numbers are comparable to each other, not to")
    out.append("  Phase 5a's pop tables (Q25).")
    out.append("")

    link_b_results = []
    for threshold in (PRIMARY_STORM_THRESHOLD_IN, SENSITIVITY_STORM_THRESHOLD_IN):
        for window in (SAME_DAY_WINDOW, LAGGED_WINDOW):
            link_b_results.append(
                link_b_declared_test(
                    df, gain_columns, threshold, STORM_COMBINATION, window
                )
            )
    out.append("  DECLARED TEST — storm rate by phase group, beside the base rate (rule 2.2):")
    out.append(_table(_rate_table(link_b_results)))
    out.append(
        "  All four cells are declared and all four are reported. The 0.5-inch rows are the "
        "sensitivity"
    )
    out.append(
        "  check, not a fallback to be quoted only if it agrees — Q26 gives 0.5 in the better "
        "claim to"
    )
    out.append("  being 'a Wasatch storm', so a disagreement between the rows is informative, not noise.")
    out.append("")

    primary_same_day = link_b_results[0]
    primary_lagged = link_b_results[1]
    for label, result in (
        (f"same-day (window {SAME_DAY_WINDOW[0]}-{SAME_DAY_WINDOW[1]})", primary_same_day),
        (f"lagged (window {LAGGED_WINDOW[0]}-{LAGGED_WINDOW[1]})", primary_lagged),
    ):
        verdict, detail = link_b_verdict(result)
        out.append(
            f"  {PRIMARY_STORM_THRESHOLD_IN:g} in {STORM_COMBINATION}, {label} — 2x2 over day-occasions:"
        )
        out.append("                            storm in window   no storm in window")
        out.append(
            f"    favourable (6,7,8)      {result['a']:>14d}   {result['b']:>18d}"
        )
        out.append(
            f"    unfavourable (2,3,4)    {result['c']:>14d}   {result['d']:>18d}"
        )
        out.append(
            f"    storm rate favourable = {result['storm_rate_favourable']:.4f}   "
            f"unfavourable = {result['storm_rate_unfavourable']:.4f}   "
            f"BASE RATE = {result['base_rate']:.4f}"
        )
        out.append(
            f"    POD = {result['pod']:.4f}   POFD = {result['pofd']:.4f}   "
            f"PSS = {result['pss']:.4f}   rate ratio = {result['rate_ratio']:.4f}"
        )
        out.append(
            f"    storm events behind it = {result['n_storm_events']}, reference occasions = "
            f"{result['n_reference_days']}"
        )
        out.append(f"    READ: {verdict.upper()} — {detail}.")
        out.append("")

    sweeps = {}
    for window, title in (
        (SAME_DAY_WINDOW, f"same-day (window {SAME_DAY_WINDOW[0]}-{SAME_DAY_WINDOW[1]})"),
        (LAGGED_WINDOW, f"lagged (window {LAGGED_WINDOW[0]}-{LAGGED_WINDOW[1]} days)"),
    ):
        sweep = link_b_by_phase(
            df, gain_columns, PRIMARY_STORM_THRESHOLD_IN, STORM_COMBINATION, window
        )
        sweeps[title] = sweep
        out.append(
            f"  DESCRIPTIVE SWEEP (context only, not a finding) — storm rate by phase, {title}:"
        )
        out.append(_table(sweep))
        out.append("")
    link_b_path = figures_dir / "mjo_link_b_storms_by_phase.png"
    plot_link_b_sweep(sweeps, link_b_path)
    out.append(f"  Sweep plot saved: {link_b_path}")
    lagged_sweep = sweeps[
        f"lagged (window {LAGGED_WINDOW[0]}-{LAGGED_WINDOW[1]} days)"
    ]
    out.append(
        f"  Sweep shape (lagged): per-phase storm rates span "
        f"{lagged_sweep['storm_rate'].min():.4f} to {lagged_sweep['storm_rate'].max():.4f} "
        f"around a base rate of {float(lagged_sweep['base_rate'].iloc[0]):.4f}; "
        f"{int((lagged_sweep['storm_rate'] > lagged_sweep['base_rate']).sum())} of 8 phases sit above it."
    )
    out.append(
        "  Any phase standing out here is EXPLORATORY ONLY and would require a fresh "
        "out-of-sample test to confirm. It is not a finding and is not reported as one."
    )
    out.append("")

    # --- Part 5: the chain read ---
    out.append("PART 4 — THE CHAIN READ")
    out.append("")
    out.extend(chain_read(link_a, link_b_results, overlap, winters))
    out.append("")
    out.append(
        "DISCIPLINE CHECK: every number above is EXPLORATORY (rule 2.3). The declared test "
        "is the"
    )
    out.append(
        "weight-bearing result; the descriptive sweep is scenery and no observation from it "
        "is stated"
    )
    out.append(
        "as a finding anywhere in this report or in DECISIONS.md. No model was built and "
        "Stage 3 remains gated."
    )

    text = "\n".join(out)
    print(text)
    report_path = outputs_dir / "phase5b_mjo_report.txt"
    report_path.write_text(text)
    logger.info("Wrote %s", report_path)


if __name__ == "__main__":
    main()
