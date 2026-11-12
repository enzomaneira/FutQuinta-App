import pytest

from app.models.attendance import Attendance
from app.models.enums import AttendanceStatus, PlayerType, Position, SlotType
from app.services import players as service
from app.services.errors import ConflictError, DomainError
from app.services.phones import normalize_phone

MONTHLY = PlayerType.MONTHLY
DROP_IN = PlayerType.DROP_IN
GK = Position.GOALKEEPER
FIELD = Position.FIELD


# --- telefone ---


@pytest.mark.parametrize(
    "raw",
    [
        "(11) 98765-4321",
        "11987654321",
        "+55 11 98765-4321",
        "5511987654321",
        "0055 11 98765 4321",
    ],
)
def test_telefone_normalizado_para_e164(raw):
    assert normalize_phone(raw) == "+5511987654321"


def test_telefone_fixo():
    assert normalize_phone("(11) 3456-7890") == "+551134567890"


@pytest.mark.parametrize("raw", [None, "", "   "])
def test_telefone_vazio_vira_none(raw):
    assert normalize_phone(raw) is None


@pytest.mark.parametrize("raw", ["123", "abc", "+0 11 9999"])
def test_telefone_invalido(raw):
    with pytest.raises(DomainError):
        normalize_phone(raw)


# --- cadastro ---


def test_cria_jogador_limpando_nome_e_telefone(db):
    player = service.create_player(
        db, name="  João   da Silva ", phone="(11) 98765-4321", type=DROP_IN, position=FIELD
    )
    assert player.name == "João da Silva"
    assert player.phone == "+5511987654321"
    assert player.active is True


def test_telefone_duplicado(db):
    service.create_player(db, name="A", phone="11987654321", type=DROP_IN, position=FIELD)
    with pytest.raises(ConflictError, match="já está cadastrado para A"):
        service.create_player(
            db, name="B", phone="+5511987654321", type=DROP_IN, position=FIELD
        )


def test_limite_de_goleiros_mensalistas(db):
    service.create_player(db, name="G1", type=MONTHLY, position=GK)
    service.create_player(db, name="G2", type=MONTHLY, position=GK)
    with pytest.raises(ConflictError, match="mensalistas goleiro"):
        service.create_player(db, name="G3", type=MONTHLY, position=GK)
    # Como avulso pode
    assert service.create_player(db, name="G3", type=DROP_IN, position=GK).id


def test_limite_de_linha_mensalistas(db):
    for i in range(15):
        service.create_player(db, name=f"L{i}", type=MONTHLY, position=FIELD)
    with pytest.raises(ConflictError, match="limite 15"):
        service.create_player(db, name="L16", type=MONTHLY, position=FIELD)


def test_desativar_mensalista_libera_vaga(db):
    g1 = service.create_player(db, name="G1", type=MONTHLY, position=GK)
    service.create_player(db, name="G2", type=MONTHLY, position=GK)
    service.update_player(db, g1.id, active=False)
    assert service.create_player(db, name="G3", type=MONTHLY, position=GK).id


def test_reativar_respeita_limite(db):
    g1 = service.create_player(db, name="G1", type=MONTHLY, position=GK)
    service.update_player(db, g1.id, active=False)
    service.create_player(db, name="G2", type=MONTHLY, position=GK)
    service.create_player(db, name="G3", type=MONTHLY, position=GK)
    with pytest.raises(ConflictError):
        service.update_player(db, g1.id, active=True)
    db.refresh(g1)
    assert g1.active is False  # nada foi alterado


def test_avulso_virando_mensalista_respeita_limite(db):
    service.create_player(db, name="G1", type=MONTHLY, position=GK)
    service.create_player(db, name="G2", type=MONTHLY, position=GK)
    avulso = service.create_player(db, name="G3", type=DROP_IN, position=GK)
    with pytest.raises(ConflictError):
        service.update_player(db, avulso.id, type=MONTHLY)
    # Mudando também para linha, cabe
    updated = service.update_player(db, avulso.id, type=MONTHLY, position=FIELD)
    assert (updated.type, updated.position) == (MONTHLY, FIELD)


def test_contagem_de_vagas_de_mensalistas(db):
    service.create_player(db, name="G1", type=MONTHLY, position=GK)
    service.create_player(db, name="L1", type=MONTHLY, position=FIELD)
    service.create_player(db, name="L2", type=MONTHLY, position=FIELD)
    service.create_player(db, name="Av", type=DROP_IN, position=FIELD)
    slots = service.monthly_slots(db)
    assert (slots[GK].used, slots[GK].total) == (1, 2)
    assert (slots[FIELD].used, slots[FIELD].total) == (2, 15)


