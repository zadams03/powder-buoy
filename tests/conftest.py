"""Shared test setup.

Tests marked `needs_processed_data` read `analysis_daily.parquet`, which is gitignored
and built by the ingest commands. On a fresh clone they skip rather than fail.
"""

import pytest

from powderbuoy.config import load_config

ANALYSIS_DAILY = load_config("utah")["paths"]["processed"] / "analysis_daily.parquet"


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "needs_processed_data: reads data/processed/analysis_daily.parquet"
    )


def pytest_collection_modifyitems(config, items):
    if ANALYSIS_DAILY.exists():
        return
    skip = pytest.mark.skip(
        reason="processed data not found — run the ingest commands in README.md"
    )
    for item in items:
        if "needs_processed_data" in item.keywords:
            item.add_marker(skip)
