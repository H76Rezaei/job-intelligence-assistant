from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.job_posting import JobStatus, WorkMode
from app.schemas.company import CompanyRead


class JobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    location: str | None
    employment_type: str | None
    work_mode: WorkMode | None
    url: str
    status: JobStatus
    first_seen_at: datetime
    last_seen_at: datetime
    company: CompanyRead