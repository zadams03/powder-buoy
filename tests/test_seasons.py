import datetime as dt

from powderbuoy.config import load_config
from powderbuoy.seasons import load_analysis_data, winter_of

HELD_OUT_WINTERS = [2004, 2005, 2006, 2008, 2021, 2022]


def test_winter_of_labels_nov_dec_as_starting_year():
    assert winter_of(dt.date(2015, 12, 15)) == 2015
    assert winter_of(dt.date(2016, 11, 2)) == 2016


def test_winter_of_labels_jan_apr_as_previous_year():
    assert winter_of(dt.date(2016, 2, 10)) == 2015


def test_winter_of_returns_none_outside_winter():
    assert winter_of(dt.date(2016, 7, 1)) is None


def test_default_load_excludes_held_out_winters():
    df = load_analysis_data(region="utah")
    present = set(df["winter"].unique())
    assert present.isdisjoint(HELD_OUT_WINTERS)


def test_include_holdout_reveals_exactly_the_held_out_winters():
    df_default = load_analysis_data(region="utah")
    df_all = load_analysis_data(region="utah", include_holdout=True)
    revealed = sorted(set(df_all["winter"].unique()) - set(df_default["winter"].unique()))
    assert revealed == HELD_OUT_WINTERS


def test_season_set_labelling_matches_config_for_a_sample():
    config = load_config("utah")
    seasons_cfg = config["seasons"]
    df = load_analysis_data(region="utah", include_holdout=True)
    labels = df[["winter", "season_set"]].drop_duplicates().set_index("winter")["season_set"]

    sample_exploration = seasons_cfg["exploration"][0]
    sample_held_out = seasons_cfg["held_out"][0]
    sample_folklore_only = seasons_cfg["folklore_only"][0]

    assert labels.get(sample_exploration) == "exploration"
    assert labels.get(sample_held_out) == "held_out"
    if sample_folklore_only in labels.index:
        assert labels.get(sample_folklore_only) == "folklore_only"


def test_no_winter_carries_more_than_one_label():
    df = load_analysis_data(region="utah", include_holdout=True)
    labels_per_winter = df.groupby("winter")["season_set"].nunique()
    assert (labels_per_winter == 1).all()


def test_loader_winter_lists_match_config_exactly():
    config = load_config("utah")
    seasons_cfg = config["seasons"]
    df = load_analysis_data(region="utah", include_holdout=True)

    for season_set in ("exploration", "held_out", "folklore_only"):
        expected = set(seasons_cfg[season_set])
        actual = set(df.loc[df["season_set"] == season_set, "winter"].unique())
        # actual may be a subset of expected if a configured winter has no
        # rows in analysis_daily at all; it must never contain a winter
        # outside the configured list.
        assert actual.issubset(expected)
