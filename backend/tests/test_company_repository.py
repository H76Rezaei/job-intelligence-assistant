import os

os.environ["POSTGRES_DB"] = "jobintel_test"

import pytest

from app.database import SessionLocal
from app.models.company import Company
from app.repositories.company_repository import CompanyRepository


@pytest.fixture
def session():
    with SessionLocal() as session:
        yield session
        session.rollback()


def test_add_assigns_id(session):
    repo = CompanyRepository(session)
    company = repo.add(Company(name="Test AG", domain="test.example"))
    assert company.id is not None


def test_get_by_domain(session):
    repo = CompanyRepository(session)
    repo.add(Company(name="Test AG", domain="test.example"))
    assert repo.get_by_domain("test.example").name == "Test AG"
    assert repo.get_by_domain("nope.example") is None