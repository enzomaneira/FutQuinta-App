"""Estatísticas do perfil, histórico e tela Início."""

from datetime import date

from app.models.enums import PlayerType, Position
from app.services import attendance as att
from app.services import billing, games, queue
from app.services.stats import player_stats
from tests.helpers import make_squad, sp

THU1, THU2, THU3 = date(2026, 11, 19), date(2026, 11, 26), date(2026, 12, 3)


def play(db, day, *, now):
    """Encerra o jogo do dia (rotina das 23h)."""
    games.run_due_transitions(db, now=now)


def test_estatisticas_calculadas_a_partir_das_presencas(db, make_player):
    me = make_player("Eu", type=PlayerType.MONTHLY)
    make_squad(make_player, goalkeepers=2, field=0)

    # Jogo 1: confirmou e jogou; levou os coletes
    g1 = games.create_game(db, THU1)
    att.confirm_player(db, g1.id, me.id, now=sp(18, 9))
    games.set_bib_player(db, g1.id, me.id)
    play(db, THU1, now=sp(19, 23, 30))

    # Jogo 2: desmarcou em cima da hora
    g2 = games.create_game(db, THU2)
    att.confirm_player(db, g2.id, me.id, now=sp(25, 9))
    att.cancel_player(db, g2.id, me.id, now=sp(26, 19))
    play(db, THU2, now=sp(26, 23, 30))

    # Jogo 3: confirmou e faltou sem avisar
    g3 = games.create_game(db, THU3)
    att.confirm_player(db, g3.id, me.id, now=sp(2, 9, month=12))
    play(db, THU3, now=sp(3, 23, 30, month=12))
    att.set_presence(db, g3.id, me.id, False)

    stats = player_stats(db, me.id)
    assert stats.games_played == 1
    assert stats.cancellations == 1
    assert stats.late_cancellations == 1
    assert stats.no_shows == 1
    assert stats.bib_times == 1
    assert stats.attendance_base == 3
    assert round(stats.attendance_rate, 2) == 0.33


def test_jogo_cancelado_nao_conta(db, make_player):
    me = make_player("Eu", type=PlayerType.MONTHLY)
    g = games.create_game(db, THU1)
    att.cancel_player(db, g.id, me.id, now=sp(18, 9))
    games.set_bib_player(db, g.id, me.id)
    games.cancel_game(db, g.id)
    stats = player_stats(db, me.id)
    assert (stats.cancellations, stats.bib_times, stats.attendance_rate) == (0, 0, None)


def test_nao_respondeu_ate_o_prazo(db, make_player):
    me = make_player("Eu", type=PlayerType.MONTHLY)
    games.create_game(db, THU1)
    games.run_due_transitions(db, now=sp(19, 12))
    assert player_stats(db, me.id).no_response == 1


def test_fila_nao_entra_nas_estatisticas(db, make_player):
    avulso = make_player("Avulso")
    g = games.create_game(db, THU1)
    queue.join_queue(db, g.id, avulso.id, now=sp(17, 11))
    queue.leave_queue(db, g.id, avulso.id)
    queue.join_queue(db, g.id, avulso.id, now=sp(17, 12))
    play(db, THU1, now=sp(19, 23, 30))
    stats = player_stats(db, avulso.id)
    assert (stats.cancellations, stats.attendance_base, stats.attendance_rate) == (0, 0, None)


# --- API ---


def test_api_perfil(auth_client, db, make_player):
    me = make_player("Eu", type=PlayerType.MONTHLY, position=Position.GOALKEEPER)
    billing.generate_monthly_fees(db, 2026, 11)
    billing.generate_monthly_fees(db, 2026, 12)
    november = billing.list_charges(db, reference="2026-11")[0][0]
    billing.register_payment(db, november.id)
    g = games.create_game(db, THU1)
    att.confirm_player(db, g.id, me.id, now=sp(18, 9))

    body = auth_client.get(f"/api/players/{me.id}/profile").json()
    assert body["stats"]["games_played"] == 0
    assert [c["reference"] for c in body["open_charges"]] == ["2026-12"]
    assert [p["reference"] for p in body["payments"]] == ["2026-11"]
    assert body["recent_games"][0] == {
        "game_id": g.id,
        "local_date": "2026-11-19",
        "game_status": "open",
        "status": "confirmed",
        "late_cancellation": False,
    }
    assert auth_client.get("/api/players/999999/profile").status_code == 404


def test_api_historico_e_valores_do_jogo(auth_client, db, make_player):
    pagou, nao_pagou = make_player("Pagou"), make_player("Não pagou")
    g = games.create_game(db, date(2026, 10, 1))  # jogo no passado
    for p in (pagou, nao_pagou):
        att.confirm_player(db, g.id, p.id, now=sp(30, 9, month=9))
    billing.register_payment(db, billing.find_drop_in_charge(db, pagou.id, g).id)

    history = auth_client.get("/api/games/history").json()
    assert [h["id"] for h in history] == [g.id]

    values = auth_client.get(f"/api/games/{g.id}/charges").json()
    assert (values["received_cents"], values["expected_cents"]) == (2500, 5000)
    assert [c["player_name"] for c in values["charges"]] == ["Não pagou", "Pagou"]


def test_api_inicio(auth_client, db, make_player):
    make_player("Mensalista", type=PlayerType.MONTHLY)
    billing.generate_monthly_fees(db, 2026, 12)
    body = auth_client.get("/api/home").json()
    assert body["cash"]["balance_cents"] == 24500
    assert body["venue"]["address"].startswith("Rua Dona Brígida, 375")
    assert (body["open_charges"]["count"], body["open_charges"]["total_cents"]) == (1, 5900)
    assert body["game"] is None or "slots" in body["game"]
