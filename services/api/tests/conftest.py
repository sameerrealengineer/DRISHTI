"""Test setup. DB tests need PostgreSQL + PostGIS at TEST_DATABASE_URL; they are skipped if it is unreachable."""

import os

TEST_DB = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+psycopg://drishti:drishti@localhost:5432/drishti_test"
)
os.environ["DATABASE_URL"] = TEST_DB
os.environ.setdefault("DRISHTI_MODE", "demo")

import pytest  # noqa: E402
from sqlalchemy import create_engine, text  # noqa: E402


def _db_available() -> bool:
    try:
        with create_engine(TEST_DB).connect() as c:
            c.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


DB_AVAILABLE = _db_available()


@pytest.fixture(scope="session")
def seeded_db():
    if not DB_AVAILABLE:
        pytest.skip("test database not available")
    from alembic import command
    from alembic.config import Config
    from app.db import session_factory
    from app.seed.loader import ALL_TABLES, load_all, truncate

    here = os.path.dirname(__file__)
    cfg = Config(os.path.join(here, "..", "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(here, "..", "alembic"))
    cfg.set_main_option("sqlalchemy.url", TEST_DB)
    command.upgrade(cfg, "head")
    with session_factory()() as db:
        truncate(db, ALL_TABLES)
        db.commit()
        load_all(db)
    yield session_factory()


@pytest.fixture(scope="session")
def client(seeded_db):
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as c:
        yield c
