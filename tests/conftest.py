"""Shared pytest fixtures. Service/model tests use an isolated in-memory
SQLite database — fast and fully isolated from the real PostgreSQL instance.
This is a test-only convenience; the application itself never falls back to
SQLite (see src/config.py)."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.models import Base


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()
