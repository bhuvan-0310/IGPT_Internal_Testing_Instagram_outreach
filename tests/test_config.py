import pytest
from src.config import mask_url, validate_database_url


def test_missing_database_url_raises_actionable_error():
    with pytest.raises(RuntimeError, match="DATABASE_URL is not set"):
        validate_database_url("")
    with pytest.raises(RuntimeError, match="DATABASE_URL is not set"):
        validate_database_url("   ")


def test_non_postgres_database_url_is_rejected():
    with pytest.raises(RuntimeError, match="PostgreSQL connection string"):
        validate_database_url("sqlite:///local.db")
    with pytest.raises(RuntimeError, match="PostgreSQL connection string"):
        validate_database_url("mysql://user:pass@localhost/db")


def test_valid_postgres_url_passes_validation():
    validate_database_url("postgresql+psycopg://user:pass@localhost:5432/db")  # should not raise
    validate_database_url("postgresql://user:pass@localhost:5432/db")  # should not raise


def test_mask_url_hides_password_but_keeps_user_and_host():
    masked = mask_url("postgresql+psycopg://outreach_app:supersecret@localhost:5432/mydb")
    assert "supersecret" not in masked
    assert "****" in masked
    assert "outreach_app" in masked
    assert "localhost:5432/mydb" in masked


def test_mask_url_handles_url_without_credentials():
    assert mask_url("postgresql://localhost:5432/mydb") == "postgresql://localhost:5432/mydb"
