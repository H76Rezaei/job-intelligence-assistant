from datetime import datetime

from typing import Any

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.job_posting import JobPosting


class JobPostingSnapshot(Base):
    __tablename__ = "job_posting_snapshots"
    __table_args__ = (UniqueConstraint("job_posting_id", "content_hash"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    job_posting_id: Mapped[int] = mapped_column(ForeignKey("job_postings.id"))
    title: Mapped[str] = mapped_column(String(255))
    location: Mapped[str | None] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)
    content_hash: Mapped[str] = mapped_column(String(64))
    # What the source sent for this version (for paste: the submitted form)
    raw_data: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    job_posting: Mapped[JobPosting] = relationship()