from app.models.enums import UserRole
from app.services import attendance as att
from app.services import games
from app.services.auth import create_user
from app.core.security import create_access_token
from tests.helpers import GAME_DAY, make_squad


def test_jogo_atual_vazio(auth_client):
    response = auth_client.get("/api/games/current")
    assert response.status_code == 200
    assert response.json() is None


def test_detalhe_do_jogo(auth_client, db, make_player):
    squad = make_squad(make_player, goalkeepers=2, field=3)
    game = games.create_game(db, GAME_DAY)
    att.confirm_player(db, game.id, squad["gk"][0].id)
    att.cancel_player(db, game.id, squad["gk"][1].id)

    body = auth_client.get(f"/api/games/{game.id}").json()
    assert body["local_date"] == "2026-11-19"
    assert (body["start_time"], body["end_time"]) == ("21:30", "23:00")
    assert body["slots"]["goalkeeper"] == {"capacity": 2, "confirmed": 1, "pending": 0, "free": 1}
    assert [a["name"] for a in body["lineup"]["goalkeeper"]] == ["Goleiro 1"]
    assert [a["name"] for a in body["out"]] == ["Goleiro 2"]
    assert "Falta 1 goleiro confirmado" in body["alerts"]
    assert "3 mensalistas ainda não responderam" in body["alerts"]
    assert body["occupied"] == 4 and body["capacity"] == 17


def test_fluxo_pela_api(auth_client, db, make_player):
    squad = make_squad(make_player)
    avulso = make_player("Avulso")
    game_id = auth_client.post("/api/games", json={"date": "2026-11-19"}).json()["id"]
    assert auth_client.post("/api/games", json={"date": "2026-11-19"}).status_code == 409

    url = f"/api/games/{game_id}"
    body = auth_client.post(f"{url}/queue", json={"player_id": avulso.id}).json()
    assert body["queue"]["field"][0]["queue_position"] == 1

    # Sem vaga ainda
    response = auth_client.post(f"{url}/call-next", json={"position": "field"})
    assert response.status_code == 409

    auth_client.post(f"{url}/players/{squad['field'][0].id}/cancel")
    body = auth_client.post(f"{url}/call-next", json={"position": "field"}).json()
    assert avulso.id in [a["player_id"] for a in body["lineup"]["field"]]
    assert body["queue"]["field"] == []

    body = auth_client.put(f"{url}/bib", json={"player_id": avulso.id}).json()
    assert body["bib_player"] == {"id": avulso.id, "name": "Avulso"}
    assert auth_client.post(f"{url}/close").json()["status"] == "closed"
    assert auth_client.post(f"{url}/cancel").json()["status"] == "cancelled"


def test_calendario(auth_client, db):
    games.create_game(db, GAME_DAY)
    body = auth_client.get("/api/calendar?month=2026-11").json()
    assert body["month"] == "2026-11"
    assert (body["game_weekday"], body["due_day"]) == (3, 15)
    assert [g["local_date"] for g in body["games"]] == ["2026-11-19"]
    assert auth_client.get("/api/calendar?month=2026-12").json()["games"] == []
    assert auth_client.get("/api/calendar?month=xx").status_code == 400


# --- configurações ---


def test_configuracoes(auth_client):
    assert auth_client.get("/api/settings").json()["drop_in_fee_cents"] == 2500
    body = auth_client.patch(
        "/api/settings", json={"drop_in_fee_cents": 3000, "pix_key": "chave@pix"}
    ).json()
    assert (body["drop_in_fee_cents"], body["pix_key"]) == (3000, "chave@pix")


def test_configuracoes_invalidas(auth_client):
    assert auth_client.patch("/api/settings", json={"game_start_time": "25:00"}).status_code == 422
    assert auth_client.patch("/api/settings", json={"game_weekday": 9}).status_code == 422
    response = auth_client.patch("/api/settings", json={"confirmation_deadline_time": "19:00"})
    assert response.status_code == 400
    assert "prazo de confirmação" in response.json()["detail"]


# --- organizadores ---


def test_organizador_comum_nao_cria_organizadores(auth_client):
    response = auth_client.post(
        "/api/users", json={"email": "novo@exemplo.com", "password": "senha-forte-1"}
    )
    assert response.status_code == 403


def test_admin_gerencia_organizadores(client, db):
    admin = create_user(db, "admin@exemplo.com", "senha-forte-1", UserRole.ADMIN)
    client.headers["Authorization"] = f"Bearer {create_access_token(admin.id)}"

    created = client.post(
        "/api/users", json={"email": "Novo@Exemplo.com", "password": "senha-forte-2"}
    )
    assert created.status_code == 201
    assert created.json()["email"] == "novo@exemplo.com"
    assert client.post(
        "/api/users", json={"email": "novo@exemplo.com", "password": "senha-forte-2"}
    ).status_code == 409
    assert client.post(
        "/api/users", json={"email": "x@exemplo.com", "password": "curta"}
    ).status_code == 400

    user_id = created.json()["id"]
    assert client.patch(f"/api/users/{user_id}", json={"active": False}).json()["active"] is False
    assert client.patch(f"/api/users/{admin.id}", json={"active": False}).status_code == 400
    assert len(client.get("/api/users").json()) == 2
