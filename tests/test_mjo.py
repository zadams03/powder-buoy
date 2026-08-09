"""Tests for the Phase 5b MJO mechanism check. No network."""

import numpy as np
import pandas as pd

from powderbuoy.mjo import (
    ERA_POOLED,
    ERA_POST_SEAM,
    ERA_PRE_SEAM,
    GROUP_EXCLUDED,
    GROUP_FAVOURABLE,
    GROUP_UNFAVOURABLE,
    link_b_declared_test,
    overlap_counts,
    phase_group,
    seam_era,
    split_at_seam,
    storm_in_window,
    straddling_winters,
)


# --- 1. Phase grouping -------------------------------------------------------


def test_a_strong_favourable_phase_day_is_favourable():
    assert phase_group(7, 1.4) == GROUP_FAVOURABLE
    assert phase_group(6, 1.01) == GROUP_FAVOURABLE
    assert phase_group(8, 2.9) == GROUP_FAVOURABLE


def test_a_strong_unfavourable_phase_day_is_unfavourable():
    assert phase_group(3, 1.2) == GROUP_UNFAVOURABLE
    assert phase_group(2, 1.5) == GROUP_UNFAVOURABLE
    assert phase_group(4, 1.1) == GROUP_UNFAVOURABLE


def test_a_low_amplitude_day_is_excluded_whatever_its_phase():
    # Below amplitude 1.0 there is no coherent MJO, so the phase label means
    # nothing — a phase 7 day at amplitude 0.8 is not a favourable day.
    assert phase_group(7, 0.8) == GROUP_EXCLUDED
    assert phase_group(3, 0.8) == GROUP_EXCLUDED
    # The threshold is strict: exactly 1.0 is not above 1.0.
    assert phase_group(7, 1.0) == GROUP_EXCLUDED


def test_transitional_phases_1_and_5_are_excluded_from_the_primary_contrast():
    assert phase_group(1, 2.0) == GROUP_EXCLUDED
    assert phase_group(5, 2.0) == GROUP_EXCLUDED


def test_a_missing_phase_or_amplitude_is_excluded_never_guessed():
    assert phase_group(None, 1.5) == GROUP_EXCLUDED
    assert phase_group(7, None) == GROUP_EXCLUDED
    assert phase_group(pd.NA, pd.NA) == GROUP_EXCLUDED
    assert phase_group(7, np.nan) == GROUP_EXCLUDED


# --- 2. Base-rate sanity: no manufactured effect -----------------------------


def _synthetic_frame(phases, storm_days, winter=2016, start="2016-11-01"):
    """One winter of days with a given phase sequence and given storm days."""
    dates = pd.date_range(start, periods=len(phases), freq="D")
    frame = pd.DataFrame(
        {
            "date": dates,
            "winter": winter,
            "mjo_phase": pd.array(phases, dtype="Int64"),
            "mjo_amplitude": 1.5,
            "snow_a_swe_gain_in": 0.0,
            "snow_b_swe_gain_in": 0.0,
        }
    )
    mark = pd.DatetimeIndex(storm_days)
    frame.loc[frame["date"].isin(mark), ["snow_a_swe_gain_in", "snow_b_swe_gain_in"]] = 2.0
    return frame


_GAIN_COLUMNS = {"A": "snow_a_swe_gain_in", "B": "snow_b_swe_gain_in"}


