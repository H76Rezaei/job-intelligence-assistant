import os

# Must run before anything imports app.config
os.environ["POSTGRES_DB"] = "jobintel_test"

import pytest
from fastapi.testclient import TestClient

from app.database import SessionLocal, get_session
from app.main import app


@pytest.fixture
def session():
    with SessionLocal() as session:
        yield session
        session.rollback()


@pytest.fixture
def client(session):
    app.dependency_overrides[get_session] = lambda: session
    yield TestClient(app)
    app.dependency_overrides.clear()