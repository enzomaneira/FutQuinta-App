"""Geração de cobranças, atrasos, pagamentos, despesas e cálculo do caixa."""

from datetime import date

import pytest
from sqlalchemy import delete, select

from app.models.charge import Charge
from app.models.enums import (
    ChargeStatus,
    ChargeType,
    ExpenseCategory,
    ExpenseType,
    PaymentMethod,
    PlayerType,
    Position,
)
from app.models.expense import Expense
from app.models.job_run import JobRun
from app.services import attendance as att
from app.services import billing, cashbox, games
from app.services.errors import DomainError
from app.services.routines import run_finance_routines
from app.services.settings import update_settings
from tests.helpers import GAME_DAY, make_squad, sp

MONTHLY = PlayerType.MONTHLY


@pytest.fixture(autouse=True)
def clean_job_runs(db):
    # A migration marca o mês da implantação como "já gerado"; os testes
    # começam sem esse registro para controlar as datas
    db.execute(delete(JobRun))
    db.commit()


def monthly_charges(db, reference="2026-12"):
    return list(
        db.scalars(
            select(Charge).where(
                Charge.type == ChargeType.MONTHLY_FEE, Charge.reference == reference
            )
        )
    )


# --- geração de mensalidades ---


def test_dia_1_gera_mensalidades_dos_mensalistas_ativos(db, make_player):
    squad = make_squad(make_player)
    make_player("Avulso")
    inativo = make_player("Inativo", type=MONTHLY)
    inativo.active = False
    db.add(JobRun(name="monthly_billing", period="2026-11", details={}))  # novembro já feito
    db.commit()

    assert run_finance_routines(db, now=sp(30, 23, 59)).monthly_generated is None
    result = run_finance_routines(db, now=sp(1, 0, 5, month=12))
    assert result.monthly_generated == 17

    charges = monthly_charges(db)
    assert len(charges) == len(squad["gk"]) + len(squad["field"])
    assert {c.amount_cents for c in charges} == {5900}  # goleiro paga o mesmo
    assert {c.due_date for c in charges} == {date(2026, 12, 15)}
    assert {c.status for c in charges} == {ChargeStatus.PENDING}


def test_geracao_roda_uma_vez_por_mes(db, make_player):
    make_squad(make_player, goalkeepers=1, field=1)
    run_finance_routines(db, now=sp(1, 9, month=12))
    make_player("Novo", type=MONTHLY)  # entrou depois do dia 1
    assert run_finance_routines(db, now=sp(2, 9, month=12)).monthly_generated is None
    assert len(monthly_charges(db)) == 2
    # O botão "gerar as que faltam" cobre o mensalista novo, sem duplicar
    assert billing.generate_monthly_fees(db, 2026, 12).created == 1
    assert billing.generate_monthly_fees(db, 2026, 12).created == 0
    assert len(monthly_charges(db)) == 3


def test_servidor_fora_no_dia_1_gera_depois(db, make_player):
    make_squad(make_player, goalkeepers=1, field=1)
    assert run_finance_routines(db, now=sp(3, 14, month=12)).monthly_generated == 2


def test_quadra_lancada_no_dia_1_se_tiver_valor(db, make_player):
    run_finance_routines(db, now=sp(1, 9, month=12))
    assert db.scalars(select(Expense)).all() == []  # valor padrão é zero

    update_settings(db, {"court_monthly_cents": 120000})
    db.execute(delete(JobRun))
    db.commit()
    assert run_finance_routines(db, now=sp(1, 9, month=12)).court_expense is True
    run_finance_routines(db, now=sp(2, 9, month=12))
    expense = db.scalar(select(Expense))
    assert (expense.amount_cents, expense.category, expense.type) == (
        120000,
        ExpenseCategory.COURT,
        ExpenseType.FIXED,
    )
    assert expense.reference == "2026-12"
    assert len(db.scalars(select(Expense)).all()) == 1


