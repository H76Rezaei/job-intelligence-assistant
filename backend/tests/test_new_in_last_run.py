from dataclasses import replace

from app.ingestion.fetched_job import FetchedJob
from app.ingestion.run import run_ingestion
from app.ingestion.settings import Center, SearchSettings

PASTED = {
    "title": "Pasted Job",
    "company_name": "Other Company AG",
    "url": "https://other.example/1",
    "description": "Text",
}
SETTINGS = SearchSettings(keywords=["Python"], centers=[Center(name="Testhausen", radius_km=25)])


class FakeSource:
    name = "fake"

    def __init__(self, *titles):
        self.titles = titles

    def search(self, settings, published_within_days):
        for title in self.titles:
            yield FetchedJob(
                source_id=title,
                title=title,
                company_name="Example Software GmbH",
                url=f"https://source.example/{title}",
                country="DE",
            )

    def fetch_details(self, job):
        return replace(job, description=f"Full text of {job.title}")


def _new_titles(jobs):
    return sorted(j["title"] for j in jobs if j["is_new"])


def test_jobs_from_the_latest_run_are_new(client, session):
    run_ingestion(session, SETTINGS, [FakeSource("Python Developer", "Data Engineer")])

    assert _new_titles(client.get("/jobs").json()) == ["Data Engineer", "Python Developer"]


def test_only_jobs_first_found_in_the_latest_run_stay_new(client, session):
    run_ingestion(session, SETTINGS, [FakeSource("Python Developer", "Data Engineer")])
    run_ingestion(session, SETTINGS, [FakeSource("Python Developer", "Data Engineer", "ML Engineer")])

    jobs = client.get("/jobs").json()
    assert len(jobs) == 3
    assert _new_titles(jobs) == ["ML Engineer"]

    only_new = client.get("/jobs", params={"new_in_last_run": True}).json()
    assert [j["title"] for j in only_new] == ["ML Engineer"]


def test_run_without_new_jobs_leaves_nothing_new(client, session):
    run_ingestion(session, SETTINGS, [FakeSource("Python Developer")])
    run_ingestion(session, SETTINGS, [FakeSource("Python Developer")])

    assert _new_titles(client.get("/jobs").json()) == []
    assert client.get("/jobs", params={"new_in_last_run": True}).json() == []


def test_pasted_jobs_are_not_new(client, session):
    run_ingestion(session, SETTINGS, [FakeSource("Python Developer")])
    client.post("/jobs", json=PASTED)

    jobs = client.get("/jobs").json()
    assert _new_titles(jobs) == ["Python Developer"]
    only_new = client.get("/jobs", params={"new_in_last_run": True}).json()
    assert [j["title"] for j in only_new] == ["Python Developer"]


def test_without_any_run_nothing_is_new(client):
    client.post("/jobs", json=PASTED)

    assert _new_titles(client.get("/jobs").json()) == []
    assert client.get("/jobs", params={"new_in_last_run": True}).json() == []


def test_job_detail_also_says_whether_it_is_new(client, session):
    run_ingestion(session, SETTINGS, [FakeSource("Python Developer")])
    [job] = client.get("/jobs").json()

    assert client.get(f"/jobs/{job['id']}").json()["is_new"] is True


class BrokenSource(FakeSource):
    def search(self, settings, published_within_days):
        raise RuntimeError("source is down")


def test_after_a_run_where_every_source_failed_nothing_is_new(client, session):
    run_ingestion(session, SETTINGS, [FakeSource("Python Developer")])
    run_ingestion(session, SETTINGS, [BrokenSource()])

    assert _new_titles(client.get("/jobs").json()) == []
