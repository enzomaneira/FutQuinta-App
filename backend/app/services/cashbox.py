"""Caixa, despesas e extrato.

Caixa atual = saldo inicial + tudo recebido (mensalidades + avulsos)
              - despesas.
Nada é guardado em contadores: tudo é calculado a partir de pagamentos e
despesas, então desfazer um pagamento ou apagar uma despesa corrige o caixa.
"""

from dataclasses import dataclass
from datetime import date, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.clock import now_utc
from app.models.charge import Charge
from app.models.enums import ChargeType, ExpenseCategory, ExpenseType
from app.models.expense import Expense
from app.models.game import Game
from app.models.payment import Payment
from app.models.player import Player
from app.services.errors import DomainError, NotFoundError
from app.services.schedule import local_date_of
from app.services.settings import get_setting

CATEGORY_LABEL = {
    ExpenseCategory.COURT: "Quadra",
    ExpenseCategory.BIBS: "Coletes",
    ExpenseCategory.BALL: "Bola",
    ExpenseCategory.OTHER: "Outros",
}


# --- caixa ---


@dataclass(frozen=True)
class CashSummary:
    initial_cents: int
    received_cents: int
    expenses_cents: int

    @property
    def balance_cents(self) -> int:
        return self.initial_cents + self.received_cents - self.expenses_cents


def cash_summary(db: Session) -> CashSummary:
    received = db.scalar(select(func.coalesce(func.sum(Payment.amount_cents), 0)))
    spent = db.scalar(select(func.coalesce(func.sum(Expense.amount_cents), 0)))
    return CashSummary(
        initial_cents=int(get_setting(db, "initial_cash_cents")),
        received_cents=int(received),
        expenses_cents=int(spent),
    )


# --- despesas ---


def create_expense(
    db: Session,
    *,
    day: date,
    description: str,
    category: ExpenseCategory,
    amount_cents: int,
) -> Expense:
    """Despesa lançada pelo organizador. Quadra é fixa; as demais, variáveis."""
    if amount_cents <= 0:
        raise DomainError("Informe um valor maior que zero")
    text = " ".join(description.split()) or CATEGORY_LABEL[category]
    expense = Expense(
        date=day,
        description=text,
        category=category,
        type=ExpenseType.FIXED if category == ExpenseCategory.COURT else ExpenseType.VARIABLE,
        amount_cents=amount_cents,
    )
    db.add(expense)
    db.commit()
    db.refresh(expense)
    return expense


def ensure_court_expense(db: Session, year: int, month: int) -> Expense | None:
    """Lança o aluguel da quadra do mês (uma vez por mês). Não lança nada se o
    valor configurado for zero."""
    amount = int(get_setting(db, "court_monthly_cents"))
    if amount <= 0:
        return None
    reference = f"{year:04d}-{month:02d}"
    existing = db.scalar(
        select(Expense).where(
            Expense.category == ExpenseCategory.COURT, Expense.reference == reference
        )
    )
    if existing is not None:
        return existing
    expense = Expense(
        date=date(year, month, 1),
        description=f"Aluguel da quadra {month:02d}/{year}",
        category=ExpenseCategory.COURT,
        type=ExpenseType.FIXED,
        amount_cents=amount,
        reference=reference,
    )
    db.add(expense)
    db.commit()
    return expense


def delete_expense(db: Session, expense_id: int) -> None:
    expense = db.get(Expense, expense_id)
    if expense is None:
        raise NotFoundError("Despesa não encontrada")
    db.delete(expense)
    db.commit()


def list_expenses(db: Session, first_day: date, last_day: date) -> list[Expense]:
    return list(
        db.scalars(
            select(Expense)
            .where(Expense.date >= first_day, Expense.date <= last_day)
            .order_by(Expense.date.desc(), Expense.id.desc())
        )
    )


# --- extrato ---


@dataclass
class StatementEntry:
    kind: str  # "payment" (entrada) ou "expense" (saída)
    day: date
    description: str
    amount_cents: int  # positivo = entrada; negativo = saída
    balance_cents: int  # caixa logo depois deste lançamento
    sort_key: datetime


def statement(db: Session, first_day: date, last_day: date) -> tuple[int, list[StatementEntry]]:
    """Lançamentos do período com o saldo após cada um (mais recentes primeiro).
    Devolve também o saldo no início do período."""
    entries: list[StatementEntry] = []

    payments = db.execute(
        select(Payment, Charge, Player, Game)
        .join(Charge, Charge.id == Payment.charge_id)
        .join(Player, Player.id == Charge.player_id)
        .outerjoin(Game, Game.id == Charge.game_id)
    ).tuples()
    for payment, charge, player, game in payments:
        if charge.type == ChargeType.MONTHLY_FEE:
            year, month = charge.reference.split("-")
            what = f"Mensalidade {month}/{year}"
        else:
            day = local_date_of(game.starts_at) if game else charge.due_date
            what = f"Avulso {day:%d/%m}"
        entries.append(
            StatementEntry(
                kind="payment",
                day=local_date_of(payment.paid_at),
                description=f"{what} — {player.name}",
                amount_cents=payment.amount_cents,
                balance_cents=0,
                sort_key=payment.paid_at,
            )
        )

    for expense in db.scalars(select(Expense)):
        entries.append(
            StatementEntry(
                kind="expense",
                day=expense.date,
                description=expense.description,
                amount_cents=-expense.amount_cents,
                balance_cents=0,
                # Despesa sem horário: conta no início do dia
                sort_key=datetime.combine(expense.date, datetime.min.time()).replace(
                    tzinfo=now_utc().tzinfo
                ),
            )
        )

    # Saldo corrido do mais antigo para o mais novo
    entries.sort(key=lambda e: (e.day, e.sort_key))
    balance = int(get_setting(db, "initial_cash_cents"))
    opening = balance
    for entry in entries:
        if entry.day < first_day:
            opening += entry.amount_cents
        balance += entry.amount_cents
        entry.balance_cents = balance

    in_period = [e for e in entries if first_day <= e.day <= last_day]
    in_period.reverse()
    return opening, in_period
