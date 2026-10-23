from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.database import get_session
from app.ingestion.fetched_job import FetchedJob
from app.ingestion.storage import store_job
from app.matching import normalize_url
from app.models.job_posting import JobPosting
from app.repositories.ingestion_run_repository import IngestionRunRepository
from app.repositories.job_posting_snapshot_repository import (
    JobPostingSnapshotRepository,
)
from app.repositories.job_repository import JobRepository
from app.schemas.job import (
    JobDetailRead,
    JobListRead,
    JobPaste,
    JobRead,
    JobSourceRead,
)

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("", response_model=list[JobListRead])
def list_jobs(new_in_last_run: bool = False, session: Session = Depends(get_session)):
    latest_run_id = IngestionRunRepository(session).latest_finished_id()
    if new_in_last_run and latest_run_id is None:
        return []
    jobs = JobRepository(session).list_all(
        new_in_run_id=latest_run_id if new_in_last_run else None
    )
    return [_job_list_item(job, latest_run_id) for job in jobs]


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


def _job_list_item(job: JobPosting, latest_run_id: int | None) -> JobListRead:
    return JobListRead(
        **JobRead.model_validate(job).model_dump(),
        is_new=latest_run_id is not None and job.new_in_run_id == latest_run_id,
    )


def _job_detail(session: Session, job: JobPosting) -> JobDetailRead:
    latest_run_id = IngestionRunRepository(session).latest_finished_id()
    snapshot = JobPostingSnapshotRepository(session).get_latest_for_job(job.id)
    return JobDetailRead(
        **_job_list_item(job, latest_run_id).model_dump(),
        description=snapshot.description if snapshot else None,
        captured_at=snapshot.captured_at if snapshot else None,
        sources=[JobSourceRead.model_validate(s) for s in job.sources],
    )
