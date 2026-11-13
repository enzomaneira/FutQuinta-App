"""Avulso: mensalista que trouxe o jogador."""

import pytest

from app.models.enums import PlayerType, Position
from app.services import games, queue
from app.services import players as service
from app.services.errors import DomainError, NotFoundError
from tests.helpers import GAME_DAY, sp

MONTHLY, DROP_IN, FIELD = PlayerType.MONTHLY, PlayerType.DROP_IN, Position.FIELD


@pytest.fixture
def mensalista(db):
    return service.create_player(db, name="Bruno", type=MONTHLY, position=FIELD)


def test_avulso_trazido_por_mensalista(db, mensalista):
    avulso = service.create_player(
        db, name="Amigo do Bruno", type=DROP_IN, position=FIELD, referred_by_id=mensalista.id
    )
    assert avulso.referred_by_id == mensalista.id
    assert service.referrer_names(db, [avulso, mensalista]) == {avulso.id: "Bruno"}


def test_campo_e_opcional(db):
    avulso = service.create_player(db, name="Sozinho", type=DROP_IN, position=FIELD)
    assert avulso.referred_by_id is None


def test_quem_trouxe_precisa_ser_mensalista(db):
    outro = service.create_player(db, name="Outro avulso", type=DROP_IN, position=FIELD)
    with pytest.raises(DomainError, match="precisa ser um mensalista"):
        service.create_player(db, name="X", type=DROP_IN, position=FIELD, referred_by_id=outro.id)
    with pytest.raises(NotFoundError):
        service.create_player(db, name="Y", type=DROP_IN, position=FIELD, referred_by_id=999999)


def test_mensalista_inativo_nao_pode_ser_escolhido(db, mensalista):
    service.update_player(db, mensalista.id, active=False)
    with pytest.raises(DomainError, match="inativo"):
        service.create_player(
            db, name="X", type=DROP_IN, position=FIELD, referred_by_id=mensalista.id
        )


def test_desativar_o_mensalista_mantem_o_historico(db, mensalista):
    avulso = service.create_player(
        db, name="Amigo", type=DROP_IN, position=FIELD, referred_by_id=mensalista.id
    )
    service.update_player(db, mensalista.id, active=False)
    # Editar outro campo do avulso não exige que o mensalista esteja ativo
    assert service.update_player(db, avulso.id, name="Amigo do Bruno").referred_by_id == mensalista.id


def test_trocar_e_remover_quem_trouxe(db, mensalista):
    outro = service.create_player(db, name="Caio", type=MONTHLY, position=FIELD)
    avulso = service.create_player(
        db, name="Amigo", type=DROP_IN, position=FIELD, referred_by_id=mensalista.id
    )
    assert service.update_player(db, avulso.id, referred_by_id=outro.id).referred_by_id == outro.id
    assert service.update_player(db, avulso.id, referred_by_id=None).referred_by_id is None


def test_avulso_que_vira_mensalista_perde_o_vinculo(db, mensalista):
    avulso = service.create_player(
        db, name="Amigo", type=DROP_IN, position=FIELD, referred_by_id=mensalista.id
    )
    assert service.update_player(db, avulso.id, type=MONTHLY).referred_by_id is None


def test_mensalista_nao_tem_quem_trouxe(db, mensalista):
    outro = service.create_player(
        db, name="Caio", type=MONTHLY, position=FIELD, referred_by_id=mensalista.id
    )
    assert outro.referred_by_id is None


# --- API ---


def test_api_cadastro_e_lista(auth_client, db, mensalista):
    created = auth_client.post(
        "/api/players",
        json={"name": "Amigo", "type": "drop_in", "position": "field", "referred_by_id": mensalista.id},
    )
    assert created.status_code == 201
    avulso_id = created.json()["id"]

    listed = auth_client.get("/api/players?type=drop_in").json()
    assert (listed[0]["referred_by_id"], listed[0]["referred_by_name"]) == (mensalista.id, "Bruno")
    assert auth_client.get(f"/api/players/{avulso_id}").json()["referred_by_name"] == "Bruno"

    cleared = auth_client.patch(f"/api/players/{avulso_id}", json={"referred_by_id": None})
    assert cleared.json()["referred_by_id"] is None


def test_api_mostra_quem_trouxe_na_fila(auth_client, db, mensalista):
    avulso = service.create_player(
        db, name="Amigo", type=DROP_IN, position=FIELD, referred_by_id=mensalista.id
    )
    game = games.create_game(db, GAME_DAY)
    queue.join_queue(db, game.id, avulso.id, now=sp(17, 11))
    body = auth_client.get(f"/api/games/{game.id}").json()
    assert body["queue"]["field"][0]["referred_by_name"] == "Bruno"
    assert body["lineup"]["field"][0]["referred_by_name"] is None  # o próprio mensalista
