"""Tests for Phase 5a event detection, matching and scoring. No network."""

import numpy as np
import pandas as pd

from powderbuoy.events import (
    POP_PERCENTILES,
    build_pop_flags,
    contingency_from_flags,
    detect_events,
)


def _daily(flags: list[bool], start: str = "2016-01-01") -> pd.Series:
    index = pd.date_range(start, periods=len(flags), freq="D")
    return pd.Series(flags, index=index)


# --- 1. Collapsing consecutive days into one event ---------------------------


def test_three_consecutive_true_days_form_one_event_dated_by_the_first():
    events = detect_events(_daily([False, True, True, True, False]))

    assert len(events) == 1
    assert events.loc[0, "event_start"] == pd.Timestamp("2016-01-02")
    assert events.loc[0, "event_end"] == pd.Timestamp("2016-01-04")
    assert events.loc[0, "duration_days"] == 3


def test_peak_value_is_the_maximum_over_the_event_span():
    flags = _daily([True, True, True])
    values = pd.Series([2.0, 5.5, 3.0], index=flags.index)
    events = detect_events(flags, values=values)

    assert events.loc[0, "peak_value"] == 5.5


def test_no_true_days_gives_an_empty_event_table():
    events = detect_events(_daily([False, False, False]))

    assert len(events) == 0
    assert list(events.columns) == ["event_start", "event_end", "duration_days"]


# --- 2. Bridging a one-day gap ----------------------------------------------


def test_one_day_gap_is_bridged_at_bridge_1_and_splits_at_bridge_0():
    flags = _daily([True, False, True])

    bridged = detect_events(flags, bridge=1)
    split = detect_events(flags, bridge=0)

    assert len(bridged) == 1
    assert bridged.loc[0, "event_start"] == pd.Timestamp("2016-01-01")
    assert bridged.loc[0, "event_end"] == pd.Timestamp("2016-01-03")
    assert len(split) == 2


def test_a_two_day_gap_is_not_bridged_at_bridge_1():
    assert len(detect_events(_daily([True, False, False, True]), bridge=1)) == 2


def test_events_never_bridge_across_a_gap_in_the_index():
    # Two winters six months apart: a True day at the end of one and the start
    # of the next must never merge, however small the bridge arithmetic.
    index = pd.DatetimeIndex(["2016-04-30", "2016-11-01"])
    events = detect_events(pd.Series([True, True], index=index), bridge=1)

    assert len(events) == 2


# --- 3. One-to-one matching --------------------------------------------------


def _flags_from_dates(dates: list[str], span: pd.DatetimeIndex) -> pd.Series:
    marks = pd.to_datetime(dates)
    return pd.Series(span.isin(marks), index=span)


def test_one_pop_with_two_storms_in_its_window_claims_only_one():
    span = pd.date_range("2016-01-01", periods=60, freq="D")
    pops = _flags_from_dates(["2016-01-05"], span)
    # Both storms start inside [pop + 10, pop + 18].
    storms = _flags_from_dates(["2016-01-16", "2016-01-21"], span)

    result = contingency_from_flags(pops, storms, lag_lo=10, lag_hi=18)

    assert result["n_pop_occasions"] == 1
    assert result["n_storm_events"] == 2
    assert result["a"] == 1
    assert result["b"] == 0


def test_two_pops_competing_for_one_storm_only_one_gets_it():
    span = pd.date_range("2016-01-01", periods=60, freq="D")
    # Both pops have the same single storm inside their windows.
    pops = _flags_from_dates(["2016-01-05", "2016-01-08"], span)
    storms = _flags_from_dates(["2016-01-20"], span)

    result = contingency_from_flags(pops, storms, lag_lo=10, lag_hi=18)

    assert result["n_pop_occasions"] == 2
    assert result["a"] == 1
    assert result["b"] == 1
    # Without claiming, both pops would have counted the same storm.
    assert result["storm_rate_pop_noclaim"] == 1.0


def test_a_window_running_past_the_end_of_its_winter_is_not_an_occasion():
    span = pd.date_range("2016-01-01", periods=20, freq="D")
    pops = _flags_from_dates(["2016-01-15"], span)
    storms = _flags_from_dates(["2016-01-03"], span)

    result = contingency_from_flags(pops, storms, lag_lo=10, lag_hi=18)

    assert result["n_pop_events"] == 1
    assert result["n_pop_occasions"] == 0


