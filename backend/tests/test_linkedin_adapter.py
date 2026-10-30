from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
import pytest

from app.ingestion.run import run_ingestion
from app.ingestion.settings import Center, LinkedInSettings, SearchSettings
from app.ingestion.source import NetworkDown, RateLimited, RequestCapReached
from app.ingestion.sources.linkedin import LinkedIn

FIXTURES = Path(__file__).parent / "fixtures" / "linkedin"
CARD = (FIXTURES / "card.html").read_text(encoding="utf-8")
DETAIL = (FIXTURES / "detail.html").read_text(encoding="utf-8")

ONE_SEARCH = SearchSettings(
    keywords=["Python Developer"], centers=[Center(name="Testhausen", radius_km=40)], remote_germany=False
)


def _card(id_, title="Python Developer (m/w/d)", company="Example Software GmbH",
          location="Testhausen, North Rhine-Westphalia, Germany"):
    return CARD.format(id=id_, title=title, company=company, location=location)


def _capped(settings, cap):
    return replace(settings, linkedin=LinkedInSettings(max_requests_per_run=cap))


def _since(days):
    return datetime.now(timezone.utc) - timedelta(days=days)


def _search_requests(requests):
    return [r for r in requests if r.url.path.endswith("/seeMoreJobPostings/search")]


def _adapter(requests, pages=None, detail=DETAIL, responses=None):
    """A LinkedIn adapter on a fake site, without pauses.

    `pages(request)` returns the cards for a search request (default: one card).
    `responses` is a list of responses served first, in order, for any request.
    """
    queued = list(responses or [])

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if queued:
            return queued.pop(0)
        if request.url.path.endswith("/seeMoreJobPostings/search"):
            cards = pages(request) if pages else [_card("4000000001")]
            return httpx.Response(200, text="".join(cards))
        return httpx.Response(200, text=detail)

    return LinkedIn(httpx.Client(transport=httpx.MockTransport(handler)), sleep=lambda seconds: None)


def test_search_maps_cards_to_fetched_jobs():
    [job] = _adapter([]).search(ONE_SEARCH, since=_since(1))

    assert job.source_id == "4000000001"
    assert job.title == "Python Developer (m/w/d)"
    assert job.company_name == "Example Software GmbH"
    assert job.location == "Testhausen, North Rhine-Westphalia, Germany"
    assert job.country == "DE"
    assert job.url == "https://de.linkedin.com/jobs/view/example-job-at-example-company-4000000001"
    assert job.raw["card"]["posted"] == "2026-10-22"


def test_job_outside_germany_has_no_country():
    def pages(request):
        return [_card("1", location="Wien, Vienna, Austria")]

    [job] = _adapter([], pages=pages).search(ONE_SEARCH, since=_since(1))

    assert job.country is None


def test_fetch_details_adds_full_text_and_employment_type():
    adapter = _adapter([])
    [job] = adapter.search(ONE_SEARCH, since=_since(1))

    detailed = adapter.fetch_details(job)

    assert detailed.description.startswith("Was dich erwartet")
    assert "Du entwickelst Backend-Dienste mit Python." in detailed.description
    assert detailed.employment_type == "full-time"
    assert detailed.raw["details"]["criteria"]["Seniority level"] == "Associate"
    assert "<ul>" in detailed.raw["details"]["description_html"]
    assert detailed.raw["card"]["title"] == "Python Developer (m/w/d)"


def test_titles_are_grouped_and_searched_around_every_center_and_remote():
    titles = [f"Title {i}" for i in range(10)]
    settings = SearchSettings(
        keywords=titles,
        centers=[Center(name="Testhausen", radius_km=40), Center(name="Musterstadt", radius_km=16)],
        remote_germany=True,
    )
    requests = []

    list(_adapter(requests).search(settings, since=_since(2)))

    asked = [
        (r.url.params["keywords"], r.url.params["location"], r.url.params.get("distance"), r.url.params.get("f_WT"))
        for r in _search_requests(requests)
    ]
    first = " OR ".join(f'"Title {i}"' for i in range(8))
    second = '"Title 8" OR "Title 9"'
    assert asked == [
        (first, "Testhausen", "25", None),
        (first, "Musterstadt", "10", None),
        (first, "Germany", None, "2"),
        (second, "Testhausen", "25", None),
        (second, "Musterstadt", "10", None),
        (second, "Germany", None, "2"),
    ]


def test_linkedin_titles_replace_the_shared_titles_when_set():
    settings = replace(ONE_SEARCH, linkedin=LinkedInSettings(keywords=["AI Engineer"]))
    requests = []

    list(_adapter(requests).search(settings, since=_since(1)))

    [search] = _search_requests(requests)
    assert search.url.params["keywords"] == '"AI Engineer"'


def test_search_asks_for_the_newest_jobs_since_the_window_start():
    requests = []

    list(_adapter(requests).search(ONE_SEARCH, since=_since(2)))

    [search] = _search_requests(requests)
    assert search.url.host == "www.linkedin.com"
    assert search.headers["Accept-Language"].startswith("en")
    assert search.url.params["sortBy"] == "DD"
    assert search.url.params["start"] == "0"
    seconds = int(search.url.params["f_TPR"].removeprefix("r"))
    assert 2 * 86400 - 5 <= seconds <= 2 * 86400


