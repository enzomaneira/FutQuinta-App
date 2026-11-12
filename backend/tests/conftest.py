"""Fixtures dos testes.

Os testes rodam num Postgres real (TEST_DATABASE_URL), com as migrations
aplicadas uma vez por sessão. Cada teste roda dentro de uma transação que é
desfeita no final, então um teste não enxerga dados de outro.
"""

import os

# Precisa vir antes de importar o app: o engine é criado na importação
TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://futquinta:futquinta@localhost:5432/futquinta_test",
)
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ.setdefault("JWT_SECRET", "segredo-de-teste-com-tamanho-suficiente")
os.environ["SCHEDULER_ENABLED"] = "false"

import pytest  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.core.config import BACKEND_DIR  # noqa: E402
from app.core.db import engine, get_db  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def migrated_database():
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option(
        "sqlalchemy.url", engine.url.render_as_string(hide_password=False)
    )
    # Recria do zero: também valida que downgrade e upgrade funcionam
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")
    yield


@pytest.fixture
def db():
    connection = engine.connect()
    transaction = connection.begin()
    # Commits dentro do código viram savepoints; o rollback final apaga tudo
    session = Session(
        bind=connection,
        join_transaction_mode="create_savepoint",
        expire_on_commit=False,
    )
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def client(db):
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
