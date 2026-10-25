from contextlib import contextmanager
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker
from src.config import DATABASE_URL, masked_database_url
from src.models import Base

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def check_connection() -> tuple[bool, str]:
    """Attempt a lightweight connection. Returns (ok, message). Never raises."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True, f"Connected to {masked_database_url()}"
    except OperationalError as exc:
        return False, (
            f"Could not connect to {masked_database_url()}. "
            "Check that PostgreSQL is running, the database and role exist, "
            f"and the password in .env is correct. Details: {exc.__class__.__name__}"
        )
    except Exception as exc:  # noqa: BLE001 - surface any other config/driver issue
        return False, f"Database connection failed ({exc.__class__.__name__}): {exc}"


def init_db():
    """Verify the database is reachable and schema-managed by Alembic.

    This does NOT create or alter tables. Schema changes are applied with
    `alembic upgrade head` (see README). Raises RuntimeError with an
    actionable message if the connection fails, so pages can show it instead
    of a raw traceback.
    """
    ok, message = check_connection()
    if not ok:
        raise RuntimeError(
            f"{message}\n\nTroubleshooting:\n"
            "1. Confirm PostgreSQL is running (pg_isready).\n"
            "2. Confirm DATABASE_URL in .env matches an existing role/database.\n"
            "3. Run 'alembic upgrade head' from the project root to create/update tables.\n"
            "4. See README.md 'Troubleshooting' section for more detail."
        )


def create_all_for_tests():
    """Create tables directly from models. Test-only convenience; production
    schema changes must go through Alembic migrations, not this function."""
    Base.metadata.create_all(bind=engine)


@contextmanager
def get_session():
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
