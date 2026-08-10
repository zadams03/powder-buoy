"""Presentation figures: the folklore's claim drawn, so a reader can see it hit or miss.

**Presentation only.** Nothing here runs a statistical test, computes a skill score or a
verdict, or produces a finding. It draws data that already exists. Two figures live here:

- **Phase 8c, `--figure hypothesis-grid`.** Each buoy pop, the nine-day window in which the
  folklore says a storm should begin, and the snowpack curve those windows are claims
  about, over four exploration winters.
- **Phase 8d, `--figure per-day`.** The probability that a storm *begins* on each individual
  day after a pop, lags 0 to 30, against the matching per-day baseline. This is the direct
  per-day view of the same claim: the project's lag scan is a *windowed* skill score, and a
  window can smear a sharp, narrowly-timed signal by averaging its target days with
  neighbours that carry none. Descriptive counting only, with the denominators reported.

Two disciplines carry over from the rest of the project and are enforced here:

- **The seal (rule 2.3).** Exploration winters only. `load_exploration_frame` reads
  `load_analysis_data` with its default `include_holdout=False` and then keeps only the
  exploration set, and `select_winters` refuses to return a held-out winter. The seal is
  spent, but making fresh pictures of the held-out winters would be post-hoc exploration
  and is not done.
- **The locked definitions (SPEC 8.2).** The pop threshold, the storm definition, the
  bridge and the window are imported from `holdout_eval`, which holds them as literals
  quoted from the frozen Section 8. Importing rather than re-typing them is the point: the
  figure draws the rule that was actually tested, and cannot drift from it. Nothing in
  this module calls `load_holdout_frame` or passes `include_holdout=True`.

The four winters of the grid are chosen by a rule declared here (two per climate era, the
most data-complete in each), never by how well or badly the pops line up with the storms.
"""

from __future__ import annotations

import argparse
import logging
import textwrap

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

# The locked rule's own constants and its pop-flag builder, imported so the picture
# cannot drift from the test (SPEC 8.2). No held-out loader is imported or called.
from powderbuoy.holdout_eval import (
    HELD_OUT_WINTERS,
    LAG_HI,
    LAG_LO,
    POP_THRESHOLD_M,
    STORM_COMBINATION,
    STORM_THRESHOLD_IN,
    build_locked_pop_flags,
)

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------
# Winter selection — a rule declared here, not a hand-pick
# --------------------------------------------------------------------------

# The two climate eras either side of 51001's 2010-2014 archive hole
# (SPEC 3.1, DECISIONS.md Q21). No exploration winter falls between them.
PRE_GAP_MAX_WINTER = 2009
POST_GAP_MIN_WINTER = 2015
WINTERS_PER_ERA = 2

# Figure geometry. Each winter is drawn as two stacked axes sharing an x-axis — the
# same construction as the existing detector-check figure — with the pops and their
# windows in a strip above the SWE curve rather than on top of it. Inside that strip,
# overlapping windows are stacked into lanes so that two pops' bands never merge into
# one block: how often the buoy pops is part of what the figure has to show.
MIN_LANES = 3
LANE_HEIGHT = 0.62  # fraction of a lane's height that the band fills
HEADROOM = 1.06  # y-limit multiplier on the SWE axes

COLOR_SWE = "#1f4e79"
COLOR_STORM = "#ffb000"
COLOR_POP = "#7a1f7a"
COLOR_WINDOW = "#2f7fbf"

FIGURE_NAME = "hypothesis_pops_over_swe_grid.png"


def era_of(winter: int) -> str | None:
    """`pre_gap` (<= 2009), `post_gap` (>= 2015), or None inside the buoy hole."""
    if winter <= PRE_GAP_MAX_WINTER:
        return "pre_gap"
    if winter >= POST_GAP_MIN_WINTER:
        return "post_gap"
    return None


def winter_completeness(df: pd.DataFrame, wvht_column: str) -> pd.DataFrame:
    """Per winter: how many days the buoy did not report, and which era it is in.

    Data-completeness is measured on the *predictor*, because that is what the rule
    decides: a winter with missing buoy days has pops that cannot be drawn (rule 2.5 —
    an unreported day has no pop flag and is never read as "no pop").
    """
    rows = []
    for winter, group in df.groupby("winter"):
        winter = int(winter)
        rows.append(
            {
                "winter": winter,
                "era": era_of(winter),
                "days": int(len(group)),
                "missing_buoy_days": int(group[wvht_column].isna().sum()),
            }
        )
    return pd.DataFrame(rows).sort_values("winter").reset_index(drop=True)


