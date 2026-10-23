from dataclasses import replace
from datetime import datetime, timedelta, timezone

from app.ingestion.fetched_job import FetchedJob
from app.ingestion.run import run_ingestion
from app.ingestion.settings import Center, SearchSettings
from app.ingestion.source import RequestCapReached
from app.models.ingestion_run import IngestionRun

SETTINGS = SearchSettings(
    keywords=["Python"],
    centers=[Center(name="Testhausen", radius_km=25)],
    max_requests_per_run=30,
    max_requests_first_run=50,
)


def _job(source_id, title, company="Example Software GmbH", country="DE"):
    return FetchedJob(
        source_id=source_id,
        title=title,
        company_name=company,
        url=f"https://source.example/{source_id}",
        location="Testhausen",
        country=country,
        raw={"id": source_id},
    )


class FakeSource:
    def __init__(self, name, jobs):
        self.name = name
        self.jobs = jobs
        self.detail_calls = []
        self.windows = []
        self.caps = []

    def search(self, settings, published_within_days):
        self.windows.append(published_within_days)
        self.caps.append(settings.max_requests_per_run)
        yield from self.jobs

    def fetch_details(self, job):
        self.detail_calls.append(job.source_id)
        return replace(job, description=f"Full text of {job.title}")


class BrokenSource:
    name = "broken"

    def search(self, settings, published_within_days):
        raise RuntimeError("source is down")
        yield

    def fetch_details(self, job):
        raise AssertionError("never called")


def test_run_stores_new_jobs_with_full_text(client, session):
    source = FakeSource("fake", [_job("1", "Python Developer"), _job("2", "Data Engineer")])

    run = run_ingestion(session, SETTINGS, [source])

    jobs = client.get("/jobs").json()
    assert sorted(j["title"] for j in jobs) == ["Data Engineer", "Python Developer"]
    detail = client.get(f"/jobs/{jobs[0]['id']}").json()
    assert detail["description"] == f"Full text of {detail['title']}"
    assert [s["source"] for s in detail["sources"]] == ["fake"]
    assert run.counts["fake"] == {
        "fetched": 2, "new": 2, "reopened": 0, "known": 0, "skipped_non_germany": 0, "detail_errors": 0,
        "skipped_by_cap": 0, "capped": False, "failed": None,
    }
    assert run.finished_at is not None


def test_rerun_creates_no_duplicates_and_fetches_no_details(client, session):
    jobs = [_job("1", "Python Developer"), _job("2", "Data Engineer")]
    run_ingestion(session, SETTINGS, [FakeSource("fake", jobs)])
    second_source = FakeSource("fake", jobs)

    run = run_ingestion(session, SETTINGS, [second_source])

    assert len(client.get("/jobs").json()) == 2
    assert second_source.detail_calls == []
    assert run.counts["fake"]["known"] == 2
    assert run.counts["fake"]["new"] == 0


def test_job_known_from_another_source_gets_no_details_but_a_source_link(client, session):
    run_ingestion(session, SETTINGS, [FakeSource("first", [_job("1", "Python Developer (m/w/d)")])])
    second = FakeSource("second", [_job("abc", "Python Developer", company="Example Software")])

    run_ingestion(session, SETTINGS, [second])

    jobs = client.get("/jobs").json()
    assert len(jobs) == 1
    assert second.detail_calls == []
    sources = client.get(f"/jobs/{jobs[0]['id']}").json()["sources"]
    assert [s["source"] for s in sources] == ["first", "second"]


def test_jobs_outside_germany_are_skipped(client, session):
    source = FakeSource(
        "fake",
        [_job("1", "Python Developer"), _job("2", "Python Developer Amsterdam", country="NL")],
    )

    run = run_ingestion(session, SETTINGS, [source])

    assert [j["title"] for j in client.get("/jobs").json()] == ["Python Developer"]
    assert source.detail_calls == ["1"]
    assert run.counts["fake"]["skipped_non_germany"] == 1


