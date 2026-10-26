import importlib.util
from pathlib import Path

from sqlalchemy import func, select

from app.ingestion.fetched_job import FetchedJob
from app.ingestion.storage import store_job
from app.models.job_posting_snapshot import JobPostingSnapshot
from app.models.job_posting_source import JobPostingSource

MIGRATION = Path(__file__).parents[1] / "alembic" / "versions" / "71fc5e2fa383_remove_stored_senior_jobs.py"


def _migration():
    # The file name starts with a digit, so it cannot be imported by name
    spec = importlib.util.spec_from_file_location("remove_senior_jobs", MIGRATION)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _ingested(session, source_id, title):
    fetched = FetchedJob(
        source_id=source_id,
        title=title,
        company_name="Example Software GmbH",
        url=f"https://source.example/{source_id}",
        description="We build things in Python.",
    )
    return store_job(session, "fake", fetched).job.id


def _count(session, model):
    return session.scalar(select(func.count()).select_from(model))


def test_senior_jobs_are_removed_except_applied_and_pasted_ones(client, session):
    _ingested(session, "1", "Senior Python Developer")
    applied = _ingested(session, "2", "Head of Data")
    _ingested(session, "3", "Python Developer")
    _ingested(session, "4", "(Senior) Data Scientist")
    client.post("/applications", json={"job_posting_id": applied})
    client.post(
        "/jobs",
        json={
            "title": "Lead Developer",
            "company_name": "Example Software GmbH",
            "url": "https://jobs.example.com/lead",
            "description": "Pasted by hand.",
        },
    )

    removed = _migration().delete_senior_jobs(session.connection())

    assert removed == 1
    titles = sorted(j["title"] for j in client.get("/jobs").json())
    assert titles == ["(Senior) Data Scientist", "Head of Data", "Lead Developer", "Python Developer"]
    assert _count(session, JobPostingSnapshot) == 4
    assert _count(session, JobPostingSource) == 4
