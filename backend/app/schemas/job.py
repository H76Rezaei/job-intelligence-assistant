from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator

from app.matching import normalize_company_name, normalize_title
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

    # An empty matching key would merge unrelated postings into one job
    @field_validator("title")
    @classmethod
    def title_has_a_matching_key(cls, title: str) -> str:
        if not normalize_title(title):
            raise ValueError("title has no words")
        return title

    @field_validator("company_name")
    @classmethod
    def company_has_a_matching_key(cls, name: str) -> str:
        if not normalize_company_name(name):
            raise ValueError("company name has no words")
        return name

    @field_validator("description")
    @classmethod
    def description_has_text(cls, description: str) -> str:
        if not description.strip():
            raise ValueError("description is blank")
        return description


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

class JobListRead(JobRead):
    is_new: bool


class JobDetailRead(JobListRead):
    description: str | None
    captured_at: datetime | None
    sources: list[JobSourceRead]
