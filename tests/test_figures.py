"""Phase 8c — the winter-selection rule behind the hypothesis figure.

The figure itself is presentation only, but the rule that picks which winters it draws is
the part that has to be trustworthy: it exists so the four panels are chosen by a declared
rule rather than by how well the pops line up. These tests hold it to that — two winters
per era, the most data-complete ones, ties by the earliest, and never a held-out winter.

No data file is read: every test builds its own frame.
"""

import numpy as np
import pandas as pd
import pytest

from powderbuoy.figures import assign_lanes, era_of, select_winters
from powderbuoy.holdout_eval import HELD_OUT_WINTERS

WVHT = "buoy_51001_wvht_mean"


def _frame(missing_by_winter: dict[int, int], days: int = 60) -> pd.DataFrame:
    """One synthetic winter per key, with the requested number of non-reporting days."""
    rows = []
    for winter, missing in missing_by_winter.items():
        dates = pd.date_range(f"{winter}-11-01", periods=days, freq="D")
        values = np.full(days, 3.0)
        values[:missing] = np.nan
        rows.append(pd.DataFrame({"date": dates, "winter": winter, WVHT: values}))
    return pd.concat(rows).reset_index(drop=True)


def test_era_split_follows_the_buoy_gap():
    assert era_of(2003) == "pre_gap"
    assert era_of(2009) == "pre_gap"
    assert era_of(2015) == "post_gap"
    # The 2010-2014 archive hole belongs to neither era and no winter sits in it.
    assert era_of(2012) is None


def test_selects_four_winters_two_per_era_by_completeness():
    df = _frame({1998: 10, 1999: 2, 2001: 0, 2015: 5, 2016: 0, 2018: 1})
    selected = select_winters(df, WVHT)

    assert list(selected["winter"]) == [1999, 2001, 2016, 2018]
    assert list(selected["era"]).count("pre_gap") == 2
    assert list(selected["era"]).count("post_gap") == 2
    # Chronological, so the grid reads earliest top-left.
    assert list(selected["winter"]) == sorted(selected["winter"])


def test_ties_on_completeness_are_broken_by_the_earliest_winter():
    df = _frame({1996: 0, 1998: 0, 2000: 0, 2016: 0, 2017: 0, 2019: 0})
    selected = select_winters(df, WVHT)
    assert list(selected["winter"]) == [1996, 1998, 2016, 2017]


def test_a_held_out_winter_is_refused():
    # Held-out winters cannot reach this function through the sanctioned loader; the
    # guard exists so that a hand-built frame cannot smuggle one into a fresh figure
    # after the seal has been spent (rule 2.3).
    sealed = HELD_OUT_WINTERS[0]
    df = _frame({1996: 0, sealed: 0, 2016: 0, 2017: 0})
    with pytest.raises(ValueError, match="held-out"):
        select_winters(df, WVHT)


def test_an_era_short_of_winters_raises_rather_than_drawing_a_lopsided_grid():
    df = _frame({1996: 0, 1998: 0, 2016: 0})
    with pytest.raises(ValueError, match="post_gap"):
        select_winters(df, WVHT)


def test_overlapping_windows_are_stacked_and_separated_ones_reuse_a_lane():
    starts = pd.DatetimeIndex(["2016-01-01", "2016-01-05", "2016-02-20"])
    lanes = assign_lanes(starts)
    # The first two overlap (each spans 18 days from its own date), the third does not.
    assert lanes[0] == 0
    assert lanes[1] == 1
    assert lanes[2] == 0
