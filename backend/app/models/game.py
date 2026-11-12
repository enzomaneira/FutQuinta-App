from datetime import datetime

from sqlalchemy import DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.enums import GameStatus, db_enum
from app.models.mixins import TimestampMixin


class Game(TimestampMixin, Base):
    """Jogo semanal. Horários em UTC; data/hora local é derivada.

    `starts_at` é único: a rotina de terça pode rodar de novo sem duplicar.
    """

    __tablename__ = "games"

    id: Mapped[int] = mapped_column(primary_key=True)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), unique=True)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[GameStatus] = mapped_column(
        db_enum(GameStatus), default=GameStatus.DRAFT
    )
    bib_player_id: Mapped[int | None] = mapped_column(
        ForeignKey("players.id", ondelete="SET NULL")
    )  # responsável pelos coletes
    confirmation_deadline: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    goalkeeper_slots: Mapped[int] = mapped_column(default=2)
    field_slots: Mapped[int] = mapped_column(default=15)
