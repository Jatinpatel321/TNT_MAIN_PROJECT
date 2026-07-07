"""Shared pytest fixtures for Vendor Module tests."""

from __future__ import annotations

from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

# Ensure all models are imported
import app.database.init_db  # noqa: F401
from app.database.base import Base
from app.main import app
from app.database.session import get_db

# ── In-memory SQLite test DB ────────────────────────────────────────────────

TEST_DATABASE_URL = "sqlite:///:memory:"
from sqlalchemy.pool import StaticPool
engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    echo=False
)
TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


@pytest.fixture(scope="session")
def db_engine():
    """Create all tables once per test session."""
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(autouse=True)
def db_session(db_engine):
    """Create a new database session for each test."""
    connection = db_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db_session) -> Generator:
    """Create a test client with overridden database dependency."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    from app.database.session import get_db as get_db_session
    from app.core.deps import get_db as get_db_deps
    app.dependency_overrides[get_db_session] = override_get_db
    app.dependency_overrides[get_db_deps] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def db(db_session) -> Session:
    """Provide database session."""
    return db_session