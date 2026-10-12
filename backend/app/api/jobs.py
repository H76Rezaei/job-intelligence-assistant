from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_session
from app.repositories.job_repository import JobRepository
from app.schemas.job import JobRead

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("", response_model=list[JobRead])
def list_jobs(session: Session = Depends(get_session)):
    return JobRepository(session).list_all()