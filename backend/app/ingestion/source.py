from collections.abc import Iterable
from datetime import datetime
from typing import Protocol

from app.ingestion.fetched_job import FetchedJob
from app.ingestion.settings import SearchSettings


class RequestCapReached(Exception):
    """The source stops sending requests for this run: it used up its request cap."""


class RateLimited(RequestCapReached):
    """The site refuses further requests (rate limit or block); handled like the cap."""


class Source(Protocol):
    """A job source. Adapters only fetch and map; they never touch the database.

    Every request in a run counts towards `settings.max_requests_per_run`,
    retries included; `search` starts a fresh allowance for the run, and
    `search` or `fetch_details` raise RequestCapReached once it is used up.
    """

    name: str

    def search(self, settings: SearchSettings, since: datetime) -> Iterable[FetchedJob]:
        """Postings published since `since`, without the full text; each job once."""
        ...

    def fetch_details(self, job: FetchedJob) -> FetchedJob:
        """The same posting with its full text and the detail response in `raw`."""
        ...