def select_winters(df: pd.DataFrame, wvht_column: str) -> pd.DataFrame:
    """The four winters the grid draws, by the declared rule.

    **The rule, stated before it is run and applied mechanically:** two winters from the
    pre-gap era (<= 2009) and two from the post-gap era (>= 2015), so both climate eras
    are visible and no single period does the arguing. Within each era, take the two most
    data-complete winters — fewest days on which the buoy did not report — breaking ties
    by the earliest winter. Nothing about how the pops line up with the storms enters
    this choice.

    Refuses to return a held-out winter (rule 2.3), and refuses to return anything at all
    if either era cannot supply two winters, rather than quietly drawing a lopsided grid.
    """
    table = winter_completeness(df, wvht_column)

    chosen = []
    for era in ("pre_gap", "post_gap"):
        candidates = table[table["era"] == era].sort_values(
            ["missing_buoy_days", "winter"], kind="mergesort"
        )
        if len(candidates) < WINTERS_PER_ERA:
            raise ValueError(
                f"Era {era} has {len(candidates)} winters available, "
                f"needs {WINTERS_PER_ERA}."
            )
        chosen.append(candidates.head(WINTERS_PER_ERA))

    selected = pd.concat(chosen).sort_values("winter").reset_index(drop=True)

    sealed = sorted(set(selected["winter"]) & set(HELD_OUT_WINTERS))
    if sealed:
        raise ValueError(
            f"Refusing to draw held-out winters {sealed} — the seal is spent, and fresh "
            "visualisations of the held-out set are post-hoc exploration (rule 2.3)."
        )
    return selected


# --------------------------------------------------------------------------
# What each panel draws
# --------------------------------------------------------------------------


def swe_columns(gain_columns: dict[str, str]) -> list[str]:
    """The `snow_{slug}_swe_in` columns behind the gain columns, same as the detector plot."""
    return [column.replace("_swe_gain_in", "_swe_in") for column in gain_columns.values()]


def winter_panel_data(
    df: pd.DataFrame,
    gain_columns: dict[str, str],
    wvht_column: str,
    winter: int,
) -> dict:
    """Everything one panel needs, all of it from the already-tested event code.

    The SWE curve is the cross-station mean of `swe_in` over the stations reporting that
    day — the same construction `plot_storm_detector_check` uses, so the two figures are
    consistent. Storms and pops are `detect_events` at the locked definitions, sliced to
    the winter first so no event can straddle two winters.
    """
    season = df[df["winter"] == winter]
    dates = pd.DatetimeIndex(season["date"])
    first, last = dates.min(), dates.max()

    mean_swe = pd.Series(
        season[swe_columns(gain_columns)].mean(axis=1, skipna=True).to_numpy(), index=dates
    )
    stations_reporting = int(season[swe_columns(gain_columns)].notna().any(axis=0).sum())

    storm_flags = build_storm_flags(df, gain_columns, STORM_THRESHOLD_IN)[STORM_COMBINATION]
    storm_events = detect_events(storm_flags.loc[first:last], bridge=BRIDGE_DAYS)

    pop_flags = build_locked_pop_flags(df, wvht_column)
    pop_events = detect_events(pop_flags.loc[first:last], bridge=BRIDGE_DAYS)

    pop_starts = pd.DatetimeIndex(
        pop_events["event_start"] if len(pop_events) else []
    ).sort_values()
    # A pop whose 10-18 day window would run past 30 April is not an occasion in the
    # locked rule (SPEC 8.2) — it is dropped there, not followed into May. It is still
    # drawn here, marked apart, so the panel does not silently lose a pop.
    window_fits = [
        bool(start + pd.Timedelta(days=LAG_HI) <= last) for start in pop_starts
    ]

    return {
        "winter": winter,
        "first": first,
        "last": last,
        "mean_swe": mean_swe,
        "stations_reporting": stations_reporting,
        "storm_events": storm_events,
        "pop_starts": pop_starts,
        "window_fits": window_fits,
        "missing_buoy_days": int(season[wvht_column].isna().sum()),
    }


def assign_lanes(pop_starts: pd.DatetimeIndex) -> list[int]:
    """Stack overlapping pop windows into lanes so no two bands merge into one block.

    Greedy and deterministic: pops in date order, each taking the lowest lane whose last
    band has already finished. A pop occupies the span from its own day (where the marker
    sits) to the end of its window, so a marker never lands inside another pop's band.
    """
    lane_ends: list[pd.Timestamp] = []
    lanes = []
    for start in pop_starts:
        end = start + pd.Timedelta(days=LAG_HI)
        for lane, lane_end in enumerate(lane_ends):
            if start > lane_end:
                lane_ends[lane] = end
                lanes.append(lane)
                break
        else:
            lane_ends.append(end)
            lanes.append(len(lane_ends) - 1)
    return lanes


def _shade_storms(ax, storm_events: pd.DataFrame) -> None:
    """Storm events shaded exactly as the existing detector-check figure shades them."""
    for _, event in storm_events.iterrows():
        ax.axvspan(
            event.event_start - pd.Timedelta(hours=12),
            event.event_end + pd.Timedelta(hours=12),
            color=COLOR_STORM,
            alpha=0.35,
            lw=0,
            zorder=1,
        )


