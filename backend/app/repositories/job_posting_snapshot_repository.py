from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.job_posting_snapshot import JobPostingSnapshot


class JobPostingSnapshotRepository:
    def __init__(self, session: Session):
        self.session = session

    def add(self, snapshot: JobPostingSnapshot) -> JobPostingSnapshot:
        self.session.add(snapshot)
        self.session.flush()
        return snapshot

    def get_latest_for_job(self, job_id: int) -> JobPostingSnapshot | None:
        stmt = (
            select(JobPostingSnapshot)
            .where(JobPostingSnapshot.job_posting_id == job_id)
            .order_by(JobPostingSnapshot.captured_at.desc(), JobPostingSnapshot.id.desc())
            .limit(1)
        )
        return self.session.scalars(stmt).first()