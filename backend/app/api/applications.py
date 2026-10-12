from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_session
from app.models.application import Application, ApplicationStatus
from app.repositories.application_repository import ApplicationRepository
from app.repositories.job_posting_snapshot_repository import (
    JobPostingSnapshotRepository,
)
from app.repositories.job_repository import JobRepository
from app.schemas.application import (
    ApplicationCreate,
    ApplicationRead,
    ApplicationUpdate,
)

router = APIRouter(prefix="/applications", tags=["applications"])


@router.get("", response_model=list[ApplicationRead])
def list_applications(
    status: ApplicationStatus | None = None,
    session: Session = Depends(get_session),
):
    return ApplicationRepository(session).list_all(status=status)


@router.get("/{application_id}", response_model=ApplicationRead)
def get_application(application_id: int, session: Session = Depends(get_session)):
    application = ApplicationRepository(session).get(application_id)
    if application is None:
        raise HTTPException(status_code=404, detail="Application not found")
    return application


@router.post("", response_model=ApplicationRead, status_code=201)
def create_application(
    data: ApplicationCreate, session: Session = Depends(get_session)
):
    job = JobRepository(session).get(data.job_posting_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    snapshot = JobPostingSnapshotRepository(session).get_latest_for_job(job.id)
    if snapshot is None:
        raise HTTPException(status_code=409, detail="Job has no snapshot yet")

    repo = ApplicationRepository(session)
    if repo.get_by_job(job.id) is not None:
        raise HTTPException(
            status_code=409, detail="Job already has an application record"
        )

    application = repo.add(
        Application(
            job_posting_id=job.id,
            snapshot_id=snapshot.id,
            status=data.status,
            notes=data.notes,
        )
    )
    session.commit()
    return application


@router.patch("/{application_id}", response_model=ApplicationRead)
def update_application(
    application_id: int,
    data: ApplicationUpdate,
    session: Session = Depends(get_session),
):
    application = ApplicationRepository(session).get(application_id)
    if application is None:
        raise HTTPException(status_code=404, detail="Application not found")

    changes = {
        field: value
        for field, value in data.model_dump(exclude_unset=True).items()
        if value is not None
    }
    for field, value in changes.items():
        setattr(application, field, value)
    session.commit()
    return application