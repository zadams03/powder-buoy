"""Event detection, contingency tables and the lag scan (Phase 5a, SPEC 6.1 Stages 1-2).

Daily weather is autocorrelated: a four-day swell is one swell, not four, and a
three-day storm is one storm, not three. Counting days would let a single
fortnight of weather inflate every number in the table. So every daily boolean
series is first collapsed into discrete *events* (`detect_events`), and all
counting is done on events and on the windows that follow them.

Everything here runs on EXPLORATION winters only. The held-out set stays sealed
(SPEC rule 2.3) — `load_analysis_data` excludes it by default and nothing in
this module passes `include_holdout=True`.

No model is built here. Stage 3 (modelling) is gated on the joint review of
what Stages 1-2 show (SPEC 6.1).
"""

from __future__ import annotations

import argparse
import logging

import numpy as np
import pandas as pd

from powderbuoy.config import load_config, repo_relative
from powderbuoy.seasons import load_analysis_data

logger = logging.getLogger(__name__)

# --- Declared and frozen BEFORE any pop-storm matching (DECISIONS.md Q16) ---
# Storm thresholds are fixed by planning, not calibrated (session prompt Part 2).
STORM_THRESHOLDS_IN = (0.5, 1.0, 1.5)
# Pop definitions are SWEEPS, not single lines. No "best" threshold is chosen
# in this session; the shape of the curve across the sweep is the result.
POP_PERCENTILES = (50, 75, 85, 90, 95)
POP_ZSCORE_SDS = (0.5, 1.0, 1.5, 2.0)

Z_WINDOW_DAYS = 30
Z_MIN_PERIODS = 20
BRIDGE_DAYS = 1

# The folklore window: a storm beginning 10-18 days after the pop's first day.
FOLKLORE_LAG_LO = 10
FOLKLORE_LAG_HI = 18
# The lag scan uses the same 9-day-wide window slid across lags 0-30, so
# lag 14 reproduces the folklore window [10, 18] exactly.
WINDOW_HALF_WIDTH = 4
LAG_SCAN_MAX = 30

STORM_COMBINATIONS = ("any2", "mean")
ANY2_MIN_STATIONS = 2

# Declared in advance for reading the plots — NOT chosen by looking at results.
PRIMARY_STORM_THRESHOLD_IN = 1.0
PRIMARY_STORM_COMBINATION = "any2"
PRIMARY_POP_PERCENTILE = 90
DETECTOR_CHECK_WINTER = 2016

EVENT_COLUMNS = ["event_start", "event_end", "duration_days"]


# --------------------------------------------------------------------------
# Core: collapsing daily flags into events
# --------------------------------------------------------------------------


def detect_events(
    daily_flags: pd.Series,
    bridge: int = 1,
    values: pd.Series | None = None,
) -> pd.DataFrame:
    """Collapse a boolean daily series into events.

    Consecutive True days form one event. A gap of up to `bridge` days between
    True runs is bridged into a single event (one dry day inside a storm does
    not split it). Each event is dated by its FIRST day.

    `daily_flags` must be indexed by date. A missing (NA) day is NOT a
    qualifying day — it cannot start or extend an event — but neither is it
    evidence of a non-event; callers count and report NA days separately rather
    than treating them as False in the analysis (SPEC rule 2.5).

    Gaps in the index are real gaps: two winters separated by a summer are never
    bridged, because bridging is measured in calendar days, not in rows.

    Returns: event_start, event_end, duration_days, and peak_value (the maximum
    of `values` over the event span) when a value series is supplied.
    """
    columns = list(EVENT_COLUMNS)
    if values is not None:
        columns.append("peak_value")

    flags = pd.Series(daily_flags).fillna(False).astype(bool)
    index = pd.DatetimeIndex(pd.Series(flags.index))
    true_dates = index[flags.to_numpy()]

    if len(true_dates) == 0:
        return pd.DataFrame(columns=columns)

    splits = (true_dates[1:] - true_dates[:-1]) > pd.Timedelta(days=bridge + 1)
    group_id = np.concatenate([[0], np.cumsum(splits)])

    rows = []
    for group in np.unique(group_id):
        members = true_dates[group_id == group]
        start, end = members[0], members[-1]
        row = {
            "event_start": start,
            "event_end": end,
            "duration_days": int((end - start).days) + 1,
        }
        if values is not None:
            span = pd.Series(values).loc[start:end]
            row["peak_value"] = float(span.max()) if span.notna().any() else np.nan
        rows.append(row)

    return pd.DataFrame(rows, columns=columns)


# --------------------------------------------------------------------------
# Contingency table over pop / non-pop occasions
# --------------------------------------------------------------------------


