from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.application import Application, ApplicationStatus
from app.models.job_posting import JobPosting


class ApplicationRepository:
    def __init__(self, session: Session):
        self.session = session

    def add(self, application: Application) -> Application:
        self.session.add(application)
        self.session.flush()
        return application

    def get(self, application_id: int) -> Application | None:
        return self.session.get(Application, application_id)

    def get_by_job(self, job_id: int) -> Application | None:
        stmt = select(Application).where(Application.job_posting_id == job_id)
        return self.session.scalars(stmt).first()

    def list_all(
        self, status: ApplicationStatus | None = None
    ) -> list[Application]:
        stmt = (
            select(Application)
            .options(
                selectinload(Application.job_posting).selectinload(JobPosting.company)
            )
            .order_by(Application.updated_at.desc(), Application.id.desc())
        )
        if status is not None:
            stmt = stmt.where(Application.status == status)
        return list(self.session.scalars(stmt))