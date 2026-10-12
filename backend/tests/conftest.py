import os

# Must run before anything imports app.config
os.environ["POSTGRES_DB"] = "jobintel_test"

import pytest
from fastapi.testclient import TestClient

from app.database import SessionLocal, get_session
from app.main import app
from sqlalchemy.orm import Session

from app.database import engine, get_session


@pytest.fixture
def session():
    connection = engine.connect()
    outer_transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    yield session
    session.close()
    outer_transaction.rollback()
    connection.close()


@pytest.fixture
def client(session):
    app.dependency_overrides[get_session] = lambda: session
    yield TestClient(app)
    app.dependency_overrides.clear()