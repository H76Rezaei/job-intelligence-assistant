from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import Session

from app.config import settings

from collections.abc import Iterator

engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(engine)

def get_session() -> Iterator[Session]:
    with SessionLocal() as session:
        yield session