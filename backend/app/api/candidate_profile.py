from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_session
from app.repositories.candidate_profile_repository import (
    CandidateProfileRepository,
)
from app.schemas.candidate_profile import (
    CandidateProfileRead,
    CandidateProfileUpdate,
)

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("", response_model=CandidateProfileRead)
def get_profile(session: Session = Depends(get_session)):
    profile = CandidateProfileRepository(session).get()
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile


@router.put("", response_model=CandidateProfileRead)
def put_profile(
    data: CandidateProfileUpdate, session: Session = Depends(get_session)
):
    profile = CandidateProfileRepository(session).upsert(data.model_dump())
    session.commit()
    return profile