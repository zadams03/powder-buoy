import numpy as np
import pandas as pd

from powderbuoy.ingest.climate import (
    build_climate_daily,
    parse_mjo,
)

MJO_HEADER = (
    " RMM values up to \"real time\".\n"
    " year, month, day, RMM1, RMM2, phase, amplitude.  Missing Value= 1.E36 or 999\n"
)


def _write_mjo_file(tmp_path, data_lines):
    path = tmp_path / "mjo_rmm.txt"
    path.write_text(MJO_HEADER + "\n".join(data_lines) + "\n")
    return path


def test_mjo_amplitude_recomputed_not_trusted_from_file(tmp_path):
    # amplitude column in the file is a bogus 99.0 - must be ignored and recomputed.
    line = "        2015           1           5   3.0000000       4.0000000               5  99.0000000      WH04_method:_OLR_&_NCEP_wind"
    path = _write_mjo_file(tmp_path, [line])
    result = parse_mjo(path)
    assert np.isclose(result.iloc[0]["mjo_amplitude"], 5.0)


def test_mjo_method_seam_at_2013_2014(tmp_path):
    lines = [
        "        2013          12          31   0.2000000       0.3000000               5   0.3605551      WH04_method:_OLR_&_NCEP_wind",
        "        2014           1           1   0.5000000       0.1000000               5   0.5099020      Gottschalk10_method:_OLR_&_ACCESS_wind",
    ]
    path = _write_mjo_file(tmp_path, lines)
    result = parse_mjo(path)
    assert result.iloc[0]["date"].isoformat() == "2013-12-31"
    assert result.iloc[0]["mjo_method"] == "WH2004"
    assert result.iloc[1]["date"].isoformat() == "2014-01-01"
    assert result.iloc[1]["mjo_method"] == "modified2014"


def test_mjo_sentinel_parses_to_nan(tmp_path):
    line = "        2015           1           5   1.00000E+36      0.5000000               5   0.5000000      WH04_method:_OLR_&_NCEP_wind"
    path = _write_mjo_file(tmp_path, [line])
    result = parse_mjo(path)
    assert np.isnan(result.iloc[0]["rmm1"])
    assert np.isnan(result.iloc[0]["mjo_amplitude"])  # depends on the now-NaN rmm1


def _mjo_daily(dates):
    return pd.DataFrame({
        "date": dates,
        "rmm1": [0.1] * len(dates),
        "rmm2": [0.2] * len(dates),
        "mjo_phase": pd.array([5] * len(dates), dtype="Int64"),
        "mjo_amplitude": [0.223606797] * len(dates),
        "mjo_method": ["modified2014"] * len(dates),
    })


def test_monthly_availability_lag_no_within_month_lookahead():
    dates = pd.date_range("2016-01-01", "2016-02-29", freq="D").date.tolist()
    mjo_df = _mjo_daily(dates)
    enso_monthly = pd.DataFrame({"year": [2016], "month": [1], "nino34": [2.5]})
    pdo_monthly = pd.DataFrame(columns=["year", "month", "pdo"])

    climate_daily = build_climate_daily(mjo_df, enso_monthly, pdo_monthly)
    climate_daily["date"] = pd.to_datetime(climate_daily["date"])

    january = climate_daily[climate_daily["date"].dt.month == 1]
    assert january["nino34"].isna().all()

    feb_1 = climate_daily[climate_daily["date"] == pd.Timestamp("2016-02-01")].iloc[0]
    assert np.isclose(feb_1["nino34"], 2.5)


def test_monthly_hold_flat_until_next_month_available():
    dates = pd.date_range("2016-01-01", "2016-02-29", freq="D").date.tolist()
    mjo_df = _mjo_daily(dates)
    enso_monthly = pd.DataFrame({"year": [2016, 2016], "month": [1, 2], "nino34": [2.5, 3.1]})
    pdo_monthly = pd.DataFrame(columns=["year", "month", "pdo"])

    climate_daily = build_climate_daily(mjo_df, enso_monthly, pdo_monthly)
    climate_daily["date"] = pd.to_datetime(climate_daily["date"])

    feb_15 = climate_daily[climate_daily["date"] == pd.Timestamp("2016-02-15")].iloc[0]
    # February's own value (3.1) is not available until March 1 - Feb 15 still
    # reads January's value, held flat.
    assert np.isclose(feb_15["nino34"], 2.5)
    assert feb_15["nino34_is_ffilled"] == True  # noqa: E712
