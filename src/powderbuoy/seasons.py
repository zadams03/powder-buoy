"""Season split and the held-out seal (Phase 4, SPEC rule 2.3).

The exploration / held-out / folklore-only winter lists are decided once, in
planning, and recorded as explicit lists in `config/regions/{region}.yaml` and
in `DECISIONS.md` Q13 — never recomputed or re-derived here. This module only
enforces the split: it reads those lists from config and refuses to hand back
held-out winters unless a caller explicitly asks for them.
"""

from __future__ import annotations

import pandas as pd

from powderbuoy.config import load_config

WINTER_START_MONTHS = (11, 12)
WINTER_END_MONTHS = (1, 2, 3, 4)


def winter_of(date) -> int | None:
    """Return the winter start-year label for a date, or None if outside Nov-Apr.

    Nov-Dec of year Y -> Y. Jan-Apr of year Y -> Y-1. May-Oct -> None (not winter).
    """
    ts = pd.Timestamp(date)
    if ts.month in WINTER_START_MONTHS:
        return ts.year
    if ts.month in WINTER_END_MONTHS:
        return ts.year - 1
    return None


def _season_lists(region: str) -> dict[str, list[int]]:
    config = load_config(region)
    seasons_cfg = config.get("seasons")
    if not seasons_cfg:
        raise ValueError(
            f"No 'seasons' block in config/regions/{region}.yaml — the split "
            "must be recorded in config before it can be loaded (SPEC rule 2.3)."
        )
    return {
        "exploration": list(seasons_cfg.get("exploration", [])),
        "held_out": list(seasons_cfg.get("held_out", [])),
        "folklore_only": list(seasons_cfg.get("folklore_only", [])),
    }


def load_analysis_data(region: str = "utah", include_holdout: bool = False) -> pd.DataFrame:
    """Load analysis_daily, filtered to winters only, with the held-out set
    EXCLUDED BY DEFAULT.

    Adds a 'winter' column (start-year label) and a 'season_set' column
    ('exploration' / 'held_out' / 'folklore_only').

    include_holdout defaults to False: the returned frame contains only
    exploration and folklore_only winters. Held-out winters are dropped. This
    is the seal (SPEC rule 2.3) — enforced here, not just in intent.

    include_holdout=True returns held-out winters too. Any caller passing
    True MUST include an inline comment citing the locked protocol version
    (SPEC Section 8) that authorises it. Before Phase 6 exists, no caller
    should pass True at all.

    A row whose winter falls outside every configured list (summer days, or
    winters not part of any set) is dropped — 'season_set' being null is what
    would mark it, so such rows never appear in the returned frame.
    """
    config = load_config(region)
    processed_dir = config["paths"]["processed"]
    analysis_path = processed_dir / "analysis_daily.parquet"

    df = pd.read_parquet(analysis_path)
    lists = _season_lists(region)

    exploration = set(lists["exploration"])
    held_out = set(lists["held_out"])
    folklore_only = set(lists["folklore_only"])

    df = df.copy()
    df["winter"] = df["date"].map(winter_of).astype("Int64")

    def _label(winter):
        if winter in exploration:
            return "exploration"
        if winter in held_out:
            return "held_out"
        if winter in folklore_only:
            return "folklore_only"
        return None

    df["season_set"] = df["winter"].map(_label)
    df = df[df["season_set"].notna()]

    if not include_holdout:
        df = df[df["season_set"] != "held_out"]

    return df.reset_index(drop=True)
