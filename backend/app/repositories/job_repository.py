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
    
    def get(self, job_id: int) -> JobPosting | None:
        stmt = (
            select(JobPosting)
            .options(selectinload(JobPosting.company), selectinload(JobPosting.sources))
            .where(JobPosting.id == job_id)
        )
        return self.session.scalars(stmt).first()

    def get_by_company_and_title(
        self, company_id: int, normalized_title: str
    ) -> JobPosting | None:
        stmt = select(JobPosting).where(
            JobPosting.company_id == company_id,
            JobPosting.normalized_title == normalized_title,
        )
        return self.session.scalars(stmt).first()