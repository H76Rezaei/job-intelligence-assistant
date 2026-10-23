import base64
import json
import logging
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
    remote_germany=True,
)
ONE_SEARCH = SearchSettings(
    keywords=["Python"], centers=[Center(name="Testhausen", radius_km=25)], remote_germany=False
)


def _search_requests(requests):
    return [r for r in requests if r.url.path.endswith("/pc/v6/jobs")]


def _adapter(requests, search=SEARCH, places=None):
    """A Bundesagentur adapter on a fake API.

    The fake reports back the place it was asked for, unless `places` maps it
    to something else (to imitate a misread place name).
    """

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if not request.url.path.endswith("/pc/v6/jobs"):
            return httpx.Response(200, json=DETAIL)
        body = search(request) if callable(search) else search
        asked = request.url.params.get("wo")
        if asked:
            reported = (places or {}).get(asked, asked)
            body = {**body, "woOutput": {"bereinigterOrt": reported, "suchmodus": "UMKREISSUCHE"}}
        else:
            body = {k: v for k, v in body.items() if k != "woOutput"}
        return httpx.Response(200, json=body)

    return Bundesagentur(httpx.Client(transport=httpx.MockTransport(handler)))


def test_search_runs_every_keyword_around_every_center_and_remote():
    requests = []

    list(_adapter(requests).search(SETTINGS, published_within_days=3))

    searches = _search_requests(requests)
    assert all(r.url.host == "rest.arbeitsagentur.de" for r in searches)
    assert all(r.headers["X-API-Key"] == "jobboerse-jobsuche" for r in searches)
    assert all(r.url.params["externestellenboersen"] == "true" for r in searches)
    assert all(r.url.params["veroeffentlichtseit"] == "3" for r in searches)
    asked = [
        (r.url.params["was"], r.url.params.get("wo"), r.url.params.get("umkreis"), r.url.params.get("homeoffice"))
        for r in searches
    ]
    assert asked == [
        ("Python", "Testhausen", "25", None),
        ("Python", "Musterstadt", "10", None),
        ("Python", None, None, "prozentual_100;nv_true"),
        ("Backend", "Testhausen", "25", None),
        ("Backend", "Musterstadt", "10", None),
        ("Backend", None, None, "prozentual_100;nv_true"),
    ]


def test_search_without_remote_switch_sends_no_remote_search():
    requests = []

    list(_adapter(requests).search(ONE_SEARCH, published_within_days=7))

    assert [r.url.params.get("wo") for r in _search_requests(requests)] == ["Testhausen"]


def test_search_pages_through_all_results():
    def page(request):
        number = int(request.url.params["page"])
        size = int(request.url.params["size"])
        first = (number - 1) * size
        results = [
            {**SEARCH["ergebnisliste"][0], "referenznummer": f"ref-{i}"}
            for i in range(first, min(first + size, 250))
        ]
        return {**SEARCH, "ergebnisliste": results, "maxErgebnisse": 250}

    requests = []
    jobs = list(_adapter(requests, search=page).search(ONE_SEARCH, published_within_days=7))

    assert len(jobs) == 250
    assert len({j.source_id for j in jobs}) == 250
    assert [r.url.params["page"] for r in _search_requests(requests)] == ["1", "2", "3"]


def test_job_found_by_several_searches_is_returned_once():
    jobs = list(_adapter([]).search(SETTINGS, published_within_days=7))

    assert [j.source_id for j in jobs] == [
        "10000-0000000001-S", "10000-0000000002-S", "10000-0000000003-S",
    ]


def test_misread_place_is_skipped_with_a_warning(caplog):
    requests = []
    adapter = _adapter(requests, places={"Musterstadt": "Mustersdorf"})

    with caplog.at_level(logging.WARNING):
        jobs = list(adapter.search(SETTINGS, published_within_days=7))

    assert len(jobs) == 3
    assert "Musterstadt" in caplog.text and "Mustersdorf" in caplog.text


def test_misread_place_alone_returns_nothing():
    jobs = list(
        _adapter([], places={"Testhausen": "Testdorf"}).search(ONE_SEARCH, published_within_days=7)
    )

    assert jobs == []


def test_remote_job_without_location_counts_as_german():
    no_location = {**SEARCH["ergebnisliste"][1], "stellenlokationen": []}
    remote_only = SearchSettings(keywords=["Python"], centers=[], remote_germany=True)

    [job] = _adapter([], search={**SEARCH, "ergebnisliste": [no_location]}).search(
        remote_only, published_within_days=7
    )

    assert job.country == "DE"
    assert job.location is None


