"""Bundesagentur für Arbeit job search.

The API is unofficial and renamed its fields in Aug 2026 (checked 23 Oct 2026),
so all field names live in this module.
"""

import base64
from collections.abc import Iterable
from dataclasses import replace
from typing import Any

import httpx

from app.ingestion.fetched_job import FetchedJob
from app.ingestion.settings import SearchSettings
from app.models.job_posting import WorkMode

BASE_URL = "https://rest.arbeitsagentur.de/jobboerse/jobsuche-service"
HEADERS = {"X-API-Key": "jobboerse-jobsuche"}
JOB_PAGE_URL = "https://www.arbeitsagentur.de/jobsuche/jobdetail/{}"


class Bundesagentur:
    name = "bundesagentur"

    def __init__(self, client: httpx.Client | None = None):
        self.client = client or httpx.Client(timeout=30)

    def search(self, settings: SearchSettings) -> Iterable[FetchedJob]:
        # Ticket 02: the first keyword around the first center only
        center = settings.centers[0]
        response = self.client.get(
            f"{BASE_URL}/pc/v6/jobs",
            headers=HEADERS,
            params={
                "was": settings.keywords[0],
                "wo": center.name,
                "umkreis": center.radius_km,
                "veroeffentlichtseit": 7,
                "page": 1,
                "size": 100,
            },
        )
        response.raise_for_status()
        for result in response.json().get("ergebnisliste", []):
            yield _to_fetched_job(result)

    def fetch_details(self, job: FetchedJob) -> FetchedJob:
        encoded = base64.b64encode(job.source_id.encode()).decode()
        response = self.client.get(f"{BASE_URL}/pc/v4/jobdetails/{encoded}", headers=HEADERS)
        response.raise_for_status()
        details = response.json()
        return replace(
            job,
            description=details.get("stellenangebotsBeschreibung") or "",
            raw={**job.raw, "details": details},
        )


def _to_fetched_job(result: dict[str, Any]) -> FetchedJob:
    location, country = _location(result.get("stellenlokationen") or [])
    return FetchedJob(
        source_id=result["referenznummer"],
        title=result["stellenangebotsTitel"],
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