def test_failing_source_is_recorded_and_does_not_stop_others(client, session):
    working = FakeSource("fake", [_job("1", "Python Developer")])

    run = run_ingestion(session, SETTINGS, [BrokenSource(), working])

    assert run.counts["broken"]["failed"] == "source is down"
    assert run.counts["fake"]["new"] == 1
    assert len(client.get("/jobs").json()) == 1


def test_job_without_location_is_skipped_unless_the_source_marks_it_german(client, session):
    unknown = replace(_job("1", "Python Developer"), location=None, country=None)
    remote = replace(_job("2", "Remote Python Developer"), location=None, country="DE")

    run = run_ingestion(session, SETTINGS, [FakeSource("fake", [unknown, remote])])

    assert [j["title"] for j in client.get("/jobs").json()] == ["Remote Python Developer"]
    assert run.counts["fake"]["skipped_non_germany"] == 1


class FlakyDetailsSource(FakeSource):
    def fetch_details(self, job):
        if job.source_id == "2":
            raise RuntimeError("detail call failed")
        return super().fetch_details(job)


def test_failed_detail_call_skips_only_that_job(client, session):
    source = FlakyDetailsSource(
        "fake", [_job("1", "Python Developer"), _job("2", "Data Engineer"), _job("3", "ML Engineer")]
    )

    run = run_ingestion(session, SETTINGS, [source])

    assert sorted(j["title"] for j in client.get("/jobs").json()) == ["ML Engineer", "Python Developer"]
    assert run.counts["fake"]["new"] == 2
    assert run.counts["fake"]["detail_errors"] == 1
    assert run.counts["fake"]["failed"] is None


def test_first_run_looks_back_seven_days(session):
    source = FakeSource("fake", [])

    run_ingestion(session, SETTINGS, [source])

    assert source.windows == [7]


def test_next_run_looks_back_from_the_last_successful_run_plus_a_day(session):
    run_ingestion(session, SETTINGS, [FakeSource("fake", [])])
    source = FakeSource("fake", [])

    run_ingestion(session, SETTINGS, [source])

    # The previous run was moments ago: at most one day, plus one day of overlap
    assert source.windows == [2]


def test_failed_run_does_not_move_the_window(session):
    class BrokenFake(BrokenSource):
        name = "fake"

    run_ingestion(session, SETTINGS, [BrokenFake()])
    source = FakeSource("fake", [])

    run_ingestion(session, SETTINGS, [source])

    assert source.windows == [7]


def test_window_is_tracked_per_source(session):
    run_ingestion(session, SETTINGS, [FakeSource("other", [])])
    source = FakeSource("fake", [])

    run_ingestion(session, SETTINGS, [source])

    assert source.windows == [7]


def test_window_counts_whole_days_since_the_last_successful_run(session):
    three_days_ago = datetime.now(timezone.utc) - timedelta(days=3, hours=2)
    session.add(
        IngestionRun(
            started_at=three_days_ago,
            finished_at=three_days_ago,
            counts={"fake": {"failed": None}},
        )
    )
    session.flush()
    source = FakeSource("fake", [])

    run_ingestion(session, SETTINGS, [source])

    # 3 days and 2 hours round up to 4, plus one day of overlap
    assert source.windows == [5]


class CappedSource(FakeSource):
    """Allows `allowed_details` detail calls, then reports the cap as reached."""

    def __init__(self, name, jobs, allowed_details, cap_during_search=False):
        super().__init__(name, jobs)
        self.allowed_details = allowed_details
        self.cap_during_search = cap_during_search

    def search(self, settings, published_within_days):
        yield from super().search(settings, published_within_days)
        if self.cap_during_search:
            raise RequestCapReached()

    def fetch_details(self, job):
        if len(self.detail_calls) >= self.allowed_details:
            raise RequestCapReached()
        return super().fetch_details(job)


