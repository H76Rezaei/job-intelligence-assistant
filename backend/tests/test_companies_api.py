from app.models.company import Company
from app.repositories.company_repository import CompanyRepository


def test_list_companies_returns_added_companies(client, session):
    repo = CompanyRepository(session)
    repo.add(Company(name="B Corp", domain="b.example"))
    repo.add(Company(name="A Corp", domain="a.example"))

    response = client.get("/companies")

    assert response.status_code == 200
    names = [c["name"] for c in response.json()]
    assert names == ["A Corp", "B Corp"]


def test_get_company_returns_company(client, session):
    company = CompanyRepository(session).add(Company(name="Test AG", domain="t.example"))

    response = client.get(f"/companies/{company.id}")

    assert response.status_code == 200
    assert response.json()["name"] == "Test AG"


def test_get_company_unknown_id_returns_404(client):
    response = client.get("/companies/999999")

    assert response.status_code == 404
    assert response.json() == {"detail": "Company not found"}