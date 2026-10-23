from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.database import get_session
from app.ingestion.fetched_job import FetchedJob
from app.ingestion.storage import store_job
from app.matching import normalize_url
from app.models.job_posting import JobPosting
from app.repositories.job_posting_snapshot_repository import (
    JobPostingSnapshotRepository,
)
from app.repositories.job_repository import JobRepository
from app.schemas.job import JobDetailRead, JobPaste, JobRead, JobSourceRead

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("", response_model=list[JobRead])
def list_jobs(session: Session = Depends(get_session)):
    return JobRepository(session).list_all()

@router.get("/{job_id}", response_model=JobDetailRead)
def get_job(job_id: int, session: Session = Depends(get_session)):
    job = JobRepository(session).get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return _job_detail(session, job)


@router.post("", response_model=JobDetailRead, status_code=201)
def paste_job(
    data: JobPaste, response: Response, session: Session = Depends(get_session)
):
    url = str(data.url)
    stored = store_job(
        session,
        "paste",
        FetchedJob(
            source_id=normalize_url(url),
            title=data.title,
            company_name=data.company_name,
            url=url,
            description=data.description,
            location=data.location,
            employment_type=data.employment_type,
            work_mode=data.work_mode,
            raw=data.model_dump(mode="json"),
        ),
    )
    session.commit()
    if not stored.created:
        response.status_code = 200
    return _job_detail(session, stored.job)


def _job_detail(session: Session, job: JobPosting) -> JobDetailRead:
    snapshot = JobPostingSnapshotRepository(session).get_latest_for_job(job.id)
    return JobDetailRead(
        **JobRead.model_validate(job).model_dump(),
        description=snapshot.description if snapshot else None,
        captured_at=snapshot.captured_at if snapshot else None,
        sources=[JobSourceRead.model_validate(s) for s in job.sources],
    )
