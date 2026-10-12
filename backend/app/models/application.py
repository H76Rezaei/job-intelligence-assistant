import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.job_posting import JobPosting
from app.models.job_posting_snapshot import JobPostingSnapshot


class ApplicationStatus(enum.Enum):
    INTERESTED = "interested"
    NOT_INTERESTED = "not_interested"
    APPLIED = "applied"
    INTERVIEW = "interview"
    REJECTED = "rejected"
    OFFER = "offer"


def _values(enum_class):
    return [member.value for member in enum_class]


class Application(Base):
    __tablename__ = "applications"

    id: Mapped[int] = mapped_column(primary_key=True)
    job_posting_id: Mapped[int] = mapped_column(
        ForeignKey("job_postings.id"), unique=True
    )
    snapshot_id: Mapped[int] = mapped_column(
        ForeignKey("job_posting_snapshots.id"), index=True
    )
    status: Mapped[ApplicationStatus] = mapped_column(
        Enum(ApplicationStatus, native_enum=False, length=20, values_callable=_values)
    )
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    job_posting: Mapped[JobPosting] = relationship()
    snapshot: Mapped[JobPostingSnapshot] = relationship()