def contingency_from_flags(
    pop_flags: pd.Series,
    storm_flags: pd.Series,
    lag_lo: int,
    lag_hi: int,
    bridge: int = 1,
    groups: pd.Series | None = None,
) -> dict:
    """Build the 2x2 contingency table for one configuration (SPEC 6.1).

    Both series are indexed by the same dates. `groups` labels the winter each
    date belongs to; windows never cross a group boundary.

    **The occasion.** The unit counted is an anchor day, and every anchor asks
    the same question: does a storm event *begin* in [anchor + lag_lo,
    anchor + lag_hi]?

    - **Pop occasions** are the first days of pop events — one occasion per
      event, so a five-day swell is one forecast, not five.
    - **Non-pop comparison occasions** are all other days of the same winters
      that lie outside every pop event. This is the base-rate row: same
      seasons, same calendar, same window length, no pop.
    - Days inside a pop event but after its first day belong to neither row.
      They are not fresh pop occasions and they are not pop-free.
    - A day is only an occasion if the pop flag is *defined* there (the buoy
      reported, and any rolling statistic the definition needs exists) and if
      its whole window fits inside the same winter. Both conditions are applied
      identically to both rows, so neither is advantaged.

    **One-to-one claiming (pop row only).** Pops are taken in chronological
    order; each claims the earliest unclaimed storm event starting in its
    window. A claimed storm cannot count for a later pop, so one busy fortnight
    cannot manufacture several hits. Storm starts are unique dates within a
    configuration, so "earliest unclaimed" is unambiguous; the chronological
    order of pops is the tie-break between competing pops.

    The non-pop row is scored WITHOUT claiming: its thousands of overlapping
    windows are a base-rate reference, not a set of competing forecasts. The
    asymmetry runs against the pop row (a pop can lose a storm to an earlier
    pop; a non-pop window never does), so it is conservative with respect to
    finding signal. `storm_rate_pop_noclaim` reports the pop row without
    claiming so the size of that effect is visible.
    """
    index = pd.DatetimeIndex(pd.Series(pop_flags.index)).as_unit("ns")
    pop_flags = pd.Series(pop_flags.to_numpy(), index=index)
    storm_flags = pd.Series(storm_flags.to_numpy(), index=index)
    group_values = (
        np.zeros(len(index), dtype=np.int64)
        if groups is None
        else pd.Series(groups).to_numpy()
    )

    pop_events = detect_events(pop_flags, bridge=bridge)
    storm_events = detect_events(storm_flags, bridge=bridge)

    frame = pd.DataFrame({"date": index, "group": group_values})
    frame["group_end"] = frame.groupby("group")["date"].transform("max")
    window_fits = (frame["date"] + pd.Timedelta(days=lag_hi)) <= frame["group_end"]
    defined = pd.Series(pop_flags.to_numpy()).notna().to_numpy()

    inside_pop = np.zeros(len(frame), dtype=bool)
    dates = frame["date"].to_numpy()
    for start, end in zip(pop_events.get("event_start", []), pop_events.get("event_end", [])):
        inside_pop |= (dates >= np.datetime64(start)) & (dates <= np.datetime64(end))

    valid = window_fits.to_numpy() & defined
    valid_by_date = pd.Series(valid, index=index)

    storm_starts = pd.DatetimeIndex(
        storm_events["event_start"] if len(storm_events) else []
    ).sort_values()
    # Force a single datetime64 unit on both sides of every comparison: the
    # parquet dates arrive as datetime64[s] while pd.Timestamp arithmetic is
    # nanosecond-based, and mixing the two silently finds nothing.
    storm_np = storm_starts.to_numpy().astype("datetime64[ns]")

    def _bounds(anchor: pd.Timestamp) -> tuple[int, int]:
        lo = np.datetime64(anchor + pd.Timedelta(days=lag_lo), "ns")
        hi = np.datetime64(anchor + pd.Timedelta(days=lag_hi), "ns")
        return (
            int(np.searchsorted(storm_np, lo, side="left")),
            int(np.searchsorted(storm_np, hi, side="right")),
        )

    # --- Pop row, one-to-one claiming ---
    pop_starts_all = pd.DatetimeIndex(
        pop_events["event_start"] if len(pop_events) else []
    ).sort_values()
    pop_starts = [d for d in pop_starts_all if bool(valid_by_date.get(d, False))]

    claimed: set = set()
    a = b = 0
    pop_hits_noclaim = 0
    for anchor in pop_starts:
        left, right = _bounds(anchor)
        candidates = [t for t in storm_np[left:right] if t not in claimed]
        if right > left:
            pop_hits_noclaim += 1
        if candidates:
            claimed.add(min(candidates))
            a += 1
        else:
            b += 1

    # --- Non-pop comparison row, no claiming ---
    nonpop_mask = valid & ~inside_pop
    nonpop_dates = index[nonpop_mask]
    c = d = 0
    for anchor in nonpop_dates:
        left, right = _bounds(anchor)
        if right > left:
            c += 1
        else:
            d += 1

    total = a + b + c + d
    return {
        "a": a,
        "b": b,
        "c": c,
        "d": d,
        "n_pop_events": int(len(pop_events)),
        "n_pop_occasions": len(pop_starts),
        "n_nonpop_occasions": int(len(nonpop_dates)),
        "n_storm_events": int(len(storm_events)),
        "n_days_undefined": int((~defined).sum()),
        "storm_rate_pop": _safe_ratio(a, a + b),
        "storm_rate_pop_noclaim": _safe_ratio(pop_hits_noclaim, len(pop_starts)),
        "base_rate": _safe_ratio(a + c, total),
        "nonpop_rate": _safe_ratio(c, c + d),
        "pod": _safe_ratio(a, a + c),
        "pofd": _safe_ratio(b, b + d),
        "pss": _safe_ratio(a, a + c) - _safe_ratio(b, b + d),
    }


def _safe_ratio(numerator: float, denominator: float) -> float:
    return float(numerator) / float(denominator) if denominator else np.nan


# --------------------------------------------------------------------------
# Building the flag series from analysis_daily
# --------------------------------------------------------------------------


def station_slug(name: str) -> str:
    """Match the `snow_{slug}_` prefix analysis_daily was built with (SPEC 5.4)."""
    return name.lower().replace("-", "_").replace(" ", "_")


