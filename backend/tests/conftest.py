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

from datetime import UTC, datetime, timedelta  # noqa: E402

from app.core.config import BACKEND_DIR  # noqa: E402
from app.core.db import engine, get_db  # noqa: E402
from app.core.security import create_access_token  # noqa: E402
from app.main import app  # noqa: E402
from app.models.enums import GameStatus, PlayerType, Position  # noqa: E402
from app.models.game import Game  # noqa: E402
from app.models.player import Player  # noqa: E402
from app.services.auth import create_user  # noqa: E402


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


@pytest.fixture
def auth_client(client, db):
    """Cliente HTTP já autenticado como organizador."""
    user = create_user(db, "org@exemplo.com", "senha-forte-123")
    client.headers["Authorization"] = f"Bearer {create_access_token(user.id)}"
    return client


@pytest.fixture
def make_player(db):
    def factory(name="Jogador", type=PlayerType.DROP_IN, position=Position.FIELD, **kw):
        player = Player(name=name, type=type, position=position, active=True, **kw)
        db.add(player)
        db.commit()
        return player

    return factory


@pytest.fixture
def make_game(db):
    def factory(starts_at=datetime(2026, 11, 20, 0, 30, tzinfo=UTC), **kw):
        # 00:30 UTC de sexta = quinta 21:30 em São Paulo
        game = Game(
            starts_at=starts_at,
            ends_at=starts_at + timedelta(minutes=90),
            confirmation_deadline=starts_at - timedelta(hours=9, minutes=30),
            status=kw.pop("status", GameStatus.OPEN),
            **kw,
        )
        db.add(game)
        db.commit()
        return game

    return factory
