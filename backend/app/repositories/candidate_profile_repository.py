from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.candidate_profile import CandidateProfile


class CandidateProfileRepository:
    def __init__(self, session: Session):
        self.session = session

    def get(self) -> CandidateProfile | None:
        stmt = select(CandidateProfile).order_by(CandidateProfile.id)
        return self.session.scalars(stmt).first()

    def upsert(self, values: dict) -> CandidateProfile:
        profile = self.get()
        if profile is None:
            profile = CandidateProfile(**values)
            self.session.add(profile)
        else:
            for field, value in values.items():
                setattr(profile, field, value)
        self.session.flush()
        return profile