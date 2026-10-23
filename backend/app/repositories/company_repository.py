from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.company import Company


class CompanyRepository:
    def __init__(self, session: Session):
        self.session = session

    def add(self, company: Company) -> Company:
        self.session.add(company)
        self.session.flush()
        return company

    def get_by_domain(self, domain: str) -> Company | None:
        stmt = select(Company).where(Company.domain == domain)
        return self.session.scalars(stmt).first()

    def get_by_normalized_name(self, normalized_name: str) -> Company | None:
        stmt = select(Company).where(Company.normalized_name == normalized_name)
        return self.session.scalars(stmt).first()
