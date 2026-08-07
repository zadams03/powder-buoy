import numpy as np
import pandas as pd

from powderbuoy.ingest.snotel import (
    build_daily_table,
    coverage_flag,
)


def test_swe_gain_null_across_gap():
    df = pd.DataFrame({
        "date": ["2020-01-01", "2020-01-03"],
        "station": ["766:UT:SNTL", "766:UT:SNTL"],
        "swe_in": [10.0, 12.0],
        "precip_accum_in": [5.0, 5.2],
        "temp_mean_f": [20.0, 22.0],
    })
    result = build_daily_table(df, "766:UT:SNTL")

    assert len(result) == 3
    assert list(result["date"].astype(str)) == ["2020-01-01", "2020-01-02", "2020-01-03"]

    day3 = result.iloc[2]
    assert np.isnan(day3["swe_gain_in"])  # not 12.0 - 10.0 smeared across the gap
    day2 = result.iloc[1]
    assert np.isnan(day2["swe_gain_in"])
    assert np.isnan(day2["swe_in"])


def test_negative_gain_preserved_not_clipped():
    df = pd.DataFrame({
        "date": ["2020-02-01", "2020-02-02"],
        "station": ["766:UT:SNTL", "766:UT:SNTL"],
        "swe_in": [10.0, 9.5],
        "precip_accum_in": [5.0, 5.0],
        "temp_mean_f": [30.0, 31.0],
    })
    result = build_daily_table(df, "766:UT:SNTL")
    day2 = result.iloc[1]
    assert np.isclose(day2["swe_gain_in"], -0.5)


def test_missing_values_parse_to_nan_not_sentinel():
    df = pd.DataFrame({
        "date": ["2020-01-01", "2020-01-02"],
        "station": ["766:UT:SNTL", "766:UT:SNTL"],
        "swe_in": [10.0, np.nan],
        "precip_accum_in": [5.0, np.nan],
        "temp_mean_f": [20.0, np.nan],
    })
    result = build_daily_table(df, "766:UT:SNTL")
    day2 = result.iloc[1]
    assert np.isnan(day2["swe_in"])
    assert day2["swe_in"] != 0
    assert pd.isna(day2["is_valid"])


def test_gap_rows_exist():
    df = pd.DataFrame({
        "date": ["2020-01-01", "2020-01-03"],
        "station": ["766:UT:SNTL", "766:UT:SNTL"],
        "swe_in": [10.0, 11.0],
        "precip_accum_in": [5.0, 5.1],
        "temp_mean_f": [20.0, 21.0],
    })
    result = build_daily_table(df, "766:UT:SNTL")
    assert len(result) == 3


def test_coverage_flag_thresholds():
    assert coverage_flag(0.95) == "good"
    assert coverage_flag(0.70) == "thin"
    assert coverage_flag(0.30) == "missing"
    # a winter before install date has no rows at all -> 0% coverage -> missing
    assert coverage_flag(0.0) == "missing"
