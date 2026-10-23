from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.job_posting_source import JobPostingSource


class JobPostingSourceRepository:
    def __init__(self, session: Session):
        self.session = session

    def add(self, source: JobPostingSource) -> JobPostingSource:
        self.session.add(source)
        self.session.flush()
        return source

    def get(self, source: str, source_id: str) -> JobPostingSource | None:
        stmt = select(JobPostingSource).where(
            JobPostingSource.source == source,
            JobPostingSource.source_id == source_id,
        )
        return self.session.scalars(stmt).first()