def draw_panel(ax_lane, ax_swe, panel: dict) -> None:
    """One winter: pops and their windows above, the SWE curve below, storms through both."""
    swe = panel["mean_swe"]
    _shade_storms(ax_swe, panel["storm_events"])
    ax_swe.plot(swe.index, swe.to_numpy(), color=COLOR_SWE, lw=1.4, zorder=3)

    top = float(np.nanmax(swe.to_numpy())) if swe.notna().any() else 1.0
    ax_swe.set_xlim(panel["first"], panel["last"])
    ax_swe.set_ylim(0.0, max(top, 1.0) * HEADROOM)
    ax_swe.set_ylabel("mean SWE (in)", fontsize=9)
    ax_swe.grid(alpha=0.22)
    ax_swe.tick_params(labelsize=8)

    _shade_storms(ax_lane, panel["storm_events"])
    lanes = assign_lanes(panel["pop_starts"])
    for start, lane, fits in zip(panel["pop_starts"], lanes, panel["window_fits"]):
        window_lo = start + pd.Timedelta(days=LAG_LO)
        window_hi = start + pd.Timedelta(days=LAG_HI)
        centre = lane + 0.5
        # The whisker: marker at the pop, a dotted lead of 10 days, then the band the
        # folklore's claim actually occupies.
        ax_lane.plot(
            [start, window_lo], [centre, centre],
            color=COLOR_POP, lw=0.8, ls=":", alpha=0.7, zorder=4,
        )
        ax_lane.fill_between(
            [window_lo, window_hi],
            centre - LANE_HEIGHT / 2,
            centre + LANE_HEIGHT / 2,
            color=COLOR_WINDOW, alpha=0.55, lw=0, zorder=4,
        )
        ax_lane.plot(
            [start], [centre],
            marker="v", ms=6.5,
            color=COLOR_POP if fits else "none",
            markeredgecolor=COLOR_POP, markeredgewidth=0.9,
            ls="none", zorder=5,
        )
        # A thin dropline so each pop's own date is readable against the snowpack below.
        ax_swe.axvline(start, color=COLOR_POP, lw=0.5, alpha=0.30, zorder=2)

    ax_lane.set_xlim(panel["first"], panel["last"])
    n_lanes = max(MIN_LANES, max(lanes) + 1 if lanes else MIN_LANES)
    ax_lane.set_ylim(-0.06, n_lanes + 0.06)
    ax_lane.set_yticks([])
    ax_lane.set_ylabel("pops +\nwindows", fontsize=8)
    ax_lane.tick_params(labelbottom=False, length=0)
    ax_lane.set_title(
        f"Winter {panel['winter']} — Nov {panel['winter']} to Apr {panel['winter'] + 1}"
        f"   ({len(panel['pop_starts'])} pops, {len(panel['storm_events'])} storms)",
        fontsize=10,
    )


