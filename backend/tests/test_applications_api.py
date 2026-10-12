from app.models.company import Company
from app.models.job_posting import JobPosting
from app.models.job_posting_snapshot import JobPostingSnapshot
from app.repositories.company_repository import CompanyRepository
from app.repositories.job_posting_snapshot_repository import (
    JobPostingSnapshotRepository,
)
from app.repositories.job_repository import JobRepository


def _add_job(session, number: int = 1, with_snapshot: bool = True):
    company = CompanyRepository(session).add(
        Company(name=f"Test AG {number}", domain=f"test{number}.example")
    )
    job = JobRepository(session).add(
        JobPosting(
            company_id=company.id,
            title="Python Developer",
            url=f"https://test.example/jobs/{number}",
        )
    )
    snapshot = None
    if with_snapshot:
        snapshot = JobPostingSnapshotRepository(session).add(
            JobPostingSnapshot(
                job_posting_id=job.id,
                title=job.title,
                description="Some text",
                content_hash=f"hash{number}",
            )
        )
    return job, snapshot


def test_create_application_defaults_to_interested_and_pins_snapshot(client, session):
    job, snapshot = _add_job(session)

    response = client.post("/applications", json={"job_posting_id": job.id})

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "interested"
    assert body["snapshot_id"] == snapshot.id
    assert body["job_posting"]["title"] == "Python Developer"
    assert body["job_posting"]["company"]["name"] == "Test AG 1"


def test_create_application_unknown_job_returns_404(client):
    response = client.post("/applications", json={"job_posting_id": 999999})

    assert response.status_code == 404
    assert response.json() == {"detail": "Job not found"}


def test_create_application_without_snapshot_returns_409(client, session):
    job, _ = _add_job(session, with_snapshot=False)

    response = client.post("/applications", json={"job_posting_id": job.id})

    assert response.status_code == 409
    assert response.json() == {"detail": "Job has no snapshot yet"}


def test_create_application_twice_returns_409(client, session):
    job, _ = _add_job(session)
    client.post("/applications", json={"job_posting_id": job.id})

    response = client.post("/applications", json={"job_posting_id": job.id})

    assert response.status_code == 409


def test_create_application_invalid_status_returns_422(client, session):
    job, _ = _add_job(session)

    response = client.post(
        "/applications", json={"job_posting_id": job.id, "status": "maybe"}
    )

    assert response.status_code == 422


def test_list_applications_filters_by_status(client, session):
    job1, _ = _add_job(session, 1)
    job2, _ = _add_job(session, 2)
    client.post("/applications", json={"job_posting_id": job1.id})
    client.post(
        "/applications",
        json={"job_posting_id": job2.id, "status": "not_interested"},
    )

    assert len(client.get("/applications").json()) == 2
    filtered = client.get("/applications", params={"status": "not_interested"})
    assert filtered.status_code == 200
    assert len(filtered.json()) == 1
    assert filtered.json()[0]["status"] == "not_interested"


def test_get_application_returns_application(client, session):
    job, _ = _add_job(session)
    created = client.post("/applications", json={"job_posting_id": job.id}).json()

    response = client.get(f"/applications/{created['id']}")

    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


def test_get_application_unknown_id_returns_404(client):
    response = client.get("/applications/999999")

    assert response.status_code == 404
    assert response.json() == {"detail": "Application not found"}


def test_patch_application_changes_status_and_notes(client, session):
    job, _ = _add_job(session)
    created = client.post("/applications", json={"job_posting_id": job.id}).json()

    response = client.patch(
        f"/applications/{created['id']}",
        json={"status": "applied", "notes": "sent CV"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "applied"
    assert body["notes"] == "sent CV"
    assert body["snapshot_id"] == created["snapshot_id"]


def test_patch_application_unknown_id_returns_404(client):
    response = client.patch("/applications/999999", json={"status": "applied"})

    assert response.status_code == 404