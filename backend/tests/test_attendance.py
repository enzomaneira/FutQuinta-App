"""Regras da lista: vagas, goleiros, desistência em cima da hora, avulsos e
cobrança do avulso."""

import pytest

from app.models.enums import AttendanceStatus as S, ChargeStatus, GameStatus, Position
from app.services import attendance as att
from app.services import billing, games, queue
from app.services.errors import ConflictError, DomainError
from tests.helpers import GAME_DAY, make_squad, sp

GK, FIELD = Position.GOALKEEPER, Position.FIELD
TUE = sp(17, 11)  # terça, lista já aberta


@pytest.fixture
def full_game(db, make_player):
    """Jogo com 17 mensalistas pendentes (2 goleiros + 15 de linha)."""
    squad = make_squad(make_player)
    game = games.create_game(db, GAME_DAY)
    return game, squad


def status_of(db, game, player):
    return att.find_attendance(db, game.id, player.id).status


def charge_of(db, game, player):
    return billing.find_drop_in_charge(db, player.id, game)


# --- vagas ---


def test_lista_cheia_nao_tem_vaga_para_avulso(db, full_game, make_player):
    game, _ = full_game
    avulso = make_player("Avulso")
    queue.join_queue(db, game.id, avulso.id, now=TUE)
    usage = att.slot_usage(db, game)
    assert (usage[FIELD].pending, usage[FIELD].free) == (15, 0)
    with pytest.raises(ConflictError, match="Não há vaga de linha"):
        att.confirm_player(db, game.id, avulso.id, now=TUE)


def test_pendente_confirma_sem_precisar_de_vaga_livre(db, full_game):
    game, squad = full_game
    player = squad["field"][0]
    att.confirm_player(db, game.id, player.id, now=TUE)
    assert status_of(db, game, player) == S.CONFIRMED


def test_desmarcar_libera_vaga_na_hora_para_o_avulso(db, full_game, make_player):
    game, squad = full_game
    a1, a2 = make_player("Primeiro"), make_player("Segundo")
    queue.join_queue(db, game.id, a1.id, now=sp(17, 12))
    queue.join_queue(db, game.id, a2.id, now=sp(17, 13))

    att.cancel_player(db, game.id, squad["field"][0].id, now=sp(18, 9))
    assert att.slot_usage(db, game)[FIELD].free == 1

    att.call_next(db, game.id, FIELD, now=sp(18, 10))
    assert status_of(db, game, a1) == S.CONFIRMED  # primeiro da fila
    assert status_of(db, game, a2) == S.QUEUED
    assert att.slot_usage(db, game)[FIELD].free == 0


def test_avulso_confirmado_gera_cobranca_de_25(db, full_game, make_player):
    game, squad = full_game
    avulso = make_player("Avulso")
    att.cancel_player(db, game.id, squad["field"][0].id, now=TUE)
    queue.join_queue(db, game.id, avulso.id, now=TUE)
    att.confirm_player(db, game.id, avulso.id, now=TUE)

    charge = charge_of(db, game, avulso)
    assert charge.amount_cents == 2500
    assert charge.status == ChargeStatus.PENDING
    assert charge.due_date == GAME_DAY
    assert charge.game_id == game.id


def test_mensalista_nao_gera_cobranca_avulsa(db, full_game):
    game, squad = full_game
    player = squad["field"][0]
    att.cancel_player(db, game.id, player.id, now=TUE)
    att.confirm_player(db, game.id, player.id, now=TUE)  # voltou atrás
    assert status_of(db, game, player) == S.CONFIRMED
    assert charge_of(db, game, player) is None


# --- goleiros ---


def test_vaga_de_linha_nao_aceita_goleiro(db, full_game, make_player):
    game, squad = full_game
    goleiro_avulso = make_player("Goleiro avulso", position=GK)
    queue.join_queue(db, game.id, goleiro_avulso.id, now=TUE)
    att.cancel_player(db, game.id, squad["field"][0].id, now=TUE)  # vaga de LINHA
    with pytest.raises(ConflictError, match="vaga de goleiro"):
        att.confirm_player(db, game.id, goleiro_avulso.id, now=TUE)
    with pytest.raises(DomainError, match="Não há linha na fila"):
        att.call_next(db, game.id, FIELD, now=TUE)


