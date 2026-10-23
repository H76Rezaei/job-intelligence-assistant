from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.job_posting import JobPosting


class JobPostingSource(Base):
    """Where a job was found: one row per source that listed it."""

    __tablename__ = "job_posting_sources"
    __table_args__ = (UniqueConstraint("source", "source_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    job_posting_id: Mapped[int] = mapped_column(
        ForeignKey("job_postings.id"), index=True
    )
    source: Mapped[str] = mapped_column(String(50))
    source_id: Mapped[str] = mapped_column(String(2048))
    url: Mapped[str] = mapped_column(String(2048))
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    job_posting: Mapped[JobPosting] = relationship(back_populates="sources")
