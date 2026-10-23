from collections.abc import Iterable
from typing import Protocol

from app.ingestion.fetched_job import FetchedJob
from app.ingestion.settings import SearchSettings


class Source(Protocol):
    """A job source. Adapters only fetch and map; they never touch the database."""

    name: str

    def search(
        self, settings: SearchSettings, published_within_days: int
    ) -> Iterable[FetchedJob]:
        """Postings published in the window, without the full text; each job once."""
        ...

    def fetch_details(self, job: FetchedJob) -> FetchedJob:
        """The same posting with its full text and the detail response in `raw`."""
        ...
