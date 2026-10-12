from app.models.application import Application, ApplicationStatus
from app.models.company import Company
from app.models.job_posting import JobPosting
from app.models.job_posting_snapshot import JobPostingSnapshot
from app.repositories.application_repository import ApplicationRepository
from app.repositories.company_repository import CompanyRepository
from app.repositories.job_posting_snapshot_repository import (
    JobPostingSnapshotRepository,
)
from app.repositories.job_repository import JobRepository


def _add_job_with_snapshot(session, number: int):
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
    snapshot = JobPostingSnapshotRepository(session).add(
        JobPostingSnapshot(
            job_posting_id=job.id,
            title=job.title,
            description="Some text",
            content_hash=f"hash{number}",
        )
    )
    return job, snapshot


def test_add_assigns_id(session):
    job, snapshot = _add_job_with_snapshot(session, 1)

    application = ApplicationRepository(session).add(
        Application(
            job_posting_id=job.id,
            snapshot_id=snapshot.id,
            status=ApplicationStatus.INTERESTED,
        )
    )

    assert application.id is not None


def test_get_by_job(session):
    repo = ApplicationRepository(session)
    job, snapshot = _add_job_with_snapshot(session, 1)
    repo.add(
        Application(
            job_posting_id=job.id,
            snapshot_id=snapshot.id,
            status=ApplicationStatus.APPLIED,
        )
    )

    found = repo.get_by_job(job.id)

    assert found.status == ApplicationStatus.APPLIED
    assert repo.get_by_job(999999) is None


def test_list_all_filters_by_status(session):
    repo = ApplicationRepository(session)
    for number, status in [
        (1, ApplicationStatus.INTERESTED),
        (2, ApplicationStatus.NOT_INTERESTED),
    ]:
        job, snapshot = _add_job_with_snapshot(session, number)
        repo.add(
            Application(
                job_posting_id=job.id, snapshot_id=snapshot.id, status=status
            )
        )

    assert len(repo.list_all()) == 2
    only_interested = repo.list_all(status=ApplicationStatus.INTERESTED)
    assert len(only_interested) == 1
    assert only_interested[0].status == ApplicationStatus.INTERESTED