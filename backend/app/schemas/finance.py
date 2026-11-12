from datetime import date, datetime

from pydantic import BaseModel, Field

from app.models.enums import (
    ChargeStatus,
    ChargeType,
    ExpenseCategory,
    ExpenseType,
    PaymentMethod,
    Position,
)


class CashOut(BaseModel):
    balance_cents: int
    initial_cents: int
    received_cents: int
    expenses_cents: int


class ChargeOut(BaseModel):
    id: int
    player_id: int
    player_name: str
    player_position: Position
    type: ChargeType
    reference: str
    amount_cents: int
    due_date: date
    status: ChargeStatus
    game_id: int | None
    paid_at: datetime | None
    payment_method: PaymentMethod | None


class PayIn(BaseModel):
    method: PaymentMethod = PaymentMethod.PIX


class GenerateIn(BaseModel):
    month: str = Field(pattern=r"^\d{4}-\d{2}$")


class GenerateOut(BaseModel):
    month: str
    created: int


class ExpenseIn(BaseModel):
    date: date
    description: str = Field(default="", max_length=200)
    category: ExpenseCategory
    amount_cents: int = Field(gt=0)


class ExpenseOut(BaseModel):
    id: int
    date: date
    description: str
    category: ExpenseCategory
    type: ExpenseType
    amount_cents: int


class StatementEntryOut(BaseModel):
    kind: str
    day: date
    description: str
    amount_cents: int
    balance_cents: int


class StatementOut(BaseModel):
    month: str
    opening_cents: int  # caixa no início do mês
    closing_cents: int  # caixa no fim do mês (ou agora, se for o mês atual)
    entries: list[StatementEntryOut]
