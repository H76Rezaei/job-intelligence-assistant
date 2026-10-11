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

    def list_all(self) -> list[Company]:
        stmt = select(Company).order_by(Company.name)
        return list(self.session.scalars(stmt))

    def get(self, company_id: int) -> Company | None:
        return self.session.get(Company, company_id)