from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CandidateProfileUpdate(BaseModel):
    full_name: str = Field(min_length=1, max_length=255)
    headline: str | None = Field(default=None, max_length=255)
    summary: str | None = None


class CandidateProfileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    headline: str | None
    summary: str | None
    created_at: datetime
    updated_at: datetime