def test_storms_independent_of_phase_give_equal_favourable_and_unfavourable_rates():
    # Phases cycle 1..8 on a fixed calendar and storms fall on a fixed 9-day
    # rhythm, so the two are coprime and no phase is favoured. The measured
    # rates must come out close to equal — the machinery must not manufacture a
    # difference where none was built in.
    rng = np.random.default_rng(11)
    n_days = 181 * 12
    dates = pd.date_range("2016-11-01", periods=n_days, freq="D")
    phases = np.tile(np.arange(1, 9), n_days // 8 + 1)[:n_days]
    storm_days = dates[rng.random(n_days) < 0.08]

    frame = pd.DataFrame(
        {
            "date": dates,
            "winter": 2016,
            "mjo_phase": pd.array(phases, dtype="Int64"),
            "mjo_amplitude": 1.5,
            "snow_a_swe_gain_in": 0.0,
            "snow_b_swe_gain_in": 0.0,
        }
    )
    frame.loc[
        frame["date"].isin(storm_days), ["snow_a_swe_gain_in", "snow_b_swe_gain_in"]
    ] = 2.0

    result = link_b_declared_test(frame, _GAIN_COLUMNS, 1.0, "any2", (1, 14))

    assert result["n_favourable_days"] > 300
    assert result["n_unfavourable_days"] > 300
    assert abs(result["storm_rate_favourable"] - result["storm_rate_unfavourable"]) < 0.05
    assert abs(result["rate_ratio"] - 1.0) < 0.10
    assert abs(result["pss"]) < 0.05


def test_the_declared_test_can_still_see_an_effect_that_is_really_there():
    # The mirror of the test above: if every storm is planted 7 days after a
    # favourable day and nowhere else, the lagged framing must find it.
    dates = pd.date_range("2016-11-01", periods=180, freq="D")
    phases = np.where((np.arange(180) // 20) % 2 == 0, 7, 3)
    frame = pd.DataFrame(
        {
            "date": dates,
            "winter": 2016,
            "mjo_phase": pd.array(phases, dtype="Int64"),
            "mjo_amplitude": 1.5,
            "snow_a_swe_gain_in": 0.0,
            "snow_b_swe_gain_in": 0.0,
        }
    )
    favourable_days = dates[phases == 7]
    planted = favourable_days[::20] + pd.Timedelta(days=7)
    frame.loc[frame["date"].isin(planted), ["snow_a_swe_gain_in", "snow_b_swe_gain_in"]] = 2.0

    result = link_b_declared_test(frame, _GAIN_COLUMNS, 1.0, "any2", (1, 14))

    assert result["storm_rate_favourable"] > result["storm_rate_unfavourable"]
    assert result["pss"] > 0


# --- 3. Overlap counting -----------------------------------------------------


def test_overlap_counts_the_both_present_days_correctly():
    dates = pd.date_range("2016-11-01", periods=10, freq="D")
    # MJO missing on days 0-1; buoy missing on days 1-3; amplitude below the
    # coherence threshold on days 4-5.
    amplitude = [np.nan, np.nan, 1.5, 1.5, 0.4, 0.4, 1.5, 1.5, 1.5, 1.5]
    phases = [None, None, 7, 3, 7, 3, 7, 3, 7, 3]
    wvht = [2.0, np.nan, np.nan, np.nan, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0]
    frame = pd.DataFrame(
        {
            "date": dates,
            "mjo_phase": pd.array(phases, dtype="Int64"),
            "mjo_amplitude": amplitude,
            "buoy_51001_wvht_mean": wvht,
        }
    )

    counts = overlap_counts(frame, "buoy_51001_wvht_mean")

    assert counts["n_winter_days"] == 10
    assert counts["n_mjo_present"] == 8  # days 2-9
    assert counts["n_buoy_present"] == 7  # day 0 and days 4-9
    assert counts["n_both_present"] == 6  # days 4-9
    assert counts["n_mjo_coherent"] == 6  # days 2,3,6,7,8,9
    assert counts["n_both_present_coherent"] == 4  # days 6-9


# --- 4. The lagged framing attributes a storm to the right anchor ------------


def test_a_storm_on_day_d_plus_7_is_attributed_to_a_favourable_day_d():
    dates = pd.date_range("2016-11-01", periods=60, freq="D")
    starts = pd.Series(dates == pd.Timestamp("2016-11-11"), index=dates)

    hit = storm_in_window(starts, dates, 1, 14)

    # 2016-11-04 is D, the storm is D+7, so D is a hit.
    assert bool(hit[dates.get_loc(pd.Timestamp("2016-11-04"))])
    # The full window [D+1, D+14] around the storm: 2016-10-28..2016-11-10 would
    # be hits, but the frame starts 11-01, so check both edges that exist.
    assert bool(hit[dates.get_loc(pd.Timestamp("2016-11-10"))])  # storm at D+1
    assert not bool(hit[dates.get_loc(pd.Timestamp("2016-11-11"))])  # storm is same-day, not lagged
    assert not bool(hit[dates.get_loc(pd.Timestamp("2016-11-12"))])  # storm already past


def test_the_same_day_framing_fires_only_on_the_storm_start_day():
    dates = pd.date_range("2016-11-01", periods=30, freq="D")
    starts = pd.Series(dates == pd.Timestamp("2016-11-15"), index=dates)

    hit = storm_in_window(starts, dates, 0, 0)

    assert hit.sum() == 1
    assert bool(hit[dates.get_loc(pd.Timestamp("2016-11-15"))])


def test_a_window_running_past_the_end_of_its_winter_is_not_an_occasion():
    # The last 14 days of a winter cannot be lagged occasions: their window
    # would run into the summer, or into the next winter.
    frame = _synthetic_frame([7] * 30, storm_days=["2016-11-20"])

    result = link_b_declared_test(frame, _GAIN_COLUMNS, 1.0, "any2", (1, 14))

    assert result["n_favourable_days"] == 30 - 14
    assert result["n_unfavourable_days"] == 0


# --- 5. The seam splitter (Phase 6 Part 3, DECISIONS.md Q23) -----------------


def test_winters_are_partitioned_at_the_2013_2014_boundary():
    # The BoM method changed at 2013-12-31 / 2014-01-01, so winter 2013 and
    # everything before it is pre-seam and winter 2014 onward is post-seam.
    assert seam_era(2013) == ERA_PRE_SEAM
    assert seam_era(2014) == ERA_POST_SEAM
    # The two eras this project actually holds, at their nearest edges.
    assert seam_era(2003) == ERA_PRE_SEAM
    assert seam_era(2015) == ERA_POST_SEAM
    assert seam_era(1989) == ERA_PRE_SEAM
    assert seam_era(2020) == ERA_POST_SEAM


def test_split_at_seam_sends_every_row_to_exactly_one_era():
    frame = pd.DataFrame(
        {
            "date": list(pd.date_range("2003-11-01", periods=3, freq="D"))
            + list(pd.date_range("2015-11-01", periods=4, freq="D")),
            "winter": [2003] * 3 + [2015] * 4,
        }
    )

    split = split_at_seam(frame)

    assert len(split[ERA_POOLED]) == 7
    assert sorted(split[ERA_PRE_SEAM]["winter"].unique()) == [2003]
    assert sorted(split[ERA_POST_SEAM]["winter"].unique()) == [2015]
    assert len(split[ERA_PRE_SEAM]) + len(split[ERA_POST_SEAM]) == len(frame)


def test_a_winter_straddling_the_seam_is_detected_not_assumed_away():
    # Winter 2013 runs Nov 2013 - Apr 2014 and so genuinely holds days computed
    # by both methods. No such winter is in any split here (the 51001 archive
    # hole removed 2009-2014), but the check must find one if it ever appears.
    straddling = pd.DataFrame(
        {
            "date": [pd.Timestamp("2013-12-30"), pd.Timestamp("2014-01-02")],
            "winter": [2013, 2013],
        }
    )
    clean = pd.DataFrame(
        {
            "date": [pd.Timestamp("2003-12-30"), pd.Timestamp("2016-01-02")],
            "winter": [2003, 2015],
        }
    )

    assert straddling_winters(straddling) == [2013]
    assert straddling_winters(clean) == []


def test_windows_never_cross_from_one_winter_into_the_next():
    # Two winters made deliberately contiguous on the calendar, so that a window
    # crossing the boundary would be arithmetically possible. It must not be:
    # the last 14 days of the first winter are not occasions at all, and the
    # storm planted just after the boundary belongs to the second winter alone.
    dates = pd.date_range("2016-11-01", periods=60, freq="D")
    frame = pd.DataFrame(
        {
            "date": dates,
            "winter": [2016] * 30 + [2017] * 30,
            "mjo_phase": pd.array([7] * 30 + [3] * 30, dtype="Int64"),
            "mjo_amplitude": 1.5,
            "snow_a_swe_gain_in": 0.0,
            "snow_b_swe_gain_in": 0.0,
        }
    )
    # Storm on the second day of the second winter — 2 days after the boundary.
    frame.loc[32, ["snow_a_swe_gain_in", "snow_b_swe_gain_in"]] = 2.0

    result = link_b_declared_test(frame, _GAIN_COLUMNS, 1.0, "any2", (1, 14))

    # Each winter contributes only the days whose window fits inside it.
    assert result["n_favourable_days"] == 30 - 14
    assert result["n_unfavourable_days"] == 30 - 14
    # Not one of the first winter's days claims the second winter's storm.
    assert result["a"] == 0
    assert result["c"] > 0
