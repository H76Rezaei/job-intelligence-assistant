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


# A job whose title contains one of these words is never stored (see is_senior_title)
SENIOR_TITLE_WORDS = ["Senior", "Sr.", "Lead", "Principal", "Staff", "Head of", "Leiter", "Teamleiter"]


@dataclass
class LinkedInSettings:
    # Its own cap, the same on the first run: scraping stays low-volume
    max_requests_per_run: int = 120
    # A random pause in this range (seconds) before every request after the first
    pause_seconds: tuple[float, float] = (20, 30)
    # A search stops after this long, details included, so one large search cannot use up the run
    max_minutes_per_search: float = 20
    # A shorter title list for LinkedIn, where every search is slow; empty: the shared titles
    keywords: list[str] = field(default_factory=list)


@dataclass
class SearchSettings:
    keywords: list[str]
    centers: list[Center]
    remote_germany: bool = True
    reopen_after_days: int = 60
    exclude_title_words: list[str] = field(default_factory=lambda: list(SENIOR_TITLE_WORDS))
    # Requests per source and run; the first run looks back further and gets more
    max_requests_per_run: int = 300
    max_requests_first_run: int = 500
    linkedin: LinkedInSettings = field(default_factory=LinkedInSettings)


def load_settings(path: Path | None = None) -> SearchSettings:
    path = path or Path(os.environ.get("SEARCH_SETTINGS_PATH", DEFAULT_PATH))
    with open(path, "rb") as f:
        data = tomllib.load(f)
    centers = [Center(**c) for c in data.pop("centers", [])]
    linkedin = data.pop("linkedin", {})
    if "pause_seconds" in linkedin:
        linkedin["pause_seconds"] = tuple(linkedin["pause_seconds"])
    return SearchSettings(
        **{"keywords": [], **data, "centers": centers, "linkedin": LinkedInSettings(**linkedin)}
    )