def test_configuracoes_de_valor_e_vencimento(db, make_player):
    make_player("M", type=MONTHLY)
    update_settings(db, {"monthly_fee_cents": 6500, "monthly_due_day": 10})
    billing.generate_monthly_fees(db, 2026, 12)
    charge = monthly_charges(db)[0]
    assert (charge.amount_cents, charge.due_date) == (6500, date(2026, 12, 10))


# --- atraso ---


def test_mensalidade_atrasa_no_dia_16(db, make_player):
    make_player("M", type=MONTHLY)
    billing.generate_monthly_fees(db, 2026, 12)
    run_finance_routines(db, now=sp(15, 23, 59, month=12))
    assert monthly_charges(db)[0].status == ChargeStatus.PENDING
    assert run_finance_routines(db, now=sp(16, 0, 1, month=12)).overdue == 1
    db.refresh(monthly_charges(db)[0])
    assert monthly_charges(db)[0].status == ChargeStatus.OVERDUE


def test_paga_nao_atrasa(db, make_player):
    make_player("M", type=MONTHLY)
    billing.generate_monthly_fees(db, 2026, 12)
    billing.register_payment(db, monthly_charges(db)[0].id)
    run_finance_routines(db, now=sp(20, 9, month=12))
    assert monthly_charges(db)[0].status == ChargeStatus.PAID


def test_avulso_atrasa_no_dia_seguinte_ao_jogo(db, make_player):
    game = games.create_game(db, GAME_DAY)
    avulso = make_player("Avulso")
    att.confirm_player(db, game.id, avulso.id, now=sp(18, 9))
    run_finance_routines(db, now=sp(19, 23, 30))
    charge = billing.find_drop_in_charge(db, avulso.id, game)
    assert charge.status == ChargeStatus.PENDING
    run_finance_routines(db, now=sp(20, 8))
    db.refresh(charge)
    assert charge.status == ChargeStatus.OVERDUE


# --- pagamentos ---


def test_pagar_desfazer_isentar(db, make_player):
    make_player("M", type=MONTHLY)
    billing.generate_monthly_fees(db, 2026, 12)
    charge_id = monthly_charges(db)[0].id

    payment = billing.register_payment(db, charge_id, method=PaymentMethod.CASH)
    assert (payment.amount_cents, payment.method) == (5900, PaymentMethod.CASH)
    with pytest.raises(DomainError, match="já está paga"):
        billing.register_payment(db, charge_id)

    undone = billing.undo_payment(db, charge_id, today=date(2026, 12, 20))
    assert undone.status == ChargeStatus.OVERDUE  # já passou do vencimento
    assert cashbox.cash_summary(db).received_cents == 0

    assert billing.waive(db, charge_id).status == ChargeStatus.WAIVED
    with pytest.raises(DomainError, match="isenta"):
        billing.register_payment(db, charge_id)
    assert billing.unwaive(db, charge_id, today=date(2026, 12, 1)).status == ChargeStatus.PENDING


def test_situacao_de_pagamento_por_jogador(db, make_player):
    a = make_player("A", type=MONTHLY)
    b = make_player("B", type=MONTHLY)
    c = make_player("C", type=MONTHLY)
    billing.generate_monthly_fees(db, 2026, 11)
    billing.generate_monthly_fees(db, 2026, 12)
    billing.mark_overdue(db, date(2026, 12, 1))  # novembro atrasou
    for charge in db.scalars(select(Charge).where(Charge.player_id == c.id)):
        billing.register_payment(db, charge.id)
    status = billing.payment_status_by_player(db)
    assert status[a.id] == "overdue"
    assert status[b.id] == "overdue"
    assert c.id not in status


# --- caixa ---


def test_caixa_soma_recebimentos_e_tira_despesas(db, make_player):
    assert cashbox.cash_summary(db).balance_cents == 24500  # saldo inicial

    make_squad(make_player, goalkeepers=1, field=1)
    billing.generate_monthly_fees(db, 2026, 12)
    for charge in monthly_charges(db):
        billing.register_payment(db, charge.id)  # 2 x 59
    cashbox.create_expense(
        db, day=date(2026, 12, 3), description="Bola nova", category=ExpenseCategory.BALL, amount_cents=15000
    )
    summary = cashbox.cash_summary(db)
    assert (summary.received_cents, summary.expenses_cents) == (11800, 15000)
    assert summary.balance_cents == 24500 + 11800 - 15000