def test_windows_do_not_cross_a_group_boundary():
    span = pd.DatetimeIndex(
        list(pd.date_range("2016-01-01", periods=30, freq="D"))
        + list(pd.date_range("2017-01-01", periods=30, freq="D"))
    )
    groups = pd.Series([2015] * 30 + [2016] * 30, index=span)
    pops = _flags_from_dates(["2016-01-25"], span)
    storms = _flags_from_dates(["2017-01-05"], span)

    result = contingency_from_flags(pops, storms, lag_lo=10, lag_hi=18, groups=groups)

    # The pop is 11 days before the storm on the raw calendar, but they sit in
    # different winters, so the pop is not a usable occasion at all.
    assert result["n_pop_occasions"] == 0


# --- 4. Base-rate sanity: noise must not manufacture skill -------------------


def test_random_flags_give_pod_close_to_pofd_and_pss_near_zero():
    rng = np.random.default_rng(42)
    span = pd.date_range("2016-01-01", periods=181 * 8, freq="D")
    pops = pd.Series(rng.random(len(span)) < 0.10, index=span)
    storms = pd.Series(rng.random(len(span)) < 0.15, index=span)

    result = contingency_from_flags(pops, storms, lag_lo=10, lag_hi=18)

    assert result["a"] + result["b"] > 50, "test needs a usable number of pop events"
    assert abs(result["pod"] - result["pofd"]) < 0.05
    assert abs(result["pss"]) < 0.05


def test_a_perfect_predictor_scores_positive_skill():
    # Every pop is followed by a storm exactly 14 days later, and there are no
    # other storms — the scorer must be able to see skill when it is there.
    span = pd.date_range("2016-01-01", periods=200, freq="D")
    pop_dates = [f"2016-01-{day:02d}" for day in (3, 9, 15, 21, 27)]
    storm_dates = [
        (pd.Timestamp(d) + pd.Timedelta(days=14)).strftime("%Y-%m-%d") for d in pop_dates
    ]
    pops = _flags_from_dates(pop_dates, span)
    storms = _flags_from_dates(storm_dates, span)

    result = contingency_from_flags(pops, storms, lag_lo=10, lag_hi=18)

    assert result["storm_rate_pop"] == 1.0
    assert result["pss"] > 0


# --- 5. The percentile sweep resolves percentiles correctly ------------------


def test_percentile_sweep_flags_the_expected_share_of_qualifying_days():
    rng = np.random.default_rng(7)
    dates = pd.date_range("2015-11-01", periods=181, freq="D")
    df = pd.DataFrame(
        {
            "date": dates,
            "winter": 2015,
            "wvht": rng.normal(2.9, 0.9, len(dates)),
        }
    )

    flags, resolved, fraction = build_pop_flags(df, "wvht")

    for percentile in POP_PERCENTILES:
        label = f"abs_p{percentile}"
        expected = 1 - percentile / 100
        assert abs(fraction[label] - expected) < 0.02, label

    # Resolved metre values must rise monotonically with the percentile.
    values = [resolved[f"abs_p{p}"] for p in POP_PERCENTILES]
    assert values == sorted(values)
    assert flags["abs_p95"].notna().all()


def test_undefined_pop_days_are_na_not_false():
    dates = pd.date_range("2015-11-01", periods=181, freq="D")
    wvht = pd.Series(np.linspace(1.0, 5.0, len(dates)))
    wvht.iloc[10:20] = np.nan
    df = pd.DataFrame({"date": dates, "winter": 2015, "wvht": wvht.to_numpy()})

    flags, _, _ = build_pop_flags(df, "wvht")

    assert flags["abs_p90"].isna().sum() == 10
    # z-scores need a trailing window, so the start of the winter is undefined too.
    assert flags["z_1sd"].isna().sum() > 10


def test_trailing_zscore_never_looks_ahead():
    from powderbuoy.events import trailing_zscore

    rng = np.random.default_rng(3)
    dates = pd.date_range("2015-11-01", periods=60, freq="D")
    values = pd.Series(rng.normal(2.0, 0.2, 60), index=dates)
    values.iloc[40] = 10.0  # one huge spike
    groups = pd.Series(2015, index=dates)

    z = trailing_zscore(values, groups, window=30, min_periods=20)

    # The trailing window needs min_periods days before any z exists at all.
    assert z.iloc[:20].isna().all()
    # The day before the spike cannot know the spike is coming.
    assert abs(z.iloc[39]) < 3
    # The spike day itself is scored against the calm days behind it.
    assert z.iloc[40] > 10
