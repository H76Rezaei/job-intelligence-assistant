from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, validates

from app.matching import normalize_company_name
from app.models.base import Base


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    # Matching key only; `name` keeps the full name for display and documents
    normalized_name: Mapped[str] = mapped_column(String(255), unique=True)
    domain: Mapped[str | None] = mapped_column(String(255), unique=True)
    industry: Mapped[str | None] = mapped_column(String(255))
    careers_url: Mapped[str | None] = mapped_column(String(2048))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    @validates("name")
    def _set_normalized_name(self, _key: str, name: str) -> str:
        self.normalized_name = normalize_company_name(name)
        return name