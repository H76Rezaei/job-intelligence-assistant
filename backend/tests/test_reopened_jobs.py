from dataclasses import replace
from datetime import datetime, timedelta, timezone

from sqlalchemy import update

from app.ingestion.fetched_job import FetchedJob
from app.ingestion.run import run_ingestion
from app.ingestion.settings import Center, SearchSettings
from app.ingestion.source import RequestCapReached
from app.models.job_posting import JobPosting

SETTINGS = SearchSettings(
    keywords=["Python"], centers=[Center(name="Testhausen", radius_km=25)], reopen_after_days=60
)


class FakeSource:
    name = "fake"

    def __init__(self, text="First text", cap_details=False):
        self.text = text
        self.cap_details = cap_details
        self.detail_calls = 0

    def search(self, settings, published_within_days):
        yield FetchedJob(
            source_id="1",
            title="Python Developer",
            company_name="Example Software GmbH",
            url="https://source.example/1",
            country="DE",
        )

    def fetch_details(self, job):
        if self.cap_details:
            raise RequestCapReached()
        self.detail_calls += 1
        return replace(job, description=self.text)


def _last_seen(session, days_ago):
    session.execute(
        update(JobPosting).values(last_seen_at=datetime.now(timezone.utc) - timedelta(days=days_ago))
    )
    session.flush()


def _only_job(client):
    [job] = client.get("/jobs").json()
    return client.get(f"/jobs/{job['id']}").json()


def test_job_unseen_for_longer_than_the_window_is_reopened(client, session):
    run_ingestion(session, SETTINGS, [FakeSource()])
    run_ingestion(session, SETTINGS, [FakeSource()])  # nothing new in this run
    _last_seen(session, 61)
    source = FakeSource(text="Second text")

    run = run_ingestion(session, SETTINGS, [source])

    assert source.detail_calls == 1
    assert run.counts["fake"]["reopened"] == 1
    assert run.counts["fake"]["known"] == 0
    job = _only_job(client)
    assert job["is_new"] is True
    assert job["description"] == "Second text"


def test_job_seen_within_the_window_is_only_known(client, session):
    run_ingestion(session, SETTINGS, [FakeSource()])
    _last_seen(session, 59)
    source = FakeSource()

    run = run_ingestion(session, SETTINGS, [source])

    assert source.detail_calls == 0
    assert (run.counts["fake"]["known"], run.counts["fake"]["reopened"]) == (1, 0)
    assert _only_job(client)["is_new"] is False


def test_reopen_window_comes_from_the_settings(client, session):
    run_ingestion(session, SETTINGS, [FakeSource()])
    _last_seen(session, 6)
    source = FakeSource()

    run = run_ingestion(session, replace(SETTINGS, reopen_after_days=5), [source])

    assert run.counts["fake"]["reopened"] == 1


def test_reopened_job_with_unchanged_text_is_new_without_a_new_version(client, session):
    run_ingestion(session, SETTINGS, [FakeSource()])
    first_captured = _only_job(client)["captured_at"]
    _last_seen(session, 61)

    run_ingestion(session, SETTINGS, [FakeSource()])

    job = _only_job(client)
    assert job["is_new"] is True
    assert job["captured_at"] == first_captured


def test_application_stays_on_the_version_it_was_made_for(client, session):
    run_ingestion(session, SETTINGS, [FakeSource()])
    job_id = client.get("/jobs").json()[0]["id"]
    application = client.post("/applications", json={"job_posting_id": job_id}).json()
    _last_seen(session, 61)

    run_ingestion(session, SETTINGS, [FakeSource(text="Second text")])

    assert _only_job(client)["description"] == "Second text"
    pinned = client.get(f"/applications/{application['id']}").json()
    assert pinned["snapshot_id"] == application["snapshot_id"]


def test_reopened_job_waits_for_the_next_run_when_the_cap_is_reached(client, session):
    run_ingestion(session, SETTINGS, [FakeSource()])
    _last_seen(session, 61)

    run = run_ingestion(session, SETTINGS, [FakeSource(cap_details=True)])

    counts = run.counts["fake"]
    assert (counts["reopened"], counts["skipped_by_cap"], counts["capped"]) == (0, 1, True)
    assert _only_job(client)["is_new"] is False


class FailingDetailsSource(FakeSource):
    def fetch_details(self, job):
        raise RuntimeError("detail call failed")


def test_reopened_job_whose_details_fail_is_reopened_by_the_next_run(client, session):
    run_ingestion(session, SETTINGS, [FakeSource()])
    _last_seen(session, 61)
    failed = run_ingestion(session, SETTINGS, [FailingDetailsSource()])

    run = run_ingestion(session, SETTINGS, [FakeSource(text="Second text")])

    assert failed.counts["fake"]["detail_errors"] == 1
    assert run.counts["fake"]["reopened"] == 1
    assert _only_job(client)["description"] == "Second text"


def test_job_seen_again_by_a_second_source_in_the_same_run_is_not_marked_new(client, session):
    run_ingestion(session, SETTINGS, [FakeSource()])
    run_ingestion(session, SETTINGS, [FakeSource()])

    class OtherSource(FakeSource):
        name = "other"

    run_ingestion(session, SETTINGS, [OtherSource()])

    job = _only_job(client)
    assert job["is_new"] is False
    assert [s["source"] for s in job["sources"]] == ["fake", "other"]
