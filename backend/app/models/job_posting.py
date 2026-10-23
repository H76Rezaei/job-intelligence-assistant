import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.matching import normalize_title
from app.models.base import Base
from app.models.company import Company


class JobStatus(enum.Enum):
    OPEN = "open"
    CLOSED = "closed"


class WorkMode(enum.Enum):
    REMOTE = "remote"
    ONSITE = "onsite"
    HYBRID = "hybrid"


def _values(enum_class):
    return [member.value for member in enum_class]


class JobPosting(Base):
    __tablename__ = "job_postings"
    # Same cleaned-up title at the same company is the same job, whatever the city or source
    __table_args__ = (UniqueConstraint("company_id", "normalized_title"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    normalized_title: Mapped[str] = mapped_column(String(255))
    location: Mapped[str | None] = mapped_column(String(255))
    employment_type: Mapped[str | None] = mapped_column(String(50))
    work_mode: Mapped[WorkMode | None] = mapped_column(
        Enum(WorkMode, native_enum=False, length=20, values_callable=_values)
    )
    url: Mapped[str] = mapped_column(String(2048))
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus, native_enum=False, length=20, values_callable=_values),
        server_default="open",
    )
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    company: Mapped[Company] = relationship()
    sources: Mapped[list["JobPostingSource"]] = relationship(
        back_populates="job_posting", order_by="JobPostingSource.id"
    )

    @validates("title")
    def _set_normalized_title(self, _key: str, title: str) -> str:
        self.normalized_title = normalize_title(title)
        return title