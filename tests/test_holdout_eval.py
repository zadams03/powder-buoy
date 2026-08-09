"""Tests for the Phase 7 held-out evaluation (SPEC Section 8, frozen at spec 0.8).

No new analytical logic is tested here — `detect_events` and `contingency_from_flags`
are reused unchanged from `events.py` and are covered by `test_events.py`. What these
tests guard is the thing that can only go wrong once: that the box is opened deliberately,
opened correctly, and that the pop threshold is the frozen metre value rather than
anything re-derived from the held-out distribution.

These tests load winter LABELS from the held-out set (as `test_seasons.py` already does)
and never score the rule — scoring happens exactly once, in the run itself.
"""

import numpy as np
import pandas as pd

from powderbuoy import holdout_eval
from powderbuoy.holdout_eval import (
    HELD_OUT_WINTERS,
    POP_THRESHOLD_M,
    build_locked_pop_flags,
    load_holdout_frame,
    verdict,
)

EXPLORATION_WINTERS = {1989, 1990, 1992, 1994, 1996, 1998, 1999, 2000, 2001, 2003,
                       2015, 2016, 2017, 2018, 2019, 2020}
FOLKLORE_ONLY_WINTERS = {2023, 2024, 2025}


# --- 1. The box is opened deliberately, and opened correctly -----------------


def test_holdout_loader_asks_for_the_holdout_explicitly(monkeypatch):
    """The unsealing must be an explicit include_holdout=True, not a forgotten filter."""
    seen = {}
    real = holdout_eval.load_analysis_data

    def spy(*args, **kwargs):
        seen.update(kwargs)
        return real(*args, **kwargs)

    monkeypatch.setattr(holdout_eval, "load_analysis_data", spy)
    load_holdout_frame(region="utah")

    assert seen.get("include_holdout") is True


def test_holdout_frame_scores_exactly_the_six_held_out_winters():
    df = load_holdout_frame(region="utah")
    winters = tuple(sorted(int(w) for w in df["winter"].unique()))

    assert winters == HELD_OUT_WINTERS
    assert winters == (2004, 2005, 2006, 2008, 2021, 2022)


def test_holdout_frame_pools_in_no_exploration_or_folklore_only_winter():
    """SPEC 8.2: the six are scored on their own. SPEC 8.5: 2023-2025 are not used."""
    df = load_holdout_frame(region="utah")
    winters = {int(w) for w in df["winter"].unique()}

    assert winters.isdisjoint(EXPLORATION_WINTERS)
    assert winters.isdisjoint(FOLKLORE_ONLY_WINTERS)
    assert set(df["season_set"].unique()) == {"held_out"}


# --- 2. The pop threshold is the frozen metre value --------------------------


def _synthetic(wvht: list[float | None]) -> pd.DataFrame:
    dates = pd.date_range("2021-11-01", periods=len(wvht), freq="D")
    return pd.DataFrame({"date": dates, "buoy_51001_wvht_mean": wvht})


def test_pop_flag_uses_the_fixed_metre_value_and_is_inclusive():
    df = _synthetic([POP_THRESHOLD_M - 0.001, POP_THRESHOLD_M, POP_THRESHOLD_M + 0.001])
    flags = build_locked_pop_flags(df, "buoy_51001_wvht_mean")

    assert list(flags) == [False, True, True]


def test_pop_threshold_is_never_re_derived_from_the_data_it_scores():
    """A frame whose own 90th percentile is nowhere near 3.9530 m must still use 3.9530.

    This is the one-shot property in SPEC 8.2: recomputing the percentile here would let
    the held-out distribution set its own threshold.
    """
    values = [1.0] * 9 + [2.0]
    df = _synthetic(values)
    flags = build_locked_pop_flags(df, "buoy_51001_wvht_mean")

    assert float(np.percentile(values, 90)) < POP_THRESHOLD_M
    assert not flags.any()


def test_a_day_the_buoy_did_not_report_has_no_pop_flag():
    """Undefined is pd.NA — an occasion on neither row, never read as 'no pop' (2.5)."""
    df = _synthetic([None, 5.0, None])
    flags = build_locked_pop_flags(df, "buoy_51001_wvht_mean")

    assert pd.isna(flags.iloc[0])
    assert flags.iloc[1] is True or bool(flags.iloc[1]) is True
    assert int(flags.notna().sum()) == 1


# --- 3. The verdict is read off SPEC 8.4's bar mechanically ------------------


def _variants(ratio_a, pss_a, ratio_b, pss_b):
    return {
        "with_claiming": {"ratio": ratio_a, "pss": pss_a},
        "without_claiming": {"ratio": ratio_b, "pss": pss_b},
    }


def test_verdict_is_null_confirmed_when_s_holds_for_neither_variant():
    assert verdict(_variants(0.9, -0.02, 1.05, 0.01))["label"] == "NULL CONFIRMED"


def test_verdict_is_surprising_when_s_holds_for_both_variants():
    assert verdict(_variants(1.30, 0.05, 1.25, 0.02))["label"] == "SURPRISING"


def test_verdict_is_split_when_s_holds_for_exactly_one_variant():
    assert verdict(_variants(1.30, 0.05, 1.10, 0.01))["label"].startswith("SPLIT")


def test_both_halves_of_s_are_required():
    """ratio >= 1.20 alone is not S, and a positive PSS alone is not S (SPEC 8.4)."""
    assert verdict(_variants(1.50, -0.01, 1.50, -0.01))["label"] == "NULL CONFIRMED"
    assert verdict(_variants(1.19, 0.30, 1.19, 0.30))["label"] == "NULL CONFIRMED"