def test_vaga_de_goleiro_so_para_goleiro(db, full_game, make_player):
    game, squad = full_game
    linha_avulso = make_player("Linha avulso")
    goleiro_avulso = make_player("Goleiro avulso", position=GK)
    queue.join_queue(db, game.id, linha_avulso.id, now=sp(17, 12))
    queue.join_queue(db, game.id, goleiro_avulso.id, now=sp(17, 13))
    att.cancel_player(db, game.id, squad["gk"][0].id, now=TUE)

    with pytest.raises(ConflictError, match="vaga de linha"):
        att.confirm_player(db, game.id, linha_avulso.id, now=TUE)
    att.call_next(db, game.id, GK, now=TUE)
    assert status_of(db, game, goleiro_avulso) == S.CONFIRMED


def test_contagem_de_goleiros(db, full_game):
    game, squad = full_game
    att.confirm_player(db, game.id, squad["gk"][0].id, now=TUE)
    att.cancel_player(db, game.id, squad["gk"][1].id, now=TUE)
    usage = att.slot_usage(db, game)[GK]
    assert (usage.capacity, usage.confirmed, usage.pending, usage.free) == (2, 1, 0, 1)


# --- desistência em cima da hora ---


def test_desmarcar_antes_das_18h_nao_e_em_cima_da_hora(db, full_game):
    game, squad = full_game
    player = squad["field"][0]
    att.confirm_player(db, game.id, player.id, now=TUE)
    attendance = att.cancel_player(db, game.id, player.id, now=sp(19, 17, 59))
    assert attendance.status == S.CANCELLED
    assert attendance.late_cancellation is False


def test_desmarcar_a_partir_das_18h_e_em_cima_da_hora(db, full_game):
    game, squad = full_game
    player = squad["field"][0]
    att.confirm_player(db, game.id, player.id, now=TUE)
    attendance = att.cancel_player(db, game.id, player.id, now=sp(19, 18, 0))
    assert attendance.late_cancellation is True


def test_sair_da_fila_nao_e_desistencia(db, full_game, make_player):
    game, _ = full_game
    avulso = make_player("Avulso")
    queue.join_queue(db, game.id, avulso.id, now=TUE)
    with pytest.raises(DomainError, match="Tirar da fila"):
        att.cancel_player(db, game.id, avulso.id, now=sp(19, 20))
    queue.leave_queue(db, game.id, avulso.id)
    assert att.find_attendance(db, game.id, avulso.id) is None  # não conta como desmarcação


def test_reconfirmar_limpa_a_marca_de_em_cima_da_hora(db, full_game):
    game, squad = full_game
    player = squad["field"][0]
    att.cancel_player(db, game.id, player.id, now=sp(19, 18, 30))
    attendance = att.confirm_player(db, game.id, player.id, now=sp(19, 18, 40))
    assert attendance.late_cancellation is False


# --- avulso que não vai não paga ---


def test_avulso_que_desmarca_fica_isento(db, full_game, make_player):
    game, squad = full_game
    avulso = make_player("Avulso")
    att.cancel_player(db, game.id, squad["field"][0].id, now=TUE)
    att.confirm_player(db, game.id, avulso.id, now=TUE)
    att.cancel_player(db, game.id, avulso.id, now=sp(19, 19))
    assert charge_of(db, game, avulso).status == ChargeStatus.WAIVED
    # Voltou e confirmou de novo: volta a ser cobrado (sem duplicar)
    att.confirm_player(db, game.id, avulso.id, now=sp(19, 19, 30))
    assert charge_of(db, game, avulso).status == ChargeStatus.PENDING


def test_cobranca_paga_nao_e_isentada(db, full_game, make_player):
    game, squad = full_game
    avulso = make_player("Avulso")
    att.cancel_player(db, game.id, squad["field"][0].id, now=TUE)
    att.confirm_player(db, game.id, avulso.id, now=TUE)
    charge_of(db, game, avulso).status = ChargeStatus.PAID
    db.commit()
    att.cancel_player(db, game.id, avulso.id, now=TUE)
    assert charge_of(db, game, avulso).status == ChargeStatus.PAID


# --- mensalista que volta atrás ---