def test_caixa_inclui_avulso_e_ignora_isentos(db, make_player):
    game = games.create_game(db, GAME_DAY)
    pagou, faltou = make_player("Pagou"), make_player("Faltou")
    for p in (pagou, faltou):
        att.confirm_player(db, game.id, p.id, now=sp(18, 9))
    att.cancel_player(db, game.id, faltou.id, now=sp(19, 10))
    billing.register_payment(db, billing.find_drop_in_charge(db, pagou.id, game).id)
    assert cashbox.cash_summary(db).balance_cents == 24500 + 2500


def test_despesa_invalida(db):
    with pytest.raises(DomainError):
        cashbox.create_expense(
            db, day=date(2026, 12, 1), description="x", category=ExpenseCategory.OTHER, amount_cents=0
        )


def test_extrato_com_saldo_corrido(db, make_player):
    make_player("M", type=MONTHLY)
    billing.generate_monthly_fees(db, 2026, 11)
    charge = monthly_charges(db, "2026-11")[0]
    billing.register_payment(db, charge.id, paid_at=sp(10, 20))
    cashbox.create_expense(
        db, day=date(2026, 11, 20), description="Coletes", category=ExpenseCategory.BIBS, amount_cents=8000
    )
    cashbox.create_expense(
        db, day=date(2026, 12, 2), description="Bola", category=ExpenseCategory.BALL, amount_cents=1000
    )

    opening, entries = cashbox.statement(db, date(2026, 11, 1), date(2026, 11, 30))
    assert opening == 24500
    assert [(e.description, e.amount_cents, e.balance_cents) for e in entries] == [
        ("Coletes", -8000, 24500 + 5900 - 8000),
        ("Mensalidade 11/2026 — M", 5900, 24500 + 5900),
    ]
    opening_dec, entries_dec = cashbox.statement(db, date(2026, 12, 1), date(2026, 12, 31))
    assert opening_dec == 24500 + 5900 - 8000
    assert entries_dec[0].balance_cents == opening_dec - 1000


# --- API ---


def test_api_financeiro(auth_client, db, make_player):
    m = make_player("Mensalista", type=MONTHLY, position=Position.GOALKEEPER)
    created = auth_client.post("/api/finance/monthly-fees/generate", json={"month": "2026-12"})
    assert created.json() == {"month": "2026-12", "created": 1}

    fees = auth_client.get("/api/finance/monthly-fees?month=2026-12").json()
    assert [(f["player_name"], f["status"], f["amount_cents"]) for f in fees] == [
        ("Mensalista", "pending", 5900)
    ]
    players = auth_client.get("/api/players").json()
    assert players[0]["payment_status"] == "pending"

    paid = auth_client.post(f"/api/charges/{fees[0]['id']}/pay", json={"method": "cash"}).json()
    assert (paid["status"], paid["payment_method"]) == ("paid", "cash")
    assert auth_client.get(f"/api/players/{m.id}").json()["payment_status"] == "ok"
    assert auth_client.get("/api/finance/cash").json()["balance_cents"] == 24500 + 5900

    expense = auth_client.post(
        "/api/expenses",
        json={"date": "2026-12-05", "description": "", "category": "bibs", "amount_cents": 4000},
    )
    assert expense.status_code == 201
    assert expense.json()["description"] == "Coletes"
    assert [e["amount_cents"] for e in auth_client.get("/api/expenses?month=2026-12").json()] == [4000]

    statement = auth_client.get("/api/finance/statement?month=2026-12").json()
    assert ("Coletes", -4000) in [(e["description"], e["amount_cents"]) for e in statement["entries"]]
    assert auth_client.get("/api/finance/cash").json()["balance_cents"] == 24500 + 5900 - 4000
    assert auth_client.get("/api/finance/statement?month=xx").status_code == 400