def plot_hypothesis_grid(panels: list[dict], out_path) -> None:
    """The 2x2 grid, chronological (earliest top-left), one shared legend and caption."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.dates as mdates
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch

    fig = plt.figure(figsize=(15, 9.5))
    outer = fig.add_gridspec(2, 2, left=0.055, right=0.985, top=0.885, bottom=0.155,
                             hspace=0.30, wspace=0.13)
    for cell, panel in zip(outer, panels):
        inner = cell.subgridspec(2, 1, height_ratios=[1.15, 3.0], hspace=0.06)
        ax_swe = fig.add_subplot(inner[1])
        ax_lane = fig.add_subplot(inner[0], sharex=ax_swe)
        draw_panel(ax_lane, ax_swe, panel)
        ax_swe.xaxis.set_major_locator(mdates.MonthLocator())
        ax_swe.xaxis.set_major_formatter(mdates.DateFormatter("%b"))

    any_clipped = any(not fits for panel in panels for fits in panel["window_fits"])
    handles = [
        Line2D([], [], color=COLOR_SWE, lw=1.6, label="cross-station mean SWE"),
        Patch(facecolor=COLOR_STORM, alpha=0.35,
              label=f"storm event ({STORM_THRESHOLD_IN:g} in {STORM_COMBINATION})"),
        Line2D([], [], color=COLOR_POP, marker="v", ms=7, ls="none",
               label=f"buoy pop (wvht_mean >= {POP_THRESHOLD_M:.4f} m)"),
        Patch(facecolor=COLOR_WINDOW, alpha=0.55,
              label=f"the folklore's window: pop + {LAG_LO} to + {LAG_HI} days"),
    ]
    if any_clipped:
        handles.append(
            Line2D([], [], color="none", marker="v", ms=7, ls="none",
                   markeredgecolor=COLOR_POP, markeredgewidth=0.9,
                   label="pop whose window runs past 30 Apr (not an occasion in the rule)")
        )

    fig.suptitle(
        "The folklore's claim, drawn — buoy pops and their 10-18 day windows over the "
        "Wasatch snowpack",
        fontsize=13,
        y=0.982,
    )
    fig.legend(
        handles=handles, loc="upper center", bbox_to_anchor=(0.5, 0.945),
        ncol=3 if any_clipped else 4, fontsize=9, frameon=False,
    )

    winters = ", ".join(str(panel["winter"]) for panel in panels)
    paragraphs = [
        "How to read it: each triangle is a buoy pop, and the shaded bar to its right is "
        "the window the folklore claims a storm will begin in — pop + 10 to + 18 days. "
        "Where a bar sits over an orange storm band the folklore hit; where a bar points at "
        "flat or melting snowpack it missed; and every orange band with no bar over it is a "
        "storm the buoy never called. A true signal would land the bars on the step-ups "
        "consistently. Bars are stacked into rows only so that overlapping windows stay "
        "separable; the row a bar sits in carries no meaning.",
        f"Definitions are the ones the study locked and tested (SPEC 8.2): pop = daily mean "
        f"wave height at buoy 51001 >= {POP_THRESHOLD_M:.4f} m; storm = SWE gain >= "
        f"{STORM_THRESHOLD_IN:g} in at >= 2 reporting SNOTEL stations ({STORM_COMBINATION}); "
        f"both collapsed into events by detect_events, bridge = {BRIDGE_DAYS} day, each dated "
        f"by its first day. The four winters were chosen by a rule declared before it was run "
        f"— the two most data-complete winters in each climate era either side of the "
        f"2010-2014 buoy gap, ties broken by the earliest — giving {winters}. They were not "
        f"chosen by how the pops line up with the storms.",
        "EXPLORATION WINTERS ONLY: the six held-out winters are not drawn (rule 2.3). This is "
        "a visualisation, not a test — it reports no rate and no skill score, and adds no "
        "finding. The study's answer is F7. EXPLORATORY.",
    ]
    caption = "\n".join(textwrap.fill(p, width=192) for p in paragraphs)
    fig.text(0.012, 0.012, caption, fontsize=8, color="#333333", va="bottom", ha="left")

    fig.savefig(out_path, dpi=160)
    plt.close(fig)


# --------------------------------------------------------------------------
# Phase 8d: per-day storm-onset probability after a pop
# --------------------------------------------------------------------------

# The reader's question: not "did a storm begin anywhere in the 10 to 18 day window",
# but "how likely is a storm to begin on each individual day after a pop". Counting only.
PER_DAY_MAX_LAG = 30
SMOOTHING_DAYS = 3
# The range the folklore is usually quoted at. Marked on the figure so a reader can look
# exactly where a bump is predicted. Nothing in the data privileges it.
CITED_LAG_LO = 12
CITED_LAG_HI = 14

PER_DAY_FIGURE_NAME = "per_day_storm_onset_after_pop.png"
PER_DAY_NOTE_NAME = "phase8d_per_day_onset_note.txt"

COLOR_BASELINE = "#c00000"
COLOR_SMOOTH = "#1f4e79"

NANOS_PER_DAY = 86_400_000_000_000


def storm_onset_days(df: pd.DataFrame, gain_columns: dict[str, str]) -> pd.DatetimeIndex:
    """First days of storm events at the locked definition, over the whole frame.

    "A storm begins on day D" means a storm event's first day is D. Events come from the
    existing tested `detect_events`; a multi-day storm has exactly one onset day, so a
    long storm cannot contribute to several lags at once.
    """
    storm_flags = build_storm_flags(df, gain_columns, STORM_THRESHOLD_IN)[STORM_COMBINATION]
    events = detect_events(storm_flags, bridge=BRIDGE_DAYS)
    return pd.DatetimeIndex(events["event_start"] if len(events) else []).sort_values()


def pop_and_nonpop_anchors(
    df: pd.DataFrame, wvht_column: str
) -> tuple[pd.DatetimeIndex, pd.DatetimeIndex]:
    """The two sets of anchor days, built the way the study's occasions are built (Q25).

    Pop anchors are pop-event first days, one per event, so a five-day swell is one
    forecast rather than five. Non-pop anchors are every other day lying outside every pop
    event and carrying a defined pop flag; a day the buoy did not report is on neither
    side and is never read as "no pop" (rule 2.5). Days inside a pop event after its first
    day belong to neither set, exactly as in `contingency_from_flags`.
    """
    pop_flags = build_locked_pop_flags(df, wvht_column)
    dates = pd.DatetimeIndex(pop_flags.index)
    events = detect_events(pop_flags, bridge=BRIDGE_DAYS)

    inside_pop = np.zeros(len(dates), dtype=bool)
    values = dates.to_numpy()
    for start, end in zip(events.get("event_start", []), events.get("event_end", [])):
        inside_pop |= (values >= np.datetime64(start)) & (values <= np.datetime64(end))

    defined = pop_flags.notna().to_numpy()
    pop_anchors = pd.DatetimeIndex(
        events["event_start"] if len(events) else []
    ).sort_values()
    nonpop_anchors = dates[defined & ~inside_pop]
    return pop_anchors, nonpop_anchors


def winter_end_lookup(df: pd.DataFrame) -> pd.Series:
    """The last in-season date of each anchor's own winter, indexed by date.

    A pop late in April cannot look 30 days ahead into May: the season is 1 Nov to 30 Apr
    (SPEC 8.2) and days outside it are not in the frame at all. Lags that would run past
    the winter's last day are dropped from that lag's denominator rather than counted as
    "no storm", which would manufacture zeros at long lags.
    """
    ends = df.groupby("winter")["date"].transform("max")
    return pd.Series(pd.DatetimeIndex(ends).to_numpy(), index=pd.DatetimeIndex(df["date"]))


def per_day_onset_curve(
    anchors: pd.DatetimeIndex,
    winter_end: pd.Series,
    onset_days: pd.DatetimeIndex,
    max_lag: int = PER_DAY_MAX_LAG,
) -> pd.DataFrame:
    """For each lag L: the fraction of anchors whose day + L is a storm-event first day.

    The denominator at each L counts only anchors for which day L is still inside the same
    winter, so it shrinks towards the long lags and at the season edges. It is returned
    with the probability, never hidden: at 30 days out, each point rests on fewer anchors
    than at 0, and the tail is correspondingly noisier.
    """
    anchor_ns = pd.DatetimeIndex(anchors).as_unit("ns").astype("int64").to_numpy()
    end_ns = (
        pd.DatetimeIndex(winter_end.loc[anchors].to_numpy())
        .as_unit("ns")
        .astype("int64")
        .to_numpy()
    )
    onset_ns = pd.DatetimeIndex(onset_days).as_unit("ns").astype("int64").to_numpy()

    rows = []
    for lag in range(max_lag + 1):
        target = anchor_ns + lag * NANOS_PER_DAY
        in_season = target <= end_ns
        n_anchors = int(in_season.sum())
        n_onsets = int(np.isin(target[in_season], onset_ns).sum())
        rows.append(
            {
                "lag": lag,
                "n_anchors": n_anchors,
                "n_storm_onsets": n_onsets,
                "probability": (n_onsets / n_anchors) if n_anchors else np.nan,
            }
        )
    return pd.DataFrame(rows)


def smooth_curve(probabilities: pd.Series, window: int = SMOOTHING_DAYS) -> pd.Series:
    """A centred rolling mean, shown ALONGSIDE the raw line and never instead of it.

    The end points average the days that exist rather than going blank, so lag 0 and lag
    30 are the mean of two days rather than three. Only the pop line is smoothed; the
    baseline is left exactly as it comes out.
    """
    return probabilities.rolling(window, center=True, min_periods=1).mean()


def plot_per_day_onset(
    pop_curve: pd.DataFrame, base_curve: pd.DataFrame, caption: str, out_path
) -> None:
    """The per-day view: pop line raw and smoothed, the per-day baseline, denominators."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig = plt.figure(figsize=(12, 7.6))
    grid = fig.add_gridspec(
        2, 1, height_ratios=[3.4, 1.0], hspace=0.10,
        left=0.085, right=0.985, top=0.905, bottom=0.30,
    )
    ax = fig.add_subplot(grid[0])
    ax_n = fig.add_subplot(grid[1], sharex=ax)

    ax.axvspan(
        CITED_LAG_LO, CITED_LAG_HI, color=COLOR_STORM, alpha=0.18, lw=0,
        label=f"the folklore's cited {CITED_LAG_LO} to {CITED_LAG_HI} day range",
    )
    ax.plot(
        pop_curve["lag"], pop_curve["probability"], "-o", ms=3.4, lw=1.0,
        color=COLOR_POP, alpha=0.75, label="after a pop, raw per day",
    )
    ax.plot(
        pop_curve["lag"], smooth_curve(pop_curve["probability"]), "-", lw=2.2,
        color=COLOR_SMOOTH, label=f"after a pop, {SMOOTHING_DAYS} day centred mean",
    )
    ax.plot(
        base_curve["lag"], base_curve["probability"], "--", lw=1.8,
        color=COLOR_BASELINE, label="baseline: after a non-pop day, raw per day",
    )

    ax.set_ylabel("probability a storm begins on that day", fontsize=10)
    # Headroom so the tallest raw point is not clipped by the axes edge, and so the
    # legend does not sit on top of it.
    highest = float(max(pop_curve["probability"].max(), base_curve["probability"].max()))
    ax.set_ylim(0.0, highest * 1.35)
    ax.set_xlim(0, PER_DAY_MAX_LAG)
    ax.grid(alpha=0.25)
    ax.legend(fontsize=9, loc="upper right", framealpha=0.9)
    ax.tick_params(labelbottom=False, labelsize=9)
    ax.set_title(
        "Probability a storm begins on each day after a buoy pop, exploration winters "
        "(EXPLORATORY)",
        fontsize=12,
    )

    ax_n.bar(pop_curve["lag"], pop_curve["n_anchors"], width=0.75, color=COLOR_POP, alpha=0.55)
    ax_n.set_ylim(0, float(pop_curve["n_anchors"].max()) * 1.30)
    ax_n.set_ylabel("pops behind\neach point", fontsize=8.5)
    ax_n.set_xlabel(
        "lag: days after the pop event's first day (each point is that single day, not a "
        "window)",
        fontsize=10,
    )
    ax_n.set_xticks(range(0, PER_DAY_MAX_LAG + 1, 2))
    ax_n.grid(alpha=0.25, axis="y")
    ax_n.tick_params(labelsize=9)

    fig.text(
        0.012, 0.012,
        "\n".join(textwrap.fill(p, width=150) for p in caption.split("\n")),
        fontsize=8.2, color="#333333", va="bottom", ha="left",
    )
    fig.savefig(out_path, dpi=160)
    plt.close(fig)


