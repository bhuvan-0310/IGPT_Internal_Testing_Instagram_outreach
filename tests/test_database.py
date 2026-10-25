import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
import src.database as database_module


def test_check_connection_reports_failure_without_raising(monkeypatch):
    """check_connection() must never raise; it returns (False, message) with
    actionable guidance when the database is unreachable."""
    broken_engine = create_engine("postgresql+psycopg://nouser:nopass@127.0.0.1:1/doesnotexist")
    monkeypatch.setattr(database_module, "engine", broken_engine)
    ok, message = database_module.check_connection()
    assert ok is False
    assert "Could not connect" in message or "failed" in message.lower()


def test_init_db_raises_runtime_error_with_troubleshooting_on_failure(monkeypatch):
    monkeypatch.setattr(database_module, "check_connection", lambda: (False, "simulated failure"))
    with pytest.raises(RuntimeError, match="Troubleshooting"):
        database_module.init_db()


def test_init_db_does_not_raise_when_connection_succeeds(monkeypatch):
    monkeypatch.setattr(database_module, "check_connection", lambda: (True, "ok"))
    database_module.init_db()  # should not raise


@pytest.mark.requires_postgres
def test_check_connection_succeeds_against_real_configured_database():
    """Exercises the actual DATABASE_URL from .env. Requires PostgreSQL to be
    running and reachable with the configured role/database. Run with:
    pytest -m requires_postgres"""
    ok, message = database_module.check_connection()
    assert ok is True
    assert "Connected" in message
