import base64
import json
from pathlib import Path

import httpx

from app.ingestion.settings import Center, SearchSettings
from app.ingestion.sources.bundesagentur import Bundesagentur
from app.models.job_posting import WorkMode

FIXTURES = Path(__file__).parent / "fixtures" / "bundesagentur"
SEARCH = json.loads((FIXTURES / "search.json").read_text(encoding="utf-8"))
DETAIL = json.loads((FIXTURES / "detail.json").read_text(encoding="utf-8"))

SETTINGS = SearchSettings(
    keywords=["Python", "Backend"],
    centers=[Center(name="Testhausen", radius_km=25), Center(name="Musterstadt", radius_km=10)],
)


def _adapter(requests, search=SEARCH):
    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path.endswith("/pc/v6/jobs"):
            return httpx.Response(200, json=search)
        return httpx.Response(200, json=DETAIL)

    return Bundesagentur(httpx.Client(transport=httpx.MockTransport(handler)))


def test_search_asks_for_the_first_keyword_around_the_first_center():
    requests = []

    list(_adapter(requests).search(SETTINGS))

    assert len(requests) == 1
    request = requests[0]
    assert request.url.host == "rest.arbeitsagentur.de"
    assert request.url.path == "/jobboerse/jobsuche-service/pc/v6/jobs"
    assert request.headers["X-API-Key"] == "jobboerse-jobsuche"
    assert request.url.params["was"] == "Python"
    assert request.url.params["wo"] == "Testhausen"
    assert request.url.params["umkreis"] == "25"
    assert request.url.params["veroeffentlichtseit"] == "7"


def test_search_maps_results_to_fetched_jobs():
    jobs = list(_adapter([]).search(SETTINGS))

    assert [j.source_id for j in jobs] == [
        "10000-0000000001-S", "10000-0000000002-S", "10000-0000000003-S",
    ]
    first, remote, foreign = jobs
    assert first.title == "Python Entwickler (m/w/d)"
    assert first.company_name == "Beispiel Software GmbH"
    assert first.location == "Testhausen"
    assert first.country == "DE"
    assert first.work_mode == WorkMode.HYBRID
    assert first.employment_type == "full-time"
    assert first.url == "https://www.arbeitsagentur.de/jobsuche/jobdetail/10000-0000000001-S"
    assert first.description == ""
    assert remote.work_mode == WorkMode.REMOTE
    assert remote.employment_type == "part-time"
    assert foreign.country != "DE"
    assert foreign.work_mode == WorkMode.ONSITE


def test_location_is_the_first_german_one():
    result = {
        **SEARCH["ergebnisliste"][0],
        "stellenlokationen": [
            {"adresse": {"ort": "Wien", "land": "OESTERREICH"}},
            {"adresse": {"ort": "Musterstadt", "land": "DEUTSCHLAND"}},
        ],
    }

    [job] = _adapter([], search={**SEARCH, "ergebnisliste": [result]}).search(SETTINGS)

    assert job.location == "Musterstadt"
    assert job.country == "DE"


def test_fetch_details_adds_full_text_and_keeps_both_responses():
    requests = []
    adapter = _adapter(requests)
    [first, *_] = adapter.search(SETTINGS)

    detailed = adapter.fetch_details(first)

    encoded = base64.b64encode(b"10000-0000000001-S").decode()
    assert requests[-1].url.path == f"/jobboerse/jobsuche-service/pc/v4/jobdetails/{encoded}"
    assert detailed.description.startswith("Wir suchen eine:n Python Entwickler:in.")
    assert detailed.raw["search"]["referenznummer"] == "10000-0000000001-S"
    assert detailed.raw["details"]["stellenangebotsBeschreibung"] == DETAIL["stellenangebotsBeschreibung"]


def test_result_without_title_uses_its_job_category():
    untitled = {**SEARCH["ergebnisliste"][0], "hauptberuf": "Frontend-Entwickler/in"}
    del untitled["stellenangebotsTitel"]

    [job] = _adapter([], search={**SEARCH, "ergebnisliste": [untitled]}).search(SETTINGS)

    assert job.title == "Frontend-Entwickler/in"
