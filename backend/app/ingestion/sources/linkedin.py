"""LinkedIn's public job search, read without a login.

Uses the guest endpoints behind linkedin.com/jobs (checked 26 Oct 2026). They
return HTML fragments, so all page structure lives in this module. LinkedIn
answers fast requests with 429, so every request after the first waits a
random pause from the settings, and a 429 waits minutes before a retry.
"""

import logging
import random
import time
from collections.abc import Callable, Iterable
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from typing import Any, NoReturn
from urllib.parse import urlsplit, urlunsplit

import httpx
from bs4 import BeautifulSoup, Tag

from app.ingestion.fetched_job import FetchedJob
from app.ingestion.settings import Center, SearchSettings
from app.ingestion.source import RateLimited, RequestCapReached

BASE_URL = "https://www.linkedin.com/jobs-guest/jobs/api"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/130.0 Safari/537.36"
    ),
    # English pages: locations end in "Germany" and job criteria are named in English
    "Accept-Language": "en-US,en;q=0.9",
}
# Titles per search, joined with OR; checked live to return a mix of all titles
TITLES_PER_SEARCH = 8
PAGE_SIZE = 10
# The guest search stops paging at about 1,000 results
MAX_START = 990
# Work type filter: remote
REMOTE = "2"
# Waits before retrying after a 429; one more 429 after the last wait stops the run
RATE_LIMIT_WAITS_SECONDS = (300, 900)
# LinkedIn's answer when it blocks a client, besides redirecting to its login wall
BLOCKED = 999
KM_PER_MILE = 1.609

log = logging.getLogger(__name__)


@dataclass
class _Query:
    titles: list[str]
    center: Center | None  # None: the remote search across Germany

    @property
    def key(self) -> str:
        place = self.center.name if self.center else "remote"
        return f"{' OR '.join(self.titles)} @ {place}"


