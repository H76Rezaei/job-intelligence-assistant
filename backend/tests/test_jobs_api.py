from app.models.company import Company
from app.models.job_posting import JobPosting
from app.repositories.company_repository import CompanyRepository
from app.repositories.job_repository import JobRepository

from app.models.job_posting_snapshot import JobPostingSnapshot
from app.repositories.job_posting_snapshot_repository import (
    JobPostingSnapshotRepository,
)


def _add_job(session) -> JobPosting:
    company = CompanyRepository(session).add(
        Company(name="Test AG", domain="test.example")
    )
    return JobRepository(session).add(
        JobPosting(
            company_id=company.id,
            title="Python Developer",
            url="https://test.example/jobs/1",
        )
    )


def test_get_job_returns_latest_snapshot(client, session):
    job = _add_job(session)
    snapshots = JobPostingSnapshotRepository(session)
    for text, hash_ in [("old text", "hash1"), ("new text", "hash2")]:
        snapshots.add(
            JobPostingSnapshot(
                job_posting_id=job.id,
                title=job.title,
                description=text,
                content_hash=hash_,
            )
        )

    response = client.get(f"/jobs/{job.id}")

    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "Python Developer"
    assert body["company"]["name"] == "Test AG"
    assert body["description"] == "new text"
    assert body["captured_at"] is not None


def test_get_job_without_snapshot_has_null_description(client, session):
    job = _add_job(session)

    response = client.get(f"/jobs/{job.id}")

    assert response.status_code == 200
    assert response.json()["description"] is None
    assert response.json()["captured_at"] is None


def test_get_job_unknown_id_returns_404(client):
    response = client.get("/jobs/999999")

    assert response.status_code == 404
    assert response.json() == {"detail": "Job not found"}
    
def test_list_jobs_returns_job_with_company(client, session):
    company = CompanyRepository(session).add(
        Company(name="Test AG", domain="test.example")
    )
    JobRepository(session).add(
        JobPosting(
            company_id=company.id,
            title="Python Developer",
            url="https://test.example/jobs/1",
        )
    )

    response = client.get("/jobs")

    assert response.status_code == 200
    jobs = response.json()
    assert len(jobs) == 1
    assert jobs[0]["title"] == "Python Developer"
    assert jobs[0]["company"]["name"] == "Test AG"


def test_list_jobs_empty(client):
    response = client.get("/jobs")

    assert response.status_code == 200
    assert response.json() == []