def load_exploration_frame(region: str = "utah") -> pd.DataFrame:
    """Exploration winters only, sorted by date, `date` as a Timestamp.

    `load_analysis_data` already excludes the held-out set by default
    (SPEC rule 2.3). Folklore-only winters (2023-2025) are dropped here too, so
    every number in this session rests on exactly the same 16 winters.
    """
    df = load_analysis_data(region=region)
    df = df[df["season_set"] == "exploration"].copy()
    df["date"] = pd.to_datetime(df["date"])
    return df.sort_values("date").reset_index(drop=True)


def snow_gain_columns(config: dict) -> dict[str, str]:
    return {
        station["name"]: f"snow_{station_slug(station['name'])}_swe_gain_in"
        for station in config["snow_stations"]
    }


def snow_precip_columns(config: dict) -> dict[str, str]:
    return {
        station["name"]: f"snow_{station_slug(station['name'])}_precip_accum_in"
        for station in config["snow_stations"]
    }


def build_storm_flags(
    df: pd.DataFrame, gain_columns: dict[str, str], threshold: float
) -> dict[str, pd.Series]:
    """Storm-day flags at one SWE threshold: per station, plus both combinations.

    `any2` — at least 2 of the reporting stations gained >= threshold that day.
    `mean` — the cross-station mean gain (over reporting stations) >= threshold.

    A station that is not reporting simply does not contribute; nothing is
    filled in for it (SPEC rule 2.5). Louis Meadow, installed 1999, is absent
    from the 1989-1998 winters for exactly this reason.
    """
    gains = df[list(gain_columns.values())]
    flags: dict[str, pd.Series] = {}
    for name, column in gain_columns.items():
        flags[name] = pd.Series(
            (df[column] >= threshold).to_numpy(), index=df["date"], dtype=bool
        )
    exceed_count = (gains >= threshold).sum(axis=1)
    flags["any2"] = pd.Series(
        (exceed_count >= ANY2_MIN_STATIONS).to_numpy(), index=df["date"], dtype=bool
    )
    flags["mean"] = pd.Series(
        (gains.mean(axis=1, skipna=True) >= threshold).to_numpy(),
        index=df["date"],
        dtype=bool,
    )
    return flags


def trailing_zscore(
    values: pd.Series,
    groups: pd.Series,
    window: int = Z_WINDOW_DAYS,
    min_periods: int = Z_MIN_PERIODS,
) -> pd.Series:
    """z of each day against the TRAILING `window` days, within its own winter.

    The window is shifted by one day, so a day is never compared against a mean
    that contains itself — no look-ahead of any kind.

    The window is computed within each winter rather than across the calendar
    year. Reaching back into October would mean loading days the season loader
    deliberately does not return, and reaching back across a summer would mean
    the risk of a window touching a sealed winter. The cost is that the first
    ~20 days of each winter have no z-score and are excluded from the sample
    entirely (counted and reported, never treated as "no pop").
    """
    frame = pd.DataFrame({"value": values.to_numpy(), "group": groups.to_numpy()})
    shifted = frame.groupby("group")["value"].shift(1)
    grouped = shifted.groupby(frame["group"])
    rolling_mean = grouped.transform(
        lambda s: s.rolling(window, min_periods=min_periods).mean()
    )
    rolling_std = grouped.transform(
        lambda s: s.rolling(window, min_periods=min_periods).std()
    )
    z = (frame["value"] - rolling_mean) / rolling_std.replace(0.0, np.nan)
    return pd.Series(z.to_numpy(), index=values.index)


def build_pop_flags(
    df: pd.DataFrame, wvht_column: str
) -> tuple[dict[str, pd.Series], dict[str, float], dict[str, float]]:
    """Both pop definitions, each swept across its declared threshold set.

    Returns (flags by label, resolved threshold value by label, flagged
    fraction of defined days by label). Flags are a nullable boolean series:
    pd.NA marks a day where the definition is undefined (buoy offline, or no
    trailing window yet), which is never silently read as "no pop".
    """
    wvht = pd.Series(df[wvht_column].to_numpy(), index=df["date"])
    z = trailing_zscore(wvht, pd.Series(df["winter"].to_numpy(), index=df["date"]))

    flags: dict[str, pd.Series] = {}
    resolved: dict[str, float] = {}
    fraction: dict[str, float] = {}

    for percentile in POP_PERCENTILES:
        value = float(np.nanpercentile(wvht.dropna().to_numpy(), percentile))
        label = f"abs_p{percentile}"
        flag = pd.Series(pd.NA, index=wvht.index, dtype="boolean")
        defined = wvht.notna()
        flag[defined] = wvht[defined] >= value
        flags[label] = flag
        resolved[label] = value
        fraction[label] = float(flag[defined].mean())

    for sd in POP_ZSCORE_SDS:
        label = f"z_{sd:g}sd"
        flag = pd.Series(pd.NA, index=z.index, dtype="boolean")
        defined = z.notna()
        flag[defined] = z[defined] >= sd
        flags[label] = flag
        resolved[label] = float(sd)
        fraction[label] = float(flag[defined].mean())

    return flags, resolved, fraction


def pop_label_order() -> list[str]:
    return [f"abs_p{p}" for p in POP_PERCENTILES] + [f"z_{sd:g}sd" for sd in POP_ZSCORE_SDS]


# --------------------------------------------------------------------------
# Part 4 — validating the storm detector
# --------------------------------------------------------------------------


