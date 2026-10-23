from dataclasses import dataclass, field
from typing import Any

from app.models.job_posting import WorkMode


@dataclass
class FetchedJob:
    """One posting as a source delivers it, before storage decides what is new."""

    source_id: str
    title: str
    company_name: str
    url: str
    description: str = ""
    location: str | None = None
    # "DE" for jobs in Germany (set by the adapter); ingestion keeps only those
    country: str | None = None
    employment_type: str | None = None
    work_mode: WorkMode | None = None
    raw: dict[str, Any] = field(default_factory=dict)
