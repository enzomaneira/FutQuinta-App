from datetime import UTC, datetime, timedelta

import pytest

from app.models.enums import AttendanceStatus, GameStatus, PlayerType, Position
from app.services import queue
from app.services.errors import ConflictError, DomainError

T0 = datetime(2026, 11, 17, 13, 0, tzinfo=UTC)  # terça 10h em São Paulo


def minutes(n):
    return T0 + timedelta(minutes=n)


def names(attendances, db):
    from app.models.player import Player

    return [db.get(Player, a.player_id).name for a in attendances]


def test_fila_segue_ordem_de_candidatura(db, make_game, make_player):
    game = make_game()
    c = make_player("C")
    a = make_player("A")
    b = make_player("B")
    queue.join_queue(db, game.id, a.id, now=minutes(5))
    queue.join_queue(db, game.id, b.id, now=minutes(1))
    queue.join_queue(db, game.id, c.id, now=minutes(9))
    assert names(queue.list_queue(db, game.id), db) == ["B", "A", "C"]


def test_fila_separa_goleiros_e_linha(db, make_game, make_player):
    game = make_game()
    gk = make_player("Goleiro", position=Position.GOALKEEPER)
    field = make_player("Linha")
    queue.join_queue(db, game.id, field.id, now=minutes(1))
    queue.join_queue(db, game.id, gk.id, now=minutes(2))
    assert names(queue.list_queue(db, game.id, Position.GOALKEEPER), db) == ["Goleiro"]
    assert queue.next_in_queue(db, game.id, Position.FIELD).player_id == field.id


def test_entrar_de_novo_mantem_posicao(db, make_game, make_player):
    game = make_game()
    a, b = make_player("A"), make_player("B")
    queue.join_queue(db, game.id, a.id, now=minutes(1))
    queue.join_queue(db, game.id, b.id, now=minutes(2))
    queue.join_queue(db, game.id, a.id, now=minutes(3))  # repetido: ignora
    assert names(queue.list_queue(db, game.id), db) == ["A", "B"]


def test_quem_sai_e_volta_vai_para_o_fim(db, make_game, make_player):
    game = make_game()
    a, b = make_player("A"), make_player("B")
    queue.join_queue(db, game.id, a.id, now=minutes(1))
    queue.join_queue(db, game.id, b.id, now=minutes(2))
    queue.leave_queue(db, game.id, a.id)
    assert names(queue.list_queue(db, game.id), db) == ["B"]
    queue.join_queue(db, game.id, a.id, now=minutes(4))
    assert names(queue.list_queue(db, game.id), db) == ["B", "A"]


def test_mensalista_nao_entra_na_fila(db, make_game, make_player):
    game = make_game()
    m = make_player("M", type=PlayerType.MONTHLY)
    with pytest.raises(DomainError, match="Só avulsos"):
        queue.join_queue(db, game.id, m.id)


def test_inativo_nao_entra_na_fila(db, make_game, make_player):
    game = make_game()
    p = make_player("P")
    p.active = False
    db.commit()
    with pytest.raises(DomainError, match="inativo"):
        queue.join_queue(db, game.id, p.id)


@pytest.mark.parametrize("status", [GameStatus.PLAYED, GameStatus.CANCELLED])
def test_jogo_encerrado_nao_aceita_fila(db, make_game, make_player, status):
    game = make_game(status=status)
    with pytest.raises(DomainError, match="não aceita"):
        queue.join_queue(db, game.id, make_player("A").id)


def test_confirmado_nao_volta_para_fila(db, make_game, make_player):
    game = make_game()
    a = make_player("A")
    attendance = queue.join_queue(db, game.id, a.id)
    attendance.status = AttendanceStatus.CONFIRMED
    db.commit()
    with pytest.raises(ConflictError, match="já está na lista"):
        queue.join_queue(db, game.id, a.id)


def test_sair_sem_estar_na_fila(db, make_game, make_player):
    game = make_game()
    with pytest.raises(DomainError, match="não está na fila"):
        queue.leave_queue(db, game.id, make_player("A").id)