def storm_counts_per_winter(
    df: pd.DataFrame, gain_columns: dict[str, str]
) -> pd.DataFrame:
    """4a — storm events per winter for every threshold and every definition.

    A winter in which a station did not yet exist is not a zero-storm winter —
    it is a winter with no measurement. Louis Meadow was installed in 1999, so
    the 1989-1998 winters are dropped from its row rather than averaged in as
    zeros, which would drag its mean down and mislabel the detector.
    """
    winters = pd.Series(df["winter"].to_numpy(), index=df["date"])
    reporting = {
        name: {
            int(winter)
            for winter, group in df.groupby("winter")[column]
            if group.notna().any()
        }
        for name, column in gain_columns.items()
    }
    all_winters = {int(w) for w in df["winter"].unique()}
    rows = []
    for threshold in STORM_THRESHOLDS_IN:
        flags = build_storm_flags(df, gain_columns, threshold)
        for definition, flag in flags.items():
            measured = reporting.get(definition, all_winters)
            per_winter = []
            for winter, group in flag.groupby(winters):
                if int(winter) not in measured:
                    continue
                events = detect_events(group, bridge=BRIDGE_DAYS)
                per_winter.append(len(events))
            counts = np.array(per_winter, dtype=float)
            rows.append(
                {
                    "threshold_in": threshold,
                    "definition": definition,
                    "winters_measured": len(per_winter),
                    "mean_per_winter": counts.mean(),
                    "min_per_winter": int(counts.min()),
                    "max_per_winter": int(counts.max()),
                    "total_events": int(counts.sum()),
                    "implausible": bool(counts.mean() < 8 or counts.mean() > 50),
                }
            )
    return pd.DataFrame(rows)


def precipitation_coincidence(
    df: pd.DataFrame,
    gain_columns: dict[str, str],
    precip_columns: dict[str, str],
    threshold: float = PRIMARY_STORM_THRESHOLD_IN,
    combination: str = PRIMARY_STORM_COMBINATION,
) -> dict:
    """4c — do SWE-detected storms line up with the precipitation gauges?

    `precip_accum_in` is a running water-year accumulator, so the daily
    increment is its within-winter difference. The pillow and the gauge are
    physically separate instruments at the same sites, so agreement is
    corroboration from an independent sensor, not circularity.
    """
    increments = pd.DataFrame(index=df.index)
    for name, column in precip_columns.items():
        increments[name] = df.groupby("winter")[column].diff()
    positive_stations = (increments > 0).sum(axis=1)
    wet_day = pd.Series(
        (positive_stations >= 2).to_numpy(), index=pd.DatetimeIndex(df["date"])
    )

    flags = build_storm_flags(df, gain_columns, threshold)
    events = detect_events(flags[combination], bridge=BRIDGE_DAYS)

    coincident = 0
    for _, event in events.iterrows():
        window = wet_day.loc[
            event.event_start - pd.Timedelta(days=1) : event.event_end + pd.Timedelta(days=1)
        ]
        if bool(window.any()):
            coincident += 1

    return {
        "threshold_in": threshold,
        "combination": combination,
        "n_events": int(len(events)),
        "n_coincident": coincident,
        "fraction": _safe_ratio(coincident, len(events)),
    }


# --------------------------------------------------------------------------
# Figures
# --------------------------------------------------------------------------


def _figure_axes(nrows=1, ncols=1, figsize=(11, 6)):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    return plt, plt.subplots(nrows, ncols, figsize=figsize)


def plot_storm_detector_check(
    df: pd.DataFrame,
    gain_columns: dict[str, str],
    winter: int,
    threshold: float,
    combination: str,
    out_path,
) -> int:
    """4b — the combined SWE signal for one winter with detected storms marked."""
    plt, (fig, axes) = _figure_axes(nrows=2, figsize=(13, 8))
    season = df[df["winter"] == winter]
    dates = pd.DatetimeIndex(season["date"])
    gains = season[list(gain_columns.values())]
    mean_gain = gains.mean(axis=1, skipna=True)
    mean_swe = season[
        [column.replace("_swe_gain_in", "_swe_in") for column in gain_columns.values()]
    ].mean(axis=1, skipna=True)

    flags = build_storm_flags(df, gain_columns, threshold)[combination]
    events = detect_events(flags.loc[dates.min() : dates.max()], bridge=BRIDGE_DAYS)

    axes[0].plot(dates, mean_swe.to_numpy(), color="#1f4e79", lw=1.6)
    axes[0].set_ylabel("cross-station mean SWE (in)")
    axes[0].set_title(
        f"Storm detector check, winter {winter} — {threshold:g} in, {combination}: "
        f"{len(events)} events marked"
    )
    axes[1].bar(dates, mean_gain.to_numpy(), color="#7f7f7f", width=1.0)
    axes[1].axhline(threshold, color="#c00000", lw=0.9, ls="--", label=f"{threshold:g} in")
    axes[1].set_ylabel("cross-station mean daily SWE gain (in)")
    axes[1].legend(loc="upper left", fontsize=8)

    for _, event in events.iterrows():
        for ax in axes:
            ax.axvspan(
                event.event_start - pd.Timedelta(hours=12),
                event.event_end + pd.Timedelta(hours=12),
                color="#ffb000",
                alpha=0.35,
                lw=0,
            )
    for ax in axes:
        ax.margins(x=0.01)
        ax.grid(alpha=0.25)

    fig.tight_layout()
    fig.savefig(out_path, dpi=130)
    plt.close(fig)
    return int(len(events))


