import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.database import Base, get_db
from app.main import app

# Use a PostgreSQL test database if TEST_DATABASE_URL is set, otherwise fall
# back to SQLite.  SQLite works because the JsonList TypeDecorator stores lists
# as plain JSON text, avoiding the PostgreSQL-only ARRAY type.
_TEST_DB_URL = os.getenv(
    "TEST_DATABASE_URL",
    "sqlite:///./test.db",
)

_connect_args = {"check_same_thread": False} if _TEST_DB_URL.startswith("sqlite") else {}

engine = create_engine(_TEST_DB_URL, connect_args=_connect_args)
TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session", autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db():
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSession(bind=connection)
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture(autouse=True)
def reset_rate_limits():
    """Clear the in-memory rate-limit counters before each test so tests don't
    bleed into each other through the shared TestClient IP address."""
    from app.core.limiter import limiter
    storage = getattr(limiter, "_storage", None)
    if storage and hasattr(storage, "reset"):
        storage.reset()


@pytest.fixture
def client(db):
    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
