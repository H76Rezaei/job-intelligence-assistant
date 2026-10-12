from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.job_posting import JobPosting


class JobRepository:
    def __init__(self, session: Session):
        self.session = session

    def add(self, job: JobPosting) -> JobPosting:
        self.session.add(job)
        self.session.flush()
        return job

    def list_all(self) -> list[JobPosting]:
        stmt = (
            select(JobPosting)
            .options(selectinload(JobPosting.company))
            .order_by(JobPosting.last_seen_at.desc())
        )
        return list(self.session.scalars(stmt))