from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.enums import PlayerType, Position, db_enum
from app.models.mixins import TimestampMixin


class Player(TimestampMixin, Base):
    """Jogador (mensalista ou avulso).

    A fila de avulsos segue a ordem de candidatura em cada jogo
    (attendances.created_at), por isso não há campo de prioridade aqui.
    """

    __tablename__ = "players"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    phone: Mapped[str | None] = mapped_column(String(20), unique=True)  # E.164
    type: Mapped[PlayerType] = mapped_column(db_enum(PlayerType))
    position: Mapped[Position] = mapped_column(db_enum(Position))
    active: Mapped[bool] = mapped_column(default=True)
    # Só para avulsos: o mensalista que trouxe o jogador
    referred_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("players.id", ondelete="SET NULL"), index=True
    )