def plot_dose_response(summary: pd.DataFrame, out_path) -> None:
    """The headline plot: storm-likelihood-given-pop against pop threshold."""
    plt, (fig, axes) = _figure_axes(nrows=1, ncols=2, figsize=(13, 5.5))
    panels = [
        ("Absolute (percentile of daily wvht_mean)", [f"abs_p{p}" for p in POP_PERCENTILES],
         [str(p) for p in POP_PERCENTILES], "percentile"),
        ("Z-score (sd over trailing 30-day mean)", [f"z_{sd:g}sd" for sd in POP_ZSCORE_SDS],
         [f"{sd:g}" for sd in POP_ZSCORE_SDS], "sd above trailing mean"),
    ]
    for ax, (title, labels, ticks, xlabel) in zip(axes, panels):
        rows = summary.set_index("pop").loc[labels]
        x = np.arange(len(labels))
        ax.plot(x, rows["storm_rate_pop"].to_numpy(), "o-", color="#1f4e79", lw=2,
                label="storm rate given a pop")
        ax.axhline(
            float(rows["base_rate"].mean()),
            color="#c00000", ls="--", lw=1.4,
            label=f"base rate = {rows['base_rate'].mean():.3f}",
        )
        for xi, (rate, n_events) in enumerate(
            zip(rows["storm_rate_pop"], rows["n_pop_occasions"])
        ):
            ax.annotate(f"n={int(n_events)}", (xi, rate), textcoords="offset points",
                        xytext=(0, 9), ha="center", fontsize=8, color="#444444")
        ax.set_xticks(x)
        ax.set_xticklabels(ticks)
        ax.set_xlabel(f"{xlabel}  (stricter to the right)")
        ax.set_ylabel("P(storm begins 10-18 days later)")
        ax.set_ylim(0, 1.05)
        ax.set_title(title, fontsize=10)
        ax.grid(alpha=0.25)
        ax.legend(loc="lower left", fontsize=8)

    fig.suptitle(
        f"Dose-response, exploration winters only — storm = {PRIMARY_STORM_THRESHOLD_IN:g} in "
        f"{PRIMARY_STORM_COMBINATION}, window 10-18 days (EXPLORATORY)",
        fontsize=11,
    )
    fig.tight_layout()
    fig.savefig(out_path, dpi=130)
    plt.close(fig)


def plot_lag_scan(scan: pd.DataFrame, labels: list[str], title: str, out_path) -> None:
    plt, (fig, ax) = _figure_axes(figsize=(11, 5.5))
    colors = plt.cm.viridis(np.linspace(0.05, 0.85, len(labels)))
    for label, color in zip(labels, colors):
        rows = scan[scan["pop"] == label].sort_values("lag")
        ax.plot(rows["lag"], rows["pss"], "-o", ms=3, lw=1.6, color=color, label=label)
    ax.axhline(0.0, color="#c00000", lw=1.2, ls="--", label="no skill (PSS = 0)")
    ax.axvspan(FOLKLORE_LAG_LO, FOLKLORE_LAG_HI, color="#ffb000", alpha=0.15, lw=0)
    ax.annotate("folklore window", (FOLKLORE_LAG_HI, ax.get_ylim()[1]),
                xytext=(2, -12), textcoords="offset points", fontsize=8, color="#8a6d00")
    ax.set_xlabel("lag (days) — window is [lag-4, lag+4], so lag 14 is the folklore 10-18 window")
    ax.set_ylabel("Peirce skill score")
    ax.set_title(title, fontsize=11)
    ax.grid(alpha=0.25)
    ax.legend(fontsize=8, ncol=2)
    fig.tight_layout()
    fig.savefig(out_path, dpi=130)
    plt.close(fig)


# --------------------------------------------------------------------------
# Report assembly
# --------------------------------------------------------------------------


def _table(frame: pd.DataFrame, floatfmt: str = "%.4f") -> str:
    return frame.to_string(index=False, float_format=lambda v: floatfmt % v)


def build_stage1_summary(
    pop_flags: dict[str, pd.Series],
    df: pd.DataFrame,
    gain_columns: dict[str, str],
    combinations: tuple[str, ...],
    thresholds: tuple[float, ...],
) -> pd.DataFrame:
    winters = pd.Series(df["winter"].to_numpy(), index=pd.DatetimeIndex(df["date"]))
    rows = []
    for threshold in thresholds:
        storm_flags = build_storm_flags(df, gain_columns, threshold)
        for combination in combinations:
            for label in pop_label_order():
                result = contingency_from_flags(
                    pop_flags[label],
                    storm_flags[combination],
                    FOLKLORE_LAG_LO,
                    FOLKLORE_LAG_HI,
                    bridge=BRIDGE_DAYS,
                    groups=winters,
                )
                rows.append(
                    {"pop": label, "storm_in": threshold, "combo": combination, **result}
                )
    return pd.DataFrame(rows)


def run_lag_scan(
    pop_flags: dict[str, pd.Series],
    labels: list[str],
    df: pd.DataFrame,
    gain_columns: dict[str, str],
    threshold: float,
    combination: str,
) -> pd.DataFrame:
    winters = pd.Series(df["winter"].to_numpy(), index=pd.DatetimeIndex(df["date"]))
    storm_flags = build_storm_flags(df, gain_columns, threshold)[combination]
    rows = []
    for label in labels:
        for lag in range(0, LAG_SCAN_MAX + 1):
            lag_lo = max(0, lag - WINDOW_HALF_WIDTH)
            lag_hi = lag + WINDOW_HALF_WIDTH
            result = contingency_from_flags(
                pop_flags[label],
                storm_flags,
                lag_lo,
                lag_hi,
                bridge=BRIDGE_DAYS,
                groups=winters,
            )
            rows.append({"pop": label, "lag": lag, "lag_lo": lag_lo, "lag_hi": lag_hi, **result})
    return pd.DataFrame(rows)