def test_editar_telefone_para_um_ja_usado(db):
    service.create_player(db, name="A", phone="11911111111", type=DROP_IN, position=FIELD)
    b = service.create_player(db, name="B", phone="11922222222", type=DROP_IN, position=FIELD)
    with pytest.raises(ConflictError):
        service.update_player(db, b.id, phone="11911111111")
    db.refresh(b)
    assert b.phone == "+5511922222222"


def test_apagar_telefone(db):
    a = service.create_player(db, name="A", phone="11911111111", type=DROP_IN, position=FIELD)
    assert service.update_player(db, a.id, phone=None).phone is None


def test_lista_filtra_e_ordena_por_nome(db):
    service.create_player(db, name="carlos", type=MONTHLY, position=FIELD)
    service.create_player(db, name="Bruno", type=DROP_IN, position=GK, phone="11955554444")
    inativo = service.create_player(db, name="Ana", type=DROP_IN, position=FIELD)
    service.update_player(db, inativo.id, active=False)

    assert [p.name for p in service.list_players(db)] == ["Bruno", "carlos"]
    assert [p.name for p in service.list_players(db, type=DROP_IN)] == ["Bruno"]
    assert [p.name for p in service.list_players(db, position=GK)] == ["Bruno"]
    assert [p.name for p in service.list_players(db, active=False)] == ["Ana"]
    assert [p.name for p in service.list_players(db, active=None)] == [
        "Ana",
        "Bruno",
        "carlos",
    ]
    assert [p.name for p in service.list_players(db, search="CAR")] == ["carlos"]
    assert [p.name for p in service.list_players(db, search="5555")] == ["Bruno"]


def test_exclui_jogador_sem_historico(db):
    a = service.create_player(db, name="A", type=DROP_IN, position=FIELD)
    service.delete_player(db, a.id)
    assert service.list_players(db, active=None) == []


def test_nao_exclui_jogador_com_historico(db, make_game):
    a = service.create_player(db, name="A", type=DROP_IN, position=FIELD)
    game = make_game()
    db.add(
        Attendance(
            game_id=game.id,
            player_id=a.id,
            status=AttendanceStatus.CONFIRMED,
            slot_type=SlotType.DROP_IN,
        )
    )
    db.commit()
    with pytest.raises(ConflictError, match="Desative"):
        service.delete_player(db, a.id)


# --- API ---


def test_api_exige_login(client):
    assert client.get("/api/players").status_code == 401


def test_api_crud(auth_client):
    created = auth_client.post(
        "/api/players",
        json={"name": "Zé", "phone": "(11) 98765-4321", "type": "drop_in", "position": "field"},
    )
    assert created.status_code == 201
    player = created.json()
    assert player["phone"] == "+5511987654321"

    detail = auth_client.get(f"/api/players/{player['id']}").json()
    assert detail["can_delete"] is True

    patched = auth_client.patch(
        f"/api/players/{player['id']}", json={"position": "goalkeeper", "name": None}
    )
    assert patched.status_code == 200
    assert patched.json()["position"] == "goalkeeper"
    assert patched.json()["name"] == "Zé"

    assert [p["name"] for p in auth_client.get("/api/players?type=drop_in").json()] == ["Zé"]
    auth_client.patch(f"/api/players/{player['id']}", json={"active": False})
    assert auth_client.get("/api/players").json() == []
    assert len(auth_client.get("/api/players?status=inactive").json()) == 1
    assert len(auth_client.get("/api/players?status=all").json()) == 1
    assert auth_client.delete(f"/api/players/{player['id']}").status_code == 204
    assert auth_client.get(f"/api/players/{player['id']}").status_code == 404


def test_api_erro_de_regra_vira_mensagem(auth_client):
    body = {"name": "A", "phone": "11987654321", "type": "drop_in", "position": "field"}
    assert auth_client.post("/api/players", json=body).status_code == 201
    response = auth_client.post("/api/players", json={**body, "name": "B"})
    assert response.status_code == 409
    assert response.json()["detail"] == "Este telefone já está cadastrado para A"

    response = auth_client.post("/api/players", json={**body, "phone": "123"})
    assert response.status_code == 400
    assert "Telefone inválido" in response.json()["detail"]


def test_api_vagas_de_mensalistas(auth_client):
    auth_client.post(
        "/api/players", json={"name": "G", "type": "monthly", "position": "goalkeeper"}
    )
    assert auth_client.get("/api/players/monthly-slots").json() == {
        "goalkeeper": {"used": 1, "total": 2},
        "field": {"used": 0, "total": 15},
    }