def test_cap_during_details_keeps_what_was_stored_and_counts_the_rest(client, session):
    jobs = [_job(str(i), f"Job {i}") for i in range(5)]

    run = run_ingestion(session, SETTINGS, [CappedSource("fake", jobs, allowed_details=2)])

    assert len(client.get("/jobs").json()) == 2
    counts = run.counts["fake"]
    assert (counts["new"], counts["skipped_by_cap"], counts["capped"]) == (2, 3, True)
    assert counts["failed"] is None


def test_cap_during_search_keeps_the_results_found_so_far(client, session):
    jobs = [_job("1", "Job 1"), _job("2", "Job 2")]

    run = run_ingestion(
        session, SETTINGS, [CappedSource("fake", jobs, allowed_details=0, cap_during_search=True)]
    )

    counts = run.counts["fake"]
    assert (counts["fetched"], counts["new"], counts["skipped_by_cap"], counts["capped"]) == (2, 0, 2, True)


def test_known_jobs_still_count_when_the_cap_is_reached(client, session):
    run_ingestion(session, SETTINGS, [FakeSource("fake", [_job("1", "Job 1")])])

    run = run_ingestion(
        session, SETTINGS, [CappedSource("fake", [_job("1", "Job 1"), _job("2", "Job 2")], allowed_details=0)]
    )

    counts = run.counts["fake"]
    assert (counts["known"], counts["skipped_by_cap"]) == (1, 1)


def test_capped_run_does_not_move_the_window(session):
    run_ingestion(session, SETTINGS, [CappedSource("fake", [_job("1", "Job 1")], allowed_details=0)])
    source = FakeSource("fake", [])

    run_ingestion(session, SETTINGS, [source])

    assert source.windows == [7]


def test_run_with_failed_detail_calls_does_not_move_the_window(session):
    run_ingestion(session, SETTINGS, [FlakyDetailsSource("fake", [_job("2", "Job 2")])])
    source = FakeSource("fake", [])

    run_ingestion(session, SETTINGS, [source])

    assert source.windows == [7]


def test_jobs_skipped_by_the_cap_are_fetched_by_the_next_run(client, session):
    jobs = [_job(str(i), f"Job {i}") for i in range(3)]
    run_ingestion(session, SETTINGS, [CappedSource("fake", jobs, allowed_details=1)])

    run = run_ingestion(session, SETTINGS, [FakeSource("fake", jobs)])

    assert run.counts["fake"]["new"] == 2
    assert len(client.get("/jobs").json()) == 3


def test_first_run_gets_the_larger_first_run_cap(session):
    source = FakeSource("fake", [])

    run_ingestion(session, SETTINGS, [source])

    assert source.caps == [50]


def test_runs_after_a_complete_run_get_the_daily_cap(session):
    run_ingestion(session, SETTINGS, [FakeSource("fake", [])])
    source = FakeSource("fake", [])

    run_ingestion(session, SETTINGS, [source])

    assert source.caps == [30]


def test_runs_still_catching_up_keep_the_first_run_cap(session):
    run_ingestion(session, SETTINGS, [CappedSource("fake", [_job("1", "Job 1")], allowed_details=0)])
    source = FakeSource("fake", [])

    run_ingestion(session, SETTINGS, [source])

    assert source.caps == [50]


def test_window_never_grows_beyond_fourteen_days(session):
    long_ago = datetime.now(timezone.utc) - timedelta(days=30)
    session.add(IngestionRun(started_at=long_ago, finished_at=long_ago, counts={"fake": {"failed": None}}))
    session.flush()
    source = FakeSource("fake", [])

    run_ingestion(session, SETTINGS, [source])

    assert source.windows == [14]


def test_cap_reached_by_the_search_alone_is_reported(session, caplog):
    source = CappedSource("fake", [_job("1", "Job 1")], allowed_details=0, cap_during_search=True)

    with caplog.at_level("WARNING"):
        run_ingestion(session, SETTINGS, [source])

    assert "search alone" in caplog.text
