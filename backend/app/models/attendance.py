from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.enums import AttendanceSource, AttendanceStatus, SlotType, db_enum
from app.models.mixins import TimestampMixin


class Attendance(TimestampMixin, Base):
    """Presença de um jogador em um jogo.

    Para avulsos, `queued_at` define a posição na fila (ordem de candidatura).
    """

    __tablename__ = "attendances"
    __table_args__ = (UniqueConstraint("game_id", "player_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    game_id: Mapped[int] = mapped_column(
        ForeignKey("games.id", ondelete="CASCADE"), index=True
    )
    player_id: Mapped[int] = mapped_column(
        ForeignKey("players.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[AttendanceStatus] = mapped_column(db_enum(AttendanceStatus))
    slot_type: Mapped[SlotType] = mapped_column(db_enum(SlotType))
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Momento em que o avulso entrou na fila; define a ordem de chamada.
    # Se ele sair e voltar, recebe um horário novo (vai para o fim da fila).
    queued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    late_cancellation: Mapped[bool] = mapped_column(default=False)  # em cima da hora
    source: Mapped[AttendanceSource] = mapped_column(
        db_enum(AttendanceSource), default=AttendanceSource.APP
    )