def describe_dose_response(rows: pd.DataFrame, definition: str) -> str:
    """Describe the curve's shape from its own numbers. No verdict — that is the
    joint gate review's call (session prompt Part 5)."""
    rates = rows["storm_rate_pop"].to_numpy()
    base = float(rows["base_rate"].mean())
    span = float(rates.max() - rates.min())
    drift = float(rates[-1] - rates[0])
    above = int((rates > rows["base_rate"].to_numpy()).sum())
    direction = "rises" if drift > 0.02 else ("falls" if drift < -0.02 else "is flat")
    return (
        f"  {definition}: storm rate given a pop runs {rates.min():.3f} to {rates.max():.3f} "
        f"(spread {span:.3f}) against a base rate of {base:.3f}. Loosest to strictest it "
        f"{direction} by {drift:+.3f}, and it sits above the base rate at {above} of "
        f"{len(rates)} swept thresholds. The whole curve lies within "
        f"{max(abs(rates.max() - base), abs(rates.min() - base)):.3f} of the base rate."
    )


def describe_lag_scan(scan: pd.DataFrame, labels: list[str]) -> list[str]:
    """Broad bump, lone spike, or flat? Described from the numbers, no verdict."""
    lines = []
    for label in labels:
        rows = scan[scan["pop"] == label].sort_values("lag")
        pss = rows["pss"].to_numpy()
        positive = pss > 0
        longest = best = 0
        for value in positive:
            best = best + 1 if value else 0
            longest = max(longest, best)
        lines.append(
            f"  {label}: PSS runs {pss.min():+.4f} to {pss.max():+.4f} across lags 0-30; "
            f"{int(positive.sum())} of {len(pss)} lags are above zero, longest run of "
            f"consecutive positive lags = {longest}. Best lag = "
            f"{int(rows['lag'].to_numpy()[np.argmax(pss)])}."
        )
    return lines


