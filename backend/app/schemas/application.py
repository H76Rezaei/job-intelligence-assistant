from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.application import ApplicationStatus
from app.schemas.job import JobRead


class ApplicationCreate(BaseModel):
    job_posting_id: int
    status: ApplicationStatus = ApplicationStatus.INTERESTED
    notes: str | None = None


class ApplicationUpdate(BaseModel):
    status: ApplicationStatus | None = None
    notes: str | None = None


class ApplicationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: ApplicationStatus
    notes: str | None
    snapshot_id: int
    created_at: datetime
    updated_at: datetime
    job_posting: JobRead