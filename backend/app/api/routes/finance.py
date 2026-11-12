"""Rotas do Financeiro. Só traduzem HTTP <-> serviços; as regras ficam em
app/services/{billing,cashbox}.py."""

import calendar
from datetime import date

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.api.deps import DbSession, get_current_user
from app.core.clock import now_utc
from app.models.charge import Charge
from app.models.enums import ChargeType
from app.models.player import Player
from app.schemas.finance import (
    CashOut,
    ChargeOut,
    ExpenseIn,
    ExpenseOut,
    GenerateIn,
    GenerateOut,
    PayIn,
    StatementEntryOut,
    StatementOut,
)
from app.services import billing, cashbox
from app.services.schedule import local_date_of

router = APIRouter(tags=["finance"], dependencies=[Depends(get_current_user)])


def _month_bounds(month: str | None) -> tuple[str, date, date]:
    if month:
        year, mon = billing.parse_month(month)
    else:
        today = local_date_of(now_utc())
        year, mon = today.year, today.month
    first = date(year, mon, 1)
    last = date(year, mon, calendar.monthrange(year, mon)[1])
    return billing.month_reference(year, mon), first, last


def charge_out(db: Session, charge: Charge, player: Player) -> ChargeOut:
    payment = billing.last_payment(db, charge.id) if charge.status.value == "paid" else None
    return ChargeOut(
        id=charge.id,
        player_id=player.id,
        player_name=player.name,
        player_position=player.position,
        type=charge.type,
        reference=charge.reference,
        amount_cents=charge.amount_cents,
        due_date=charge.due_date,
        status=charge.status,
        game_id=charge.game_id,
        paid_at=payment.paid_at if payment else None,
        payment_method=payment.method if payment else None,
    )


def _charge_by_id(db: Session, charge_id: int) -> ChargeOut:
    charge = billing.get_charge(db, charge_id)
    return charge_out(db, charge, db.get(Player, charge.player_id))


# --- caixa e extrato ---


@router.get("/finance/cash", response_model=CashOut)
def get_cash(db: DbSession):
    summary = cashbox.cash_summary(db)
    return CashOut(
        balance_cents=summary.balance_cents,
        initial_cents=summary.initial_cents,
        received_cents=summary.received_cents,
        expenses_cents=summary.expenses_cents,
    )


@router.get("/finance/statement", response_model=StatementOut)
def get_statement(db: DbSession, month: str | None = None):
    reference, first, last = _month_bounds(month)
    opening, entries = cashbox.statement(db, first, last)
    closing = entries[0].balance_cents if entries else opening
    return StatementOut(
        month=reference,
        opening_cents=opening,
        closing_cents=closing,
        entries=[
            StatementEntryOut(
                kind=e.kind,
                day=e.day,
                description=e.description,
                amount_cents=e.amount_cents,
                balance_cents=e.balance_cents,
            )
            for e in entries
        ],
    )


# --- cobranças ---


@router.get("/finance/monthly-fees", response_model=list[ChargeOut])
def monthly_fees(db: DbSession, month: str | None = None):
    reference, _, _ = _month_bounds(month)
    rows = billing.list_charges(db, type=ChargeType.MONTHLY_FEE, reference=reference)
    return [charge_out(db, c, p) for c, p in rows]


@router.post("/finance/monthly-fees/generate", response_model=GenerateOut)
def generate_monthly_fees(body: GenerateIn, db: DbSession):
    year, month = billing.parse_month(body.month)
    result = billing.generate_monthly_fees(db, year, month)
    return GenerateOut(month=result.reference, created=result.created)


@router.get("/finance/drop-ins", response_model=list[ChargeOut])
def drop_in_charges(db: DbSession, month: str | None = None):
    _, first, last = _month_bounds(month)
    rows = billing.list_charges(db, type=ChargeType.DROP_IN, due_from=first, due_to=last)
    return [charge_out(db, c, p) for c, p in rows]


@router.get("/finance/open-charges", response_model=list[ChargeOut])
def open_charges(db: DbSession, player_id: int | None = None):
    rows = billing.list_charges(db, open_only=True, player_id=player_id)
    return [charge_out(db, c, p) for c, p in rows]


@router.post("/charges/{charge_id}/pay", response_model=ChargeOut)
def pay(charge_id: int, body: PayIn, db: DbSession):
    billing.register_payment(db, charge_id, method=body.method)
    return _charge_by_id(db, charge_id)


@router.post("/charges/{charge_id}/undo-payment", response_model=ChargeOut)
def undo_payment(charge_id: int, db: DbSession):
    billing.undo_payment(db, charge_id)
    return _charge_by_id(db, charge_id)


@router.post("/charges/{charge_id}/waive", response_model=ChargeOut)
def waive(charge_id: int, db: DbSession):
    billing.waive(db, charge_id)
    return _charge_by_id(db, charge_id)


@router.post("/charges/{charge_id}/unwaive", response_model=ChargeOut)
def unwaive(charge_id: int, db: DbSession):
    billing.unwaive(db, charge_id)
    return _charge_by_id(db, charge_id)


# --- despesas ---


@router.get("/expenses", response_model=list[ExpenseOut])
def list_expenses(db: DbSession, month: str | None = None):
    _, first, last = _month_bounds(month)
    return [ExpenseOut.model_validate(e, from_attributes=True) for e in cashbox.list_expenses(db, first, last)]


@router.post("/expenses", response_model=ExpenseOut, status_code=status.HTTP_201_CREATED)
def create_expense(body: ExpenseIn, db: DbSession):
    expense = cashbox.create_expense(
        db,
        day=body.date,
        description=body.description,
        category=body.category,
        amount_cents=body.amount_cents,
    )
    return ExpenseOut.model_validate(expense, from_attributes=True)


@router.delete("/expenses/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_expense(expense_id: int, db: DbSession):
    cashbox.delete_expense(db, expense_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
