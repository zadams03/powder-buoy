import math

import numpy as np
import pandas as pd

from powderbuoy.ingest.ndbc import (
    _expand_two_digit_year,
    aggregate_daily,
    apply_sentinels,
    circular_mean_deg,
)


def test_circular_mean_deg_crosses_north():
    result = circular_mean_deg([350, 10])
    assert result is not None
    assert math.isclose(result, 0.0, abs_tol=1e-6) or math.isclose(result, 360.0, abs_tol=1e-6)


def test_circular_mean_deg_empty_returns_none():
    assert circular_mean_deg([]) is None


def test_apply_sentinels_converts_missing_but_keeps_legitimate_values():
    df = pd.DataFrame({
        "WVHT": [99.00, 9.90],
        "MWD": [999, 180],
    })
    result = apply_sentinels(df)
    assert np.isnan(result["WVHT"].iloc[0])
    assert result["WVHT"].iloc[1] == 9.90
    assert np.isnan(result["MWD"].iloc[0])
    assert result["MWD"].iloc[1] == 180


def test_two_digit_year_expansion():
    assert _expand_two_digit_year(85) == 1985
    assert _expand_two_digit_year(3) == 2003


def test_aggregate_daily_preserves_gap_rows():
    df = pd.DataFrame({
        "timestamp": pd.to_datetime(
            ["2020-01-01 00:00", "2020-01-01 06:00", "2020-01-03 12:00"], utc=True
        ),
        "WVHT": [1.0, 2.0, 3.0],
        "DPD": [10.0, 11.0, 12.0],
        "APD": [8.0, 8.5, 9.0],
        "MWD": [300, 310, 320],
        "WSPD": [5.0, 6.0, 7.0],
        "PRES": [1010.0, 1011.0, 1012.0],
    })
    result = aggregate_daily(df, "51001")

    assert len(result) == 3
    assert list(result["date"].astype(str)) == ["2020-01-01", "2020-01-02", "2020-01-03"]

    day2 = result.iloc[1]
    assert day2["n_obs"] == 0
    assert np.isnan(day2["wvht_mean"])
    assert np.isnan(day2["dpd_mean"])
    assert np.isnan(day2["apd_mean"])
    assert day2["mwd_mean"] is None or np.isnan(day2["mwd_mean"])
    assert np.isnan(day2["wspd_mean"])
    assert np.isnan(day2["pres_mean"])
    assert day2["station"] == "51001"

    day1 = result.iloc[0]
    assert day1["n_obs"] == 2
    assert math.isclose(day1["wvht_mean"], 1.5)