def test_liberado_volta_se_houver_vaga(db, full_game):
    game, squad = full_game
    games.run_due_transitions(db, now=sp(19, 12))  # todos pendentes liberados
    player = squad["field"][0]
    assert status_of(db, game, player) == S.RELEASED
    att.confirm_player(db, game.id, player.id, now=sp(19, 13))
    assert status_of(db, game, player) == S.CONFIRMED


def test_desmarcou_e_a_vaga_foi_ocupada(db, full_game, make_player):
    game, squad = full_game
    player = squad["field"][0]
    att.cancel_player(db, game.id, player.id, now=TUE)
    att.confirm_player(db, game.id, make_player("Avulso").id, now=TUE)
    with pytest.raises(ConflictError):
        att.confirm_player(db, game.id, player.id, now=TUE)


# --- substituição ---


def test_substituir_mensalista_por_avulso(db, full_game, make_player):
    game, squad = full_game
    out, avulso = squad["field"][0], make_player("Avulso")
    queue.join_queue(db, game.id, avulso.id, now=TUE)
    att.substitute(db, game.id, out.id, avulso.id, now=TUE)
    assert status_of(db, game, out) == S.CANCELLED
    assert status_of(db, game, avulso) == S.CONFIRMED


def test_substituicao_invalida_nao_altera_nada(db, full_game, make_player):
    game, squad = full_game
    out, goleiro = squad["field"][0], make_player("Goleiro avulso", position=GK)
    att.confirm_player(db, game.id, out.id, now=TUE)
    with pytest.raises(ConflictError):
        att.substitute(db, game.id, out.id, goleiro.id, now=TUE)
    assert status_of(db, game, out) == S.CONFIRMED


# --- depois do jogo, cancelamento, coletes ---


def test_presenca_so_depois_do_jogo(db, full_game):
    game, squad = full_game
    with pytest.raises(DomainError, match="depois do jogo"):
        att.set_presence(db, game.id, squad["field"][0].id, False)


def test_falta_de_avulso_isenta_cobranca(db, full_game, make_player):
    game, squad = full_game
    avulso = make_player("Avulso")
    att.cancel_player(db, game.id, squad["field"][0].id, now=TUE)
    att.confirm_player(db, game.id, avulso.id, now=TUE)
    games.run_due_transitions(db, now=sp(19, 23, 30))
    assert status_of(db, game, avulso) == S.PRESENT

    att.set_presence(db, game.id, avulso.id, False)
    assert status_of(db, game, avulso) == S.ABSENT
    assert charge_of(db, game, avulso).status == ChargeStatus.WAIVED
    att.set_presence(db, game.id, avulso.id, True, now=sp(19, 23, 40))
    assert charge_of(db, game, avulso).status == ChargeStatus.PENDING


def test_jogo_realizado_nao_aceita_mudancas_na_lista(db, full_game):
    game, squad = full_game
    games.run_due_transitions(db, now=sp(19, 23, 30))
    with pytest.raises(DomainError, match="já foi realizado"):
        att.confirm_player(db, game.id, squad["field"][0].id)


def test_cancelar_jogo_isenta_avulsos_e_reabrir_cobra_de_novo(db, full_game, make_player):
    game, squad = full_game
    avulso = make_player("Avulso")
    att.cancel_player(db, game.id, squad["field"][0].id, now=TUE)
    att.confirm_player(db, game.id, avulso.id, now=TUE)

    assert games.cancel_game(db, game.id).status == GameStatus.CANCELLED
    assert charge_of(db, game, avulso).status == ChargeStatus.WAIVED
    assert games.reopen_list(db, game.id, now=TUE).status == GameStatus.OPEN
    assert charge_of(db, game, avulso).status == ChargeStatus.PENDING


def test_fechar_e_reabrir_lista(db, full_game):
    game, _ = full_game
    assert games.close_list(db, game.id).status == GameStatus.CLOSED
    with pytest.raises(DomainError):
        games.close_list(db, game.id)
    assert games.reopen_list(db, game.id).status == GameStatus.OPEN


def test_coletes(db, full_game):
    game, squad = full_game
    player = squad["field"][3]
    assert games.set_bib_player(db, game.id, player.id).bib_player_id == player.id
    assert games.set_bib_player(db, game.id, None).bib_player_id is None
