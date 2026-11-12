import pytest

from app.core.security import create_access_token
from app.services.auth import EmailAlreadyUsedError, create_user

EMAIL = "organizador@exemplo.com"
PASSWORD = "senha-forte-123"


@pytest.fixture
def organizer(db):
    return create_user(db, EMAIL, PASSWORD)


def login(client, email, password):
    return client.post("/api/auth/login", json={"email": email, "password": password})


def test_login_ok_devolve_token(client, organizer):
    response = login(client, EMAIL, PASSWORD)
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]


def test_login_ignora_maiusculas_no_email(client, organizer):
    assert login(client, EMAIL.upper(), PASSWORD).status_code == 200


def test_login_senha_errada(client, organizer):
    response = login(client, EMAIL, "errada")
    assert response.status_code == 401
    assert response.json()["detail"] == "E-mail ou senha incorretos"


def test_login_email_inexistente(client):
    assert login(client, "ninguem@exemplo.com", PASSWORD).status_code == 401


def test_login_usuario_inativo(client, db, organizer):
    organizer.active = False
    db.commit()
    assert login(client, EMAIL, PASSWORD).status_code == 401


def test_me_com_token(client, organizer):
    token = login(client, EMAIL, PASSWORD).json()["access_token"]
    response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json() == {"id": organizer.id, "email": EMAIL, "role": "organizer"}


def test_me_sem_token(client):
    assert client.get("/api/auth/me").status_code == 401


def test_me_token_invalido(client):
    response = client.get("/api/auth/me", headers={"Authorization": "Bearer lixo"})
    assert response.status_code == 401


def test_me_usuario_removido(client, db, organizer):
    token = create_access_token(organizer.id)
    db.delete(organizer)
    db.commit()
    response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


def test_senha_fica_com_hash(organizer):
    assert organizer.password_hash != PASSWORD
    assert organizer.password_hash.startswith("$argon2")


def test_email_duplicado(db, organizer):
    with pytest.raises(EmailAlreadyUsedError):
        create_user(db, EMAIL.upper(), "outra-senha-123")