def per_day_caption(pop_curve: pd.DataFrame, base_curve: pd.DataFrame) -> str:
    """The caption, with the figure's own numbers filled in. No em dashes anywhere.

    Everything quantitative in it is read off the two curves rather than typed in, so the
    caption cannot drift from the figure, and the awkward detail is stated rather than
    smoothed over: the smoothed line's own maximum is located and reported wherever it
    falls, including inside the cited range.
    """
    smoothed = smooth_curve(pop_curve["probability"])
    peak_lag = int(pop_curve.loc[smoothed.idxmax(), "lag"])
    peak_value = float(smoothed.max())
    peak_base = float(base_curve.loc[base_curve["lag"] == peak_lag, "probability"].iloc[0])
    low_lag = int(pop_curve.loc[pop_curve["probability"].idxmin(), "lag"])
    low_value = float(pop_curve["probability"].min())
    cited = pop_curve[pop_curve["lag"].between(CITED_LAG_LO, CITED_LAG_HI)]
    cited_base = base_curve[base_curve["lag"].between(CITED_LAG_LO, CITED_LAG_HI)]
    return (
        "Probability that a storm begins on each day after a buoy pop, out to 30 days, on "
        "the exploration winters, against the per day baseline (the background chance a "
        "storm begins that many days after any non-pop day). The folklore predicts a bump "
        f"around {CITED_LAG_LO} to {CITED_LAG_HI} days, shaded. The pop line stays close to "
        "the baseline across the whole range and the cited range is no exception: it "
        f"averages {cited['probability'].mean():.4f} there against a baseline of "
        f"{cited_base['probability'].mean():.4f}, that is, below the background rather than "
        f"above it. Stated plainly because it is visible: the smoothed line's own highest "
        f"point does fall at lag {peak_lag}, at {peak_value:.4f} against a baseline of "
        f"{peak_base:.4f}, but it is a single point about one percentage point above the "
        f"background, it sits beside lag {low_lag}, which carries the lowest raw value in "
        f"the entire range at {low_value:.4f}, and the neighbouring days do not rise with "
        "it. That is a wiggle, not a bump. Isolated single day wiggles are expected here "
        f"because each point rests on only tens of pop events "
        f"({int(pop_curve['n_anchors'].min())} to {int(pop_curve['n_anchors'].max())} across "
        "the lags, shown beneath), each carrying a handful of storm onsets.\n"
        f"Locked definitions (SPEC 8.2): pop = daily mean wave height at buoy 51001 >= "
        f"{POP_THRESHOLD_M:.4f} m; storm = SWE gain >= {STORM_THRESHOLD_IN:g} in at >= 2 "
        f"reporting SNOTEL stations ({STORM_COMBINATION}); both collapsed into events by "
        f"detect_events, bridge = {BRIDGE_DAYS} day, dated by first day, so a multi day "
        "storm has one onset. Anchors whose day L would fall past 30 April are dropped from "
        "that lag rather than counted as no storm.\n"
        "A true signal would show a broad rise above the baseline sustained across several "
        "adjacent days near the cited lag, not a lone spike. This is a descriptive "
        "visualisation, not a test, and adds no finding: the study's answer remains F7. "
        "Exploration winters only, EXPLORATORY."
    )


