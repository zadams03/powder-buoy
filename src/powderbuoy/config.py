"""Load and validate project configuration.

Merges the shared `config/settings.yaml` with a region file under
`config/regions/{region}.yaml`. The region name is the only thing a caller
passes — no station ID may appear anywhere outside `config/regions/`.
"""

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]

_REQUIRED_SETTINGS_KEYS = [
    ("paths", "raw"),
    ("paths", "processed"),
    ("paths", "outputs"),
    ("defaults", "seed"),
    ("defaults", "request_delay_seconds"),
    ("defaults", "request_timeout_seconds"),
    ("defaults", "max_retries"),
]

_REQUIRED_REGION_KEYS = [
    ("region",),
    ("buoys", "primary"),
    ("buoys", "secondary"),
    ("snow_stations",),
    ("season", "start_month_day"),
    ("season", "end_month_day"),
]


def _require(config: dict, keys: tuple, source: Path) -> None:
    node = config
    for key in keys:
        if not isinstance(node, dict) or key not in node:
            path = ".".join(keys)
            raise ValueError(f"Missing required key '{path}' in {source}")
        node = node[key]


def _load_yaml(path: Path) -> dict:
    if not path.exists():
        raise ValueError(f"Config file not found: {path}")
    with open(path) as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError(f"Config file did not parse to a mapping: {path}")
    return data


def load_config(region: str = "utah") -> dict:
    """Load settings.yaml merged with the named region file.

    Raises ValueError with a clear message if a required key is missing.
    Resolves relative paths against the repo root.
    """
    settings_path = REPO_ROOT / "config" / "settings.yaml"
    region_path = REPO_ROOT / "config" / "regions" / f"{region}.yaml"

    settings = _load_yaml(settings_path)
    for keys in _REQUIRED_SETTINGS_KEYS:
        _require(settings, keys, settings_path)

    region_config = _load_yaml(region_path)
    for keys in _REQUIRED_REGION_KEYS:
        _require(region_config, keys, region_path)

    resolved_paths = {
        name: (REPO_ROOT / value).resolve()
        for name, value in settings["paths"].items()
    }

    config = {
        "paths": resolved_paths,
        "defaults": settings["defaults"],
        **region_config,
    }
    return config