def format_2x2(label: str, result: dict) -> str:
    lines = [
        f"  {label}",
        "                          storm followed   no storm followed",
        f"    pop                   {result['a']:>14d}   {result['b']:>17d}",
        f"    no pop (comparison)   {result['c']:>14d}   {result['d']:>17d}",
        f"    storm rate given pop = {result['storm_rate_pop']:.4f}   "
        f"BASE RATE = {result['base_rate']:.4f}   "
        f"(non-pop windows = {result['nonpop_rate']:.4f})",
        f"    storm rate given pop, without one-to-one claiming = "
        f"{result['storm_rate_pop_noclaim']:.4f}",
        f"    POD = {result['pod']:.4f}   POFD = {result['pofd']:.4f}   "
        f"PSS = {result['pss']:.4f}",
        f"    pop events = {result['n_pop_events']} "
        f"(usable occasions {result['n_pop_occasions']}), "
        f"storm events = {result['n_storm_events']}, "
        f"non-pop occasions = {result['n_nonpop_occasions']}",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Phase 5a: event detection, contingency tables, lag scan."
    )
    parser.add_argument("--region", default="utah")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--calibrate-only",
        action="store_true",
        help="Print the frozen threshold calibration and stop, before any matching.",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    np.random.seed(args.seed)

    config = load_config(args.region)
    outputs_dir = config["paths"]["outputs"]
    figures_dir = outputs_dir / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)

    df = load_exploration_frame(args.region)
    gain_columns = snow_gain_columns(config)
    precip_columns = snow_precip_columns(config)
    wvht_column = f"buoy_{config['buoys']['primary']}_wvht_mean"
    winters_used = sorted(int(w) for w in df["winter"].unique())

    out: list[str] = []
    out.append("PHASE 5a — EVENT DETECTION, CONTINGENCY TABLES, LAG SCAN")
    out.append("Stages 1-2 of SPEC 6.1. Stage 3 (modelling) is GATED and not run here.")
    out.append("EXPLORATORY — exploration winters only, protocol not yet locked (rule 2.3).")
    out.append("")
    out.append(f"Winters used ({len(winters_used)}): {winters_used}")
    out.append("Held-out winters: never loaded — include_holdout was never set True.")
    out.append(
        "Folklore-only winters (2023-2025) were available for the storm side but were "
        "NOT used, so every number below rests on the same 16 exploration winters."
    )
    out.append(f"Winter days in sample: {len(df)}   predictor: {wvht_column}")
    out.append("")

    # --- Part 2: calibration, frozen before any matching ---
    pop_flags, resolved, fraction = build_pop_flags(df, wvht_column)
    wvht = df[wvht_column]
    out.append("PART 2 — THRESHOLD CALIBRATION (marginal distributions only)")
    out.append(
        f"  wvht_mean over exploration winter days: n={int(wvht.notna().sum())} defined, "
        f"{int(wvht.isna().sum())} null (buoy offline), "
        f"mean={wvht.mean():.3f} m, sd={wvht.std():.3f} m"
    )
    calibration = pd.DataFrame(
        [
            {
                "pop": label,
                "definition": "absolute percentile" if label.startswith("abs") else "z-score sd",
                "threshold": resolved[label],
                "units": "m" if label.startswith("abs") else "sd",
                "flagged_frac_of_defined_days": fraction[label],
                "defined_days": int(pop_flags[label].notna().sum()),
            }
            for label in pop_label_order()
        ]
    )
    out.append(_table(calibration))
    out.append(
        f"  Storm thresholds (fixed by planning, not calibrated): "
        f"{', '.join(f'{t:g} in' for t in STORM_THRESHOLDS_IN)}"
    )
    out.append("")

    if args.calibrate_only:
        text = "\n".join(out)
        print(text)
        return

    # --- Part 3: event counts ---
    out.append("PART 3 — EVENT DETECTION (bridge = 1 day, event dated by its first day)")
    pop_event_rows = []
    for label in pop_label_order():
        events = detect_events(pop_flags[label], bridge=BRIDGE_DAYS, values=pd.Series(
            wvht.to_numpy(), index=pd.DatetimeIndex(df["date"])
        ))
        pop_event_rows.append(
            {
                "pop": label,
                "threshold": resolved[label],
                "n_events": len(events),
                "mean_duration_days": events["duration_days"].mean() if len(events) else np.nan,
                "events_per_winter": len(events) / len(winters_used),
            }
        )
    out.append(_table(pd.DataFrame(pop_event_rows)))
    out.append(
        "  The strict end of each sweep has few events — a noisier storm-likelihood "
        "estimate there (DECISIONS.md Q17). Surfaced, not hidden."
    )
    out.append("")

    # --- Part 4: detector validation ---
    out.append("PART 4 — STORM DETECTOR VALIDATION")
    counts = storm_counts_per_winter(df, gain_columns)
    out.append("4a — storm events per winter (plausible range roughly 15-30):")
    out.append(_table(counts, floatfmt="%.2f"))
    flagged = counts[counts["implausible"]]
    if len(flagged):
        out.append("  FLAGGED as implausible (mean per winter < 8 or > 50) — reported, not fixed:")
        for _, row in flagged.iterrows():
            out.append(
                f"    {row['threshold_in']:g} in / {row['definition']}: "
                f"mean {row['mean_per_winter']:.1f} events per winter"
            )
    else:
        out.append("  No configuration flagged as implausible.")
    out.append("")

    detector_path = figures_dir / "storm_detector_check_2016.png"
    n_marked = plot_storm_detector_check(
        df, gain_columns, DETECTOR_CHECK_WINTER,
        PRIMARY_STORM_THRESHOLD_IN, PRIMARY_STORM_COMBINATION, detector_path,
    )
    out.append(
        f"4b — eyeball plot saved: {repo_relative(detector_path)} "
        f"(winter {DETECTOR_CHECK_WINTER}, {PRIMARY_STORM_THRESHOLD_IN:g} in "
        f"{PRIMARY_STORM_COMBINATION}, {n_marked} events marked)"
    )
    out.append(
        "  Eyeball result: every one of the marked bands sits on a visible step-up in the "
        "cross-station mean SWE curve — no mark lands on flat or melting snow, so the "
        "detector is not firing on noise. The converse is not clean: at least one clear "
        "multi-day step-up (early Feb 2017, roughly 22.4 to 25.2 in over about a week) "
        "carries no mark, because it accumulated at 0.4-0.75 in/day and never reached "
        "1 inch at two stations on any single day. The 1-inch threshold therefore misses "
        "slow-accumulation storms, which is the same finding 4a flags from the counts. "
        "Reported, not fixed — the threshold choice is Phase 6's (Q6)."
    )
    out.append("")

    coincidence = precipitation_coincidence(df, gain_columns, precip_columns)
    out.append(
        f"4c — precipitation cross-check ({coincidence['threshold_in']:g} in "
        f"{coincidence['combination']}): {coincidence['n_coincident']} of "
        f"{coincidence['n_events']} SWE-detected storm events coincide (within +/-1 day) "
        f"with a positive daily precipitation increment at 2 or more stations = "
        f"{coincidence['fraction']:.4f}"
    )
    out.append(
        "  The precipitation gauge is a physically separate instrument from the SWE "
        "pillow at the same sites, so this is independent corroboration, not circularity."
    )
    out.append("")

    # --- Part 5: Stage 1 ---
    summary = build_stage1_summary(
        pop_flags, df, gain_columns, STORM_COMBINATIONS, STORM_THRESHOLDS_IN
    )
    out.append("PART 5 — STAGE 1: CONTINGENCY TABLES (window 10-18 days after the pop)")
    out.append(
        "  Occasion = one anchor day. Pop occasions are pop-event FIRST days "
        "(one per event). Non-pop comparison occasions are all other days of the same "
        "exploration winters lying outside every pop event. Both rows require a defined "
        "pop flag and a window that fits inside the same winter."
    )
    out.append(
        "  One-to-one: pops in date order each claim the earliest unclaimed storm in "
        "their window; a claimed storm cannot count again. The non-pop base-rate row is "
        "not claimed against, which is conservative for the pop row."
    )
    out.append("")
    out.append(
        f"  Full 2x2 tables at the primary storm definition "
        f"({PRIMARY_STORM_THRESHOLD_IN:g} in, {PRIMARY_STORM_COMBINATION}):"
    )
    primary = summary[
        (summary["storm_in"] == PRIMARY_STORM_THRESHOLD_IN)
        & (summary["combo"] == PRIMARY_STORM_COMBINATION)
    ]
    for _, row in primary.iterrows():
        out.append("")
        out.append(format_2x2(f"pop = {row['pop']}", row.to_dict()))
    out.append("")
    out.append("  Compact summary across every configuration (rule 2.2 — base rate beside every rate):")
    compact = summary[
        ["pop", "storm_in", "combo", "a", "b", "c", "d", "storm_rate_pop",
         "storm_rate_pop_noclaim", "base_rate", "nonpop_rate", "pod", "pofd", "pss",
         "n_pop_occasions", "n_storm_events"]
    ]
    out.append(_table(compact))
    out.append("")
    out.append(
        "  Reading PSS here: the pop row holds one occasion per pop event (dozens) while "
        "the comparison row holds every other winter day (thousands). POD is therefore "
        "small by construction — a rare forecast cannot detect most storms — and PSS is "
        "bounded by how often pops fire, so its MAGNITUDE is not comparable across "
        "thresholds. Its SIGN is meaningful, and the row-conditional storm-rate-given-pop "
        "against base rate is the comparison to read across the sweep."
    )
    out.append("")

    # Per-station view for Q20
    station_summary = build_stage1_summary(
        pop_flags, df, gain_columns, tuple(gain_columns.keys()), (PRIMARY_STORM_THRESHOLD_IN,)
    )
    out.append(
        f"  Per-station view at {PRIMARY_STORM_THRESHOLD_IN:g} in (DECISIONS.md Q20 — does "
        "combining stations blur a canyon-sharp signal?):"
    )
    out.append(
        _table(
            station_summary[
                ["pop", "combo", "storm_rate_pop", "base_rate", "pss",
                 "n_pop_occasions", "n_storm_events"]
            ]
        )
    )
    out.append("")

    dose_path = figures_dir / "dose_response_curve.png"
    plot_dose_response(primary, dose_path)
    out.append(f"  Dose-response curve saved: {repo_relative(dose_path)}")
    out.append("  Shape of the dose-response curve, in words:")
    out.append(
        describe_dose_response(
            primary[primary["pop"].str.startswith("abs_")],
            "absolute / percentile sweep",
        )
    )
    out.append(
        describe_dose_response(
            primary[primary["pop"].str.startswith("z_")], "z-score sweep"
        )
    )
    out.append("")

    # --- Part 6: Stage 2 ---
    abs_labels = [f"abs_p{p}" for p in POP_PERCENTILES]
    z_labels = [f"z_{sd:g}sd" for sd in POP_ZSCORE_SDS]
    scan = run_lag_scan(
        pop_flags, abs_labels + z_labels, df, gain_columns,
        PRIMARY_STORM_THRESHOLD_IN, PRIMARY_STORM_COMBINATION,
    )
    lag_path = figures_dir / "lag_scan_pss.png"
    lag_z_path = figures_dir / "lag_scan_pss_zscore.png"
    plot_lag_scan(
        scan, abs_labels,
        f"Lag scan, absolute pop definition — storm {PRIMARY_STORM_THRESHOLD_IN:g} in "
        f"{PRIMARY_STORM_COMBINATION} (EXPLORATORY)",
        lag_path,
    )
    plot_lag_scan(
        scan, z_labels,
        f"Lag scan, z-score pop definition — storm {PRIMARY_STORM_THRESHOLD_IN:g} in "
        f"{PRIMARY_STORM_COMBINATION} (EXPLORATORY)",
        lag_z_path,
    )
    out.append("PART 6 — STAGE 2: LAG SCAN (0-30 days, window [lag-4, lag+4])")
    out.append(
        f"  Primary configuration, declared in advance: absolute pop at the "
        f"{PRIMARY_POP_PERCENTILE}th percentile, storm {PRIMARY_STORM_THRESHOLD_IN:g} in "
        f"{PRIMARY_STORM_COMBINATION}. Every swept threshold is plotted, so no lag or "
        "threshold is selected by its result."
    )
    out.append(
        "  Reading guide: a genuine regime signal shows a BROAD bump across adjacent lags, "
        "because atmospheric patterns persist for days. An isolated spike at one lag with "
        "near-zero neighbours is noise, not physics. No 'best lag' is chosen here."
    )
    out.append("")
    primary_scan = scan[scan["pop"] == f"abs_p{PRIMARY_POP_PERCENTILE}"].sort_values("lag")
    out.append(f"  PSS by lag, pop = abs_p{PRIMARY_POP_PERCENTILE}:")
    out.append(
        _table(
            primary_scan[["lag", "lag_lo", "lag_hi", "a", "b", "storm_rate_pop",
                          "base_rate", "pod", "pofd", "pss"]]
        )
    )
    out.append("")
    pivot = scan.pivot_table(index="lag", columns="pop", values="pss")[abs_labels + z_labels]
    out.append("  PSS by lag, every swept pop threshold:")
    out.append(pivot.to_string(float_format=lambda v: "%.4f" % v))
    out.append("")
    out.append(f"  Lag scan plots saved: {repo_relative(lag_path)}, {repo_relative(lag_z_path)}")
    out.append("  Shape of the lag scan, in words (no lag is crowned):")
    out.extend(describe_lag_scan(scan, abs_labels + z_labels))
    out.append("")
    out.append(
        "EVENT-COUNT CAVEAT (rule 2.2 / Q17): 16 exploration winters give dozens of "
        "independent events, not thousands. Every table above carries its pop-event and "
        "storm-event counts; none may be over-read."
    )
    out.append("GATE: Stage 3 (modelling) is not run. It is gated on the joint review.")

    text = "\n".join(out)
    print(text)
    report_path = outputs_dir / "phase5a_counting_report.txt"
    report_path.write_text(text)
    logger.info("Wrote %s", repo_relative(report_path))


if __name__ == "__main__":
    main()
