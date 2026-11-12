import datetime as dt

from sqlalchemy import Date, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.enums import ExpenseCategory, ExpenseType, db_enum
from app.models.mixins import TimestampMixin


class Expense(TimestampMixin, Base):
    """Despesa. Para a quadra (fixa), `reference` = "AAAA-MM" evita lançar duas
    vezes no mesmo mês. Despesas variáveis deixam `reference` nulo."""

    __tablename__ = "expenses"
    __table_args__ = (UniqueConstraint("category", "reference"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    date: Mapped[dt.date] = mapped_column(Date)
    description: Mapped[str] = mapped_column(String(200))
    category: Mapped[ExpenseCategory] = mapped_column(db_enum(ExpenseCategory))
    type: Mapped[ExpenseType] = mapped_column(db_enum(ExpenseType))
    amount_cents: Mapped[int]
    reference: Mapped[str | None] = mapped_column(String(30))
