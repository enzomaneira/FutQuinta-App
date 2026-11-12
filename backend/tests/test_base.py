from app.core.config import Settings
from app.models.setting import Setting
from app.services.settings import DEFAULTS, get_all_settings, get_setting


def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_rota_inexistente_da_api_devolve_404(client):
    assert client.get("/api/nao-existe").status_code == 404


def test_migration_grava_os_padroes_de_configuracao(db):
    # Garante que a migration e DEFAULTS não divergem
    stored = {row.key: row.value for row in db.query(Setting).all()}
    assert stored == DEFAULTS


def test_valores_de_negocio(db):
    assert get_setting(db, "monthly_fee_cents") == 5900
    assert get_setting(db, "drop_in_fee_cents") == 2500
    assert get_setting(db, "initial_cash_cents") == 24500
    assert get_setting(db, "monthly_due_day") == 15


def test_configuracao_editada_prevalece_sobre_padrao(db):
    db.get(Setting, "drop_in_fee_cents").value = 3000
    db.commit()
    assert get_all_settings(db)["drop_in_fee_cents"] == 3000


def test_url_do_railway_ganha_driver_psycopg():
    settings = Settings(
        database_url="postgresql://u:p@host:5432/db", jwt_secret="x" * 32
    )
    assert settings.database_url == "postgresql+psycopg://u:p@host:5432/db"

    settings = Settings(database_url="postgres://u:p@host/db", jwt_secret="x" * 32)
    assert settings.database_url == "postgresql+psycopg://u:p@host/db"