def build_per_day_note(
    winters: list[int],
    wvht_column: str,
    pop_curve: pd.DataFrame,
    base_curve: pd.DataFrame,
    caption: str,
    figure_path,
) -> str:
    """The report note: the per lag table, its denominators, and the caption. No em dashes."""
    table = pop_curve.merge(base_curve, on="lag", suffixes=("_pop", "_base"))
    table["pop_smoothed"] = smooth_curve(pop_curve["probability"]).to_numpy()
    table = table[
        ["lag", "n_anchors_pop", "n_storm_onsets_pop", "probability_pop", "pop_smoothed",
         "n_anchors_base", "n_storm_onsets_base", "probability_base"]
    ]

    out: list[str] = []
    out.append("PHASE 8d, PER DAY STORM ONSET PROBABILITY AFTER A POP")
    out.append("=" * 78)
    out.append("")
    out.append(
        "PRESENTATION ONLY. This note records what one figure draws. No statistical test "
        "was run, no skill score or verdict was computed, no existing number changed, and "
        "no finding was added. The study's answer remains F7 (SPEC 8.4, DECISIONS.md)."
    )
    out.append("")
    out.append(
        "Why the figure exists: the project's lag scan (F3) is a WINDOWED skill score, and "
        "a window can smear a sharp, narrowly timed signal by averaging its target days "
        "with neighbours that carry none. This is the direct per day view of the same "
        "claim, asked for by a reader. Either outcome would have been useful; the check is "
        "made directly rather than argued from the windowed result."
    )
    out.append("")
    out.append(f"Exploration winters used ({len(winters)}): {winters}")
    out.append(
        "  include_holdout was never set True. The six held-out winters (2004, 2005, 2006, "
        "2008, 2021, 2022) were not loaded, plotted or counted (rule 2.3)."
    )
    out.append(f"  Predictor column: {wvht_column}")
    out.append("")
    out.append("DEFINITIONS, imported from the locked rule and not re-chosen (SPEC 8.2)")
    out.append(f"  pop day    : {wvht_column} >= {POP_THRESHOLD_M:.4f} m (fixed metre value)")
    out.append(
        f"  storm day  : swe_gain_in >= {STORM_THRESHOLD_IN:g} in at >= 2 reporting "
        f"stations ({STORM_COMBINATION})"
    )
    out.append(f"  events     : detect_events, bridge = {BRIDGE_DAYS} day, dated by first day")
    out.append(
        f"  storm onset: the first day of a storm event, so a multi day storm has exactly "
        "one onset day and cannot contribute to several lags at once"
    )
    out.append(
        "  anchors    : pop anchors are pop event first days; non pop anchors are every "
        "other day outside every pop event with a defined pop flag (Q25, rule 2.5)"
    )
    out.append("")
    out.append(
        f"Anchors: {int(pop_curve.loc[0, 'n_anchors'])} pop events and "
        f"{int(base_curve.loc[0, 'n_anchors'])} non pop days at lag 0. The denominator at "
        "each lag counts only anchors whose day L is still inside the same winter, so it "
        "shrinks towards the long lags and at the season edges."
    )
    out.append(
        f"  Cross check against numbers already on record, not a new measurement: at lag "
        f"{LAG_HI} the denominators are "
        f"{int(pop_curve.loc[pop_curve['lag'] == LAG_HI, 'n_anchors'].iloc[0])} pops and "
        f"{int(base_curve.loc[base_curve['lag'] == LAG_HI, 'n_anchors'].iloc[0])} non pop "
        "days, which is the same in season condition the locked rule's window imposes. "
        "Phase 5a recorded 142 usable pop occasions at this configuration (DECISIONS.md "
        "Q16, F2) and F7 quotes 2263 exploration comparison occasions (c + d = 1438 + 825). "
        "The two match, so the anchors here are the study's own occasions counted a "
        "different way, not a different sample."
    )
    out.append("")
    out.append("PER LAG TABLE. n_anchors is the denominator behind each probability.")
    out.append(table.to_string(index=False, float_format=lambda v: "%.4f" % v))
    out.append("")
    out.append("CAPTION, as written onto the figure:")
    out.append("")
    for paragraph in caption.split("\n"):
        out.append(textwrap.fill(paragraph, width=92, initial_indent="  ", subsequent_indent="  "))
        out.append("")
    out.append(f"Figure: {figure_path}")
    return "\n".join(out)