def test_search_pages_until_a_page_is_not_full():
    def pages(request):
        start = int(request.url.params["start"])
        count = 10 if start < 20 else 3
        return [_card(str(start + i)) for i in range(count)]
    requests = []

    jobs = list(_adapter(requests, pages=pages).search(ONE_SEARCH, since=_since(1)))

    assert [r.url.params["start"] for r in _search_requests(requests)] == ["0", "10", "20"]
    assert len(jobs) == 23


def test_job_found_by_several_searches_is_returned_once():
    settings = replace(ONE_SEARCH, remote_germany=True)

    jobs = list(_adapter([]).search(settings, since=_since(1)))

    assert [j.source_id for j in jobs] == ["4000000001"]
    assert jobs[0].search_key == jobs[0].raw["search"] == "Python Developer @ Testhausen"


def test_every_request_after_the_first_waits_a_random_pause():
    pauses = []
    adapter = _adapter([])
    adapter.sleep = pauses.append
    settings = replace(ONE_SEARCH, remote_germany=True)

    [job] = adapter.search(settings, since=_since(1))
    adapter.fetch_details(job)

    assert len(pauses) == 2
    assert all(20 <= p <= 30 for p in pauses)


def test_search_stops_at_the_cap_and_keeps_what_it_found():
    settings = _capped(replace(ONE_SEARCH, remote_germany=True), 1)
    requests = []
    adapter = _adapter(requests)
    found = []

    with pytest.raises(RequestCapReached):
        for job in adapter.search(settings, since=_since(1)):
            found.append(job)

    assert len(requests) == 1
    assert [j.source_id for j in found] == ["4000000001"]


def test_detail_calls_count_towards_the_cap():
    adapter = _adapter([])
    [job] = adapter.search(_capped(ONE_SEARCH, 2), since=_since(1))
    adapter.fetch_details(job)

    with pytest.raises(RequestCapReached):
        adapter.fetch_details(job)


def test_rate_limit_waits_five_then_fifteen_minutes_before_retrying():
    waits = []
    requests = []
    adapter = _adapter(requests, responses=[httpx.Response(429), httpx.Response(429)])
    adapter.sleep = waits.append

    jobs = list(adapter.search(ONE_SEARCH, since=_since(1)))

    assert len(jobs) == 1
    assert len(requests) == 3
    assert [w for w in waits if w > 30] == [300, 900]


def test_third_rate_limit_in_a_row_stops_the_source_for_this_run():
    adapter = _adapter([], responses=[httpx.Response(429)] * 3)

    with pytest.raises(RateLimited):
        list(adapter.search(ONE_SEARCH, since=_since(1)))


def test_retries_count_towards_the_cap():
    requests = []
    adapter = _adapter(requests, responses=[httpx.Response(429)])

    with pytest.raises(RequestCapReached):
        list(adapter.search(_capped(replace(ONE_SEARCH, remote_germany=True), 2), since=_since(1)))

    assert len(requests) == 2


def test_login_wall_stops_the_source_for_this_run():
    wall = httpx.Response(302, headers={"Location": "https://www.linkedin.com/authwall"})

    with pytest.raises(RateLimited):
        list(_adapter([], responses=[wall]).search(ONE_SEARCH, since=_since(1)))


def test_block_during_details_stops_the_source_instead_of_trying_every_job():
    adapter = _adapter([])
    [job] = adapter.search(ONE_SEARCH, since=_since(1))
    adapter.client = httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(999)))

    with pytest.raises(RateLimited):
        adapter.fetch_details(job)


def _no_network(request):
    raise httpx.ConnectError("getaddrinfo failed")


def test_network_error_stops_the_source_for_this_run_without_a_retry():
    requests = []

    def handler(request):
        requests.append(request)
        _no_network(request)

    adapter = LinkedIn(httpx.Client(transport=httpx.MockTransport(handler)), sleep=lambda seconds: None)

    with pytest.raises(NetworkDown):
        list(adapter.search(ONE_SEARCH, since=_since(1)))

    assert len(requests) == 1


def test_network_error_during_details_ends_the_searches_too():
    requests = []
    adapter = _adapter(requests)
    found = adapter.search(replace(ONE_SEARCH, remote_germany=True), _since(7), windows={})
    job = next(found)
    adapter.client = httpx.Client(transport=httpx.MockTransport(_no_network))

    with pytest.raises(NetworkDown):
        adapter.fetch_details(job)
    with pytest.raises(RequestCapReached):
        list(found)

    assert len(requests) == 1


def test_other_unexpected_answer_fails_the_request():
    with pytest.raises(httpx.HTTPStatusError):
        list(_adapter([], responses=[httpx.Response(500)]).search(ONE_SEARCH, since=_since(1)))


TWO_SEARCHES = replace(ONE_SEARCH, remote_germany=True)
CENTER_KEY = "Python Developer @ Testhausen"
REMOTE_KEY = "Python Developer @ remote"


