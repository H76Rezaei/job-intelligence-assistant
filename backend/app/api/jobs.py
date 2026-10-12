from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_session
from app.repositories.job_repository import JobRepository
from app.schemas.job import JobRead

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_session
from app.repositories.job_posting_snapshot_repository import (
    JobPostingSnapshotRepository,
)
from app.repositories.job_repository import JobRepository
from app.schemas.job import JobDetailRead, JobRead

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("", response_model=list[JobRead])
def list_jobs(session: Session = Depends(get_session)):
    return JobRepository(session).list_all()

@router.get("/{job_id}", response_model=JobDetailRead)
def get_job(job_id: int, session: Session = Depends(get_session)):
    job = JobRepository(session).get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    snapshot = JobPostingSnapshotRepository(session).get_latest_for_job(job_id)

    return JobDetailRead(
        **JobRead.model_validate(job).model_dump(),
        description=snapshot.description if snapshot else None,
        captured_at=snapshot.captured_at if snapshot else None,
    )