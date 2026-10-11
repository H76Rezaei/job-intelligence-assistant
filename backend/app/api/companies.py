from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_session
from app.repositories.company_repository import CompanyRepository
from app.schemas.company import CompanyRead

router = APIRouter(prefix="/companies", tags=["companies"])


@router.get("", response_model=list[CompanyRead])
def list_companies(session: Session = Depends(get_session)):
    return CompanyRepository(session).list_all()


@router.get("/{company_id}", response_model=CompanyRead)
def get_company(company_id: int, session: Session = Depends(get_session)):
    company = CompanyRepository(session).get(company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")
    return company