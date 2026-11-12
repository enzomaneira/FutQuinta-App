from datetime import date

from sqlalchemy import Date, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.enums import ChargeStatus, ChargeType, db_enum
from app.models.mixins import TimestampMixin


class Charge(TimestampMixin, Base):
    """Cobrança. `reference` é "AAAA-MM" para mensalidade e "game:<id>" para avulso.

    O único (player_id, type, reference) torna a geração de cobranças idempotente.
    """

    __tablename__ = "charges"
    __table_args__ = (UniqueConstraint("player_id", "type", "reference"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    player_id: Mapped[int] = mapped_column(
        ForeignKey("players.id", ondelete="RESTRICT"), index=True
    )
    game_id: Mapped[int | None] = mapped_column(
        ForeignKey("games.id", ondelete="SET NULL")
    )  # preenchido só para cobranças de avulso
    type: Mapped[ChargeType] = mapped_column(db_enum(ChargeType))
    reference: Mapped[str] = mapped_column(String(30))
    amount_cents: Mapped[int]
    due_date: Mapped[date] = mapped_column(Date)
    status: Mapped[ChargeStatus] = mapped_column(
        db_enum(ChargeStatus), default=ChargeStatus.PENDING
    )