def test_center_job_without_location_is_not_assumed_german():
    no_location = {**SEARCH["ergebnisliste"][0], "stellenlokationen": []}

    [job] = _adapter([], search={**SEARCH, "ergebnisliste": [no_location]}).search(
        ONE_SEARCH, published_within_days=7
    )

    assert job.country is None


def test_search_maps_results_to_fetched_jobs():
    jobs = list(_adapter([]).search(ONE_SEARCH, published_within_days=7))

    first, remote, foreign = jobs
    assert first.source_id == "10000-0000000001-S"
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
            {"adresse": {"ort": "Bergdorf", "land": "OESTERREICH"}},
            {"adresse": {"ort": "Musterstadt", "land": "DEUTSCHLAND"}},
        ],
    }

    [job] = _adapter([], search={**SEARCH, "ergebnisliste": [result]}).search(
        ONE_SEARCH, published_within_days=7
    )

    assert job.location == "Musterstadt"
    assert job.country == "DE"


def test_result_without_title_uses_its_job_category():
    untitled = {**SEARCH["ergebnisliste"][0], "hauptberuf": "Frontend-Entwickler/in"}
    del untitled["stellenangebotsTitel"]

    [job] = _adapter([], search={**SEARCH, "ergebnisliste": [untitled]}).search(
        ONE_SEARCH, published_within_days=7
    )

    assert job.title == "Frontend-Entwickler/in"


def test_fetch_details_adds_full_text_and_keeps_both_responses():
    requests = []
    adapter = _adapter(requests)
    [first, *_] = adapter.search(ONE_SEARCH, published_within_days=7)

    detailed = adapter.fetch_details(first)

    encoded = base64.b64encode(b"10000-0000000001-S").decode()
    assert requests[-1].url.path == f"/jobboerse/jobsuche-service/pc/v4/jobdetails/{encoded}"
    assert detailed.description.startswith("Wir suchen eine:n Python Entwickler:in.")
    assert detailed.raw["search"]["referenznummer"] == "10000-0000000001-S"
    assert detailed.raw["details"]["stellenangebotsBeschreibung"] == DETAIL["stellenangebotsBeschreibung"]


def test_place_with_a_regional_suffix_is_the_same_place():
    requests = []

    jobs = list(
        _adapter(requests, places={"Testhausen": "Testhausen, Nord"}).search(
            ONE_SEARCH, published_within_days=7
        )
    )

    assert len(jobs) == 3


def test_place_with_a_different_suffix_than_configured_is_skipped():
    settings = SearchSettings(
        keywords=["Python"], centers=[Center(name="Testhausen, Nord", radius_km=25)], remote_germany=False
    )

    jobs = list(
        _adapter([], places={"Testhausen, Nord": "Testhausen, Süd"}).search(settings, published_within_days=7)
    )

    assert jobs == []


def test_job_without_location_found_by_center_and_remote_search_is_returned_once_as_german():
    no_location = {**SEARCH["ergebnisliste"][0], "stellenlokationen": []}
    settings = SearchSettings(
        keywords=["Python"], centers=[Center(name="Testhausen", radius_km=25)], remote_germany=True
    )

    jobs = list(
        _adapter([], search={**SEARCH, "ergebnisliste": [no_location]}).search(settings, published_within_days=7)
    )

    assert [(j.source_id, j.country) for j in jobs] == [("10000-0000000001-S", "DE")]


def test_temporary_server_error_is_retried():
    calls = []

    def handler(request):
        calls.append(request)
        if len(calls) == 1:
            return httpx.Response(503)
        return httpx.Response(200, json={**SEARCH, "woOutput": {"bereinigterOrt": "Testhausen"}})

    adapter = Bundesagentur(httpx.Client(transport=httpx.MockTransport(handler)), retry_delay=0)

    jobs = list(adapter.search(ONE_SEARCH, published_within_days=7))

    assert len(jobs) == 3
    assert len(calls) == 2


def test_more_results_than_the_api_pages_through_are_logged(caplog, monkeypatch):
    import app.ingestion.sources.bundesagentur as module

    monkeypatch.setattr(module, "MAX_RESULTS", 200)

    def huge(request):
        return {**SEARCH, "maxErgebnisse": 5000}

    with caplog.at_level(logging.WARNING):
        list(_adapter([], search=huge).search(ONE_SEARCH, published_within_days=7))

    assert "5000" in caplog.text
