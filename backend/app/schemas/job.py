from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from app.models.job_posting import JobStatus, WorkMode
from app.schemas.company import CompanyRead


class JobPaste(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    company_name: str = Field(min_length=1, max_length=255)
    url: HttpUrl
    description: str = Field(min_length=1)
    location: str | None = Field(default=None, max_length=255)
    employment_type: str | None = Field(default=None, max_length=50)
    work_mode: WorkMode | None = None


class JobSourceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    source: str
    url: str
    first_seen_at: datetime


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

class JobDetailRead(JobRead):
    description: str | None
    captured_at: datetime | None
    sources: list[JobSourceRead]