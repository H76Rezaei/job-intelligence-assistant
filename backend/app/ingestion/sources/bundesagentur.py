"""Bundesagentur für Arbeit job search.

The API is unofficial and renamed its fields in Aug 2026 (checked 23 Oct 2026),
so all field names live in this module.
"""

import base64
import logging
import time
from collections.abc import Iterable
from dataclasses import dataclass, replace
from typing import Any

import httpx

from app.ingestion.fetched_job import FetchedJob
from app.ingestion.settings import Center, SearchSettings
from app.models.job_posting import WorkMode

BASE_URL = "https://rest.arbeitsagentur.de/jobboerse/jobsuche-service"
HEADERS = {"X-API-Key": "jobboerse-jobsuche"}
JOB_PAGE_URL = "https://www.arbeitsagentur.de/jobsuche/jobdetail/{}"
# Fully remote jobs plus "home office by arrangement"
REMOTE_ONLY = "prozentual_100;nv_true"
PAGE_SIZE = 100
# The API refuses to page beyond 10,000 results
MAX_RESULTS = 10_000

log = logging.getLogger(__name__)


def _reported_place(body: dict[str, Any]) -> str:
    return (body.get("woOutput") or {}).get("bereinigterOrt") or ""


def _same_place(asked: str, reported: str) -> bool:
    """The API silently replaces place names it misreads with another town.

    A name configured without a suffix also matches the API's name with a
    regional suffix ("Musterstadt" and "Musterstadt, Nord"). A configured
    suffix must match exactly.
    """
    asked, reported = asked.casefold().strip(), reported.casefold().strip()
    if "," in asked:
        return asked == reported
    return reported.split(",")[0].strip() == asked


@dataclass
class _Query:
    keyword: str
    center: Center | None  # None: the remote search across Germany


class Bundesagentur:
    name = "bundesagentur"

    def __init__(self, client: httpx.Client | None = None, retry_delay: float = 2.0):
        self.client = client or httpx.Client(timeout=30)
        self.retry_delay = retry_delay

    def search(
        self, settings: SearchSettings, published_within_days: int
    ) -> Iterable[FetchedJob]:
        """Every keyword around every center, plus remote jobs in all of Germany.

        Each job is returned once. Jobs without a known country wait until all
        searches are done, in case the remote search shows they are in Germany.
        """
        returned: set[str] = set()
        unknown_country: dict[str, FetchedJob] = {}
        for query in self._queries(settings):
            for job in self._search_pages(query, published_within_days):
                if job.source_id in returned:
                    continue
                if job.country is None:
                    unknown_country.setdefault(job.source_id, job)
                    continue
                unknown_country.pop(job.source_id, None)
                returned.add(job.source_id)
                yield job
        yield from unknown_country.values()

    def _queries(self, settings: SearchSettings) -> Iterable[_Query]:
        for keyword in settings.keywords:
            for center in settings.centers:
                yield _Query(keyword, center)
            if settings.remote_germany:
                yield _Query(keyword, None)

    def _search_pages(self, query: _Query, published_within_days: int) -> Iterable[FetchedJob]:
        params: dict[str, Any] = {
            "was": query.keyword,
            "veroeffentlichtseit": published_within_days,
            "externestellenboersen": "true",
        }
        if query.center:
            params |= {"wo": query.center.name, "umkreis": query.center.radius_km}
        else:
            params["homeoffice"] = REMOTE_ONLY

        for page in range(1, MAX_RESULTS // PAGE_SIZE + 1):
            body = self._get(
                f"{BASE_URL}/pc/v6/jobs", params={**params, "page": page, "size": PAGE_SIZE}
            )
            if page == 1 and query.center:
                reported = _reported_place(body)
                if not _same_place(query.center.name, reported):
                    log.warning(
                        "Skipped search for %r: the Bundesagentur searched %r instead of %r",
                        query.keyword, reported, query.center.name,
                    )
                    return
            results = body.get("ergebnisliste") or []
            for result in results:
                job = _to_fetched_job(result)
                # The remote search covers only Germany, so a job without a location is German
                if query.center is None and not result.get("stellenlokationen"):
                    job.country = "DE"
                yield job
            total = body.get("maxErgebnisse", 0)
            if not results or page * PAGE_SIZE >= total:
                return
        log.warning(
            "Search for %r found %s results; only the first %s can be fetched",
            query.keyword, total, MAX_RESULTS,
        )

    def _get(self, url: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """GET with two retries for connection problems and server errors."""
        for attempt in range(3):
            try:
                response = self.client.get(url, headers=HEADERS, params=params)
                if response.status_code < 500:
                    response.raise_for_status()
                    return response.json()
                error: Exception = httpx.HTTPStatusError(
                    f"Server error {response.status_code}", request=response.request, response=response
                )
            except httpx.TransportError as transport_error:
                error = transport_error
            if attempt < 2:
                log.info("Retrying %s after: %s", url, error)
                time.sleep(self.retry_delay)
        raise error

    def fetch_details(self, job: FetchedJob) -> FetchedJob:
        encoded = base64.b64encode(job.source_id.encode()).decode()
        details = self._get(f"{BASE_URL}/pc/v4/jobdetails/{encoded}")
        return replace(
            job,
            description=details.get("stellenangebotsBeschreibung") or "",
            raw={**job.raw, "details": details},
        )


def _to_fetched_job(result: dict[str, Any]) -> FetchedJob:
    location, country = _location(result.get("stellenlokationen") or [])
    return FetchedJob(
        source_id=result["referenznummer"],
        # A few postings have no title; their job category is the closest stand-in
        title=result.get("stellenangebotsTitel") or result.get("hauptberuf") or "Untitled",
        company_name=result["firma"],
        url=JOB_PAGE_URL.format(result["referenznummer"]),
        location=location,
        country=country,
        employment_type=_employment_type(result),
        work_mode=_work_mode(result),
        raw={"search": result},
    )


def _location(locations: list[dict[str, Any]]) -> tuple[str | None, str | None]:
    """The first German location; otherwise the first location's country."""
    addresses = [loc.get("adresse") or {} for loc in locations]
    for address in addresses:
        if address.get("land") == "DEUTSCHLAND":
            return address.get("ort"), "DE"
    if addresses:
        return addresses[0].get("ort"), addresses[0].get("land")
    return None, None


def _work_mode(result: dict[str, Any]) -> WorkMode:
    if result.get("homeofficeprozent") == 100:
        return WorkMode.REMOTE
    if result.get("homeofficemoeglich"):
        return WorkMode.HYBRID
    return WorkMode.ONSITE


def _employment_type(result: dict[str, Any]) -> str | None:
    if result.get("arbeitszeitVollzeit"):
        return "full-time"
    if any(v is True for k, v in result.items() if k.startswith("arbeitszeitTeilzeit")):
        return "part-time"
    return None
