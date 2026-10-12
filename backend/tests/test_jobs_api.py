from app.models.company import Company
from app.models.job_posting import JobPosting
from app.repositories.company_repository import CompanyRepository
from app.repositories.job_repository import JobRepository


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