class LinkedIn:
    name = "linkedin"
    # Keeps a window per search, so a stopped run continues where it stopped (see run.py)
    resumable = True

    def __init__(
        self,
        client: httpx.Client | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ):
        # Redirects are not followed: LinkedIn redirects to its login wall when it blocks
        self.client = client or httpx.Client(timeout=30)
        self.sleep = sleep
        # Set by each search; none before that
        self.requests_left = 0
        self.pause_seconds: tuple[float, float] = (0, 0)
        self._sent_any = False
        # Per search key of the last search: True once it was read to the end
        self.searches_finished: dict[str, bool] = {}

    def search(
        self,
        settings: SearchSettings,
        since: datetime,
        windows: dict[str, datetime] | None = None,
    ) -> Iterable[FetchedJob]:
        """Every title group around every center, plus remote jobs in Germany; each job once.

        Each search looks back to its own time in `windows`, or to `since` when
        it has none yet. The searches waiting longest go first.
        """
        self.requests_left = settings.linkedin.max_requests_per_run
        self.pause_seconds = settings.linkedin.pause_seconds
        self._sent_any = False
        query_since = {query.key: (windows or {}).get(query.key, since) for query in self._queries(settings)}
        queries = sorted(self._queries(settings), key=lambda query: query_since[query.key])
        self.searches_finished = {query.key: False for query in queries}
        returned: set[str] = set()
        for query in queries:
            seconds = int((datetime.now(timezone.utc) - query_since[query.key]).total_seconds())
            for job in self._search_pages(query, seconds):
                if job.source_id not in returned:
                    returned.add(job.source_id)
                    yield job
            self.searches_finished[query.key] = True

    def _queries(self, settings: SearchSettings) -> Iterable[_Query]:
        keywords = settings.keywords
        for i in range(0, len(keywords), TITLES_PER_SEARCH):
            titles = keywords[i : i + TITLES_PER_SEARCH]
            for center in settings.centers:
                yield _Query(titles, center)
            if settings.remote_germany:
                yield _Query(titles, None)

    def _search_pages(self, query: _Query, seconds: int) -> Iterable[FetchedJob]:
        params: dict[str, Any] = {
            "keywords": " OR ".join(f'"{title}"' for title in query.titles),
            "f_TPR": f"r{seconds}",
            "sortBy": "DD",
        }
        if query.center:
            params["location"] = query.center.name
            # LinkedIn's distance is in miles
            params["distance"] = round(query.center.radius_km / KM_PER_MILE)
        else:
            params |= {"location": "Germany", "f_WT": REMOTE}

        for start in range(0, MAX_START + 1, PAGE_SIZE):
            html = self._get(f"{BASE_URL}/seeMoreJobPostings/search", {**params, "start": start})
            cards = BeautifulSoup(html, "html.parser").select("div.base-search-card")
            for card in cards:
                job = _to_fetched_job(card)
                if job is not None:
                    job.search_key = query.key
                    job.raw["search"] = query.key
                    yield job
            if len(cards) < PAGE_SIZE:
                return
        log.warning("Search %r has more results than LinkedIn pages through", query.key)

    def _get(self, url: str, params: dict[str, Any] | None = None) -> str:
        """GET after a pause; on 429 wait longer and retry, then give up for this run.

        A redirect (to the login wall) or a block also ends LinkedIn for this run,
        so a blocked run does not spend its remaining requests. Every attempt
        counts towards the request cap.
        """
        for attempt in range(len(RATE_LIMIT_WAITS_SECONDS) + 1):
            if self.requests_left <= 0:
                raise RequestCapReached()
            self.requests_left -= 1
            if self._sent_any:
                self.sleep(random.uniform(*self.pause_seconds))
            self._sent_any = True
            response = self.client.get(url, params=params, headers=HEADERS)
            if response.is_redirect or response.status_code == BLOCKED:
                log.warning("LinkedIn blocked %s with %s", url, response.status_code)
                self._give_up()
            if response.status_code != 429:
                response.raise_for_status()
                return response.text
            if attempt < len(RATE_LIMIT_WAITS_SECONDS):
                wait = RATE_LIMIT_WAITS_SECONDS[attempt]
                log.info("LinkedIn rate-limited %s; waiting %s s", url, wait)
                self.sleep(wait)
        self._give_up()

    def _give_up(self) -> NoReturn:
        """No further request in this run, also from a search still being read."""
        self.requests_left = 0
        raise RateLimited()

    def fetch_details(self, job: FetchedJob) -> FetchedJob:
        page = BeautifulSoup(self._get(f"{BASE_URL}/jobPosting/{job.source_id}"), "html.parser")
        markup = page.select_one("div.show-more-less-html__markup")
        criteria = {
            _text(item.select_one(".description__job-criteria-subheader")): _text(
                item.select_one(".description__job-criteria-text")
            )
            for item in page.select("li.description__job-criteria-item")
        }
        employment_type = criteria.get("Employment type")
        return replace(
            job,
            description=markup.get_text("\n", strip=True) if markup else "",
            employment_type=employment_type.lower() if employment_type else None,
            raw={
                **job.raw,
                "details": {"description_html": markup.decode_contents() if markup else "", "criteria": criteria},
            },
        )


def _text(tag: Tag | None) -> str:
    return tag.get_text(" ", strip=True) if tag else ""


def _to_fetched_job(card: Tag) -> FetchedJob | None:
    urn = card.get("data-entity-urn") or ""
    if not urn.startswith("urn:li:jobPosting:"):
        return None
    link = card.select_one("a.base-card__full-link")
    url = urlunsplit(urlsplit(link["href"])._replace(query="")) if link else ""
    title = _text(card.select_one(".base-search-card__title"))
    company = _text(card.select_one(".base-search-card__subtitle"))
    location = _text(card.select_one(".job-search-card__location"))
    posted = card.select_one("time")
    return FetchedJob(
        source_id=urn.rsplit(":", 1)[1],
        title=title or "Untitled",
        company_name=company,
        url=url,
        location=location or None,
        country="DE" if location.endswith("Germany") else None,
        raw={
            "card": {
                "title": title,
                "company": company,
                "location": location,
                "posted": posted.get("datetime") if posted else None,
            }
        },
    )