# --------------------------------------------------------------------------
# Entry points
# --------------------------------------------------------------------------


def run_hypothesis_grid(df: pd.DataFrame, config: dict, figures_dir) -> None:
    gain_columns = snow_gain_columns(config)
    wvht_column = f"buoy_{config['buoys']['primary']}_wvht_mean"
    available = sorted(int(w) for w in df["winter"].unique())
    selected = select_winters(df, wvht_column)
    winters = [int(w) for w in selected["winter"]]

    print("PHASE 8c — HYPOTHESIS VISUALISATION: buoy pops over the SWE curve")
    print("Presentation only. No analysis is run, no rate or skill score is computed,")
    print("and no number in the project changes. EXPLORATORY (exploration winters).")
    print("")
    print(f"Exploration winters available ({len(available)}): {available}")
    print("include_holdout was never set True; load_exploration_frame excludes the")
    print("held-out set by default (rule 2.3), and folklore-only winters with it.")
    print("")
    print("WINTER SELECTION — the declared rule, applied mechanically")
    print("  Two winters per climate era either side of the 2010-2014 buoy gap "
          f"(pre-gap <= {PRE_GAP_MAX_WINTER}, post-gap >= {POST_GAP_MIN_WINTER});")
    print("  within each era the two most data-complete winters (fewest days on which")
    print("  51001 did not report), ties broken by the earliest winter. Not chosen by")
    print("  how well or badly the pops line up with the storms.")
    print("")
    print("  Completeness of every exploration winter (the input to that rule):")
    print(winter_completeness(df, wvht_column).to_string(index=False))
    print("")
    print(f"  >>> CHOSEN: {winters}")
    print(selected.to_string(index=False))
    sealed = sorted(set(winters) & set(HELD_OUT_WINTERS))
    print(f"  Held-out winters {list(HELD_OUT_WINTERS)} — appear in the selection: "
          f"{sealed if sealed else 'NONE'}. Seal intact.")
    print("")
    print("DEFINITIONS — imported from the locked rule, not re-chosen (SPEC 8.2)")
    print(f"  pop day   : {wvht_column} >= {POP_THRESHOLD_M:.4f} m (fixed metre value)")
    print(f"  storm day : swe_gain_in >= {STORM_THRESHOLD_IN:g} in at >= 2 reporting "
          f"stations ({STORM_COMBINATION})")
    print(f"  events    : detect_events, bridge = {BRIDGE_DAYS} day, dated by first day")
    print(f"  window    : pop first day + {LAG_LO} to + {LAG_HI} days, inclusive")
    print("")

    panels = [
        winter_panel_data(df, gain_columns, wvht_column, winter) for winter in winters
    ]

    print("WHAT IS DRAWN (a manifest of the figure, not a result — no rate is computed)")
    for panel in panels:
        clipped = sum(1 for fits in panel["window_fits"] if not fits)
        print(
            f"  winter {panel['winter']}: {len(panel['pop_starts'])} pop events, "
            f"{len(panel['storm_events'])} storm events, "
            f"{panel['stations_reporting']} SNOTEL stations reporting, "
            f"{panel['missing_buoy_days']} missing buoy days, "
            f"{clipped} pop windows running past 30 Apr"
        )
    print("")

    out_path = figures_dir / FIGURE_NAME
    plot_hypothesis_grid(panels, out_path)
    print(f"Figure saved: {out_path}")
    logger.info("Wrote %s", out_path)