def _window(request):
    return int(request.url.params["f_TPR"].removeprefix("r")) / 86400


def test_each_search_uses_its_own_window_and_new_ones_the_default():
    requests = []

    list(_adapter(requests).search(TWO_SEARCHES, _since(7), windows={CENTER_KEY: _since(1)}))

    assert [round(_window(r)) for r in _search_requests(requests)] == [7, 1]


def test_searches_waiting_longest_go_first():
    requests = []
    windows = {CENTER_KEY: _since(1), REMOTE_KEY: _since(3)}

    list(_adapter(requests).search(TWO_SEARCHES, _since(7), windows=windows))

    assert [r.url.params["location"] for r in _search_requests(requests)] == ["Germany", "Testhausen"]


def test_searches_report_whether_they_were_read_to_the_end():
    adapter = _adapter([])

    with pytest.raises(RequestCapReached):
        list(adapter.search(_capped(TWO_SEARCHES, 1), _since(7), windows={}))

    assert adapter.searches_finished == {CENTER_KEY: True, REMOTE_KEY: False}


def test_network_drop_through_run_ingestion_keeps_the_stored_job_and_both_searches_wait(client, session):
    details = []

    def handler(request):
        if request.url.path.endswith("/seeMoreJobPostings/search"):
            return httpx.Response(200, text=_card("1", title="Python Developer") + _card("2", title="Data Engineer"))
        details.append(request)
        if len(details) > 1:
            _no_network(request)
        return httpx.Response(200, text=DETAIL)

    adapter = LinkedIn(httpx.Client(transport=httpx.MockTransport(handler)), sleep=lambda seconds: None)

    counts = run_ingestion(session, TWO_SEARCHES, [adapter]).counts["linkedin"]

    assert counts["failed"] is None
    assert (counts["new"], counts["skipped_by_cap"], counts["detail_errors"]) == (1, 1, 0)
    assert (counts["capped"], counts["network_error"], counts["rate_limited"]) == (True, True, False)
    assert counts["searches_waiting"] == 2
    assert [j["title"] for j in client.get("/jobs").json()] == ["Python Developer"]


def test_block_during_details_ends_the_searches_too():
    requests = []
    adapter = _adapter(requests)
    found = adapter.search(TWO_SEARCHES, _since(7), windows={})
    job = next(found)
    adapter.client = httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(999)))

    with pytest.raises(RateLimited):
        adapter.fetch_details(job)
    with pytest.raises(RequestCapReached):
        list(found)

    assert len(requests) == 1


def _timed_adapter(requests, pages, limit_minutes=5):
    """A LinkedIn adapter whose clock moves only with its pauses, 60 seconds each."""
    now = [0.0]

    def pause(seconds):
        now[0] += seconds

    def handler(request):
        requests.append(request)
        if request.url.path.endswith("/seeMoreJobPostings/search"):
            return httpx.Response(200, text="".join(pages(request)))
        return httpx.Response(200, text=DETAIL)

    adapter = LinkedIn(
        httpx.Client(transport=httpx.MockTransport(handler)), sleep=pause, clock=lambda: now[0]
    )
    settings = replace(
        TWO_SEARCHES, linkedin=LinkedInSettings(pause_seconds=(60, 60), max_minutes_per_search=limit_minutes)
    )
    return adapter, settings


def _endless_center_search(request):
    """A full page for every request of the center search; one job in the remote search."""
    if request.url.params["location"] == "Germany":
        return [_card("remote-1", title="Remote Job")]
    start = int(request.url.params["start"])
    return [_card(f"{start + i}", title=f"Job {start + i}") for i in range(10)]


def test_search_over_its_time_limit_stops_and_the_next_search_gets_its_turn():
    requests = []
    adapter, settings = _timed_adapter(requests, _endless_center_search)

    jobs = list(adapter.search(settings, _since(7), windows={}))

    center_pages = [r for r in _search_requests(requests) if r.url.params["location"] == "Testhausen"]
    assert len(center_pages) == 6
    assert "remote-1" in [j.source_id for j in jobs]
    assert adapter.searches_finished == {CENTER_KEY: False, REMOTE_KEY: True}


def test_time_for_details_counts_towards_the_search_limit():
    requests = []
    adapter, settings = _timed_adapter(requests, _endless_center_search, limit_minutes=3)
    handled = []

    for job in adapter.search(settings, _since(7), windows={}):
        adapter.fetch_details(job)
        handled.append(job.source_id)

    assert handled == ["0", "1", "2", "remote-1"]
    assert adapter.searches_finished == {CENTER_KEY: False, REMOTE_KEY: True}


def test_search_stopped_by_the_time_limit_keeps_its_window_and_the_others_move_on(session):
    adapter, settings = _timed_adapter([], _endless_center_search)

    counts = run_ingestion(session, settings, [adapter]).counts["linkedin"]

    assert counts["failed"] is None
    assert counts["capped"] is False
    assert counts["searches_waiting"] == 1
    assert datetime.fromisoformat(counts["search_since"][CENTER_KEY]) < _since(6)
    assert datetime.fromisoformat(counts["search_since"][REMOTE_KEY]) > _since(1)
