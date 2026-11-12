"""Rotinas por horário: abrir a lista (terça 10h), liberar pendentes
(quinta 12h) e encerrar o jogo (após 23h)."""

from sqlalchemy import select

from app.models.attendance import Attendance
from app.models.enums import AttendanceStatus as S, GameStatus, PlayerType
from app.models.game import Game
from app.services import attendance as att
from app.services import games
from app.services.settings import update_settings
from tests.helpers import GAME_DAY, make_squad, sp


def statuses(db, game_id):
    return sorted(
        a.status
        for a in db.scalars(select(Attendance).where(Attendance.game_id == game_id))
    )


def all_games(db):
    return list(db.scalars(select(Game)))


def test_lista_abre_terca_10h_com_mensalistas_pendentes(db, make_player):
    squad = make_squad(make_player)
    make_player("Avulso")  # avulso não entra na lista
    inativo = make_player("Inativo", type=PlayerType.MONTHLY)
    inativo.active = False
    db.commit()

    assert games.run_due_transitions(db, now=sp(17, 9, 59)).opened_game_id is None
    assert all_games(db) == []

    result = games.run_due_transitions(db, now=sp(17, 10, 0))
    game = db.get(Game, result.opened_game_id)
    assert game.status == GameStatus.OPEN
    assert game.starts_at == sp(19, 21, 30)
    assert game.ends_at == sp(19, 23, 0)
    assert game.confirmation_deadline == sp(19, 12, 0)
    assert statuses(db, game.id) == [S.PENDING] * (len(squad["gk"]) + len(squad["field"]))


def test_abrir_lista_e_idempotente(db, make_player):
    make_squad(make_player)
    games.run_due_transitions(db, now=sp(17, 10, 0))
    games.run_due_transitions(db, now=sp(17, 10, 1))
    games.run_due_transitions(db, now=sp(18, 15, 0))
    assert len(all_games(db)) == 1


def test_nao_abre_sozinho_depois_do_prazo_de_confirmacao(db, make_player):
    # Ex.: servidor sobe pela primeira vez na quinta à tarde
    assert games.run_due_transitions(db, now=sp(19, 12, 0)).opened_game_id is None
    assert games.run_due_transitions(db, now=sp(19, 17, 50)).opened_game_id is None
    assert all_games(db) == []


def test_jogo_cancelado_nao_e_recriado(db, make_player):
    result = games.run_due_transitions(db, now=sp(17, 10, 0))
    games.cancel_game(db, result.opened_game_id)
    assert games.run_due_transitions(db, now=sp(17, 11, 0)).opened_game_id is None
    assert len(all_games(db)) == 1


def test_lista_criada_manualmente_nao_duplica(db, make_player):
    games.create_game(db, GAME_DAY)
    assert games.run_due_transitions(db, now=sp(17, 10, 0)).opened_game_id is None


def test_configuracao_muda_o_dia_de_abertura(db, make_player):
    update_settings(db, {"list_open_days_before": 1, "list_open_time": "08:00"})
    assert games.run_due_transitions(db, now=sp(17, 10, 0)).opened_game_id is None
    assert games.run_due_transitions(db, now=sp(18, 8, 0)).opened_game_id is not None


def test_quinta_12h_pendentes_perdem_a_vaga(db, make_player):
    squad = make_squad(make_player)
    game_id = games.run_due_transitions(db, now=sp(17, 10, 0)).opened_game_id
    confirmado = squad["field"][0]
    att.confirm_player(db, game_id, confirmado.id, now=sp(18, 9, 0))

    assert games.run_due_transitions(db, now=sp(19, 11, 59)).released == 0
    result = games.run_due_transitions(db, now=sp(19, 12, 0))
    assert result.released == 16
    assert att.find_attendance(db, game_id, confirmado.id).status == S.CONFIRMED
    assert statuses(db, game_id).count(S.RELEASED) == 16


def test_apos_o_jogo_confirmados_viram_compareceu(db, make_player):
    squad = make_squad(make_player, goalkeepers=1, field=2)
    game_id = games.run_due_transitions(db, now=sp(17, 10, 0)).opened_game_id
    att.confirm_player(db, game_id, squad["gk"][0].id, now=sp(18, 9, 0))
    att.confirm_player(db, game_id, squad["field"][0].id, now=sp(18, 9, 0))

    assert games.run_due_transitions(db, now=sp(19, 22, 59)).closed_games == 0
    assert games.run_due_transitions(db, now=sp(19, 23, 0)).closed_games == 1
    game = db.get(Game, game_id)
    db.refresh(game)
    assert game.status == GameStatus.PLAYED
    assert statuses(db, game_id) == [S.PRESENT, S.PRESENT, S.RELEASED]
    # Rodar de novo não muda nada
    assert games.run_due_transitions(db, now=sp(20, 1, 0)).changed is False


def test_recupera_atraso_se_o_servidor_ficou_fora(db, make_player):
    make_squad(make_player, goalkeepers=1, field=1)
    game_id = games.run_due_transitions(db, now=sp(17, 10, 0)).opened_game_id
    # Servidor volta só na sexta: libera e encerra na mesma execução
    result = games.run_due_transitions(db, now=sp(20, 9, 0))
    assert result.released == 2
    assert result.closed_games == 1
    assert db.get(Game, game_id).status == GameStatus.PLAYED