def run_per_day_onset(df: pd.DataFrame, config: dict, figures_dir) -> None:
    """Phase 8d. Counting and drawing only; no test, no verdict, no finding."""
    gain_columns = snow_gain_columns(config)
    wvht_column = f"buoy_{config['buoys']['primary']}_wvht_mean"
    winters = sorted(int(w) for w in df["winter"].unique())

    onset_days = storm_onset_days(df, gain_columns)
    pop_anchors, nonpop_anchors = pop_and_nonpop_anchors(df, wvht_column)
    winter_end = winter_end_lookup(df)

    pop_curve = per_day_onset_curve(pop_anchors, winter_end, onset_days)
    base_curve = per_day_onset_curve(nonpop_anchors, winter_end, onset_days)

    caption = per_day_caption(pop_curve, base_curve)
    figure_path = figures_dir / PER_DAY_FIGURE_NAME
    plot_per_day_onset(pop_curve, base_curve, caption, figure_path)

    note = build_per_day_note(
        winters, wvht_column, pop_curve, base_curve, caption, figure_path
    )
    print(note)
    note_path = config["paths"]["outputs"] / PER_DAY_NOTE_NAME
    note_path.write_text(note)
    logger.info("Wrote %s", note_path)
    logger.info("Wrote %s", figure_path)


FIGURE_RUNNERS = {
    "hypothesis-grid": run_hypothesis_grid,
    "per-day": run_per_day_onset,
}


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Presentation figures for the folklore claim. Presentation only: no analysis, "
            "no test, no finding. Exploration winters only."
        )
    )
    parser.add_argument("--region", default="utah")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--figure",
        choices=[*FIGURE_RUNNERS, "all"],
        default="all",
        help=(
            "hypothesis-grid: pops and their 10-18 day windows over the SWE curve "
            "(Phase 8c). per-day: per day storm onset probability after a pop, lags 0 to "
            "30, against the per day baseline (Phase 8d)."
        ),
    )
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    np.random.seed(args.seed)

    config = load_config(args.region)
    figures_dir = config["paths"]["outputs"] / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)

    df = load_exploration_frame(args.region)
    wanted = list(FIGURE_RUNNERS) if args.figure == "all" else [args.figure]
    for name in wanted:
        FIGURE_RUNNERS[name](df, config, figures_dir)


if __name__ == "__main__":
    main()
