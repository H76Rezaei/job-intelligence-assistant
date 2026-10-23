import hashlib
from dataclasses import dataclass

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.ingestion.fetched_job import FetchedJob
from app.matching import normalize_company_name, normalize_title
from app.models.company import Company
from app.models.job_posting import JobPosting
from app.models.job_posting_snapshot import JobPostingSnapshot
from app.models.job_posting_source import JobPostingSource
from app.repositories.company_repository import CompanyRepository
from app.repositories.job_posting_snapshot_repository import (
    JobPostingSnapshotRepository,
)
from app.repositories.job_posting_source_repository import JobPostingSourceRepository
from app.repositories.job_repository import JobRepository


@dataclass
class StoredJob:
    job: JobPosting
    created: bool


def content_hash(title: str, location: str | None, description: str) -> str:
    text = "\n".join([title, location or "", description])
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def find_existing_job(session: Session, source: str, fetched: FetchedJob) -> JobPosting | None:
    """Same source ID first, then the same cleaned-up title at the same company."""
    source_row = JobPostingSourceRepository(session).get(source, fetched.source_id)
    if source_row is not None:
        return source_row.job_posting

    company = CompanyRepository(session).get_by_normalized_name(
        normalize_company_name(fetched.company_name)
    )
    if company is None:
        return None
    return JobRepository(session).get_by_company_and_title(
        company.id, normalize_title(fetched.title)
    )


def store_job(session: Session, source: str, fetched: FetchedJob) -> StoredJob:
    """Store a fetched job, or attach it to the job we already have."""
    job = find_existing_job(session, source, fetched)
    created = job is None

    if job is None:
        job = JobRepository(session).add(
            JobPosting(
                company_id=_get_or_create_company(session, fetched.company_name).id,
                title=fetched.title,
                location=fetched.location,
                employment_type=fetched.employment_type,
                work_mode=fetched.work_mode,
                url=fetched.url,
            )
        )
    else:
        job.last_seen_at = func.now()

    sources = JobPostingSourceRepository(session)
    if sources.get(source, fetched.source_id) is None:
        sources.add(
            JobPostingSource(
                job_posting_id=job.id,
                source=source,
                source_id=fetched.source_id,
                url=fetched.url,
            )
        )

    if fetched.description:
        _add_snapshot_if_new(session, job, fetched)

    session.flush()
    session.refresh(job)
    return StoredJob(job=job, created=created)


def _get_or_create_company(session: Session, name: str) -> Company:
    companies = CompanyRepository(session)
    company = companies.get_by_normalized_name(normalize_company_name(name))
    return company or companies.add(Company(name=name))


def _add_snapshot_if_new(session: Session, job: JobPosting, fetched: FetchedJob) -> None:
    snapshots = JobPostingSnapshotRepository(session)
    hash_ = content_hash(fetched.title, fetched.location, fetched.description)
    if snapshots.has_hash(job.id, hash_):
        return
    snapshots.add(
        JobPostingSnapshot(
            job_posting_id=job.id,
            title=fetched.title,
            location=fetched.location,
            description=fetched.description,
            content_hash=hash_,
            raw_data=fetched.raw,
        )
    )
