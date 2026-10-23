from dataclasses import replace
from datetime import datetime, timedelta, timezone

from app.ingestion.fetched_job import FetchedJob
from app.ingestion.run import run_ingestion
from app.ingestion.settings import Center, SearchSettings
from app.models.ingestion_run import IngestionRun

SETTINGS = SearchSettings(
    keywords=["Python"], centers=[Center(name="Testhausen", radius_km=25)]
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

    def search(self, settings, published_within_days):
        self.windows.append(published_within_days)
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
        "fetched": 2, "new": 2, "known": 0, "skipped_non_germany": 0, "detail_errors": 0,
        "failed": None,
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
