import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from app.config import ROOT_DIR

# The real file holds personal search settings and is ignored by git
DEFAULT_PATH = ROOT_DIR / "config" / "search.toml"


@dataclass
class Center:
    name: str
    radius_km: int


@dataclass
class SearchSettings:
    keywords: list[str]
    centers: list[Center]
    remote_germany: bool = True
    reopen_after_days: int = 60
    max_requests_per_run: int = 300


def load_settings(path: Path | None = None) -> SearchSettings:
    path = path or Path(os.environ.get("SEARCH_SETTINGS_PATH", DEFAULT_PATH))
    with open(path, "rb") as f:
        data = tomllib.load(f)
    centers = [Center(**c) for c in data.pop("centers", [])]
    return SearchSettings(**{"keywords": [], **data, "centers": centers})
